"""Install only the stock-colour Cerbios animation on an identified Xbox HDD.

Called before Xemu opens the disk. No formatting, dashboard or BIOS changes.
Only the audited Cerbios 3.1.0 image is supported for automatic installation.
Existing files are backed up on E: before replacement; matching files are left.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

CERBIOS_310 = 'c5e9d940faf66692b56a16f7a7d779445c1c6d9191d7e7e31c1c1e8168da0733'
ANIMATION = '/Cerbios/BootAnims/Xbox/'
INI_PATH = '/Cerbios/cerbios.ini'
BOOT_PATH = r'HDD0-E:\Cerbios\BootAnims\Xbox\bootanim.xbe'


def validate_disk(path, bios):
    if hashlib.sha256(Path(bios).read_bytes()).hexdigest() != CERBIOS_310:
        raise ValueError('BIOS nao auditada para instalacao automatica da animacao')
    mode = os.stat(path).st_mode
    if not (stat.S_ISBLK(mode) or stat.S_ISREG(mode)):
        raise ValueError('HDD invalido')
    if stat.S_ISBLK(mode):
        mounts = subprocess.run(['lsblk', '-nrpo', 'MOUNTPOINTS', str(path)],
                                check=True, capture_output=True, text=True).stdout
        if mounts.strip():
            raise ValueError('HDD ou particao montada; nenhuma escrita permitida')
    with open(path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        if f.tell() < 0x1DD156000:
            raise ValueError('HDD menor que layout retail')
        for offset in (0x8CA80000, 0xABE80000):
            f.seek(offset)
            if f.read(4) != b'FATX':
                raise ValueError('C/E sem assinatura FATX; nenhuma escrita permitida')


def read_optional(fs, path):
    try:
        attr = fs.get_attr(path)
    except AssertionError:
        return None
    if not attr.is_file or attr.file_size > 2 * 1024 * 1024:
        raise ValueError('arquivo inesperado: ' + path)
    return bytes(fs.read(path))


def mkdirs(fs, path):
    current = ''
    for part in path.strip('/').split('/'):
        current += '/' + part
        try:
            attr = fs.get_attr(current)
        except AssertionError:
            fs.mkdir(current)
        else:
            if not attr.is_directory:
                raise ValueError('caminho nao e diretorio: ' + current)


def replace_verified(fs, path, data):
    old = read_optional(fs, path)
    if old == data:
        return False
    backup, stage = path + '.xrevive.bak', path + '.xrevive.new'
    if old is not None and read_optional(fs, backup) is None:
        fs.write(backup, old)
        if read_optional(fs, backup) != old:
            raise ValueError('backup nao confere: ' + path)
    if read_optional(fs, stage) is not None:
        fs.unlink(stage)
    fs.write(stage, data)
    if read_optional(fs, stage) != data:
        raise ValueError('arquivo temporario nao confere: ' + path)
    fs.rename(stage, path)
    if read_optional(fs, path) != data:
        raise ValueError('verificacao final falhou: ' + path)
    print('animacao: instalado E:' + path)
    return True


def configured_ini(data):
    # Preserve every unrelated Cerbios option and the original line endings.
    text = data.decode('latin1')
    value = 'BootAnimPath = ' + BOOT_PATH
    pattern = r'(?im)^[ \t]*BootAnimPath[ \t]*=[^\r\n]*'
    if re.search(pattern, text):
        text = re.sub(pattern, lambda match: value, text)
    else:
        ending = '\r\n' if '\r\n' in text else '\n'
        text += ending + value + ending
    return text.encode('latin1')


def install(fs, assets):
    assets = Path(assets)
    xbe = (assets/'BootAnim.xbe').read_bytes()
    ini = (assets/'bootanim.ini').read_bytes()
    if xbe[:4] != b'XBEH' or not 65536 <= len(xbe) <= 1048576:
        raise ValueError('BootAnim.xbe invalido')
    mkdirs(fs, ANIMATION)
    changed = replace_verified(fs, ANIMATION+'BootAnim.xbe', xbe)
    changed |= replace_verified(fs, ANIMATION+'bootanim.ini', ini)
    config = read_optional(fs, INI_PATH)
    # No INI is needed for the default E: fallback. Never inject a full INI
    # with storage/video settings that could break DVD or dashboard behavior.
    if config is not None:
        changed |= replace_verified(fs, INI_PATH, configured_ini(config))
    print('animacao: pronta' if changed else 'animacao: ja conferida; sem escrita')


def main(disk, bios, assets):
    validate_disk(disk, bios)
    from pyfatx import Fatx
    fs = Fatx(str(disk), drive='e')
    try:
        install(fs, assets)
    finally:
        del fs  # close FATX before Xemu starts
        os.sync()


if __name__ == '__main__':
    main(*sys.argv[1:])
