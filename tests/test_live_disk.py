import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'cartucho/overlay/usr/local/lib/console'
sys.path.insert(0,str(LIB))
import live_disk as live
import fatx
import standalone


def native_image(path,explicit=False,extended=False):
    with path.open('xb') as out:out.truncate(9*1024**3 if extended else 8*1024**3)
    regions=list(standalone.RETAIL)
    if extended:regions.append(('F:',standalone.F_OFFSET,path.stat().st_size-standalone.F_OFFSET))
    with tempfile.TemporaryDirectory() as tmp,path.open('r+b') as out:
        source=Path(tmp);(source/'sentinel.txt').write_text('existing Xbox data')
        for _,start,size in regions:fatx.format_tree(out.fileno(),start,size,source)
        if explicit:
            first=bytearray(512);first[:16]=standalone.PARTINFO
            for i,(name,start,size) in enumerate(regions):
                struct.pack_into('<16sIIII',first,48+i*32,name.encode(),0x80000000,start//512,size//512,0)
            os.pwrite(out.fileno(),first,0)
    return regions


def sampled_hash(path,regions):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        h.update(stream.read(4096))
        for _,offset,size in regions:
            stream.seek(offset);h.update(stream.read(2*1024**2))
        stream.seek(-4096,2);h.update(stream.read())
    return h.hexdigest()


class LiveDiskTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.image=self.root/'native.img';self.regions=native_image(self.image)
        self.source={'device':str(self.root/'usb.img')}
    def tearDown(self):self.tmp.cleanup()

    def test_retail_8gb_detected_without_writes_and_usb_refused(self):
        before=sampled_hash(self.image,self.regions);stamp=self.image.stat().st_mtime_ns
        p=live.plan(self.image,self.source,qa=True)
        self.assertEqual(p['table'],'retail');self.assertEqual(len(p['regions']),5)
        self.assertEqual(p['device']['bytes'],8*1024**3)
        self.assertEqual(live.check_plan(p,self.source)['metadata_sha256'],p['metadata_sha256'])
        self.assertEqual(sampled_hash(self.image,self.regions),before)
        self.assertEqual(self.image.stat().st_mtime_ns,stamp)
        with self.assertRaisesRegex(ValueError,'boot bloqueado'):
            live.plan(self.image,{'device':str(self.image)},qa=True)
        # Retail HDDs need ~8.004 GB, not the installer's 32 GiB minimum.
        with self.image.open('r+b') as out:out.truncate(standalone.F_OFFSET)
        self.assertEqual(live.inspect(self.image,qa=True)['device']['bytes'],8004132864)

    def test_partinfo_f_bounds_and_overlap(self):
        image=self.root/'extended.img';native_image(image,explicit=True,extended=True)
        p=live.plan(image,self.source,qa=True)
        self.assertEqual([r['drive'] for r in p['regions']],['e','c','x','y','z','f'])
        with image.open('r+b') as out:
            out.seek(48+5*32+20);out.write(struct.pack('<I',standalone.RETAIL[1][1]//512))
        with self.assertRaisesRegex(ValueError,'sobrepostas'):live.inspect(image,qa=True)

    def test_pc_headers_do_not_block_valid_fatx_but_plain_pc_and_bad_root_are_refused(self):
        with self.image.open('r+b') as out:out.seek(512);out.write(b'EFI PART')
        self.assertEqual(live.inspect(self.image,qa=True)['table'],'retail')
        with self.image.open('r+b') as out:
            out.seek(512);out.write(bytes(8));out.seek(510);out.write(b'\x55\xaa')
        self.assertEqual(live.inspect(self.image,qa=True)['xbox_bytes'],standalone.F_OFFSET)
        with self.image.open('r+b') as out:
            out.seek(510);out.write(bytes(2));out.seek(standalone.RETAIL[1][1]+12);out.write(bytes(4))
        with self.assertRaisesRegex(ValueError,'Raiz FATX'):live.inspect(self.image,qa=True)
        with self.image.open('r+b') as out:
            out.seek(0);out.write(standalone.PARTINFO)
        with self.assertRaisesRegex(ValueError,'incompleta'):live.inspect(self.image,qa=True)
        pc=self.root/'pc.img'
        with pc.open('xb') as out:out.truncate(8*1024**3);out.seek(510);out.write(b'\x55\xaa')
        with self.assertRaisesRegex(ValueError,'FATX ausente'):live.inspect(pc,qa=True)

    def test_cache_missing_does_not_block_live_and_smaller_clusters_are_readable(self):
        with self.image.open('r+b') as out:
            os.pwrite(out.fileno(),bytes(4096),standalone.RETAIL[2][1])
            start,size=standalone.RETAIL[1][1:];cluster=4096
            fat_bytes=(((size//cluster+1)*4+4095)//4096)*4096
            header=struct.pack('<4sIII',b'FATX',1,8,1).ljust(4096,b'\xff')
            os.pwrite(out.fileno(),header,start)
            os.pwrite(out.fileno(),b'\xff'*4,start+4096+4)
            os.pwrite(out.fileno(),b'\xff'*4096,start+4096+fat_bytes)
        result=live.inspect(self.image,qa=True)
        self.assertEqual(next(r for r in result['regions'] if r['drive']=='c')['cluster_bytes'],4096)
        self.assertIn('warning',next(r for r in result['regions'] if r['drive']=='x'))

    def test_hot_swap_resize_metadata_change_refused(self):
        p=live.plan(self.image,self.source,qa=True)
        with self.image.open('r+b') as out:
            out.seek(standalone.RETAIL[0][1]+4);out.write(b'abcd')
        with self.assertRaisesRegex(ValueError,'mudou'):live.check_plan(p,self.source)
        p=live.plan(self.image,self.source,qa=True)
        self.image.rename(self.root/'removed.img');native_image(self.image)
        with self.assertRaisesRegex(ValueError,'mudou'):live.check_plan(p,self.source)

    def test_real_hybrid_and_missing_mbr_keep_live_bounded_to_xbox(self):
        image=self.root/'hybrid.img';native_image(image,explicit=True,extended=True)
        data=dict(schema=1,experimental=True,xbox_bytes=10*1024**3,disk_id='12345678',build_id='test',source_sha256='test')
        end=data['xbox_bytes']
        for name in ('system','console','cache','utils'):
            data[name]=dict(offset=end,bytes=1024**2);end+=1024**2
        data['image_bytes']=end+1024**2
        with image.open('r+b') as out:
            out.truncate(data['image_bytes']);first=os.pread(out.fileno(),512,0)
            os.pwrite(out.fileno(),standalone.repair_sector(first,data),0)
            os.pwrite(out.fileno(),standalone.footer(data),data['image_bytes']-standalone.FOOTER_BYTES)
        before=sampled_hash(image,standalone.RETAIL);stamp=image.stat().st_mtime_ns
        result=live.plan(image,self.source,qa=True)
        self.assertEqual(result['xbox_bytes'],10*1024**3)
        self.assertEqual(result['boot']['kind'],'repair');self.assertTrue(result['boot']['available'])
        self.assertEqual(result['installation'],data)
        self.assertEqual(sampled_hash(image,standalone.RETAIL),before)
        self.assertEqual(image.stat().st_mtime_ns,stamp)
        with image.open('r+b') as out:os.pwrite(out.fileno(),bytes(72),440)
        self.assertEqual(live.inspect(image,qa=True)['installation'],data)

    def test_boot_offer_never_uses_free_clusters_or_nonzero_tail(self):
        import boot_existing
        image=self.root/'space.img';native_image(image,explicit=True,extended=True)
        with image.open('r+b') as out:out.truncate(16*1024**3)
        source=dict(self.source,regions={n:dict(offset=0,bytes=m*1024**2)
            for n,m in [('system',2048),('console',128),('cache',1024),('utils',64)]},build_id='test',source_sha256='test')
        p=live.plan(image,source,qa=True)
        self.assertTrue(p['boot']['available']);self.assertEqual(p['boot']['kind'],'append')
        self.assertEqual(p['boot']['layout']['native_regions'][-1]['offset'],standalone.F_OFFSET)
        with self.image.open('r+b') as out:out.truncate(10*1024**3)
        self.assertFalse(live.plan(self.image,source,qa=True)['boot']['available'])
        small=self.root/'tail';small.write_bytes(bytes(4096)+b'existing data')
        before=small.read_bytes();stamp=small.stat().st_mtime_ns
        with small.open('rb') as stream:
            boot_existing.check_empty(stream.fileno(),0,4096)
            with self.assertRaisesRegex(ValueError,'contém dados'):boot_existing.check_empty(stream.fileno(),0,small.stat().st_size)
        self.assertEqual(small.read_bytes(),before);self.assertEqual(small.stat().st_mtime_ns,stamp)
        with image.open('r+b') as out:
            os.pwrite(out.fileno(),b'\x55\xaa',510)
            os.pwrite(out.fileno(),b'\x07',450)
        p=live.plan(image,source,qa=True)
        self.assertEqual(p['table'],'PARTINFO')
        self.assertTrue(p['boot']['available'])  # a stale type byte is not a partition
        with image.open('r+b') as out:
            os.pwrite(out.fileno(),struct.pack('<II',p['boot']['layout']['system']['offset']//512,2048),454)
        p=live.plan(image,source,qa=True)
        self.assertFalse(p['boot']['available']);self.assertIn('coexistentes',p['boot']['message'])

    @unittest.skipUnless(shutil.which('qemu-img') and shutil.which('qemu-io'),'QEMU tools optional')
    def test_real_overlay_write_does_not_modify_base(self):
        base=self.root/'backing.raw';base.write_bytes(bytes(1024**2))
        before=hashlib.sha256(base.read_bytes()).digest()
        overlay=self.root/'changes.qcow2';live.create_overlay(base,overlay)
        subprocess.run(['qemu-io','-f','qcow2','-c','write -P 0x5a 4096 512',str(overlay)],check=True,capture_output=True)
        subprocess.run(['qemu-io','-f','qcow2','-r','-c','read -P 0x5a 4096 512',str(overlay)],check=True,capture_output=True)
        self.assertEqual(hashlib.sha256(base.read_bytes()).digest(),before)
        data=json.loads(subprocess.check_output(['qemu-img','info','--output=json',str(overlay)],text=True))
        self.assertEqual(data['backing-filename-format'],'raw')

    def test_live_never_writes_and_boot_requires_separate_double_confirmation(self):
        # Exercise the actual dispatcher without starting a privileged server.
        tree=ast.parse((LIB/'installer-worker.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dispatch')
        private=self.root/'private';private.mkdir()
        pending={'token':'live-token','device':{'path':str(self.image)},'boot':{'available':True}}
        env=dict(Path=Path,status={'busy':False},mutex=threading.Lock(),pending=None,confirmation=0,
                 live_pending=pending,live_confirmed=False,SOURCE=self.source,
                 live_disk=types.SimpleNamespace(PRIVATE=private),job=lambda function:dict(started=True))
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<dispatcher>','exec'),env)
        call=env['dispatch']
        with self.assertRaisesRegex(ValueError,'sem gravar'):call(dict(action='live-start',token='live-token',mode='normal'))
        with self.assertRaisesRegex(ValueError,'inválida'):call(dict(action='live-boot-confirm',token='install-token',step=1))
        self.assertFalse(env['live_confirmed'])
        with self.assertRaisesRegex(ValueError,'Dupla'):call(dict(action='live-boot-prepare',token='live-token'))
        with self.assertRaisesRegex(ValueError,'Ordem'):call(dict(action='live-boot-confirm',token='live-token',step=2))
        call(dict(action='live-boot-confirm',token='live-token',step=1))
        call(dict(action='live-boot-cancel',token='live-token'));self.assertFalse(env['live_confirmed'])
        call(dict(action='live-boot-confirm',token='live-token',step=1))
        call(dict(action='live-boot-confirm',token='live-token',step=2))
        self.assertEqual(call(dict(action='live-boot-prepare',token='live-token')),dict(started=True))
        self.assertIsNone(env['live_pending']);self.assertFalse(env['live_confirmed'])
        with self.assertRaisesRegex(ValueError,'inválida'):call(dict(action='live-start',token='live-token',mode='protected'))
        env['live_pending']=pending;call(dict(action='cancel'))
        self.assertIsNone(env['live_pending'])
        (private/'session.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Sessão LIVE'):call(dict(action='install',token='anything'))

    def test_ui_live_and_optional_boot_selection_and_cancellation(self):
        tree=ast.parse((LIB/'installer-ui.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='UI')
        calls=[];env=dict(rpc=lambda action,**kw:calls.append((action,kw)))
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'<ui>','exec'),env)
        ui=object.__new__(env['UI']);ui.boot={'installed':False};ui.state='welcome'
        def call(action,success=None,failure=None,**args):
            result=env['rpc'](action,**args)
            if success:success(result)
        ui.call=call
        ui.selected=2;ui.go=lambda state:setattr(ui,'state',state)
        self.assertIn('LIVE',ui.options()[0])
        ui.plan={'token':'token','boot':{'available':True}}
        ui.state='live-choice';ui.selected=1;ui.accept()
        self.assertEqual(ui.state,'live-boot-confirm1');self.assertEqual(calls,[])
        ui.back();self.assertEqual(ui.state,'live-choice')
        ui.back();self.assertEqual(ui.state,'live-disks')
        self.assertEqual(calls,[('live-boot-cancel',{'token':'token'}),('cancel',{})])

    def test_live_identity_stays_on_usb_and_initial_write_does_not_replace(self):
        run=self.root/'run';run.mkdir();private=self.root/'private';private.mkdir()
        user=self.root/'user';storage=user/'live'/'disk-id';storage.mkdir(parents=True)
        (private/'session.json').write_text(json.dumps(dict(storage=str(storage))))
        first=bytes(range(256));second=first[::-1]
        (run/'eeprom.bin').write_bytes(first)
        with patch.object(live,'PRIVATE',private),patch.object(live,'USER',user),patch.object(live.os.path,'ismount',return_value=True),patch.object(live.subprocess,'run'):
            live.save(run,initial=True)
            dest=storage/'firmware/xbox/eeprom.bin';self.assertEqual(dest.read_bytes(),first)
            (run/'eeprom.bin').write_bytes(second);live.save(run,initial=True)
            self.assertEqual(dest.read_bytes(),first)
            live.save(run,initial=False);self.assertEqual(dest.read_bytes(),second)
        self.assertEqual((run/'eeprom.bin').read_bytes(),second)


if __name__=='__main__':unittest.main()
