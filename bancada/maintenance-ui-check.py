"""Exercise maintenance UI with keyboard; RPC reads only monitor completion."""
import argparse,importlib.util,json,re,time
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();f=a.folder

def cmd(text):
 r=m.serial(f/'serial.sock',text);print(r,flush=True);return r

def invariant(mode,marker):
 cmd('python3 /run/maintenance-invariants.py '+mode+' >/run/maintenance-check.log 2>&1 &')
 deadline=time.monotonic()+120
 while time.monotonic()<deadline:
  raw=cmd('cat /run/maintenance-check.log')
  if marker in raw:return raw
  if 'Traceback' in raw:raise RuntimeError(raw)
  time.sleep(2)
 raise TimeoutError('maintenance invariants')

def key(k):
 for down in (True,False):
  m.qmp(f/'vm.qmp',{'execute':'input-send-event','arguments':{'events':[{'type':'key','data':{'down':down,'key':{'type':'qcode','data':k}}}]}})
  time.sleep(.12)
 time.sleep(.2)

def frame(name):
 ppm=(f/(name+'.ppm')).resolve();m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))

def wait():
 deadline=time.monotonic()+120
 while time.monotonic()<deadline:
  raw=cmd("python3 -c \"import socket;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall(b'{\\\"action\\\":\\\"status\\\"}\\n');print(s.makefile().readline())\"")
  match=re.findall(r'\{"ok": true, "data": .*\}',raw)
  if match:
   status=json.loads(match[-1])['data']
   if not status['busy']:
    if status.get('error'):raise ValueError(status['error'])
    return
  time.sleep(2)
 raise TimeoutError('maintenance job')

cmd("python3 -c \"from urllib.request import urlretrieve;urlretrieve('http://10.0.2.2:8866/maintenance-invariants.py','/run/maintenance-invariants.py')\"")
raw=invariant('before','MAINTENANCE_BASELINE');assert 'MAINTENANCE_BASELINE' in raw
key('down');key('ret');frame('maintenance-options')
key('down');key('ret');wait();frame('maintenance-repair-complete')
raw=invariant('repair','MAINTENANCE_REPAIR_NO_FORMAT_PASS');assert 'MAINTENANCE_REPAIR_NO_FORMAT_PASS' in raw
key('esc');key('down');key('ret');key('down');key('down');key('ret');frame('maintenance-dashboard-options')
for _ in range(5):key('down')
key('ret');wait();frame('maintenance-dashboard-complete')
raw=invariant('dashboard','MAINTENANCE_DASHBOARD_NO_FORMAT_PASS');assert 'MAINTENANCE_DASHBOARD_NO_FORMAT_PASS' in raw
print('MAINTENANCE_KEYBOARD_UI_PASS',flush=True)
