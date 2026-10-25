"""Prove SSD-only normal boot, then actual R maintenance through virtual keys."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import time
from PIL import Image
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();f=a.folder.resolve()
def cmd(c):
 r=m.serial(f/'serial.sock',c)
 with (f/'proof.log').open('a') as out:out.write(r)
 print(r,flush=True);return r
def frame(n):
 p=f/(n+'.ppm');m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(p)}});Image.open(p).save(p.with_suffix('.png'))
def key(k):m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey '+k+' 150'}});time.sleep(1)
deadline=time.monotonic()+180
while time.monotonic()<deadline:
 r=cmd("systemctl is-active --quiet console.service && grep -q RUNNING /proc/asound/card0/pcm0p/sub0/status && printf 'SSD_%s\\n' ACTIVE")
 if 'SSD_ACTIVE' in r:break
 time.sleep(3)
else:raise TimeoutError('normal boot')
cmd('sha256sum /console/firmware/xbox/bios.bin; cat /usr/share/console/build.json; cat /run/console/profile')
for i in range(70):
 frame('console-%03d'%i);time.sleep(1)
frame('normal-dashboard')
cmd('systemctl --no-block reboot')
deadline=time.monotonic()+180
while time.monotonic()<deadline:
 m.qmp(f/'vm.qmp',{'execute':'input-send-event','arguments':{'events':[{'type':'key','data':{'down':False,'key':{'type':'qcode','data':'r'}}},{'type':'key','data':{'down':True,'key':{'type':'qcode','data':'r'}}}]}})
 time.sleep(1)
 r=cmd("test -f /run/console/installer && systemctl is-active --quiet console-installer.service && test -s /run/console/interface.log && printf 'MAINT_%s\\n' ACTIVE")
 if 'MAINT_ACTIVE' in r:break
else:raise TimeoutError('R maintenance')
m.qmp(f/'vm.qmp',{'execute':'input-send-event','arguments':{'events':[{'type':'key','data':{'down':False,'key':{'type':'qcode','data':'r'}}}]}})
time.sleep(4);frame('r-maintenance')
r=cmd("python3 -c \"import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall(b'{\\\"action\\\":\\\"hello\\\"}\\n');print(s.makefile().readline())\"")
rows=re.findall(r'\{"ok": true, "data": .*\}',r);assert rows
hello=json.loads(rows[-1])['data'];assert hello['installed'] and hello['files']==98996 and len(hello['dashboards'])==10
(f/'maintenance-hello.json').write_text(json.dumps(hello,indent=2))
key('down');key('ret');key('down');key('down');key('ret');time.sleep(2);frame('r-dashboard-list')
print('SSD_NORMAL_AND_R_MAINTENANCE_PASS',flush=True)
