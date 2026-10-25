"""Verify real Xemu generation, immediate persistence and identity across reboot.

Reads private EEPROM bytes only inside the disposable VM; emits hashes, never
serial/MAC/HDD keys. No mutation RPC or physical disk is used.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import time
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();f=a.folder.resolve()

def command(c):
    result=m.serial(f/'serial.sock',c)
    with (f/'eeprom-proof.log').open('a') as out:out.write(result)
    return result

snippet='''from pathlib import Path
import sys,hashlib,json
sys.path.insert(0,'/usr/local/lib/console/platform/tools')
import eeprom
def identity(data):
 assert len(data)==256
 ver,plain=eeprom.decrypt(data)
 assert ver is not None
 return hashlib.sha256(plain[8:24]+data[0x34:0x46]).hexdigest()
a=Path('/run/console/eeprom.bin').read_bytes()
b=Path('/console/firmware/xbox/eeprom.bin').read_bytes()
assert identity(a)==identity(b)
print(json.dumps(dict(identity=identity(b),runtime_sha=hashlib.sha256(a).hexdigest(),stored_sha=hashlib.sha256(b).hexdigest(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),build=json.loads(Path('/usr/share/console/build.json').read_text())['version'])))
'''

def wait_ready():
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        result=command("systemctl is-active --quiet console.service && test -s /console/firmware/xbox/eeprom.bin && grep -q RUNNING /proc/asound/card0/pcm0p/sub0/status && printf 'EEPROM_%s\\n' READY")
        if 'EEPROM_READY' in result:break
        time.sleep(3)
    else:raise TimeoutError('Xemu generation / immediate EEPROM persistence')
    text=command('python3 -c '+shlex.quote(snippet))
    rows=re.findall(r'\{"identity": [^\r\n]+\}',text)
    if not rows:raise RuntimeError('No identity verification result')
    return json.loads(rows[-1])

first=wait_ready();assert first['build']=='0.1.0-beta.3'
print('XEMU_GENERATION_AND_IMMEDIATE_PERSISTENCE_PASS',first['identity'],flush=True)
command('systemctl --no-block reboot')
# Wait until the guest actually has a new boot id; the old runtime may still be ready.
deadline=time.monotonic()+180
while time.monotonic()<deadline:
    time.sleep(3)
    raw=command('cat /proc/sys/kernel/random/boot_id')
    ids=re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',raw)
    if ids and ids[-1]!=first['boot_id']:break
else:raise TimeoutError('No actual guest reboot')
second=wait_ready();assert second['boot_id']!=first['boot_id'] and second['identity']==first['identity']
(f/'eeprom-persistence.json').write_text(json.dumps(dict(first=first,second=second,verified=True),indent=2)+'\n')
print('EEPROM_IDENTITY_PRESERVED_ACROSS_REBOOT_PASS',flush=True)
