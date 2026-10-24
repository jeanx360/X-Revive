"""Create an Ed25519 signed, Xemu-only release channel (never uploads anything)."""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('updater',ROOT/'cartucho/overlay/usr/local/lib/console/updater.py')
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)


def init_key(private, public):
    private=Path(private);public=Path(public)
    if private.exists() or public.exists():raise ValueError('Chaves existentes não serão sobrescritas')
    private.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(private,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(private)],check=True)
    public.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['openssl','pkey','-in',str(private),'-pubout','-out',str(public)],check=True)


def package(args):
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    binary=Path(args.binary);u.version(args.version)
    if args.sequence<1:raise ValueError('Sequência precisa crescer a cada publicação')
    files={'xemu':binary,'LICENSE.txt':Path(args.license),'smc.patch':Path(args.smc_patch),'menu.patch':Path(args.menu_patch)}
    provenance={'version':args.version,'upstream_commit':args.commit,'runtime_abi':u.ABI,
        'binary_sha256':u.digest(binary),'smc_patch_sha256':u.digest(args.smc_patch),'menu_patch_sha256':u.digest(args.menu_patch)}
    with tempfile.TemporaryDirectory(dir=output,prefix='.package-') as tmp:
        tmp=Path(tmp);(tmp/'PROVENANCE.json').write_bytes(u.canonical(provenance))
        files['PROVENANCE.json']=tmp/'PROVENANCE.json'
        archive=tmp/'package.tar.gz'
        with tarfile.open(archive,'w:gz',dereference=True) as tar:
            for name,path in sorted(files.items()):tar.add(path,arcname=name,recursive=False)
        identity=u.digest(archive);name='xemu-'+identity+'.tar.gz'
        data=dict(provenance,schema=1,sequence=args.sequence,sha256=identity,bytes=archive.stat().st_size,
            unpacked_bytes=sum(p.stat().st_size for p in files.values()),package_url=args.base_url.rstrip('/')+'/'+name,
            changelog=Path(args.changelog).read_text())
        (tmp/'manifest').write_bytes(u.canonical(data))
        subprocess.run(['openssl','pkeyutl','-sign','-inkey',args.key,'-rawin','-in',str(tmp/'manifest'),'-out',str(tmp/'signature')],check=True)
        envelope={'manifest':data,'signature':base64.b64encode((tmp/'signature').read_bytes()).decode()}
        public=subprocess.check_output(['openssl','pkey','-in',args.key,'-pubout'],text=True)
        u.verified(envelope,public)
        os.replace(archive,output/name)
        u.atomic(output/'latest.json',envelope)
    print(json.dumps(data,indent=2))


def upstream():
    request=urllib.request.Request('https://api.github.com/repos/xemu-project/xemu/releases/latest',headers={'User-Agent':'X-Revive-build/1','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=15) as response:data=json.load(response)
    if data['draft'] or data['prerelease']:raise ValueError('Release upstream não é estável')
    return {'tag':data['tag_name'],'published_at':data['published_at'],'url':data['html_url'],'changelog':data['body']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    key=commands.add_parser('init-key');key.add_argument('--private',required=True);key.add_argument('--public',required=True)
    commands.add_parser('upstream')
    build=commands.add_parser('package')
    for name in ('binary','license','smc-patch','menu-patch','commit','version','key','base-url','changelog','output'):build.add_argument('--'+name,required=True)
    build.add_argument('--sequence',type=int,required=True)
    args=parser.parse_args()
    if args.command=='init-key':init_key(args.private,args.public)
    elif args.command=='package':package(args)
    else:print(json.dumps(upstream(),ensure_ascii=False,indent=2))
