"""Local privileged worker with a finite JSON protocol, no shell/eval input."""
import grp
import hashlib
import json
import os
from pathlib import Path
import socketserver
import threading
import subprocess

import installer as engine
import standalone as layout
import fatx
import package_source

PRIVATE=Path('/run/xrevive-installer')
PAYLOAD=Path('/utils/payload')
status={'busy':False,'message':'Pronto','progress':0}
mutex=threading.Lock()
pending=None
confirmation=0


def source_info():
    state=layout.PRIVATE_STATE/'state.json'
    if state.exists():
        item=json.loads(state.read_text());data=item['layout']
        layout.read_verified(item['boot_device'],data)
        return dict(device=item['boot_device'],regions={n:data[n] for n in ('system','console','cache','utils')},
                    build_id=data['build_id'],source_sha256=data['source_sha256'],
                    identity=engine.info(item['boot_device'],allow_busy=True)['identity'])
    return json.loads((PRIVATE/'source.json').read_text())


SOURCE=source_info()
MANIFEST=json.loads((PAYLOAD/'manifest.json').read_text())


def progress(message,percent):
    with mutex:status.update(message=message,progress=percent)
    print(percent,message,flush=True)


def available():
    return engine.disks(SOURCE['device'])


def maintenance_target(request):
    path=request.get('target')
    current=Path(SOURCE['device']).resolve()
    if path=='current':
        if not (layout.PRIVATE_STATE/'state.json').exists():raise ValueError('pendrive não é instalação')
        target=str(current)
        data=json.loads((layout.PRIVATE_STATE/'state.json').read_text())['layout']
        layout.read_verified(target,data)
        return target,data
    else:
        row=next((r for r in available() if r.get('identity')==path and r['available']),None)
        if row is None:raise ValueError('disco indisponível/trocado')
        target=row['path']
    return target,engine.installed(target)


def job(function):
    with mutex:
        if status['busy']:raise ValueError('operação em andamento')
        status.update(busy=True,message='Verificando...',progress=0,error=None,result=None)
    def execute():
        try:
            result=function()
            with mutex:status.update(busy=False,result=result,message='Operação concluída',progress=100)
        except Exception as exc:
            with mutex:status.update(busy=False,error=str(exc),message='Operação interrompida')
            print('INSTALLER_ERROR',repr(exc),flush=True)
    threading.Thread(target=execute,daemon=True).start()
    return dict(started=True)


def dispatch(request):
    global pending,confirmation
    action=request.get('action')
    if action=='status':
        with mutex:return dict(status)
    if status['busy']:raise ValueError('aguarde a operação terminar')
    if action=='hello':
        return dict(disks=available(),installed=(layout.PRIVATE_STATE/'state.json').exists(),
                    dashboards=MANIFEST['dashboards'],packages=len(MANIFEST['packages']),
                    files=len(MANIFEST['files']),sources=package_source.sources(),
                    ready=bool(SOURCE.get('firmware')) or not SOURCE.get('thin'))
    if action=='prepare':
        mode=request.get('mode');identity=request.get('identity')
        def prepare():
            global PAYLOAD,MANIFEST,pending,confirmation
            pending=None;confirmation=0
            PAYLOAD,MANIFEST,files=package_source.prepare(mode,identity,progress)
            SOURCE['firmware']=files
            return dict(ready=True,files=len(MANIFEST['files']),packages=len(MANIFEST['packages']))
        return job(prepare)
    if action=='plan':
        if SOURCE.get('thin') and not SOURCE.get('firmware'):raise ValueError('Prepare a coleção primeiro')
        row=next((r for r in available() if r.get('identity')==request.get('target') and r['available']),None)
        if row is None:raise ValueError('disco indisponível/trocado')
        pending=engine.plan(row['path'],SOURCE,PAYLOAD);confirmation=0
        return pending
    if action=='cancel':pending=None;confirmation=0;return dict(cancelled=True)
    if action=='confirm':
        if pending is None or request.get('token')!=pending['token']:raise ValueError('confirmação inválida')
        step=request.get('step')
        if step!=confirmation+1 or step not in (1,2):raise ValueError('ordem das confirmações inválida')
        confirmation=step
        return dict(confirmed=step)
    if action=='install':
        if pending is None or confirmation!=2 or request.get('token')!=pending['token']:
            raise ValueError('dupla confirmação ausente')
        prepared=pending;pending=None;confirmation=0
        return job(lambda:engine.install(prepared,SOURCE,PAYLOAD,progress))
    if action=='revert-emulator':
        if request.get('target')!='current' or not (layout.PRIVATE_STATE/'state.json').exists():
            raise ValueError('Reversão exige iniciar a manutenção do SSD instalado')
        def revert():
            from updater import Store
            storage=Store()
            with storage.lock():
                state=storage.state()
                if not state['active']:raise ValueError('O emulador original já está em uso')
                storage.rollback(state,'Reversão escolhida na manutenção')
                return dict(version=storage.current())
        return job(revert)
    if action=='repair':
        target,data=maintenance_target(request)
        return job(lambda:engine.repair_boot(target,data))
    if action=='maintenance-info':
        target,data=maintenance_target(request)
        manifest=engine.installed_manifest(target,data)
        return dict(dashboards=manifest['dashboards'],files=len(manifest['files']))
    if action=='dashboard':
        target,data=maintenance_target(request)
        return job(lambda:engine.choose_dashboard(target,data,engine.installed_manifest(target,data),request.get('name')))
    if action=='verify':
        target,data=maintenance_target(request)
        def verify():
            manifest=engine.installed_manifest(target,data)
            fd=os.open(target,os.O_RDONLY)
            try:
                volumes={drive:fatx.Volume(fd,*engine.drive_regions(data)[drive]) for drive in ('c','e','f')}
                result=dict(checked=0,modified=0,missing=0,examples=[])
                for index,item in enumerate(manifest['files']):
                    if index%250==0:progress('Comparando com o pacote original...',int(100*index/len(manifest['files'])))
                    path=item['path'];digest=hashlib.sha256();difference=None
                    try:
                        for block in volumes[path[0]].chunks(path[2:]):digest.update(block)
                        if digest.hexdigest()!=item['sha256']:difference='modified'
                    except FileNotFoundError:difference='missing'
                    result['checked']+=1
                    if difference:
                        result[difference]+=1
                        if len(result['examples'])<20:result['examples'].append(dict(path=path,kind=difference))
                # Configs, saves and dashboard updates legitimately change.
                # Comparison reports differences; it never restores/formats.
                return result
            finally:os.close(fd)
        return job(verify)
    if action in ('poweroff','reboot'):
        subprocess.run(['systemctl','--no-block',action],check=True)
        return dict(accepted=True)
    raise ValueError('ação desconhecida')


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(30)
        try:
            raw=self.rfile.readline(8193)
            if len(raw)>8192:raise ValueError('pedido grande demais')
            request=json.loads(raw)
            result=dict(ok=True,data=dispatch(request))
        except Exception as exc:result=dict(ok=False,error=str(exc))
        self.wfile.write((json.dumps(result,ensure_ascii=False)+'\n').encode())


if __name__=='__main__':
    PRIVATE.mkdir(mode=0o755,exist_ok=True);PRIVATE.chmod(0o755)
    sock=PRIVATE/'control.sock'
    if sock.exists():sock.unlink()
    with socketserver.UnixStreamServer(str(sock),Handler) as server:
        os.chown(sock,0,grp.getgrnam('console').gr_gid);sock.chmod(0o660)
        server.serve_forever()
