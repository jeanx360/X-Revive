"""Read-only preparation checks through real keyboard UI; no disk confirmation."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import time
from PIL import Image
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('mode',choices=('online','offline'));a=p.parse_args();f=a.folder.resolve()
def cmd(c):r=m.serial(f/'serial.sock',c);print(r,flush=True);return r
def frame(n):
 ppm=f/(n+'.ppm');m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))
def key(k):m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey '+k+' 150'}});time.sleep(1)
before=(f/'ssd.img').stat().st_mtime_ns
deadline=time.monotonic()+180
while time.monotonic()<deadline:
 r=cmd('test -s /run/console/interface.log && cat /run/console/interface.log')
 if 'UI: janela pronta' in r:break
 time.sleep(3)
else:raise TimeoutError('UI')
time.sleep(1);key('esc');key('ret')
if a.mode=='offline':key('down')
key('ret')
if a.mode=='offline':key('ret')
deadline=time.monotonic()+7200
while time.monotonic()<deadline:
 r=cmd("python3 -c \"import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall(b'{\\\"action\\\":\\\"status\\\"}\\n');print(s.makefile().readline())\"")
 rows=re.findall(r'\{"ok": true, "data": .*\}',r)
 if rows:
  status=json.loads(rows[-1])['data'];(f/(a.mode+'-prepare.json')).write_text(json.dumps(status,indent=2))
  assert (f/'ssd.img').stat().st_mtime_ns==before,'early target write'
  if status.get('error'):frame(a.mode+'-error');raise RuntimeError(status['error'])
  if (status.get('result') or {}).get('ready') and not status['busy']:
   frame(a.mode+'-ready');print('PREPARE_NO_TARGET_WRITE_PASS',a.mode,status['result'],flush=True);break
 time.sleep(10)
else:raise TimeoutError('prepare')
