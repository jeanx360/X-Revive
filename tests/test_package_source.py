"""Boundary tests: untrusted local inventories and pre-format firmware checks."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'cartucho/overlay/usr/local/lib/console'
sys.path.insert(0,str(LIB))
import package_source as source
import installer


class PackageSourcesTests(unittest.TestCase):
    def test_real_embedded_signed_catalog_and_tampering(self):
        envelope=json.loads((ROOT/'cartucho/overlay/usr/share/console/rocky5-catalog.json').read_text())
        with patch.object(source,'KEY',ROOT/'cartucho/overlay/usr/share/console/update-key.pem'):
            self.assertEqual(len(source.validate_catalog(envelope)['packages']),107)
            envelope['manifest']['packages'][0]['url']='https://example.org/changed.zip'
            with self.assertRaises(Exception):source.validate_catalog(envelope)

    def test_manifest_rejects_escape_duplicate_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'f').mkdir();(root/'f/test').write_bytes(b'XBEH')
            manifest=dict(schema=1,default_dashboard='XBMC4Gamers',files=[dict(path='f/test',bytes=4,sha256=hashlib.sha256(b'XBEH').hexdigest())])
            def write():(root/'manifest.json').write_text(json.dumps(manifest))
            write();source.safe_manifest(root)
            for path in ('/etc/passwd','f/../../outside','f/./test','f/other\\test'):
                manifest['files'][0]['path']=path;write()
                with self.assertRaises(ValueError):source.safe_manifest(root)
            manifest['files'][0]['path']='f/test';manifest['files'].append(dict(manifest['files'][0]));write()
            with self.assertRaises(ValueError):source.safe_manifest(root)
            manifest['files'].pop();(root/'f/test').unlink();(root/'f/test').symlink_to('/etc/passwd');write()
            with self.assertRaises(ValueError):source.safe_manifest(root)

    def test_firmware_required_before_download_or_staging(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(source,'USER',Path(tmp)):
            with self.assertRaisesRegex(ValueError,'bios.bin'):source.prepare('online',None,lambda *_:None)
            self.assertFalse((Path(tmp)/'cache').exists())

    def test_corrupt_imported_firmware_never_opens_target_for_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);payload=root/'payload';payload.mkdir()
            for d in 'cef':(payload/d).mkdir()
            (payload/'manifest.json').write_text(json.dumps(dict(schema=1,default_dashboard='XBMC4Gamers',files=[])))
            fw=root/'bios.bin';fw.write_bytes(b'changed')
            target=root/'ssd.img';target.write_bytes(b'data to preserve')
            info=dict(device=str(root/'usb.img'),firmware={'bios.bin':dict(path=str(fw),sha256='0'*64)})
            before=target.stat().st_mtime_ns
            with self.assertRaisesRegex(ValueError,'Firmware mudou'):installer.install({},info,payload)
            self.assertEqual(target.stat().st_mtime_ns,before)
            self.assertEqual(target.read_bytes(),b'data to preserve')


if __name__=='__main__':unittest.main()
