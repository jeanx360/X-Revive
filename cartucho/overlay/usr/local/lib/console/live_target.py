"""Explicit selected-disk LIVE plans, independent of pre-existing FATX.

Discovery and planning are read-only. Only the worker's two confirmations may
call unlock/prepare(write). The boot USB and busy/hot-swapped disks are denied.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess

import installer as engine
import live_disk
import safe_live
import standalone


def inspect(path,source,qa=False):
    if Path(path).resolve()==Path(source['device']).resolve():raise ValueError('Pendrive de boot bloqueado')
    device=engine.info(path,qa=qa,allow_readonly=True)
    if not standalone.F_OFFSET<=device['bytes']<2**41:raise ValueError('HDD Xbox deve ter ao menos 8 GB e menos de 2 TiB')
    with open(device['path'],'rb') as stream:first=stream.read(4096)
    installed=None
    try:installed=engine.installed(device['path'])
    except (ValueError,OSError,KeyError,TypeError):pass
    found=None
    try:found=live_disk.inspect(path,qa=qa)
    except (ValueError,OSError,subprocess.SubprocessError):pass
    if not installed and found:installed=found.get('installation')
    # Never expose a recognized hybrid's Linux tail, even with damaged FATX.
    if installed:limit=installed['xbox_bytes'];kind='X-Revive híbrido'
    elif standalone.is_container(device['path']):
        raise ValueError('X-Revive com manifesto danificado: diagnostique o limite do HDD antes de acessar')
    else:limit=device['bytes'];kind='Disco para preparar / formato não reconhecido'
    if found:
        kind='X-Revive híbrido' if installed else 'Xbox FATX'
        # Native disks may have free space after retail partitions. Tools
        # need the real capacity to create F/G; hybrids retain their limit.
    return dict(device=device,xbox_bytes=limit,kind=kind,installation=installed,
                header_sha256=hashlib.sha256(first).hexdigest(),qa=qa)


def disks(source):
    rows=json.loads(engine.command('lsblk','-J','-b','-d','-o','PATH,TYPE,SIZE,MODEL,TRAN,SERIAL'))['blockdevices']
    result=[]
    for row in rows:
        if Path(row['path']).name.startswith(('nbd','loop','ram','zram')):continue
        if row['type']!='disk' or Path(row['path']).resolve()==Path(source['device']).resolve():continue
        base=dict(path=row['path'],model=(row.get('model') or '').strip(),serial=row.get('serial') or '',
                  bytes=int(row['size']),transport=row.get('tran') or '')
        try:
            data=inspect(row['path'],source)
            result.append(dict(**base,identity=data['device']['identity'],available=True,kind=data['kind']))
        except (ValueError,OSError,subprocess.SubprocessError) as exc:
            result.append(dict(**base,available=False,reason=str(exc)))
    return result


def plan(path,source,qa=False):return dict(**inspect(path,source,qa),token=secrets.token_hex(24))


def check(prepared,source):
    fresh=inspect(prepared['device']['path'],source,qa=prepared['qa'])
    if any(fresh[k]!=prepared[k] for k in ('device','xbox_bytes','header_sha256','installation')):
        raise ValueError('Disco mudou desde a seleção; selecione novamente')
    return fresh


def unlock(device,source):
    """No data writes here; authorization is checked by the worker, not RPC."""
    if Path(device['path']).resolve()==Path(source['device']).resolve():raise ValueError('Pendrive de boot bloqueado')
    if engine.info(device['path'],allow_readonly=True)!=device:raise ValueError('Disco trocado ou em uso')
    if source.get('identity')!=engine.info(source['device'],allow_busy=True)['identity']:raise ValueError('Pendrive mudou')
    private=live_disk.PRIVATE;private.mkdir(mode=0o700,exist_ok=True);private.chmod(0o700)
    (private/'write-target.json').write_text(json.dumps(device));(private/'write-target.json').chmod(0o600)
    try:
        safe_live.protect(source['device'],exclude=(device['path'],))
        nodes=json.loads(engine.command('lsblk','-J','-o','PATH',device['path']))['blockdevices']
        def visit(node):
            subprocess.run(['blockdev','--setrw',node['path']],check=True)
            for child in node.get('children',[]):visit(child)
        for node in nodes:visit(node)
        if engine.command('blockdev','--getro',device['path'])!='0':raise ValueError('Disco permanece somente leitura')
        if engine.info(device['path'])!=device:raise ValueError('Disco mudou durante a autorização')
    except Exception:
        (private/'write-target.json').unlink(missing_ok=True);safe_live.protect(source['device']);raise


def relock(source):
    (live_disk.PRIVATE/'write-target.json').unlink(missing_ok=True)
    safe_live.protect(source['device'])


def prepare(prepared,source,mode,media,progress,run=live_disk.RUN):
    if mode not in ('protected','write'):raise ValueError('Modo LIVE inválido')
    if prepared.get('qa'):raise ValueError('Ativação exige dispositivos de bloco dentro da VM/appliance')
    if (live_disk.PRIVATE/'session.json').exists():raise ValueError('Sessão LIVE já preparada')
    fresh=check(prepared,source)
    if media['mode']=='hdd':iso=None
    else:
        iso=safe_live.disc(media['mode'],media.get('identity'),lambda message,n:progress(message,5+int(.35*n)))
        progress('Mídia pronta. Conferindo novamente o HDD escolhido...',40)
    # Download/conversion may take minutes: recheck disk before granting access.
    try:
        check(prepared,source)
        mapping_progress=progress if iso is None else lambda message,n:progress(message,40+int(.35*n))
        return live_disk.prepare_media(prepared,source,mode,iso,mapping_progress,run)
    except Exception:
        if isinstance(iso,dict) and iso.get('virtual'):
            import live_media
            live_media.release_disc(iso['path'])
        raise
