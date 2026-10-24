"""Boot one release image in an isolated VM, with snapshot disks and virtual I/O.

Debug shell is enabled only in the test VM command line, never in the image.
Usage: python3 bancada/smoke-image.py universal|nvidia [r|g|normal]
"""
import json
import os
import array
import fcntl
from pathlib import Path
import socket
import subprocess
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]


def qmp(path, command):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(5)
        s.connect(str(path))
        with s.makefile('rwb', buffering=0) as f:
            f.readline()
            for c in ({'execute': 'qmp_capabilities'}, command):
                f.write(json.dumps(c).encode()+b'\n')
                while True:
                    reply = json.loads(f.readline())
                    if 'return' in reply or 'error' in reply:
                        break
                if 'error' in reply:
                    raise RuntimeError(reply)
            return reply


def serial(path, command):
    if len(command.encode())>900:
        raise ValueError('use a VM-only helper file for long serial commands')
    # QEMU's serial console is one terminal. Independent QA readers must not
    # interleave shell commands and accidentally leave an interactive REPL.
    with Path(str(path)+'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _serial(path,command)


def _serial(path, command):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(.5)
        s.connect(str(path))
        s.sendall(('\n'+command+'\n').encode())
        result = b''
        deadline = time.monotonic()+2
        while time.monotonic() < deadline:
            try:
                data = s.recv(65536)
                if not data:
                    break
                result += data
            except TimeoutError:
                pass
        return result.decode(errors='replace')


def main(variant, key='r'):
    if variant not in ('universal', 'nvidia'):
        raise ValueError('variante invalida')
    if key not in ('r', 'g', 'normal'):
        raise ValueError('atalho invalido')
    folder = Path(os.environ.get('SMOKE_RESULT_ROOT', str(ROOT/'bancada/validacao-boot')))/(variant+'-'+key)
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'result.json').unlink(missing_ok=True)
    (folder/'checks.log').write_text('')
    (folder/'serial.log').write_text('')
    image = Path(os.environ.get('SMOKE_IMAGE', str(ROOT/f'cartucho/out/console-xbox-{variant}.img')))
    metadata = json.loads(image.with_suffix('.json').read_text())
    for name in ('vmlinuz', 'initrd.img'):
        subprocess.run(['mcopy', '-o', '-i', str(image)+'@@1048576', '::/live/'+name,
                        str(folder/name)], check=True)
    # Use an existing virtual FATX HDD; -snapshot prevents writes to its source.
    hdd = ROOT/'bancada/vm/hdd.img'
    if not hdd.is_file():
        raise FileNotFoundError('HDD virtual de bancada ausente')
    args = ['qemu-system-x86_64', '-name', 'xrevive-smoke-'+variant,
        '-enable-kvm', '-machine', 'q35', '-cpu', 'host', '-smp', '4', '-m', '6144', '-snapshot',
        '-kernel', str(folder/'vmlinuz'), '-initrd', str(folder/'initrd.img'),
        '-append', 'boot=live live-media=/dev/disk/by-label/SYSTEM toram console=tty0 quiet splash '
                   'loglevel=0 systemd.show_status=false vt.global_cursor_default=0 '
                   'systemd.debug_shell=ttyS0 systemd.mask=serial-getty@ttyS0.service',
        '-device', 'qemu-xhci,id=xhci', '-drive', f'if=none,id=usb,format=raw,file={image}',
        '-device', 'usb-storage,bus=xhci.0,drive=usb',
        '-drive', f'if=none,id=hdd,format=raw,file={hdd}', '-device', 'ide-hd,bus=ide.0,drive=hdd',
        '-device', 'virtio-vga', '-display', 'none',
        '-audiodev', f'wav,id=som,path={folder}/audio.wav',
        '-device', 'ich9-intel-hda', '-device', 'hda-output,audiodev=som',
        '-netdev', 'user,id=net', '-device', 'e1000,netdev=net',
        '-chardev', f'socket,id=ser,path={folder}/serial.sock,server=on,wait=off,logfile={folder}/serial.log',
        '-serial', 'chardev:ser', '-qmp', f'unix:{folder}/vm.qmp,server=on,wait=off',
        '-drive', 'if=none,id=dvd,media=cdrom', '-device', 'ide-cd,bus=ide.1,drive=dvd']
    (folder/'command.json').write_text(json.dumps(args, indent=2)+'\n')
    with (folder/'qemu.log').open('w') as log:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
        try:
            print('VM iniciada:', variant, key, flush=True)
            deadline = time.monotonic()+120
            passed = False
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('QEMU saiu antes da validacao')
                if not (folder/'vm.qmp').exists():
                    time.sleep(1)
                    continue
                # Explicit transitions avoid a key held before PS/2 init being
                # lost by the guest while HMP keeps resetting its hold timer.
                if key != 'normal':
                    qmp(folder/'vm.qmp', {'execute': 'input-send-event', 'arguments': {'events': [
                        {'type': 'key', 'data': {'down': False, 'key': {'type': 'qcode', 'data': key}}},
                        {'type': 'key', 'data': {'down': True, 'key': {'type': 'qcode', 'data': key}}},
                    ]}})
                qmp(folder/'vm.qmp', {'execute': 'screendump', 'arguments': {
                    'filename': str(folder/('boot-%03d.ppm' % int(120-(deadline-time.monotonic()))))}})
                if (folder/'serial.sock').exists():
                    flag = {'r': 'test -f /run/console/boot-hexen',
                            'g': 'test -f /run/console/boot-ogxbox',
                            'normal': 'test ! -e /run/console/boot-hexen && test ! -e /run/console/boot-ogxbox'}[key]
                    # Split PASS token so echoed command cannot be mistaken for result.
                    result = serial(folder/'serial.sock',
                        'systemctl is-active --quiet console.service console-prepare.service console-tray-monitor.service '
                        f'&& {flag} '
                        '&& test -f /utils/ogxbox.iso '
                        '&& grep -q "animacao: pronta\\|animacao: ja conferida" /run/console/bootanim.log '
                        '&& grep -q RUNNING /proc/asound/card0/pcm0p/sub0/status '
                        '&& printf "SMOKE_%s\\n" PASS')
                    with (folder/'checks.log').open('a') as checks:
                        checks.write(result)
                    if 'SMOKE_PASS' in result:
                        passed = True
                        break
                time.sleep(3)
            if not passed:
                raise RuntimeError('Timeout: servicos/atalho/UTILS/animacao/audio nao confirmados')
            # The audio device opens before the emulated BIOS finishes booting.
            # Allow the dashboard to appear before collecting visual evidence.
            print('Servicos ativos; aguardando boot do dashboard:', variant, flush=True)
            serial(folder/'serial.sock', 'sha256sum /utils/ogxbox.iso > /run/console/ogxbox.sha256 &')
            time.sleep(30)
            qmp(folder/'vm.qmp', {'execute': 'screendump', 'arguments': {'filename': str(folder/'animacao.ppm')}})
            time.sleep(30)
            expected = metadata['utilities']['ogxbox']['sha256']
            media_deadline = time.monotonic()+90
            media_result = ''
            while time.monotonic() < media_deadline:
                media_result = serial(folder/'serial.sock', 'cat /run/console/ogxbox.sha256')
                if expected in media_result:
                    break
                time.sleep(3)
            (folder/'media-check.log').write_text(media_result)
            if expected not in media_result:
                raise RuntimeError('Hash da ISO lida de dentro da imagem nao confirmado')
            binary = metadata.get('emulator', {}).get('binary_sha256')
            binary_result = serial(folder/'serial.sock', 'sha256sum /opt/xemu/usr/bin/xemu')
            (folder/'emulator-check.log').write_text(binary_result)
            if binary and binary not in binary_result:
                raise RuntimeError('Executavel Xemu nao corresponde ao manifesto')
            serial(folder/'serial.sock', 'cat /etc/console-variant; cat /run/console/hardware.env; '
                   'cat /usr/share/console/build.json; ip -4 -brief address; pgrep -a xemu; '
                   'systemctl is-active console.service; cat /run/console/bootanim.log; '
                   'stat -c "%s %n" /utils/ogxbox.iso; '
                   'grep skip_boot_anim /run/console/xemu.toml; echo DIAGNOSTICO_FIM')
            qmp(folder/'vm.qmp', {'execute': 'screendump', 'arguments': {'filename': str(folder/'tela.ppm')}})
            result = dict(variant=variant, shortcut=key, smoke_pass=True,
                build_id=metadata['build_id'], source_sha256=metadata['source_sha256'],
                emulator_sha256=binary,
                media_sha256=expected,
                scope='VM virtio, sem GPU NVIDIA fisica; aceleracao GTX requer bancada')
            serial(folder/'serial.sock', 'systemctl poweroff')
            process.wait(timeout=30)
            with wave.open(str(folder/'audio.wav')) as audio:
                if audio.getsampwidth() != 2:
                    raise RuntimeError('Formato WAV inesperado')
                values = array.array('h', audio.readframes(audio.getnframes()))
                result['audio_peak'] = max(map(abs, values), default=0)
            if result['audio_peak'] == 0:
                raise RuntimeError('Captura de audio ficou silenciosa')
            (folder/'result.json').write_text(json.dumps(result, indent=2)+'\n')
            print('SMOKE PASS:', variant, key, flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    main(*sys.argv[1:])
