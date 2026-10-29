import importlib.util
import os
import struct
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fatx',ROOT/'cartucho/overlay/usr/local/lib/console/fatx.py')
fatx=importlib.util.module_from_spec(spec);spec.loader.exec_module(fatx)


class FATXInstallerTests(unittest.TestCase):
    def test_native_empty_file_without_cluster_is_readable_but_nonempty_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);source=tmp/'files';source.mkdir();(source/'empty.txt').touch()
            disk=tmp/'volume';disk.write_bytes(bytes(2*1024**2));fd=os.open(disk,os.O_RDWR)
            try:
                fatx.format_tree(fd,0,disk.stat().st_size,source)
                volume=fatx.Volume(fd,0,disk.stat().st_size);entry=volume.find('empty.txt')
                os.pwrite(fd,struct.pack('<II',0,0),entry['at']+44)
                self.assertEqual(fatx.Volume(fd,0,disk.stat().st_size).read('empty.txt'),b'')
                os.pwrite(fd,struct.pack('<II',0,1),entry['at']+44)
                with self.assertRaisesRegex(ValueError,'cadeia FATX'):
                    fatx.Volume(fd,0,disk.stat().st_size).read('empty.txt')
            finally:os.close(fd)

    def test_large_trainer_directory_chains_and_boundary_sentinels(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);source=tmp/'files';source.mkdir();(source/'trainers').mkdir()
            for i in range(1100):(source/'trainers'/f'{i:04}.etm').write_bytes(str(i).encode())
            disk=tmp/'disk.img';size=32*1024**2
            with disk.open('wb') as f:f.write(b'A'*4096);f.truncate(size+8192);f.seek(size+4096);f.write(b'Z'*4096)
            fd=os.open(disk,os.O_RDWR)
            try:
                report=fatx.format_tree(fd,4096,size,source)
                volume=fatx.Volume(fd,4096,size)
                self.assertEqual(report['files'],1100)
                self.assertEqual(volume.verify(source),1100)
                self.assertEqual(volume.read('/trainers/1099.etm'),b'1099')
                self.assertEqual(os.pread(fd,4096,0),b'A'*4096)
                self.assertEqual(os.pread(fd,4096,size+4096),b'Z'*4096)
            finally:os.close(fd)

    def test_small_configuration_replacement_preserves_neighbor(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);source=tmp/'files';source.mkdir()
            (source/'Dashloader.ini').write_bytes(b'[Dashboard]\nPath = F:\\Dashboards\\XBMC4Gamers\\default.xbe\n')
            (source/'evoxdash.xbe').write_bytes(b'loader-binary')
            disk=tmp/'volume';disk.write_bytes(bytes(2*1024**2));fd=os.open(disk,os.O_RDWR)
            try:
                fatx.format_tree(fd,0,disk.stat().st_size,source)
                volume=fatx.Volume(fd,0,disk.stat().st_size)
                volume.replace('/Dashloader.ini',b'[Dashboard]\nPath = E:\\Recovery\\default.xbe\n')
                self.assertEqual(volume.read('/evoxdash.xbe'),b'loader-binary')
                self.assertIn(b'Recovery',volume.read('/Dashloader.ini'))
                with self.assertRaises(ValueError):volume.replace('/Dashloader.ini',bytes(20000))
            finally:os.close(fd)

    def test_invalid_tree_refuses_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);source=tmp/'files';source.mkdir();(source/('a'*43)).write_bytes(b'x')
            disk=tmp/'volume';disk.write_bytes(b'Z'*(1024**2));before=disk.read_bytes();fd=os.open(disk,os.O_RDWR)
            try:
                with self.assertRaises(ValueError):fatx.format_tree(fd,0,len(before),source)
                self.assertEqual(disk.read_bytes(),before)
            finally:os.close(fd)


if __name__=='__main__':unittest.main()
