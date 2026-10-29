"""Read-only virtual Xbox DVD: generated directory metadata, original ISO files.

Runs only inside the appliance. NBD presents a DVD without a second full ISO.
The source remains mounted read-only until release; no user HDD is opened here.
"""
import argparse
import bisect
from collections import OrderedDict
import errno
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import struct
import subprocess
import threading
import time

import xiso

PRIVATE=Path('/run/xrevive-disc')
SET_SOCK=0xab00;SET_SIZE_BLOCKS=0xab07;SET_BLKSIZE=0xab01;SET_FLAGS=0xab0a
DO_IT=0xab03;DISCONNECT=0xab08;CLEAR_SOCK=0xab04


class Image:
    def __init__(self,root,aliases=None,renames=None):
        self.bytes,self.segments=xiso.plan(Path(root),{k:Path(v) for k,v in (aliases or {}).items()},renames)
        self.starts=[item['offset'] for item in self.segments];self.files=OrderedDict()

    def read(self,offset,length):
        if offset<0 or length<0 or offset+length>self.bytes:raise ValueError('Leitura fora do DVD virtual')
        result=bytearray(length);index=max(0,bisect.bisect_right(self.starts,offset)-1)
        while index<len(self.segments):
            item=self.segments[index];start=item['offset'];end=start+item['bytes']
            if start>=offset+length:break
            left=max(start,offset);right=min(end,offset+length)
            if left<right:
                if 'data' in item:block=item['data'][left-start:right-start]
                else:
                    path=item['path']
                    if path not in self.files:
                        if len(self.files)>=32:os.close(self.files.popitem(last=False)[1])
                        self.files[path]=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
                    self.files.move_to_end(path)
                    block=os.pread(self.files[path],right-left,left-start)
                    if len(block)!=right-left:raise OSError('A mídia original ficou indisponível')
                result[left-offset:right-offset]=block
            index+=1
        return bytes(result)

    def close(self):
        for fd in self.files.values():os.close(fd)
        self.files.clear()


def exact(sock,length):
    out=bytearray()
    while len(out)<length:
        block=sock.recv(length-len(out))
        if not block:raise EOFError
        out.extend(block)
    return bytes(out)


def serve(sock,image):
    while True:
        try:magic,kind,handle,offset,length=struct.unpack('>II8sQI',exact(sock,28))
        except EOFError:return
        if magic!=0x25609513:raise ValueError('Pedido NBD inválido')
        kind&=0xffff
        if kind==2:return
        if kind==1:exact(sock,length)
        error=0;data=b''
        try:
            if kind==0:data=image.read(offset,length)
            elif kind!=3:error=errno.EROFS
        except (ValueError,OSError):error=errno.EIO
        sock.sendall(struct.pack('>II8s',0x67446698,error,handle)+data)


def start(root,mounted,aliases,renames,progress):
    if not Path('/run/console/installer').exists():raise ValueError('DVD virtual exige o appliance X-Revive')
    subprocess.run(['modprobe','nbd','nbds_max=1','max_part=0'],check=True,timeout=10)
    PRIVATE.mkdir(mode=0o700,exist_ok=True)
    lock=os.open(PRIVATE/'lock',os.O_RDWR|os.O_CREAT,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        device=next((p for p in sorted(Path('/sys/class/block').glob('nbd*')) if not (p/'pid').exists()),None)
        if device is None:raise ValueError('Nenhum dispositivo de DVD virtual disponível')
        config=dict(root=str(root),mounted=str(mounted),aliases={k:str(v) for k,v in aliases.items()},renames=renames,device='/dev/'+device.name)
        (PRIVATE/'ready.json').unlink(missing_ok=True)
        (PRIVATE/'config.json').write_text(json.dumps(config));(PRIVATE/'config.json').chmod(0o600)
        log=(PRIVATE/'server.log').open('w')
        process=subprocess.Popen(['python3',str(Path(__file__).resolve()),str(PRIVATE/'config.json')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=[lock]);log.close()
        for _ in range(120):
            if (PRIVATE/'ready.json').exists():
                result=json.loads((PRIVATE/'ready.json').read_text())
                if result['pid']!=process.pid:raise ValueError('Identidade do DVD virtual mudou')
                result['virtual']=True;return result
            if process.poll() is not None:raise ValueError('DVD virtual não iniciou; consulte os detalhes do teste')
            progress('Preparando DVD virtual; sem duplicar a ISO no pendrive...',45);time.sleep(.5)
        process.terminate();raise TimeoutError('A preparação do DVD virtual excedeu o tempo de espera')
    except BaseException:
        if 'process' in locals() and process.poll() is None:
            process.terminate();process.wait(timeout=10)
        raise
    finally:os.close(lock)


def release(device):
    if not Path(device).name.startswith('nbd'):return False
    fd=os.open(device,os.O_RDONLY)
    try:
        try:fcntl.ioctl(fd,DISCONNECT)
        except OSError as exc:
            if exc.errno not in (errno.EINVAL,errno.ENOTCONN):raise
    finally:os.close(fd)
    return True


def main(config):
    config=json.loads(Path(config).read_text());image=Image(config['mounted'],config['aliases'],config['renames'])
    device=config['device'];fd=os.open(device,os.O_RDONLY);left,right=socket.socketpair();thread=None
    def stop(*_):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    try:
        fcntl.ioctl(fd,SET_BLKSIZE,2048);fcntl.ioctl(fd,SET_SIZE_BLOCKS,image.bytes//2048)
        fcntl.ioctl(fd,SET_SOCK,left.fileno());fcntl.ioctl(fd,SET_FLAGS,3);fcntl.ioctl(fd,0xab09,15)
        def kernel():
            try:fcntl.ioctl(fd,DO_IT)
            except OSError:pass
            finally:
                try:right.shutdown(socket.SHUT_RDWR)
                except OSError:pass
        thread=threading.Thread(target=kernel,daemon=True);thread.start()
        pending=PRIVATE/'ready.new'
        pending.write_text(json.dumps(dict(path=device,offset=0,disc_bytes=image.bytes,adapted=True,kind='collection' if config['aliases'] else 'iso9660',pid=os.getpid())))
        os.replace(pending,PRIVATE/'ready.json')
        serve(right,image)
    finally:
        try:fcntl.ioctl(fd,DISCONNECT)
        except OSError:pass
        if thread:thread.join(timeout=2)
        try:fcntl.ioctl(fd,CLEAR_SOCK)
        except OSError:pass
        left.close();right.close();os.close(fd);image.close();(PRIVATE/'ready.json').unlink(missing_ok=True)
        subprocess.run(['umount',config['mounted']],check=False,timeout=10)
        if not os.path.ismount(config['mounted']) and Path(config['root']).exists():shutil.rmtree(config['root'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config');main(p.parse_args().config)
