"""Read-only XDVDFS inspection and complete ISO identity for bundled media."""
import hashlib
import json
from pathlib import Path
import struct
import sys


def inspect(path):
    path = Path(path)
    length = path.stat().st_size
    files, directories = [], set()
    with path.open('rb') as f:
        f.seek(32 * 2048)
        descriptor = f.read(2048)
        if descriptor[:20] != b'MICROSOFT*XBOX*MEDIA':
            raise ValueError('ISO sem XDVDFS na particao de jogo esperada')
        root_sector, root_size = struct.unpack_from('<II', descriptor, 20)

        def directory(sector, size, parent=''):
            if (sector, size) in directories:
                raise ValueError('diretorio ciclico/duplicado na ISO')
            directories.add((sector, size))
            if size <= 0 or size > 16 * 1024 * 1024 or sector * 2048 + size > length:
                raise ValueError('tabela de diretorio fora da ISO')
            f.seek(sector * 2048)
            table = f.read(size)
            visited = set()

            def node(offset):
                if offset in visited or offset + 14 > size:
                    raise ValueError('entrada XDVDFS invalida')
                visited.add(offset)
                left, right, start, count, attrs, namesize = struct.unpack_from('<HHIIBB', table, offset)
                if offset + 14 + namesize > size or namesize == 0:
                    raise ValueError('nome XDVDFS invalido')
                name = table[offset+14:offset+14+namesize].decode('ascii')
                if '/' in name or '\\' in name or name in ('.', '..'):
                    raise ValueError('nome XDVDFS inseguro')
                if left:
                    node(left * 4)
                target = parent + '/' + name
                if start * 2048 + count > length:
                    raise ValueError('arquivo fora da ISO: ' + target)
                if attrs & 0x10:
                    if count:
                        directory(start, count, target)
                else:
                    files.append(dict(path=target, bytes=count, sector=start))
                if right:
                    node(right * 4)
            node(0)
        directory(root_sector, root_size)
        if not any(x['path'].lower() == '/default.xbe' for x in files):
            raise ValueError('default.xbe ausente na raiz')
        h = hashlib.sha256()
        f.seek(0)
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
    return dict(file='ogxbox.iso', bytes=length, sha256=h.hexdigest(),
                files=len(files), directories=len(directories), format='XDVDFS', inventory=files)


if __name__ == '__main__':
    print(json.dumps(inspect(sys.argv[1]), indent=2))
