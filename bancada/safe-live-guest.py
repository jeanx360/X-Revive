"""Runs only inside disposable outer QEMU guests, with private readonly inputs."""
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

assert 'QEMU' in Path('/sys/class/dmi/id/sys_vendor').read_text()
assert 'xrevive.safe-live=1' in Path('/proc/cmdline').read_text().split()
sys.path.insert(0,'/usr/local/lib/console')
import safe_live


def rpc(action,**args):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.connect('/run/xrevive-installer/control.sock')
        sock.sendall((json.dumps(dict(action=action,**args))+'\n').encode())
        result=json.loads(sock.makefile().readline())
    return result


def guard():
    hello=rpc('hello');assert hello['ok'] and hello['data']['safe_live'] and hello['data']['disks']==[]
    protected=json.loads(Path('/run/xrevive-installer/protected-disks.json').read_text())
    for device in protected:
        assert subprocess.check_output(['blockdev','--getro',device],text=True).strip()=='1'
        fd=os.open(device,os.O_RDWR)
        try:
            try:os.pwrite(fd,b'WRITING-MUST-FAIL',0)
            except OSError as exc:assert exc.errno in (errno.EROFS,errno.EPERM,errno.EACCES)
            else:raise AssertionError('Physical QA disk was writable!')
        finally:os.close(fd)
    for action in ('live-plan','live-start','live-boot-prepare','install','repair','dashboard','prepare'):
        result=rpc(action,target='/dev/sda')
        assert not result['ok'] and 'discos físicos bloqueado' in result['error'],result
    return dict(protected_devices=protected,physical_writes_rejected=True,rpc_writes_rejected=True)


if sys.argv[1]=='setup':
    mode=sys.argv[2]
    # Import firmware into the disposable USB, explicitly test native EEPROM generation.
    target=Path('/userdata/X-Revive/firmware')
    shutil.copytree('/mnt/input/X-Revive/firmware',target,dirs_exist_ok=True)
    (target/'xbox/eeprom.bin').unlink(missing_ok=True)
    if mode=='offline':
        shutil.copyfile('/mnt/input/rocky5-live.iso','/userdata/X-Revive/pacotes/live/rocky5.iso')
    else:
        lock=json.loads(safe_live.LOCK.read_text());key=safe_live.digest(safe_live.LOCK)
        cache=safe_live.USER/'cache/rocky5-live'/key/'disc'
        shutil.copytree('/mnt/input/extras',cache,dirs_exist_ok=True)
        # Force an actual HTTPS download in the production downloader as well
        # as verifying the 172 real upstream downloads already made on host.
        (cache/'default.xbe').unlink()
    print('SAFE_SETUP_PASS',guard(),flush=True)
elif sys.argv[1]=='proof':
    proof=guard();state=json.loads(Path('/run/xrevive-live/session.json').read_text())
    assert state['mode']=='sandbox' and state['device'] is None
    assert state['hdd'].startswith('/run/console/live-changes/')
    assert subprocess.check_output(['blockdev','--getro',state['dvd']],text=True).strip()=='1'
    eeprom=Path('/run/console/eeprom.bin').read_bytes()
    assert len(eeprom)==256 and Path(state['storage']+'/firmware/xbox/eeprom.bin').read_bytes()==eeprom
    proof.update(state=state,eeprom_generated_and_preserved=True,
                 graphics=json.loads(Path('/run/console/graphics.json').read_text()))
    Path('/run/safe-proof.json').write_text(json.dumps(proof,indent=2))
    print('SAFE_PROOF='+json.dumps(proof),flush=True)
