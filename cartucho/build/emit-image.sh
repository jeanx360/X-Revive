#!/bin/sh
set -eu
. /src/cartucho/build/versions.env
rootfs=${IMAGE_ROOTFS:?}
work=${IMAGE_WORK:?}
variant=${IMAGE_VARIANT:?}
mkdir -p "$work"
export IMAGE_VARIANT XREVIVE_VERSION
mkdir -p "$rootfs/usr/share/console"
python3 - <<'PY'
import hashlib, json, os, subprocess
from pathlib import Path
root = Path(os.environ['IMAGE_ROOTFS'])
driver = subprocess.run(['chroot', str(root), 'dpkg-query', '-W', '-f=${Version}', 'nvidia-driver'],
                        capture_output=True, text=True)
data = dict(version=os.environ['XREVIVE_VERSION'], distribution='public', build_id=os.environ['BUILD_ID'], source_sha256=os.environ['SOURCE_SHA'],
            variant=os.environ['IMAGE_VARIANT'], kernel=os.environ['IMAGE_KERNEL'],
            nvidia_driver=driver.stdout if driver.returncode == 0 else None)
data['utilities'] = {'rocky5': {'delivery':'online-or-user-iso','catalog_sha256':hashlib.sha256((root/'usr/share/console/rocky5-catalog.json').read_bytes()).hexdigest()}}
data['emulator'] = dict(version='0.8.138-xrevive-smc2',
    upstream_commit=Path('/cache/xemu-smc-build/upstream-commit').read_text().strip(),
    binary_sha256=hashlib.sha256((root/'opt/xemu/usr/bin/xemu').read_bytes()).hexdigest(),
    patch_sha256=hashlib.sha256(Path('/src/cartucho/build/patches/xemu-0.8.138-smc-tray.patch').read_bytes()).hexdigest(),
    menu_patch_sha256=hashlib.sha256(Path('/src/cartucho/build/patches/xemu-0.8.138-menu-combo.patch').read_bytes()).hexdigest())
data['updates'] = dict(protocol=1, runtime_abi='debian13-amd64-xrevive-smc2',
    public_key_sha256=hashlib.sha256((root/'usr/share/console/update-key.pem').read_bytes()).hexdigest())
(root/'usr/share/console/build.json').write_text(json.dumps(data, indent=2)+'\n')
PY
sys=$work/system
mkdir -p "$sys/EFI/BOOT" "$sys/live"
cp "$rootfs/boot/vmlinuz-$IMAGE_KERNEL" "$sys/live/vmlinuz"
cp "$rootfs/boot/initrd.img-$IMAGE_KERNEL" "$sys/live/initrd.img"
mksquashfs "$rootfs" "$sys/live/filesystem.squashfs" -comp zstd -e boot -noappend -quiet
system_partuuid=$(python3 -c 'import os,uuid;print(uuid.uuid5(uuid.NAMESPACE_URL,os.environ["BUILD_ID"]+"-installer-system"))')
system_id=$(printf %s "$system_partuuid" | cut -c1-8)
system_fsuuid=$(printf %s "$system_id" | sed 's/\(....\)\(....\)/\1-\2/' | tr a-f A-F)
sed -e "s/@SYSTEM_PARTUUID@/$system_partuuid/g" -e "s/@SYSTEM_FSUUID@/$system_fsuuid/g" \
    /src/cartucho/build/grub.cfg >"$work/grub.cfg"
grub-mkstandalone -O x86_64-efi -o "$sys/EFI/BOOT/BOOTX64.EFI" \
    "boot/grub/grub.cfg=$work/grub.cfg"
con=$work/console
mkdir -p "$con/firmware/$PLATFORM" "$con/config" "$con/profiles"
cp /src/cartucho/overlay/usr/local/lib/console/ports.conf.default "$con/config/ports.conf"
cp "$rootfs/usr/share/console/build.json" "$con/config/build.json"
# Firmware is imported by the owner from XREVIVE, never bundled.
stem=console-$PLATFORM-$variant
img=/out/$stem.img
mkfs.vfat -C -F 32 -i "$system_id" -n SYSTEM "$work/system.part" $((SYSTEM_MIB * 1024)) >/dev/null
mcopy -s -i "$work/system.part" "$sys"/* ::/
mkfs.vfat -C -F 32 -n CONSOLE "$work/console.part" $((CONSOLE_MIB * 1024)) >/dev/null
mcopy -s -i "$work/console.part" "$con"/* ::/
truncate -s "${CACHE_MIB}M" "$work/cache.part"
mkfs.ext4 -q -F -L CACHE "$work/cache.part" >/dev/null
utils=$work/utils
mkdir -p "$utils"
mkdir -p "$utils/payload"
printf '%s\n' '{"schema":1,"default_dashboard":"XBMC4Gamers","dashboards":[],"packages":[],"files":[]}' >"$utils/payload/manifest.json"
cp "$rootfs/usr/share/console/build.json" "$utils/build.json"
UTILS_MIB=64
truncate -s "${UTILS_MIB}M" "$work/utils.part"
mkfs.ext4 -q -F -m 0 -L UTILS -d "$utils" "$work/utils.part" >/dev/null
truncate -s $((SYSTEM_MIB + CONSOLE_MIB + CACHE_MIB + UTILS_MIB + USERS_MIB + 2))M "$img"
sfdisk -q "$img" <<EOF
label: gpt
start=1MiB, size=${SYSTEM_MIB}MiB, type=U, name=SYSTEM, uuid=$system_partuuid
size=${CONSOLE_MIB}MiB, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name=CONSOLE
size=${CACHE_MIB}MiB, type=0FC63DAF-8483-4772-8E79-3D69D8477DE4, name=CACHE
size=${UTILS_MIB}MiB, type=0FC63DAF-8483-4772-8E79-3D69D8477DE4, name=UTILS
size=${USERS_MIB}MiB, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name=XREVIVE
EOF
dd if="$work/system.part" of="$img" bs=1M seek=1 conv=notrunc status=none
dd if="$work/console.part" of="$img" bs=1M seek=$((1 + SYSTEM_MIB)) conv=notrunc status=none
dd if="$work/cache.part" of="$img" bs=1M seek=$((1 + SYSTEM_MIB + CONSOLE_MIB)) conv=notrunc status=none
dd if="$work/utils.part" of="$img" bs=1M seek=$((1 + SYSTEM_MIB + CONSOLE_MIB + CACHE_MIB)) conv=notrunc status=none
truncate -s "${USERS_MIB}M" "$work/users.part"
mkfs.exfat -L XREVIVE "$work/users.part" >/dev/null
# Area exFAT vazia: a arvore do usuario e criada no primeiro boot.
dd if="$work/users.part" of="$img" bs=1M seek=$((1 + SYSTEM_MIB + CONSOLE_MIB + CACHE_MIB + UTILS_MIB)) conv=notrunc status=none
sfdisk --verify "$img"
cp "$rootfs/usr/share/console/build.json" "/out/$stem.json"
chroot "$rootfs" dpkg-query -W >"/out/$stem.packages.txt"
echo "imagem concluida: $stem.img"
