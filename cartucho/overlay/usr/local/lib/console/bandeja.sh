#!/bin/sh
# Sincroniza a bandeja fisica com o pedido da dashboard/menu. Preserva o
# emulador quando o leitor esta livre; se ocupado, fecha o backend e repete.
RUN=${RUN:-/run/console}
action=${1:-open}
case "$action" in open | close | toggle) ;; *) exit 2 ;; esac
dvd=$(cat "$RUN/dvd" 2>/dev/null || true)
[ -n "$dvd" ] || { echo "bandeja: nenhum leitor configurado; nada a ejetar" >&2; exit 0; }
exec 9>"$RUN/tray.lock"
flock -n 9 || exit 0
# Evita reiniciar o console para um pedido que ja esta satisfeito (inclui
# pedidos de fechar a bandeja feitos pelo BIOS durante a inicializacao).
state=$(python3 - "$dvd" <<'PY'
import fcntl, os, sys
try:
    fd = os.open(sys.argv[1], os.O_RDONLY | os.O_NONBLOCK)
    try: print(fcntl.ioctl(fd, 0x5326, 0))  # CDROM_DRIVE_STATUS, CDS_TRAY_OPEN=2
    finally: os.close(fd)
except OSError:
    print('unknown')
PY
)
case "$action:$state" in
	open:2) : >"$RUN/tray-open"; exit 0 ;;
	close:1 | close:4) rm -f "$RUN/tray-open"; exit 0 ;;
esac
: >"$RUN/ejecting"
restart=no
cleanup() {
	rm -f "$RUN/ejecting"
	[ "$restart" != yes ] || systemctl start console.service
}
trap cleanup EXIT
echo "bandeja: $action solicitado para $dvd (estado=$state)" | tee -a "$RUN/tray-events.log" >&2
case "$action" in
	open) set -- "$dvd" ;;
	close) set -- -t "$dvd" ;;
	toggle) set -- -T "$dvd" ;;
esac
# QMP eject ja soltou o backend: manter o emulador vivo preserva o estado SMC
# para a dashboard conseguir mandar fechar. Botao fisico com backend ocupado
# ainda tem o caminho de recuperacao que destrava parando o emulador.
if ! eject "$@"; then
	restart=yes
	systemctl stop console.service || exit 1
	if ! eject "$@"; then
		echo "bandeja: falha em $action de $dvd" | tee -a "$RUN/tray-events.log" >&2
		exit 1
	fi
fi
sleep 2
case "$action:$state" in
	open:* | toggle:1 | toggle:4 | toggle:unknown) : >"$RUN/tray-open" ;;
	close:* | toggle:2) rm -f "$RUN/tray-open" ;;
esac
rm -f "$RUN/ejecting"
if [ "$action" != open ] && udevadm info -q property -n "$dvd" 2>/dev/null | grep -q '^ID_CDROM_MEDIA=1$'; then
	systemctl --no-block start console-media.service
fi
