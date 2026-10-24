"""Capture an isolated installed VM's boot and prove the actual firmware hash."""
import argparse
import importlib.util
from pathlib import Path
import time
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();f=a.folder.resolve()
for i in range(180):
 try:
  ppm=f/('boot-%03d.ppm'%i);m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))
 except (OSError,RuntimeError):pass
 if i%8==0 and (f/'serial.sock').exists():
  text=m.serial(f/'serial.sock',"systemctl is-active console.service; sha256sum /console/firmware/xbox/bios.bin; cat /proc/asound/card0/pcm0p/sub0/status 2>/dev/null | head -4")
  with (f/'boot-proof.log').open('a') as out:out.write(text)
 time.sleep(.7)
