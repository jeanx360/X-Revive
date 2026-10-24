"""Drive the real update UI in an existing isolated QEMU VM; RPC reads only."""
import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import time
from PIL import Image

s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path)
p.add_argument('action',choices=['open','cancel','apply','baseline','verify','status']);a=p.parse_args();f=a.folder


def command(c):
 result=m.serial(f/'serial.sock',c);print(result,flush=True);return result


def key(name):
 m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey '+name+(' 1000' if name=='u' else ' 100')}})


def frame(name):
 ppm=(f/(name+'.ppm')).resolve();m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}})
 Image.open(ppm).save(ppm.with_suffix('.png'))


def status():
 code="import socket;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-update/control.sock');s.sendall(b'{\"action\":\"status\"}\\n');print('RPC_RESULT',s.makefile().readline())"
 raw=command('python3 -c '+shlex.quote(code))
 for line in raw.splitlines():
  if line.startswith('RPC_RESULT {'):return json.loads(line[len('RPC_RESULT '):])['data']
 return {}


def check_invariants(mode):
 command("python3 -c \"from urllib.request import urlretrieve;urlretrieve('http://10.0.2.2:8866/update-invariants.py','/run/update-invariants.py')\"")
 raw=command('python3 /run/update-invariants.py '+mode)
 # Hashing all of SYSTEM can outlast serial's short read; wait on a result file instead.
 return raw


if a.action=='open':
 deadline=time.monotonic()+240
 while not (f/'vm.qmp').exists():time.sleep(.2)
 while time.monotonic()<deadline:
  key('u')
  raw=command("systemctl is-active --quiet console-update-ui.service && printf 'UPDATE_UI_%s\\n' READY")
  frame('update-boot')
  if 'UPDATE_UI_READY' in raw:
   time.sleep(3);frame('update-notes');result=status();assert result['release']['version']=='0.8.139-xrevive-smc2'
   (f/'update-offer.json').write_text(json.dumps(result,indent=2));print('UPDATE_U_NOTES_PASS',flush=True);break
  time.sleep(.5)
 else:raise TimeoutError('U update UI')
elif a.action=='status':print(json.dumps(status(),indent=2))
elif a.action=='cancel':
 assert status()['phase']=='ready';key('esc');time.sleep(5)
 raw=command("cat /run/xrevive-update/choice.json; test ! -f /var/cache/console/updates/state.json && printf 'UPDATE_CANCEL_%s\\n' PASS")
 assert 'UPDATE_CANCEL_PASS' in raw;frame('cancel-existing-xemu');print('UPDATE_CANCEL_PASS',flush=True)
elif a.action=='apply':
 result=status();assert result['release']['version']=='0.8.139-xrevive-smc2'
 command("python3 -c \"from urllib.request import urlretrieve;urlretrieve('http://10.0.2.2:8866/installer-pad.py','/run/installer-pad.py')\"; python3 /run/installer-pad.py >/run/pad.log 2>&1 &")
 time.sleep(2);command('echo A >/run/xrevive-pad-command')
 deadline=time.monotonic()+150;index=0
 while time.monotonic()<deadline:
  frame('update-progress-%03d'%index);index+=1
  raw=command("cat /run/xrevive-update/choice.json 2>/dev/null; cat /var/cache/console/updates/state.json 2>/dev/null; pgrep -a -u console -f '^/var/cache/console/updates/versions/'")
  if '0.8.139-xrevive-smc2' in raw and '"pending":null' in raw:
   frame('updated-xbox');(f/'update-health.txt').write_text(raw)
   print('UPDATE_CONTROLLER_A_DOWNLOAD_ACTIVATE_QMP_HEALTH_PASS',flush=True);break
  time.sleep(4)
 else:raise TimeoutError('updated Xemu health')
elif a.action in ('baseline','verify'):
 mode='before' if a.action=='baseline' else 'after'
 command("python3 -c \"from urllib.request import urlretrieve;urlretrieve('http://10.0.2.2:8866/update-invariants.py','/run/update-invariants.py')\"")
 command('python3 /run/update-invariants.py '+mode+' >/run/update-invariants-result.log 2>&1 &')
 deadline=time.monotonic()+150
 while time.monotonic()<deadline:
  raw=command('cat /run/update-invariants-result.log')
  if 'UPDATER_BASELINE' in raw or 'UPDATER_SYSTEM_FATX_FIRMWARE_PREFERENCES_PRESERVED' in raw:
   (f/('invariants-'+mode+'.txt')).write_text(raw);print('INVARIANTS_'+mode.upper()+'_PASS',flush=True);break
  if 'Traceback' in raw:raise RuntimeError(raw)
  time.sleep(2)
 else:raise TimeoutError('invariants')
