"""Choose freely named media through the production UI; disks stay protected."""
import argparse,importlib.util,json,re,shlex,time
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--media',choices=['hexen','ogx'],default='hexen');a=p.parse_args();f=a.folder.resolve()
def cmd(code):
 try:result=m.serial(f/'serial.sock',code)
 except (FileNotFoundError,ConnectionRefusedError):return ''
 with (f/'media-commands.log').open('a') as out:out.write(result)
 return result
def wait(code,token,timeout=180):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  result=cmd(code)
  if token in result:return result
  time.sleep(2)
 raise TimeoutError(token)
def key(k):m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey '+k+' 140'}});time.sleep(.6)
def frame(name):
 ppm=f/(name+'.ppm');m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))
def rpc(action):
 code="import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall("+repr((json.dumps(dict(action=action))+'\n').encode())+");print('MEDIA_RESULT='+s.makefile().readline())"
 values=re.findall(r'MEDIA_RESULT=(\{[^\r\n]+\})',cmd('python3 -c '+shlex.quote(code)))
 if not values:return {}
 result=json.loads(values[-1]);assert result['ok'],result
 return result['data']
wait("grep -q 'UI: janela pronta' /run/console/interface.log && printf 'UI_%s\\n' READY",'UI_READY')
stamp=(f/'ssd.img').stat().st_mtime_ns
cmd('mkdir -p /mnt/input; mountpoint -q /mnt/input || mount -t 9p -o trans=virtio,version=9p2000.L,ro userfiles /mnt/input')
cmd("grep -q MEDIA_SETUP_PASS /run/media-setup.log 2>/dev/null || pgrep -f '^python3 /mnt/input/media-setup.py$' >/dev/null || setsid python3 /mnt/input/media-setup.py > /run/media-setup.log 2>&1 < /dev/null &")
wait('cat /run/media-setup.log','MEDIA_SETUP_PASS',900)
cmd("mount -o remount,rw /console && sed -i 's/net_interface=auto/net_interface=none/' /console/config/ports.conf && mount -o remount,ro /console")
for _ in range(3):key('esc')
key('ret');key('down');key('ret')
rows=rpc('hello')['live_images'];assert len(rows)==4,rows
(f/'media-list.json').write_text(json.dumps(rows,indent=2));frame('all-media-visible')
key('ret')
for i in range(15):
 status=rpc('status')
 if status and not status['busy']:break
 time.sleep(1)
assert status.get('error'),status
assert len(rpc('hello')['live_images'])==4
frame('invalid-media-still-listed')
which='HeXEn' if a.media=='hexen' else 'OGXbox'
index=next(i for i,row in enumerate(rows) if which in row['name'])
for _ in range(index):key('down')
key('ret')
wait("systemctl is-active --quiet console.service && grep -q RUNNING /proc/asound/card0/pcm0p/sub0/status && printf 'MEDIA_CONSOLE_%s\\n' ACTIVE",'MEDIA_CONSOLE_ACTIVE',180)
cmd('python3 /mnt/input/live-ftp-guest.py protected > /run/media-ftp.log 2>&1 < /dev/null &')
wait('cat /run/media-ftp.log','LIVE_FTP_READ_WRITE_PASS',240)
output=cmd('python3 /mnt/input/safe-live-guest.py proof')
proof=json.loads(re.findall(r'SAFE_PROOF=(\{[^\r\n]+\})',output)[-1])
proof.update(media=which,all_four_listed=True,invalid_media_remains_listed=True,ftp_passed=True)
assert (f/'ssd.img').stat().st_mtime_ns==stamp
(f/'media-proof.json').write_text(json.dumps(proof,indent=2));frame('guest-'+a.media)
print('MEDIA_GUI_FTP_PASS',which,flush=True);cmd('systemctl --no-block poweroff')
