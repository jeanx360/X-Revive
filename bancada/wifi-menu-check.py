"""UI + real mac80211_hwsim WPA2/DHCP/HTTPS in a disposable QEMU VM."""
import argparse,importlib.util,json,re,shlex,time
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();f=a.folder.resolve()
def cmd(code):
 try:result=m.serial(f/'serial.sock',code)
 except (FileNotFoundError,ConnectionRefusedError):return ''
 with (f/'wifi-commands.log').open('a') as out:out.write(result)
 return result
def wait(code,token,timeout=180):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  result=cmd(code)
  if token in result:return result
  time.sleep(2)
 raise TimeoutError(token)
def rpc(action):
 code="import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall("+repr((json.dumps(dict(action=action))+'\n').encode())+");print('WIFI_RESULT='+s.makefile().readline())"
 values=re.findall(r'WIFI_RESULT=(\{[^\r\n]+\})',cmd('python3 -c '+shlex.quote(code)))
 if not values:return {}
 result=json.loads(values[-1]);assert result['ok'],result
 return result['data']
def idle(timeout=65,error=False):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  result=rpc('status')
  if result and not result['busy']:
   if not error:assert not result.get('error'),result
   return result
  time.sleep(1)
 raise TimeoutError('wifi job')
def key(k):
 m.qmp(f/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey '+k+' 120'}});time.sleep(.4)
def pad(k):cmd('echo '+k+' > /run/xrevive-pad-command');time.sleep(.25)
def frame(name):
 ppm=f/(name+'.ppm');m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))
wait("grep -q 'UI: janela pronta' /run/console/interface.log && printf 'UI_%s\\n' READY",'UI_READY')
cmd('mkdir -p /mnt/input; mount -t 9p -o trans=virtio,version=9p2000.L,ro userfiles /mnt/input')
cmd('setsid sh /mnt/input/wifi-setup.sh > /run/wifi-setup.log 2>&1 < /dev/null &')
wait('tail -3 /run/wifi-setup.log','WIFI_QA_READY',240)
hello=rpc('hello')
for _ in range(1 if hello.get('safe_live') else 2 if hello.get('installed') else 4):key('down')
key('ret');state=idle()['result'];refreshes=0
while not state['networks'] and refreshes<3:
 time.sleep(2);key('ret');state=idle()['result'];refreshes+=1
assert state['networks'],state;frame('wifi-networks')
key('ret')
for k in '12345678':key(k)
frame('physical-password-masked');key('ret');state=idle()['result'];assert state['connected'];frame('physical-connected')
# Disconnect, submit a wrong password, then recover through controller only.
key('down');key('down');key('ret');assert not idle()['result']['connected']
key('ret')
for k in '11111111':key(k)
key('ret');bad=idle(error=True);assert bad.get('error') and '11111111' not in bad['error'];frame('wrong-password')
cmd('python3 /mnt/input/installer-pad.py > /run/wifi-pad.log 2>&1 < /dev/null &')
wait('cat /run/wifi-pad.log','VIRTUAL_XBOX_PAD_READY',30)
pad('A')
for index in range(8):
 if index:pad('right')
 pad('A')
pad('X');pad('A');frame('controller-password-masked')
for i in range(4):pad('down')
pad('left');pad('A');state=idle()['result'];assert state['connected'];frame('controller-connected')
cmd('python3 /mnt/input/wifi-proof.py > /run/wifi-proof.log 2>&1 < /dev/null &')
proof=wait('cat /run/wifi-proof.log','WIFI_PROOF_PASS',60)
(f/'wifi-proof-result.log').write_text(proof)
(f/'wifi-state.json').write_text(json.dumps(dict(state=state,initial_refreshes=refreshes),indent=2))
print('WIFI_GUI_KEYBOARD_CONTROLLER_WPA2_DHCP_HTTPS_PASS',flush=True)
# Leave the UI connected at welcome so media tests can continue in the same VM.
pad('B');cmd('pkill -f "^python3 /mnt/input/installer-pad.py$"')
