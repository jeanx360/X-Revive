"""X-Revive installation engine. Physical writes require a freshly checked plan.

The GUI cannot pass shell commands, offsets or arbitrary paths to the worker.
QA can use regular image files explicitly through this Python API.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import tempfile

import fatx
import standalone as layout

MIB=1024**2
GIB=1024**3


def command(*args):
    return subprocess.check_output(args,text=True).strip()


def info(path, qa=False, allow_busy=False):
    path=Path(path).resolve();st=path.stat()
    if qa:
        if not stat.S_ISREG(st.st_mode):raise ValueError('QA aceita somente arquivo regular')
        size=st.st_size;serial='QA';model=path.name;device_id=[st.st_dev,st.st_ino]
    else:
        if not stat.S_ISBLK(st.st_mode):raise ValueError('destino não é disco de bloco')
        row=json.loads(command('lsblk','-J','-b','-d','-o','PATH,TYPE,SIZE,MODEL,SERIAL,RO,LOG-SEC',str(path)))['blockdevices'][0]
        if row['type']!='disk' or (row['ro'] and not allow_busy) or row['log-sec']!=512:
            raise ValueError('disco somente leitura, não inteiro ou sem setores de 512 bytes')
        size=int(row['size']);serial=row['serial'] or '';model=(row['model'] or '').strip()
        device_id=[os.major(st.st_rdev),os.minor(st.st_rdev)]
        # NAME requests lsblk's hierarchy; otherwise children may be flattened
        # and a mounted partition would be missed when checking its parent.
        rows=json.loads(command('lsblk','-J','-o','NAME,PATH,MOUNTPOINTS',str(path)))['blockdevices']
        def busy(node):
            holders=Path('/sys/class/block',Path(node['path']).name,'holders')
            return (any(node.get('mountpoints') or []) or
                    (holders.exists() and any(holders.iterdir())) or
                    any(busy(c) for c in node.get('children',[])))
        if not allow_busy and any(busy(r) for r in rows):raise ValueError('disco contém partição montada')
        if not allow_busy and list(Path('/sys/class/block',path.name,'holders').iterdir()):raise ValueError('disco em uso por outro dispositivo')
        if not allow_busy and any(str(path) in line for line in Path('/proc/swaps').read_text().splitlines()[1:]):
            raise ValueError('disco em uso como swap')
    identity=json.dumps([str(path),device_id,size,serial,model],sort_keys=True)
    return dict(path=str(path),bytes=size,model=model,serial=serial,
                identity=hashlib.sha256(identity.encode()).hexdigest())


def disks(source):
    rows=json.loads(command('lsblk','-J','-b','-d','-o','PATH,TYPE,SIZE,MODEL,SERIAL'))['blockdevices']
    result=[]
    for row in rows:
        if row['type']!='disk':continue
        if Path(row['path']).resolve()==Path(source).resolve():continue
        try:result.append(dict(info(row['path']),available=True))
        except (ValueError,OSError,subprocess.CalledProcessError) as exc:
            result.append(dict(path=row['path'],bytes=int(row['size']),model=row.get('model') or '',
                               serial=row.get('serial') or '',available=False,reason=str(exc)))
    return result


def make_layout(capacity, source):
    end=capacity//MIB*MIB
    reserve=sum(source['regions'][n]['bytes'] for n in ('system','console','cache','utils'))+MIB
    xbox=end-reserve
    data=dict(schema=1,experimental=True,xbox_bytes=xbox,disk_id=secrets.token_hex(4),
              build_id=source['build_id'],source_sha256=source['source_sha256'],
              base_variant='auto',installed=True)
    current=xbox
    for name in ('system','console','cache','utils'):
        data[name]=dict(offset=current,bytes=source['regions'][name]['bytes']);current+=data[name]['bytes']
    data['image_bytes']=end
    return layout.checked_layout(data)


def drive_regions(data):
    result={'e':layout.RETAIL[0][1:],'c':layout.RETAIL[1][1:],
            'x':layout.RETAIL[2][1:],'y':layout.RETAIL[3][1:],'z':layout.RETAIL[4][1:]}
    for i,(_,start,size) in enumerate(layout.extended(data)):result['fg'[i]]=(start,size)
    return result


def verify_payload(payload, progress=lambda *_:None):
    payload=Path(payload);manifest=json.loads((payload/'manifest.json').read_text())
    if manifest.get('schema')!=1 or manifest.get('default_dashboard')!='XBMC4Gamers':
        raise ValueError('catálogo de instalação inválido')
    for index,item in enumerate(manifest['files']):
        if index%250==0:progress('Conferindo pacotes de instalação...',int(8*index/max(1,len(manifest['files']))))
        path=payload/item['path']
        if not path.resolve().is_relative_to(payload.resolve()) or path.is_symlink():
            raise ValueError('caminho de pacote inválido')
        with path.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if path.stat().st_size!=item['bytes'] or actual!=item['sha256']:
            raise ValueError('pacote corrompido: '+item['path'])
    return manifest


def plan(target, source, payload, qa=False):
    device=info(target,qa)
    if Path(device['path'])==Path(source['device']).resolve():raise ValueError('mídia de origem bloqueada')
    data=make_layout(device['bytes'],source)
    regions=drive_regions(data)
    manifest=json.loads((Path(payload)/'manifest.json').read_text())
    for drive in ('c','e','f'):
        files=[dict(path=f['path'][2:],bytes=f['bytes']) for f in manifest['files'] if f['path'].startswith(drive+'/')]
        directories=[p[2:] for p in manifest.get('directories',[]) if p.startswith(drive+'/')]
        fatx.plan(Path(payload)/drive,regions[drive][1],files=files,directories=directories)
    minimum=(16*GIB+sum(source['regions'][n]['bytes'] for n in ('system','console','cache','utils')))
    return dict(device=device,layout=data,qa=qa,token=secrets.token_hex(24),
                xbox_gib=round(data['xbox_bytes']/GIB,2),minimum_bytes=minimum)


def copy_region(src_fd, dst_fd, start, dest, count):
    while count:
        chunk=os.pread(src_fd,min(count,4*MIB),start)
        if not chunk:raise OSError('mídia de instalação truncada')
        done=0
        while done<len(chunk):
            n=os.pwrite(dst_fd,chunk[done:],dest+done)
            if n<=0:raise OSError('cópia incompleta')
            done+=n
        start+=len(chunk);dest+=len(chunk);count-=len(chunk)


def boot_files(fd,data):
    """Install exact-device UEFI boot; writes only the checked SYSTEM region."""
    reference=f'/proc/{os.getpid()}/fd/{fd}@@{data["system"]["offset"]}'
    with tempfile.TemporaryDirectory(prefix='xrevive-boot-') as tmp:
        tmp=Path(tmp);diskid=data['disk_id']
        (tmp/'layout.json').write_text(json.dumps(data,indent=2)+'\n')
        cmdline=('boot=live live-media=/dev/disk/by-partuuid/'+diskid+'-04 toram quiet splash '
                 'xrevive.standalone=1 loglevel=0 rd.udev.log_level=0 '
                 'systemd.show_status=false vt.global_cursor_default=0 console=tty0')
        (tmp/'grub.cfg').write_text('set timeout=0\ninsmod part_msdos\ninsmod fat\n'
            'search --no-floppy --fs-uuid '+diskid[:4].upper()+'-'+diskid[4:].upper()+' --set=root\n'
            'set cmdline="'+cmdline+'"\n'
            'if [ -f /debug ]; then\n set cmdline="$cmdline systemd.debug_shell=ttyS0 systemd.mask=serial-getty@ttyS0.service"\nfi\n'
            'linux /live/vmlinuz $cmdline\ninitrd /live/initrd.img\nboot\n')
        subprocess.run(['grub-mkstandalone','-O','x86_64-efi','-o',str(tmp/'BOOTX64.EFI'),
                        'boot/grub/grub.cfg='+str(tmp/'grub.cfg')],check=True)
        subprocess.run(['mlabel','-i',reference,'-N',diskid,'::SYSTEM'],check=True)
        for name,dest in [('BOOTX64.EFI','::/EFI/BOOT/BOOTX64.EFI'),('layout.json','::/xrevive-standalone.json')]:
            subprocess.run(['mcopy','-o','-i',reference,str(tmp/name),dest],check=True)


def install(prepared, source, payload, progress=lambda *_:None):
    def source_identity():
        return info(source['device'],qa=prepared['qa'],allow_busy=True)['identity']
    if source.get('identity') and source_identity()!=source['identity']:
        raise ValueError('mídia de instalação foi trocada')
    manifest=verify_payload(payload,progress)
    imported=source.get('firmware')
    firmware_bytes={}
    if imported:
        for name,item in imported.items():
            if name not in ('bios.bin','mcpx_1.0.bin','eeprom.bin'):
                raise ValueError('arquivo de firmware não permitido')
            content=Path(item['path']).read_bytes()
            if hashlib.sha256(content).hexdigest()!=item['sha256']:
                raise ValueError('Firmware mudou; prepare a instalação novamente')
            firmware_bytes[name]=content
    original=prepared['device'];fresh=info(original['path'],prepared['qa'])
    if original!=fresh:raise ValueError('disco foi trocado desde a seleção')
    data=layout.checked_layout(prepared['layout']);regions=drive_regions(data)
    progress('Conferindo espaço no disco...',8)
    for drive in ('c','e','f'):fatx.plan(Path(payload)/drive,regions[drive][1])
    with open(source['device'],'rb',buffering=0) as source_file:
        if source.get('identity') and source_identity()!=source['identity']:
            raise ValueError('mídia de instalação foi trocada')
        source_size=os.lseek(source_file.fileno(),0,os.SEEK_END)
        for region in source['regions'].values():
            if region['offset']<0 or region['offset']+region['bytes']>source_size:
                raise ValueError('região de origem inválida')
        # CACHE can be mounted/writable when maintenance starts from an SSD.
        # Build a clean filesystem in a temporary regular file, never clone a
        # live ext4 journal and never pass a whole physical disk to mkfs.
        cache_tmp=tempfile.TemporaryDirectory(prefix='xrevive-cache-')
        cache_image=Path(cache_tmp.name)/'cache.part'
        with cache_image.open('xb') as cache_file:cache_file.truncate(data['cache']['bytes'])
        subprocess.run(['mkfs.ext4','-q','-F','-m','0','-L','CACHE',str(cache_image)],check=True)
        # Thin USB carries no collection. Persist only its actual inventory on
        # the SSD so maintenance remains independent of USB and the network.
        utils_image=None
        if source.get('thin'):
            metadata=Path(cache_tmp.name)/'metadata/payload';metadata.mkdir(parents=True)
            (metadata/'manifest.json').write_text(json.dumps(manifest))
            utils_image=Path(cache_tmp.name)/'utils.part'
            with utils_image.open('xb') as f:f.truncate(data['utils']['bytes'])
            subprocess.run(['mkfs.ext4','-q','-F','-m','0','-L','UTILS','-d',str(metadata.parent),str(utils_image)],check=True)
        fd=os.open(original['path'],os.O_RDWR|os.O_NOFOLLOW)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            expected=os.stat(original['path']);opened=os.fstat(fd)
            if (opened.st_dev,opened.st_ino,opened.st_rdev)!=(expected.st_dev,expected.st_ino,expected.st_rdev):
                raise ValueError('identidade do descritor mudou')
            if info(original['path'],prepared['qa'])!=original:raise ValueError('destino entrou em uso')
            # Erase old GPT headers, not the whole disk, AFTER double confirmation.
            progress('Preparando o disco...',10)
            os.pwrite(fd,bytes(MIB),0)
            os.pwrite(fd,bytes(MIB),data['image_bytes']-MIB)
            os.pwrite(fd,bytes(512),original['bytes']-512)
            for index,name in enumerate(('system','console','cache','utils')):
                progress('Instalando sistema X-Revive...',12+index*10)
                if name=='cache':
                    with cache_image.open('rb') as clean:
                        copy_region(clean.fileno(),fd,0,data[name]['offset'],data[name]['bytes'])
                elif name=='utils' and utils_image:
                    with utils_image.open('rb') as clean:
                        copy_region(clean.fileno(),fd,0,data[name]['offset'],data[name]['bytes'])
                else:
                    copy_region(source_file.fileno(),fd,source['regions'][name]['offset'],
                                data[name]['offset'],data[name]['bytes'])
            if imported:
                with tempfile.TemporaryDirectory(prefix='xrevive-firmware-') as tmp:
                    fw=Path(tmp)/'xbox';fw.mkdir()
                    for name,item in imported.items():
                        (fw/name).write_bytes(firmware_bytes[name])
                    reference=f'/proc/{os.getpid()}/fd/{fd}@@{data["console"]["offset"]}'
                    subprocess.run(['mmd','-i',reference,'::/firmware'],check=False,stderr=subprocess.DEVNULL)
                    subprocess.run(['mcopy','-o','-s','-i',reference,str(fw),'::/firmware/'],check=True)
            with tempfile.TemporaryDirectory(prefix='xrevive-empty-') as empty:
                for index,(drive,(offset,size)) in enumerate(regions.items()):
                    if drive=='g':
                        (Path(empty)/'Games').mkdir()
                        (Path(empty)/'Homebrew').mkdir()
                    progress('Instalando '+drive.upper()+': — dashboards e aplicativos...',45+index*5)
                    fatx.format_tree(fd,offset,size,Path(payload)/drive if drive in 'cef' else empty,
                        lambda a,b:progress('Preparando '+drive.upper()+':',45+index*5+int(5*a/max(1,b))))
            # A failed/partial install has no valid hybrid boot record.
            progress('Verificando todos os arquivos...',85)
            for drive in ('c','e','f'):
                fatx.Volume(fd,*regions[drive]).verify(Path(payload)/drive)
            progress('Preparando boot independente...',95)
            boot_files(fd,data)
            os.pwrite(fd,layout.footer(data),data['image_bytes']-layout.FOOTER_BYTES)
            os.fsync(fd)
            os.pwrite(fd,layout.sector0(data),0)
            os.fsync(fd)
        finally:os.close(fd);cache_tmp.cleanup()
    layout.read_verified(original['path'],data)
    progress('Instalação concluída. Remova o pendrive.',100)
    return dict(layout=data,packages=len(manifest['packages']),files=len(manifest['files']),
                default_dashboard='XBMC4Gamers',verified=True)


def installed(path):
    with open(path,'rb',buffering=0) as f:
        end=os.lseek(f.fileno(),0,os.SEEK_END)//MIB*MIB
        f.seek(end-layout.FOOTER_BYTES);data=layout.decode_footer(f.read(layout.FOOTER_BYTES))
    if data['image_bytes']!=end:raise ValueError('rodapé não pertence à capacidade atual')
    layout.read_verified(path,data)
    return data


def installed_manifest(path,data):
    """Read the target's own inventory through a bounded readonly mapping.

    The thin USB has an empty inventory. Never report a successful zero-file
    verification or choose dashboards from a different installation.
    """
    layout.read_verified(path,data)
    region=data['utils']
    loop=command('losetup','--find','--show','--read-only','--offset',str(region['offset']),
                 '--sizelimit',str(region['bytes']),str(path))
    try:
        with tempfile.TemporaryDirectory(prefix='xrevive-inventory-') as tmp:
            mounted=False
            try:
                subprocess.run(['mount','-o','ro,noload,nodev,nosuid,noexec',loop,tmp],check=True);mounted=True
                manifest=Path(tmp)/'payload/manifest.json'
                if manifest.is_symlink() or not 0<manifest.stat().st_size<32*MIB:
                    raise ValueError('inventário instalado inválido')
                result=json.loads(manifest.read_text())
                if result.get('schema')!=1 or not result.get('files') or not result.get('dashboards'):
                    raise ValueError('inventário instalado ausente/inválido')
                return result
            finally:
                if mounted:subprocess.run(['umount',tmp],check=True)
    finally:subprocess.run(['losetup','-d',loop],check=True)


def choose_dashboard(path,data,manifest,name):
    selected=next((d for d in manifest['dashboards'] if d['name']==name),None)
    if selected is None:raise ValueError('dashboard não cadastrada')
    drive=selected['path'][0].lower();relative=selected['path'][3:].replace('\\','/')
    fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        layout.read_verified(path,data)
        executable=fatx.Volume(fd,*drive_regions(data)[drive])
        if next(executable.chunks(relative),b'')[:4]!=b'XBEH':
            raise ValueError('executável da dashboard inválido')
        volume=fatx.Volume(fd,*drive_regions(data)['c'])
        content=volume.read('/Dashloader.ini').decode()
        import re
        content,count=re.subn(r'(\[Dashboard\]\s*\nPath\s*=)[^\n]*',lambda m:m[1]+' '+selected['path'],content)
        if count!=1:raise ValueError('configuração do carregador inválida')
        volume.replace('/Dashloader.ini',content.encode())
    finally:os.close(fd)


def repair_boot(path,data):
    fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        original=layout.read_verified(path,data)
        boot_files(fd,data)
        os.pwrite(fd,layout.repair_sector(original,data),0);os.fsync(fd)
    finally:os.close(fd)
