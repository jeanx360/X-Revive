import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release', ROOT/'cartucho/build/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTest(unittest.TestCase):
    def test_installer_retires_previous_images_without_deleting_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);stage=root/'stage';out=root/'out';stage.mkdir();out.mkdir()
            old=out/'console-xbox-nvidia.img';old.write_bytes(b'working baseline')
            self.prepare(stage,'installer')
            release.publish(stage,out,'xbox','pair-1','source-1')
            self.assertEqual([p.name for p in out.glob('*.img')],['console-xbox-installer.img'])
            self.assertEqual((root/'cache/retired-before-pair-1/console-xbox-nvidia.img').read_bytes(),b'working baseline')
            self.assertEqual(len(json.loads((out/'release.json').read_text())['images']),1)

    def prepare(self, root, variant, build='pair-1', kernel='kernel-1'):
        stem = 'console-xbox-' + variant
        (root/(stem+'.img')).write_bytes(variant.encode())
        (root/(stem+'.packages.txt')).write_text('package 1\n')
        (root/(stem+'.json')).write_text(json.dumps(dict(build_id=build,
            source_sha256='source-1', variant=variant, kernel=kernel, nvidia_driver=None)))

    def test_incomplete_or_mismatched_pair_preserves_existing_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage, out = root/'stage', root/'out'
            stage.mkdir(); out.mkdir()
            old = out/'console-xbox-universal.img'
            old.write_bytes(b'previous')
            self.prepare(stage, 'universal')
            with self.assertRaises(FileNotFoundError):
                release.publish(stage, out, 'xbox', 'pair-1', 'source-1')
            self.assertEqual(old.read_bytes(), b'previous')
            self.prepare(stage, 'nvidia', build='different-pair')
            with self.assertRaises(ValueError):
                release.publish(stage, out, 'xbox', 'pair-1', 'source-1')
            self.assertEqual(old.read_bytes(), b'previous')

    def test_publish_two_images_with_matching_manifest_and_no_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage, out = root/'stage', root/'out'
            stage.mkdir(); out.mkdir()
            (out/'console-xbox.img').write_bytes(b'legacy')
            for variant in ('universal', 'nvidia'):
                self.prepare(stage, variant)
            release.publish(stage, out, 'xbox', 'pair-1', 'source-1')
            self.assertEqual(len(list(out.glob('*.img'))), 2)
            manifest = json.loads((out/'release.json').read_text())
            self.assertEqual(manifest['build_id'], 'pair-1')
            for entry in manifest['images']:
                self.assertEqual(release.digest(out/entry['file']), entry['sha256'])
            self.assertFalse(list(stage.iterdir()))

    def test_different_utility_media_does_not_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage, out = root/'stage', root/'out'
            stage.mkdir(); out.mkdir()
            old = out/'console-xbox-nvidia.img'
            old.write_bytes(b'working')
            for variant in ('universal', 'nvidia'):
                self.prepare(stage, variant)
                path = stage/f'console-xbox-{variant}.json'
                metadata = json.loads(path.read_text())
                metadata['utilities'] = {'ogxbox': {'sha256': variant, 'bytes': 123}}
                path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'Utilitarios divergentes'):
                release.publish(stage, out, 'xbox', 'pair-1', 'source-1')
            self.assertEqual(old.read_bytes(), b'working')

    def test_third_image_requires_experimental_layout_before_replacing_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage = root/'stage'; out = root/'out'
            stage.mkdir(); out.mkdir()
            old = out/'console-xbox-nvidia.img'; old.write_bytes(b'working')
            for variant in ('universal', 'nvidia', 'standalone'):
                self.prepare(stage, variant)
            with self.assertRaisesRegex(ValueError, 'Standalone'):
                release.publish(stage, out, 'xbox', 'pair-1', 'source-1')
            self.assertEqual(old.read_bytes(), b'working')
            path = stage/'console-xbox-standalone.json'
            metadata = json.loads(path.read_text()); metadata['experimental'] = True
            path.write_text(json.dumps(metadata))
            (stage/'console-xbox-standalone.layout.json').write_text('{"schema":1}')
            release.publish(stage, out, 'xbox', 'pair-1', 'source-1')
            self.assertEqual(len(list(out.glob('*.img'))), 3)
            self.assertTrue((out/'console-xbox-standalone.layout.json').is_file())
            self.assertEqual(len(json.loads((out/'release.json').read_text())['images']), 3)

    def test_different_emulator_does_not_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage = root/'stage'; out = root/'out'
            stage.mkdir(); out.mkdir()
            for variant in ('universal', 'nvidia'):
                self.prepare(stage, variant)
                path = stage/f'console-xbox-{variant}.json'
                data = json.loads(path.read_text()); data['emulator'] = {'sha256': variant}
                path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Emulador divergente'):
                release.publish(stage, out, 'xbox', 'pair-1', 'source-1')
            self.assertFalse(list(out.iterdir()))


if __name__ == '__main__':
    unittest.main()
