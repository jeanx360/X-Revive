"""Boot a QA copy of a standalone image with ONE SSD, no USB or other HDD.

Only the QA copy receives /debug. QEMU snapshot mode isolates all guest writes.
The production image and its checksum are never modified. Use the serial socket
for checks, and systemctl poweroff inside the VM to finish.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('s', ROOT/'bancada/smoke-image.py')
smoke = importlib.util.module_from_spec(spec); spec.loader.exec_module(smoke)


def main(image):
    image = Path(image).resolve()
    data = json.loads(image.with_suffix('.layout.json').read_text())
    if not data.get('experimental'):
        raise ValueError('somente prototipo standalone')
    folder = ROOT/'bancada/validacao-final'/data['source_sha256'][:8]/'standalone-live'
    folder.mkdir(parents=True, exist_ok=True)
    disk = folder/'ssd.img'
    subprocess.run(['cp','--reflink=auto',str(image),str(disk)], check=True)
    (folder/'debug').touch()
    subprocess.run(['mcopy','-o','-i',str(disk)+'@@'+str(data['system']['offset']),
                    str(folder/'debug'),'::/debug'], check=True)
    firmware = Path('/usr/share/edk2/ovmf')
    shutil.copyfile(firmware/'OVMF_VARS.fd',folder/'OVMF_VARS.fd')
    args = ['qemu-system-x86_64','-name','xrevive-standalone-final','-enable-kvm',
        '-machine','q35','-cpu','host','-smp','4','-m','6144','-snapshot',
        '-drive',f'if=pflash,format=raw,readonly=on,file={firmware}/OVMF_CODE.fd',
        '-drive',f'if=pflash,format=raw,file={folder}/OVMF_VARS.fd',
        '-drive',f'if=none,id=ssd,format=raw,file={disk}',
        '-device','ide-hd,bus=ide.0,drive=ssd,bootindex=1',
        '-device','virtio-vga','-display','none',
        '-audiodev',f'wav,id=som,path={folder}/audio.wav',
        '-device','ich9-intel-hda','-device','hda-output,audiodev=som',
        '-netdev','user,id=net','-device','e1000,netdev=net',
        '-chardev',f'socket,id=ser,path={folder}/serial.sock,server=on,wait=off,logfile={folder}/serial.log',
        '-serial','chardev:ser','-qmp',f'unix:{folder}/vm.qmp,server=on,wait=off',
        '-drive','if=none,id=dvd,media=cdrom','-device','ide-cd,bus=ide.1,drive=dvd']
    (folder/'command.json').write_text(json.dumps(args,indent=2)+'\n')
    with (folder/'qemu.log').open('w') as log:
        process = subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
        print('ONE SSD VM:',process.pid,'serial:',folder/'serial.sock',flush=True)
        try:
            while process.poll() is None:
                time.sleep(1)
        finally:
            if process.poll() is None:
                process.terminate();process.wait(timeout=10)


if __name__ == '__main__':
    main(sys.argv[1])
