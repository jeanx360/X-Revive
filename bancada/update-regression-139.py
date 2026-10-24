"""Boot the QA-selected UnleashX, then test actual updated Xemu FTP and tray."""
import importlib.util,time,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
f=Path(sys.argv[1])
if '--no-reboot' not in sys.argv:m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey ret 100'}})
end=time.monotonic()+240
while time.monotonic()<end:
 raw=m.serial(f/'serial.sock',"systemctl is-active --quiet console.service && test ! -f /run/console/installer && printf 'UPDATE139_%s\\n' READY")
 print(raw,flush=True)
 if 'UPDATE139_READY' in raw:break
 time.sleep(3)
else:raise TimeoutError('normal installed boot')
print(m.serial(f/'serial.sock',"pkill -TERM -f '^python3 /run/postinstall-regression.py$'; systemctl stop console.service"),flush=True)
code="from pathlib import Path;p=Path('/run/console/xemu.toml');s=p.read_text();s=s.replace(\"backend = 'pcap'\",\"backend = 'nat'\");p.write_text(s)"
import shlex
print(m.serial(f/'serial.sock','python3 -c '+shlex.quote(code)),flush=True)
print(m.serial(f/'serial.sock','systemctl start console.service'),flush=True)
print(m.serial(f/'serial.sock',"python3 -c \"from urllib.request import urlretrieve;urlretrieve('http://10.0.2.2:8866/postinstall-regression.py','/run/postinstall-regression.py')\"; python3 /run/postinstall-regression.py >/run/qa-regression.log 2>&1 &"),flush=True)
end=time.monotonic()+300
while time.monotonic()<end:
 raw=m.serial(f/'serial.sock','cat /run/qa-regression.log');print(raw,flush=True)
 if 'POSTINSTALL_REGRESSION_PASS' in raw:
  (f/'regression-139.txt').write_text(raw);print('UPDATED_139_FTP_TRAY_SYSTEM_PASS',flush=True);break
 if 'Traceback' in raw:raise RuntimeError(raw)
 time.sleep(3)
else:raise TimeoutError('updated 139 FTP/tray')
