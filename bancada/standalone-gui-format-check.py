"""Inside QA VM: arm keyboard for HeXEn, then inspect its actual formatting."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

assert 'QEMU' in Path('/sys/class/dmi/id/sys_vendor').read_text()
spec=importlib.util.spec_from_file_location('l','/usr/local/lib/console/standalone.py')
layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
info=json.loads((layout.PRIVATE_STATE/'state.json').read_text());data=info['layout']
layout.read_verified(info['boot_device'],data)
with open(info['boot_device'],'rb',buffering=0) as disk:
    disk.seek(data['system']['offset']);digest=hashlib.sha256(disk.read(16*1024**2)).hexdigest()
if sys.argv[1]=='before':
    Path('/run/gui-format-before.json').write_text(json.dumps(dict(system_sha256=digest)))
    subprocess.run(['systemctl','stop','console.service'],check=True)
    p=Path('/run/console/xemu.toml')
    p.write_text(p.read_text()+'\n[input.bindings]\nport1="keyboard"\n')
    subprocess.run(['systemctl','start','console.service'],check=True)
    print('ARMED_HEXEN_KEYBOARD',digest,flush=True)
elif sys.argv[1]=='after':
    assert digest==json.loads(Path('/run/gui-format-before.json').read_text())['system_sha256']
    signatures={}
    with open(info['xbox_device'],'rb',buffering=0) as disk:
        for name,offset,_ in layout.RETAIL+[('DRIVE F',layout.F_OFFSET,0)]:
            disk.seek(offset);signatures[name]=disk.read(4).decode(errors='replace')
    print('RETAIL_SIGNATURES',signatures,flush=True)
    assert set(signatures.values())=={'FATX'},signatures
    print('HEXEN_GUI_FORMAT_RETAIL_AND_PROTECTED_SYSTEM_PASS',data['xbox_bytes'],digest,flush=True)
else:raise ValueError('before|after')
