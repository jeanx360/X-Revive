"""Small deterministic XDVDFS writer and bounded boot-disc validation.

Only regular files in a verified download tree are written into a new regular
ISO. Never opens a block device. Directory entries are balanced prefix trees.
"""
import os
from pathlib import Path
import shutil
import stat
import struct

SECTOR=2048
MAGIC=b'MICROSOFT*XBOX*MEDIA'


def align(n,b=SECTOR):return (n+b-1)//b*b


def inspect(path,require_boot=True):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or not 34*SECTOR<=info.st_size<=16*1024**3:
            raise ValueError('Mídia Xbox deve ser arquivo regular entre 68 KiB e 16 GiB')
        # XISO trimmed, Redump/full DVD and older DVD layouts. Xemu expects
        # the Xbox partition at byte zero, so the caller maps this offset.
        base=None
        for candidate in (0,0x18300000,0xfd90000):
            f.seek(candidate+32*SECTOR);header=f.read(SECTOR)
            if header[:20]==MAGIC and header[-20:]==MAGIC:
                base=candidate;break
        if base is None:raise ValueError('Sem partição Xbox XDVDFS; verificando ISO de arquivos/coleção')
        sector,size=struct.unpack_from('<II',header,20)
        if not 0<size<=256*1024 or sector<33 or base+sector*SECTOR+size>info.st_size:
            raise ValueError('Diretório raiz XISO inválido')
        f.seek(base+sector*SECTOR);table=f.read(size);pending=[0];seen=set()
        # Walk both branches. A valid disc must not be rejected because its
        # mastering tool used a different case/collation order from Python.
        while pending:
            offset=pending.pop()
            if offset in seen or offset+14>len(table):raise ValueError('Árvore XISO inválida')
            seen.add(offset)
            left,right,start,length,attr,n=struct.unpack_from('<HHIIBB',table,offset)
            if offset+14+n>len(table):raise ValueError('Nome XISO inválido')
            name=table[offset+14:offset+14+n].upper()
            if name==b'DEFAULT.XBE':
                if attr&16 or length<4 or base+start*SECTOR+length>info.st_size:break
                f.seek(base+start*SECTOR)
                if f.read(4)!=b'XBEH':break
                return dict(bytes=info.st_size,offset=base,disc_bytes=info.st_size-base,default_xbe_bytes=length)
            pending.extend(branch*4 for branch in (left,right) if branch)
        if not require_boot:
            return dict(bytes=info.st_size,offset=base,disc_bytes=info.st_size-base,default_xbe_bytes=0,
                        boot_warning='Sem default.xbe validado na raiz; o boot será decidido pela BIOS da sessão')
        raise ValueError('Partição Xbox sem default.xbe iniciável na raiz; verifique a integridade da cópia da mídia')


def plan(root,aliases=None,renames=None):
    root=Path(root)
    nodes=[]
    def tree(path,name=None,top=False):
        if path.is_symlink():raise ValueError('Links não são permitidos no disco LIVE')
        node=dict(path=path,name=name or path.name,children=[],records=[],offset=0,size=0)
        if path.is_dir():
            entries={p.name:p for p in path.iterdir()}
            if top:entries.update(aliases or {})
            entries=sorted((((renames or {}).get(str(p),label),p) for label,p in entries.items()),key=lambda row:row[0].upper())
            names=set()
            for label,p in entries:
                name=label.encode('cp1252')
                if not 0<len(name)<=255 or label.upper() in names:raise ValueError('Nome XISO inválido/duplicado')
                names.add(label.upper());node['children'].append(tree(p,label))
            cursor=0
            def layout(items):
                nonlocal cursor
                if not items:return 0
                mid=len(items)//2;item=items[mid]
                length=align(14+len(item['name'].encode('cp1252')),4)
                if cursor%SECTOR+length>SECTOR:cursor=align(cursor)
                here=cursor;cursor+=length
                left=layout(items[:mid]);right=layout(items[mid+1:])
                node['records'].append((item,here,left,right));return here
            layout(node['children']);node['size']=cursor
            if node['size']>256*1024:raise ValueError('Diretório XISO grande demais')
        elif path.is_file():node['size']=path.stat().st_size
        else:raise ValueError('Entrada não regular')
        nodes.append(node);return node
    top=tree(root,top=True)
    # Allocate parents first, then files; offsets are known before serialization.
    nodes.reverse();position=33*SECTOR
    for node in nodes:node['offset']=position;position+=align(node['size'])
    header=bytearray(SECTOR);header[:20]=MAGIC;header[-20:]=MAGIC
    struct.pack_into('<II',header,20,top['offset']//SECTOR,top['size'])
    segments=[dict(offset=32*SECTOR,bytes=SECTOR,data=bytes(header))]
    for node in nodes:
        if not node['size']:continue
        if not node['path'].is_dir():
            segments.append(dict(offset=node['offset'],bytes=node['size'],path=node['path']));continue
        table=bytearray(b'\xff'*node['size'])
        for item,here,left,right in node['records']:
            name=item['name'].encode('cp1252')
            struct.pack_into('<HHIIBB',table,here,left//4,right//4,item['offset']//SECTOR,
                             item['size'],16 if item['path'].is_dir() else 32,len(name))
            table[here+14:here+14+len(name)]=name
        segments.append(dict(offset=node['offset'],bytes=len(table),data=bytes(table)))
    return align(position,32*SECTOR),sorted(segments,key=lambda item:item['offset'])


def build(root,destination,aliases=None,renames=None):
    total,segments=plan(root,aliases,renames)
    with Path(destination).open('xb') as out:
        out.truncate(total)
        for item in segments:
            out.seek(item['offset'])
            if 'data' in item:out.write(item['data'])
            else:
                with item['path'].open('rb') as src:shutil.copyfileobj(src,out,1024**2)
        out.flush();os.fsync(out.fileno())
    return inspect(destination)
