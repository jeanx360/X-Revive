"""INSIDE QA VM, after reboot: validate the actual image runtime and FATX data."""
import hashlib
import importlib.util
import json
import subprocess

spec=importlib.util.spec_from_file_location('layout','/usr/local/lib/console/standalone.py')
layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
print(subprocess.check_output(['systemctl','is-active','console.service','console-prepare.service']).decode(),flush=True)
subprocess.run(['systemctl','stop','console.service'],check=True)
info=json.loads((layout.PRIVATE_STATE/'state.json').read_text());data=info['layout']
original=layout.read_verified(info['boot_device'],data)
assert original==layout.repair_sector(original,data)
from pyfatx import Fatx
e=Fatx(info['xbox_device'],drive='e')
marker=bytes(e.read('/xrevive-fresh-format.txt'));del e
assert marker==b'fresh standalone FATX persists'
f=Fatx(info['xbox_device'],offset=layout.F_OFFSET,size=data['xbox_bytes']-layout.F_OFFSET)
payload=bytes(f.read('/xrevive-qa.bin'));del f
assert payload==bytes(range(256))*1024
print('COMPLETE_IMAGE_FRESH_FORMAT_UEFI_REBOOT_PERSISTENCE_PASS',len(payload),hashlib.sha256(payload).hexdigest(),flush=True)
print('NATIVE_MBR_AND_FOOTER_VALID',data['xbox_bytes'],data['image_bytes'],flush=True)
