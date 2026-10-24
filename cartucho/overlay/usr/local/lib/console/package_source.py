"""Prepare user-owned packages on the boot USB. Never opens a target disk."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from updater import Transport, canonical, digest
import installer
import rocky_payload

USER=Path('/userdata/X-Revive')
CONFIG=Path('/etc/xrevive-packages.json')
CATALOG=Path('/usr/share/console/rocky5-catalog.json')
KEY=Path('/usr/share/console/update-key.pem')
STAGE_BYTES=8*1024**3
STAGE=Path('/run/xrevive-packages')
OFFLINE=Path('/run/xrevive-offline')


def catalog():
    config=json.loads(CONFIG.read_text())
    raw=CATALOG.read_bytes()
    if config.get('catalog_url'):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'catalog'
                Transport().fetch(config['catalog_url'],path,1024**2)
                candidate=validate_catalog(json.loads(path.read_bytes()))
                if candidate['revision'] < validate_catalog(json.loads(raw))['revision']:
                    raise ValueError('catálogo antigo')
                return candidate
        except Exception as exc:print('CATALOG_FALLBACK',repr(exc),flush=True)
    return validate_catalog(json.loads(raw))


def validate_catalog(envelope):
    data=envelope['manifest']
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);(root/'body').write_bytes(canonical(data))
        (root/'sig').write_bytes(base64.b64decode(envelope['signature'],validate=True))
        subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(KEY),'-rawin',
                        '-in',str(root/'body'),'-sigfile',str(root/'sig')],check=True,capture_output=True,timeout=5)
    if data.get('kind')!='xrevive-rocky5' or data.get('recipe')!=1 or data.get('revision',0)<1:
        raise ValueError('catálogo incompatível')
    seen=set()
    for item in data['packages']:
        name=item['file']
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+',name) or name in seen:raise ValueError('nome de pacote inválido')
        seen.add(name)
        if not re.fullmatch('[a-f0-9]{64}',item['sha256']) or not 0<item['bytes']<2*1024**3:
            raise ValueError('identidade do pacote inválida')
        Transport().validate(item['url'])
    return data


def firmware():
    root=USER/'firmware/xbox';files={}
    for name,sizes in [('bios.bin',(256*1024,512*1024,1024**2)),('mcpx_1.0.bin',(512,)),('eeprom.bin',(256,))]:
        path=root/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size not in sizes:
            raise ValueError('Forneça '+str(path)+' com tamanho válido')
        files[name]=dict(path=str(path),sha256=digest(path),bytes=path.stat().st_size)
    # Reject blank EEPROM/ROMs; EEPROM integrity itself is handled by Xemu.
    if any(len(set(Path(i['path']).read_bytes()))<2 for i in files.values()):
        raise ValueError('Firmware vazio/inválido')
    return files


def sources():
    folder=USER/'pacotes'
    if not folder.is_dir():return []
    return [dict(id=p.name,name=p.name,bytes=p.stat().st_size)
            for p in sorted(folder.iterdir()) if p.is_file() and not p.is_symlink()
            and p.suffix.lower()=='.iso']


def safe_manifest(payload,progress=lambda *_:None):
    root=Path(payload);manifest=json.loads((root/'manifest.json').read_text())
    if manifest.get('schema')!=1 or manifest.get('default_dashboard')!='XBMC4Gamers':
        raise ValueError('ISO não contém coleção X-Revive compatível (payload/manifest.json)')
    if not 1<=len(manifest['files'])<=150000:raise ValueError('inventário inválido')
    seen=set();total=0
    for item in manifest['files']:
        path=item['path'];parts=Path(path).parts
        if not parts or parts[0] not in ('c','e','f') or len(parts)<2 or any(x in ('.','..') for x in path.split('/')):
            raise ValueError('caminho de pacote inválido')
        if Path(path).is_absolute() or '\\' in path or path.casefold() in seen:raise ValueError('caminho duplicado/inválido')
        seen.add(path.casefold());total+=item['bytes']
        if not 0<=item['bytes']<=2*1024**3 or not re.fullmatch('[a-f0-9]{64}',item['sha256']):raise ValueError('arquivo inválido')
        actual=root/path
        if not actual.resolve().is_relative_to(root.resolve()) or actual.is_symlink():raise ValueError('caminho fora do pacote')
    if total>7*1024**3:raise ValueError('coleção grande demais')
    for d in manifest.get('directories',[]):
        if d.startswith('/') or '\\' in d or any(x in ('.','..') for x in d.split('/')) or d.split('/')[0] not in ('c','e','f'):
            raise ValueError('diretório inválido')
    installer.verify_payload(root,lambda message,n:progress('Conferindo arquivos da coleção...',15+int(70*n/8)))
    return manifest


def prepare(mode,identity,progress):
    files=firmware()  # before downloads or allocating persistent staging
    if not os.path.ismount('/userdata'):raise ValueError('Área XREVIVE do pendrive não está montada')
    if mode=='offline':
        row=next((r for r in sources() if r['id']==identity),None)
        if row is None:raise ValueError('ISO local não encontrada em X-Revive/pacotes')
        path=(USER/'pacotes'/row['id']).resolve()
        if not path.is_relative_to((USER/'pacotes').resolve()):raise ValueError('origem inválida')
        OFFLINE.mkdir(exist_ok=True)
        if os.path.ismount(OFFLINE):subprocess.run(['umount',str(OFFLINE)],check=True)
        progress('Abrindo ISO offline...',5)
        # Kernel ISO9660 parser only. No boot/executable from the ISO is run.
        subprocess.run(['mount','-t','iso9660','-o','loop,ro,nodev,nosuid,noexec',str(path),str(OFFLINE)],check=True)
        payload=OFFLINE/'payload'
        progress('Conferindo a coleção offline inteira...',15)
        manifest=safe_manifest(payload,progress)
    elif mode=='online':
        data=catalog();cache=USER/'cache';cache.mkdir(exist_ok=True)
        image=cache/'rocky5-stage.ext4'
        STAGE.mkdir(exist_ok=True)
        if not image.exists():
            free=shutil.disk_usage(cache).free
            if free<STAGE_BYTES+128*1024**2:
                raise ValueError('Falta espaço para preparar Rocky5 (8 GiB). Retire ISOs offline antes do teste online.')
            progress('Preparando área persistente no pendrive...',2)
            with image.open('xb') as f:f.truncate(STAGE_BYTES)
            try:
                subprocess.run(['mkfs.ext4','-q','-F','-m','0','-N','180000',str(image)],check=True)
            except Exception:
                image.unlink();raise
        if image.stat().st_size!=STAGE_BYTES:raise ValueError('Área de preparação inválida')
        if not os.path.ismount(STAGE):
            subprocess.run(['e2fsck','-p',str(image)],check=False,stdout=subprocess.DEVNULL)
            subprocess.run(['mount','-o','loop,rw,nodev,nosuid,noexec',str(image),str(STAGE)],check=True)
        packages=STAGE/'packages';packages.mkdir(exist_ok=True)
        total=sum(i['bytes'] for i in data['packages']);done=0
        transport=Transport()
        for item in data['packages']:
            path=packages/item['file'];valid=path.exists() and path.stat().st_size==item['bytes'] and digest(path)==item['sha256']
            if not valid:
                temp=path.with_suffix('.download');temp.unlink(missing_ok=True)
                progress('Baixando '+item['title'],5+int(35*done/total))
                try:
                    transport.fetch(item['url'],temp,item['bytes'],
                        lambda a,b:progress('Baixando '+item['title'],5+int(35*(done+a)/total)))
                    if temp.stat().st_size!=item['bytes'] or digest(temp)!=item['sha256']:
                        raise ValueError('Download não confere: '+item['title'])
                    temp.replace(path)
                finally:temp.unlink(missing_ok=True)
            done+=item['bytes']
        lock=STAGE/'rocky5.lock.json';lock.write_text(json.dumps(data))
        payload=STAGE/'payload'
        marker=STAGE/'prepared-catalog.sha256'
        identity=hashlib.sha256(canonical(data)).hexdigest()
        if payload.exists() and (not marker.exists() or marker.read_text()!=identity):
            shutil.rmtree(payload)
        if payload.exists():
            try:manifest=safe_manifest(payload,progress)
            except Exception:
                # Remove only our normalized transaction, never user packages.
                shutil.rmtree(payload)
                manifest=None
            else:
                if manifest.get('upstream_commit')!=data['upstream_commit']:
                    shutil.rmtree(payload);manifest=None
        else:manifest=None
        if manifest is None:
            progress('Preparando dashboards e aplicativos...',45)
            rocky_payload.build(packages,lock,payload,animations=USER/'firmware/bootanims',progress=progress)
            manifest=safe_manifest(payload,progress)
            marker.write_text(identity)
        subprocess.run(['sync','-f',str(STAGE)],check=True)
    else:raise ValueError('origem desconhecida')
    # Bind the exact imported firmware hashes to the final confirmation plan.
    if files!=firmware():raise ValueError('Firmware mudou durante a preparação')
    progress('Coleção e firmware verificados. Escolha o disco.',100)
    return payload,manifest,files
