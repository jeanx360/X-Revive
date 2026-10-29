"""Prepare owner media without changing the original or any target HDD.

Native XDVDFS is mapped directly. ISO9660 trees are mastered to a cached
XDVDFS disc; the older X-Revive collection gets an explicit UnleashX menu.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET

import package_source
import xiso
import fatx

RECIPE=2


def reclaim_generated_cache(parent,source_sha):
    """Remove only verified, reproducible older recipes for this same input.

    Never visits pacotes, firmware or other source hashes. Unknown/corrupt files
    are preserved. This prevents a previous generated ISO occupying all free USB.
    """
    reclaimed=0
    for number in range(1,RECIPE):
        folder=Path(parent)/str(number);marker=folder/'verified.json';image=folder/'disc.iso'
        if folder.is_symlink() or marker.is_symlink() or image.is_symlink():continue
        if not marker.is_file() or not image.is_file() or marker.stat().st_size>65536:continue
        try:
            state=json.loads(marker.read_text())
            if state.get('source_sha256')!=source_sha or state.get('kind') not in ('collection','iso9660'):continue
            with image.open('rb') as stream:check=hashlib.file_digest(stream,'sha256').hexdigest()
            if check!=state.get('sha256'):continue
            reclaimed+=image.stat().st_size;image.unlink();marker.unlink()
        except (OSError,ValueError,TypeError):continue
    return reclaimed


def collection_menu():
    root=ET.Element('Unleashx');settings=ET.SubElement(root,'Settings')
    preference=ET.SubElement(settings,'Preference')
    for key,text in [('AbortOnError','Yes'),('EnableDriveF','Yes'),('EnableDriveG','Yes')]:
        ET.SubElement(preference,key).text=text
    ET.SubElement(preference,'VideoSettings',Use480P='Yes',FastRefresh='No')
    ET.SubElement(preference,'DVD',AutoLaunch='No')
    ET.SubElement(preference,'Games',AutoLaunch='No')
    ET.SubElement(preference,'LiveUpdate',AutoCheck='No')
    ET.SubElement(settings,'Network',Type='DHCP',Enable='Yes')
    ftp=ET.SubElement(settings,'FTP',Enable='Yes');ET.SubElement(ftp,'User').text='xbox';ET.SubElement(ftp,'Password').text='xbox'
    menu=ET.SubElement(root,'Menu')
    def item(parent,action,text='',**args):
        node=ET.SubElement(parent,'Item',Action=action,**args);node.text=text;return node
    item(menu,'Filemanager','Explorar arquivos / copiar manualmente')
    install=ET.SubElement(menu,'List',Text='Instalar colecao X-Revive (C, E e F)',Sort='Off',Batch='True')
    item(install,'AskUser','Sobrescreve arquivos em C, E e F. Jogos existentes nao sao removidos. Confirme apenas no HDD escolhido.',Arg1='Instalar colecao?')
    item(install,'AskUser','Confirme novamente. C, E e F precisam estar formatadas e ter espaco suficiente.',Arg1='Confirmar escrita no HDD?')
    for drive in 'cef':item(install,'Copy','Instalando '+drive.upper()+':',Arg1='D:\\payload\\'+drive,Arg2=drive.upper()+':\\')
    item(install,'MessageBox','Colecao copiada. Dashboard padrao: XBMC4Gamers. Reinicie sem a midia para iniciar pelo HDD.',Arg1='Concluido')
    formats=ET.SubElement(menu,'List',Text='Formatacao manual de volumes',Sort='Off')
    for drive in 'cefgxyz':
        batch=ET.SubElement(formats,'List',Text='Formatar '+drive.upper()+': (apaga o volume)',Batch='True',Sort='Off')
        item(batch,'AskUser','Todos os dados deste volume serao apagados.',Arg1='Formatar '+drive.upper()+':?')
        item(batch,'AskUser','Confira o volume escolhido. Esta operacao nao pode ser desfeita.',Arg1='Confirmar formatacao?')
        item(batch,'Format',Arg1=drive.upper())
    for label,paths in [('Aplicativos da midia',['D:\\payload\\f\\Apps','D:\\payload\\e\\Apps']),
                        ('Dashboards da midia',['D:\\payload\\f\\Dashboards']),
                        ('Emuladores da midia',['D:\\payload\\f\\Emulators'])]:
        node=ET.SubElement(menu,'List',Text=label,Sort='On',DelayLoad='True')
        for path in paths:ET.SubElement(node,'Path').text=path
    item(menu,'Settings','Configuracoes');item(menu,'Restart','Reiniciar Xbox');item(menu,'Shutdown','Desligar')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def source_tree(mounted,extra,progress):
    aliases={};renames={};changes=[];kind='iso9660'
    if (mounted/'payload/manifest.json').is_file():
        manifest=package_source.safe_manifest(mounted/'payload',lambda message,n:progress(message,min(40,n)))
        binary=mounted/'payload/e/Apps/UnleashX/default.xbe'
        if not binary.is_file():raise ValueError('Coleção sem UnleashX para iniciar o menu LIVE')
        with binary.open('rb') as stream:
            if stream.read(4)!=b'XBEH':raise ValueError('UnleashX inválido na coleção')
        (extra/'config.xml').write_bytes(collection_menu())
        aliases={'default.xbe':binary,'config.xml':extra/'config.xml'};kind='collection'
        # Do not rename applications or their referenced resources.
        # Legacy normalized collections contain a few synopsis names
        # (comma/plus/mojibake) that native Xbox CreateFile rejects.
        for item in manifest['files']:
            relative=item['path'];old=Path(relative).name
            if '/synopsis/' not in '/'+relative.lower() or not old.lower().endswith('.txt'):continue
            new=fatx.metadata_filename(old)
            if new!=old:
                renames[str(mounted/'payload'/relative)]=new
                changes.append(dict(source=relative,installed=str(Path(relative).with_name(new)),sha256=item['sha256'],bytes=item['bytes']))
        if changes:
            (extra/'XREVIVE-NAMES.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2))
            aliases['XREVIVE-NAMES.json']=extra/'XREVIVE-NAMES.json'
    elif not any(p.name.casefold()=='default.xbe' and p.is_file() for p in mounted.iterdir()):
        raise ValueError('ISO de arquivos sem executável Xbox de boot. Use a ISO Xbox completa do autor.')
    return aliases,renames,changes,kind


def prepare_cached(path,user,progress):
    path=Path(path)
    try:
        result=dict(path=str(path),**xiso.inspect(path,require_boot=False),adapted=False)
        print('LIVE_MEDIA',json.dumps(result),flush=True);return result
    except ValueError as native_error:
        # Only fall back for a different filesystem, not a corrupt Xbox tree.
        if 'Sem partição Xbox' not in str(native_error):raise
    stamp=path.stat();progress('Verificando mídia e preparando compatibilidade de boot...',5)
    with path.open('rb') as src:sha=hashlib.file_digest(src,'sha256').hexdigest()
    cache=Path(user)/'cache/live-media'/sha/str(RECIPE);cache.mkdir(parents=True,exist_ok=True)
    output=cache/'disc.iso';marker=cache/'verified.json'
    if output.is_file() and marker.is_file():
        state=json.loads(marker.read_text())
        with output.open('rb') as src:valid=hashlib.file_digest(src,'sha256').hexdigest()==state.get('sha256')
        if valid:return dict(path=str(output),**xiso.inspect(output),adapted=True,kind=state['kind'])
    temporary=cache/('disc-'+uuid.uuid4().hex+'.iso')
    with tempfile.TemporaryDirectory(prefix='xrevive-disc-') as folder:
        root=Path(folder);mounted=root/'iso';mounted.mkdir();extra=root/'boot';extra.mkdir()
        try:
            result=subprocess.run(['mount','-t','iso9660','-o','loop,ro,nodev,nosuid,noexec',str(path),str(mounted)],capture_output=True,text=True)
            if result.returncode:raise ValueError('Mídia sem XDVDFS ou ISO9660 legível. Confira se a cópia terminou e se o arquivo está íntegro.')
            aliases,renames,changes,kind=source_tree(mounted,extra,progress)
            total=sum(p.stat().st_size for p in mounted.rglob('*') if p.is_file())
            if shutil.disk_usage(cache).free<total+128*1024**2:
                progress('Recriando somente o cache gerado da versão anterior; original preservado...',40)
                reclaim_generated_cache(cache.parent,sha)
                if shutil.disk_usage(cache).free<total+128*1024**2:
                    raise ValueError(f'Libere {(total+128*1024**2)/1024**3:.1f} GiB no pendrive para adaptar esta mídia uma vez')
            progress('Criando mídia Xbox compatível no pendrive; o original será preservado...',45)
            # The collection is already validated, including names and hashes.
            xiso.build(mounted,temporary,aliases,renames)
            if (stamp.st_size,stamp.st_mtime_ns,stamp.st_ino)!=(path.stat().st_size,path.stat().st_mtime_ns,path.stat().st_ino):
                raise ValueError('Mídia mudou durante a preparação')
            with temporary.open('rb') as src:check=hashlib.file_digest(src,'sha256').hexdigest()
            os.replace(temporary,output)
            pending=marker.with_suffix('.new');pending.write_text(json.dumps(dict(sha256=check,kind=kind,source_sha256=sha,name_changes=changes)))
            os.replace(pending,marker)
            return dict(path=str(output),**xiso.inspect(output),adapted=True,kind=kind)
        finally:
            if os.path.ismount(mounted):subprocess.run(['umount',str(mounted)],check=True)
            temporary.unlink(missing_ok=True)


def prepare(path,user,progress):
    path=Path(path)
    try:return dict(path=str(path),**xiso.inspect(path,require_boot=False),adapted=False)
    except ValueError as exc:
        if 'Sem partição Xbox' not in str(exc):raise
    # The current appliance kernel includes nbd. Keep the disk-cache adapter
    # as a compatibility path for an older kernel lacking that module.
    modules=Path('/lib/modules')/os.uname().release
    if not any(modules.glob('kernel/drivers/block/nbd.ko*')):
        return prepare_cached(path,user,progress)
    import virtual_disc
    root=Path(tempfile.mkdtemp(prefix='xrevive-disc-'));mounted=root/'iso';mounted.mkdir();extra=root/'boot';extra.mkdir()
    transferred=False;result=None
    try:
        progress('Abrindo a mídia original em somente leitura...',5)
        subprocess.run(['mount','-t','iso9660','-o','loop,ro,nodev,nosuid,noexec',str(path),str(mounted)],check=True,timeout=15)
        aliases,renames,changes,kind=source_tree(mounted,extra,progress)
        result=virtual_disc.start(root,mounted,aliases,renames,progress)
        result['kind']=kind;result['name_changes']=changes
        progress('DVD virtual pronto; ISO original preservada e sem cópia adicional.',50)
        transferred=True
        return result
    finally:
        if not transferred:
            if result:release_disc(result['path'])
            if os.path.ismount(mounted):subprocess.run(['umount',str(mounted)],check=True,timeout=10)
            if root.exists():shutil.rmtree(root)


def release_disc(device):
    import virtual_disc
    if not virtual_disc.release(device):subprocess.run(['losetup','-d',device],check=True,timeout=10)


def map_disc(prepared,gid):
    if prepared.get('virtual'):
        path=prepared['path'];os.chown(path,0,gid);os.chmod(path,0o440);return path
    args=['losetup','--find','--show','--read-only','--offset',str(prepared['offset']),
          '--sizelimit',str(prepared['disc_bytes']),prepared['path']]
    loop=subprocess.check_output(args,text=True).strip()
    os.chown(loop,0,gid);os.chmod(loop,0o440)
    return loop
