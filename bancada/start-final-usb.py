"""Reuse isolated QA user data with new production system and readonly fixtures."""
import fcntl
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import time
from stat import S_ISREG

root=Path(__file__).resolve().parents[1];old=root/'bancada/validacao-online-offline';f=root/'bancada/validacao-online-final';f.mkdir(exist_ok=True)
image=root/'cartucho/cache/repack.8cG5QD/console-xbox-installer.img'
usb=f/'installer.img';subprocess.run(['cp','--reflink=auto',str(image),str(usb)],check=True)
ssource=old/'installer.img'
with ssource.open('rb') as src,usb.open('r+b') as dst:
 assert S_ISREG(__import__('os').fstat(src.fileno()).st_mode) and S_ISREG(__import__('os').fstat(dst.fileno()).st_mode)
 rows=json.loads(subprocess.check_output(['sfdisk','-J',str(image)],text=True))['partitiontable']['partitions'];p=next(x for x in rows if x['name']=='XREVIVE')
 off=p['start']*512;size=p['size']*512
 fcntl.ioctl(dst.fileno(),0x4020940d,struct.pack('qQQQ',src.fileno(),off,size,off))
(f/'debug').touch();subprocess.run(['mcopy','-o','-i',str(usb)+'@@1048576',str(f/'debug'),'::/debug'],check=True)
subprocess.run(['cp','--reflink=auto',str(old/'ssd.img'),str(f/'ssd.img')],check=True)
shutil.copyfile('/usr/share/edk2/ovmf/OVMF_VARS.fd',f/'OVMF_VARS.fd')
cmd=json.loads((old/'command.json').read_text());i=cmd.index('-virtfs');del cmd[i:i+2]
cmd=[x.replace(str(old),str(f)) for x in cmd]
(f/'command.json').write_text(json.dumps(cmd,indent=2))
with (f/'qemu.log').open('w') as log:
 p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);(f/'pid').write_text(str(p.pid));print('FINAL_USB',p.pid,flush=True)
 while p.poll() is None:time.sleep(1)
