"""Inside the final QA VM: verify unmodified product runtime, FTP and tray."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import urlretrieve

metadata=json.loads(Path('/usr/share/console/build.json').read_text())
binary=hashlib.sha256(Path('/opt/xemu/usr/bin/xemu').read_bytes()).hexdigest()
assert binary==metadata['emulator']['binary_sha256']
assert Path('/usr/local/lib/console/media-change.sh').is_file()
for name in ('standalone-ftp-check.py','tray-dashboard-check.py'):
    urlretrieve('http://10.0.2.2:8866/'+name,'/run/'+name)
subprocess.run([sys.executable,'/run/standalone-ftp-check.py','--expect-f-total','8.748,52MB'],check=True)
subprocess.run([sys.executable,'/run/tray-dashboard-check.py'],check=True)
print('FINAL_STANDALONE_FTP_TRAY_DELAYED_EVENT_PASS',metadata['build_id'],binary,flush=True)
