"""USB-only Rocky5 session. No physical HDD is ever passed to Xemu.

Safe boot also denies installer write actions and protects other block devices
in the running kernel. Protection resets on reboot, never edits their contents.
"""
import argparse
import concurrent.futures
import grp
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import shutil
import subprocess
import tempfile
import urllib.parse
import uuid

import fatx
import live_disk
import package_source
import standalone
from updater import Transport
import xiso
import media_source
import live_media

LIB=Path(__file__).resolve().parent
LOCK=Path('/usr/share/console/rocky5-live-lock.json')
USER=package_source.USER


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def enabled():return 'xrevive.safe-live=1' in Path('/proc/cmdline').read_text().split()


def protect(source,exclude=()):
    """Fail closed if any attached non-USB disk cannot be made read-only."""
    rows=json.loads(subprocess.check_output(['/usr/bin/lsblk','-J','-p','--tree','-o','PATH,TYPE'],text=True))['blockdevices']
    protected=[]
    def visit(row):
        # Protect the whole disk first. A boot-table reread can recreate a
        # partition between SETRO and GETRO; the parent must already deny writes.
        try:
            subprocess.run(['/usr/sbin/blockdev','--setro',row['path']],check=True,timeout=5)
            readonly=subprocess.check_output(['/usr/sbin/blockdev','--getro',row['path']],text=True,timeout=5).strip()
        except (OSError,subprocess.CalledProcessError):
            if row['type']=='part' and not Path(row['path']).exists():return
            raise
        if readonly!='1':
            raise ValueError('Não foi possível proteger '+row['path'])
        protected.append(row['path'])
        for child in row.get('children',[]):visit(child)
    for row in rows:
        if row['type']=='disk' and Path(row['path']).resolve() not in {Path(p).resolve() for p in (source,*exclude)}:visit(row)
    return protected


def images():
    return media_source.images(USER)


def keyboard_fallback(config,pads=Path('/dev/input')):
    # Xemu auto-binds gamepads but only binds its keyboard when requested.
    # Keep controller port 1 free when a physical gamepad is already attached.
    if any(pads.glob('js[0-9]*')):return False
    with Path(config).open('a') as out:out.write("\n[input.bindings]\nport1 = 'keyboard'\n")
    return True


def checked_download_tree(lock,folder,progress):
    origin='https://raw.githubusercontent.com/Rocky5/Xbox-Softmodding-Tool/'
    if lock['origin']!=origin or len(lock['commit'])!=40:raise ValueError('Origem Rocky5 inválida')
    rows=lock['files'];seen=set()
    for item in rows:
        p=PurePosixPath(item['path'])
        if p.is_absolute() or '..' in p.parts or str(p) in seen or '\\' in str(p):raise ValueError('Caminho Rocky5 inválido')
        seen.add(str(p))
    total=sum(i['bytes'] for i in rows);done=0
    def fetch(item):
        path=folder/item['path'];path.parent.mkdir(parents=True,exist_ok=True)
        def valid():
            return (path.is_file() and not path.is_symlink() and path.stat().st_size==item['bytes']
                    and digest(path)==item['sha256'])
        if not valid():
            temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.download')
            url=origin+lock['commit']+'/Extras%20Disc/'+urllib.parse.quote(item['path'])
            try:
                Transport().fetch(url,temporary,item['bytes'])
                if temporary.stat().st_size!=item['bytes'] or digest(temporary)!=item['sha256']:
                    raise ValueError('Download Rocky5 não confere: '+item['path'])
                os.replace(temporary,path)
            finally:temporary.unlink(missing_ok=True)
        return item['bytes']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for count in pool.map(fetch,rows):
            done+=count;progress('Baixando e verificando Rocky5 Extras Disc...',5+int(65*done/total))


def disc(mode,identity,progress):
    if mode=='offline':
        path=media_source.selected(USER,identity)
        return live_media.prepare(path,USER,progress)
    if mode!='online':raise ValueError('Origem LIVE inválida')
    lock=json.loads(LOCK.read_text());key=hashlib.sha256(LOCK.read_bytes()).hexdigest()
    cache=USER/'cache/rocky5-live'/key;cache.mkdir(parents=True,exist_ok=True)
    output=cache/'rocky5-live.iso'
    if output.is_file() and digest(output)==lock['iso_sha256']:
        xiso.inspect(output);return output
    folder=cache/'disc';folder.mkdir(exist_ok=True)
    if shutil.disk_usage(cache).free<1600*1024**2:raise ValueError('Libere 1,6 GiB no pendrive para preparar o LIVE Rocky5')
    checked_download_tree(lock,folder,progress)
    progress('Preparando disco LIVE do Rocky5 no pendrive...',75)
    # Only locked files are accepted; never include arbitrary cache leftovers.
    expected={i['path'] for i in lock['files']}
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('Cache Rocky5 contém arquivos inesperados')
    temporary=cache/('disc-'+uuid.uuid4().hex+'.iso')
    try:
        xiso.build(folder,temporary)
        if digest(temporary)!=lock['iso_sha256']:
            raise ValueError('XISO Rocky5 gerada não confere')
        os.replace(temporary,output)
    finally:temporary.unlink(missing_ok=True)
    return output


def prepare(source,mode,identity,progress,run=Path('/run/console')):
    if (live_disk.PRIVATE/'session.json').exists():raise ValueError('LIVE já preparado')
    files=package_source.firmware()
    if not os.path.ismount('/userdata'):raise ValueError('Área pessoal do USB ausente')
    if source.get('identity')!=live_disk.engine.info(source['device'],allow_busy=True)['identity']:
        raise ValueError('Pendrive de boot mudou')
    if files!=package_source.firmware():raise ValueError('Firmware mudou durante a preparação')
    token=uuid.uuid4().hex;console=run/('live-console-'+token);fw=console/'firmware/xbox'
    fw.mkdir(parents=True);(console/'config').mkdir()
    for folder in (console,console/'firmware',fw):folder.chmod(0o755)
    storage=USER/'live/rocky5-sandbox';storage.mkdir(parents=True,exist_ok=True)
    for name,item in files.items():
        data=Path(item['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Firmware mudou')
        (fw/name).write_bytes(data);(fw/name).chmod(0o644)
    persisted=storage/'firmware/xbox/eeprom.bin'
    if 'eeprom.bin' not in files and persisted.exists():
        (fw/'eeprom.bin').write_bytes(live_disk.read_eeprom(persisted));(fw/'eeprom.bin').chmod(0o644)
    scratch=run/'live-changes';scratch.mkdir(exist_ok=True)
    uid=pwd.getpwnam('console').pw_uid;gid=grp.getgrnam('console').gr_gid;loop=None;iso=None
    try:
        iso=disc(mode,identity,lambda message,n:progress(message,5+int(.35*n)))
        progress('Mídia pronta. Criando o HDD temporário na RAM...',40)
        subprocess.run(['mount','-t','tmpfs','-o',f'size=1024M,mode=0700,uid={uid},gid={gid}',
                        'xrevive-sandbox',str(scratch)],check=True)
        raw=scratch/'virtual-hdd.raw'
        with raw.open('xb') as out:
            out.truncate(8*1024**3)
            with tempfile.TemporaryDirectory(dir=scratch) as empty:
                for _,offset,size in standalone.RETAIL:fatx.format_tree(out.fileno(),offset,size,Path(empty))
        raw.chmod(0o644)
        hdd=scratch/'hdd.qcow2';live_disk.create_overlay(raw,hdd);os.chown(hdd,uid,gid);hdd.chmod(0o600)
        # The sole mapped block device is the owner's ISO file on this USB.
        # No physical HDD descriptor, path or selected target enters the state.
        prepared=iso if isinstance(iso,dict) else dict(path=str(iso),**xiso.inspect(iso,require_boot=False))
        loop=live_media.map_disc(prepared,gid)
        state=dict(mode='sandbox',device=None,loop=loop,dvd=loop,hdd=str(hdd),console=str(console),storage=str(storage))
        live_disk.PRIVATE.mkdir(mode=0o700,exist_ok=True)
        live_disk.PRIVATE.chmod(0o700)
        (live_disk.PRIVATE/'session.json').write_text(json.dumps(state));(live_disk.PRIVATE/'session.json').chmod(0o600)
        (run/'live.json').write_text(json.dumps(dict(mode='sandbox')))
        progress('Mídia pronta — somente HDD virtual, discos físicos fora da sessão.',55)
        return dict(mode='sandbox',physical_disk=False,ram_limit_mib=1024)
    except Exception:
        if loop:live_media.release_disc(loop)
        elif isinstance(iso,dict) and iso.get('virtual'):live_media.release_disc(iso['path'])
        if os.path.ismount(scratch):subprocess.run(['umount',str(scratch)],check=False)
        (live_disk.PRIVATE/'session.json').unlink(missing_ok=True);(run/'live.json').unlink(missing_ok=True)
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['protect-new']);parser.add_argument('device')
    args=parser.parse_args()
    source=Path('/run/xrevive-installer/source.json')
    if source.is_file():
        selected=Path('/run/xrevive-live/write-target.json')
        exclude=()
        if selected.is_file():
            expected=json.loads(selected.read_text())
            try:
                if live_disk.engine.info(expected['path'],allow_readonly=True)==expected:exclude=(expected['path'],)
            except (OSError,ValueError,subprocess.CalledProcessError):pass
        protect(json.loads(source.read_text())['device'],exclude)
