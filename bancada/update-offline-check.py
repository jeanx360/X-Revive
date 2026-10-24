"""Installed updated Xemu must boot while its update channel is unavailable."""
import importlib.util,sys,time
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
f=Path(sys.argv[1]);end=time.monotonic()+240
while not (f/'vm.qmp').exists():time.sleep(.2)
while time.monotonic()<end:
 raw=m.serial(f/'serial.sock',"cat /run/xrevive-update/notice.json; cat /run/xrevive-update/choice.json; cat /var/cache/console/updates/state.json; systemctl is-active console.service")
 print(raw,flush=True)
 if '0.8.139-xrevive-smc2' in raw and '"available":false' in raw and '"pending":null' in raw and 'active\r' in raw:
  (f/'offline-persistence.txt').write_text(raw);time.sleep(5)
  ppm=(f/'offline-updated-xemu.ppm').resolve();m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))
  print('UPDATED_XEMU_PERSISTS_WITH_CHANNEL_UNAVAILABLE_PASS',flush=True);break
 time.sleep(2)
else:raise TimeoutError('offline persistence')
print(m.serial(f/'serial.sock','systemctl poweroff'),flush=True)
