"""Fetch the complete selected Rocky5 catalog into a versioned local cache.

Only downloads/inspects archives. Never executes them or touches Xbox disks.
An existing lock is verified, never silently refreshed by a normal build.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = 'https://www.xbmc4gamers.co.uk/X4G-XEmu/urldownloader/'
COMMIT = '53203aa1c1272468c9374f260233f92557c9f324'
CATEGORIES = ('dashboards', 'applications', 'emulators', 'themes')


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'X-Revive package catalog/2 (read-only download)'}), timeout=60)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(4*1024**2): h.update(chunk)
    return h.hexdigest()


def catalog():
    result = []
    for category in CATEGORIES:
        with get(BASE+category+'/') as response:
            page = response.read().decode('utf8')
        for link, title in re.findall(r'<a[^>]+href=[\"\x27]([^\"\x27]+)[\"\x27][^>]*>(.*?)</a>', page, re.S|re.I):
            if not link.lower().endswith('.zip'): continue
            url = urllib.parse.urljoin(BASE+category+'/', link)
            url = urllib.parse.quote(url, safe=':/%')
            key = category+'-'+hashlib.sha256(url.encode()).hexdigest()[:12]
            result.append(dict(id=key, category=category, title=re.sub('<[^>]+>', '', title).strip(),
                               url=url, file=key+'.zip'))
    for filename in ('Dashloader.ini', 'evoxdash.xbe'):
        url = 'https://raw.githubusercontent.com/Rocky5/Xbox-Softmodding-Tool/'+COMMIT+'/Extras%20Disc/Hardmod/dashloader/'+filename
        result.append(dict(id='hardmod-'+filename, category='loader', title=filename,
                           url=url, file='hardmod-'+filename))
    result.append(dict(id='shortcut-msdash',category='loader',title='Microsoft Dashboard Shortcut',
        url='https://raw.githubusercontent.com/Rocky5/Xbox-Softmodding-Tool/'+COMMIT+'/Extras%20Disc/Softmod/dashboards/msdash/other/msdash.xbe',
        file='shortcut-msdash.xbe'))
    return result


def fetch(cache, lock):
    cache, lock = Path(cache), Path(lock)
    cache.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        data = json.loads(lock.read_text())
        entries = data['packages']
    else:
        entries = catalog()
        data = dict(schema=1, upstream_commit=COMMIT, catalog=BASE, packages=entries)

    def download(item):
        target = cache/item['file']
        if not target.exists():
            temporary = target.with_suffix(target.suffix+'.download')
            print('download', item['category'], item['title'], flush=True)
            for attempt in range(4):
                try:
                    with get(item['url']) as response, temporary.open('wb') as f:
                        while chunk := response.read(1024**2): f.write(chunk)
                    break
                except OSError:
                    if attempt == 3: raise
                    time.sleep(attempt+1)
            temporary.replace(target)
        actual = digest(target)
        if item.get('sha256') and item['sha256'] != actual:
            raise ValueError('pacote mudou: '+item['id'])
        if item['file'].endswith('.zip'):
            with zipfile.ZipFile(target) as archive:
                if archive.testzip(): raise ValueError('ZIP corrompido: '+item['id'])
                item['unpacked_bytes'] = sum(i.file_size for i in archive.infolist())
                item['entries'] = len(archive.infolist())
        item.update(sha256=actual, bytes=target.stat().st_size)
        return item

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(download, entries))
    temporary = lock.with_suffix('.json.new')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
    temporary.replace(lock)
    print('ROCKY5_CATALOG_VERIFIED', len(entries), sum(i['bytes'] for i in entries), flush=True)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', default=str(ROOT/'cartucho/cache/rocky5/packages'))
    parser.add_argument('--lock', default=str(ROOT/'cartucho/build/rocky5.lock.json'))
    args = parser.parse_args()
    fetch(args.cache, args.lock)
