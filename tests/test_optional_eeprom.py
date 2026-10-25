import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cartucho/overlay/usr/local/lib/console'))
import package_source
import eeprom_store

class OptionalEEPROMTests(unittest.TestCase):
    def fixture(self,tmp):
        root=Path(tmp);fw=root/'firmware/xbox';fw.mkdir(parents=True)
        (fw/'bios.bin').write_bytes(bytes(range(256))*1024)
        (fw/'mcpx_1.0.bin').write_bytes(bytes(range(256))*2)
        return root,fw

    def test_absence_is_optional_but_invalid_or_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,fw=self.fixture(tmp)
            with patch.object(package_source,'USER',root):
                self.assertEqual(set(package_source.firmware()),{'bios.bin','mcpx_1.0.bin'})
                (fw/'eeprom.bin').write_bytes(b'bad')
                with self.assertRaises(ValueError):package_source.firmware()
                (fw/'eeprom.bin').unlink();(fw/'eeprom.bin').symlink_to(fw/'missing')
                with self.assertRaises(ValueError):package_source.firmware()

    def test_supplied_eeprom_is_bound_to_source_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,fw=self.fixture(tmp);(fw/'eeprom.bin').write_bytes(bytes(range(256)))
            with patch.object(package_source,'USER',root):
                self.assertIn('eeprom.bin',package_source.firmware())

    def test_generated_identity_saved_once_and_existing_identity_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'run';console=root/'console';run.mkdir();console.mkdir()
            data=bytes(range(256));(run/'eeprom.bin').write_bytes(data);mounts=[]
            self.assertTrue(eeprom_store.persist_initial(run,console,mounts.append))
            dst=console/'firmware/xbox/eeprom.bin';self.assertEqual(dst.read_bytes(),data)
            self.assertEqual(mounts,['rw','ro'])
            (run/'eeprom.bin').write_bytes(data[::-1]);mounts.clear()
            self.assertFalse(eeprom_store.persist_initial(run,console,mounts.append))
            self.assertEqual(dst.read_bytes(),data);self.assertEqual(mounts,[])

    def test_partial_creation_waits_without_remount_or_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'run';console=root/'console';run.mkdir();console.mkdir()
            (run/'eeprom.bin').write_bytes(b'');mounts=[]
            self.assertFalse(eeprom_store.persist_initial(run,console,mounts.append))
            self.assertEqual(mounts,[]);self.assertFalse((console/'firmware').exists())

if __name__=='__main__':unittest.main()
