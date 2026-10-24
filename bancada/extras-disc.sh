#!/bin/sh
# Gera a ISO do Extras Disc do Xbox Softmodding Tool (Rocky5) para o leitor
# de DVD virtual da bancada.
#
#   bancada/extras-disc.sh <repo-softmodding-tool>
#   bancada/vm.sh --dvd bancada/vm/extras-disc.iso
#
# Equivale ao Build XISO.bat original, usando o zip de reinstalacao do softmod
# que ja vem no repositorio (o .bat o regera com WinRAR).
set -eu

[ $# -eq 1 ] || { echo "uso: $0 <repo-softmodding-tool>" >&2; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
smt=$(cd "$1" && pwd)
[ -f "$smt/Extras Disc/default.xbe" ] || { echo "$smt: Extras Disc nao encontrado" >&2; exit 1; }
mkdir -p "$root/bancada/vm"

# extract-xiso fixado por tag (XboxDev)
tag=build-202505152050
podman run --rm \
	-v "$smt/Extras Disc":/disc:ro,Z \
	-v "$root/bancada/vm":/out:Z \
	debian:trixie sh -euc "
		apt-get update -qq
		apt-get install -y -qq --no-install-recommends git ca-certificates build-essential cmake >/dev/null
		git clone -q --depth 1 --branch $tag https://github.com/XboxDev/extract-xiso /tmp/x
		cmake -S /tmp/x -B /tmp/x/build >/dev/null && make -s -C /tmp/x/build
		mkdir -p /tmp/disc && cp -r /disc/. /tmp/disc/
		find /tmp/disc -iname thumbs.db -delete
		cd /tmp && /tmp/x/build/extract-xiso -c /tmp/disc /out/extras-disc.iso
	"
ls -lh "$root/bancada/vm/extras-disc.iso"
