import hashlib
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


held = load('held_assets', 'plataformas/xbox/tools/held.py')
boot = load('bootanim', 'plataformas/xbox/tools/bootanim.py')


class Files:
    def __init__(self):
        self.files = {}
        self.dirs = set()
        self.writes = 0

    def get_attr(self, path):
        if path in self.dirs:
            return SimpleNamespace(is_file=False, is_directory=True, file_size=0)
        if path not in self.files:
            raise AssertionError(path)
        return SimpleNamespace(is_file=True, is_directory=False, file_size=len(self.files[path]))

    def read(self, path): return self.files[path]
    def mkdir(self, path): self.dirs.add(path)
    def unlink(self, path): del self.files[path]
    def rename(self, src, dst): self.files[dst] = self.files.pop(src)
    def write(self, path, data):
        self.files[path] = data
        self.writes += 1


class BootAssetsTest(unittest.TestCase):
    def test_G_R_and_recovery_priority_across_devices(self):
        for keys, expected in [({'a': {34}}, ''), ({'a': {19}}, 'installer'),
                               ({'a': {34}, 'b': {314, 315}}, 'installer'), ({}, '')]:
            with patch.object(held, 'held', lambda dev, combo=held.COMBO: set(combo) <= keys.get(dev, set())):
                self.assertEqual(held.selection(['a', 'b']), expected)

    def test_selection_catches_late_controller_in_same_window(self):
        now = [0.0]
        sleep = lambda seconds: now.__setitem__(0, now[0]+seconds)
        self.assertEqual(held.wait_selection(8, lambda: 'installer' if now[0]>3 else '',
                                             lambda: now[0], sleep), 'installer')

    def test_ini_preserves_dashboard_storage_and_line_endings(self):
        original = b'DashPath = HDD0-C:\\custom.xbe\r\nDriveSetup = 0\r\nBootAnimPath = missing\r\n'
        changed = boot.configured_ini(original)
        self.assertIn(b'DashPath = HDD0-C:\\custom.xbe\r\nDriveSetup = 0\r\n', changed)
        self.assertIn(boot.BOOT_PATH.encode(), changed)
        self.assertEqual(changed, boot.configured_ini(changed))

    def test_animation_backup_idempotence_and_no_dashboard_writes(self):
        fs = Files()
        fs.files[boot.ANIMATION+'bootanim.ini'] = b'original colours'
        fs.files[boot.INI_PATH] = b'DashPath = custom\nDriveSetup = 0\n'
        fs.files['/evoxdash.xbe'] = b'custom dashboard'
        fixture = tempfile.TemporaryDirectory()
        self.addCleanup(fixture.cleanup)
        assets = Path(fixture.name)
        # Fixture sintética: o clone público não contém executáveis Xbox.
        (assets/'BootAnim.xbe').write_bytes(b'XBEH'+bytes(65536-4))
        (assets/'bootanim.ini').write_bytes(b'; synthetic test configuration\n')
        boot.install(fs, assets)
        self.assertEqual(fs.files['/evoxdash.xbe'], b'custom dashboard')
        self.assertEqual(fs.files[boot.ANIMATION+'bootanim.ini.xrevive.bak'], b'original colours')
        self.assertIn(b'DriveSetup = 0', fs.files[boot.INI_PATH])
        writes = fs.writes
        boot.install(fs, assets)
        self.assertEqual(fs.writes, writes)

    def test_refuses_unknown_bios_or_non_fatx_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            bios, disk = Path(tmp)/'bios.bin', Path(tmp)/'hdd.img'
            bios.write_bytes(b'test bios')
            with disk.open('wb') as f: f.truncate(8*1024**3)
            with self.assertRaisesRegex(ValueError, 'BIOS nao auditada'):
                boot.validate_disk(disk, bios)
            with patch.object(boot, 'CERBIOS_310', hashlib.sha256(bios.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError, 'sem assinatura FATX'):
                    boot.validate_disk(disk, bios)
            with disk.open('rb') as f:
                f.seek(0xABE80000)
                self.assertEqual(f.read(4), b'\0'*4)


if __name__ == '__main__':
    unittest.main()
