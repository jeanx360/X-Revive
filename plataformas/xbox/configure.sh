#!/bin/sh
# Gera a configuracao do xemu a partir do perfil de hardware e das portas.
# Recebe do prepare.sh: CONSOLE, RUN, PROFILE, HDD, DVD.
set -eu

fw="$CONSOLE/firmware/xbox"
for f in mcpx_1.0.bin bios.bin; do
	# Como um Xbox sem BIOS: sem os arquivos, o console nao liga.
	[ -f "$fw/$f" ] || { echo "configure: falta firmware/xbox/$f" >&2; exit 1; }
done

get() { sed -n "s/^$1=//p" "$PROFILE"; }

# Disco instalado: dashboard por padrao, manutencao propria por R/Start+Back.
# FATX ausente tambem encaminha a manutencao, sem formatacao automatica.
here=$(dirname "$0")
if [ "${XREVIVE_LIVE:-}" != 1 ]; then
rm -f "$RUN/boot-hexen" "$RUN/boot-ogxbox" "$RUN/installer" "$RUN/update"
echo 'configure: segure R ou Start+Back para manutencao X-Revive (8s)' >&2
selected=$(python3 "$here/tools/held.py" --select --timeout 8) || selected=""
boot_message() {
	# Confirmacao fica no logo antes de o cage assumir o video.
	plymouth display-message --text="$1" 2>/dev/null || true
	printf '%s\n' "$1" >"$RUN/boot-message"
	sleep 2
}
if [ "$selected" = installer ] || [ "${HDD_FATX:-}" != yes ]; then
	printf 'maintenance\n' >"$RUN/installer"
	boot_message 'Iniciando manutencao X-Revive - pode soltar R / Start+Back'
elif [ "$selected" = update ]; then
	touch "$RUN/update"
	boot_message 'Abrindo atualizacoes - pode soltar U / Y'
fi
fi

# RAM do console: 64 (original) ou 128 (upgrade "Ultimate Xbox"). A Cerbios
# suporta 128 MB; jogos/apps com patch de 128 a usam. Padrao 64 (mais compativel).
case "${RAM:-}" in
	128) mem_limit=128 ;;
	*)   mem_limit=64 ;;
esac
echo "configure: RAM=${RAM:-vazio} -> mem_limit=$mem_limit MB" >&2

# A EEPROM importada/persistida conserva a identidade existente. Sem arquivo,
# o próprio Xemu gera no caminho de trabalho; console-eeprom.path a preserva
# imediatamente no SSD. save.sh mantém as mudanças feitas durante a sessão.
if [ -f "$fw/eeprom.bin" ]; then
    install -m 0600 -o console -g console "$fw/eeprom.bin" "$RUN/eeprom.bin"
else
    echo 'configure: EEPROM opcional ausente; Xemu gerara a identidade no primeiro boot' >&2
fi

cat >"$RUN/xemu.toml" <<EOF
[general]
show_welcome = false
skip_boot_anim = false

[general.updates]
check = false

[input]
auto_bind = true
allow_vibration = true

# O interpretador do DSP aborta o xemu em instrucao ilegal (assert fixo no
# codigo); o JIT segue em frente, como o hardware real. Visto com UnleashX.
[audio]
use_dsp_jit = true
volume_limit = 1.0

[net]
enable = true
backend = '${NET_BACKEND:-nat}'

[net.pcap]
netif = '${NET_INTERFACE:-}'

[[net.nat.forward_ports]]
host = 2121
guest = 21
protocol = 'tcp'

[display]
renderer = '$(get renderer)'

[display.quality]
surface_scale = $(get render_scale)

[display.window]
fullscreen_on_startup = true
vsync = true

[display.ui]
show_menubar = false
show_notifications = false
hide_cursor = true

[sys]
mem_limit = '$mem_limit'

[sys.files]
bootrom_path = '$fw/mcpx_1.0.bin'
flashrom_path = '$fw/bios.bin'
eeprom_path = '$RUN/eeprom.bin'
hdd_path = '$HDD'
# dvd_path fica vazio: run.sh passa o disco a cada partida (-dvd_path)
dvd_path = ''
EOF
python3 "$here/tools/preferences.py" restore "$RUN/xemu.toml" "$PROFILE" "$CONSOLE"
chown console:console "$RUN/xemu.toml"
