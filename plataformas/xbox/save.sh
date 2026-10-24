#!/bin/sh
# No desligamento: preserva EEPROM e preferencias do xemu no pendrive.
set -eu

src="$RUN/eeprom.bin"
dst="$CONSOLE/firmware/xbox/eeprom.bin"
here=$(dirname "$0")
# Valida antes de abrir a janela de escrita. EEPROM inalterada nao deve
# impedir o salvamento das preferencias (o comportamento anterior saía aqui).
preferences_ready=no
if python3 "$here/tools/preferences.py" capture "$RUN/xemu.toml" "$RUN/profile" "$RUN"; then
	preferences_ready=yes
fi

mount -o remount,rw "$CONSOLE"
trap 'mount -o remount,ro "$CONSOLE"' EXIT
if [ -f "$src" ] && ! cmp -s "$src" "$dst"; then
	[ ! -f "$dst" ] || cp "$dst" "$dst.anterior"
	cp "$src" "$dst"
fi
if [ "$preferences_ready" = yes ]; then
	python3 "$here/tools/preferences.py" commit "$RUN" "$CONSOLE"
fi
mkdir -p "$CONSOLE/config/diagnostico"
for name in hardware.txt tray-events.log bootanim.log; do
	[ ! -f "$RUN/$name" ] || cp "$RUN/$name" "$CONSOLE/config/diagnostico/$name"
done
journalctl -b -u console.service -u console-bandeja.service -u console-tray-monitor.service \
	-n 200 --no-pager >"$CONSOLE/config/diagnostico/console.log" 2>/dev/null || true
sync
