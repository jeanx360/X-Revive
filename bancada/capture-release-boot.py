"""Capture an unmodified image's UEFI boot and R/G feedback in snapshot mode.

Usage: python3 bancada/capture-release-boot.py IMAGE [r|g|normal]
Never attaches a physical HDD or enables a debug shell in the release.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('smoke', ROOT/'bancada/smoke-image.py')
smoke = importlib.util.module_from_spec(spec); spec.loader.exec_module(smoke)


def main(image, key='normal'):
    image = Path(image).resolve()
    metadata = json.loads(image.with_suffix('.json').read_text())
    variant = metadata['variant']
    if key not in ('r', 'g', 'normal'):
        raise ValueError('atalho invalido')
    folder = ROOT/'bancada/validacao-final'/metadata['source_sha256'][:8]/('uefi-'+variant+'-'+key)
    folder.mkdir(parents=True, exist_ok=True)
    firmware = Path('/usr/share/edk2/ovmf')
    shutil.copyfile(firmware/'OVMF_VARS.fd', folder/'OVMF_VARS.fd')
    args = ['qemu-system-x86_64', '-name', 'xrevive-final-'+variant,
        '-enable-kvm', '-machine', 'q35', '-cpu', 'host', '-smp', '4', '-m', '6144', '-snapshot',
        '-drive', f'if=pflash,format=raw,readonly=on,file={firmware}/OVMF_CODE.fd',
        '-drive', f'if=pflash,format=raw,file={folder}/OVMF_VARS.fd',
        '-device', 'virtio-vga', '-display', 'none',
        '-audiodev', f'wav,id=som,path={folder}/audio.wav',
        '-device', 'ich9-intel-hda', '-device', 'hda-output,audiodev=som',
        '-netdev', 'user,id=net', '-device', 'e1000,netdev=net',
        '-qmp', f'unix:{folder}/vm.qmp,server=on,wait=off',
        '-drive', 'if=none,id=dvd,media=cdrom', '-device', 'ide-cd,bus=ide.1,drive=dvd']
    if variant == 'standalone':
        args += ['-drive', f'if=none,id=ssd,format=raw,file={image}',
                 '-device', 'ide-hd,bus=ide.0,drive=ssd,bootindex=1']
    else:
        args += ['-device', 'qemu-xhci,id=xhci',
            '-drive', f'if=none,id=usb,format=raw,file={image}',
            '-device', 'usb-storage,bus=xhci.0,drive=usb,bootindex=1',
            '-drive', f'if=none,id=hdd,format=raw,file={ROOT}/bancada/vm/hdd.img',
            '-device', 'ide-hd,bus=ide.0,drive=hdd']
    (folder/'command.json').write_text(json.dumps(args, indent=2)+'\n')
    with (folder/'qemu.log').open('w') as log:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
        try:
            start = time.monotonic(); frame = 0
            while time.monotonic()-start < 100:
                if process.poll() is not None:
                    raise RuntimeError('QEMU saiu durante boot')
                if not (folder/'vm.qmp').exists():
                    time.sleep(.1); continue
                if key != 'normal':
                    smoke.qmp(folder/'vm.qmp', {'execute':'input-send-event', 'arguments':{'events':[
                        {'type':'key','data':{'down':False,'key':{'type':'qcode','data':key}}},
                        {'type':'key','data':{'down':True,'key':{'type':'qcode','data':key}}}]}})
                elapsed = time.monotonic()-start
                name = folder/('frame-%05d-%06.2f.png' % (frame, elapsed))
                temporary = folder/'capture.ppm'
                smoke.qmp(folder/'vm.qmp', {'execute':'screendump','arguments':{'filename':str(temporary)}})
                with Image.open(temporary) as shot:
                    shot.save(name)
                frame += 1
                if frame % 20 == 0:
                    print(variant, key, 'capturas', frame, 'segundos', round(elapsed), flush=True)
                time.sleep(.35 if elapsed < 65 else 4)
            (folder/'capture.json').write_text(json.dumps(dict(build_id=metadata['build_id'],
                variant=variant, key=key, frames=frame, scope='UEFI original, snapshots, sem GPU fisica'), indent=2)+'\n')
            smoke.qmp(folder/'vm.qmp', {'execute':'system_powerdown'})
            process.wait(timeout=30)
        finally:
            if process.poll() is None:
                process.terminate(); process.wait(timeout=10)
    print('CAPTURE COMPLETE', folder, flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])
