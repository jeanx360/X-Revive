"""Exercise the real source-selection GUI then double confirmation on a QA SSD."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import time
from PIL import Image

s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('mode',choices=('online','offline'));p.add_argument('--monitor',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args();f=a.folder.resolve()

def command(c):
 r=m.serial(f/'serial.sock',c);print(r,flush=True);return r

def key(k,hold=120):
 m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':f'sendkey {k} {hold}'}});time.sleep(.6)

def frame(name):
 ppm=f/(name+'.ppm');m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))

def status():
 raw=command("python3 -c \"import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall(b'{\\\"action\\\":\\\"status\\\"}\\n');print(s.makefile().readline())\"")
 rows=re.findall(r'\{"ok": true, "data": .*\}',raw)
 return json.loads(rows[-1])['data'] if rows else {}

if not a.monitor:
 before=(f/'ssd.img').stat().st_mtime_ns
 if not a.resume:
  deadline=time.monotonic()+180
  while time.monotonic()<deadline:
   r=command('test -s /run/console/interface.log && cat /run/console/interface.log')
   if 'UI: janela pronta' in r:break
   time.sleep(3)
  else:raise TimeoutError('No initial UI frame')
  time.sleep(2);frame('welcome')
  key('ret');frame('sources')
  if a.mode=='offline':key('down')
  key('ret')
  if a.mode=='offline':time.sleep(1);key('ret')
 deadline=time.monotonic()+5400
 while time.monotonic()<deadline:
  st=status();(f/'prepare-status.json').write_text(json.dumps(st,indent=2))
  assert (f/'ssd.img').stat().st_mtime_ns==before,'target changed during package preparation'
  if st.get('error'):frame('prepare-error');raise RuntimeError(st['error'])
  if (st.get('result') or {}).get('ready') and not st['busy']:break
  time.sleep(10)
 else:raise TimeoutError('package preparation')
 time.sleep(2);frame('disks')
 key('ret');time.sleep(8);frame('confirm1')
 key('esc');assert (f/'ssd.img').stat().st_mtime_ns==before
 key('ret');time.sleep(8);key('f10',5000);time.sleep(6);frame('confirm2-held')
 assert (f/'ssd.img').stat().st_mtime_ns==before,'held keyboard bypassed second confirmation'
 key('f10',5000);time.sleep(6);frame('installing')
 print('NO_EARLY_TARGET_WRITE_PASS',flush=True)

deadline=time.monotonic()+3000
while time.monotonic()<deadline:
 st=status();(f/'install-status.json').write_text(json.dumps(st,indent=2))
 if st.get('error'):frame('install-error');raise RuntimeError(st['error'])
 if (st.get('result') or {}).get('verified') and not st['busy']:
  frame('complete');print('FULL_INSTALL_PASS',st['result'],flush=True);break
 time.sleep(10)
else:raise TimeoutError('install')
