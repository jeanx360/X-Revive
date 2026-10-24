"""QA clone only: explicit local HTTP channel, production code stays identical."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('image',type=Path);p.add_argument('folder',type=Path);a=p.parse_args()
assert a.image.is_file() and not a.image.is_symlink()
f=a.folder.resolve();f.mkdir(parents=True,exist_ok=True);image=f/'channel-qa.img'
if image.exists():raise ValueError('QA destination already exists')
subprocess.run(['cp','--reflink=auto',str(a.image.resolve()),str(image)],check=True)
table=json.loads(subprocess.check_output(['sfdisk','-J',str(image)],text=True))['partitiontable']
offset=next(i['start']*512 for i in table['partitions'] if i['name']=='SYSTEM')
subprocess.run(['mcopy','-i',str(image)+'@@'+str(offset),'::/live/filesystem.squashfs',str(f/'original.squashfs')],check=True)
code="""import json
from pathlib import Path
p=Path('/qa/rootfs/etc/xrevive-updates.json');d=json.loads(p.read_text());d.update(manifest_url='http://10.0.2.2:8866/latest.json',allow_http=True);p.write_text(json.dumps(d,indent=2)+'\\n')
"""
(f/'channel.py').write_text(code)
script='''set -eu
apt-get update -qq
apt-get install -y -qq --no-install-recommends squashfs-tools python3 >/dev/null
unsquashfs -no-progress -no-xattrs -d /qa/rootfs /qa/original.squashfs >/qa/extract.log
python3 /qa/channel.py
mksquashfs /qa/rootfs /qa/channel.squashfs -comp zstd -noappend -quiet -no-xattrs -processors 4
'''
subprocess.run(['podman','run','--rm','-v',str(f)+':/qa:z','docker.io/library/debian:trixie','sh','-c',script],check=True)
subprocess.run(['mcopy','-o','-i',str(image)+'@@'+str(offset),str(f/'channel.squashfs'),'::/live/filesystem.squashfs'],check=True)
(f/'qa-config.json').write_text(json.dumps({'production_image':str(a.image.resolve()),'qa_image':str(image),'changes':['/etc/xrevive-updates.json: local HTTP channel only'],'production_code_modified':False},indent=2))
print('QA_LOCAL_CHANNEL_IMAGE',image,flush=True)
