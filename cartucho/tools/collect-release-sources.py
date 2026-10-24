"""Collect exact Debian source packages for an extracted release rootfs.

Run inside a Debian container with authenticated deb-src indexes. Downloads only;
never installs packages or opens a host disk. Includes Built-Using dependencies.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request


def paragraphs(text):
    result=[]
    for raw in text.strip().split('\n\n'):
        data={};key=None
        for line in raw.splitlines():
            if line[:1].isspace() and key:data[key]+='\n'+line[1:]
            elif ':' in line:key,value=line.split(':',1);data[key]=value.lstrip(' ')
        if data:result.append(data)
    return result


def units(status):
    result=set()
    for package in paragraphs(status):
        if package.get('Status')!='install ok installed':continue
        source=package.get('Source',package['Package'])
        match=re.fullmatch(r'([a-z0-9+.-]+)(?: \(([^)]+)\))?',source)
        if not match:raise ValueError('Invalid source field: '+source)
        result.add((match[1],match[2] or re.sub(r'\+b\d+$','',package['Version'])))
        for field in ('Built-Using','Static-Built-Using'):
            for name,version in re.findall(r'([a-z0-9+.-]+)\s*\(=\s*([^)]+)\)',package.get(field,'')):
                result.add((name,version))
    return sorted(result)


def resolve(unit):
    name,version=unit
    result=subprocess.run(['apt-cache','showsrc','--only-source',name],capture_output=True,text=True,check=True)
    matches=[p for p in paragraphs(result.stdout) if p.get('Package')==name and p.get('Version')==version]
    if not matches:raise ValueError('Exact source not in authenticated indexes: '+name+'='+version)
    record=matches[0];directory=record['Directory']
    if '..' in directory.split('/') or not directory.startswith('pool/'):raise ValueError('Invalid directory')
    base='https://security.debian.org/debian-security/' if directory.startswith('pool/updates/') else 'https://deb.debian.org/debian/'
    files=[]
    for line in record['Checksums-Sha256'].splitlines():
        if not line.strip():continue
        digest,size,filename=line.split()
        if not re.fullmatch(r'[A-Za-z0-9.+~_-]+',filename):raise ValueError('Invalid filename')
        files.append(dict(file=filename,bytes=int(size),sha256=digest,url=base+directory+'/'+filename))
    return dict(package=name,version=version,files=files)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(4*1024**2):h.update(chunk)
    return h.hexdigest()


def fetch(item,folder):
    path=folder/item['file']
    if path.is_file() and path.stat().st_size==item['bytes'] and sha(path)==item['sha256']:return
    for attempt in range(3):
        try:
            temporary=path.with_suffix(path.suffix+'.download');h=hashlib.sha256();size=0
            req=urllib.request.Request(item['url'],headers={'User-Agent':'X-Revive corresponding sources/1'})
            with urllib.request.urlopen(req,timeout=60) as response,temporary.open('wb') as f:
                if not response.url.startswith('https://'):raise ValueError('HTTPS downgrade')
                while chunk:=response.read(1024**2):
                    size+=len(chunk)
                    if size>item['bytes']:raise ValueError('Oversized source')
                    h.update(chunk);f.write(chunk)
            if size!=item['bytes'] or h.hexdigest()!=item['sha256']:raise ValueError('Source checksum mismatch')
            temporary.replace(path);return
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('rootfs',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
    wanted=units((a.rootfs/'var/lib/dpkg/status').read_text());a.output.mkdir(parents=True,exist_ok=True)
    records=[];missing=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[(u,pool.submit(resolve,u)) for u in wanted]
        for unit,future in futures:
            try:records.append(future.result())
            except Exception as e:missing.append(dict(package=unit[0],version=unit[1],error=str(e)))
    (a.output/'coverage.json').write_text(json.dumps(dict(requested=len(wanted),resolved=len(records),missing=missing),indent=2)+'\n')
    if missing:raise SystemExit('Missing '+str(len(missing))+' source versions; see coverage.json')
    manifest=dict(schema=1,packages=records)
    (a.output/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
    unique={}
    for r in records:
        for item in r['files']:
            if item['file'] in unique and item['sha256']!=unique[item['file']]['sha256']:raise ValueError('Conflicting filename')
            unique[item['file']]=item
    folder=a.output/'debian';folder.mkdir(exist_ok=True)
    print('DEBIAN_SOURCE_PLAN',len(records),'source versions',len(unique),'files',sum(i['bytes'] for i in unique.values()),'bytes',flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[(item,pool.submit(fetch,item,folder)) for item in unique.values()]
        for n,(item,future) in enumerate(futures,1):
            future.result()
            if n%25==0 or item['bytes']>100*1024**2:print('SOURCE_VERIFIED',n,'/',len(unique),item['file'],flush=True)
    print('ALL_DEBIAN_SOURCES_VERIFIED',len(records),len(unique),flush=True)


if __name__=='__main__':main()
