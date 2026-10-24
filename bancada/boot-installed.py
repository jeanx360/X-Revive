"""Boot a QA-installed regular SSD image alone; never attaches a USB or device."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cartucho/overlay/usr/local/lib/console'))
import installer


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ssd');parser.add_argument('folder')
    args=parser.parse_args();ssd=Path(args.ssd).resolve();folder=Path(args.folder).resolve()
    if not ssd.is_file():raise ValueError('somente SSD virtual regular')
    data=installer.installed(ssd)
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'layout.json').write_text(json.dumps(data,indent=2))
    with ssd.open('rb') as f:
        f.seek(data['system']['offset']);digest=hashlib.sha256(f.read(16*1024**2)).hexdigest()
    (folder/'system-before.sha256').write_text(digest)
    firmware=Path('/usr/share/edk2/ovmf')
    shutil.copyfile(firmware/'OVMF_VARS.fd',folder/'OVMF_VARS.fd')
    options=['qemu-system-x86_64','-name','xrevive-installed-qa','-enable-kvm','-machine','q35',
        '-cpu','host','-smp','4','-m','6144',
        '-drive',f'if=pflash,format=raw,readonly=on,file={firmware}/OVMF_CODE.fd',
        '-drive',f'if=pflash,format=raw,file={folder}/OVMF_VARS.fd',
        '-drive',f'if=none,id=ssd,format=raw,file={ssd}',
        '-device','ide-hd,bus=ide.0,drive=ssd,serial=XREVIVE-QA-SSD,bootindex=1',
        '-device','virtio-vga','-display','none',
        '-audiodev',f'wav,id=som,path={folder}/audio.wav','-device','ich9-intel-hda','-device','hda-output,audiodev=som',
        '-netdev','user,id=net,hostfwd=tcp:127.0.0.1:2121-:2121','-device','e1000,netdev=net',
        '-chardev',f'socket,id=ser,path={folder}/serial.sock,server=on,wait=off,logfile={folder}/serial.log',
        '-serial','chardev:ser','-qmp',f'unix:{folder}/vm.qmp,server=on,wait=off',
        '-drive','if=none,id=dvd,media=cdrom','-device','ide-cd,bus=ide.1,drive=dvd']
    (folder/'command.json').write_text(json.dumps(options,indent=2))
    with (folder/'qemu.log').open('w') as log:
        process=subprocess.Popen(options,stdout=log,stderr=subprocess.STDOUT)
        (folder/'pid').write_text(str(process.pid))
        print('INSTALLED_SSD_ONLY_VM',process.pid,folder,flush=True)
        try:
            while process.poll() is None:time.sleep(1)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
