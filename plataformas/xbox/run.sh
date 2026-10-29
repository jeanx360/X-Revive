#!/bin/sh
# Executado pelo cage como usuario console. Religado a cada troca de disco.
# Recebe do ambiente (console-prepare -> /run/console/env):
#   XDG_DATA_HOME  cache de shaders persistente desta maquina
#   CONSOLE_CPUSET nucleos reservados para o emulador
RUN=${RUN:-/run/console}
CONSOLE=${CONSOLE:-/console}
dvd=$(cat "$RUN/dvd" 2>/dev/null || true)
disc=""
# Leitor fisico pelo driver host_device do QEMU: o host_cdrom trava o xemu na
# leitura. Sem disco na bandeja, o console liga com o leitor vazio.
if [ -f "$RUN/live-disc" ]; then
	disc=$(cat "$RUN/live-disc")
elif [ -f "$RUN/boot-ogxbox" ] && [ -f "${UTILS:-/utils}/ogxbox.iso" ]; then
	disc="${UTILS:-/utils}/ogxbox.iso"
elif [ -f "$RUN/boot-hexen" ] && [ -f "$CONSOLE/utils/hexen.iso" ]; then
	# Recuperacao ganha do DVD fisico e permanece nos restarts desta sessao.
	disc="$CONSOLE/utils/hexen.iso"
elif [ -n "$dvd" ] && udevadm info -q property -n "$dvd" 2>/dev/null | grep -q '^ID_CDROM_MEDIA=1$'; then
	disc="host_device:$dvd"
fi

echo "console: DVD=$disc audio=${AUDIODEV:-default}" >&2
export SDL_AUDIODRIVER=alsa
export SDL_AUDIO_DRIVER=alsa
if [ -n "${AUDIODEV:-}" ]; then
	export SDL_AUDIO_ALSA_DEFAULT_PLAYBACK_DEVICE="$AUDIODEV"
fi
app=$(cat /run/xrevive-update/app 2>/dev/null || echo /opt/xemu/AppRun)
set -- "${XEMU_APP:-$app}" -config_path "$RUN/xemu.toml" -full-screen -dvd_path "$disc" \
	-qmp "unix:$RUN/xemu.qmp,server=on,wait=off"
# Fixa o emulador nos nucleos reservados, longe do sistema (CPU 0)
[ -n "${CONSOLE_CPUSET:-}" ] && set -- taskset -c "$CONSOLE_CPUSET" "$@"

# Wayland direto (sem XWayland) quando o compositor e as libs estao presentes.
# Se o xemu sair em menos de 5 s, foi falha de init: cai para X11 nesta partida.
if [ -z "${SDL_VIDEODRIVER:-}" ] && [ -n "${WAYLAND_DISPLAY:-}" ] \
   && ldconfig -p 2>/dev/null | grep -q 'libwayland-egl\.so'; then
	start=$(date +%s)
	SDL_VIDEODRIVER=wayland "$@" && exit 0
	[ $(( $(date +%s) - start )) -lt 5 ] && exec env SDL_VIDEODRIVER=x11 "$@"
	exit 1
fi
exec "$@"
