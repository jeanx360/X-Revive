"""Capture the real UEFI/GRUB boot of a release image, with snapshot disks."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('smoke', ROOT/'bancada/smoke-image.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def main(variant):
    if variant not in ('universal', 'nvidia'):
        raise ValueError('variante invalida')
    folder = ROOT/'bancada/validacao-boot'/('uefi-'+variant)
    folder.mkdir(parents=True, exist_ok=True)
    firmware = Path('/usr/share/edk2/ovmf')
    shutil.copyfile(firmware/'OVMF_VARS.fd', folder/'OVMF_VARS.fd')
    args = ['qemu-system-x86_64', '-name', 'xrevive-uefi-'+variant,
        '-enable-kvm', '-machine', 'q35', '-cpu', 'host', '-smp', '4', '-m', '6144', '-snapshot',
        '-drive', f'if=pflash,format=raw,readonly=on,file={firmware}/OVMF_CODE.fd',
        '-drive', f'if=pflash,format=raw,file={folder}/OVMF_VARS.fd',
        '-device', 'qemu-xhci,id=xhci',
        '-drive', f'if=none,id=usb,format=raw,file={ROOT}/cartucho/out/console-xbox-{variant}.img',
        '-device', 'usb-storage,bus=xhci.0,drive=usb,bootindex=1',
        '-drive', f'if=none,id=hdd,format=raw,file={ROOT}/bancada/vm/hdd.img',
        '-device', 'ide-hd,bus=ide.0,drive=hdd', '-device', 'virtio-vga', '-display', 'none',
        '-audiodev', f'wav,id=som,path={folder}/audio.wav',
        '-device', 'ich9-intel-hda', '-device', 'hda-output,audiodev=som',
        '-netdev', 'user,id=net', '-device', 'e1000,netdev=net',
        '-qmp', f'unix:{folder}/vm.qmp,server=on,wait=off',
        '-drive', 'if=none,id=dvd,media=cdrom', '-device', 'ide-cd,bus=ide.1,drive=dvd']
    (folder/'command.json').write_text(json.dumps(args, indent=2)+'\n')
    with (folder/'qemu.log').open('w') as log:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
        try:
            start = time.monotonic()
            for second in (2, 6, 10, 14, 18, 25, 40, 60, 90):
                time.sleep(max(0, start+second-time.monotonic()))
                if process.poll() is not None:
                    raise RuntimeError('QEMU saiu durante boot UEFI')
                smoke.qmp(folder/'vm.qmp', {'execute': 'screendump', 'arguments': {
                    'filename': str(folder/f'boot-{second:03}.ppm')}})
                print('Captura UEFI:', variant, second, flush=True)
            smoke.qmp(folder/'vm.qmp', {'execute': 'system_powerdown'})
            process.wait(timeout=30)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


if __name__ == '__main__':
    main(sys.argv[1])
