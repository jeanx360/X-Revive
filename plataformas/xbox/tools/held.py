#!/usr/bin/env python3
"""R/Start+Back selecionam a manutencao propria X-Revive.

Consulta EVIOCGKEY repetidamente no boot, incluindo dispositivos novos.
"""
import array
import fcntl
import glob
import sys
import time
import argparse
import json
from pathlib import Path
import subprocess

KEY_MAX = 0x2FF
NBYTES = (KEY_MAX + 8) // 8
# EVIOCGKEY(len): _IOC(_IOC_READ=2, type='E', nr=0x18, size=len)
EVIOCGKEY = (2 << 30) | (NBYTES << 16) | (ord("E") << 8) | 0x18

# BTN_SELECT (Back) = 314, BTN_START = 315 (controles Xbox via xpad/xone)
COMBO = (314, 315)


def held(path, combo=COMBO):
    buf = array.array("B", [0] * NBYTES)
    try:
        with open(path, "rb") as f:
            fcntl.ioctl(f, EVIOCGKEY, buf, True)
    except OSError:
        return False
    return all((buf[c >> 3] >> (c & 7)) & 1 for c in combo)


def wait_held(timeout, scan=None, clock=time.monotonic, sleep=time.sleep):
    # KEY_R=19. Rescan catches devices enumerated late in cold boot.
    scan = scan or (lambda: any(held(dev, (19,)) or held(dev)
                               for dev in glob.glob("/dev/input/event*")))
    deadline = clock() + timeout
    while True:
        if scan():
            return True
        if clock() >= deadline:
            return False
        sleep(0.1)


def selection(devices=None):
    devices = list(devices if devices is not None else glob.glob('/dev/input/event*'))
    # Recovery wins if both shortcuts are held, even on different devices.
    if any(held(dev, (19,)) or held(dev) for dev in devices):
        return 'installer'
    if any(held(dev, (22,)) or held(dev, (308,)) for dev in devices):
        return 'update'
    return ''


def wait_selection(timeout, scan=selection, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    notice_shown = False
    while True:
        if not notice_shown:
            try:
                notice = json.loads(Path('/run/xrevive-update/notice.json').read_text())
                if notice.get('available'):
                    subprocess.run(['plymouth','display-message','--text=Nova atualização disponível - segure U ou Y'], check=False, timeout=1)
                    notice_shown = True
            except (OSError, ValueError, subprocess.TimeoutExpired): pass
        target = scan()
        if target:
            return target
        if clock() >= deadline:
            return ''
        sleep(0.1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=0)
    parser.add_argument("--select", action="store_true")
    args = parser.parse_args()
    if args.select:
        target = wait_selection(args.timeout)
        if target:
            print(target)
        sys.exit(0 if target else 1)
    sys.exit(0 if wait_held(args.timeout) else 1)
