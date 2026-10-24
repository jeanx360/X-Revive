import array
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "cartucho/overlay/usr/local/lib/console"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hardware = load("hardware", LIB / "hardware.py")
held = load("held", ROOT / "plataformas/xbox/tools/held.py")
tray = load("tray", LIB / "tray-monitor.py")


class RecoveryHardwareTest(unittest.TestCase):
    def test_only_explicit_guest_shutdown_powers_off_host(self):
        self.assertTrue(tray.wants_poweroff({'event':'SHUTDOWN','data':{'guest':True,'reason':'guest-shutdown'}}))
        self.assertFalse(tray.wants_poweroff({'event':'SHUTDOWN','data':{'guest':False,'reason':'host-signal'}}))
        self.assertFalse(tray.wants_poweroff({'event':'RESET','data':{'guest':True,'reason':'guest-reset'}}))

    def test_R_and_controller_combo(self):
        def ioctl_for(keys):
            def ioctl(fd, req, buf, mutate):
                for key in keys:
                    buf[key >> 3] |= 1 << (key & 7)
            return ioctl
        with tempfile.NamedTemporaryFile() as f:
            for keys, combo, expected in [([19], (19,), True), ([18], (19,), False),
                                          ([314, 315], held.COMBO, True), ([314], held.COMBO, False)]:
                with patch.object(held.fcntl, "ioctl", ioctl_for(keys)):
                    self.assertEqual(held.held(f.name, combo), expected)

    def test_late_input_and_timeout(self):
        now = [0.0]
        sleep = lambda seconds: now.__setitem__(0, now[0] + seconds)
        self.assertTrue(held.wait_held(8, lambda: now[0] > 2, lambda: now[0], sleep))
        self.assertFalse(held.wait_held(1, lambda: False, lambda: now[0], sleep))

    def test_wired_prefers_carrier_excludes_wifi_and_virtual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, carrier in [("enp1s0", "0"), ("enp2s0", "1"), ("wlan0", "1"), ("lo", "1")]:
                dev = root / name
                dev.mkdir()
                (dev / "type").write_text("1")
                (dev / "carrier").write_text(carrier)
                if name != "lo":
                    (dev / "device").mkdir()
                if name == "wlan0":
                    (dev / "wireless").mkdir()
            self.assertEqual(hardware.wired_interface(root), "enp2s0")
            self.assertEqual(hardware.wired_interface(root, "enp1s0"), "enp1s0")
            self.assertEqual(hardware.wired_interface(root, "wlan0"), "")

    def test_audio_playback_selection(self):
        pcm = ('00-03: HDMI 0 : HDMI 0 : playback 1\n'
               '01-00: ALC897 Analog : playback 1 : capture 1\n'
               '01-02: Alt Analog : capture 1\n')
        self.assertEqual(hardware.audio_device(pcm), "plughw:1,0")
        self.assertEqual(hardware.audio_device(pcm, "hdmi"), "plughw:0,3")
        self.assertEqual(hardware.audio_device(""), "")

    def test_guest_eject_only_when_physical_mode(self):
        event = {"event": "DEVICE_TRAY_MOVED", "data": {"tray-open": True}}
        self.assertTrue(tray.wants_eject(event, False))
        self.assertFalse(tray.wants_eject(event, True))
        self.assertFalse(tray.wants_eject({"event": "RESET"}, False))
        event["data"]["tray-open"] = False
        self.assertFalse(tray.wants_eject(event, False))
        self.assertEqual(tray.tray_action(event, False), 'close')
        self.assertIsNone(tray.tray_action(event, True))

    def test_physical_eject_stops_emulator_and_restarts_even_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dvd").write_text("/dev/test-dvd")
            bindir = root / "bin"
            bindir.mkdir()
            for name, script in {
                "systemctl": '#!/bin/sh\nprintf "%s\\n" "$*" >> "$RUN/order"\n',
                "eject": '#!/bin/sh\necho eject >> "$RUN/order"\nexit "${EJECT_RESULT:-0}"\n',
                "sleep": '#!/bin/sh\nexit 0\n',
            }.items():
                path = bindir / name
                path.write_text(script)
                path.chmod(0o755)
            env = dict(os.environ, RUN=tmp, PATH=str(bindir) + ":" + os.environ["PATH"])
            for result in (0, 1):
                (root / "order").write_text("")
                proc = subprocess.run(["sh", str(LIB / "bandeja.sh")],
                                      env=dict(env, EJECT_RESULT=str(result)), capture_output=True)
                self.assertEqual(proc.returncode, result)
                expected = ['eject'] if result == 0 else ['eject', 'stop console.service', 'eject', 'start console.service']
                self.assertEqual((root / "order").read_text().splitlines(), expected)
                self.assertFalse((root / "ejecting").exists())

    def test_recovery_overrides_physical_dvd_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "utils").mkdir()
            (root / "utils/hexen.iso").touch()
            (root / "boot-hexen").touch()
            (root / "dvd").write_text("/dev/sr0")
            app = root / "fake-xemu"
            app.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$RUN/args"\n')
            app.chmod(0o755)
            env = dict(os.environ, RUN=tmp, CONSOLE=tmp, XEMU_APP=str(app),
                       WAYLAND_DISPLAY="", CONSOLE_CPUSET="")
            for _ in range(2):
                subprocess.run(["sh", str(ROOT / "plataformas/xbox/run.sh")], env=env, check=True,
                               capture_output=True)
                args = (root / "args").read_text().splitlines()
                self.assertEqual(args[args.index("-dvd_path") + 1], str(root / "utils/hexen.iso"))
                self.assertIn("-qmp", args)
                self.assertTrue((root / "boot-hexen").exists())

    def test_late_media_event_preserves_open_tray_but_inserted_disc_restarts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); bindir=root/'bin'; bindir.mkdir()
            (root/'dvd').write_text('/dev/test-dvd')
            for name,body in {
                'udevadm':'#!/bin/sh\n[ "${MEDIA_PRESENT:-0}" = 0 ] || echo ID_CDROM_MEDIA=1\n',
                'systemctl':'#!/bin/sh\necho "$*" >> "$RUN/restarts"\n',
            }.items():
                path=bindir/name;path.write_text(body);path.chmod(0o755)
            env=dict(os.environ,RUN=tmp,PATH=str(bindir)+':'+os.environ['PATH'])
            (root/'tray-open').touch()
            subprocess.run(['sh',str(LIB/'media-change.sh')],env=env,check=True)
            self.assertFalse((root/'restarts').exists())
            self.assertTrue((root/'tray-open').exists())
            subprocess.run(['sh',str(LIB/'media-change.sh')],env=dict(env,MEDIA_PRESENT='1'),check=True)
            self.assertEqual((root/'restarts').read_text().strip(),'--no-block restart console.service')
            self.assertFalse((root/'tray-open').exists())
            (root/'restarts').unlink();(root/'boot-ogxbox').touch()
            subprocess.run(['sh',str(LIB/'media-change.sh')],env=dict(env,MEDIA_PRESENT='1'),check=True)
            self.assertFalse((root/'restarts').exists())

    def test_configure_fatx_recovery_and_enabled_lan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fw = root / "firmware/xbox"
            fw.mkdir(parents=True)
            for name in ("mcpx_1.0.bin", "bios.bin", "eeprom.bin"):
                (fw / name).touch()
            (root / "utils").mkdir()
            (root / "utils/hexen.iso").touch()
            profile = root / "profile"
            profile.write_text("renderer=OPENGL\nrender_scale=1\nfingerprint=abcdef012345\n")
            bindir = root / "bin"
            bindir.mkdir()
            scripts = {
                "chown": "#!/bin/sh\nexit 0\n",
                "install": '#!/bin/sh\nwhile [ "$#" -gt 2 ]; do shift; done\ncp "$1" "$2"\n',
                "python3": f'#!/bin/sh\ncase "$1" in */held.py) echo "${{BOOT_SELECTION:-installer}}"; exit 0;; esac\nexec {sys.executable} "$@"\n',
            }
            for name, text in scripts.items():
                path = bindir / name
                path.write_text(text)
                path.chmod(0o755)
            env = dict(os.environ, PATH=str(bindir) + ":" + os.environ["PATH"],
                       CONSOLE=tmp, RUN=tmp, PROFILE=str(profile), HDD_FATX="yes",
                       HDD="/dev/test-hdd", DVD="/dev/sr0", NET_BACKEND="pcap", NET_INTERFACE="enp2s0")
            subprocess.run(["sh", str(ROOT / "plataformas/xbox/configure.sh")], env=env,
                           check=True, capture_output=True)
            config = tomllib.loads((root / "xemu.toml").read_text())
            self.assertTrue((root / "installer").exists())
            self.assertIn('Iniciando manutencao X-Revive', (root/'boot-message').read_text())
            self.assertTrue(config["net"]["enable"])
            self.assertEqual(config["net"]["pcap"]["netif"], "enp2s0")
            self.assertEqual(config["net"]["nat"]["forward_ports"][0]["guest"], 21)
            self.assertFalse(config['general']['skip_boot_anim'])
            (root/'ogxbox.iso').touch()
            subprocess.run(['sh', str(ROOT/'plataformas/xbox/configure.sh')],
                           env=dict(env, BOOT_SELECTION='', UTILS=tmp, HDD_FATX='no'),
                           check=True, capture_output=True)
            self.assertTrue((root/'installer').exists())
            self.assertIn('manutencao X-Revive',(root/'boot-message').read_text())
            self.assertFalse((root/'boot-hexen').exists())
            self.assertFalse((root/'boot-ogxbox').exists())
            (root/'utils/ogxbox.iso').touch()
            env.update(UTILS=str(root/'utils'), XEMU_APP=str(root/'fake-xemu'),
                       WAYLAND_DISPLAY='', CONSOLE_CPUSET='')
            app = root/'fake-xemu'
            app.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$RUN/args"\n')
            app.chmod(0o755)
            for _ in range(2):
                subprocess.run(['sh', str(ROOT/'plataformas/xbox/run.sh')], env=env,
                               check=True, capture_output=True)
                args = (root/'args').read_text().splitlines()
                self.assertEqual(args[args.index('-dvd_path')+1], '')
                self.assertFalse((root/'boot-ogxbox').exists())


if __name__ == "__main__":
    unittest.main()
