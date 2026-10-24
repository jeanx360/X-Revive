#!/bin/sh
# Repack only an explicitly supplied, locally built rootfs archive. No host disk.
set -eu
root=$(cd "$(dirname "$0")/../.." && pwd)
archive=${1:?uso: repack-rootfs.sh ARQUIVO-ROOTFS-TAR}
[ -f "$archive" ] || exit 1
sha=$(python3 "$root/cartucho/build/release.py" source "$root" xbox)
build_id="$(date -u +%Y%m%dT%H%M%SZ)-$(printf %.12s "$sha")"
stage=$(mktemp -d "$root/cartucho/cache/repack.XXXXXX")
echo "build_id=$build_id staging=$stage"
podman run --rm --privileged -v "$root:/src:ro,z" -v "$root/cartucho/cache:/cache:z" \
 -v "$stage:/out:z" -v "$(realpath "$archive"):/base.tar:ro,z" \
 -e BUILD_ID="$build_id" -e SOURCE_SHA="$sha" -e PLATFORM=xbox \
 docker.io/library/debian:trixie sh -c '
 set -eu
 apt-get update -qq
 apt-get install -y -qq --no-install-recommends python3 squashfs-tools dosfstools e2fsprogs exfatprogs mtools fdisk grub-efi-amd64-bin grub-common >/dev/null
 mkdir -p /tmp/build/rootfs
 tar -xf /base.tar -C /tmp/build/rootfs
 cp -r --preserve=mode /src/cartucho/overlay/. /tmp/build/rootfs/
 cp -r --preserve=mode /src/plataformas/xbox/. /tmp/build/rootfs/usr/local/lib/console/platform/
 cp --preserve=mode /src/hal/probe.sh /tmp/build/rootfs/usr/local/lib/console/hal/
 rm -rf /tmp/build/rootfs/usr/local/lib/console/platform/firstrun/dash /tmp/build/rootfs/usr/local/lib/console/platform/firstrun/bootanims
 python3 /src/cartucho/build/public-rootfs.py /tmp/build/rootfs /src
 export IMAGE_ROOTFS=/tmp/build/rootfs IMAGE_WORK=/tmp/build/installer IMAGE_VARIANT=installer
 export IMAGE_KERNEL=$(ls /tmp/build/rootfs/lib/modules)
 sh /src/cartucho/build/emit-image.sh'
[ "$(python3 "$root/cartucho/build/release.py" source "$root" xbox)" = "$sha" ] || { echo 'Fontes mudaram; nao publicar'; exit 1; }
echo "QA_CANDIDATE=$stage"
