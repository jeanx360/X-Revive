import copy
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('layout', ROOT/'cartucho/overlay/usr/local/lib/console/standalone.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


def example():
    data = dict(schema=1, experimental=True, xbox_bytes=16*1024**3, disk_id='12345678')
    current = data['xbox_bytes']
    for name, mib in (('system',2048), ('console',640), ('cache',1024), ('utils',4864)):
        data[name] = dict(offset=current, bytes=mib*layout.MIB)
        current += data[name]['bytes']
    data['image_bytes'] = current + layout.MIB
    return data


class StandaloneTest(unittest.TestCase):
    def test_both_tables_share_sector_without_changing_active_fatx_entries(self):
        data = example()
        block = layout.sector0(data)
        self.assertEqual(block[:16], layout.PARTINFO)
        self.assertEqual(block[446:494], b'\0'*48)
        self.assertEqual(block[510:], b'\x55\xaa')
        self.assertEqual(block[498], 0xef)
        self.assertEqual(struct.unpack_from('<II',block,502),
                         (data['xbox_bytes']//512,data['system']['bytes']//512))
        for i in range(6):
            name, flags, start, count, _ = struct.unpack_from('<16sIIII',block,48+i*32)
            self.assertEqual(flags,0x80000000)
            self.assertLessEqual((start+count)*512,data['xbox_bytes'])
        self.assertEqual(layout.repair_sector(block,data),block)

    def test_restore_boot_fields_after_guest_rewrites_native_table(self):
        data = example()
        original = layout.sector0(data)
        native = bytearray(original)
        native[440:512] = b'\0'*72
        fixed = layout.repair_sector(bytes(native),data)
        self.assertEqual(fixed[:432],bytes(native[:432]))
        self.assertEqual(fixed,original)

    def test_refuse_table_entry_into_system_or_reserved_slot(self):
        data = example()
        for index in (5,12,13):
            block=bytearray(layout.sector0(data))
            struct.pack_into('<16sIIII',block,48+index*32,b'INVALID',0x80000000,
                             data['xbox_bytes']//512,2048,0)
            with self.assertRaisesRegex(ValueError,'invade'):
                layout.repair_sector(bytes(block),data)

    def test_refuse_overlapping_manifest_and_corrupt_footer(self):
        data=example()
        bad=copy.deepcopy(data);bad['console']['offset']-=layout.MIB
        with self.assertRaises(ValueError): layout.checked_layout(bad)
        block=bytearray(layout.footer(data));block[30]^=1
        with self.assertRaisesRegex(ValueError,'CRC'):layout.decode_footer(bytes(block))
        self.assertEqual(layout.decode_footer(layout.footer(data)),data)

    def test_refuse_active_xbox_partitions_overlapping_each_other(self):
        data=example(); block=bytearray(layout.sector0(data))
        struct.pack_into('<16sIIII',block,48+6*32,b'DRIVE G:',0x80000000,
                         layout.F_OFFSET//512,2048,0)
        with self.assertRaisesRegex(ValueError,'sobrepostas'):
            layout.repair_sector(bytes(block),data)

    def test_inspection_and_validation_never_modify_the_disk(self):
        data=example()
        with tempfile.TemporaryDirectory() as tmp:
            disk=Path(tmp)/'standalone.img'
            with disk.open('wb') as f:
                f.truncate(data['image_bytes']);f.seek(0);f.write(layout.sector0(data))
                f.seek(data['image_bytes']-4096);f.write(layout.footer(data))
            before=disk.stat().st_mtime_ns
            self.assertEqual(layout.read_verified(disk,data),layout.sector0(data))
            self.assertEqual(disk.stat().st_mtime_ns,before)
            with disk.open('r+b') as f:
                f.seek(data['image_bytes']-4096);f.write(b'BAD')
            with self.assertRaises(ValueError):layout.read_verified(disk,data)

    def test_usb_guard_recognizes_combined_disk_even_after_mbr_loss(self):
        data=example()
        with tempfile.TemporaryDirectory() as tmp:
            disk=Path(tmp)/'combined.img'
            with disk.open('wb') as f:
                f.write(layout.sector0(data))
            self.assertTrue(layout.is_container(disk))
            native=bytearray(layout.sector0(data));native[440:512]=b'\0'*72
            with disk.open('r+b') as f:
                f.write(native);f.seek(data['system']['offset'])
                boot=bytearray(512);boot[71:82]=b'SYSTEM     ';boot[82:90]=b'FAT32   '
                boot[510:512]=b'\x55\xaa';f.write(boot)
            self.assertTrue(layout.is_container(disk))
            with disk.open('r+b') as f:
                f.seek(data['system']['offset']);f.write(b'\0'*512)
            self.assertFalse(layout.is_container(disk))


if __name__ == '__main__': unittest.main()
