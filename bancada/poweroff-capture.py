"""Capture a clean Linux shutdown of an isolated VM, without changing services."""
import argparse
import importlib.util
from pathlib import Path
import time
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--watch',action='store_true');a=p.parse_args();f=a.folder
if not a.watch:print(m.serial(f/'serial.sock','(sleep 3; systemctl poweroff) >/run/qa-poweroff.log 2>&1 &'),flush=True)
for i in range(100):
    try:
        ppm=(f/('poweroff-%03d.ppm'%i)).resolve()
        m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}})
        Image.open(ppm).save(ppm.with_suffix('.png'))
    except (OSError,ValueError):print('VM_OFF',i,flush=True);break
    time.sleep(.3)
