"""Copy user files from a readonly 9p share into an already booted QA USB."""
import argparse
import importlib.util
from pathlib import Path
import time
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--offline',action='store_true');a=p.parse_args()
f=a.folder.resolve();assert (f/'ssd.img').is_file()
before=(f/'ssd.img').stat().st_mtime_ns
deadline=time.monotonic()+180
while time.monotonic()<deadline:
 result=m.serial(f/'serial.sock',"mountpoint -q /userdata && test -d /userdata/X-Revive/firmware && printf 'USER_AREA_%s\\n' READY")
 if 'USER_AREA_READY' in result:break
 time.sleep(2)
else:raise TimeoutError('Área pessoal não preparada')
cmd="grep -q QEMU /sys/class/dmi/id/sys_vendor && mountpoint -q /userdata && mkdir -p /mnt/input && (mountpoint -q /mnt/input || mount -t 9p -o trans=virtio,version=9p2000.L,ro userfiles /mnt/input) && rm -f /run/xrevive-user-files-ready && cp -r /mnt/input/X-Revive/firmware /userdata/X-Revive/"
if a.offline:cmd+=' && cp /mnt/input/X-Revive/pacotes/rocky5-offline.iso /userdata/X-Revive/pacotes/'
cmd+=" && sync -f /userdata && touch /run/xrevive-user-files-ready && printf 'USER_FILES_%s\\n' READY"
print(m.serial(f/'serial.sock',cmd),flush=True)
deadline=time.monotonic()+240
while time.monotonic()<deadline:
 time.sleep(2)
 result=m.serial(f/'serial.sock',"test -f /run/xrevive-user-files-ready && test -s /userdata/X-Revive/firmware/xbox/bios.bin"+(' && test -s /userdata/X-Revive/pacotes/rocky5-offline.iso' if a.offline else '')+" && printf 'COPIED_%s\\n' PASS")
 print(result,flush=True)
 if 'COPIED_PASS' in result:break
else:raise TimeoutError('copy')
assert (f/'ssd.img').stat().st_mtime_ns==before
