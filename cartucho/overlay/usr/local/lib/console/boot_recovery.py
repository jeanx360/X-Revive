"""Recover the reserved X-Revive layout from its ESP, without modifying disks."""
import json
import os
import subprocess

import standalone


def recover(path,size,regions):
    end=max(r['offset']+r['bytes'] for r in regions)
    offsets={((end+1048575)//1048576)*1048576}
    with open(path,'rb',buffering=0) as source:
        first=source.read(512)
        for i in range(4):
            at=446+16*i
            if first[at+4]==0xEF:
                offsets.add(int.from_bytes(first[at+8:at+12],'little')*512)
        for offset in sorted(offsets):
            if offset<end or offset+1048576>size:continue
            source.seek(offset);boot=source.read(512)
            if boot[510:512]!=b'\x55\xaa' or boot[82:90]!=b'FAT32   ':continue
            try:
                result=subprocess.run(['mtype','-i',str(path)+'@@'+str(offset),'::/xrevive-standalone.json'],capture_output=True,text=True,timeout=10)
                if result.returncode or len(result.stdout)>16384:continue
                data=standalone.checked_layout(json.loads(result.stdout))
                if data['system']['offset']!=offset or data['xbox_bytes']<end or data['image_bytes']>size:continue
                standalone.repair_sector(first,data)
                return data
            except (ValueError,KeyError,TypeError,OSError,subprocess.TimeoutExpired):continue
    return None


def pc_regions(path,size):
    """Bounded MBR/GPT discovery; a stale signature alone reserves no region."""
    import binascii,struct,uuid
    result=[];efi=uuid.UUID('c12a7328-f81f-11d2-ba4b-00a0c93ec93b').bytes_le
    with open(path,'rb',buffering=0) as source:
        first=source.read(512)
        if first[510:512]==b'\x55\xaa':
            for i in range(4):
                entry=first[446+i*16:462+i*16];start,count=struct.unpack_from('<II',entry,8)
                if entry[0] not in (0,128) or not entry[4] or not start or not count or (start+count)*512>size:continue
                if entry[4]!=0xEE:result.append(dict(offset=start*512,bytes=count*512,efi=entry[4]==0xEF))
        for offset in (512,size-512):
            source.seek(offset);header=source.read(512)
            if header[:8]!=b'EFI PART':continue
            length,crc=struct.unpack_from('<II',header,12)
            if not 92<=length<=512:continue
            check=bytearray(header[:length]);check[16:20]=bytes(4)
            if binascii.crc32(check)!=crc:continue
            lba,count,stride,checksum=struct.unpack_from('<QIII',header,72)
            if not 1<=count<=4096 or not 128<=stride<=1024 or count*stride>1024**2 or lba*512+count*stride>size:continue
            source.seek(lba*512);entries=source.read(count*stride)
            if binascii.crc32(entries)!=checksum:continue
            for i in range(count):
                entry=entries[i*stride:(i+1)*stride]
                if entry[:16]==bytes(16):continue
                start,end=struct.unpack_from('<QQ',entry,32)
                if start<1 or end<start or (end+1)*512>size:continue
                row=dict(offset=start*512,bytes=(end+1-start)*512,efi=entry[:16]==efi)
                if row not in result:result.append(row)
    return result
