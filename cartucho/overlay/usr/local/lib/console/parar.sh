#!/bin/sh
# Desliga o emulador de forma limpa. Pela sessao PAM ele roda no escopo de
# sessao do usuario console, fora do cgroup do console.service, entao o
# systemd sozinho so derrubaria o cage e deixaria o emulador segurando o HDD.
pkill -TERM -u console -f '^/opt/|^/var/cache/console/updates/versions/[a-f0-9]+/xemu' || exit 0
i=0
while pgrep -u console -f '^/opt/|^/var/cache/console/updates/versions/[a-f0-9]+/xemu' >/dev/null && [ $i -lt 100 ]; do
	sleep 0.1
	i=$((i + 1))
done
pkill -KILL -u console -f '^/opt/|^/var/cache/console/updates/versions/[a-f0-9]+/xemu' || true
