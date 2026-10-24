"""INSIDE isolated QA VM: verify native F size and transfer with a SHA check."""
import argparse
import ftplib
import hashlib
import io
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expect-f-total', required=True)
args = parser.parse_args()
deadline = time.monotonic()+150
while True:
    ftp = ftplib.FTP()
    try:
        ftp.connect('127.0.0.1', 2121, timeout=6)
        ftp.login('xbox', 'xbox')
        break
    except (OSError, EOFError):
        ftp.close()
        if time.monotonic() > deadline:
            raise
        time.sleep(3)

banner = ftp.getwelcome()
print(banner, flush=True)
f_line = next(line for line in banner.splitlines() if 'Drive F' in line)
assert 'Total: '+args.expect_f_total in f_line, f_line
# Active data connection goes to the Xemu NAT gateway (the Linux VM itself).
ftp.set_pasv(False)
sendport = ftp.sendport
ftp.sendport = lambda host, port: sendport('10.0.2.2', port)
payload = bytes(range(256))*1024
ftp.cwd('/F')
print('STOR', ftp.storbinary('STOR xrevive-qa.bin', io.BytesIO(payload)), flush=True)
result = io.BytesIO()
print('RETR', ftp.retrbinary('RETR xrevive-qa.bin', result.write), flush=True)
assert result.getvalue() == payload
print('F_LIMIT_AND_FTP_PASS', len(payload), hashlib.sha256(payload).hexdigest(), flush=True)
ftp.quit()
