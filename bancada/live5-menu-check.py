"""Exercise unified production UI on disposable QEMU files, including USB HDD."""
import argparse,importlib.util,json,re,shlex,time
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--media',choices=['hexen','ogxbox','rocky5-offline'],required=True);p.add_argument('--access',choices=['virtual','protected','write'],default='virtual');p.add_argument('--setup',action='store_true');p.add_argument('--reboot-after-setup',action='store_true');p.add_argument('--leave-running',action='store_true');a=p.parse_args();f=a.folder.resolve()
def cmd(code):
 try:result=m.serial(f/'serial.sock',code)
 except (FileNotFoundError,ConnectionRefusedError,TimeoutError):return ''
 with (f/'menu-commands.log').open('a') as out:out.write(result)
 return result
def wait(code,token,timeout=240):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  result=cmd(code)
  if token in result:return result
  time.sleep(2)
 raise TimeoutError(token)
def key(k,hold=140):m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':f'sendkey {k} {hold}'}});time.sleep(hold/1000+.5)
def frame(name):
 ppm=f/(name+'.ppm');m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))
def rpc(action,**args):
 code="import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall("+repr((json.dumps(dict(action=action,**args))+'\n').encode())+");print('LIVE5_RESULT='+s.makefile().readline())"
 values=re.findall(r'LIVE5_RESULT=(\{[^\r\n]+\})',cmd('python3 -c '+shlex.quote(code)))
 if not values:return {}
 result=json.loads(values[-1]);assert result['ok'],result
 return result['data']
wait("grep -q 'UI: janela pronta' /run/console/interface.log && printf 'UI_%s\\n' READY",'UI_READY')
frame('unified-welcome')
cmd('mkdir -p /mnt/input; mountpoint -q /mnt/input || mount -t 9p -o trans=virtio,version=9p2000.L,ro userfiles /mnt/input')
cmd("mount -o remount,rw /console && sed -i 's/net_interface=auto/net_interface=none/' /console/config/ports.conf && mount -o remount,ro /console")
if a.setup:
 cmd('mkdir -p /mnt/input; mountpoint -q /mnt/input || mount -t 9p -o trans=virtio,version=9p2000.L,ro userfiles /mnt/input')
 cmd('setsid python3 /mnt/input/live5-setup.py '+shlex.quote(a.media)+' > /run/live5-setup.log 2>&1 < /dev/null &')
 wait('cat /run/live5-setup.log','LIVE5_SETUP_PASS',900)
 if a.reboot_after_setup:
  cmd('systemctl --no-block reboot');time.sleep(10)
  wait("test -f /run/console/dongle.json && grep -q 'UI: janela pronta' /run/console/interface.log && printf 'UI_%s\\n' REBOOTED",'UI_REBOOTED',240)
  cmd('mkdir -p /mnt/input; mount -t 9p -o trans=virtio,version=9p2000.L,ro userfiles /mnt/input')
  output=cmd("cat /run/console/dongle.json; sha256sum /usr/lib/firmware/xone_dongle_*.bin")
  (f/'dongle-import.log').write_text(output);assert '02fe.bin' in output
  frame('unified-after-reboot')
for _ in range(4):key('esc')
key('ret');frame('live-modes')
if a.access=='write':key('down')
key('ret');key('down');key('ret');frame('media-list')
rows=rpc('hello')['live_images'];assert len(rows)==1,rows
(f/'media-list.json').write_text(json.dumps(rows,indent=2))
key('ret');frame('disk-selection')
disks=rpc('media-disks')['disks'];(f/'disk-list.json').write_text(json.dumps(disks,indent=2))
if a.access!='virtual':
 index=next(i for i,row in enumerate(disks) if row.get('serial') in ('XREVIVE-QA-USB-HDD','XREVIVE-QA-SSD'))
 if a.access=='protected':index+=1
 for _ in range(index):key('down')
key('ret')
if a.access=='write':
 frame('write-confirm1');before=rpc('status');assert not before['busy']
 # Holding through the transition MUST NOT accept the second screen.
 key('f10',3000);frame('write-confirm2');assert not rpc('status')['busy']
 time.sleep(.4);key('f10',1600)
for _ in range(750):
 status=rpc('status')
 if status and not status['busy']:
  if status.get('error'):frame('error');raise AssertionError(status)
  break
 time.sleep(2)
else:raise TimeoutError('LIVE preparation')
wait("systemctl is-active --quiet console.service && grep -q RUNNING /proc/asound/card0/pcm0p/sub0/status && printf 'LIVE5_CONSOLE_%s\\n' ACTIVE",'LIVE5_CONSOLE_ACTIVE',240)
time.sleep(15);frame('xbox-'+a.media)
cmd('python3 /mnt/input/live-ftp-guest.py '+('normal' if a.access=='write' else 'protected')+' > /run/live5-ftp.log 2>&1 < /dev/null &')
wait('cat /run/live5-ftp.log','LIVE_FTP_READ_WRITE_PASS',240)
code="import json,subprocess;from pathlib import Path;s=json.loads(Path('/run/xrevive-live/session.json').read_text());print('LIVE5_STATE='+json.dumps(s));print(subprocess.check_output(['lsblk','-o','PATH,TYPE,TRAN,RO,SERIAL'],text=True));print('EEPROM',len(Path('/run/console/eeprom.bin').read_bytes()))"
output=cmd('python3 -c '+shlex.quote(code));state=json.loads(re.findall(r'LIVE5_STATE=(\{[^\r\n]+\})',output)[-1])
(f/'session-proof.log').write_text(output)
assert state['mode']==('sandbox' if a.access=='virtual' else a.access)
(f/'proof.json').write_text(json.dumps(dict(media=a.media,access=a.access,ftp=True,audio=True,state=state),indent=2))
cmd('python3 /mnt/input/live5-proof.py '+shlex.quote(a.media)+' > /run/live5-proof-final.log 2>&1 < /dev/null &')
output=wait('cat /run/live5-proof-final.log','LIVE5_PROOF=',120)
(f/'disk-guards-proof.log').write_text(output)
assert 'LIVE5_PROOF=' in output,output
print('LIVE5_GUI_FTP_PASS',a.media,a.access,flush=True)
if not a.leave_running:cmd('systemctl --no-block poweroff')
