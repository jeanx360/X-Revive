"""Exercise the production USB-only LIVE using keys and a disposable PC disk."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import time
from PIL import Image

s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--online',action='store_true')
a=p.parse_args();f=a.folder.resolve()


def command(code):
    try:result=m.serial(f/'serial.sock',code)
    except (FileNotFoundError,ConnectionRefusedError):return ''
    with (f/'safe-commands.log').open('a') as out:out.write(result)
    return result


def wait(code,token,seconds=180):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        result=command(code)
        if token in result:return result
        time.sleep(2)
    raise TimeoutError(token)


def frame(name):
    ppm=f/(name+'.ppm');m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}})
    Image.open(ppm).save(ppm.with_suffix('.png'))


def key(name):
    m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':f'sendkey {name} 120'}})
    time.sleep(.7)


wait("grep -q 'UI: janela pronta' /run/console/interface.log && printf 'SAFE_UI_%s\\n' READY",'SAFE_UI_READY')
stamp=(f/'ssd.img').stat().st_mtime_ns
frame('welcome')
command('mkdir -p /mnt/input; mountpoint -q /mnt/input || mount -t 9p -o trans=virtio,version=9p2000.L,ro userfiles /mnt/input')
command('python3 /mnt/input/safe-live-guest.py setup '+('online' if a.online else 'offline')+' > /run/safe-setup.log 2>&1 &')
wait('cat /run/safe-setup.log','SAFE_SETUP_PASS',240)
# Nested VM network setup only. This edits the disposable USB, never the PC disk.
command("mount -o remount,rw /console && sed -i 's/net_interface=auto/net_interface=none/' /console/config/ports.conf && mount -o remount,ro /console")
key('ret');frame('sources')
if not a.online:key('down')
key('ret')
if not a.online:time.sleep(1);key('ret')
wait("systemctl is-active --quiet console.service && grep -q RUNNING /proc/asound/card0/pcm0p/sub0/status && printf 'SAFE_CONSOLE_%s\\n' ACTIVE",'SAFE_CONSOLE_ACTIVE',300)
time.sleep(15);frame('rocky-boot')
command('python3 /mnt/input/live-ftp-guest.py protected > /run/safe-ftp.log 2>&1 &')
wait('cat /run/safe-ftp.log','LIVE_FTP_READ_WRITE_PASS',240)
output=wait('python3 /mnt/input/safe-live-guest.py proof','SAFE_PROOF=',30)
proof=json.loads(re.findall(r'SAFE_PROOF=(\{[^\r\n]+\})',output)[-1])
assert (f/'ssd.img').stat().st_mtime_ns==stamp
proof.update(online=a.online,gui_keyboard=True,ftp_passed=True,pc_disk_mtime_unchanged=True)
(f/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');frame('rocky-menu')
key('down');time.sleep(1);frame('keyboard-navigation')
print('SAFE_LIVE_PASS',a.online,proof['protected_devices'],flush=True)
command('systemctl --no-block poweroff')
