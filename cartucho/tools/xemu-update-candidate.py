"""Poll official stable releases and optionally compile a patched candidate.

Does not sign/promote/upload releases. A candidate needs bench validation.
Safe for a maintainer's scheduled job; no firmware or Xbox disks required.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('packager',ROOT/'cartucho/build/xemu-update-package.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'X-Revive-candidate/1','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=15) as response:return json.load(response)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',action='store_true');args=parser.parse_args()
    latest=p.upstream();tag=latest['tag']
    if not re.fullmatch(r'v\d+\.\d+\.\d+',tag):raise ValueError('Tag estável inválida')
    obj=get('https://api.github.com/repos/xemu-project/xemu/git/ref/tags/'+tag)['object']
    for _ in range(3):
        if obj['type']=='commit':break
        if obj['type']!='tag':raise ValueError('Referência upstream inválida')
        obj=get('https://api.github.com/repos/xemu-project/xemu/git/tags/'+obj['sha'])['object']
    if obj['type']!='commit' or not re.fullmatch('[0-9a-f]{40}',obj['sha']):raise ValueError('Commit não resolvido')
    latest['commit']=obj['sha'];cache=ROOT/'cartucho/cache';cache.mkdir(exist_ok=True)
    p.u.atomic(cache/'xemu-upstream-candidate.json',latest)
    print(json.dumps(latest,ensure_ascii=False,indent=2),flush=True)
    if args.build:
        # No automatic stock binary: patches must apply to the exact tag/commit.
        subprocess.run(['podman','run','--rm','-v',str(ROOT)+':/src:ro,z','-v',str(cache)+':/cache:z',
            '-e','XEMU_UPDATE_VERSION='+tag[1:],'-e','XEMU_UPDATE_COMMIT='+obj['sha'],
            'docker.io/library/debian:trixie','sh','/src/cartucho/build/xemu-update-build.sh'],check=True)
        print('Candidato compilado. Validar e promover pelo empacotador; ainda não está no canal.',flush=True)


if __name__=='__main__':main()
