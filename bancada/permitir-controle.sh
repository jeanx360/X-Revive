#!/bin/sh
# Libera os controles Xbox USB desta maquina para a VM da bancada (passthrough
# USB do QEMU precisa de escrita em /dev/bus/usb). Roda uma vez, com sudo.
#
#   sudo bancada/permitir-controle.sh
#
# A regra da acesso ao usuario logado na sessao (uaccess), como o desktop ja
# faz com webcams e outros dispositivos. Para desfazer, apague o arquivo.
set -eu

rule=/etc/udev/rules.d/70-console-appliance-controle.rules
[ "$(id -u)" -eq 0 ] || { echo "rode com sudo" >&2; exit 1; }

# Microsoft, PDP, PowerA, Hori: controles Xbox originais e licenciados
cat >"$rule" <<'RULES'
# console-appliance: controles Xbox liberados para passthrough na VM
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="045e", TAG+="uaccess"
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="0e6f", TAG+="uaccess"
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="24c6", TAG+="uaccess"
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="20d6", TAG+="uaccess"
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="0f0d", TAG+="uaccess"
RULES
udevadm control --reload
udevadm trigger --subsystem-match=usb --action=change
echo "regra instalada: $rule"
