"""LIVE media adapters and explicit disk authorization, without host devices."""
import ast
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

LIB=Path(__file__).resolve().parents[1]/'cartucho/overlay/usr/local/lib/console'
sys.path.insert(0,str(LIB))
import dongle
import live_disk
import live_media
import live_target
import xiso
import fatx

class TargetTests(unittest.TestCase):
    def test_blank_or_pc_disk_can_be_selected_without_modification_and_hot_swap_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);disk=root/'usb-hdd.img';source=dict(device=str(root/'boot.img'))
            with disk.open('xb') as out:out.truncate(12*1024**3);out.seek(510);out.write(b'\x55\xaaEFI PART')
            stamp=disk.stat().st_mtime_ns
            planned=live_target.plan(disk,source,qa=True)
            self.assertEqual(planned['xbox_bytes'],12*1024**3)
            self.assertEqual(live_target.check(planned,source)['device'],planned['device'])
            self.assertEqual(disk.stat().st_mtime_ns,stamp)
            with self.assertRaisesRegex(ValueError,'boot bloqueado'):live_target.plan(disk,dict(device=str(disk)),qa=True)
            with disk.open('r+b') as out:out.write(b'changed')
            with self.assertRaisesRegex(ValueError,'mudou'):live_target.check(planned,source)

    def test_usb_disks_are_not_filtered_by_bus_or_preexisting_fatx(self):
        rows=dict(blockdevices=[dict(path='/dev/sda',type='disk',size=12*1024**3,model='External USB',tran='usb',serial='USB-QA'),dict(path='/dev/sdb',type='disk',size=16*1024**3,model='boot',tran='usb',serial='BOOT')])
        found=dict(device=dict(identity='selected'),kind='Disco para preparar')
        with patch.object(live_target.engine,'command',return_value=json.dumps(rows)),patch.object(live_target,'inspect',return_value=found):
            result=live_target.disks(dict(device='/dev/sdb'))
        self.assertEqual(len(result),1);self.assertEqual(result[0]['transport'],'usb');self.assertTrue(result[0]['available'])

    def dispatcher(self,folder):
        tree=ast.parse((LIB/'installer-worker.py').read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dispatch')
        env=dict(Path=Path,status={'busy':False},mutex=threading.Lock(),SOURCE={},pending=None,confirmation=0,live_pending=None,live_confirmed=False,
                 media_pending=dict(token='token',access='write'),media_confirmed=0,live_target=types.SimpleNamespace(check=lambda *a:True),
                 live_disk=types.SimpleNamespace(PRIVATE=Path(folder)),job=lambda f:dict(started=True))
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<dispatch>','exec'),env)
        return env,env['dispatch']

    def test_write_requires_two_ordered_confirmations_bound_to_plan_and_cancel_revokes(self):
        with tempfile.TemporaryDirectory() as folder:
            env,call=self.dispatcher(folder)
            for req in [dict(action='media-start',token='token'),dict(action='media-confirm',token='other',step=1),dict(action='media-confirm',token='token',step=2),dict(action='media-confirm',token='token',step=True)]:
                with self.assertRaises(ValueError):call(req)
            call(dict(action='media-confirm',token='token',step=1))
            with self.assertRaises(ValueError):call(dict(action='media-start',token='token'))
            call(dict(action='cancel'));self.assertIsNone(env['media_pending']);self.assertEqual(env['media_confirmed'],0)
            env['media_pending']=dict(token='new',access='write',media=dict(mode='offline'))
            call(dict(action='media-confirm',token='new',step=1));call(dict(action='media-confirm',token='new',step=2))
            self.assertEqual(call(dict(action='media-start',token='new')),dict(started=True))
            self.assertIsNone(env['media_pending']);self.assertEqual(env['media_confirmed'],0)
            with self.assertRaises(ValueError):call(dict(action='media-start',token='new'))

    def test_protected_does_not_request_write_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            env,call=self.dispatcher(folder);env['media_pending']=dict(token='token',access='protected')
            with self.assertRaises(ValueError):call(dict(action='media-confirm',token='token',step=1))
            self.assertEqual(call(dict(action='media-start',token='token')),dict(started=True))

class MediaTests(unittest.TestCase):
    def test_synopsis_names_are_native_copy_compatible_deterministic_and_keep_contents(self):
        for name in ['Bun for Barney, A.txt','Summer Games I + II.txt','Stadt Der L÷wen, Die.txt','a'*50+'.txt']:
            safe=fatx.metadata_filename(name)
            self.assertNotEqual(safe,name);self.assertEqual(safe,fatx.metadata_filename(name))
            self.assertLessEqual(len(safe),42);self.assertTrue(safe.endswith('.txt'))
            self.assertTrue(safe.isascii());self.assertFalse(set(safe)&set(',+;='))
        self.assertEqual(fatx.metadata_filename('Already legal.txt'),'Already legal.txt')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);tree=root/'tree';tree.mkdir();(tree/'default.xbe').write_bytes(b'XBEHtest')
            source=tree/'Bun for Barney, A.txt';source.write_bytes(b'synopsis content')
            iso=root/'adapted.iso';xiso.build(tree,iso,renames={str(source):fatx.metadata_filename(source.name)})
            self.assertTrue(xiso.inspect(iso));self.assertEqual(source.read_bytes(),b'synopsis content')
            self.assertIn(fatx.metadata_filename(source.name).encode(),iso.read_bytes());self.assertNotIn(source.name.encode(),iso.read_bytes())

    def test_cache_reclaims_only_verified_generated_old_recipe_for_same_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=root/'1';old.mkdir();image=old/'disc.iso';image.write_bytes(b'generated disc')
            marker=old/'verified.json';state=dict(kind='collection',source_sha256='input',sha256=hashlib.sha256(image.read_bytes()).hexdigest())
            marker.write_text(json.dumps(state));(old/'owner.txt').write_text('keep me')
            self.assertEqual(live_media.reclaim_generated_cache(root,'other'),0);self.assertTrue(image.exists())
            image.write_bytes(b'owner modified disc');self.assertEqual(live_media.reclaim_generated_cache(root,'input'),0)
            image.write_bytes(b'generated disc');self.assertEqual(live_media.reclaim_generated_cache(root,'input'),14)
            self.assertTrue((old/'owner.txt').exists());self.assertFalse(marker.exists())
            image.symlink_to(old/'owner.txt');marker.write_text(json.dumps(state))
            self.assertEqual(live_media.reclaim_generated_cache(root,'input'),0);self.assertTrue(image.is_symlink())
    def test_full_dvd_offset_and_non_python_collation_are_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);tree=root/'tree';tree.mkdir();(tree/'default.xbe').write_bytes(b'XBEH'+bytes(100));(tree/'z.txt').write_text('test')
            iso=root/'trimmed.iso';xiso.build(tree,iso)
            header=iso.read_bytes()[32*2048:33*2048];sector,size=struct.unpack_from('<II',header,20)
            # Build normally, then deliberately place the executable on the
            # wrong search branch. Traversal still finds the genuine XBE.
            with iso.open('r+b') as out:
                out.seek(sector*2048);table=bytearray(out.read(size));left,right=struct.unpack_from('<HH',table)
                struct.pack_into('<HH',table,0,right,left);out.seek(sector*2048);out.write(table)
            self.assertEqual(xiso.inspect(iso)['offset'],0)
            full=root/'full.iso';base=0x18300000
            with full.open('xb') as out:out.truncate(base+iso.stat().st_size);out.seek(base);out.write(iso.read_bytes())
            self.assertEqual(xiso.inspect(full)['offset'],base)
            self.assertEqual(xiso.inspect(full)['disc_bytes'],iso.stat().st_size)

    def test_aliases_make_boot_disc_without_copying_payload_and_keep_cp1252_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);tree=root/'tree';tree.mkdir();(tree/'coleção.txt').write_text('test')
            xbe=root/'unleash.xbe';xbe.write_bytes(b'XBEH'+bytes(100));out=root/'out.iso'
            xiso.build(tree,out,aliases={'default.xbe':xbe})
            self.assertEqual(xiso.inspect(out)['default_xbe_bytes'],104)
            self.assertEqual(sorted(p.name for p in tree.iterdir()),['coleção.txt'])

    def test_native_disc_can_be_attempted_even_without_standard_boot_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);tree=root/'tree';tree.mkdir();(tree/'default.xbe').write_bytes(b'XBEHtest')
            iso=root/'native.iso';xiso.build(tree,iso)
            with iso.open('r+b') as out:
                out.seek(32*2048+20);sector,size=struct.unpack('<II',out.read(8));out.seek(sector*2048+14);out.write(b'customx.xbe')
            with self.assertRaisesRegex(ValueError,'default.xbe'):xiso.inspect(iso)
            info=xiso.inspect(iso,require_boot=False)
            self.assertEqual(info['offset'],0);self.assertIn('BIOS',info['boot_warning'])
            result=live_media.prepare(iso,root,lambda *_:None)
            self.assertFalse(result['adapted']);self.assertEqual(result['path'],str(iso))

    def test_normalized_collection_has_explicit_install_and_format_menus(self):
        tree=ET.fromstring(live_media.collection_menu())
        copy=tree.findall('.//Item[@Action="Copy"]');self.assertEqual(len(copy),3)
        self.assertEqual([i.attrib['Arg2'] for i in copy],['C:\\','E:\\','F:\\'])
        batch=tree.find('.//List[@Text="Instalar colecao X-Revive (C, E e F)"]')
        self.assertEqual(len(batch.findall('Item[@Action="AskUser"]')),2)
        for parent in tree.findall('.//List'):
            if parent.find('Item[@Action="Format"]') is not None:self.assertEqual(len(parent.findall('Item[@Action="AskUser"]')),2)

class DongleTests(unittest.TestCase):
    def test_only_known_valid_owner_firmware_is_imported_and_early_bound_empty_interface_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);owner=root/'owner';owner.mkdir();fw=root/'firmware';fw.mkdir();run=root/'run';run.mkdir()
            usb=root/'usb/devices';usb.mkdir(parents=True);(usb.parent/'drivers_probe').touch()
            device=usb/'1-2';device.mkdir();(device/'idVendor').write_text('045e');(device/'idProduct').write_text('02fe')
            interface=usb/'1-2:1.0';interface.mkdir();driver=root/'drivers/xone-dongle';driver.mkdir(parents=True)
            (driver/'unbind').touch();(interface/'driver').symlink_to(driver);(interface/'active_clients').write_text('Active clients: 0\n[00]\t[08]\n')
            name='xone_dongle_02fe.bin';data=b'valid test firmware';(owner/name).write_bytes(data)
            with patch.dict(dongle.HASHES,{'02fe':hashlib.sha256(data).hexdigest()}),patch.object(dongle.subprocess,'run'):
                result=dongle.import_owner([owner],fw,usb,run)
            self.assertEqual(result['imported'],[name]);self.assertEqual((fw/name).read_bytes(),data)
            self.assertEqual((driver/'unbind').read_text(),interface.name);self.assertEqual((usb.parent/'drivers_probe').read_text(),interface.name)
            (owner/name).write_bytes(b'corrupt');found,errors=dongle.files([owner]);self.assertEqual(found,{});self.assertTrue(errors)
            (owner/name).unlink();(owner/name).symlink_to(fw/name)
            self.assertEqual(dongle.files([owner])[0],{})

if __name__=='__main__':unittest.main()
