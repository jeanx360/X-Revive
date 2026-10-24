"""INSIDE isolated VM: dashboard eject of an actually opened host_device DVD.

Use a virtual external DVD containing an ISO. Empty-drive tests alone do not
prove that eject releases a busy backend. Closing with media may reboot Xemu.
"""
import fcntl
import ftplib
import json
import os
from pathlib import Path
import subprocess
import time

deadline = time.monotonic()+150
while True:
    ftp = ftplib.FTP()
    try:
        ftp.connect('127.0.0.1',2121,timeout=6);ftp.login('xbox','xbox');break
    except (OSError,EOFError):
        ftp.close()
        if time.monotonic() > deadline:raise
        time.sleep(3)

def pid():
    return subprocess.check_output(['pgrep','-f','^/opt/xemu']).decode().strip()

def state():
    fd=os.open('/dev/sr0',os.O_RDONLY|os.O_NONBLOCK)
    try:return fcntl.ioctl(fd,0x5326,0)
    finally:os.close(fd)

before=pid()
print(ftp.getwelcome(),flush=True)
print(ftp.sendcmd('SITE TRAYOPEN'),flush=True)
time.sleep(8)
assert pid()==before,(pid(),before)
assert state()==2,state()
assert Path('/run/console/tray-open').exists()
print('OPEN_WITH_MEDIA_BACKEND_RELEASED_PID_STABLE',before,flush=True)
print(ftp.sendcmd('SITE TRAYCLOSE'),flush=True)
ftp.close();time.sleep(8)
assert state()!=2,state()
print(json.dumps(dict(result='PASS',physical_tray_closed=True,pid_after_close=pid())),flush=True)
