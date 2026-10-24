import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
public=load('public_rootfs','cartucho/build/public-rootfs.py')
sources=load('release_sources','cartucho/tools/collect-release-sources.py')

class PublicReleaseTests(unittest.TestCase):
    def test_status_empty_fields_and_built_using_keep_exact_source_versions(self):
        text='Package: test\nStatus: install ok installed\nSource: sample (1:2.0-1)\nVersion: 1:2.0-1+b1\nConffiles:\n /etc/test abc\nBuilt-Using: extra (= 3.0-2)\nStatic-Built-Using: static (= 1.0-1)\n\n'
        self.assertEqual(sources.units(text),[('extra','3.0-2'),('sample','1:2.0-1'),('static','1.0-1')])
        record=sources.paragraphs('Checksums-Sha256:\n abc 12 file.tar.xz\nDirectory: pool/main/a/app\n')[0]
        self.assertEqual(record['Checksums-Sha256'],'\nabc 12 file.tar.xz')

    def fixture(self,tmp):
        root=Path(tmp)/'root';repo=Path(tmp)/'repo';repo.mkdir()
        for name in ('LICENSE','NOTICE.md','THIRD_PARTY_NOTICES.md'):(repo/name).write_text('test')
        for name in ('var/lib/dpkg/status','opt/xemu/usr/bin/xemu','usr/lib/firmware/xone_dongle_02e6.bin','usr/lib/firmware/other.bin','var/lib/dkms/mok.key','etc/machine-id','opt/xemu/usr/lib/obsolete.so'):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
        return root,repo

    def test_public_preparation_removes_only_staging_private_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,repo=self.fixture(tmp);result=public.prepare(root,repo)
            self.assertFalse((root/'var/lib/dkms/mok.key').exists())
            self.assertFalse((root/'usr/lib/firmware/xone_dongle_02e6.bin').exists())
            self.assertTrue((root/'usr/lib/firmware/other.bin').exists())
            self.assertFalse((root/'opt/xemu/usr/lib').exists())
            self.assertEqual((root/'etc/machine-id').read_bytes(),b'')
            self.assertTrue(result['public'])

    def test_user_firmware_and_symlink_escape_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,repo=self.fixture(tmp);(root/'bios.bin').write_bytes(b'personal')
            with self.assertRaisesRegex(ValueError,'Xbox data'):public.prepare(root,repo)
        with tempfile.TemporaryDirectory() as tmp:
            root,repo=self.fixture(tmp);lib=root/'opt/xemu/usr/lib';(lib/'obsolete.so').unlink();lib.rmdir();lib.symlink_to(repo,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):public.prepare(root,repo)
            self.assertTrue((repo/'LICENSE').exists())

if __name__=='__main__':unittest.main()
