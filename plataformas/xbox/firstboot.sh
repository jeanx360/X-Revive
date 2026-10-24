#!/bin/sh
# Auto-instalador do Xbox: disco vazio -> formata e instala a dashboard sozinho;
# disco com dados -> pergunta na tela (teclado Y/N, controle A/B); ja FATX -> nada.
set -eu
[ -n "${HDD_RAW:-}" ] || exit 0
here=$(dirname "$0")
[ -d "$here/firstrun/dash" ] || exit 0
exec python3 "$here/tools/hdd.py" primeiro-boot --perguntar "$HDD_RAW" "$here/firstrun/dash"
