#!/bin/sh
set -eu
. /src/cartucho/build/versions.env
rootfs=${IMAGE_ROOTFS:?}
kver=${IMAGE_KERNEL:?}
# Limitar RAM durante a compilacao e nunca carregar modulos no kernel do host.
mkdir -p "$rootfs/etc/dkms/framework.conf.d"
printf 'parallel_jobs=4\nmodprobe_on_install="no"\n' >"$rootfs/etc/dkms/framework.conf.d/console.conf"
# resolved ainda nao roda no chroot; fornecer DNS apenas durante o build.
mkdir -p "$rootfs/run/systemd/resolve"
cp /etc/resolv.conf "$rootfs/run/systemd/resolve/stub-resolv.conf"
# O bootstrap ja desmontou /dev e /proc; recriar ambiente privado do chroot.
# Nao expor os dispositivos GPU do host ao instalador.
mount -t tmpfs -o mode=755 tmpfs "$rootfs/dev"
cleanup() {
    umount "$rootfs/proc" 2>/dev/null || true
    for name in null zero random urandom; do umount "$rootfs/dev/$name" 2>/dev/null || true; done
    umount "$rootfs/dev" 2>/dev/null || true
}
trap cleanup EXIT
# Bind dos dispositivos basicos funciona tambem em podman rootless; mknod nao.
for name in null zero random urandom; do
    touch "$rootfs/dev/$name"
    mount --bind "/dev/$name" "$rootfs/dev/$name"
done
mount --bind /proc "$rootfs/proc"
ln -s /proc/self/fd "$rootfs/dev/fd"
chroot "$rootfs" apt-get update -qq
chroot "$rootfs" env DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Use-Pty=0 install -y --no-install-recommends \
    "linux-headers-$kver" "nvidia-driver=$NVIDIA_VERSION" \
    "nvidia-kernel-dkms=$NVIDIA_VERSION" "nvidia-smi=$NVIDIA_VERSION" \
    "nvidia-vulkan-icd=$NVIDIA_VERSION" "libgles-nvidia2=$NVIDIA_VERSION" \
    "libnvidia-allocator1=$NVIDIA_VERSION" \
    libnvidia-egl-wayland1 libnvidia-egl-gbm1
chroot "$rootfs" dkms autoinstall -k "$kver"
chroot "$rootfs" depmod "$kver"
test -f "$rootfs/usr/lib/x86_64-linux-gnu/nvidia/current/nvidia-drm_gbm.so"
module=$(find "$rootfs/lib/modules/$kver" -name '*nvidia*drm*.ko*' | head -n1)
[ -n "$module" ] || { echo 'modulo NVIDIA DRM ausente' >&2; exit 1; }
chroot "$rootfs" modinfo -F vermagic "${module#"$rootfs"}" | grep -F "$kver"
mkdir -p "$rootfs/etc/modprobe.d"
cat >"$rootfs/etc/modprobe.d/console-nvidia.conf" <<EOF
blacklist nouveau
options nvidia-drm modeset=1 fbdev=1
options nvidia-current-drm modeset=1 fbdev=1
EOF
# xrevive-video hook includes the modules without forcing them onto machines
# without NVIDIA. The init-premount script loads them only for a matching GPU.
# Debian's GLX alternative also creates a global modules-load entry. Mask that
# entry; otherwise systemd tries NVIDIA on Intel/AMD/virtio after switch-root.
ln -sfn /dev/null "$rootfs/etc/modules-load.d/nvidia.conf"
chroot "$rootfs" update-initramfs -u -k "$kver"
chroot "$rootfs" lsinitramfs "/boot/initrd.img-$kver" >/cache/nvidia-initramfs.list
grep -E 'nvidia.*drm.*ko' /cache/nvidia-initramfs.list
chroot "$rootfs" dpkg-query -W nvidia-driver nvidia-kernel-dkms
rm -f "$rootfs/run/systemd/resolve/stub-resolv.conf"
umount "$rootfs/proc"
for name in null zero random urandom; do umount "$rootfs/dev/$name"; done
umount "$rootfs/dev"
trap - EXIT
