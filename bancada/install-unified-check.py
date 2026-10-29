"""Regression of full installer using regular QEMU SSD/USB images only."""
import argparse,importlib.util,json,re,shlex,time
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();f=a.folder.resolve()
def cmd(code):
 try:out=m.serial(f/'serial.sock',code)
 except (FileNotFoundError,ConnectionRefusedError):return ''
 with (f/'install-commands.log').open('a') as stream:stream.write(out)
 return out
def wait(code,token,timeout=240):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  out=cmd(code)
  if token in out:return out
  time.sleep(2)
 raise TimeoutError(token)
def rpc(action):
 code="import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall("+repr((json.dumps(dict(action=action))+'\n').encode())+");print('INSTALL_RESULT='+s.makefile().readline())"
 values=re.findall(r'INSTALL_RESULT=(\{[^\r\n]+\})',cmd('python3 -c '+shlex.quote(code)))
 if not values:return {}
 result=json.loads(values[-1]);assert result['ok'],result;return result['data']
def key(k,hold=140):m.qmp(f/'vm.qmp',dict(execute='human-monitor-command',arguments={'command-line':f'sendkey {k} {hold}'}));time.sleep(.5+hold/1000)
def frame(name):
 ppm=f/(name+'.ppm');m.qmp(f/'vm.qmp',dict(execute='screendump',arguments=dict(filename=str(ppm))));Image.open(ppm).save(ppm.with_suffix('.png'))
def idle(timeout):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  status=rpc('status')
  if status and not status['busy']:
   frame('idle-'+str(status.get('progress',0)));assert not status.get('error'),status;return status
  time.sleep(2)
 raise TimeoutError('installer job')
wait("grep -q 'UI: janela pronta' /run/console/interface.log && printf 'UI_%s\\n' READY",'UI_READY')
hello=rpc('hello');assert not hello['safe_live'] and not hello['installed']
frame('welcome');key('down');key('ret');key('down');key('ret');frame('offline-list');key('ret')
ready=idle(1200);assert ready['result']['ready'];frame('target-disks')
rows=rpc('hello')['disks'];index=next(i for i,row in enumerate(rows) if row.get('serial')=='XREVIVE-QA-USB-HDD')
assert rows[index]['available'];assert len(rows)==2
(f/'disks.json').write_text(json.dumps(rows,indent=2))
for _ in range(index):key('down')
key('ret');frame('confirm1');key('f10',3000);assert not rpc('status')['busy'];frame('confirm2');key('f10',1600)
result=idle(1800);assert result['result']['verified'];frame('installed')
(f/'result.json').write_text(json.dumps(result,indent=2))
print('NORMAL_INSTALL_USB_VERIFIED_PASS',flush=True);cmd('systemctl --no-block poweroff')
