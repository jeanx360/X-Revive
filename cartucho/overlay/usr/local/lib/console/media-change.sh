#!/bin/sh
# Eventos udev podem chegar depois de o movimento da bandeja terminar.
RUN=${RUN:-/run/console}
echo 'media-change' >>"$RUN/tray-events.log"
for flag in ejecting boot-hexen boot-ogxbox; do
	[ ! -e "$RUN/$flag" ] || exit 0
done
dvd=$(cat "$RUN/dvd" 2>/dev/null || true)
[ -n "$dvd" ] || exit 0
if [ -e "$RUN/tray-open" ] && ! udevadm info -q property -n "$dvd" 2>/dev/null | grep -q '^ID_CDROM_MEDIA=1$'; then
	# Ejeicao nossa ja soltou o backend. Reiniciar agora perderia o estado
	# SMC aberto e impediria o proximo pedido de fechar pela dashboard.
	echo 'media-change: bandeja aberta sem midia; estado preservado' >>"$RUN/tray-events.log"
	exit 0
fi
rm -f "$RUN/tray-open"
systemctl --no-block restart console.service
