"""Read-only boot checks for the isolated SSD-only VM; no runtime overrides."""
import argparse,importlib.util,time
from pathlib import Path
from PIL import Image
s=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();f=a.folder

def frame(name):
 ppm=(f/(name+'.ppm')).resolve();m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}});Image.open(ppm).save(ppm.with_suffix('.png'))

def cmd(c):
 r=m.serial(f/'serial.sock',c);print(r,flush=True);return r

deadline=time.monotonic()+240;index=0
while time.monotonic()<deadline:
 frame('cold-boot-%03d'%index);index+=1
 raw=cmd("systemctl is-active --quiet console.service console-prepare.service && test ! -f /run/console/installer && printf 'SSD_ONLY_%s\\n' PASS")
 if 'SSD_ONLY_PASS' in raw:break
 time.sleep(3)
else:raise TimeoutError('installed console services')
raw=cmd("readlink /etc/modules-load.d/nvidia.conf; if dmesg | grep -q NVRM; then printf 'SSD_VIDEO_%s\\n' FAIL; else printf 'SSD_VIDEO_%s\\n' PASS; fi")
assert 'SSD_VIDEO_PASS' in raw and '/dev/null' in raw
for i in range(10):
 time.sleep(10);frame('xbox-startup-%02d'%i)
frame('dashboard-factory')
raw=cmd('sha256sum /opt/xemu/usr/bin/xemu; cat /run/console/bootanim.log; cat /proc/asound/card0/pcm0p/sub0/status')
assert '892784091cc4263ad3449beef70f3fb17b431cc896498069f4df8f489d233034' in raw
assert 'animacao: ja conferida' in raw or 'animacao: pronta' in raw
assert 'RUNNING' in raw
print('SSD_ONLY_FACTORY_BOOT_SERVICES_VIDEO_AUDIO_BINARY_PASS',flush=True)
