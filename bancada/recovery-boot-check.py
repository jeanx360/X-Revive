"""Request a clean VM reboot and verify R reaches the installed maintenance UI."""
import argparse
import importlib.util
from pathlib import Path
import time
from PIL import Image

spec=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();f=a.folder
print(m.serial(f/'serial.sock','systemctl reboot'),flush=True)
deadline=time.monotonic()+240
index=0
while time.monotonic()<deadline:
    for pressed in (False,True):
        m.qmp(f/'vm.qmp',{'execute':'input-send-event','arguments':{'events':[
            {'type':'key','data':{'down':pressed,'key':{'type':'qcode','data':'r'}}}]}})
    ppm=(f/('recovery-%03d.ppm'%index)).resolve()
    m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}})
    result=m.serial(f/'serial.sock',"systemctl is-active --quiet console-installer.service console-installer-worker.service && test -f /run/xrevive-standalone/state.json && printf 'RECOVERY_%s\\n' PASS")
    print(result,flush=True)
    if 'RECOVERY_PASS' in result:
        m.qmp(f/'vm.qmp',{'execute':'input-send-event','arguments':{'events':[
            {'type':'key','data':{'down':False,'key':{'type':'qcode','data':'r'}}}]}})
        time.sleep(3)
        final=(f/'recovery-ready.ppm').resolve()
        m.qmp(f/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(final)}})
        Image.open(final).save(final.with_suffix('.png'))
        print('R_INSTALLED_MAINTENANCE_PASS',flush=True);break
    index+=1;time.sleep(2)
else:raise TimeoutError('R did not reach maintenance')
