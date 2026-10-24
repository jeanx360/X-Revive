"""Identify build inputs and publish validated images as one release."""
import hashlib
import json
import os
from pathlib import Path
import sys


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def source(root, platform):
    root = Path(root)
    h = hashlib.sha256()
    files = []
    for folder in ('cartucho/build', 'cartucho/overlay', 'hal', f'plataformas/{platform}'):
        files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                     and 'firstrun' not in p.relative_to(root).parts)
    # These notices are copied into the public rootfs and are build inputs.
    files.extend(root/name for name in ('LICENSE', 'NOTICE.md', 'THIRD_PARTY_NOTICES.md')
                 if (root/name).is_file())
    for p in sorted(files):
        h.update(str(p.relative_to(root)).encode() + b'\0')
        h.update(oct(p.stat().st_mode & 0o777).encode() + b'\0')
        h.update(p.read_bytes())
    return h.hexdigest()


def publish(stage, output, platform, build_id, source_sha):
    stage, output = Path(stage), Path(output)
    entries = []
    # Validate the complete staged set before replacing anything in out.
    variants = ['installer'] if (stage/f'console-{platform}-installer.json').exists() else ['universal', 'nvidia']
    if any((stage/f'console-{platform}-standalone{suffix}').exists() for suffix in ('.img', '.json')):
        variants.append('standalone')
    for variant in variants:
        stem = f'console-{platform}-{variant}'
        image = stage/f'{stem}.img'
        metadata = json.loads((stage/f'{stem}.json').read_text())
        if (metadata.get('build_id'), metadata.get('source_sha256'), metadata.get('variant')) != (build_id, source_sha, variant):
            raise ValueError(f'Identidade divergente: {stem}')
        if not image.is_file() or image.stat().st_size == 0:
            raise ValueError(f'Imagem ausente/vazia: {stem}')
        packages = stage/f'{stem}.packages.txt'
        if not packages.is_file():
            raise ValueError(f'Manifesto de pacotes ausente: {stem}')
        if variant == 'standalone' and (not metadata.get('experimental') or not (stage/f'{stem}.layout.json').is_file()):
            raise ValueError('Standalone sem marcador experimental/layout')
        checksum = digest(image)
        (stage/f'{stem}.img.sha256').write_text(f'{checksum}  {stem}.img\n')
        entries.append(dict(file=image.name, sha256=checksum, bytes=image.stat().st_size, **metadata))
    if any(e['kernel'] != entries[0]['kernel'] for e in entries):
        raise ValueError('Kernel divergente entre variantes')
    if any(e.get('utilities') != entries[0].get('utilities') for e in entries):
        raise ValueError('Utilitarios divergentes entre variantes')
    if any(e.get('emulator') != entries[0].get('emulator') for e in entries):
        raise ValueError('Emulador divergente entre variantes')
    output.mkdir(parents=True, exist_ok=True)
    manifest = dict(build_id=build_id, source_sha256=source_sha, images=entries)
    (stage/'release.json').write_text(json.dumps(manifest, indent=2)+'\n')
    for entry in entries:
        stem = entry['file'].removesuffix('.img')
        for suffix in ('.img', '.img.sha256', '.json', '.packages.txt'):
            os.replace(stage/(stem+suffix), output/(stem+suffix))
        if entry['variant'] == 'standalone':
            os.replace(stage/(stem+'.layout.json'), output/(stem+'.layout.json'))
    # This manifest is the commit marker: verify its checksums after interruption.
    os.replace(stage/'release.json', output/'release.json')
    if variants == ['installer']:
        # Preserve superseded artifacts outside out, rather than delete them.
        retired=output.parent/'cache'/('retired-before-'+build_id)
        for image in list(output.glob(f'console-{platform}-*.img')):
            if image.name == entries[0]['file']:continue
            retired.mkdir(parents=True,exist_ok=True)
            stem=image.stem
            for old in output.glob(stem+'.*'):
                destination=retired/old.name
                if destination.exists():raise ValueError('arquivo de baseline já existe')
                os.rename(old,destination)
    for suffix in ('.img', '.img.sha256'):
        legacy = output/f'console-{platform}{suffix}'
        if legacy.is_file():
            legacy.unlink()
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    if sys.argv[1] == 'source':
        print(source(*sys.argv[2:]))
    elif sys.argv[1] == 'publish':
        publish(*sys.argv[2:])
    else:
        raise SystemExit('acao desconhecida')
