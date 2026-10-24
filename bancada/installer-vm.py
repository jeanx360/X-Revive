"""Boot the installer against a disposable regular SSD image, never a device.

QA USB copy alone receives /debug. The production image remains unchanged.
The SSD is intentionally persistent so a later VM can boot it without USB.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image');parser.add_argument('--folder',default='bancada/validacao-estagio2')
    parser.add_argument('--ssd-gib',type=int,default=64)
    parser.add_argument('--ftp-port',type=int,default=2121)
    parser.add_argument('--user-files',type=Path)
    args=parser.parse_args();image=Path(args.image).resolve()
    if not image.is_file():raise ValueError('somente imagem regular')
    folder=Path(args.folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    usb=folder/'installer.img'
    subprocess.run(['cp','--reflink=auto',str(image),str(usb)],check=True)
    table=json.loads(subprocess.check_output(['sfdisk','-J',str(usb)],text=True))['partitiontable']
    system=next(p for p in table['partitions'] if p['name']=='SYSTEM')
    (folder/'debug').touch()
    subprocess.run(['mcopy','-o','-i',str(usb)+'@@'+str(system['start']*512),str(folder/'debug'),'::/debug'],check=True)
    ssd=folder/'ssd.img'
    with ssd.open('xb') as f:f.truncate(args.ssd_gib*1024**3)
    firmware=Path('/usr/share/edk2/ovmf')
    shutil.copyfile(firmware/'OVMF_VARS.fd',folder/'OVMF_VARS.fd')
    options=['qemu-system-x86_64','-name','xrevive-installer-qa','-enable-kvm','-machine','q35',
        '-cpu','host','-smp','4','-m','6144',
        '-drive',f'if=pflash,format=raw,readonly=on,file={firmware}/OVMF_CODE.fd',
        '-drive',f'if=pflash,format=raw,file={folder}/OVMF_VARS.fd',
        '-device','qemu-xhci,id=xhci','-drive',f'if=none,id=usb,format=raw,file={usb}',
        '-device','usb-storage,bus=xhci.0,drive=usb,bootindex=1',
        '-drive',f'if=none,id=ssd,format=raw,file={ssd}',
        '-device','ide-hd,bus=ide.0,drive=ssd,serial=XREVIVE-QA-SSD',
        '-device','virtio-vga','-display','none',
        '-audiodev',f'wav,id=som,path={folder}/audio.wav','-device','ich9-intel-hda','-device','hda-output,audiodev=som',
        '-netdev',f'user,id=net,hostfwd=tcp:127.0.0.1:{args.ftp_port}-:2121','-device','e1000,netdev=net',
        '-chardev',f'socket,id=ser,path={folder}/serial.sock,server=on,wait=off,logfile={folder}/serial.log',
        '-serial','chardev:ser','-qmp',f'unix:{folder}/vm.qmp,server=on,wait=off',
        '-drive','if=none,id=dvd,media=cdrom','-device','ide-cd,bus=ide.1,drive=dvd']
    if args.user_files:
        if not args.user_files.is_dir():raise ValueError('pasta de entrada ausente')
        options.extend(['-virtfs','local,path='+str(args.user_files.resolve())+',mount_tag=userfiles,security_model=none,readonly=on'])
    (folder/'command.json').write_text(json.dumps(options,indent=2))
    with (folder/'qemu.log').open('w') as log:
        process=subprocess.Popen(options,stdout=log,stderr=subprocess.STDOUT)
        (folder/'pid').write_text(str(process.pid))
        print('INSTALLER_VM',process.pid,folder,flush=True)
        try:
            while process.poll() is None:time.sleep(1)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
