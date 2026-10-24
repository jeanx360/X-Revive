"""Capture alternative dashboards on an already installed isolated QA VM.

Requires the VM-only select-dash helper. Never runs against physical disks.
Frames document startup only, not a full functional test of every application.
"""
import argparse
import importlib.util
from pathlib import Path
import time
from PIL import Image

spec=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--seconds',type=int,default=100)
a=p.parse_args()
items=[('Avalaunch','avalaunch'),('EvolutionX','evolutionx'),
 ('Microsoft Dashboard 5960','microsoft'),('User Interface X','uix'),
 ('UnleashX Network Patched','unleashx-network'),('XBMC-Emustation','emustation'),
 ('XBMC4Xbox','xbmc4xbox'),('XBMC4Gamers','gamers')]
for name,slug in items:
    print('START',name,flush=True)
    print(m.serial(a.folder/'serial.sock',"python3 /run/select-dash.py '"+name+"' >/run/dash-select.log 2>&1 &"),flush=True)
    time.sleep(a.seconds)
    ppm=(a.folder/('matrix-'+slug+'.ppm')).resolve()
    m.qmp(a.folder/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}})
    Image.open(ppm).save(ppm.with_suffix('.png'))
    print(m.serial(a.folder/'serial.sock','cat /run/dash-select.log'),flush=True)
    print('CAPTURED',name,flush=True)
