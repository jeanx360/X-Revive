"""Local privileged worker with a finite JSON protocol, no shell/eval input."""
import grp
import hashlib
import json
import os
from pathlib import Path
import socketserver
import threading
import subprocess
import time
import uuid
import traceback
import runtime_command
import operation_log
import re

import installer as engine
import standalone as layout
import fatx
import package_source
import live_disk
import boot_existing
import safe_live
import wifi
import live_target

PRIVATE=Path('/run/xrevive-installer')
PAYLOAD=Path('/utils/payload')
status={'busy':False,'message':'Pronto','progress':0}
mutex=threading.Lock()
control_mutex=threading.Lock()
request_context=threading.local()
cancel_event=threading.Event()
runtime_command.cancel_event=cancel_event
diagnostics=None
pending=None
confirmation=0
live_pending=None
live_confirmed=False
media_pending=None
media_confirmed=0


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
    if cancel_event.is_set():raise runtime_command.OperationCancelled('Operação cancelada')
    now=time.monotonic()
    with mutex:
        if status.get('message')==message and status.get('progress')==percent:return
        status.update(message=message,progress=percent,updated=now)
        status.setdefault('history',[]).append(dict(message=message,elapsed=round(now-status.get('started',now),1)))
        status['history']=status['history'][-20:]
        job_id=status.get('job_id')
    if diagnostics:diagnostics.record(job_id,message,percent)
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
        now=time.monotonic()
        cancel_event.clear()
        job_id=getattr(request_context,'operation_id',None)
        if not re.fullmatch('[a-f0-9]{32}',job_id or ''):job_id=uuid.uuid4().hex
        status.update(busy=True,message='Verificando...',progress=0,error=None,result=None,
                      job_id=job_id,
                      started=now,updated=now,history=[],cancelled=False,
                      cancellable=getattr(request_context,'action','') in ('media-start','live-start','sandbox-start','prepare'))
    def execute():
        if diagnostics:diagnostics.record(job_id,'Iniciando operação',0)
        try:
            result=function()
            with mutex:status.update(busy=False,result=result,message='Operação concluída',progress=100)
            if diagnostics:diagnostics.record(job_id,'Operação concluída',100)
        except runtime_command.OperationCancelled:
            with mutex:status.update(busy=False,cancelled=True,error=None,message='Operação cancelada; escolha outra opção.')
            if diagnostics:diagnostics.record(job_id,'Operação cancelada',None)
        except Exception as exc:
            with mutex:status.update(busy=False,error=str(exc),message='Operação interrompida')
            print('INSTALLER_ERROR',repr(exc),flush=True)
            if diagnostics:diagnostics.record(job_id,'Operação interrompida; veja a última etapa registrada',None)
            traceback.print_exc()
    threading.Thread(target=execute,daemon=True).start()
    return dict(started=True)


def dispatch(request):
    global pending,confirmation,live_pending,live_confirmed,media_pending,media_confirmed
    action=request.get('action')
    if action=='status':
        with mutex:
            now=time.monotonic()
            return dict(status,elapsed=round(now-status.get('started',now),1),
                        idle_seconds=round(now-status.get('updated',now),1),responding=True)
    if action=='task-cancel':
        with mutex:
            if not status['busy']:return dict(cancelled=False)
            if not status.get('cancellable') or request.get('operation_id')!=status.get('job_id'):
                raise ValueError('Esta etapa não pode ser interrompida; aguarde a gravação terminar.')
            cancel_event.set()
        return dict(cancelling=True)
    if status['busy']:raise ValueError('aguarde a operação terminar')
    if SOURCE.get('safe_live') and action not in ('hello','sandbox-start','live-launch','poweroff','reboot','wifi-status','wifi-scan','wifi-connect','wifi-disconnect'):
        raise ValueError('LIVE seguro: acesso aos discos físicos bloqueado; use apenas o HDD virtual')
    if (live_disk.PRIVATE/'session.json').exists() and action not in ('hello','live-launch','poweroff','reboot','wifi-status','wifi-scan','wifi-connect','wifi-disconnect'):
        raise ValueError('Sessão LIVE preparada; reinicie para escolher outra operação')
    if action=='hello':
        return dict(disks=[] if SOURCE.get('safe_live') else available(),installed=(layout.PRIVATE_STATE/'state.json').exists(),
                    dashboards=MANIFEST['dashboards'],packages=len(MANIFEST['packages']),
                    files=len(MANIFEST['files']),sources=package_source.sources(),
                    safe_live=bool(SOURCE.get('safe_live')),live_images=safe_live.images(),
                    ready=bool(SOURCE.get('firmware')) or not SOURCE.get('thin'))
    if action=='wifi-status':return wifi.call('status')
    if action=='media-disks':
        if (layout.PRIVATE_STATE/'state.json').exists():raise ValueError('LIVE exige boot pelo pendrive')
        return dict(disks=live_target.disks(SOURCE))
    if action=='media-plan':
        if (layout.PRIVATE_STATE/'state.json').exists():raise ValueError('LIVE exige boot pelo pendrive')
        row=next((r for r in live_target.disks(SOURCE) if r.get('identity')==request.get('target') and r['available']),None)
        if row is None:raise ValueError('Disco indisponível/trocado; atualize a lista')
        mode=request.get('mode');identity=request.get('identity');access=request.get('access')
        if access not in ('protected','write') or mode not in ('online','offline','hdd'):raise ValueError('Escolha LIVE inválida')
        if mode=='offline':package_source.media_source.selected(package_source.USER,identity)
        pending=None;confirmation=0;live_pending=None;live_confirmed=False;media_confirmed=0
        media_pending=live_target.plan(row['path'],SOURCE)
        media_pending.update(access=access,media=dict(mode=mode,identity=identity))
        return media_pending
    if action=='media-confirm':
        if media_pending is None or request.get('token')!=media_pending['token'] or media_pending['access']!='write':raise ValueError('Confirmação de escrita inválida')
        step=request.get('step')
        if type(step) is not int or step not in (1,2) or step!=media_confirmed+1:raise ValueError('Ordem das confirmações inválida')
        live_target.check(media_pending,SOURCE);media_confirmed=step
        return dict(confirmed=step)
    if action=='media-start':
        if media_pending is None or request.get('token')!=media_pending['token']:raise ValueError('Seleção LIVE inválida')
        if media_pending['access']=='write' and media_confirmed!=2:raise ValueError('Dupla confirmação de acesso ao HDD ausente')
        prepared=media_pending;media_pending=None;media_confirmed=0
        def start_media():
            progress('Conferindo disco selecionado...' if prepared['media']['mode']=='hdd' else 'Conferindo mídia e disco selecionado...',5)
            result=live_target.prepare(prepared,SOURCE,prepared['access'],prepared['media'],progress)
            try:live_disk.configure(progress=progress)
            except Exception:
                live_disk.abort();raise
            return result
        return job(start_media)
    if action in ('wifi-scan','wifi-connect','wifi-disconnect'):
        def wireless():
            progress('Conectando à rede Wi-Fi...' if action=='wifi-connect' else 'Verificando redes Wi-Fi...',10)
            if action=='wifi-connect':return wifi.call('connect',identity=request.get('identity'),password=request.get('password',''))
            return wifi.call('scan' if action=='wifi-scan' else 'disconnect')
        return job(wireless)
    if action=='sandbox-start':
        if (layout.PRIVATE_STATE/'state.json').exists():raise ValueError('LIVE Rocky5 exige boot pelo pendrive')
        pending=None;confirmation=0;live_pending=None;live_confirmed=False;media_pending=None;media_confirmed=0
        def sandbox():
            result=safe_live.prepare(SOURCE,request.get('mode'),request.get('identity'),progress)
            try:live_disk.configure(progress=progress)
            except Exception:
                live_disk.abort();raise
            return result
        return job(sandbox)
    if action=='live-disks':
        if (layout.PRIVATE_STATE/'state.json').exists():raise ValueError('LIVE exige boot pelo pendrive')
        return dict(disks=live_disk.disks(SOURCE['device']))
    if action=='live-plan':
        if (layout.PRIVATE_STATE/'state.json').exists():raise ValueError('LIVE exige boot pelo pendrive')
        row=next((r for r in live_disk.disks(SOURCE['device']) if r.get('identity')==request.get('target') and r['available']),None)
        if row is None:raise ValueError('HDD Xbox indisponível/trocado')
        pending=None;confirmation=0;live_confirmed=False;media_pending=None;media_confirmed=0
        live_pending=live_disk.plan(row['path'],SOURCE)
        return live_pending
    if action=='live-boot-confirm':
        if live_pending is None or request.get('token')!=live_pending['token']:raise ValueError('Confirmação LIVE inválida')
        if not live_pending['boot']['available']:raise ValueError(live_pending['boot']['message'])
        step=request.get('step')
        if step not in (1,2) or step!=live_confirmed+1:raise ValueError('Ordem das confirmações de boot inválida')
        live_confirmed=step
        return dict(confirmed=step)
    if action=='live-boot-cancel':
        if live_pending is None or request.get('token')!=live_pending['token']:raise ValueError('Seleção LIVE inválida')
        live_confirmed=False
        return dict(cancelled=True)
    if action=='live-boot-prepare':
        if live_pending is None or request.get('token')!=live_pending['token'] or live_confirmed!=2:
            raise ValueError('Dupla confirmação do boot ausente')
        prepared=live_pending;live_pending=None;live_confirmed=False
        def prepare_boot():
            live_disk.check_plan(prepared,SOURCE)
            live_target.unlock(prepared['device'],SOURCE)
            try:return boot_existing.prepare(prepared,SOURCE,progress)
            finally:live_target.relock(SOURCE)
        return job(prepare_boot)
    if action=='live-start':
        if live_pending is None or request.get('token')!=live_pending['token']:raise ValueError('Seleção LIVE inválida')
        mode=request.get('mode','protected')
        if mode!='protected':raise ValueError('LIVE apenas inicia, sem gravar no HDD')
        prepared=live_pending;live_pending=None;live_confirmed=False
        def start_live():
            progress('Conferindo HDD e preparando sessão LIVE...',10)
            result=live_disk.prepare(prepared,SOURCE,mode,progress=progress)
            try:
                live_disk.configure(progress=progress)
            except Exception:
                live_disk.abort()
                raise
            return result
        return job(start_live)
    if action=='live-launch':
        if not (live_disk.PRIVATE/'session.json').exists():raise ValueError('Sessão LIVE ausente')
        subprocess.run(['systemctl','--no-block','start','console-live-launch.service'],check=True)
        return dict(accepted=True)
    if action=='prepare':
        mode=request.get('mode');identity=request.get('identity')
        def prepare():
            global PAYLOAD,MANIFEST,pending,confirmation,live_pending,live_confirmed,media_pending,media_confirmed
            pending=None;confirmation=0;live_pending=None;live_confirmed=False;media_pending=None;media_confirmed=0
            PAYLOAD,MANIFEST,files=package_source.prepare(mode,identity,progress)
            SOURCE['firmware']=files
            return dict(ready=True,files=len(MANIFEST['files']),packages=len(MANIFEST['packages']))
        return job(prepare)
    if action=='plan':
        live_pending=None;live_confirmed=False;media_pending=None;media_confirmed=0
        if SOURCE.get('thin') and not SOURCE.get('firmware'):raise ValueError('Prepare a coleção primeiro')
        row=next((r for r in available() if r.get('identity')==request.get('target') and r['available']),None)
        if row is None:raise ValueError('disco indisponível/trocado')
        pending=engine.plan(row['path'],SOURCE,PAYLOAD);confirmation=0
        return pending
    if action=='cancel':
        pending=None;confirmation=0;live_pending=None;live_confirmed=False;media_pending=None;media_confirmed=0
        return dict(cancelled=True)
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
        def install():
            if engine.info(prepared['device']['path'],allow_readonly=True)!=prepared['device']:raise ValueError('Disco mudou')
            live_target.unlock(prepared['device'],SOURCE)
            try:return engine.install(prepared,SOURCE,PAYLOAD,progress)
            finally:live_target.relock(SOURCE)
        return job(install)
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
        def repair():
            external=request.get('target')!='current'
            if external:live_target.unlock(engine.info(target,allow_readonly=True),SOURCE)
            try:return engine.repair_boot(target,data,source=SOURCE if external else None,progress=progress)
            finally:
                if external:live_target.relock(SOURCE)
        return job(repair)
    if action=='maintenance-info':
        try:
            target,data=maintenance_target(request)
            manifest=engine.installed_manifest(target,data)
        except (ValueError,OSError,subprocess.SubprocessError):
            # An Xbox HDD given a PC boot area need not have our application
            # inventory. Boot repair and LIVE do not depend on that inventory.
            row=next((r for r in available() if r.get('identity')==request.get('target') and r['available']),None)
            if row is None:raise
            live_pending=live_disk.plan(row['path'],SOURCE)
            live_confirmed=False;pending=None;confirmation=0;media_pending=None;media_confirmed=0
            return dict(native=True,plan=live_pending)
        return dict(dashboards=manifest['dashboards'],files=len(manifest['files']))
    if action=='dashboard':
        target,data=maintenance_target(request)
        def dashboard():
            manifest=engine.installed_manifest(target,data)
            external=request.get('target')!='current'
            if external:live_target.unlock(engine.info(target,allow_readonly=True),SOURCE)
            try:return engine.choose_dashboard(target,data,manifest,request.get('name'))
            finally:
                if external:live_target.relock(SOURCE)
        return job(dashboard)
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
            request_context.operation_id=request.get('operation_id')
            request_context.action=request.get('action')
            if request.get('action') in ('status','task-cancel'):data=dispatch(request)
            else:
                with control_mutex:data=dispatch(request)
            result=dict(ok=True,data=data)
        except Exception as exc:result=dict(ok=False,error=str(exc))
        self.wfile.write((json.dumps(result,ensure_ascii=False)+'\n').encode())


class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
    daemon_threads=True


if __name__=='__main__':
    diagnostics=operation_log.Writer()
    PRIVATE.mkdir(mode=0o755,exist_ok=True);PRIVATE.chmod(0o755)
    sock=PRIVATE/'control.sock'
    if sock.exists():sock.unlink()
    with Server(str(sock),Handler) as server:
        os.chown(sock,0,grp.getgrnam('console').gr_gid);sock.chmod(0o660)
        server.serve_forever()
