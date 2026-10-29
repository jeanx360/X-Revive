"""Mount only partitions belonging to the actual USB boot device."""
import json
import os
from pathlib import Path
import subprocess
import installer as engine
import safe_live
import dongle

LIB=Path(__file__).resolve().parent
RUN=Path('/run/console')
PRIVATE=Path('/run/xrevive-installer')


def main():
    cmdline=Path('/proc/cmdline').read_text().split()
    medium=next((w.split('=',1)[1] for w in cmdline if w.startswith('live-media=/dev/')),None)
    if medium is None:raise ValueError('mídia de boot explícita ausente')
    part=Path(medium).resolve()
    parent=subprocess.check_output(['lsblk','-dnro','PKNAME',str(part)],text=True).strip()
    if not parent:raise ValueError('origem não é partição de disco')
    device='/dev/'+parent
    table=json.loads(subprocess.check_output(['lsblk','-J','-b','-o','NAME,PATH,PARTLABEL,START,SIZE',device],text=True))
    children=table['blockdevices'][0].get('children',[])
    regions={}
    for name in ('system','console','cache','utils'):
        item=next((p for p in children if (p.get('partlabel') or '').lower()==name),None)
        if not item:raise ValueError('partição de origem ausente: '+name)
        regions[name]=dict(offset=int(item['start'])*512,bytes=int(item['size']))
        if name in ('console','utils'):
            dest='/console' if name=='console' else '/utils'
            Path(dest).mkdir(exist_ok=True)
            options='ro,uid=console,gid=console,fmask=0137,dmask=0027' if name=='console' else 'ro,noload,nodev,nosuid,noexec'
            subprocess.run(['mount','-o',options,item['path'],dest],check=True)
    actual=next(p for p in children if Path(p['path']).resolve()==part)
    if actual.get('partlabel')!='SYSTEM':raise ValueError('boot não pertence à SYSTEM')
    PRIVATE.mkdir(mode=0o700,exist_ok=True)
    build=json.loads(Path('/usr/share/console/build.json').read_text())
    source=dict(device=device,regions=regions,build_id=build['build_id'],source_sha256=build['source_sha256'])
    source['identity']=engine.info(device,allow_busy=True)['identity']
    source['safe_live']=safe_live.enabled()
    users=next((p for p in children if p.get('partlabel')=='XREVIVE'),None)
    if users:
        Path('/userdata').mkdir(exist_ok=True)
        subprocess.run(['mount','-t','exfat','-o','rw,nodev,nosuid,noexec,uid=0,gid=0,fmask=0077,dmask=0077',users['path'],'/userdata'],check=True)
    if users:
        base=Path('/userdata/X-Revive')
        for folder in ('firmware/xbox','firmware/dongle','pacotes/live','cache','diagnosticos'):(base/folder).mkdir(parents=True,exist_ok=True)
        readme=Path('/userdata/LEIA-ME.txt')
        if not readme.exists():readme.write_bytes(Path('/usr/share/console/ARQUIVOS-DO-USUARIO.txt').read_bytes())
    source['thin']=bool(users)
    (PRIVATE/'source.json').write_text(json.dumps(source))
    (PRIVATE/'source.json').chmod(0o600)
    # The unified wizard starts with every other disk protected. Only a
    # confirmed, revalidated target can be unlocked for a write operation.
    protected=safe_live.protect(device)
    (PRIVATE/'protected-disks.json').write_text(json.dumps(protected))
    dongle.import_owner([Path('/userdata/X-Revive/firmware/dongle'),Path('/userdata/firmware/dongle')])
    RUN.mkdir(exist_ok=True)
    (RUN/'installer').write_text('usb\n')
    (RUN/'env').write_text('XREVIVE_INSTALLER=1\n')
    (RUN/'dvd').write_text('')
    os.chown(RUN,-1,__import__('grp').getgrnam('console').gr_gid)


if __name__=='__main__':main()
