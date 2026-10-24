"""Run INSIDE a test VM: ask UnleashX to open/close and require real QMP events.

The VM must have an isolated NAT forward 2121 -> guest 21. This tests commands
handled by the dashboard, not merely a direct QMP request from the test runner.
"""
import ftplib
import json
from pathlib import Path
import subprocess
import time

run = Path('/run/console')
events = run/'tray-events.log'
start = events.stat().st_size if events.exists() else 0
pid = subprocess.check_output(['pgrep', '-f', '^/opt/xemu']).decode().strip()
deadline = time.monotonic()+150
while True:
    ftp = ftplib.FTP()
    try:
        ftp.connect('127.0.0.1', 2121, timeout=6)
        print(ftp.getwelcome(), flush=True)
        ftp.login('xbox', 'xbox')
        break
    except (OSError, EOFError) as exc:
        ftp.close()
        if time.monotonic() > deadline:
            raise
        print('Waiting for dashboard FTP:', str(exc), flush=True)
        time.sleep(3)

for index, command in enumerate(('SITE TRAYOPEN', 'SITE TRAYCLOSE', 'SITE TRAYOPEN', 'SITE TRAYCLOSE')):
    print(command, ftp.sendcmd(command), flush=True)
    time.sleep(3)
    if index == 0:
        assert (run/'tray-open').exists()
        # Reproduce a udev notification arriving after ejecting was cleared.
        subprocess.run(['systemctl','start','console-media.service'],check=True)
        print('DELAYED_MEDIA_EVENT_REQUESTED',flush=True)
    time.sleep(3)
ftp.close()
after = subprocess.check_output(['pgrep', '-f', '^/opt/xemu']).decode().strip()
log = events.read_bytes()[start:].decode()
print(log, flush=True)
states = [event['data']['tray-open'] for line in log.splitlines()
          if line.startswith('{') and (event := json.loads(line)).get('event') == 'DEVICE_TRAY_MOVED']
assert states == [True, False, True, False], states
assert pid == after, (pid, after)
print(json.dumps(dict(result='PASS', pid=pid, tray_states=states)), flush=True)
