#!/bin/sh
# Bancada virtual: roda o pendrive do console numa VM (QEMU/KVM + UEFI).
#
#   bancada/vm.sh [opcoes]
#     --novo-pendrive    descarta a copia do pendrive e copia a imagem de novo
#     --novo-hdd         apaga o HDD virtual (disco virgem)
#     --dvd <arquivo>    ISO no leitor de DVD (ex.: utilitario de formatacao)
#     --sem-controle     nao passa os controles Xbox desta maquina para a VM
#                        (por padrao todos os detectados vao para a VM)
#     --sem-janela       sem janela e video por software (lento, mas permite
#                        captura de tela com bancada/tela.sh)
#     --ligar-hdd        grava em ports.conf a porta do HDD virtual (pula o
#                        passo manual do primeiro boot)
#
# Tudo fica em bancada/vm/: os discos da VM sao arquivos, nenhum disco real
# desta maquina e usado. Log serial: bancada/vm/serial.log
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
vm=$root/bancada/vm
variant=universal
image=$root/cartucho/out/console-xbox-universal.img
ovmf=/usr/share/edk2/ovmf

new_pendrive=no
new_hdd=no
dvd=""
pass_controllers=yes
link_hdd=no
display="gtk,gl=on"
gpu=virtio-vga-gl
while [ $# -gt 0 ]; do
	case "$1" in
		--nvidia) variant=nvidia; image=$root/cartucho/out/console-xbox-nvidia.img; new_pendrive=yes ;;
		--novo-pendrive) new_pendrive=yes ;;
		--novo-hdd) new_hdd=yes ;;
		--dvd) dvd=$2; shift ;;
		--sem-controle) pass_controllers=no ;;
		--ligar-hdd) link_hdd=yes ;;
		--sem-janela) display=none gpu=virtio-vga ;;
		*) echo "opcao desconhecida: $1" >&2; exit 1 ;;
	esac
	shift
done

mkdir -p "$vm"
[ "$(cat "$vm/image-variant" 2>/dev/null || true)" = "$variant" ] || new_pendrive=yes

# Pendrive: copia da imagem gerada, com o modo de diagnostico ligado
if [ "$new_pendrive" = yes ] || [ ! -f "$vm/pendrive.img" ]; then
	cp --sparse=always "$image" "$vm/pendrive.img"
	: | mcopy -o -i "$vm/pendrive.img@@1M" - ::/debug
	printf '%s\n' "$variant" >"$vm/image-variant"
fi

if [ "$link_hdd" = yes ]; then
	# Particao CONSOLE comeca logo apos a SYSTEM (ver versions.env)
	. "$root/cartucho/build/versions.env"
	printf 'hdd=pci-0000:00:1f.2-ata-1\ndvd=auto\n' |
		mcopy -o -i "$vm/pendrive.img@@$((1 + SYSTEM_MIB))M" - ::/config/ports.conf
fi

# HDD do console: disco SATA virtual de 10 GB (o Xbox exige no minimo 8 GB)
if [ "$new_hdd" = yes ] || [ ! -f "$vm/hdd.img" ]; then
	rm -f "$vm/hdd.img"
	truncate -s 10G "$vm/hdd.img"
fi

[ -f "$vm/OVMF_VARS.fd" ] || cp "$ovmf/OVMF_VARS.fd" "$vm/OVMF_VARS.fd"

set -- \
	-name "console-appliance" \
	-enable-kvm -machine q35 -cpu host -smp 4 -m 4096 \
	-drive if=pflash,format=raw,readonly=on,file="$ovmf/OVMF_CODE.fd" \
	-drive if=pflash,format=raw,file="$vm/OVMF_VARS.fd" \
	-device qemu-xhci,id=xhci \
	-drive if=none,id=pendrive,format=raw,file="$vm/pendrive.img" \
	-device usb-storage,bus=xhci.0,drive=pendrive,bootindex=0 \
	-drive if=none,id=hdd,format=raw,file="$vm/hdd.img" \
	-device ide-hd,bus=ide.0,drive=hdd \
	-device "$gpu" -display "$display" \
	-audiodev pipewire,id=som -device ich9-intel-hda -device hda-output,audiodev=som \
	-serial file:"$vm/serial.log" \
	-monitor unix:"$vm/monitor.sock",server,nowait

# Leitor de DVD SATA (vazio se nao houver ISO)
if [ -n "$dvd" ]; then
	set -- "$@" -drive if=none,id=dvd,media=cdrom,readonly=on,file="$dvd"
else
	set -- "$@" -drive if=none,id=dvd,media=cdrom
fi
set -- "$@" -device ide-cd,bus=ide.1,drive=dvd

# Controles Xbox USB desta maquina, pela assinatura da interface:
#   ff/47/d0 One e Series (GIP)   ff/5d/01 360   58/42 Duke original
# e dongles sem fio pelo produto. Vao para a VM pela porta fisica.
is_xbox_pad() {
	for intf in "$1":*; do
		[ -f "$intf/bInterfaceClass" ] || continue
		case "$(cat "$intf/bInterfaceClass")/$(cat "$intf/bInterfaceSubClass")/$(cat "$intf/bInterfaceProtocol")" in
			ff/47/d0 | ff/5d/01 | 58/42/*) return 0 ;;
		esac
	done
	case "$(cat "$1/idVendor"):$(cat "$1/idProduct")" in
		045e:02e6 | 045e:02fe | 045e:02f9 | 045e:091e) return 0 ;;
	esac
	return 1
}
if [ "$pass_controllers" = yes ]; then
	for dev in /sys/bus/usb/devices/*; do
		[ -f "$dev/idVendor" ] && [ -f "$dev/devpath" ] || continue
		is_xbox_pad "$dev" || continue
		bus=$(cat "$dev/busnum")
		node=$(printf '/dev/bus/usb/%03d/%03d' "$bus" "$(cat "$dev/devnum")")
		name="$(cat "$dev/product" 2>/dev/null || echo controle) ($(cat "$dev/idVendor"):$(cat "$dev/idProduct"))"
		if [ ! -w "$node" ]; then
			echo "controle sem permissao: $name. Rode uma vez: sudo bancada/permitir-controle.sh" >&2
			continue
		fi
		echo "controle na VM: $name"
		set -- "$@" -device usb-host,bus=xhci.0,hostbus="$bus",hostport="$(cat "$dev/devpath")"
	done
fi

exec qemu-system-x86_64 "$@"
