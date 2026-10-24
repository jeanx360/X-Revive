"""Send commands/capture frames only through an existing isolated QA VM socket."""
import argparse
import importlib.util
from pathlib import Path
from PIL import Image

spec=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('smoke-image.py'))
smoke=importlib.util.module_from_spec(spec);spec.loader.exec_module(smoke)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('folder',type=Path)
parser.add_argument('--command',action='append',default=[])
parser.add_argument('--capture')
parser.add_argument('--key',action='append',default=[],choices=('up','down','ret','esc','f1','f10'))
args=parser.parse_args()
for command in args.command:print(smoke.serial(args.folder/'serial.sock',command),flush=True)
for key in args.key:
    smoke.qmp(args.folder/'vm.qmp',{'execute':'human-monitor-command','arguments':{'command-line':'sendkey '+key+' 100'}})
    __import__('time').sleep(.3)
if args.capture:
    ppm=(args.folder/(args.capture+'.ppm')).resolve()
    smoke.qmp(args.folder/'vm.qmp',{'execute':'screendump','arguments':{'filename':str(ppm)}})
    Image.open(ppm).save(ppm.with_suffix('.png'))
