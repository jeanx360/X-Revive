import hashlib
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cartucho/overlay/usr/local/lib/console'))
import media_source
import on_screen_keyboard as keyboard
import safe_live
import wifi


class MediaTests(unittest.TestCase):
    def test_all_media_are_visible_recursively_in_both_usb_layouts_without_content_filters(self):
        with tempfile.TemporaryDirectory() as folder:
            usb=Path(folder);user=usb/'X-Revive';packages=user/'pacotes';(packages/'outras').mkdir(parents=True)
            legacy=usb/'pacotes';legacy.mkdir()
            paths=[packages/'offline.iso',packages/'outras/OGXBOX.XISO',packages/'HeXEn.IMG',legacy/'offline.iso']
            for p in paths:p.write_bytes(b'not yet validated')
            (packages/'readme.txt').write_text('instructions')
            (packages/'outside').symlink_to(usb,target_is_directory=True)
            rows=media_source.images(user)
            self.assertEqual(len(rows),4);self.assertEqual(len({r['id'] for r in rows}),4)
            self.assertIn('outras/OGXBOX.XISO',[r['name'] for r in rows])
            self.assertIn('pacotes/offline.iso',[r['name'] for r in rows])
            for r in rows:self.assertIn(media_source.selected(user,r['id']),paths)
            with patch.object(safe_live,'USER',user):
                before=paths[0].stat().st_mtime_ns
                with self.assertRaisesRegex(ValueError,'Mídia Xbox'):safe_live.disc('offline',rows[0]['id'],lambda *_:None)
                self.assertEqual(len(safe_live.images()),4);self.assertEqual(paths[0].stat().st_mtime_ns,before)
            paths[0].unlink()
            with self.assertRaises(ValueError):media_source.selected(user,'../../personal.img')


class KeyboardTests(unittest.TestCase):
    def test_controller_can_type_erase_switch_case_and_symbols_and_cancel(self):
        k=keyboard.Keyboard();k.choose();self.assertEqual(k.text,'1')
        k.move(dy=1);k.choose();self.assertEqual(k.text,'1q')
        k.row=len(k.rows())-1;k.col=0;k.choose();self.assertTrue(k.upper)
        k.row=1;k.col=0;k.choose();self.assertEqual(k.text,'1qQ')
        k.row=len(k.rows())-1;k.col=1;k.choose();self.assertTrue(k.symbols)
        self.assertIn('Ç',[v for r in k.rows()[:-1] for v in r])
        k.col=3;k.choose();self.assertEqual(k.text,'1q')
        k.col=5;self.assertEqual(k.choose(),'Cancelar');k.clear();self.assertEqual(k.text,'')

    def test_physical_unicode_typing_and_grid_edges(self):
        k=keyboard.Keyboard();k.insert('Minha senha: ç!\\"\n');self.assertNotIn('\n',k.text)
        k.erase();k.move(dx=-1);k.move(dy=-1)
        self.assertLess(k.col,len(k.rows()[k.row]));k.insert('x'*300);self.assertEqual(len(k.text),256)


class WifiTests(unittest.TestCase):
    def test_first_scan_waits_for_scan_already_started_by_networkmanager(self):
        class Busy(Exception):pass
        b=object.__new__(wifi.Backend);counter=[]
        b.status=lambda:dict(available=True,blocked=False)
        b.devices=lambda:[('/wifi',{})]
        def props(*args):
            counter.append(1);return {'LastScan':len(counter)-1}
        b.properties=props
        def busy(*args,**kw):raise Busy()
        interface=types.SimpleNamespace(Set=lambda *a,**kw:None,RequestScan=busy)
        b.d=types.SimpleNamespace(Interface=lambda *a:interface,Boolean=bool,Dictionary=lambda v,**kw:v,DBusException=Busy)
        b.manager=None;b.bus=types.SimpleNamespace(get_object=lambda *a:None)
        b.access_points=lambda:[dict(id='ap',ssid='visible',signal=80,connected=False)] if len(counter)>1 else []
        self.assertEqual(b.scan()['networks'][0]['ssid'],'visible')

    def test_security_types(self):
        self.assertEqual(wifi.security(0,0,0),('Aberta','',False))
        self.assertEqual(wifi.security(1,0,0x100)[1],'wpa-psk')
        self.assertEqual(wifi.security(1,0,0x400)[1],'sae')
        self.assertIsNone(wifi.security(1,0,0x200)[1])
        self.assertEqual(wifi.display('SSID\nwith\ttabs'),'SSID with tabs')

    def backend(self):
        class BusError(Exception):pass
        b=object.__new__(wifi.Backend)
        b.d=types.SimpleNamespace(Boolean=bool,ByteArray=bytes,Int64=int,ObjectPath=str,
                                 Dictionary=lambda x,**kw:x,DBusException=BusError)
        b.access_points=lambda:[dict(id='chosen',supported=True,password=True,_key='wpa-psk',_ssid=b'QA:SSID',_device='/wifi',_ap='/ap')]
        b.properties=lambda *a:dict(State=100,ActiveConnection='/active')
        b.scan=lambda:dict(connected=True)
        return b,BusError

    def test_password_only_enters_volatile_dbus_settings(self):
        b,_=self.backend();calls=[]
        def activate(*args,**kw):calls.append(args);return ('/connection','/active',{})
        b.nm=types.SimpleNamespace(AddAndActivateConnection2=activate)
        self.assertTrue(b.connect('chosen','dummy-test-password')['connected'])
        settings,device,ap,options=calls[0]
        self.assertEqual(options,{'persist':'volatile'})
        self.assertEqual(settings['802-11-wireless-security']['psk'],'dummy-test-password')
        self.assertFalse(settings['connection']['autoconnect']);self.assertEqual(device,'/wifi')

    def test_authentication_error_cannot_echo_password(self):
        b,Error=self.backend()
        def fail(*a,**kw):raise Error('settings echo dummy-secret')
        b.nm=types.SimpleNamespace(AddAndActivateConnection2=fail)
        with self.assertRaises(ValueError) as caught:b.connect('chosen','dummy-secret')
        self.assertNotIn('dummy-secret',str(caught.exception))
        with self.assertRaisesRegex(ValueError,'disponível'):b.connect('removed','dummy-secret')


if __name__=='__main__':unittest.main()
