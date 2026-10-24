"""Translate virtual Xbox eject to the physical tray via QMP."""
import json
from pathlib import Path
import socket
import struct
import threading
import subprocess
import time


def wants_eject(event, recovery):
    return (not recovery and event.get("event") == "DEVICE_TRAY_MOVED"
            and event.get("data", {}).get("tray-open") is True)


def tray_action(event, recovery):
    if recovery or event.get('event') != 'DEVICE_TRAY_MOVED':
        return None
    state = event.get('data', {}).get('tray-open')
    if type(state) is bool:
        return 'open' if state else 'close'
    return None


def wants_poweroff(event):
    data=event.get('data',{})
    return (event.get('event')=='SHUTDOWN' and data.get('guest') is True
            and data.get('reason')=='guest-shutdown')


def monitor(run=Path("/run/console")):
    from updater import atomic
    while True:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(str(run / "xemu.qmp"))
                with sock.makefile("rwb", buffering=0) as stream:
                    if not json.loads(stream.readline()).get("QMP"):
                        raise ValueError("QMP greeting ausente")
                    stream.write(b'{"execute":"qmp_capabilities"}\r\n')
                    # Reuse this sole QMP connection; opening another client blocks Xemu.
                    stopped = threading.Event()
                    def heartbeat(sock=sock, stopped=stopped):
                        while not stopped.is_set():
                            try: sock.sendall(b'{"execute":"query-status","id":"xrevive-health"}\r\n')
                            except OSError: return
                            stopped.wait(5)
                    threading.Thread(target=heartbeat, daemon=True).start()
                    pid = struct.unpack('3i',sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))[0]
                    for line in stream:
                        event = json.loads(line)
                        if event.get('id') == 'xrevive-health' and event.get('return',{}).get('status') == 'running':
                            atomic(Path('/run/xrevive-update/qmp-ready.json'), {'pid':pid, 'at':time.monotonic()})
                        if event.get("event"):
                            with (run / "tray-events.log").open("a") as log:
                                log.write(json.dumps(event) + "\n")
                        if wants_poweroff(event):
                            subprocess.run(['systemctl','--no-block','poweroff'],check=False)
                        action = tray_action(event, any((run / flag).exists() for flag in ("boot-hexen", "boot-ogxbox", "ejecting")))
                        if action:
                            subprocess.run(["systemctl", "--no-block", "start",
                                            "console-bandeja@"+action+".service"], check=False)
        except (OSError, ValueError) as exc:
            print(f"tray-monitor: {exc}", flush=True)
        finally:
            if 'stopped' in locals(): stopped.set()
        time.sleep(1)


if __name__ == "__main__":
    monitor()
