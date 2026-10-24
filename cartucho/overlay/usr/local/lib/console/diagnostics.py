"""Persist bounded boot diagnostics on the verified boot USB, no firmware."""
from pathlib import Path
import os
import subprocess
import sys
import time

if '--wait' in sys.argv:time.sleep(15)
if os.path.ismount('/userdata'):
    dest=Path('/userdata/X-Revive/diagnosticos')/Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    dest.mkdir(parents=True,exist_ok=True)
    for name,cmd in [('servicos.log',['journalctl','-b','--no-pager','-n','1800']),
                     ('hardware.log',['lspci','-nnk']),
                     ('discos.log',['lsblk','-b','-o','NAME,MODEL,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS'])]:
        try:
            result=subprocess.run(cmd,capture_output=True,timeout=12)
            (dest/name).write_bytes((result.stdout+result.stderr)[-1024**2:])
        except Exception as exc:(dest/name).write_text(str(exc))
    for src in ('/run/console/profile','/run/console/interface.log','/usr/share/console/build.json','/proc/cmdline'):
        if Path(src).is_file():(dest/Path(src).name).write_bytes(Path(src).read_bytes())
    subprocess.run(['sync','-f',str(dest)],timeout=10)
