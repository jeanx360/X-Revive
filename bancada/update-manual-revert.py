"""Use the actual R maintenance menu to revert; no mutation RPCs."""
import importlib.util,json,subprocess,sys,time
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
f=Path(sys.argv[1])
def command(c):
 raw=m.serial(f/'serial.sock',c);print(raw,flush=True);return raw
subprocess.run(['python3',str(Path(__file__).with_name('recovery-boot-check.py')),str(f)],check=True)
def key(k):
 m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey '+k+' 100'}});time.sleep(.5)
key('down');key('ret')
for _ in range(3):key('down')
ppm=(f/'manual-revert-option.ppm').resolve();m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))
key('ret');time.sleep(3)
raw=command('cat /var/cache/console/updates/state.json')
assert '"active":null' in raw and '"pending":null' in raw
command("python3 -c \"from urllib.request import urlretrieve;urlretrieve('http://10.0.2.2:8866/verify-ftp-persist.py','/run/verify-ftp-persist.py')\"; python3 /run/verify-ftp-persist.py >/run/qa-persist.log 2>&1 &")
end=time.monotonic()+120
while time.monotonic()<end:
 raw=command('cat /run/qa-persist.log')
 if 'FTP_USER_FILE_AND_LAYOUT_PRESERVED' in raw:break
 if 'Traceback' in raw:raise RuntimeError(raw)
 time.sleep(2)
else:raise TimeoutError('persist')
print('MANUAL_R_REVERT_AND_FTP_PERSIST_PASS',flush=True)
