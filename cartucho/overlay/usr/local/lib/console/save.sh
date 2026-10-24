#!/bin/sh
# Desligamento: deixa a plataforma salvar o que mudou (ex.: EEPROM do Xbox).
CONSOLE=/console RUN=/run/console
export CONSOLE RUN
[ -f "$RUN/eeprom.bin" ] && [ -x /usr/local/lib/console/platform/save.sh ] && /usr/local/lib/console/platform/save.sh
python3 /usr/local/lib/console/standalone.py finalize "$RUN" || \
	echo 'standalone: boot nao reparado; usar pendrive de recuperacao' >&2
exit 0
