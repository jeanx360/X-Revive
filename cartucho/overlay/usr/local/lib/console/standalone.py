"""Experimental single-disk layout, mapping and boot-record repair.

FATX remains at its native offsets. MBR entry 4 describes an ESP after a
bounded Xbox region. The remaining appliance filesystems are mapped by offset.
No GPT, resizing, physical installation or automatic migration is performed.
"""
import argparse
import binascii
import json
import os
from pathlib import Path
import stat
import struct
import subprocess

MIB = 1024**2
MAGIC = b'XRVSTANDALONE01\0'
PARTINFO = b'****PARTINFO****'
FOOTER_BYTES = 4096
PRIVATE_STATE = Path('/run/xrevive-standalone')
RETAIL = [('XBOX MUSIC', 0xABE80000, 0x1312D6000),
          ('XBOX SYSTEM', 0x8CA80000, 0x1F400000),
          ('XBOX GAME SWAP 1', 0x80000, 0x2EE00000),
          ('XBOX GAME SWAP 2', 0x2EE80000, 0x2EE00000),
          ('XBOX GAME SWAP 3', 0x5DC80000, 0x2EE00000)]
F_OFFSET = 0x1DD156000


def checked_layout(data):
    if data.get('schema') != 1 or data.get('experimental') is not True:
        raise ValueError('layout standalone nao reconhecido')
    xbox = data['xbox_bytes']
    if type(xbox) is not int or xbox < 10*1024**3 or xbox % MIB:
        raise ValueError('limite Xbox invalido')
    current = xbox
    for name in ('system', 'console', 'cache', 'utils'):
        part = data[name]
        if any(type(part.get(k)) is not int for k in ('offset', 'bytes')):
            raise ValueError('geometria nao numerica')
        if part['offset'] != current or part['bytes'] < MIB or part['bytes'] % MIB:
            raise ValueError('regioes sobrepostas/desalinhadas')
        current += part['bytes']
    if data['image_bytes'] != current + MIB or data['image_bytes'] >= 2**41:
        raise ValueError('tamanho fora do prototipo MBR <2 TiB')
    if not isinstance(data['disk_id'], str) or len(data['disk_id']) != 8:
        raise ValueError('identidade MBR invalida')
    int(data['disk_id'], 16)
    if data.get('existing_fatx'):
        regions=data.get('native_regions',[])
        if not isinstance(regions,list) or not 5<=len(regions)<=7:raise ValueError('mapa FATX existente ausente')
        if not all(isinstance(r,dict) for r in regions):raise ValueError('mapa FATX existente inválido')
        if {r.get('drive') for r in regions} not in ({'e','c','x','y','z'},{'e','c','x','y','z','f'},{'e','c','x','y','z','f','g'}):
            raise ValueError('mapa de unidades FATX inválido')
        for r in regions:
            if any(type(r.get(k)) is not int for k in ('offset','bytes')) or r['offset']<0x80000 or r['bytes']<4096 or r['offset']+r['bytes']>xbox:
                raise ValueError('FATX invade o sistema')
        ordered=sorted(regions,key=lambda r:r['offset'])
        if any(a['offset']+a['bytes']>b['offset'] for a,b in zip(ordered,ordered[1:])):
            raise ValueError('FATX existente sobreposto')
    return data


def footer(data):
    checked_layout(data)
    payload = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
    if len(payload) > FOOTER_BYTES-24:
        raise ValueError('manifesto grande demais')
    return (MAGIC + struct.pack('<II', len(payload), binascii.crc32(payload))
            + payload).ljust(FOOTER_BYTES, b'\0')


def decode_footer(block):
    if len(block) != FOOTER_BYTES or block[:16] != MAGIC:
        raise ValueError('assinatura standalone ausente')
    length, crc = struct.unpack_from('<II', block, 16)
    if length > FOOTER_BYTES-24:
        raise ValueError('manifesto truncado')
    payload = block[24:24+length]
    if binascii.crc32(payload) != crc:
        raise ValueError('CRC standalone nao confere')
    return checked_layout(json.loads(payload))


def sector0(data):
    checked_layout(data)
    result = bytearray(512)
    result[:16] = PARTINFO
    for i, (name, offset, size) in enumerate(RETAIL + extended(data)):
        struct.pack_into('<16sIIII', result, 48+i*32, name.encode().ljust(16, b' '),
                         0x80000000, offset//512, size//512, 0)
    return repair_sector(bytes(result), data)


def extended(data):
    remaining = data['xbox_bytes']-F_OFFSET
    if remaining <= 1023*1024**3:
        return [('DRIVE F:', F_OFFSET, remaining)]
    first = (remaining//2//MIB)*MIB
    return [('DRIVE F:', F_OFFSET, first),
            ('DRIVE G:', F_OFFSET+first, remaining-first)]


def repair_sector(original, data):
    checked_layout(data)
    if len(original) != 512 or original[:16] != PARTINFO:
        raise ValueError('tabela Xbox ausente; reparo automatico recusado')
    active = []
    for i in range(14):
        _, flags, start, count, _ = struct.unpack_from('<16sIIII', original, 48+i*32)
        if flags & 0x80000000:
            if i >= 12 or count == 0 or start < 1024 or (start+count)*512 > data['xbox_bytes']:
                raise ValueError('particao Xbox invade area protegida/reservada')
            if i < 5 and (start*512, count*512) != RETAIL[i][1:]:
                raise ValueError('particao retail deslocada')
            active.append((start, start+count))
    active.sort()
    if any(left[1] > right[0] for left, right in zip(active, active[1:])):
        raise ValueError('particoes Xbox sobrepostas')
    result = bytearray(original)
    # These fields touch only the last two INACTIVE Xbox entries. Active
    # entries 1..12 stay intact. MBR record 4 starts at byte 494; its first
    # two zero bytes preserve the end of the 496-byte Xbox table.
    result[440:444] = bytes.fromhex(data['disk_id'])[::-1]
    result[446:494] = b'\0'*48
    struct.pack_into('<B3sB3sII', result, 494, 0, b'\0'*3, 0xEF, b'\0'*3,
                     data['system']['offset']//512, data['system']['bytes']//512)
    result[510:512] = b'\x55\xaa'
    return bytes(result)


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def read_verified(device, data):
    checked_layout(data)
    with open(device, 'rb') as f:
        f.seek(0, os.SEEK_END)
        if f.tell() < data['image_bytes']:
            raise ValueError('disco menor que layout')
        f.seek(data['image_bytes']-FOOTER_BYTES)
        if decode_footer(f.read(FOOTER_BYTES)) != data:
            raise ValueError('manifestos do boot e rodape divergem')
        f.seek(0)
        original = f.read(512)
        repair_sector(original, data)  # also validates all active Xbox ranges
    return original


def is_container(device):
    """Read-only guard for USB mode: never expose a known combined SSD raw.

    Also recognizes a lost MBR when native PARTINFO still points to SYSTEM.
    This is detection, not permission to repair or migrate an existing disk.
    """
    with open(device, 'rb', buffering=0) as disk:
        first = disk.read(512)
        if len(first) != 512 or first[:16] != PARTINFO:
            return False
        if first[498] == 0xEF and first[510:512] == b'\x55\xaa':
            return True
        ends = []
        for i in range(14):
            _, flags, start, count, _ = struct.unpack_from('<16sIIII', first, 48+i*32)
            if flags & 0x80000000:
                ends.append((start+count)*512)
        if not ends or max(ends) < 10*1024**3 or max(ends) % MIB:
            return False
        disk.seek(max(ends))
        boot = disk.read(512)
        return (len(boot) == 512 and boot[71:82] == b'SYSTEM     '
                and boot[82:90] == b'FAT32   ' and boot[510:512] == b'\x55\xaa')


def loop(device, offset, size):
    return run('losetup', '--find', '--show', '--offset', str(offset),
               '--sizelimit', str(size), str(device))


def prepare(run_dir):
    run_dir = Path(run_dir)
    cmdline = Path('/proc/cmdline').read_text().split()
    if 'xrevive.standalone=1' not in cmdline:
        return  # USB/recovery images never silently adopt another disk's layout
    # Prefer the exact device requested by the standalone GRUB, not an
    # arbitrary duplicate SYSTEM label on a recovery USB.
    requested = [w.split('=', 1)[1] for w in cmdline
                 if w.startswith('live-media=')]
    medium = requested[0] if requested and requested[0].startswith('/dev/') else ''
    if not medium or not Path(medium).exists():
        medium = run('blkid', '-L', 'SYSTEM')
    mountpoint = run_dir/'boot-media'
    mountpoint.mkdir(exist_ok=True)
    subprocess.run(['mount', '-o', 'ro', medium, str(mountpoint)], check=True)
    manifest = mountpoint/'xrevive-standalone.json'
    if not manifest.is_file():
        subprocess.run(['umount', str(mountpoint)], check=True)
        return
    data = checked_layout(json.loads(manifest.read_text()))
    part = Path(medium).resolve()
    parent = run('lsblk', '-dnro', 'PKNAME', str(part))
    device = '/dev/'+parent
    if not parent or not stat.S_ISBLK(os.stat(device).st_mode):
        raise ValueError('boot nao esta em uma particao de disco')
    start = int(Path('/sys/class/block', part.name, 'start').read_text())*512
    size = int(Path('/sys/class/block', part.name, 'size').read_text())*512
    if (start, size) != (data['system']['offset'], data['system']['bytes']):
        raise ValueError('ESP real nao corresponde ao manifesto')
    read_verified(device, data)
    mapped = []
    try:
        mappings = {}
        for name in ('console', 'cache', 'utils'):
            region = data[name]
            mappings[name+'_device'] = loop(device, region['offset'], region['bytes'])
            mapped.append(mappings[name+'_device'])
        mappings['xbox_device'] = loop(device, 0, data['xbox_bytes'])
        mapped.append(mappings['xbox_device'])
        mappings.update(boot_device=device, layout=data)
        PRIVATE_STATE.mkdir(mode=0o700, exist_ok=True)
        PRIVATE_STATE.chmod(0o700)
        (PRIVATE_STATE/'state.json').write_text(json.dumps(mappings, indent=2)+'\n')
        (PRIVATE_STATE/'state.json').chmod(0o600)
        (run_dir/'standalone.json').write_text(json.dumps(mappings, indent=2)+'\n')
        print('standalone: prefixo Xbox limitado a', data['xbox_bytes'], 'bytes')
    except Exception:
        for mapped_device in reversed(mapped):
            subprocess.run(['losetup', '-d', mapped_device], check=False)
        raise


def finalize(run_dir):
    state = PRIVATE_STATE/'state.json'
    if not state.exists():
        return
    info = json.loads(state.read_text())
    device, data = info['boot_device'], info['layout']
    original = read_verified(device, data)
    repaired = repair_sector(original, data)
    if original != repaired:
        # Only the boot fields in two inactive entries and MBR signature
        # are restored, after Xemu has closed. No partition is moved/resized.
        with open(device, 'r+b', buffering=0) as f:
            f.write(repaired)
            os.fsync(f.fileno())
        print('standalone: campos UEFI/MBR restaurados apos fechar o guest')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'finalize', 'field', 'is-container'))
    parser.add_argument('run_dir')
    parser.add_argument('field', nargs='?')
    args = parser.parse_args()
    if args.action == 'is-container':
        raise SystemExit(0 if is_container(args.run_dir) else 1)
    elif args.action == 'field':
        info = json.loads((Path(args.run_dir)/'standalone.json').read_text())
        if args.field not in ('console_device', 'cache_device', 'utils_device', 'xbox_device', 'boot_device'):
            raise ValueError('campo invalido')
        print(info[args.field])
    else:
        globals()[args.action](args.run_dir)
