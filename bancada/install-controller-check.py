"""Controller-only UI install into the regular SSD file of installer-vm.py.

No installer RPC mutations are used. Status RPC is read-only; all navigation
and both destructive confirmations use the virtual Xbox controller.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import time
from PIL import Image

spec=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--monitor-only',action='store_true');p.add_argument('--source',choices=('online','offline'));p.add_argument('--check-generic-video',action='store_true');a=p.parse_args();f=a.folder
assert (f/'ssd.img').is_file()


def command(c):
    result=m.serial(f/'serial.sock',c);print(result,flush=True);return result


def pad(c):command('echo '+c+' >/run/xrevive-pad-command')


def frame(name):
    ppm=(f/(name+'.ppm')).resolve()
    m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}})
    Image.open(ppm).save(ppm.with_suffix('.png'))


if not a.monitor_only:
    deadline=time.monotonic()+240
    boot_frame=0
    while time.monotonic()<deadline:
        frame('boot-%03d'%boot_frame);boot_frame+=1
        ready=command("systemctl is-active --quiet console-installer.service console-installer-worker.service && printf 'INSTALLER_UI_%s\\n' READY")
        if 'INSTALLER_UI_READY' in ready:break
        time.sleep(2)
    else:raise TimeoutError('installer UI not ready')
    if a.check_generic_video:
        result=command("readlink /etc/modules-load.d/nvidia.conf; if dmesg | grep -q NVRM; then printf 'GENERIC_VIDEO_%s\\n' FAIL; else printf 'GENERIC_VIDEO_%s\\n' PASS; fi")
        assert 'GENERIC_VIDEO_PASS' in result and '/dev/null' in result
    command("python3 -c \"from urllib.request import urlretrieve;urlretrieve('http://10.0.2.2:8866/installer-pad.py','/run/installer-pad.py')\"; python3 /run/installer-pad.py >/run/pad.log 2>&1 &")
    time.sleep(2);frame('welcome-controller')
    pad('A')
    if a.source:
        if a.source=='offline':pad('down')
        pad('A')
        if a.source=='offline':pad('A')
        request="python3 -c \"import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall(b'{\\\"action\\\":\\\"status\\\"}\\n');print(s.makefile().readline())\""
        deadline=time.monotonic()+5400
        while time.monotonic()<deadline:
            raw=command(request)
            matches=re.findall(r'\{"ok": true, "data": .*\}',raw)
            if matches:
                status=json.loads(matches[-1])['data']
                (f/'prepare-status.json').write_text(json.dumps(status,indent=2))
                if status.get('error'):frame('prepare-error');raise RuntimeError(status['error'])
                if not status['busy'] and (status.get('result') or {}).get('ready'):break
            time.sleep(10)
        else:raise TimeoutError('package preparation')
    pad('A');time.sleep(10);frame('confirm1-controller')
    # Cancel works without any target writes, then select the same disk again.
    before=(f/'ssd.img').stat().st_mtime_ns
    pad('B');pad('A');time.sleep(10);frame('confirm1-after-cancel')
    assert (f/'ssd.img').stat().st_mtime_ns==before
    pad('hold-confirm');time.sleep(4);frame('confirm2-held-controller')
    assert (f/'ssd.img').stat().st_mtime_ns==before,'held combo confirmed twice'
    print('NO_WRITE_BEFORE_SECOND_CONFIRM',before,flush=True)
    pad('release');time.sleep(1);pad('confirm');time.sleep(4);frame('installing-controller')
# Read-only status, never plan/confirm/install RPC.
request="python3 -c \"import socket,json;s=socket.socket(socket.AF_UNIX);s.connect('/run/xrevive-installer/control.sock');s.sendall(b'{\\\"action\\\":\\\"status\\\"}\\n');print(s.makefile().readline())\""
deadline=time.monotonic()+2400
while True:
    raw=command(request)
    candidates=re.findall(r'\{"ok": true, "data": .*\}',raw)
    if candidates:
        status=json.loads(candidates[-1])['data']
        (f/'install-status.json').write_text(json.dumps(status,indent=2))
        if not status['busy']:
            if status.get('error'):raise RuntimeError(status['error'])
            if (status.get('result') or {}).get('verified'):
                frame('completed-controller');print('CONTROLLER_INSTALL_PASS',status['result'],flush=True);break
    if time.monotonic()>deadline:raise TimeoutError('installation did not finish')
    time.sleep(15)
