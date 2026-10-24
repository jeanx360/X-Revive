"""Read the native formatter's output with independent upstream libfatx.

Run inside the isolated Debian QA container, with pyfatx installed. No format,
delete or write methods are called. Uses only a regular disposable image.
"""
import hashlib
import json
import os
from pathlib import Path

from pyfatx import Fatx

base=Path(os.environ.get('ROCKY5_QA','/qa'))
path=base/'qa/fatx64.img'
assert path.is_file()
lock=json.loads(Path('/src/cartucho/build/rocky5.lock.json').read_text())
loader=next(p for p in lock['packages'] if p['id']=='hardmod-evoxdash.xbe')
c=Fatx(str(path),drive='c')
assert hashlib.sha256(bytes(c.read('/evoxdash.xbe'))).hexdigest()==loader['sha256']
assert b'F:\\Dashboards\\XBMC4Gamers\\default.xbe' in bytes(c.read('/Dashloader.ini'))
del c
f=Fatx(str(path),offset=0x1dd156000,size=path.stat().st_size-0x1dd156000)
trainers=list(f.listdir('/Dashboards/XBMC4Gamers/trainers'))
assert len(trainers)>512
for item in (trainers[0],trainers[511],trainers[512],trainers[-1]):
    actual=bytes(f.read('/Dashboards/XBMC4Gamers/trainers/'+item.filename))
    expected=(base/'payload-v3/f/Dashboards/XBMC4Gamers/trainers'/item.filename).read_bytes()
    assert actual==expected
for name in ('XBMC4Gamers','XBMC-Emustation','Avalaunch','EvolutionX'):
    assert bytes(f.read('/Dashboards/'+name+'/default.xbe'))[:4]==b'XBEH'
print('INDEPENDENT_LIBFATX_READ_PASS',len(trainers),'trainers and dashboard executables',flush=True)
