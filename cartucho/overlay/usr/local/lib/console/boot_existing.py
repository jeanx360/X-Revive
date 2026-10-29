"""Optional PC boot preparation alongside existing Xbox data, never formatting FATX."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

import installer as engine
import standalone


def offer(found,source):
    if found['installation']:
        return dict(available=True,kind='repair',layout=found['installation'],
                    message='O boot existente será substituído/atualizado. Dashboards, jogos e EEPROM serão preservados.')
    try:
        if any(r.get('warning') for r in found['regions']):
            raise ValueError('Há volumes que precisam de diagnóstico. O LIVE está disponível sem gravar no HDD.')
        with open(found['device']['path'],'rb') as stream:
            first=stream.read(512);gpt=stream.read(8)==b'EFI PART'
            stream.seek(found['device']['bytes']-512);gpt=gpt or stream.read(8)==b'EFI PART'
        data=engine.make_layout(found['device']['bytes'],source)
        if found['xbox_bytes']>data['xbox_bytes']:
            raise ValueError('O FATX ocupa a área necessária ao boot. É preciso reservar '+str(round((data['image_bytes']-data['xbox_bytes'])/1024**3,2))+' GiB fora dos volumes Xbox; iniciar em LIVE não altera o disco.')
        if found['table']!='PARTINFO' and any(r['drive']=='f' for r in found['regions']):
            raise ValueError('F: sem tabela explícita: use LIVE; preparação depende de confirmar a geometria.')
        import boot_recovery
        pc=boot_recovery.pc_regions(found['device']['path'],found['device']['bytes'])
        low,high=data['system']['offset'],data['image_bytes']
        for row in pc:
            if not row['efi'] and row['offset']>=found['xbox_bytes'] and max(low,row['offset'])<min(high,row['offset']+row['bytes']):
                raise ValueError('Partições de PC coexistentes: a área proposta contém uma partição de dados, fora do FATX.')
        replace=[row for row in pc if row['efi'] and row['offset']>=found['xbox_bytes']]
        data['existing_fatx']=True
        data['native_regions']=[{k:r[k] for k in ('drive','offset','bytes')} for r in found['regions']]
        standalone.checked_layout(data)
        native_sector(found,data,first)
        return dict(available=True,kind='append',layout=data,replace_ranges=replace,
                    message='O boot UEFI existente será substituído.' if replace else 'Criar o boot após o FATX, preservando dashboards e jogos.')
    except (ValueError,KeyError,TypeError,OSError) as exc:
        return dict(available=False,kind='unavailable',message=str(exc))


def native_sector(found,data,first):
    if first[:16]!=standalone.PARTINFO:
        if first not in (bytes(512),b'\xff'*512):
            import boot_recovery
            pc=boot_recovery.pc_regions(found['device']['path'],found['device']['bytes'])
            if not any(r['efi'] and r['offset']>=found['xbox_bytes'] for r in pc):
                raise ValueError('O setor de boot não tem um mapa UEFI reconhecido para substituir.')
        block=bytearray(512);block[:16]=standalone.PARTINFO
        for r in found['regions']:
            i='ecxyzfg'.index(r['drive'])
            struct.pack_into('<16sIIII',block,48+i*32,r['drive'].upper().encode(),0x80000000,
                             r['offset']//512,r['bytes']//512,0)
        first=bytes(block)
    return standalone.repair_sector(first,data)


def check_empty(fd,offset,count,progress=lambda *_:None,replace_ranges=()):
    """Conversion never treats free FATX clusters or deleted data as free sectors."""
    done=0
    while done<count:
        block=os.pread(fd,min(8*1024**2,count-done),offset+done)
        if not block:raise ValueError('Área de boot truncada')
        view=bytearray(block)
        for region in replace_ranges:
            a=max(offset+done,region['offset']);b=min(offset+done+len(block),region['offset']+region['bytes'])
            if a<b:view[a-offset-done:b-offset-done]=bytes(b-a)
        if view.count(0)!=len(view):
            raise ValueError('A área proposta contém dados. Nada foi alterado; use apenas LIVE.')
        done+=len(block);progress('Conferindo área disponível fora do FATX...',int(20*done/count))


def prepare(prepared,source,progress=lambda *_:None):
    import live_disk
    fresh=live_disk.check_plan(prepared,source)
    selected=prepared['boot']
    if not selected.get('available'):raise ValueError(selected['message'])
    device=engine.info(fresh['device']['path'],qa=prepared['qa'])
    if device!=prepared['device']:raise ValueError('Disco mudou desde a seleção')
    if selected['kind']=='repair':
        if prepared['qa']:
            raise ValueError('Reparo de boot completo exige VM/appliance')
        progress('Reparando o boot existente do X-Revive...',30)
        engine.repair_boot(device['path'],selected['layout'],source=source,progress=progress,recovered=True)
        return dict(boot_ready=True,kind='repair')
    if selected['kind']!='append':raise ValueError('Preparação de boot desconhecida')
    current=offer(fresh,source)
    # Disk-id is generated for each offer. All actual offsets must still match.
    data=standalone.checked_layout(selected['layout'])
    if not current['available'] or current['kind']!='append' or any(
        current['layout'][k]!=data[k] for k in ('xbox_bytes','system','console','cache','utils','image_bytes','native_regions')):
        raise ValueError('Mapa de espaço disponível mudou')
    if current.get('replace_ranges',[])!=selected.get('replace_ranges',[]):raise ValueError('Regiões de boot mudaram')
    if prepared['qa']:raise ValueError('Instalação de boot somente em VM/appliance')
    if engine.info(source['device'],allow_busy=True)['identity']!=source['identity']:
        raise ValueError('Pendrive de origem mudou')
    files=live_disk.package_source.firmware()
    firmware={}
    for name,item in files.items():
        content=Path(item['path']).read_bytes()
        if hashlib.sha256(content).hexdigest()!=item['sha256']:raise ValueError('Firmware mudou')
        firmware[name]=content
    fd=os.open(device['path'],os.O_RDWR|os.O_NOFOLLOW)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        current_stat=os.stat(device['path']);opened=os.fstat(fd)
        if (current_stat.st_dev,current_stat.st_ino,current_stat.st_rdev)!=(opened.st_dev,opened.st_ino,opened.st_rdev):
            raise ValueError('Identidade do descritor do HDD mudou')
        if engine.info(device['path'])!=device:raise ValueError('HDD entrou em uso')
        live_disk.check_plan(prepared,source)
        first=os.pread(fd,512,0);sector=native_sector(fresh,data,first)
        check_empty(fd,data['system']['offset'],data['image_bytes']-data['system']['offset'],progress,selected.get('replace_ranges',()))
        with tempfile.TemporaryDirectory(prefix='xrevive-existing-boot-') as tmp:
            tmp=Path(tmp);cache=tmp/'cache.part'
            with cache.open('xb') as stream:stream.truncate(data['cache']['bytes'])
            subprocess.run(['mkfs.ext4','-q','-F','-m','0','-L','CACHE',str(cache)],check=True)
            with open(source['device'],'rb',buffering=0) as src,cache.open('rb') as clean:
                size=os.lseek(src.fileno(),0,os.SEEK_END)
                if engine.info(source['device'],allow_busy=True)['identity']!=source['identity']:
                    raise ValueError('Pendrive de origem foi trocado')
                if any(r['offset']<0 or r['offset']+r['bytes']>size for r in source['regions'].values()):
                    raise ValueError('Região de origem inválida')
                for i,name in enumerate(('system','console','cache','utils')):
                    progress('Preparando boot sem formatar FATX: '+name.upper(),25+i*15)
                    region=data[name]
                    engine.copy_region(clean.fileno() if name=='cache' else src.fileno(),fd,
                        0 if name=='cache' else source['regions'][name]['offset'],region['offset'],region['bytes'])
            fw=tmp/'xbox';fw.mkdir()
            for name,content in firmware.items():(fw/name).write_bytes(content)
            reference=f'/proc/{os.getpid()}/fd/{fd}@@{data["console"]["offset"]}'
            subprocess.run(['mcopy','-o','-s','-i',reference,str(fw),'::/firmware/'],check=True)
            import dongle
            dongle.persist(reference,[Path('/userdata/X-Revive/firmware/dongle'),Path('/userdata/firmware/dongle')])
            engine.boot_files(fd,data)
            engine.clear_old_gpt(fd,device['bytes'],data)
            # Only publish the footer/boot record after all system files exist.
            os.pwrite(fd,standalone.footer(data),data['image_bytes']-standalone.FOOTER_BYTES)
            os.fsync(fd)
            os.pwrite(fd,sector,0);os.fsync(fd)
            standalone.read_verified(device['path'],data)
        progress('Boot preparado; seus dados FATX foram mantidos.',100)
        return dict(boot_ready=True,kind='append')
    finally:os.close(fd)
