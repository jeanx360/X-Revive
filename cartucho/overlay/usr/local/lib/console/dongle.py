"""Load owner-provided Xbox Wireless firmware into the live RAM filesystem."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HASHES={
    '02e6':'080ce4091e53a4ef3e5fe29939f51fd91f46d6a88be6d67eb6e99a5723b3a223',
    '02fe':'48084d9fa53b9bb04358f3bb127b7495dc8f7bb0b3ca1437bd24ef2b6eabdf66',
    '02f9':'0023a7bae02974834500c665a281e25b1ba52c9226c84989f9084fa5ce591d9b',
    '091e':'e2710daf81e7b36d35985348f68a81d18bc537a2b0c508ffdfde6ac3eae1bad7',
}


def files(roots):
    found={};errors=[]
    for pid,expected in HASHES.items():
        name='xone_dongle_'+pid+'.bin'
        for root in map(Path,roots):
            path=root/name
            if not path.exists() and not path.is_symlink():continue
            if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<1024**2:
                errors.append(name+': arquivo inválido');continue
            data=path.read_bytes()
            if hashlib.sha256(data).hexdigest()!=expected:
                errors.append(name+': hash não confere');continue
            found[name]=data;break
    return found,errors


def import_owner(roots,firmware=Path('/usr/lib/firmware'),usb=Path('/sys/bus/usb/devices'),run=Path('/run/console')):
    found,errors=files(roots)
    changed=set()
    for name,data in found.items():
        target=firmware/name
        if target.is_file() and target.read_bytes()==data:continue
        changed.add(name)
        with tempfile.NamedTemporaryFile(dir=firmware,prefix='.xrevive-dongle-',delete=False) as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno());temporary=Path(stream.name)
        temporary.chmod(0o644);os.replace(temporary,target)
    result=dict(imported=sorted(found),errors=errors,devices=[])
    if found:
        subprocess.run(['modprobe','xone_dongle'],check=False,capture_output=True)
        # Retry devices whose early firmware request failed before USB mounted.
        # No unloading active controllers or unrelated network drivers.
        for device in usb.iterdir():
            try:
                if not (device/'idVendor').is_file() or not (device/'idProduct').is_file():continue
                pid=(device/'idProduct').read_text().strip()
                if (device/'idVendor').read_text().strip()!='045e' or pid not in HASHES:continue
                for interface in usb.glob(device.name+':*'):
                    driver=interface/'driver'
                    if driver.exists():
                        # xone requests firmware asynchronously; it may remain
                        # bound after the early request failed. Retry just this
                        # empty interface when its firmware was first imported.
                        active=interface/'active_clients'
                        if (driver.resolve().name=='xone-dongle' and 'xone_dongle_'+pid+'.bin' in changed
                                and active.exists() and active.read_text().partition('\n')[0].strip() in ('0','Active clients: 0')):
                            (driver/'unbind').write_text(interface.name)
                            (usb.parent/'drivers_probe').write_text(interface.name)
                    else:(usb.parent/'drivers_probe').write_text(interface.name)
                result['devices'].append(device.name)
            except OSError as exc:errors.append('dongle: '+str(exc))
    run.mkdir(exist_ok=True);(run/'dongle.json').write_text(json.dumps(result))
    return result


def persist(reference,roots):
    found,_=files(roots)
    if not found:return
    with tempfile.TemporaryDirectory(prefix='xrevive-owner-dongle-') as folder:
        root=Path(folder)/'dongle';root.mkdir()
        for name,data in found.items():(root/name).write_bytes(data)
        subprocess.run(['mmd','-i',reference,'::/firmware'],check=False,capture_output=True)
        subprocess.run(['mcopy','-o','-s','-i',reference,str(root),'::/firmware/'],check=True)


if __name__=='__main__':
    import sys
    print(json.dumps(import_owner(sys.argv[1:])))
