#!/bin/sh
# Roda dentro do container Debian (chamado por build.sh).
set -eu

. /src/cartucho/build/versions.env
work=/tmp/build
rootfs=$work/rootfs
mkdir -p "$work"

apt-get update -qq
apt-get install -y -qq --no-install-recommends \
	mmdebstrap squashfs-tools dosfstools e2fsprogs exfatprogs mtools fdisk \
	grub-efi-amd64-bin grub-common ca-certificates curl >/dev/null

# xemu fixado por versao e hash
appimage=/cache/xemu-$XEMU_VERSION-x86_64.AppImage
[ -f "$appimage" ] || curl -sfL -o "$appimage" \
	"https://github.com/xemu-project/xemu/releases/download/v$XEMU_VERSION/xemu-$XEMU_VERSION-x86_64.AppImage"
echo "$XEMU_SHA256  $appimage" | sha256sum -c -
sh /src/cartucho/build/xemu-smc.sh

# Sistema base
packages=$(grep -v -e '^#' -e '^$' /src/cartucho/build/packages.list | paste -sd, -)
mmdebstrap --mode=root --variant=minbase \
	--components="main contrib non-free non-free-firmware" \
	--include="$packages" \
	--customize-hook='useradd -R "$1" -m -U -G video,render,input,audio,cdrom console' \
	--customize-hook='cp -r --preserve=mode /src/cartucho/overlay/. "$1/"' \
	--customize-hook="cp -r --preserve=mode /src/plataformas/$PLATFORM \"\$1/usr/local/lib/console/platform\"" \
	--customize-hook='mkdir -p "$1/usr/local/lib/console/hal" && cp --preserve=mode /src/hal/probe.sh "$1/usr/local/lib/console/hal/"' \
	--customize-hook='chroot "$1" systemctl enable console-prepare.service console-update-health.service console-pad.service console.service console-tray-monitor.service console-installer.service console-installer-worker.service console-diagnostics.service systemd-networkd.service systemd-resolved.service' \
	--customize-hook='chroot "$1" systemctl mask getty@tty1.service getty@tty3.service console-getty.service plymouth-quit.service plymouth-quit-wait.service' \
	--customize-hook='echo console > "$1/etc/hostname"' \
	--customize-hook='chroot "$1" plymouth-set-default-theme x-revive || true' \
	--customize-hook='chroot "$1" update-initramfs -u' \
	"$DEBIAN_SUITE" "$rootfs"

# Docs do repositorio nao vao para o console (tools/ fica: o auto-instalador usa hdd.py)
rm -f "$rootfs/usr/local/lib/console/platform/README.md"
# Apenas os assets da animação seguem no runtime; a dashboard é do catálogo.
rm -rf "$rootfs/usr/local/lib/console/platform/firstrun/dash" "$rootfs/usr/local/lib/console/platform/firstrun/bootanims"

# pyfatx (abi3) para o auto-instalador formatar FATX no 1o boot do console
apt-get install -y -qq --no-install-recommends python3-pip >/dev/null
pip3 download --no-deps --only-binary :all: pyfatx==0.0.8 -d "$work/wh"
mkdir -p "$rootfs/usr/lib/python3/dist-packages"
python3 -m zipfile -e "$(ls "$work"/wh/pyfatx-*.whl)" "$rootfs/usr/lib/python3/dist-packages/"

# xemu extraido em /opt/xemu
(cd "$work" && sh -c "cp '$appimage' xemu.AppImage && chmod +x xemu.AppImage && ./xemu.AppImage --appimage-extract >/dev/null")
mv "$work/squashfs-root" "$rootfs/opt/xemu"
# A extracao cria arquivos so para o dono; o usuario console precisa executar
chmod -R a+rX "$rootfs/opt/xemu"
cp /cache/xemu-smc-build/xemu "$rootfs/opt/xemu/usr/bin/xemu"
mkdir -p "$rootfs/usr/share/doc/xrevive-xemu"
cp /cache/xemu-smc-build/LICENSE.txt /cache/xemu-smc-build/xemu.sha256 \
   /cache/xemu-smc-build/upstream-commit /cache/xemu-smc-build/compiler-packages.txt \
   /src/cartucho/build/patches/xemu-0.8.138-smc-tray.patch \
   /src/cartucho/build/patches/xemu-0.8.138-menu-combo.patch "$rootfs/usr/share/doc/xrevive-xemu/"

# Bibliotecas que o xemu espera do sistema e nao existem na imagem
missing=$(chroot "$rootfs" ldd /opt/xemu/usr/bin/xemu | grep 'not found' || true)
if [ -n "$missing" ]; then
	echo "xemu: bibliotecas faltando na imagem:" >&2
	echo "$missing" >&2
	exit 1
fi

# Dongle sem fio do Xbox: xone, compilado para o kernel da imagem. Controles
# com fio (Duke original, One, Series) ficam com o xpad do kernel, entao o
# xone_wired nao e instalado e o xpad continua ativo.
kver=$(ls "$rootfs/lib/modules")
xone=/cache/xone-$XONE_VERSION.tar.gz
[ -f "$xone" ] || curl -sfL -o "$xone" \
	"https://github.com/dlundqvist/xone/archive/refs/tags/v$XONE_VERSION.tar.gz"
echo "$XONE_SHA256  $xone" | sha256sum -c -
apt-get install -y -qq --no-install-recommends make gcc "linux-headers-$kver" >/dev/null
tar -xzf "$xone" -C "$work"
make -s -C "/usr/src/linux-headers-$kver" M="$work/xone-$XONE_VERSION" modules
mkdir -p "$rootfs/lib/modules/$kver/updates/xone"
for m in "$work/xone-$XONE_VERSION"/*.ko; do
	case "${m##*/}" in xone_wired.ko) continue ;; esac
	cp "$m" "$rootfs/lib/modules/$kver/updates/xone/"
done
chroot "$rootfs" depmod "$kver"
# O mt76x2u tambem reconhece o dongle (e um chip MT76) e tomaria o lugar do xone
echo "blacklist mt76x2u" >"$rootfs/etc/modprobe.d/xone.conf"
# Firmware do adaptador sem fio pertence ao usuário e não entra na IMG pública.
# A limpeza também cobre bases locais usadas por repack.
python3 /src/cartucho/build/public-rootfs.py "$rootfs" /src

# Uma imagem com Mesa e NVIDIA. O destino instalado usa este mesmo sistema.
export IMAGE_ROOTFS="$rootfs" IMAGE_KERNEL="$kver"
IMAGE_ROOTFS="$rootfs" sh /src/cartucho/build/nvidia.sh
echo auto >"$rootfs/etc/console-variant"
IMAGE_VARIANT=installer IMAGE_WORK="$work/installer" sh /src/cartucho/build/emit-image.sh
