"""Build an experimental standalone FILE from a completed USB release image.

Never accepts a physical target or changes the source. Default Xbox prefix is
16 GiB, followed by the appliance. Optional seed is a regular QA HDD image.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('standalone_layout', ROOT/'cartucho/overlay/usr/local/lib/console/standalone.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


def regular(path):
    if not stat.S_ISREG(Path(path).stat().st_mode):
        raise ValueError('somente arquivo regular: '+str(path))


def copy_range(source, target, source_offset, target_offset, count):
    with open(source, 'rb', buffering=0) as src, open(target, 'r+b', buffering=0) as dst:
        while count:
            amount = min(count, 16*1024**2)
            try:
                copied = os.copy_file_range(src.fileno(), dst.fileno(), amount, source_offset, target_offset)
            except OSError:
                src.seek(source_offset);dst.seek(target_offset)
                chunk = src.read(amount)
                if not chunk: raise ValueError('fonte truncada')
                dst.write(chunk);copied=len(chunk)
            if not copied: raise ValueError('copia truncada')
            source_offset += copied;target_offset += copied;count -= copied


def pack(source, output, guest_gib=16, seed=None):
    source, output = Path(source), Path(output)
    regular(source)
    if seed:
        regular(seed)
    source_meta = json.loads(source.with_suffix('.json').read_text())
    source_table = json.loads(subprocess.check_output(['sfdisk', '--json', str(source)], text=True))['partitiontable']
    parts = {p['name'].lower(): p for p in source_table['partitions']}
    xbox = Path(seed).stat().st_size if seed else guest_gib*1024**3
    data = dict(schema=1, experimental=True, xbox_bytes=xbox, build_id=source_meta['build_id'],
                base_variant=source_meta['variant'], source_sha256=source_meta['source_sha256'])
    disk_id = hashlib.sha256((source_meta['build_id']+'standalone').encode()).hexdigest()[:8]
    data['disk_id'] = disk_id
    current = xbox
    for name in ('system', 'console', 'cache', 'utils'):
        data[name] = dict(offset=current, bytes=parts[name]['size']*512)
        current += data[name]['bytes']
    data['image_bytes'] = current + layout.MIB
    layout.checked_layout(data)
    # O_EXCL prevents overwriting either a disk, prior image, or a symlink.
    with output.open('xb') as f:
        f.truncate(data['image_bytes'])
    try:
        if seed:
            copy_range(seed, output, 0, 0, xbox)
        for name in ('system', 'console', 'cache', 'utils'):
            copy_range(source, output, parts[name]['start']*512, data[name]['offset'], data[name]['bytes'])
        with output.open('r+b', buffering=0) as f:
            f.write(layout.sector0(data))
            f.seek(data['image_bytes']-layout.FOOTER_BYTES)
            f.write(layout.footer(data))
            os.fsync(f.fileno())
        metadata = dict(source_meta, variant='standalone', base_variant=source_meta['variant'],
                        experimental=True, xbox_bytes=xbox)
        with tempfile.TemporaryDirectory(prefix='xrv-standalone-') as tmp:
            tmp = Path(tmp)
            (tmp/'layout.json').write_text(json.dumps(data, indent=2)+'\n')
            (tmp/'build.json').write_text(json.dumps(metadata, indent=2)+'\n')
            uuid = (disk_id[:4]+'-'+disk_id[4:]).upper()
            cmdline = ('boot=live live-media=/dev/disk/by-partuuid/'+disk_id+'-04 toram quiet splash '
                       'xrevive.standalone=1 '
                       'loglevel=0 rd.udev.log_level=0 systemd.show_status=false '
                       'vt.global_cursor_default=0 console=tty0')
            (tmp/'grub.cfg').write_text('set timeout=0\nset timeout_style=hidden\ninsmod part_msdos\n'
                'insmod fat\nsearch --no-floppy --fs-uuid '+uuid+' --set=root\n'
                'set cmdline="'+cmdline+'"\n'
                'if [ -f /debug ]; then\n'
                ' set cmdline="$cmdline systemd.debug_shell=ttyS0 systemd.mask=serial-getty@ttyS0.service"\nfi\n'
                'linux /live/vmlinuz $cmdline\ninitrd /live/initrd.img\nboot\n')
            subprocess.run(['grub-mkstandalone','-O','x86_64-efi','-o',str(tmp/'BOOTX64.EFI'),
                            'boot/grub/grub.cfg='+str(tmp/'grub.cfg')],check=True)
            system = str(output)+'@@'+str(data['system']['offset'])
            subprocess.run(['mlabel','-i',system,'-N',disk_id,'::SYSTEM'],check=True)
            subprocess.run(['mcopy','-o','-i',system,str(tmp/'BOOTX64.EFI'),'::/EFI/BOOT/BOOTX64.EFI'],check=True)
            subprocess.run(['mcopy','-o','-i',system,str(tmp/'layout.json'),'::/xrevive-standalone.json'],check=True)
            console = str(output)+'@@'+str(data['console']['offset'])
            subprocess.run(['mcopy','-o','-i',console,str(tmp/'build.json'),'::/config/build.json'],check=True)
        layout.read_verified(output, data)
        parsed = json.loads(subprocess.check_output(['sfdisk','--json',str(output)],text=True))['partitiontable']
        if len(parsed['partitions']) != 1 or parsed['partitions'][0]['start']*512 != xbox:
            raise ValueError('MBR nao identificou ESP no limite esperado')
        output.with_suffix('.json').write_text(json.dumps(metadata, indent=2)+'\n')
        output.with_suffix('.layout.json').write_text(json.dumps(data, indent=2)+'\n')
        output.with_suffix('.packages.txt').write_bytes(source.with_suffix('.packages.txt').read_bytes())
        print('standalone experimental:', output, data['image_bytes'], 'bytes; Xbox', xbox, flush=True)
        return data
    except Exception:
        # Keep failed artifacts for diagnosis; never clean or alter the source.
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--guest-gib',type=int,default=16)
    parser.add_argument('--seed-hdd',help='imagem de HDD virtual para QA; nunca dispositivo fisico')
    args = parser.parse_args()
    pack(args.source,args.output,args.guest_gib,args.seed_hdd)
