#!/bin/sh
# Uma midia USB instaladora, com Mesa e NVIDIA no mesmo sistema.
set -eu
root=$(cd "$(dirname "$0")/../.." && pwd)
platform=${1:?uso: build.sh xbox [diretorio-de-firmware]}
firmware=${2:-}
case "$platform" in xbox) ;; *) echo 'plataforma nao suportada' >&2; exit 1;; esac
. "$root/cartucho/build/versions.env"
mkdir -p "$root/cartucho/out" "$root/cartucho/cache"
source_sha=$(python3 "$root/cartucho/build/release.py" source "$root" "$platform")
build_id="$(date -u +%Y%m%dT%H%M%SZ)-$(printf %.12s "$source_sha")"
stage=$(mktemp -d "$root/cartucho/cache/pair.XXXXXX")
echo "build_id=$build_id staging=$stage"
set -- podman run --rm --privileged \
 -v "$root:/src:ro,z" -v "$stage:/out:z" -v "$root/cartucho/cache:/cache:z" \
 -e "PLATFORM=$platform" -e "BUILD_ID=$build_id" -e "SOURCE_SHA=$source_sha"
if [ -n "$firmware" ]; then
 set -- "$@" -v "$(cd "$firmware" && pwd):/firmware:ro,z"
fi
"$@" "docker.io/library/debian:$DEBIAN_SUITE" sh /src/cartucho/build/inside.sh
[ "$(python3 "$root/cartucho/build/release.py" source "$root" "$platform")" = "$source_sha" ] \
 || { echo 'Fontes mudaram durante o build; par nao publicado.' >&2; exit 1; }
if [ "${PUBLISH_RELEASE:-1}" = 0 ]; then
 echo "Build em rascunho para QA, sem alterar out: $stage"
 exit 0
fi
python3 "$root/cartucho/build/release.py" publish "$stage" "$root/cartucho/out" "$platform" "$build_id" "$source_sha"
rmdir "$stage"
