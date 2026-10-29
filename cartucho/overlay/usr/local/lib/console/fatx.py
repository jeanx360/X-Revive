"""Bounded FATX bulk formatter/reader for installation and verification.

Native retail offsets are supplied by standalone.py. Geometry follows FATX's
4096-byte superblock/FAT alignment, FAT16/32 threshold and 64-byte directory
entries (documented by mborgerson/fatx). Directory chains are allocated in one
pass, including large trainer directories; no incremental directory extension.
This module has no command line accepting physical disks.
"""
import hashlib
import math
import os
from pathlib import Path
import struct
import unicodedata


def metadata_filename(name):
    """Native Xbox APIs reject punctuation accepted by some raw FATX writers.

    Used only for optional synopsis TXT metadata, never executable/resources.
    Keep bytes unchanged and give changed names a deterministic collision suffix.
    """
    allowed=set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&'()-.@[]^_`{}~ ")
    converted=unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode()
    converted=''.join(c for c in converted if c in allowed).strip(' .')
    if converted==name and len(name)<=42:return name
    stem,ext=os.path.splitext(converted)
    stem=(stem or 'metadata')[:31].rstrip(' .')
    return stem+'-'+hashlib.sha256(name.encode()).hexdigest()[:6]+ext[:4]


def geometry(size, cluster=16384):
    if cluster not in (16384, 32768, 65536):
        raise ValueError('cluster FATX não suportado')
    count = size//cluster+1
    width = 2 if count < 0xfff0 else 4
    fat = ((count*width+4095)//4096)*4096
    available = (size-4096-fat)//cluster
    if available > 0xffffef:
        raise ValueError('partição excede limite de clusters FATX')
    return width, fat, available


def cluster_size(size):
    # Conservative extended-partition geometry: <=256/512/1024 GiB.
    for cluster in (16384, 32768, 65536):
        if (size+cluster-1)//cluster <= 0xffff00:
            return cluster
    raise ValueError('partição acima de 1 TiB exige F/G; não suportada ainda')


def valid_path(path):
    components = path.strip('/').split('/') if path.strip('/') else []
    for name in components:
        raw = name.encode('cp1252')
        if not 1 <= len(raw) <= 42 or name in ('.', '..') or any(c in name for c in '\\:*?"<>|'):
            raise ValueError('nome incompatível com FATX: '+path)
    if len(path.encode('cp1252')) > 250:
        raise ValueError('caminho FATX longo: '+path)
    return components


def tree(source):
    root = dict(name='', children={}, file=None)
    for path in sorted(Path(source).rglob('*')):
        if path.is_symlink(): raise ValueError('symlink no pacote')
        parts = valid_path(path.relative_to(source).as_posix())
        cur = root
        for index, part in enumerate(parts):
            key = part.casefold()
            last = index == len(parts)-1
            if key not in cur['children']:
                cur['children'][key] = dict(name=part, children={}, file=None)
            node = cur['children'][key]
            if node['name'] != part: raise ValueError('colisão de caixa FATX: '+str(path))
            if last and path.is_file():
                node['file'] = path
                node['size'] = path.stat().st_size
                if node['size'] >= 2**32: raise ValueError('arquivo FATX >=4 GiB')
            cur = node
    return root


def metadata_tree(source, files, directories=()):
    """Preflight a locked manifest without slow USB directory traversal."""
    root=dict(name='',children={},file=None)
    def add(path,size=None):
        cur=root
        for name in valid_path(path):
            key=name.casefold()
            if key not in cur['children']:cur['children'][key]=dict(name=name,children={},file=None)
            cur=cur['children'][key]
            if cur['name']!=name:raise ValueError('colisão de caixa FATX')
        if size is not None:
            if not 0<=size<2**32:raise ValueError('arquivo FATX >=4 GiB')
            cur.update(file=Path(source)/path,size=size)
    for path in directories:add(path)
    for item in files:add(item['path'],item['bytes'])
    return root


def plan(source, size, cluster=None, files=None, directories=()):
    cluster = cluster or cluster_size(size)
    width, fat_size, available = geometry(size, cluster)
    root = tree(source) if files is None else metadata_tree(source,files,directories)
    next_cluster = 1
    nodes = []

    def assign(node):
        nonlocal next_cluster
        if node['file'] is None:
            if len(node['children']) > 4095: raise ValueError('diretório FATX cheio')
            count = max(1, math.ceil((len(node['children'])+1)*64/cluster))
        else:
            count = max(1, math.ceil(node['size']/cluster))
        node.update(first=next_cluster, clusters=count)
        next_cluster += count
        nodes.append(node)
        for child in node['children'].values(): assign(child)
    assign(root)
    if next_cluster-1 > available: raise ValueError('pacotes não cabem na partição FATX')
    return dict(root=root, nodes=nodes, used=next_cluster-1, width=width,
                fat_size=fat_size, cluster=cluster, size=size)


def format_tree(fd, offset, size, source, progress=lambda *_: None):
    prepared = plan(source, size)
    width, fat_size, cluster = (prepared[k] for k in ('width', 'fat_size', 'cluster'))
    data_start = offset+4096+fat_size
    mask = (1 << (8*width))-1
    fmt = '<H' if width == 2 else '<I'
    fat = bytearray(fat_size)
    struct.pack_into(fmt, fat, 0, 0xfffffff8 & mask)
    for node in prepared['nodes']:
        first, count = node['first'], node['clusters']
        for c in range(first, first+count):
            value = c+1 if c < first+count-1 else mask
            struct.pack_into(fmt, fat, c*width, value)
    # Prepare all metadata/capacity checks before the first write.
    def write(at, data):
        if at < offset or at+len(data) > offset+size: raise ValueError('escrita fora da partição')
        done = 0
        while done < len(data):
            n = os.pwrite(fd, data[done:], at+done)
            if n <= 0: raise OSError('escrita FATX incompleta')
            done += n
    # Invalid signature until all data and metadata have reached the disk.
    write(offset, bytes(4096))
    write(offset+4096, fat)
    total = len(prepared['nodes'])
    for index, node in enumerate(prepared['nodes']):
        at = data_start+(node['first']-1)*cluster
        if node['file'] is None:
            directory = bytearray(b'\xff'*(node['clusters']*cluster))
            for j, child in enumerate(node['children'].values()):
                name = child['name'].encode('cp1252')
                attrs = 0x10 if child['file'] is None else 0x20
                date = (26 << 9) | (10 << 5) | 23  # FATX epoch 2000
                struct.pack_into('<BB42sII6H', directory, j*64, len(name), attrs,
                    name.ljust(42,b'\xff'), child['first'], child.get('size',0),
                    0, date, 0, date, 0, date)
            write(at, directory)
        else:
            with node['file'].open('rb') as source_file:
                remaining = node['size']
                while remaining:
                    block = source_file.read(min(remaining,1024**2))
                    if not block: raise OSError('arquivo fonte truncado')
                    write(at, block); at += len(block); remaining -= len(block)
                padding = node['clusters']*cluster-node['size']
                if padding: write(at, bytes(padding))
        if index % 200 == 0: progress(index, total)
    os.fsync(fd)
    block = bytearray(b'\xff'*4096)
    struct.pack_into('<4sIIII', block, 0, b'FATX', 0x58525632, cluster//512, 1, 0)
    write(offset, block)
    os.fsync(fd)
    progress(total,total)
    return dict(files=sum(n['file'] is not None for n in prepared['nodes']),
                cluster_bytes=cluster, used_bytes=prepared['used']*cluster)


class Volume:
    def __init__(self, fd, offset, size):
        self.fd, self.offset, self.size = fd, offset, size
        magic, _, sectors, self.root = struct.unpack('<4sIII', self.read_at(offset,16))
        if magic != b'FATX': raise ValueError('FATX ausente')
        self.cluster = sectors*512
        self.width, self.fat_size, self.available = geometry(size,self.cluster)
        self.data = offset+4096+self.fat_size
        self.fat = self.read_at(offset+4096,self.fat_size)
        self.dir_cache = {}

    def read_at(self, at, count):
        if at < self.offset or at+count > self.offset+self.size: raise ValueError('leitura fora da partição')
        data = os.pread(self.fd,count,at)
        if len(data) != count: raise OSError('FATX truncado')
        return data

    def chain(self, first):
        seen = set()
        while first < (0xfff0 if self.width==2 else 0xfffffff0):
            if not 1 <= first <= self.available or first in seen: raise ValueError('cadeia FATX inválida')
            seen.add(first);yield first
            first = int.from_bytes(self.fat[first*self.width:(first+1)*self.width], 'little')

    def directory(self, first):
        for cluster in self.chain(first):
            at = self.data+(cluster-1)*self.cluster
            raw = self.read_at(at,self.cluster)
            for i in range(0,len(raw),64):
                n = raw[i]
                if n in (0,255): return
                if n == 0xe5: continue
                if n > 42: raise ValueError('entrada FATX inválida')
                name = raw[i+2:i+2+n].decode('cp1252')
                first,size = struct.unpack_from('<II',raw,i+44)
                yield dict(name=name,first=first,size=size,directory=bool(raw[i+1]&16),at=at+i)

    def find(self, path):
        current = dict(first=self.root,directory=True)
        for part in valid_path(path):
            if not current['directory']: raise ValueError('não é diretório')
            first=current['first']
            if first not in self.dir_cache:
                self.dir_cache[first]={n['name'].casefold():n for n in self.directory(first)}
            current = self.dir_cache[first].get(part.casefold())
            if current is None: raise FileNotFoundError(path)
        return current

    def chunks(self, path):
        item = self.find(path)
        if item['directory']: raise IsADirectoryError(path)
        remaining = item['size']
        # Native Xbox formatters may leave empty files with no allocated cluster.
        if not remaining: return
        for c in self.chain(item['first']):
            if not remaining: break
            block = self.read_at(self.data+(c-1)*self.cluster,min(remaining,self.cluster))
            remaining -= len(block);yield block
        if remaining: raise ValueError('cadeia menor que arquivo')

    def read(self, path):
        return b''.join(self.chunks(path))

    def replace(self, path, data):
        """Replace a small existing config, never allocate/delete/format."""
        item = self.find(path)
        clusters = list(self.chain(item['first']))
        if item['directory'] or len(data)>len(clusters)*self.cluster:
            raise ValueError('configuração maior que espaço reservado')
        for index,c in enumerate(clusters):
            block = data[index*self.cluster:(index+1)*self.cluster].ljust(self.cluster,b'\0')
            os.pwrite(self.fd,block,self.data+(c-1)*self.cluster)
        os.pwrite(self.fd,struct.pack('<I',len(data)),item['at']+48)
        os.fsync(self.fd)
        self.dir_cache.clear()

    def verify(self, source):
        count = 0
        for path in sorted(Path(source).rglob('*')):
            relative = path.relative_to(source).as_posix()
            item = self.find(relative)
            if path.is_dir():
                if not item['directory']: raise ValueError(relative)
                continue
            actual = hashlib.sha256()
            for chunk in self.chunks(relative): actual.update(chunk)
            expected = hashlib.sha256()
            with path.open('rb') as f:
                while chunk:=f.read(1024**2):expected.update(chunk)
            if actual.digest()!=expected.digest():raise ValueError('verificação FATX falhou: '+relative)
            count += 1
        return count
