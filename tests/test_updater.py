import base64
import functools
import http.server
import importlib.util
import io
import json
from pathlib import Path
import shutil
import socketserver
import subprocess
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('update_test',ROOT/'cartucho/overlay/usr/local/lib/console/updater.py')
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
spec=importlib.util.spec_from_file_location('held_update_test',ROOT/'plataformas/xbox/tools/held.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
        self.channel=self.path/'channel';self.channel.mkdir()
        self.server=socketserver.TCPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(self.channel)))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_address[1])
        subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(self.path/'key')],check=True,capture_output=True)
        self.public=subprocess.check_output(['openssl','pkey','-in',str(self.path/'key'),'-pubout'],text=True)
        self.config=self.path/'config.json';u.atomic(self.config,{'public_key_pem':self.public,'allow_http':True,'manifest_url':self.url+'/latest.json'})
        self.store=u.Store(self.path/'updates',self.config,require_mount=False)
        self.protected=self.path/'xbox-data';self.protected.write_bytes(b'games saves EEPROM dashboard FATX')
    def tearDown(self):
        self.assertEqual(self.protected.read_bytes(),b'games saves EEPROM dashboard FATX')
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def sign(self,data):
        (self.path/'data').write_bytes(u.canonical(data))
        subprocess.run(['openssl','pkeyutl','-sign','-rawin','-inkey',str(self.path/'key'),'-in',str(self.path/'data'),'-out',str(self.path/'sig')],check=True,capture_output=True)
        return {'manifest':data,'signature':base64.b64encode((self.path/'sig').read_bytes()).decode()}
    def release(self,seq=1,version='0.8.139-xrevive-smc2',extra=None):
        binary=Path(shutil.which('true')).read_bytes()
        entries={'xemu':binary,'LICENSE.txt':b'GPL','PROVENANCE.json':json.dumps({'version':version}).encode(),'smc.patch':b'SMC','menu.patch':b'Start+UP'}
        if extra:entries.update(extra)
        package=self.channel/'package.tar.gz'
        with tarfile.open(package,'w:gz') as tar:
            for name,content in entries.items():
                member=tarfile.TarInfo(name);member.size=len(content);tar.addfile(member,io.BytesIO(content))
        data=dict(schema=1,runtime_abi=u.ABI,version=version,sequence=seq,sha256=u.digest(package),bytes=package.stat().st_size,
            unpacked_bytes=sum(map(len,entries.values())),binary_sha256=__import__('hashlib').sha256(binary).hexdigest(),
            upstream_commit='a'*40,smc_patch_sha256=__import__('hashlib').sha256(entries['smc.patch']).hexdigest(),
            menu_patch_sha256=__import__('hashlib').sha256(entries['menu.patch']).hexdigest(),
            package_url=self.url+'/package.tar.gz',changelog='Correções gráficas\nDVD e controles preservados.')
        u.atomic(self.channel/'latest.json',self.sign(data));self.store.check();return data
    def test_unsigned_change_rejected(self):
        self.release();envelope=u.read(self.channel/'latest.json');envelope['manifest']['version']='0.8.999-xrevive-smc2'
        u.atomic(self.channel/'latest.json',envelope)
        with self.assertRaisesRegex(ValueError,'Assinatura'):self.store.check()
        self.assertIsNone(self.store.state()['active'])
    def test_install_health_and_previous_version_recovery(self):
        first=self.release();self.store.apply(first['sha256'],'boot1');self.store.launch('boot1');self.store.healthy(first['sha256'])
        second=self.release(2,'0.8.140-xrevive-smc2');self.store.apply(second['sha256'],'boot1')
        self.assertEqual(self.store.launch('boot1')['version'],'0.8.140-xrevive-smc2')
        self.store.recover('boot2')
        self.assertEqual(self.store.current(),'0.8.139-xrevive-smc2')
        self.assertIn(second['sha256'],self.store.state()['failed'])
    def test_repeated_start_failure_falls_back_without_reboot(self):
        data=self.release();self.store.apply(data['sha256'],'boot');self.store.launch('boot');self.store.launch('boot')
        self.assertEqual(self.store.launch('boot')['app'],'/opt/xemu/AppRun')
        self.assertIsNone(self.store.state()['pending'])
    def test_healthy_update_survives_new_boot_and_replay_rejected(self):
        data=self.release();self.store.apply(data['sha256'],'boot');self.store.launch('boot');self.store.healthy(data['sha256'])
        self.store.recover('next-boot');self.assertEqual(self.store.current(),data['version']);self.assertIsNone(self.store.candidate())
    def test_corrupt_active_binary_uses_immutable_base(self):
        data=self.release();self.store.apply(data['sha256'],'boot');self.store.healthy(data['sha256'])
        (self.store.root/'versions'/data['sha256']/'xemu').write_bytes(b'bad')
        self.store.recover('next');self.assertEqual(self.store.current(),u.BASE)
    def test_truncated_download_preserves_current(self):
        data=self.release();(self.channel/'package.tar.gz').write_bytes(b'partial')
        with self.assertRaisesRegex(ValueError,'incompleto'):self.store.apply(data['sha256'],'boot')
        self.assertEqual(self.store.current(),u.BASE)
        self.assertFalse(list(self.store.root.glob('.download-*')))
    def test_archive_path_escape_rejected_even_with_valid_signature(self):
        data=self.release(extra={'../escape':b'bad'})
        with self.assertRaisesRegex(ValueError,'caminhos'):self.store.apply(data['sha256'],'boot')
        self.assertFalse((self.store.root/'escape').exists());self.assertEqual(self.store.current(),u.BASE)
    def test_insufficient_space_does_not_activate(self):
        data=self.release()
        with patch.object(shutil,'disk_usage',return_value=type('Space',(),{'free':1})()):
            with self.assertRaisesRegex(ValueError,'Espaço'):self.store.apply(data['sha256'],'boot')
        self.assertIsNone(self.store.state()['active'])
    def test_incompatible_signed_manifest_rejected(self):
        data=self.release();data['runtime_abi']='other-linux';u.atomic(self.channel/'latest.json',self.sign(data))
        with self.assertRaisesRegex(ValueError,'incompatível'):self.store.check()
    def test_offer_identity_must_match_confirmation(self):
        self.release()
        with self.assertRaisesRegex(ValueError,'mudou'):self.store.apply('b'*64,'boot')
    def test_production_rejects_http_and_file(self):
        for url in [self.url,'file:///tmp/release','https://user:pass@example.org/update']:
            with self.assertRaises(ValueError):u.Transport().validate(url)
    def test_offline_preserves_verified_cached_offer(self):
        data=self.release()
        with patch.object(self.store.transport,'fetch',side_effect=OSError('offline')):
            with self.assertRaises(OSError):self.store.check()
        self.assertEqual(self.store.candidate()['sha256'],data['sha256'])
    def test_keyboard_u_controller_y_and_recovery_priority(self):
        for keys,wanted in [({'k':{22}},'update'),({'pad':{308}},'update'),({'k':{22},'pad':{314,315}},'installer'),({'k':{19,22}},'installer')]:
            with patch.object(h,'held',lambda dev,combo=h.COMBO:set(combo)<=keys.get(dev,set())):
                self.assertEqual(h.selection(['k','pad']),wanted)
    def test_atomic_pointer_failure_leaves_base_bootable(self):
        data=self.release();original=u.atomic
        def interrupted(path,value):
            if Path(path).name=='state.json':raise OSError('power interruption before switch')
            return original(path,value)
        with patch.object(u,'atomic',interrupted):
            with self.assertRaises(OSError):self.store.apply(data['sha256'],'boot')
        self.assertEqual(self.store.current(),u.BASE)
        self.store.recover('next');self.assertEqual(self.store.launch('next')['app'],'/opt/xemu/AppRun')


if __name__=='__main__':unittest.main()
