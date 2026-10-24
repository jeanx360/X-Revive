"""ONLY inside the isolated standalone QEMU VM: format its bounded Xbox loop.

Requires --confirm-vm, QEMU DMI, standalone cmdline, private verified layout and
an exact loop size. Never used by the product or on physical test hardware.
The dashboard fixture is exported from a copied local virtual HDD, not shipped.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.request import urlretrieve
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--confirm-vm', action='store_true', required=True)
parser.add_argument('--skip-format', action='store_true',help='usar FATX ja formatado pela interface HeXEn')
args=parser.parse_args()
assert 'QEMU' in Path('/sys/class/dmi/id/sys_vendor').read_text()
assert 'xrevive.standalone=1' in Path('/proc/cmdline').read_text().split()
spec = importlib.util.spec_from_file_location('layout','/usr/local/lib/console/standalone.py')
layout = importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
info = json.loads((layout.PRIVATE_STATE/'state.json').read_text())
device, data = info['boot_device'],info['layout']
loop = Path(info['xbox_device']).resolve()
assert loop.name.startswith('loop')
assert int(subprocess.check_output(['blockdev','--getsize64',str(loop)])) == data['xbox_bytes']
layout.read_verified(device,data)
subprocess.run(['systemctl','stop','console.service'],check=True)

def boot_hash():
    with open(device,'rb',buffering=0) as disk:
        disk.seek(data['system']['offset'])
        return hashlib.sha256(disk.read(16*1024**2)).hexdigest()

before = boot_hash()
from pyfatx import Fatx
from pyfatx.libfatx import lib
if args.skip_format:
    with loop.open('rb',buffering=0) as disk:
        for offset in [item[1] for item in layout.RETAIL]+[layout.F_OFFSET]:
            disk.seek(offset);assert disk.read(4)==b'FATX'
else:
    handle = lib.pyfatx_open_helper()
    assert lib.fatx_disk_format(handle,str(loop).encode(),512,2,32) == 0
layout.read_verified(device,data)
layout.finalize('/run/console')
assert boot_hash() == before
urlretrieve('http://10.0.2.2:8866/standalone-c-fixture.zip','/run/c-fixture.zip')
spec = importlib.util.spec_from_file_location('hdd','/usr/local/lib/console/platform/tools/hdd.py')
hdd = importlib.util.module_from_spec(spec);spec.loader.exec_module(hdd)
c = Fatx(str(loop),drive='c')
with zipfile.ZipFile('/run/c-fixture.zip') as archive:
    for name in archive.namelist():
        content = archive.read(name)
        if name.lower() == 'config.xml':
            content = re.sub(rb'<Network Type="[^"]+"',b'<Network Type="Static"',content)
            content = re.sub(rb'<IP>[^<]+</IP>',b'<IP>10.0.2.15</IP>',content)
            content = re.sub(rb'<Gateway>[^<]+</Gateway>',b'<Gateway>10.0.2.2</Gateway>',content)
        hdd.put(c,'/'+name,content)
del c
e = Fatx(str(loop),drive='e')
hdd.put(e,'/xrevive-fresh-format.txt',b'fresh standalone FATX persists')
del e
for flag in ('boot-hexen','boot-ogxbox'):
    Path('/run/console',flag).unlink(missing_ok=True)
config = Path('/run/console/xemu.toml')
config.write_text(re.sub(r"backend = '[^']+'", "backend = 'nat'",config.read_text()))
print('FRESH_BOUNDED_FORMAT_AND_SYSTEM_PRESERVATION_PASS',data['xbox_bytes'],before,flush=True)
subprocess.run(['systemctl','start','console.service'],check=True)
