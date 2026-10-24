"""QEMU-only session failure injection, covering Wayland/X11 fallback as a unit."""
from pathlib import Path
import importlib.util,sys,time
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
f=Path(sys.argv[1])
def command(c):
 raw=m.serial(f/'serial.sock',c);print(raw,flush=True);return raw
m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey ret 100'}})
end=time.monotonic()+240
while time.monotonic()<end:
 raw=command("systemctl is-active --quiet console.service && test ! -f /run/console/installer && printf 'FAILURE_SETUP_%s\\n' READY")
 if 'FAILURE_SETUP_READY' in raw:break
 time.sleep(2)
else:raise TimeoutError('console')
command('systemctl stop console.service')
command("python3 -c \"from urllib.request import urlretrieve;urlretrieve('http://10.0.2.2:8866/rearm-observation.py','/run/rearm.py');urlretrieve('http://10.0.2.2:8866/early-failure.py','/run/early-failure.py')\"; python3 /run/rearm.py")
command('python3 /run/early-failure.py >/run/qa-session-failure.log 2>&1 & systemctl start console.service')
end=time.monotonic()+180
while time.monotonic()<end:
 raw=command('cat /run/qa-session-failure.log; cat /run/xrevive-update/choice.json')
 if 'AUTOMATIC_LAST_GOOD_RECOVERY_PASS' in raw:
  (f/'automatic-recovery-session.txt').write_text(raw);print('AUTOMATIC_TWO_SESSION_FAILURES_RECOVERY_PASS',flush=True);break
 if 'Traceback' in raw:raise RuntimeError(raw)
 time.sleep(2)
else:raise TimeoutError('automatic recovery')
