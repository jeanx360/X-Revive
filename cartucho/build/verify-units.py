"""Check the complete boot transaction in a staged rootfs before packaging."""
import argparse
from pathlib import Path
import subprocess


def verify(root):
    root = Path(root).resolve()
    if root == Path('/') or not (root/'var/lib/dpkg/status').is_file():
        raise ValueError('Expected a staged Debian rootfs')
    result = subprocess.run(
        ['chroot', str(root), 'systemd-analyze', 'verify', '--man=no',
         'multi-user.target'], capture_output=True, text=True)
    output = result.stdout + result.stderr
    print(output, end='')
    if result.returncode or 'ordering cycle' in output or 'deleted to break' in output:
        raise RuntimeError('Invalid systemd boot transaction')
    print('SYSTEMD_BOOT_TRANSACTION_PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rootfs')
    verify(parser.parse_args().rootfs)
