#!/bin/sh
# Primeiro boot: hook opcional da plataforma (ex.: formatar/instalar o HDD).
# Roda numa tty (tela visivel) antes do emulador, para poder perguntar ao
# usuario quando o disco tem dados.
set -eu
LIB=/usr/local/lib/console
[ -x "$LIB/platform/firstboot.sh" ] && exec "$LIB/platform/firstboot.sh"
exit 0
