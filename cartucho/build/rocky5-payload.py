"""Normalize the locked Rocky5 packages into the offline FATX install tree."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('fatx',ROOT/'cartucho/overlay/usr/local/lib/console/fatx.py')
fatx=importlib.util.module_from_spec(spec);spec.loader.exec_module(fatx)
uix_spec=importlib.util.spec_from_file_location('uix',Path(__file__).with_name('uix-relocate.py'))
uix=importlib.util.module_from_spec(uix_spec);uix_spec.loader.exec_module(uix)


def slug(text):
    return re.sub('[^a-zA-Z0-9_-]+','-',text).strip('-')[:32]


def build(cache, lock, output):
    cache,output=Path(cache),Path(output)
    data=json.loads(Path(lock).read_text())
    if output.exists():raise ValueError('destino já existe; manter diagnóstico anterior')
    output.mkdir(parents=True)
    for drive in ('c','e','f'):(output/drive).mkdir()
    records=[];dashboards=[];emulators={};warnings=[]
    case_paths={'':output}
    # Newer alternative versions take the canonical emulator directory first.
    items=sorted(data['packages'],key=lambda i:(i['title'],i['url']),reverse=True)
    order={'loader':0,'dashboards':1,'applications':2,'emulators':3,'themes':4}
    items.sort(key=lambda i:(order[i['category']], any(t in i['title'] for t in ('Synopsis','Configs'))))

    def put(dest,content,replace=False):
        # FATX is case-insensitive; merge upstream spelling variants on host.
        current=output;key=''
        for part in dest.relative_to(output).parts:
            key+='/'+part.casefold()
            if key not in case_paths:case_paths[key]=current/part
            current=case_paths[key]
        dest=current
        relative=dest.relative_to(output).as_posix()
        fatx.valid_path('/'+relative[2:])
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists() and dest.read_bytes()!=content and not replace:
            raise ValueError('colisão de pacote: '+relative)
        dest.write_bytes(content)

    for item in items:
        archive=cache/item['file']
        digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
        if digest!=item['sha256']:raise ValueError('pacote corrompido: '+item['title'])
        category,title=item['category'],item['title']
        if category=='loader':
            if title=='evoxdash.xbe':put(output/'c/evoxdash.xbe',archive.read_bytes())
            if item['id']=='shortcut-msdash':put(output/'f/Apps/Microsoft-Dashboard/default.xbe',archive.read_bytes())
            continue
        with zipfile.ZipFile(archive) as z:
            infos=[i for i in z.infolist() if not i.is_dir()]
            paths=[i.filename.replace('\\','/') for i in infos]
            for p in paths:
                if p.startswith('/') or any(c in ('..','.') for c in p.split('/')):
                    raise ValueError('caminho ZIP inseguro: '+p)
            roots={p.split('/')[0] for p in paths}
            common=next(iter(roots)) if len(roots)==1 and all('/' in p for p in paths) else ''
            strip=common+'/' if common else ''
            if category=='dashboards':
                if title=='Microsoft Dashboard 5960':
                    target=output/'c';strip='';launch='C:\\xboxdash.xbe'
                elif title=='UnleashX':
                    target=output/'e/Apps/UnleashX';launch='E:\\Apps\\UnleashX\\default.xbe'
                else:
                    target=output/'f/Dashboards'/('XBMC4Gamers' if title=='XBMC4Gamers' else
                        'XBMC-Emustation' if title=='XBMC-Emustation' else slug(title))
                    launch='F:\\'+str(target.relative_to(output/'f')).replace('/','\\')+'\\default.xbe'
                dashboards.append(dict(name=title,path=launch))
            elif category=='applications':target=output/'f/Apps'/slug(title)
            elif category=='emulators':
                name=common or slug(title)
                addon=not any(p[len(strip):].lower()=='default.xbe' for p in paths)
                if addon and name.casefold() in emulators:
                    target=emulators[name.casefold()]
                else:
                    if name.casefold() in emulators:name=slug(name+'-'+item['id'][-6:])
                    target=output/'f/Emulators'/name;emulators[name.casefold()]=target
            elif category=='themes':
                filename=item['url'].rsplit('/',1)[-1].lower()
                if filename.startswith('es-'):
                    target=output/'f/Dashboards/XBMC-Emustation/emustation/themes';strip=''
                else:
                    target=output/'f/Dashboards/XBMC4Gamers/skins/Profile';strip=''
            else:raise ValueError(category)
            for info,path in zip(infos,paths):
                relative=path[len(strip):]
                if relative.rsplit('/',1)[-1].lower() in ('thumbs.db','desktop.ini'):continue
                name=relative.rsplit('/',1)[-1]
                if len(name.encode('cp1252'))>42 and '/synopsis/' in ('/'+relative.lower()) and name.lower().endswith('.txt'):
                    shortened=name[:-4][:31]+'-'+hashlib.sha256(name.encode()).hexdigest()[:6]+'.txt'
                    warnings.append(dict(package=item['id'],original=relative,
                                         installed=relative[:-len(name)]+shortened,
                                         reason='upstream synopsis filename exceeds FATX 42-byte limit'))
                    relative=relative[:-len(name)]+shortened
                # Its native paths bypass the launch directory. Keep original
                # MS resources on C: and the complete UIX resource tree on F:.
                # Nine pinned native path literals select Partition6 instead.
                if category=='dashboards' and title=='UIX Lite':
                    content=z.read(info)
                    if relative=='xboxdash.xbe':
                        content=uix.relocate(content)
                        put(target/'default.xbe',content)
                    put(output/'f'/relative,content)
                    continue
                put(target/relative,z.read(info),replace=category=='emulators' and addon)
        records.append(dict(id=item['id'],title=title,category=category,sha256=digest,
                            destination=target.relative_to(output).as_posix()))
        print('payload',category,title,flush=True)
    # Standard launcher settings, independent of the example paths from chat.
    loader=('[UI]\nEnabled = 0\n[Logging]\nEnabled = 0\n[Dashboard]\n'
        'Path = F:\\Dashboards\\XBMC4Gamers\\default.xbe\n'
        '[Recovery]\nPath = E:\\Apps\\UnleashX\\default.xbe\n')
    put(output/'c/Dashloader.ini',loader.encode())
    (output/'e/UDATA').mkdir(exist_ok=True);(output/'e/TDATA').mkdir(exist_ok=True)
    (output/'f/Games').mkdir(exist_ok=True);(output/'f/Homebrew').mkdir(exist_ok=True)
    # Xbox's animation files remain supplied by the owner, like the firmware.
    animations=ROOT/'plataformas/xbox/firstrun/bootanims'
    if not (animations/'Xbox/BootAnim.xbe').is_file():raise ValueError('animação Xbox local ausente')
    shutil.copytree(animations,output/'e/Cerbios/BootAnims')
    # Surface dashboards alongside applications without moving their assets.
    source_path=output/'f/Dashboards/XBMC4Gamers/system/UserData/sources.xml'
    sources=ET.fromstring(source_path.read_bytes())
    programs=sources.find('programs')
    applications=next(s for s in programs.findall('source') if s.findtext('name')=='Applications')
    ET.SubElement(applications,'path',pathversion='1').text='F:\\Dashboards\\'
    dashboards_source=ET.SubElement(programs,'source')
    ET.SubElement(dashboards_source,'name').text='Dashboards'
    ET.SubElement(dashboards_source,'path',pathversion='1').text='F:\\Dashboards\\'
    ET.SubElement(dashboards_source,'path',pathversion='1').text='E:\\Apps\\'
    put(source_path,ET.tostring(sources,encoding='utf-8'),replace=True)
    # Emustation includes its own curated cores and naming scheme. Preserve
    # its default relative paths; the separate full emulator catalog remains
    # accessible through XBMC4Gamers' original Emulators source on F:.
    # Xored supplies the trainers; also expose its ETM set to XBMC4Gamers.
    trainer_root=output/'f/Apps/Xored-Mini'
    if trainer_root.exists():
        for path in trainer_root.rglob('*.etm'):
            put(output/'f/Dashboards/XBMC4Gamers/trainers'/path.name,path.read_bytes())
    # Audit every path/case and each destination before producing an image.
    for drive in ('c','e','f'):fatx.tree(output/drive)
    files=[]
    for p in sorted(output.rglob('*')):
        if p.is_file():
            with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
            files.append(dict(path=p.relative_to(output).as_posix(),bytes=p.stat().st_size,sha256=h))
    manifest=dict(schema=1,upstream_commit=data['upstream_commit'],packages=records,
                  dashboards=dashboards,files=files,warnings=warnings,
                  directories=[p.relative_to(output).as_posix() for p in sorted(output.rglob('*')) if p.is_dir()],
                  default_dashboard='XBMC4Gamers')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('PAYLOAD_COMPLETE',len(files),sum(i['bytes'] for i in files),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output');parser.add_argument('--cache',default=str(ROOT/'cartucho/cache/rocky5/packages'))
    parser.add_argument('--lock',default=str(ROOT/'cartucho/build/rocky5.lock.json'))
    args=parser.parse_args();build(args.cache,args.lock,args.output)
