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
    parser.add_argument('--usb-gib',type=int,default=16)
    parser.add_argument('--ram-mib',type=int,default=6144)
    parser.add_argument('--ftp-port',type=int,default=2121)
    parser.add_argument('--user-files',type=Path)
    parser.add_argument('--hdd-image',type=Path,help='Clone regular de HDD Xbox para ensaiar LIVE; nunca dispositivo')
    parser.add_argument('--no-hdd',action='store_true',help='LIVE independente: nenhum HDD conectado à VM')
    parser.add_argument('--hdd-usb',action='store_true',help='HDD QA regular conectado pelo barramento USB virtual')
    parser.add_argument('--guard-image',type=Path,help='Disco de dados regular adicional que deve permanecer intocado')
    parser.add_argument('--prepared-usb-image',type=Path,help='Reutilizar somente XREVIVE de outro USB regular QA; todo o sistema vem da IMG candidata')
    parser.add_argument('--xbox-dongle',action='store_true',help='Passagem reversível apenas do adaptador Microsoft 045e:02fe; nunca storage/teclado/mouse')
    parser.add_argument('--efi-override',type=Path,help='EFI regular de QA, apenas para escolher outra entrada do mesmo menu')
    args=parser.parse_args();image=Path(args.image).resolve()
    if not image.is_file():raise ValueError('somente imagem regular')
    if args.usb_gib*1024**3<image.stat().st_size:raise ValueError('USB virtual menor que a IMG')
    folder=Path(args.folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    usb=folder/'installer.img'
    if usb.exists() or (folder/'ssd.img').exists():raise ValueError('Pasta QA já contém discos; use outra pasta')
    subprocess.run(['cp','--reflink=auto',str(image),str(usb)],check=True)
    with usb.open('r+b') as disk:disk.truncate(args.usb_gib*1024**3)
    table=json.loads(subprocess.check_output(['sfdisk','-J',str(usb)],text=True))['partitiontable']
    if args.prepared_usb_image:
        prepared=args.prepared_usb_image.resolve()
        if not prepared.is_file() or prepared.is_block_device():raise ValueError('USB preparado QA exige arquivo regular')
        previous=json.loads(subprocess.check_output(['sfdisk','-J',str(prepared)],text=True))['partitiontable']
        users=next(p for p in table['partitions'] if p['name']=='XREVIVE')
        old=next(p for p in previous['partitions'] if p['name']=='XREVIVE')
        if (old['start'],old['size'])!=(users['start'],users['size']):raise ValueError('Área pessoal QA com geometria diferente')
        # This is our newly created regular QA copy, never a physical disk.
        # Clear only its XREVIVE range, then preserve holes while importing
        # prepared owner files. Avoid writing ten GiB of empty exFAT space.
        subprocess.run(['fallocate','--punch-hole','--keep-size','--offset',str(users['start']*512),
                        '--length',str(users['size']*512),str(usb)],check=True)
        with prepared.open('rb') as src,usb.open('r+b') as dst:
            src.seek(old['start']*512);dst.seek(users['start']*512);remaining=users['size']*512
            while remaining:
                block=src.read(min(8*1024**2,remaining))
                if not block:raise ValueError('USB preparado truncado')
                if block.count(0)==len(block):dst.seek(len(block),1)
                else:dst.write(block)
                remaining-=len(block)
    system=next(p for p in table['partitions'] if p['name']=='SYSTEM')
    (folder/'debug').touch()
    subprocess.run(['mcopy','-o','-i',str(usb)+'@@'+str(system['start']*512),str(folder/'debug'),'::/debug'],check=True)
    if args.efi_override:
        if not args.efi_override.is_file() or args.efi_override.is_block_device():raise ValueError('EFI QA exige arquivo regular')
        subprocess.run(['mcopy','-o','-i',str(usb)+'@@'+str(system['start']*512),str(args.efi_override),'::/EFI/BOOT/BOOTX64.EFI'],check=True)
    ssd=folder/'ssd.img'
    if ssd.exists():raise ValueError('SSD QA já existe; use outra pasta')
    if args.hdd_image:
        if not args.hdd_image.is_file() or args.hdd_image.is_block_device():raise ValueError('HDD QA exige arquivo regular')
        subprocess.run(['cp','--reflink=auto',str(args.hdd_image.resolve()),str(ssd)],check=True)
    else:
        with ssd.open('xb') as f:f.truncate(args.ssd_gib*1024**3)
    (folder/'ssd-before.json').write_text(json.dumps(dict(bytes=ssd.stat().st_size,mtime_ns=ssd.stat().st_mtime_ns)))
    firmware=Path('/usr/share/edk2/ovmf')
    shutil.copyfile(firmware/'OVMF_VARS.fd',folder/'OVMF_VARS.fd')
    options=['qemu-system-x86_64','-name','xrevive-installer-qa','-enable-kvm','-machine','q35',
        '-cpu','host','-smp','4','-m',str(args.ram_mib),
        '-drive',f'if=pflash,format=raw,readonly=on,file={firmware}/OVMF_CODE.fd',
        '-drive',f'if=pflash,format=raw,file={folder}/OVMF_VARS.fd',
        '-device','qemu-xhci,id=xhci','-drive',f'if=none,id=usb,format=raw,file={usb}',
        '-device','usb-storage,bus=xhci.0,drive=usb,bootindex=1',
        '-device','virtio-vga','-display','none',
        '-audiodev',f'wav,id=som,path={folder}/audio.wav','-device','ich9-intel-hda','-device','hda-output,audiodev=som',
        '-netdev',f'user,id=net,hostfwd=tcp:127.0.0.1:{args.ftp_port}-:2121','-device','e1000,netdev=net',
        '-chardev',f'socket,id=ser,path={folder}/serial.sock,server=on,wait=off,logfile={folder}/serial.log',
        '-serial','chardev:ser','-qmp',f'unix:{folder}/vm.qmp,server=on,wait=off',
        '-drive','if=none,id=dvd,media=cdrom','-device','ide-cd,bus=ide.1,drive=dvd']
    if not args.no_hdd:
        options.extend(['-drive',f'if=none,id=ssd,format=raw,file={ssd}',
                        '-device',('usb-storage,bus=xhci.0,drive=ssd,serial=XREVIVE-QA-USB-HDD' if args.hdd_usb else 'ide-hd,bus=ide.0,drive=ssd,serial=XREVIVE-QA-SSD')])
    if args.guard_image:
        if not args.guard_image.is_file() or args.guard_image.is_block_device():raise ValueError('Disco de proteção QA exige arquivo regular')
        guard=folder/'guard.img'
        if guard.exists():raise ValueError('Disco de proteção QA já existe')
        subprocess.run(['cp','--reflink=auto',str(args.guard_image.resolve()),str(guard)],check=True)
        options.extend(['-drive',f'if=none,id=guard,format=raw,file={guard}',
                        '-device','ide-hd,bus=ide.0,drive=guard,serial=XREVIVE-QA-NAO-APAGAR'])
    if args.user_files:
        if not args.user_files.is_dir():raise ValueError('pasta de entrada ausente')
        options.extend(['-virtfs','local,path='+str(args.user_files.resolve())+',mount_tag=userfiles,security_model=none,readonly=on'])
    if args.xbox_dongle:
        options.extend(['-device','usb-host,bus=xhci.0,id=xboxradio,vendorid=0x045e,productid=0x02fe'])
    (folder/'command.json').write_text(json.dumps(options,indent=2))
    with (folder/'qemu.log').open('w') as log:
        process=subprocess.Popen(options,stdout=log,stderr=subprocess.STDOUT)
        (folder/'pid').write_text(str(process.pid))
        print('INSTALLER_VM',process.pid,folder,flush=True)
        try:
            while process.poll() is None:time.sleep(1)
            if process.returncode:
                raise RuntimeError('QEMU saiu com erro; confira '+str(folder/'qemu.log'))
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
