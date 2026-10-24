"""Root boot/update coordinator; the unprivileged UI has a finite RPC API."""
import grp
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

from updater import Store, atomic, read

RUN = Path('/run/xrevive-update')
CONFIG = '/etc/xrevive-updates.json'
BOOT_ID = Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def store(): return Store(config=CONFIG)


def notice():
    try:
        storage = store()
        with storage.lock(): result = storage.check()
    except Exception as exc:
        result = {'available':False, 'message':str(exc)}
        try:
            data = storage.candidate()
            if data: result.update(available=True, version=data['version'])
        except Exception: pass
    atomic(RUN/'notice.json', result)


def prepare():
    RUN.mkdir(mode=0o755, exist_ok=True)
    try:
        storage = store()
        with storage.lock(): storage.recover(BOOT_ID)
    except Exception as exc: print('update: usando versão da imagem:', exc, flush=True)
    # timeout bounds DNS resolution too. Runs in parallel with the 8 s key window.
    subprocess.Popen(['timeout','--kill-after=1','7',sys.executable,__file__,'check'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def launch():
    choice = {'app':'/opt/xemu/AppRun', 'version':'0.8.138-xrevive-smc2', 'identity':None}
    try:
        storage = store()
        with storage.lock(): choice = storage.launch(BOOT_ID)
    except Exception as exc: print('update: fallback imutável:', exc, flush=True)
    atomic(RUN/'choice.json', choice)
    # The shell launcher reads only this root-owned file, not paths supplied by UI.
    (RUN/'app').write_text(choice['app']+'\n')
    os.chmod(RUN/'app', 0o644)


def serve():
    if not Path('/run/console/update').exists(): return
    storage = store(); status = {'phase':'ready', 'message':'', 'progress':0}
    finish = threading.Event(); operation = None
    def snapshot():
        data = None
        try: data = storage.candidate()
        except Exception: pass
        return dict(status, current=storage.current(), release=data,
                    channel=read(RUN/'notice.json', {}))
    def apply(expected):
        def progress(done, total): status.update(progress=int(done*100/total), message='Baixando atualização...')
        try:
            with storage.lock(): result = storage.apply(expected, BOOT_ID, progress)
            status.update(phase='complete', progress=100, message='Atualização instalada: '+result)
            time.sleep(2); finish.set()
        except Exception as exc: status.update(phase='error', message=str(exc))
    address = RUN/'control.sock'
    address.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(address)); os.chown(address, 0, grp.getgrnam('console').gr_gid)
        os.chmod(address, 0o660); listener.listen(4); listener.settimeout(.3)
        subprocess.run(['systemctl','--no-block','start','console-update-ui.service'], check=True)
        try:
            while not finish.is_set():
                try: client, _ = listener.accept()
                except socket.timeout:
                    # A crashed screen must not hold boot forever.
                    if operation is None and subprocess.run(['systemctl','is-failed','--quiet','console-update-ui.service']).returncode == 0:
                        finish.set()
                    continue
                with client:
                    client.settimeout(2)
                    try:
                        line = client.makefile('rb').readline(4097)
                        if len(line)>4096: raise ValueError('Pedido grande demais')
                        request = json.loads(line); action = request['action']
                        if action == 'status': result = snapshot()
                        elif action == 'apply':
                            if status['phase'] not in ('ready','error'): raise ValueError('Atualização já iniciada')
                            status.update(phase='downloading', progress=0, message='Preparando download...')
                            operation = threading.Thread(target=apply, args=(request['identity'],), daemon=True)
                            operation.start(); result = snapshot()
                        elif action == 'continue':
                            if status['phase']=='downloading': raise ValueError('Aguarde concluir a atualização')
                            finish.set(); result = {}
                        else: raise ValueError('Ação desconhecida')
                        response = {'ok':True, 'data':result}
                    except Exception as exc: response = {'ok':False, 'error':str(exc)}
                    client.sendall((json.dumps(response)+'\n').encode())
        finally:
            subprocess.run(['systemctl','stop','console-update-ui.service'], check=False)
            address.unlink(missing_ok=True)
            Path('/run/console/update').unlink(missing_ok=True)


def health():
    while True:
        try:
            storage = store(); state = storage.state(); pending = state['pending']
            if pending and pending['attempts']:
                age = time.monotonic()-pending['started']
                ready = read(RUN/'qmp-ready.json', {})
                choice = read(RUN/'choice.json', {})
                pid = ready.get('pid',0)
                if pid and time.monotonic()-ready.get('at',0)<10 and choice.get('identity') == state['active'] and age >= 30 and Path('/proc/'+str(pid)+'/exe').resolve() == Path(choice['app']):
                    with storage.lock(): storage.healthy(state['active'])
                    print('update: primeira inicialização confirmada', flush=True)
                elif age > 65:
                    subprocess.run(['systemctl','restart','console.service'], check=False)
        except Exception: pass
        time.sleep(1)


if __name__ == '__main__':
    {'prepare':prepare,'check':notice,'launch':launch,'serve':serve,'health':health}[sys.argv[1]]()
