#!/bin/sh
# Small, auditable patch against the exact release used by the appliance.
set -eu
base=/cache/xemu-smc-build
source_dir=$base/src
commit=bf817de2b0354b7afe5e70efcd4f9c53bc7d4c67
patch=/src/cartucho/build/patches/xemu-0.8.138-smc-tray.patch
menu_patch=/src/cartucho/build/patches/xemu-0.8.138-menu-combo.patch
mkdir -p "$base"
# Both the preparatory compiler and image builds share this cache.
exec 9>"$base/build.lock"
flock 9
recipe=$(cat "$patch" "$menu_patch" /src/cartucho/build/xemu-smc.sh | sha256sum | cut -d' ' -f1)
if [ -f "$base/recipe.sha256" ] && [ "$(cat "$base/recipe.sha256")" = "$recipe" ]; then
    (cd "$base" && sha256sum -c xemu.sha256)
    echo 'xemu SMC: binario conferido em cache'
    exit 0
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends git curl ca-certificates build-essential cmake \
    pkg-config libcurl4-gnutls-dev libepoxy-dev libpixman-1-dev \
    libgtk-3-dev libssl-dev libsamplerate0-dev libpcap-dev ninja-build \
    python3-venv python3-pip python3-tomli python3-yaml libslirp-dev libvulkan-dev \
    libpipewire-0.3-dev zlib1g-dev libzstd-dev libasound2-dev libpulse-dev \
    libudev-dev libx11-dev libxcursor-dev libxfixes-dev libxi-dev libxrandr-dev \
    libxss-dev libwayland-dev libxkbcommon-dev libdecor-0-dev libegl-dev \
    libdrm-dev libgbm-dev >/dev/null
if [ ! -d "$source_dir/.git" ]; then
    git clone --depth 1 --branch v0.8.138 https://github.com/xemu-project/xemu.git "$source_dir"
fi
git -C "$source_dir" config --global --add safe.directory "$source_dir"
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$commit" ] || { echo 'commit xemu divergente' >&2; exit 1; }
for change in "$patch" "$menu_patch"; do
    if git -C "$source_dir" apply --check "$change" 2>/dev/null; then
        git -C "$source_dir" apply "$change"
    else
        git -C "$source_dir" apply --reverse --check "$change"
    fi
done
printf '0.8.138-xrevive-smc2\n' >"$source_dir/XEMU_VERSION"
printf '%s\n' "$commit" >"$source_dir/XEMU_COMMIT"
cd "$source_dir"
export XEMU_VERSION_SUFFIX=-xrevive-smc2
./build.sh -j6 --disable-docs --disable-guest-agent --disable-tools --disable-vnc --disable-curses \
    >"$base/compiler.log" 2>&1
install -m 0755 dist/xemu "$base/xemu"
strip --strip-unneeded "$base/xemu"
cp dist/LICENSE.txt "$base/LICENSE.txt"
dpkg-query -W >"$base/compiler-packages.txt"
(cd "$base" && sha256sum xemu >xemu.sha256)
printf '%s\n' "$recipe" >"$base/recipe.sha256"
printf '%s\n' "$commit" >"$base/upstream-commit"
echo 'xemu SMC: compilado e identificado'
