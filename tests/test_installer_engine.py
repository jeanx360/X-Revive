import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'cartucho/overlay/usr/local/lib/console'
sys.path.insert(0,str(LIB))
import installer
import standalone


class InstallerEngineTests(unittest.TestCase):
    def test_mounted_child_partition_blocks_whole_disk(self):
        real_stat=Path.stat
        def disk_stat(path,*args,**kwargs):
            if str(path)=='/dev/xrevive-test':
                return SimpleNamespace(st_mode=stat.S_IFBLK,st_rdev=os.makedev(240,0))
            return real_stat(path,*args,**kwargs)
        calls=[]
        def lsblk(*args):
            calls.append(args)
            if '-d' in args:
                return json.dumps({'blockdevices':[dict(type='disk',ro=False,**{'log-sec':512},size=64*1024**3,model='QA',serial='test')]})
            return json.dumps({'blockdevices':[dict(path='/dev/xrevive-test',mountpoints=[None],
                children=[dict(path='/dev/xrevive-test1',mountpoints=['/busy'])])]})
        with patch.object(Path,'stat',disk_stat),patch.object(installer,'command',lsblk):
            with self.assertRaisesRegex(ValueError,'montada'):installer.info('/dev/xrevive-test')
        self.assertIn('NAME,PATH,MOUNTPOINTS',calls[-1])

    def fixtures(self,tmp):
        payload=tmp/'payload';payload.mkdir()
        files=[]
        for drive in ('c','e','f'):
            (payload/drive).mkdir();path=payload/drive/'test.txt';path.write_bytes(drive.encode())
            files.append(dict(path=drive+'/test.txt',bytes=1,
                sha256=__import__('hashlib').sha256(drive.encode()).hexdigest()))
        (payload/'manifest.json').write_text(json.dumps(dict(schema=1,default_dashboard='XBMC4Gamers',files=files,packages=[])))
        source=tmp/'usb.img';source.write_bytes(bytes(4*1024**2))
        manifest=dict(device=str(source),build_id='qa',source_sha256='a'*64,
            regions={name:dict(offset=index*1024**2,bytes=1024**2)
                for index,name in enumerate(('system','console','cache','utils'))})
        target=tmp/'ssd.img'
        with target.open('wb') as f:f.truncate(24*1024**3)
        return payload,manifest,target

    def test_plan_and_install_file_with_dynamic_capacity_and_protected_regions(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload,source,target=self.fixtures(Path(tmp))
            prepared=installer.plan(target,source,payload,qa=True)
            self.assertGreater(prepared['layout']['xbox_bytes'],16*1024**3)
            with patch.object(installer,'boot_files'):
                result=installer.install(prepared,source,payload)
            self.assertTrue(result['verified'])
            standalone.read_verified(target,result['layout'])
            with target.open('rb') as f:
                f.seek(result['layout']['system']['offset']);self.assertEqual(f.read(512),bytes(512))
            self.assertEqual(installer.installed(target),result['layout'])

    def test_corrupt_payload_refused_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload,source,target=self.fixtures(Path(tmp));prepared=installer.plan(target,source,payload,qa=True)
            (payload/'e/test.txt').write_bytes(b'corrupt')
            before=target.stat().st_mtime_ns
            with self.assertRaisesRegex(ValueError,'corrompido'):installer.install(prepared,source,payload)
            self.assertEqual(target.stat().st_mtime_ns,before)

    def test_source_replaced_and_slow_payload_scan_are_guarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload,source,target=self.fixtures(Path(tmp))
            source['identity']=installer.info(source['device'],qa=True)['identity']
            with patch.object(installer.fatx,'tree',side_effect=AssertionError('slow scan')):
                prepared=installer.plan(target,source,payload,qa=True)
            with open(source['device'],'ab') as f:f.write(b'changed')
            before=target.stat().st_mtime_ns
            with self.assertRaisesRegex(ValueError,'mídia'):installer.install(prepared,source,payload)
            self.assertEqual(target.stat().st_mtime_ns,before)

    def test_replaced_or_resized_target_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload,source,target=self.fixtures(Path(tmp));prepared=installer.plan(target,source,payload,qa=True)
            with target.open('r+b') as f:f.truncate(25*1024**3)
            before=target.stat().st_mtime_ns
            with self.assertRaisesRegex(ValueError,'trocado'):installer.install(prepared,source,payload)
            self.assertEqual(target.stat().st_mtime_ns,before)

    def test_source_cannot_be_destination_and_large_layout_splits_f_g(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload,source,target=self.fixtures(Path(tmp))
            with self.assertRaisesRegex(ValueError,'origem'):installer.plan(source['device'],source,payload,qa=True)
            data=installer.make_layout(1800*1024**3,source)
            extended=standalone.extended(data)
            self.assertEqual(len(extended),2)
            self.assertEqual(extended[-1][1]+extended[-1][2],data['xbox_bytes'])
            for _,_,size in extended:installer.fatx.geometry(size,installer.fatx.cluster_size(size))
            self.assertEqual(standalone.repair_sector(standalone.sector0(data),data),standalone.sector0(data))


if __name__=='__main__':unittest.main()
