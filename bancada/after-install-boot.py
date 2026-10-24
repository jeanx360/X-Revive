"""Power off a completed QA installer and boot its regular SSD without USB."""
from pathlib import Path
import importlib.util,json,subprocess,time,os,sys
folder=Path(sys.argv[1]);s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
while True:
 p=folder/'install-status.json';data=json.loads(p.read_text()) if p.exists() else {}
 if (data.get('result') or {}).get('verified'):break
 if data.get('error'):raise RuntimeError(data['error'])
 time.sleep(3)
time.sleep(3);print(m.serial(folder/'serial.sock','systemctl poweroff'),flush=True)
pid=int((folder/'pid').read_text());deadline=time.monotonic()+60
while True:
 try:os.kill(pid,0)
 except ProcessLookupError:break
 if time.monotonic()>deadline:raise TimeoutError('QA installer poweroff')
 time.sleep(1)
subprocess.run(['python3',str(Path(__file__).with_name('boot-installed.py')),str(folder/'ssd.img'),str(folder/'ssd-boot')],check=True)
