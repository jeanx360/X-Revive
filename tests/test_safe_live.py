import ast
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'cartucho/overlay/usr/local/lib/console'
sys.path.insert(0,str(LIB))
import graphics
import safe_live
import xiso


def card(name,driver,connected=True,panel=False,boot=False):
    return dict(path='/dev/dri/'+name,driver=driver,connected=connected,panel=panel,boot=boot)


class GraphicsTests(unittest.TestCase):
    def test_hybrid_prefers_internal_panel_even_when_nvidia_is_enumerated_first(self):
        nv=card('card0','nvidia',False,boot=True);intel=card('card1','i915',panel=True)
        selected,env=graphics.environment([nv,intel])
        self.assertEqual(selected,intel);self.assertEqual(env['WLR_DRM_DEVICES'],'/dev/dri/card1')
        self.assertNotIn('GBM_BACKEND',env);self.assertNotIn('__GLX_VENDOR_LIBRARY_NAME',env)
        self.assertNotIn('SDL_VIDEODRIVER',env)

    def test_single_nvidia_keeps_proven_gtx750_settings(self):
        selected,env=graphics.environment([card('card0','nvidia',boot=True)])
        self.assertEqual(env['GBM_BACKEND'],'nvidia-drm');self.assertEqual(env['WLR_RENDERER'],'gles2')
        self.assertEqual(env['SDL_VIDEODRIVER'],'wayland')

    def test_connected_monitor_wins_over_headless_boot_gpu_and_compat_has_no_modifiers(self):
        selected,env=graphics.environment([card('card0','nvidia',False,boot=True),card('card1','amdgpu')],'compat')
        self.assertEqual(selected['driver'],'amdgpu');self.assertEqual(env['WLR_DRM_NO_MODIFIERS'],'1')
        self.assertEqual(graphics.environment([]),(None,{}))


class SafeLiveTests(unittest.TestCase):
    def test_keyboard_works_without_requiring_a_gamepad_and_does_not_take_its_port(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cfg=root/'xemu.toml';cfg.write_text('[input]\nauto_bind = true\n')
            self.assertTrue(safe_live.keyboard_fallback(cfg,root))
            self.assertIn("port1 = 'keyboard'",cfg.read_text())
            cfg.write_text('[input]\nauto_bind = true\n');(root/'js0').touch()
            self.assertFalse(safe_live.keyboard_fallback(cfg,root));self.assertNotIn('keyboard',cfg.read_text())

    def test_protection_excludes_entire_usb_and_sets_other_disk_and_partitions_readonly(self):
        rows={'blockdevices':[dict(path='/dev/sdb',type='disk',children=[dict(path='/dev/sdb1',type='part')]),
                              dict(path='/dev/nvme0n1',type='disk',children=[dict(path='/dev/nvme0n1p1',type='part')]) ]}
        calls=[]
        def output(args,**kw):return json.dumps(rows) if Path(args[0]).name=='lsblk' else '1\n'
        with patch.object(safe_live.subprocess,'check_output',side_effect=output),patch.object(safe_live.subprocess,'run',side_effect=lambda args,**kw:calls.append(args)):
            result=safe_live.protect('/dev/sdb')
        self.assertEqual(result,['/dev/nvme0n1','/dev/nvme0n1p1'])
        self.assertTrue(all(c[:2]==['/usr/sbin/blockdev','--setro'] for c in calls))

    def test_safe_rpc_refuses_every_physical_disk_action_before_work(self):
        tree=ast.parse((LIB/'installer-worker.py').read_text())
        dispatch=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dispatch')
        env=dict(SOURCE={'safe_live':True},status={'busy':False},mutex=threading.Lock())
        exec(compile(ast.Module(body=[dispatch],type_ignores=[]),'<dispatch>','exec'),env)
        for action in ('live-disks','live-plan','live-start','live-boot-prepare','plan','confirm','install','repair','dashboard','verify','prepare'):
            with self.subTest(action=action),self.assertRaisesRegex(ValueError,'discos físicos bloqueado'):
                env['dispatch'](dict(action=action,target='/dev/nvme0n1'))

    def test_safe_welcome_only_offers_virtual_live_or_poweroff(self):
        tree=ast.parse((LIB/'installer-ui.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='UI')
        env={};exec(compile(ast.Module(body=[cls],type_ignores=[]),'<ui>','exec'),env)
        ui=object.__new__(env['UI']);ui.state='welcome';ui.boot=dict(safe_live=True,installed=False)
        self.assertEqual(ui.options(),['LIVE — mídias do usuário','Configurar rede Wi-Fi','Desligar'])

    def test_xiso_is_deterministic_bootable_and_rejects_non_bootable_or_cycles(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);tree=root/'tree';tree.mkdir();(tree/'default.xbe').write_bytes(b'XBEH'+bytes(128))
            (tree/'a.txt').write_text('hello');(tree/'z.txt').write_text('end')
            nested=tree/'Hardmod';nested.mkdir();(nested/'default.xbe').write_bytes(b'XBEHnested')
            a=root/'a.iso';b=root/'b.iso';xiso.build(tree,a);xiso.build(tree,b)
            self.assertEqual(a.read_bytes(),b.read_bytes());self.assertEqual(xiso.inspect(a)['default_xbe_bytes'],132)
            with a.open('r+b') as out:out.seek(32*2048+20);out.write(struct.pack('<II',0xFFFFFFFF,256))
            with self.assertRaisesRegex(ValueError,'raiz'):xiso.inspect(a)
            (tree/'default.xbe').write_bytes(b'not-xbe')
            with self.assertRaisesRegex(ValueError,'default.xbe'):xiso.build(tree,root/'bad.iso')

    def test_online_lock_verifies_every_file_and_offline_list_cannot_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);user=root/'user';iso=user/'pacotes/live';iso.mkdir(parents=True)
            (iso/'ok.iso').write_bytes(b'own ISO');(iso/'bad.iso').symlink_to(root/'outside')
            with patch.object(safe_live,'USER',user):
                self.assertEqual([r['name'] for r in safe_live.images()],['live/ok.iso'])
                with self.assertRaisesRegex(ValueError,'ausente'):safe_live.disc('offline','../other.iso',lambda *_:None)
            data=b'XBEHtested';sha=hashlib.sha256(data).hexdigest();cache=root/'cache';cache.mkdir()
            lock=dict(origin='https://raw.githubusercontent.com/Rocky5/Xbox-Softmodding-Tool/',commit='a'*40,
                      files=[dict(path='default.xbe',bytes=len(data),sha256=sha)])
            def good(url,path,limit):Path(path).write_bytes(data)
            with patch.object(safe_live.Transport,'fetch',side_effect=good):safe_live.checked_download_tree(lock,cache,lambda *_:None)
            self.assertEqual((cache/'default.xbe').read_bytes(),data)
            (cache/'default.xbe').write_text('corrupt')
            with patch.object(safe_live.Transport,'fetch',side_effect=lambda url,path,limit:Path(path).write_bytes(b'bad')):
                with self.assertRaisesRegex(ValueError,'não confere'):safe_live.checked_download_tree(lock,cache,lambda *_:None)
            lock['files'][0]['path']='../outside'
            with self.assertRaisesRegex(ValueError,'Caminho'):safe_live.checked_download_tree(lock,cache,lambda *_:None)


if __name__=='__main__':unittest.main()
