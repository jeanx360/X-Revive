"""FTP through Xemu NAT inside the disposable Linux QA VM only."""
import ftplib
import io
from pathlib import Path
import sys
import time

assert 'QEMU' in Path('/sys/class/dmi/id/sys_vendor').read_text()
mode=sys.argv[1];assert mode in ('protected','normal')
deadline=time.monotonic()+180
while True:
    ftp=ftplib.FTP()
    try:
        ftp.connect('127.0.0.1',2121,timeout=6);ftp.login('xbox','xbox');break
    except (OSError,EOFError,ftplib.Error):
        ftp.close()
        if time.monotonic()>deadline:raise
        time.sleep(3)
ftp.set_pasv(False)
sendport=ftp.sendport
ftp.sendport=lambda host,port:sendport('10.0.2.2',port)
probe=b'X-Revive isolated LIVE QA '+mode.encode()
ftp.storbinary('STOR /E/xrevive-live-probe.txt',io.BytesIO(probe))
received=bytearray();ftp.retrbinary('RETR /E/xrevive-live-probe.txt',received.extend);ftp.quit()
assert bytes(received)==probe
print('LIVE_FTP_READ_WRITE_PASS',mode,flush=True)
