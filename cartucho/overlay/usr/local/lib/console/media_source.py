"""Discover owner media without guessing its purpose from name or contents."""
import os
import hashlib
from pathlib import Path

EXTENSIONS={'.iso','.xiso','.img'}


def candidates(user):
    user=Path(user);seen=set()
    # Also accept the earlier USB layout with pacotes directly in XREVIVE.
    for root in (user/'pacotes',user.parent/'pacotes'):
        if not root.is_dir() or root.is_symlink():continue
        for base,dirs,files in os.walk(root,followlinks=False):
            dirs[:]=sorted(d for d in dirs if not (Path(base)/d).is_symlink())
            for name in files:
                path=Path(base)/name
                if path.suffix.lower() not in EXTENSIONS or path.is_symlink() or not path.is_file():continue
                resolved=path.resolve()
                if resolved in seen or not resolved.is_relative_to(root.resolve()):continue
                seen.add(resolved)
                label=path.relative_to(root).as_posix()
                if root==user.parent/'pacotes':label='pacotes/'+label
                yield path,label


def images(user):
    rows=[]
    for path,name in candidates(user):
        try:rows.append(dict(id=hashlib.sha256(str(path.resolve()).encode()).hexdigest(),name=name,bytes=path.stat().st_size))
        except FileNotFoundError:continue
    return sorted(rows,key=lambda r:r['name'].casefold())


def selected(user,identity):
    for path,_ in candidates(user):
        if hashlib.sha256(str(path.resolve()).encode()).hexdigest()==identity:return path.resolve()
    raise ValueError('Mídia ausente ou removida; atualize a lista do pendrive')
