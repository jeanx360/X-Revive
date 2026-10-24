"""Real GUI error/cancel: temporarily withhold the requested signed package."""
import importlib.util,json,os,sys,time,shlex
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
f=Path(sys.argv[1]);root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'cartucho/cache/update-channel/latest.json').read_text())['manifest']
package=root/'cartucho/cache/update-channel'/('xemu-'+manifest['sha256']+'.tar.gz')
saved=root/'cartucho/cache'/('withheld-'+package.name)
assert package.is_file() and not saved.exists()
os.rename(package,saved)
try:
 m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey ret 100'}})
 end=time.monotonic()+60
 while time.monotonic()<end:
  c="python3 -c "+shlex.quote('import socket;s=socket.socket(socket.AF_UNIX);s.connect(\'/run/xrevive-update/control.sock\');s.sendall(b\'{"action":"status"}\\n\');print(s.makefile().readline())')
  raw=m.serial(f/'serial.sock',c);print(raw,flush=True)
  if '"phase": "error"' in raw:
   assert 'HTTP Error 404' in raw
   check=m.serial(f/'serial.sock',"test ! -f /var/cache/console/updates/state.json && printf 'DOWNLOAD_ERROR_NO_ACTIVATION_%s\\n' PASS")
   print(check,flush=True);assert 'DOWNLOAD_ERROR_NO_ACTIVATION_PASS' in check
   ppm=(f/'download-error.ppm').resolve();m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))
   break
  time.sleep(1)
 else:raise TimeoutError('download error')
finally:os.rename(saved,package)
m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey esc 100'}})
time.sleep(5)
raw=m.serial(f/'serial.sock','cat /run/xrevive-update/choice.json');print(raw,flush=True)
assert '0.8.138-xrevive-smc2' in raw
print('REAL_DOWNLOAD_ERROR_AND_CONTINUE_OLD_VERSION_PASS',flush=True)
