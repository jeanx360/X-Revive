import importlib.util
from pathlib import Path
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('uix',ROOT/'cartucho/build/uix-relocate.py')
uix=importlib.util.module_from_spec(spec);spec.loader.exec_module(uix)


class UIXRelocationTests(unittest.TestCase):
    def test_unrecognized_binary_refused(self):
        with self.assertRaisesRegex(ValueError,'mudou'):uix.relocate(b'XBEHunknown')

    def test_locked_catalog_changes_only_nine_resource_volume_digits(self):
        archive=ROOT/'cartucho/cache/rocky5/packages/dashboards-5ef0c5105cb0.zip'
        if not archive.exists():self.skipTest('catálogo privado não baixado')
        with zipfile.ZipFile(archive) as z:original=z.read('xboxdash.xbe')
        patched=uix.relocate(original)
        changed=[i for i,(a,b) in enumerate(zip(original,patched)) if a!=b]
        self.assertEqual(len(original),len(patched))
        self.assertEqual(len(changed),9)
        for index in changed:
            self.assertEqual((original[index],patched[index]),(ord('2'),ord('6')))
        with self.assertRaises(ValueError):uix.relocate(patched)
