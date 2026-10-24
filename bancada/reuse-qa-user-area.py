"""Clone only the verified USER region between regular QA USB image files."""
import argparse
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('dest',type=Path);a=p.parse_args()
for f in (a.source,a.dest):
 if not f.is_file():raise ValueError('somente arquivos regulares de bancada')
def part(f):
 rows=json.loads(subprocess.check_output(['sfdisk','-J',str(f)],text=True))['partitiontable']['partitions']
 return next(r for r in rows if r['name']=='XREVIVE')
s,d=part(a.source),part(a.dest);assert s['size']==d['size']
with a.source.open('rb') as src,a.dest.open('r+b') as dst:
 src.seek(s['start']*512);dst.seek(d['start']*512);left=s['size']*512
 while left:
  data=src.read(min(left,4*1024**2));assert data;dst.write(data);left-=len(data)
print('QA_USER_REGION_COPIED')
