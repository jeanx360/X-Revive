"""Read-only USB LIVE for Xbox FATX, including X-Revive hybrid disks.

No partitioning, formatting, boot repair or package installation belongs here.
The protected path has a kernel read-only loop backing a disposable qcow2.
"""
import argparse
import fcntl
import grp
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import struct
import subprocess

import fatx
import installer as engine
import package_source
import standalone
import runtime_command
from eeprom_store import read_eeprom

RUN=Path('/run/console')
PRIVATE=Path('/run/xrevive-live')
USER=Path('/userdata/X-Revive')
LIB=Path(__file__).resolve().parent
DRIVES=('e','c','x','y','z','f','g')


def volume_metadata(fd,region):
    start,count=region['offset'],region['bytes']
    header=os.pread(fd,4096,start)
    if len(header)!=4096 or header[:4]!=b'FATX':
        raise ValueError('FATX ausente em '+region['drive'].upper()+':')
    _,_,sectors,root=struct.unpack_from('<4sIII',header)
    cluster=sectors*512
    if not 512<=cluster<=1024**2 or cluster & (cluster-1):
        raise ValueError('Tamanho de cluster FATX inválido')
    clusters=count//cluster+1
    width=2 if clusters<0xfff0 else 4
    fat_bytes=((clusters*width+4095)//4096)*4096
    available=(count-4096-fat_bytes)//cluster
    if not 1<=root<=available:raise ValueError('Raiz FATX inválida')
    link=os.pread(fd,width,start+4096+root*width)
    value=int.from_bytes(link,'little')
    if len(link)!=width or not (1<=value<=available or value>=(0xfff8 if width==2 else 0xfffffff8)):
        raise ValueError('Cadeia da raiz FATX inválida')
    block=os.pread(fd,cluster,start+4096+fat_bytes+(root-1)*cluster)
    if len(block)!=cluster:raise ValueError('Raiz FATX truncada')
    # Check the first directory cluster, without walking user file trees.
    for index in range(0,len(block),64):
        n=block[index]
        if n in (0,255):break
        if n==0xe5:continue
        if n>42:raise ValueError('Diretório FATX inválido')
    return cluster,header+link+block


def inspect_fd(fd,size):
    """Recognize Xbox volumes independently of a PC boot record."""
    if size < standalone.F_OFFSET or size >= 2**41 or size%512:
        raise ValueError('Disco menor que a região Xbox retail ou acima de 2 TiB')
    first=os.pread(fd,4096,0)
    if len(first)!=4096:raise ValueError('HDD truncado ou inacessível')
    explicit=first[:16]==standalone.PARTINFO
    regions=[]
    if explicit:
        for i in range(14):
            _,flags,start,count,_=struct.unpack_from('<16sIIII',first,48+i*32)
            if flags & 0x80000000:
                if i>=len(DRIVES) or not count or start<1024 or (start+count)*512>size:
                    raise ValueError('Região PARTINFO fora do disco ou não suportada')
                regions.append(dict(drive=DRIVES[i],offset=start*512,bytes=count*512))
        if not set(DRIVES[:5]).issubset(r['drive'] for r in regions):
            raise ValueError('Tabela PARTINFO incompleta')
    else:
        regions=[dict(drive=DRIVES[i],offset=start,bytes=count)
                 for i,(_,start,count) in enumerate(standalone.RETAIL)]
        if os.pread(fd,4,standalone.F_OFFSET)==b'FATX':
            # Legacy BIOSes can use F to the disk end without PARTINFO. This
            # fallback permits a read-only attempt; boot preparation requires
            # an explicit map and never relies on this inferred extent.
            regions.append(dict(drive='f',offset=standalone.F_OFFSET,bytes=size-standalone.F_OFFSET))
    ordered=sorted(regions,key=lambda r:r['offset'])
    if any(a['offset']+a['bytes']>b['offset'] for a,b in zip(ordered,ordered[1:])):
        raise ValueError('Partições FATX sobrepostas')
    digest=hashlib.sha256(first)
    for region in regions:
        start,count=region['offset'],region['bytes']
        if start+count>size:raise ValueError('Partição FATX truncada')
        try:
            cluster,metadata=volume_metadata(fd,region)
            region['cluster_bytes']=cluster;digest.update(metadata)
        except ValueError as exc:
            if region['drive'] in ('c','e'):raise
            region['warning']=str(exc)
            digest.update(os.pread(fd,4096,start))
    return dict(table='PARTINFO' if explicit else 'retail',regions=regions,
                metadata_sha256=digest.hexdigest(),xbox_bytes=max(r['offset']+r['bytes'] for r in regions))


def inspect(path,qa=False):
    device=engine.info(path,qa=qa,allow_readonly=True)
    fd=os.open(device['path'],os.O_RDONLY|os.O_NOFOLLOW)
    try:
        installed=None
        try:installed=engine.installed(device['path'])
        except (ValueError,OSError,KeyError,TypeError):pass
        result=inspect_fd(fd,installed['xbox_bytes'] if installed else device['bytes'])
        if not installed:
            import boot_recovery
            installed=boot_recovery.recover(device['path'],device['bytes'],result['regions'])
        result['installation']=installed
        if installed:result['xbox_bytes']=installed['xbox_bytes']
    finally:os.close(fd)
    return dict(device=device,**result)


def disks(source):
    rows=json.loads(engine.command('lsblk','-J','-b','-d','-o','PATH,TYPE,SIZE,MODEL'))['blockdevices']
    result=[]
    for row in rows:
        if Path(row['path']).name.startswith(('nbd','loop','ram','zram')):continue
        if row['type']!='disk' or Path(row['path']).resolve()==Path(source).resolve():continue
        try:
            data=inspect(row['path'])
            result.append(dict(**data['device'],available=True,table=data['table'],
                               drives=[r['drive'].upper() for r in data['regions']]))
        except (ValueError,OSError,subprocess.SubprocessError) as exc:
            result.append(dict(path=row['path'],model=(row.get('model') or '').strip(),
                               bytes=int(row['size']),available=False,reason=str(exc)))
    return result


def plan(target,source,qa=False):
    if Path(target).resolve()==Path(source['device']).resolve():raise ValueError('Pendrive de boot bloqueado')
    result=inspect(target,qa)
    from boot_existing import offer
    return dict(**result,token=secrets.token_hex(24),qa=qa,boot=offer(result,source))


def check_plan(prepared,source):
    if Path(prepared['device']['path']).resolve()==Path(source['device']).resolve():
        raise ValueError('Pendrive de boot bloqueado')
    fresh=inspect(prepared['device']['path'],prepared['qa'])
    if any(fresh[k]!=prepared[k] for k in ('device','regions','metadata_sha256','xbox_bytes','installation')):
        raise ValueError('HDD mudou desde a seleção; selecione novamente')
    return fresh


def session_key(prepared):
    d=prepared['device']
    identity=[d['serial'],d['model'],d['bytes']] if d['serial'] else [d['identity']]
    return hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()


def create_overlay(backing,destination):
    subprocess.run(['qemu-img','create','-q','-f','qcow2','-F','raw','-b',str(backing),str(destination)],check=True)


def prepare(prepared,source,mode,run=RUN,progress=lambda *_:None):
    if mode!='protected':raise ValueError('LIVE não grava no HDD; escolha apenas iniciar ou preparar boot')
    if prepared.get('qa'):raise ValueError('Ativação LIVE somente em VM/appliance com dispositivos de bloco')
    if (PRIVATE/'session.json').exists():raise ValueError('LIVE já preparado; reinicie para trocar o HDD')
    fresh=check_plan(prepared,source)
    return prepare_mapping(prepared,fresh,source,mode,None,progress,run,lambda:check_plan(prepared,source))


def prepare_media(prepared,source,mode,iso,progress,run=RUN):
    import live_target
    fresh=live_target.check(prepared,source)
    return prepare_mapping(prepared,fresh,source,mode,iso,progress,run,lambda:live_target.check(prepared,source))


def prepare_mapping(prepared,fresh,source,mode,iso,progress,run,check):
    import live_target
    import live_media
    if source.get('identity')!=engine.info(source['device'],allow_busy=True)['identity']:
        raise ValueError('Pendrive de boot mudou')
    progress('Conferindo BIOS, MCPX e identidade do Xbox...',15)
    files=package_source.firmware()  # No collection/download for LIVE.
    if not os.path.ismount('/userdata'):raise ValueError('Área pessoal do USB ausente')
    console=run/('live-console-'+prepared['token']);fw=console/'firmware/xbox'
    console.mkdir()  # A failed attempt can never donate another HDD's EEPROM.
    fw.mkdir(parents=True);(console/'config').mkdir()
    for folder in (console,console/'firmware',fw):folder.chmod(0o755)
    storage=USER/'live'/session_key(prepared)
    storage.mkdir(parents=True,exist_ok=True)
    for name,item in files.items():
        data=Path(item['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Firmware mudou durante a leitura')
        (fw/name).write_bytes(data);(fw/name).chmod(0o644)
    persisted=storage/'firmware/xbox/eeprom.bin'
    if 'eeprom.bin' not in files and persisted.exists():
        (fw/'eeprom.bin').write_bytes(read_eeprom(persisted))
        (fw/'eeprom.bin').chmod(0o644)
    preferences=storage/'config/xemu'
    if preferences.is_dir():shutil.copytree(preferences,console/'config/xemu',dirs_exist_ok=True)
    progress('Preparando o acesso ao HDD selecionado...',25)
    loop=None;disc_loop=None;scratch=run/'live-changes';unlocked=False
    if mode=='write':live_target.unlock(fresh['device'],source);unlocked=True
    fd=None
    try:
        fd=os.open(fresh['device']['path'],(os.O_RDWR if mode=='write' else os.O_RDONLY)|os.O_NOFOLLOW)
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        current=os.stat(fresh['device']['path']);opened=os.fstat(fd)
        if (current.st_rdev,current.st_ino)!=(opened.st_rdev,opened.st_ino):raise ValueError('HDD trocado')
        check()
        args=['losetup','--find','--show','--sizelimit',str(fresh['xbox_bytes'])]
        if mode=='protected':args.append('--read-only')
        loop=subprocess.check_output(args+[f'/proc/{os.getpid()}/fd/{fd}'],text=True,timeout=15).strip()
        actual_ro=int(engine.command('blockdev','--getro',loop))
        if actual_ro!=int(mode=='protected'):raise ValueError('Proteção do mapeamento não confere')
        if int(engine.command('blockdev','--getsize64',loop))!=fresh['xbox_bytes']:
            raise ValueError('Tamanho do mapeamento diverge do HDD')
        gid=grp.getgrnam('console').gr_gid;uid=__import__('pwd').getpwnam('console').pw_uid
        os.chown(loop,0,gid);os.chmod(loop,0o440 if mode=='protected' else 0o660)
        hdd=loop
        if mode=='protected':
            progress('Criando alterações temporárias na RAM; HDD protegido...',40)
            scratch.mkdir(exist_ok=True)
            subprocess.run(['mount','-t','tmpfs','-o',f'size=512M,mode=0700,uid={uid},gid={gid}',
                            'xrevive-live',str(scratch)],check=True)
            hdd=str(scratch/'hdd.qcow2')
            create_overlay(loop,hdd)
            os.chown(hdd,uid,gid);os.chmod(hdd,0o600)
        if iso:
            progress('Conectando a mídia Xbox selecionada...',50)
            import xiso
            media=iso if isinstance(iso,dict) else dict(path=str(iso),**xiso.inspect(iso,require_boot=False))
            disc_loop=live_media.map_disc(media,gid)
        state=dict(mode=mode,device=fresh['device'],loop=loop,hdd=hdd,
                   console=str(console),storage=str(storage),dvd=disc_loop)
        PRIVATE.mkdir(mode=0o700,exist_ok=True);PRIVATE.chmod(0o700)
        (PRIVATE/'session.json').write_text(json.dumps(state));(PRIVATE/'session.json').chmod(0o600)
        (run/'live.json').write_text(json.dumps(dict(mode=mode)))
        progress('HDD pronto. Preparando a inicialização do Xbox...',55)
        return dict(mode=mode,physical_disk=True,write_enabled=mode=='write')
    except Exception:
        if os.path.ismount(scratch):subprocess.run(['umount',str(scratch)],check=False)
        if loop:subprocess.run(['losetup','-d',loop],check=False)
        if disc_loop:live_media.release_disc(disc_loop)
        if unlocked:live_target.relock(source)
        (PRIVATE/'session.json').unlink(missing_ok=True)
        (run/'live.json').unlink(missing_ok=True)
        raise
    finally:
        if fd is not None:os.close(fd)


def configure(run=RUN,progress=lambda *_:None):
    state=json.loads((PRIVATE/'session.json').read_text())
    if not (run/'installer').exists():raise ValueError('Assistente LIVE ausente')
    if state['mode']=='protected' and engine.command('blockdev','--getro',state['loop'])!='1':
        raise ValueError('HDD protegido perdeu somente leitura')
    progress('Identificando áudio e conexão de rede deste computador...',60)
    def hardware_line(line):
        if line.startswith('XREVIVE_STAGE '):progress(line.removeprefix('XREVIVE_STAGE '),65)
    runtime_command.run(['python3',str(LIB/'hardware.py'),str(run),'/console/config/ports.conf'],timeout=90,on_line=hardware_line)
    # All values are generated locally; hardware.py restricts interface names.
    env=dict(os.environ,CONSOLE=state['console'],RUN=str(run),PROFILE=str(run/'profile'),
             HDD=state['hdd'],HDD_FATX='yes',XREVIVE_LIVE='1',RAM='64')
    for line in (run/'hardware.env').read_text().splitlines():
        key,value=line.split('=',1);env[key]=value
    dvd='' if state.get('dvd') else next((str(p) for p in sorted(Path('/dev').glob('sr*')) if p.is_block_device()),'')
    (run/'dvd').write_text(dvd+'\n')
    if state.get('dvd'):
        (run/'live-disc').write_text(state['dvd']);(run/'live-disc').chmod(0o644)
    else:(run/'live-disc').unlink(missing_ok=True)
    if dvd:
        progress('Configurando o drive óptico...',75)
        events=Path('/sys/class/block',Path(dvd).name,'events_poll_msecs')
        if events.exists():events.write_text('2000')
        rules=Path('/run/udev/rules.d/91-xrevive-live.rules');rules.parent.mkdir(exist_ok=True)
        rules.write_text(f'SUBSYSTEM=="block", KERNEL=="{Path(dvd).name}", GROUP="console", MODE="0660"\n'
            f'ACTION=="change", SUBSYSTEM=="block", KERNEL=="{Path(dvd).name}", ENV{{DISK_MEDIA_CHANGE}}=="1", RUN+="/usr/bin/systemctl --no-block start console-media.service"\n'
            f'ACTION=="change", SUBSYSTEM=="block", KERNEL=="{Path(dvd).name}", ENV{{DISK_EJECT_REQUEST}}=="1", RUN+="/usr/bin/systemctl --no-block start console-bandeja.service"\n')
        runtime_command.run(['udevadm','control','--reload'],timeout=5)
        runtime_command.run(['udevadm','trigger','--action=change',dvd],timeout=5)
        # Do not wait for unrelated disks, networking or dongles to settle.
        subprocess.run(['udevadm','settle','--timeout=5'],check=False,timeout=7)
    progress('Configurando vídeo, controle e dashboard...',85)
    runtime_command.run(['sh',str(LIB/'platform/configure.sh')],env=env,timeout=25)
    from safe_live import keyboard_fallback
    keyboard_fallback(run/'xemu.toml')
    (run/'env').write_text((run/'hardware.env').read_text()+'XREVIVE_LIVE=1\n')
    progress('Configuração pronta. Abrindo o Xbox...',95)


def activate(run=RUN):
    state=json.loads((PRIVATE/'session.json').read_text())
    if not (run/'installer').exists() or not (run/'xemu.toml').is_file():
        raise ValueError('Configuração LIVE incompleta')
    if state['mode']=='protected' and engine.command('blockdev','--getro',state['loop'])!='1':
        raise ValueError('Proteção LIVE ausente')
    (run/'installer').unlink()
    try:
        subprocess.run(['systemctl','stop','console-installer.service'],check=True)
        subprocess.run(['systemctl','start','console.service'],check=True)
    except Exception:
        (run/'installer').write_text('usb\n')
        subprocess.run(['systemctl','stop','console.service'],check=False)
        subprocess.run(['systemctl','--no-block','start','console-installer.service'],check=False)
        raise


def abort(run=RUN):
    state_path=PRIVATE/'session.json'
    if not state_path.exists():return
    state=json.loads(state_path.read_text())
    if os.path.ismount(run/'live-changes'):
        subprocess.run(['umount',str(run/'live-changes')],check=True)
    import live_media
    live_media.release_disc(state['loop'])
    if state.get('dvd') and state['dvd']!=state['loop']:
        live_media.release_disc(state['dvd'])
    if state['mode']=='write':
        import live_target
        source=json.loads(Path('/run/xrevive-installer/source.json').read_text())
        live_target.relock(source)
    state_path.unlink();(run/'live.json').unlink(missing_ok=True)


def save(run=RUN,initial=False):
    fd=os.open(run/'eeprom-save.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        save_locked(run,initial)


def save_locked(run,initial):
    state=json.loads((PRIVATE/'session.json').read_text())
    storage=Path(state['storage'])
    if not storage.is_relative_to(USER/'live'):raise ValueError('Destino LIVE inválido')
    if not os.path.ismount('/userdata'):return
    source=run/'eeprom.bin';dest=storage/'firmware/xbox/eeprom.bin'
    if source.exists() and (not initial or not dest.exists()):
        try:data=read_eeprom(source)
        except ValueError:return
        dest.parent.mkdir(parents=True,exist_ok=True)
        temporary=dest.with_suffix('.new');temporary.write_bytes(data)
        with temporary.open('rb') as stream:os.fsync(stream.fileno())
        os.replace(temporary,dest)
        directory=os.open(dest.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    if not initial:
        tool=LIB/'platform/tools/preferences.py'
        subprocess.run(['python3',str(tool),'capture',str(run/'xemu.toml'),str(run/'profile'),str(run)],check=True)
        subprocess.run(['python3',str(tool),'commit',str(run),str(storage)],check=True)
    subprocess.run(['sync','-f',str(storage)],check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['activate','save','persist'])
    args=parser.parse_args()
    if args.action=='activate':activate()
    else:save(initial=args.action=='persist')
