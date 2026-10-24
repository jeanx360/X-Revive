"""VM-only virtual Xbox 360 pad for controller-only installation tests.

echo A|B|up|down|confirm|hold-confirm|release|menu > /run/xrevive-pad-command
Never run on the host. The virtual device vanishes when this process exits.
"""
import fcntl
import os
from pathlib import Path
import struct
import subprocess
import time

assert 'QEMU' in Path('/sys/class/dmi/id/sys_vendor').read_text()
subprocess.run(['modprobe','uinput'],check=True)
fd=os.open('/dev/uinput',os.O_WRONLY|os.O_NONBLOCK)
for event in (1,3):fcntl.ioctl(fd,0x40045564,event)
buttons=[304,305,307,308,310,311,314,315,316,317,318]
for key in buttons:fcntl.ioctl(fd,0x40045565,key)
axes=[0,1,2,3,4,5,16,17]
for axis in axes:fcntl.ioctl(fd,0x40045567,axis)
maximum=[0]*64;minimum=[0]*64;flat=[0]*64;fuzz=[0]*64
for axis in axes:
    maximum[axis]=255 if axis in (2,5) else 1 if axis in (16,17) else 32767
    minimum[axis]=0 if axis in (2,5) else -1 if axis in (16,17) else -32768
description=struct.pack('80sHHHHi',b'X-Revive QA Xbox 360',3,0x045e,0x028e,1,0)
for values in (maximum,minimum,fuzz,flat):description+=struct.pack('64i',*values)
os.write(fd,description);fcntl.ioctl(fd,0x5501)


def event(kind,code,value):os.write(fd,struct.pack('llHHi',0,0,kind,code,value))


def release():
    for key in buttons:event(1,key,0)
    for axis in axes:event(3,axis,0)
    event(0,0,0)


print('VIRTUAL_XBOX_PAD_READY',flush=True)
path=Path('/run/xrevive-pad-command');stamp=0;until=0
try:
    release()
    while True:
        if until and time.monotonic()>until:release();until=0
        if path.exists() and path.stat().st_mtime_ns!=stamp:
            stamp=path.stat().st_mtime_ns;cmd=path.read_text().strip();release()
            # Software-rendered nested Xbox frames can miss a short tap.
            duration=1.5 if cmd.startswith('slow-') else .15
            if cmd.startswith('slow-'):cmd=cmd[5:]
            if cmd in ('A','B','X','Y','start','back'):
                event(1,{'A':304,'B':305,'X':307,'Y':308,'start':315,'back':314}[cmd],1);until=time.monotonic()+duration
            elif cmd in ('up','down','left','right'):
                event(3,17 if cmd in ('up','down') else 16,-1 if cmd in ('up','left') else 1);until=time.monotonic()+duration
            elif cmd in ('confirm','hold-confirm'):
                event(3,2,255);event(3,5,255);event(1,315,1)
                until=time.monotonic()+2 if cmd=='confirm' else 0
            elif cmd=='menu':event(3,17,-1);event(1,315,1);until=time.monotonic()+.15
            elif cmd=='backstart':event(1,314,1);event(1,315,1);until=time.monotonic()+.15
            event(0,0,0);print('PAD',cmd,flush=True)
        time.sleep(.04)
finally:
    release();fcntl.ioctl(fd,0x5502);os.close(fd)
