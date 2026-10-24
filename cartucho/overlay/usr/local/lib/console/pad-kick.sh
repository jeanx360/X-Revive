#!/bin/sh
# Controle Xbox One/Series plugado no boot as vezes nao e visto pelo emulador
# ate um re-plug (quirk do xpad no cold-boot). Aqui, depois que o emulador sobe,
# re-enumeramos o controle (como um re-plug), e o xemu o detecta via hotplug.
set -eu
i=0
while ! pgrep -u console -f '^/opt/|^/var/cache/console/updates/versions/[a-f0-9]+/xemu|python3 /usr/local/lib/console/(installer|update)-ui.py' >/dev/null 2>&1 && [ "$i" -lt 40 ]; do
	sleep 0.5; i=$((i + 1))
done
sleep 1
is_gip() {   # interface GIP do Xbox One/Series: classe ff / sub 47 / proto d0
	for intf in "$1":*; do
		[ -f "$intf/bInterfaceClass" ] || continue
		[ "$(cat "$intf/bInterfaceClass")$(cat "$intf/bInterfaceSubClass")$(cat "$intf/bInterfaceProtocol")" = "ff47d0" ] && return 0
	done
	return 1
}
for dev in /sys/bus/usb/devices/*; do
	[ -f "$dev/idVendor" ] || continue
	is_gip "$dev" || continue
	[ -w "$dev/authorized" ] || continue
	echo 0 >"$dev/authorized" 2>/dev/null || continue
	sleep 0.3
	echo 1 >"$dev/authorized" 2>/dev/null || true
done
