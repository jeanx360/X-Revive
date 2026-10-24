"""Signed Xemu-only updates. Never opens an Xbox disk or changes firmware.

The immutable /opt version remains available even if CACHE is unavailable.
Only a root-owned directory on the mounted CACHE stores versions and state.
"""
import base64
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request

ABI = 'debian13-amd64-xrevive-smc2'
BASE = '0.8.138-xrevive-smc2'
MAX_PACKAGE = 96 * 1024**2
MAX_UNPACKED = 160 * 1024**2
FILES = {'xemu', 'LICENSE.txt', 'PROVENANCE.json', 'smc.patch', 'menu.patch'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.'+path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
        os.chmod(name, 0o644)
        os.replace(name, path)
        sync_dir(path.parent)
    finally:
        if os.path.exists(name): os.unlink(name)


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def read(path, default=None):
    try: return json.loads(Path(path).read_text())
    except FileNotFoundError: return default


def version(text):
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)-xrevive-smc2', text)
    if not match: raise ValueError('Versão X-Revive inválida')
    return tuple(map(int, match.groups()))


def verified(envelope, public_key):
    data = envelope['manifest']
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder/'data').write_bytes(canonical(data))
        (folder/'signature').write_bytes(base64.b64decode(envelope['signature'], validate=True))
        (folder/'key').write_text(public_key)
        result = subprocess.run(['openssl', 'pkeyutl', '-verify', '-pubin', '-inkey', str(folder/'key'),
            '-rawin', '-in', str(folder/'data'), '-sigfile', str(folder/'signature')],
            capture_output=True, timeout=5)
        if result.returncode: raise ValueError('Assinatura da atualização inválida')
    if data['schema'] != 1 or data['runtime_abi'] != ABI:
        raise ValueError('Atualização incompatível com este sistema')
    version(data['version'])
    for key in ('sha256', 'binary_sha256', 'upstream_commit', 'smc_patch_sha256', 'menu_patch_sha256'):
        size = 40 if key == 'upstream_commit' else 64
        if not re.fullmatch('[0-9a-f]{'+str(size)+'}', data[key]): raise ValueError('Proveniência inválida')
    if type(data['sequence']) is not int or data['sequence'] < 1: raise ValueError('Sequência inválida')
    if type(data['bytes']) is not int or not 0 < data['bytes'] <= MAX_PACKAGE: raise ValueError('Pacote grande demais')
    if type(data['unpacked_bytes']) is not int or not 0 < data['unpacked_bytes'] <= MAX_UNPACKED:
        raise ValueError('Conteúdo grande demais')
    if not isinstance(data['changelog'], str) or len(data['changelog']) > 12000:
        raise ValueError('Notas da versão inválidas')
    return data


class Transport:
    def __init__(self, allow_http=False): self.allow_http = allow_http
    def validate(self, url):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in (('https', 'http') if self.allow_http else ('https',)) or not parts.hostname or parts.username or parts.password:
            raise ValueError('Canal exige uma URL HTTPS válida')
        return url
    def open(self, url):
        transport = self
        class Redirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                transport.validate(newurl)
                return super().redirect_request(req, fp, code, msg, headers, newurl)
        opener = urllib.request.build_opener(Redirect())
        return opener.open(urllib.request.Request(self.validate(url), headers={'User-Agent':'X-Revive-Updater/1'}), timeout=8)
    def fetch(self, url, path, limit, progress=lambda *_: None):
        total = 0; started = time.monotonic()
        with self.open(url) as source, Path(path).open('xb') as target:
            while chunk := source.read1(256*1024):
                total += len(chunk)
                if total > limit or time.monotonic()-started > 300: raise ValueError('Download excedeu o limite')
                target.write(chunk); progress(total, limit)
            target.flush(); os.fsync(target.fileno())
        return total


class Store:
    def __init__(self, root='/var/cache/console/updates', config='/etc/xrevive-updates.json', require_mount=True):
        self.root = Path(root); self.config = read(config)
        if require_mount and not os.path.ismount('/var/cache/console'):
            raise ValueError('Área persistente de atualizações indisponível')
        self.root.mkdir(mode=0o755, parents=True, exist_ok=True)
        info = self.root.lstat()
        if self.root.is_symlink() or info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise ValueError('Diretório de atualizações não é confiável')
        self.transport = Transport(self.config.get('allow_http', False))
        self.key = self.config['public_key_pem']
    @contextlib.contextmanager
    def lock(self):
        with (self.root/'lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX); yield
    def state(self):
        return read(self.root/'state.json', dict(active=None, previous=None, pending=None, highwater=0, failed=[]))
    def save(self, state): atomic(self.root/'state.json', state)
    def manifest(self, identity, check_binary=True):
        if not re.fullmatch('[0-9a-f]{64}', identity): raise ValueError('Identidade inválida')
        folder = self.root/'versions'/identity
        data = verified(read(folder/'release.json'), self.key)
        if data['sha256'] != identity or (check_binary and digest(folder/'xemu') != data['binary_sha256']):
            raise ValueError('Emulador armazenado está corrompido')
        return data
    def current(self):
        state = self.state()
        return self.manifest(state['active'], check_binary=False)['version'] if state['active'] else BASE
    def candidate(self):
        data = verified(read(self.root/'available.json'), self.key)
        state = self.state()
        if (version(data['version']) < version(BASE) or data['sha256'] in state['failed']
            or data['sequence'] <= state['highwater'] or version(data['version']) < version(self.current())):
            return None
        return data
    def check(self):
        url = self.config.get('manifest_url', '')
        # Optional data-only mirror URL; the immutable public key stays authoritative.
        ports = Path('/console/config/ports.conf')
        if ports.is_file():
            for line in ports.read_text().splitlines():
                if line.startswith('updates_url='): url = line.split('=', 1)[1].strip()
        if not url: return {'message':'Canal de atualizações ainda não configurado', 'available':False}
        with tempfile.TemporaryDirectory(dir=self.root, prefix='.check-') as tmp:
            path = Path(tmp)/'manifest'
            self.transport.fetch(url, path, 64000)
            envelope = json.loads(path.read_text()); verified(envelope, self.key)
            atomic(self.root/'available.json', envelope)
        data = self.candidate()
        return {'available':bool(data), 'version':data['version'] if data else self.current()}
    def rollback(self, state, reason):
        failed = state['active']
        active = state['previous']
        if active:
            try: self.manifest(active)
            except (OSError, ValueError, KeyError, TypeError): active = None
        state.update(active=active, previous=None, pending=None, rollback=reason)
        if failed: state['failed'] = (state['failed'] + [failed])[-16:]
        self.save(state)
    def recover(self, boot_id):
        # Only abandoned private updater transactions, never shader/user data.
        for folder in self.root.iterdir():
            if re.fullmatch(r'\.(download|check)-[a-z0-9_]+', folder.name) and folder.is_dir() and not folder.is_symlink() and folder.stat().st_uid == os.geteuid():
                shutil.rmtree(folder)
        state = self.state()
        if state['pending'] and state['pending']['boot_id'] != boot_id:
            self.rollback(state, 'A versão anterior não concluiu a primeira inicialização')
        elif state['active']:
            try: self.manifest(state['active'])
            except (OSError, ValueError, KeyError, TypeError): self.rollback(state, 'Emulador armazenado inválido')
    def launch(self, boot_id):
        state = self.state()
        pending = state['pending']
        if pending:
            if pending['attempts'] >= 2:
                self.rollback(state, 'O emulador novo falhou ao iniciar duas vezes')
                state = self.state()
            else:
                pending.update(attempts=pending['attempts']+1, started=time.monotonic())
                self.save(state)
        identity = state['active']
        if identity: self.manifest(identity)
        app = str(self.root/'versions'/identity/'xemu') if identity else '/opt/xemu/AppRun'
        return {'app':app, 'version':self.current(), 'identity':identity}
    def healthy(self, identity):
        state = self.state()
        if state['active'] == identity and state['pending']:
            state['pending'] = None; self.save(state)
            keep = {state['active'], state['previous']}
            for folder in (self.root/'versions').iterdir():
                if re.fullmatch('[0-9a-f]{64}', folder.name) and folder.name not in keep and folder.is_dir() and not folder.is_symlink():
                    shutil.rmtree(folder)
            sync_dir(self.root/'versions')
    def apply(self, expected, boot_id, progress=lambda *_: None):
        data = self.candidate()
        if not data or data['sha256'] != expected: raise ValueError('A versão oferecida mudou; confira as notas novamente')
        needed = data['bytes'] + data['unpacked_bytes'] + 32*1024**2
        if shutil.disk_usage(self.root).free < needed: raise ValueError('Espaço insuficiente na área de atualizações')
        versions = self.root/'versions'; versions.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.root, prefix='.download-') as tmp:
            tmp = Path(tmp); package = tmp/'package.tar.gz'
            count = self.transport.fetch(data['package_url'], package, data['bytes'], progress)
            if count != data['bytes'] or digest(package) != expected: raise ValueError('Download incompleto ou checksum inválido')
            stage = tmp/'version'; stage.mkdir()
            total = 0; seen = set()
            with tarfile.open(package, 'r:gz') as archive:
                for member in archive:
                    if member.name not in FILES or not member.isfile() or member.name in seen:
                        raise ValueError('Pacote contém caminhos ou tipos proibidos')
                    seen.add(member.name); total += member.size
                    if total > data['unpacked_bytes']: raise ValueError('Conteúdo excedeu o tamanho declarado')
                    with archive.extractfile(member) as source, (stage/member.name).open('xb') as target:
                        shutil.copyfileobj(source, target); target.flush(); os.fsync(target.fileno())
                    os.chmod(stage/member.name, 0o755 if member.name == 'xemu' else 0o644)
            if seen != FILES or total != data['unpacked_bytes'] or digest(stage/'xemu') != data['binary_sha256']:
                raise ValueError('Conteúdo do pacote não confere')
            header = (stage/'xemu').read_bytes()[:20]
            if header[:5] != b'\x7fELF\x02' or header[18:20] != b'\x3e\x00': raise ValueError('Executável não é ELF x86-64')
            for name, key in [('smc.patch','smc_patch_sha256'), ('menu.patch','menu_patch_sha256')]:
                if digest(stage/name) != data[key]: raise ValueError('Patch não confere')
            libraries = subprocess.run(['ldd', str(stage/'xemu')], capture_output=True, text=True, timeout=10)
            if libraries.returncode or 'not found' in libraries.stdout: raise ValueError('Bibliotecas incompatíveis com este sistema')
            atomic(stage/'release.json', read(self.root/'available.json'))
            destination = versions/expected
            if destination.exists():
                if self.manifest(expected) != data: raise ValueError('Identidade de pacote já usada por outra versão')
            else:
                os.rename(stage, destination); sync_dir(versions)
            state = self.state()
            state.update(previous=state['active'], active=expected,
                highwater=data['sequence'], pending={'boot_id':boot_id, 'attempts':0, 'started':time.monotonic()})
            self.save(state)
        return data['version']
