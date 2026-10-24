"""Capture the SSD boot notice and inspect the real selected Xemu."""
import importlib.util,json,time,sys
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
f=Path(sys.argv[1]);deadline=time.monotonic()+300
while not (f/'vm.qmp').exists():time.sleep(.2)
for index in range(30):
 ppm=(f/('notice-%02d.ppm'%index)).resolve()
 m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}})
 Image.open(ppm).save(ppm.with_suffix('.png'));time.sleep(1)
while time.monotonic()<deadline:
 raw=m.serial(f/'serial.sock',"cat /run/xrevive-update/notice.json; cat /run/xrevive-update/choice.json; systemctl is-active console.service console-update-health.service")
 print(raw,flush=True)
 if '0.8.138-xrevive-smc2' in raw and '"available":true' in raw:
  (f/'normal-boot.txt').write_text(raw);print('NORMAL_BOOT_CACHED_SIGNED_OFFER_PASS',flush=True);break
 time.sleep(2)
else:raise TimeoutError('normal boot update notice')
