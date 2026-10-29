"""GUI/FTP validation of read-only hybrid LIVE and optional existing-disk boot."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

from PIL import Image

spec=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--prepare-boot',action='store_true')
p.add_argument('--pad',action='store_true');p.add_argument('--resume-disks',action='store_true');p.add_argument('--boot-only',action='store_true')
a=p.parse_args();f=a.folder.resolve()


def command(text):
    try:result=m.serial(f/'serial.sock',text)
    except (FileNotFoundError,ConnectionRefusedError):return ''
    with (f/'hybrid-commands.log').open('a') as out:out.write(result)
    return result


def rpc(action):
    code="import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall("+repr((json.dumps(dict(action=action))+'\n').encode())+");print('HYBRID_RESULT='+s.makefile().readline())"
    rows=re.findall(r'HYBRID_RESULT=(\{[^\r\n]*\})',command('python3 -c '+shlex.quote(code)))
    if not rows:return {}
    result=json.loads(rows[-1])
    if not result['ok']:raise RuntimeError(result)
    return result['data']


def key(name,hold=160):
    if a.pad:command('echo '+{'down':'down','ret':'A','esc':'B','f10':'confirm'}[name]+' > /run/xrevive-pad-command')
    else:m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':f'sendkey {name} {hold}'}})
    time.sleep(.8)


def frame(name):
    image=f/(name+'.ppm');m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(image)}})
    Image.open(image).save(image.with_suffix('.png'))


deadline=time.monotonic()+200
while time.monotonic()<deadline:
    if 'UI_READY' in command("grep -q 'UI: janela pronta' /run/console/interface.log && printf 'UI_%s\\n' READY"):break
    time.sleep(3)
else:raise TimeoutError('initial UI')
before=(f/'ssd.img').stat().st_mtime_ns
if not a.resume_disks:
    subprocess.run(['python3',str(Path(__file__).with_name('populate-user-usb.py')),str(f)],check=True)
    assert 'QA_NAT_READY' in command("grep -q QEMU /sys/class/dmi/id/sys_vendor && mount -o remount,rw /console && sed -i 's/net_interface=auto/net_interface=none/' /console/config/ports.conf && mount -o remount,ro /console && printf 'QA_NAT_%s\\n' READY")
    if a.pad:
        command('python3 /mnt/input/installer-pad.py > /run/live-pad.log 2>&1 &')
        time.sleep(2)
    frame('welcome');key('down');key('down');key('ret')
rows=rpc('live-disks')['disks'];assert len(rows)==1 and rows[0]['available'],rows
frame('recognized-hdd');key('ret');frame('two-options')
assert (f/'ssd.img').stat().st_mtime_ns==before
if a.prepare_boot:
    key('down');key('ret');frame('boot-confirm1');key('esc')
    assert (f/'ssd.img').stat().st_mtime_ns==before
    key('down');key('ret');key('f10',2500);time.sleep(3);frame('boot-confirm2')
    assert (f/'ssd.img').stat().st_mtime_ns==before
    key('f10',2500)
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        result=rpc('status');(f/'boot-status.json').write_text(json.dumps(result,indent=2)+'\n')
        if result.get('error'):frame('boot-error');raise RuntimeError(result['error'])
        if (result.get('result') or {}).get('boot_ready') and not result['busy']:break
        time.sleep(5)
    else:raise TimeoutError('boot preparation')
    time.sleep(2);frame('boot-ready')
    if a.boot_only:
        print('BOOT_PREPARED_BEFORE_ANY_XBOX_BOOT_PASS',flush=True)
        command('systemctl --no-block poweroff')
        raise SystemExit(0)
    before=(f/'ssd.img').stat().st_mtime_ns
key('ret')
deadline=time.monotonic()+150
while time.monotonic()<deadline:
    result=rpc('status')
    if result.get('error'):frame('live-error');raise RuntimeError(result['error'])
    if 'LIVE_ACTIVE' in command("systemctl is-active --quiet console.service && grep -q RUNNING /proc/asound/card0/pcm0p/sub0/status && printf 'LIVE_%s\\n' ACTIVE"):break
    time.sleep(3)
else:raise TimeoutError('LIVE activation')
code="import json,subprocess;from pathlib import Path;s=json.loads(Path('/run/xrevive-live/session.json').read_text());assert s['mode']=='protected';assert subprocess.check_output(['blockdev','--getro',s['loop']],text=True).strip()=='1';print('XBOX_LOOP_BYTES='+subprocess.check_output(['blockdev','--getsize64',s['loop']],text=True).strip())"
output=command('python3 -c '+shlex.quote(code));bounds=re.findall(r'XBOX_LOOP_BYTES=(\d+)',output);assert bounds
assert int(bounds[-1])<(f/'ssd.img').stat().st_size,'system tail exposed to Xbox'
command('python3 /mnt/input/live-ftp-guest.py protected > /run/live-ftp-result.log 2>&1 &')
deadline=time.monotonic()+240
while time.monotonic()<deadline:
    if 'LIVE_FTP_READ_WRITE_PASS' in command('cat /run/live-ftp-result.log'):break
    time.sleep(5)
else:raise TimeoutError('dashboard FTP')
frame('dashboard');assert (f/'ssd.img').stat().st_mtime_ns==before
(f/'live-proof.json').write_text(json.dumps(dict(boot_prepared=a.prepare_boot,controller=a.pad,
    read_only=True,no_live_writes=True,audio_running=True,ftp_passed=True,xbox_loop_bytes=int(bounds[-1])),indent=2)+'\n')
print('HYBRID_LIVE_GUI_FTP_PASS',a.prepare_boot,a.pad,flush=True)
command('systemctl --no-block poweroff')
