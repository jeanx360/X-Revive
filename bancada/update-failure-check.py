"""Confirm a valid local revision with A; kill its first two launches in QEMU."""
import importlib.util,json,time,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
f=Path(sys.argv[1])
def command(c):
 raw=m.serial(f/'serial.sock',c);print(raw,flush=True);return raw
command("python3 -c \"from urllib.request import urlretrieve;urlretrieve('http://10.0.2.2:8866/early-failure.py','/run/early-failure.py');urlretrieve('http://10.0.2.2:8866/installer-pad.py','/run/installer-pad.py')\"")
command('python3 /run/early-failure.py >/run/qa-early-failure.log 2>&1 &')
command('python3 /run/installer-pad.py >/run/pad.log 2>&1 &');time.sleep(2)
command('echo A >/run/xrevive-pad-command')
end=time.monotonic()+180
while time.monotonic()<end:
 raw=command('cat /run/qa-early-failure.log; cat /run/xrevive-update/choice.json 2>/dev/null')
 if 'AUTOMATIC_LAST_GOOD_RECOVERY_PASS' in raw:
  (f/'automatic-recovery.txt').write_text(raw);print('AUTOMATIC_TWO_FAILURES_RECOVERY_PASS',flush=True);break
 if 'Traceback' in raw:raise RuntimeError(raw)
 time.sleep(2)
else:raise TimeoutError('automatic recovery')
