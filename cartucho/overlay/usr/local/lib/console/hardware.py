"""Prepare wired LAN and ALSA in the appliance, never the FATX HDD."""
from pathlib import Path
import re
import subprocess
import sys


def wired_interface(root, requested="auto"):
    candidates = []
    for link in sorted(Path(root).iterdir()):
        if not (link / "device").exists() or (link / "wireless").exists():
            continue
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", link.name):
            continue
        if (link / "type").read_text().strip() != "1":
            continue
        if requested != "auto" and link.name != requested:
            continue
        try:
            carrier = (link / "carrier").read_text().strip() == "1"
        except OSError:
            carrier = False
        candidates.append((not carrier, link.name))
    # An unplugged Ethernet port cannot carry pcap traffic. NAT also works
    # through the host's Wi-Fi; explicit port selections remain respected.
    if requested=='auto':candidates=[item for item in candidates if not item[0]]
    return min(candidates)[1] if candidates else ""


def audio_device(pcm, requested="auto"):
    options = []
    for line in pcm.splitlines():
        match = re.match(r"(\d+)-(\d+): (.*)", line)
        if not match or "playback" not in line:
            continue
        card, device = int(match[1]), int(match[2])
        hdmi = "HDMI" in line or "DisplayPort" in line
        if requested in ("analog", "hdmi") and (requested == "hdmi") != hdmi:
            continue
        options.append((hdmi, card, device))
    if re.fullmatch(r"plughw:\d+,\d+", requested):
        return requested
    if not options:
        return ""
    _, card, device = min(options)
    return f"plughw:{card},{device}"


def command(*args):
    print('XREVIVE_STAGE Configurando '+{'ip':'rede','ethtool':'conexão Ethernet','amixer':'saída de áudio','aplay':'dispositivos de áudio','nvidia-smi':'placa de vídeo'}.get(args[0],args[0])+'...',flush=True)
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=4)
        return result.stdout + result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)


def setup(run, config):
    run = Path(run)
    values = dict(line.split("=", 1) for line in Path(config).read_text().splitlines()
                  if "=" in line and not line.startswith("#"))
    interface = wired_interface("/sys/class/net", values.get("net_interface", "auto"))
    backend = "pcap" if interface else "nat"
    offloads = ""
    if interface:
        command("ip", "link", "set", "dev", interface, "up")
        # Pcap forwards Ethernet frames without GSO/GRO metadata. Coalesced
        # TCP segments/checksum offload can break transfers to the Xbox NIC.
        # Tested with 64 KiB FTP: truncated before, byte-identical after.
        for feature in ("gro", "gso", "tso", "lro", "tx", "rx"):
            offloads += feature + ": " + command("ethtool", "-K", interface, feature, "off") + "\n"
    pcm_path = Path("/proc/asound/pcm")
    pcm = pcm_path.read_text() if pcm_path.exists() else ""
    audio = audio_device(pcm, values.get("audio", "auto"))
    env = f"NET_BACKEND={backend}\nNET_INTERFACE={interface}\n"
    if audio:
        card, device = audio.removeprefix("plughw:").split(",")
        Path("/etc/asound.conf").write_text(
            f'pcm.!default {{ type plug slave.pcm "hw:{card},{device}" }}\n'
            f'ctl.!default {{ type hw card {card} }}\n')
        for control in ("Master", "PCM", "Front", "Speaker", "Headphone"):
            command("amixer", "-c", card, "sset", control, "80%", "unmute")
        command("amixer", "-c", card, "sset", "IEC958", "unmute")
        command("amixer", "-c", card, "sset", "Auto-Mute Mode", "Disabled")
        env += f"AUDIODEV={audio}\n"
    (run / "hardware.env").write_text(env)
    (run / "hardware.txt").write_text(
        env + "\nALSA PCM:\n" + pcm + "\nAudio devices:\n" + command("aplay", "-l")
        + "\nNetwork:\n" + command("ip", "-br", "address")
        + "\nRoutes:\n" + command("ip", "route") + "\nPcap offloads:\n" + offloads)
    with (run / "hardware.txt").open('a') as log:
        log.write('\nGraphics build:\n' + (Path('/etc/console-variant').read_text()
                  if Path('/etc/console-variant').exists() else 'universal\n'))
        if Path('/sys/module/nvidia').exists():
            log.write(command('nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'))
    print(f"console: rede={backend}:{interface} audio={audio or 'SEM SAIDA ALSA'}", file=sys.stderr)


if __name__ == "__main__":
    setup(*sys.argv[1:])
