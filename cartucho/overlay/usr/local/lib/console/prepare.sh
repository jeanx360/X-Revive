#!/bin/sh
# Prepara o console antes do emulador (roda como root, uma vez por boot):
# monta a particao CONSOLE, detecta o hardware, liga as portas fisicas
# (HDD, DVD) ao console virtual e chama a configuracao da plataforma.
set -eu

LIB=/usr/local/lib/console
CONSOLE=/console
RUN=/run/console
export CONSOLE RUN

log() { echo "console-prepare: $*" >&2; }

mkdir -p "$RUN" "$CONSOLE"
chown console:console "$RUN"
if grep -qw 'xrevive.installer=1' /proc/cmdline; then
	python3 "$LIB/installer-prepare.py"
	"$LIB/hal/probe.sh" >"$RUN/profile"
	plymouth display-message --text='Iniciando instalador X-Revive...' 2>/dev/null || true
	exit 0
fi
if ! grep -qw 'xrevive.standalone=1' /proc/cmdline; then
	log 'modo de boot ausente; iniciar pela midia oficial X-Revive'
	exit 1
fi

# Standalone opt-in: manifesto + rodape + geometria devem conferir antes
# de mapear qualquer regiao. Na imagem USB normal nao ha manifesto.
python3 "$LIB/standalone.py" prepare "$RUN"
standalone=no
st_field() { python3 "$LIB/standalone.py" field "$RUN" "$1"; }
if [ -f "$RUN/standalone.json" ]; then standalone=yes; fi
if [ "$standalone" = yes ]; then
	part=$(st_field console_device)
else
	part=$(blkid -L CONSOLE || true)
fi
[ -n "$part" ] || { log "particao CONSOLE nao encontrada"; exit 1; }
mount -o ro,uid=console,gid=console,fmask=0137,dmask=0027 "$part" "$CONSOLE"
if [ "$standalone" = yes ]; then boot_disk=$(st_field boot_device)
else boot_disk=/dev/$(lsblk -no PKNAME "$part"); fi

# Utilitarios grandes ficam fora de FAT32, do squashfs e do toram.
if [ "$standalone" = yes ]; then utils_part=$(st_field utils_device)
else utils_part=$(blkid -L UTILS 2>/dev/null || true); fi
if [ -n "$utils_part" ]; then
	mkdir -p /utils
	mount -o ro,noload,nodev,nosuid,noexec "$utils_part" /utils
fi

# Discos inteiros que nao sao o pendrive de boot (um por dispositivo)
nonboot_disks() {
	seen=" "
	for d in /sys/block/*; do
		dev=/dev/${d##*/}
		[ -b "$dev" ] || continue
		[ "$dev" = "$boot_disk" ] && continue
		case "$seen" in *" $dev "*) continue ;; esac
		seen="$seen$dev "
		[ "$(lsblk -dno TYPE "$dev")" = disk ] || continue
		echo "$dev"
	done
}

# Um HDD de Xbox formatado tem a assinatura "FATX" no inicio das particoes.
# Checa a X (cache, 0x80000) e a C (0x8ca80000) -> reconhece o disco do console.
is_fatx() {
	for skip in 1024 4609024; do
		[ "$(dd if="$1" bs=512 skip="$skip" count=1 2>/dev/null | head -c4)" \
			= FATX ] && return 0
	done
	return 1
}

# Escolhe o HDD sozinho (hdd=auto): plugou, achou, bootou.
#   1) um disco ja formatado FATX (o HDD do console, mesmo com varios discos);
#   2) senao, se houver exatamente um disco nao-pendrive, usa ele (1o boot,
#      disco em branco a formatar).
# Com varios discos nenhum FATX, nao chuta (evita apontar para um disco de dados).
autodetect_hdd() {
	for dev in $(nonboot_disks); do
		is_fatx "$dev" && { echo "$dev"; return 0; }
	done
	set -- $(nonboot_disks)
	[ "$#" -eq 1 ] && echo "$1"
}

# Lista legivel dos discos vistos (diagnostico; o usuario nao precisa editar nada)
list_disks() {
	echo "# Discos vistos no ultimo boot (o HDD e escolhido automaticamente)."
	for dev in $(nonboot_disks); do
		printf '%s\t%s\t%s\t%s\n' "$dev" "$(lsblk -dno SIZE "$dev")" \
			"$(lsblk -dno MODEL "$dev")" \
			"$(is_fatx "$dev" && echo FATX || echo 'nao-formatado')"
	done
}

# Lista legivel dos leitores opticos vistos (diagnostico do DVD)
list_optical() {
	echo "# Leitores opticos vistos no ultimo boot (o DVD e escolhido automaticamente)."
	found=no
	for d in /sys/block/sr*; do
		[ -e "$d" ] || continue
		found=yes
		printf '%s\t%s\n' "/dev/${d##*/}" "$(cat "$d/device/model" 2>/dev/null || echo '?')"
	done
	[ "$found" = yes ] || echo "# nenhum leitor optico (/dev/sr*) detectado neste boot"
}

# Unica janela de escrita na particao CONSOLE (FAT32) durante o boot:
# perfil de hardware desta maquina, lista de discos e ports.conf inicial.
mount -o remount,rw "$CONSOLE"
mkdir -p "$CONSOLE/profiles" "$CONSOLE/config"
"$LIB/hal/probe.sh" "$CONSOLE/profiles" >"$RUN/profile"
list_disks >"$CONSOLE/config/discos-detectados.txt"
list_optical >"$CONSOLE/config/leitores-detectados.txt"
[ -f "$CONSOLE/config/ports.conf" ] || cp "$LIB/ports.conf.default" "$CONSOLE/config/ports.conf"
sync
mount -o remount,ro "$CONSOLE"

# ports.conf e editado pelo usuario em qualquer PC: e lido, nunca executado.
conf() { sed -n "s/^$1=//p" "$CONSOLE/config/ports.conf" | tr -d '\r' | tail -n1; }
hdd_port=$(conf hdd)
dvd_port=$(conf dvd)
ram_opt=$(conf ram)

# Perfil de hardware desta maquina (gerado acima por probe.sh)
prof() { sed -n "s/^$1=//p" "$RUN/profile" | tr -d '\r' | tail -n1; }

# CPU no maximo (desktop/console); o governador vem do perfil
gov=$(prof cpu_governor)
if [ -n "$gov" ]; then
	for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
		[ -w "$g" ] || continue
		avail=$(cat "${g%scaling_governor}scaling_available_governors" 2>/dev/null || echo)
		case " $avail " in *" $gov "*) echo "$gov" >"$g" 2>/dev/null || true ;; esac
	done
fi

# CACHE: particao persistente para cache de shaders e dados do xemu, por
# maquina. Sem ela (pendrive antigo), o xemu usa a RAM e perde o cache no boot.
: >"$RUN/env"
if [ "$standalone" = yes ]; then cache_part=$(st_field cache_device)
else cache_part=$(blkid -L CACHE 2>/dev/null || true); fi
if [ -n "$cache_part" ]; then
	mkdir -p /var/cache/console
	fsck.ext4 -p "$cache_part" >/dev/null 2>&1 || true
	if mount -o rw,noatime "$cache_part" /var/cache/console; then
		xdg="/var/cache/console/$(prof fingerprint)/xdg"
		mkdir -p "$xdg"
		chown -R console:console "/var/cache/console/$(prof fingerprint)"
		echo "XDG_DATA_HOME=$xdg" >>"$RUN/env"
		log "cache persistente em $xdg"
	else
		log "CACHE nao montou; cache de shaders fica so na RAM"
	fi
fi

# Fixar o xemu em nucleos proprios (deixa a CPU 0 para o sistema)
if [ "$(prof cpu_isolate)" = yes ]; then
	last=$(( $(nproc) - 1 ))
	echo "CONSOLE_CPUSET=1-$last" >>"$RUN/env"
fi
chown console:console "$RUN/env"

HDD=""
hdd_dev=""
rules=/run/udev/rules.d/90-console.rules
mkdir -p /run/udev/rules.d
: >"$rules"
# hdd: auto (padrao, acha sozinho), none (sem HDD) ou um nome de porta by-path.
if [ "$standalone" = yes ]; then
	# O sistema instalado sempre usa seu proprio prefixo limitado; uma antiga
	# configuracao by-path jamais pode expor outro disco inteiro ao Xbox.
	hdd_dev=$(st_field xbox_device)
else
case "$hdd_port" in
	none) ;;
	"" | auto)
		if [ "$standalone" = yes ]; then hdd_dev=$(st_field xbox_device)
		else hdd_dev=$(autodetect_hdd); fi
		[ -n "$hdd_dev" ] && log "HDD detectado: $hdd_dev ($(lsblk -dno SIZE "$hdd_dev"))" \
			|| log "nenhum HDD detectado (ligue um disco ou veja discos-detectados.txt)"
		;;
	*)
		if [ -e "/dev/disk/by-path/$hdd_port" ]; then
			hdd_dev=$(readlink -f "/dev/disk/by-path/$hdd_port")
		else
			log "nenhum disco na porta $hdd_port (console sem HDD)"
		fi
		;;
esac
fi
if [ "$standalone" = no ] && [ -n "$hdd_dev" ] && \
   python3 "$LIB/standalone.py" is-container "$hdd_dev"; then
	log 'SSD standalone reconhecido: recusando acesso bruto pelo USB; iniciar pela propria UEFI'
	log 'recuperacao/instalador standalone via USB ainda em desenvolvimento'
	hdd_dev=""
fi
if [ -n "$hdd_dev" ] && [ "$hdd_dev" != "$boot_disk" ]; then
	# A regra usa o nome do kernel resolvido neste boot
	echo "SUBSYSTEM==\"block\", KERNEL==\"${hdd_dev#/dev/}\", GROUP=\"console\", MODE=\"0660\", SYMLINK+=\"console-hdd\"" >>"$rules"
	HDD=/dev/console-hdd
	echo "HDD_RAW=$hdd_dev" >>"$RUN/env"   # disco real (diagnostico / uso manual pelo PC)
elif [ "$hdd_dev" = "$boot_disk" ]; then
	log "disco escolhido e o proprio pendrive; HDD ignorado"
fi

# Sem FATX, configure.sh abre a manutenção própria. Nunca formata no boot.
HDD_FATX=""
if [ -n "$hdd_dev" ] && [ "$hdd_dev" != "$boot_disk" ]; then
	if is_fatx "$hdd_dev"; then HDD_FATX=yes; else HDD_FATX=no; fi
	[ "$HDD_FATX" = yes ] && log "HDD e FATX (disco de Xbox): boota a dashboard" \
		|| log "HDD sem FATX: abre manutencao X-Revive"
fi

DVD=""
case "$dvd_port" in
	none) ;;
	"" | auto)
		for sr in /dev/sr*; do [ -b "$sr" ] && DVD=$sr && break; done
		[ -n "$DVD" ] \
			&& log "leitor DVD: $DVD ($(cat "/sys/block/${DVD#/dev/}/device/model" 2>/dev/null || echo '?'))" \
			|| log "nenhum leitor DVD (/dev/sr*); veja config/leitores-detectados.txt"
		;;
	*)
		if [ -e "/dev/disk/by-path/$dvd_port" ]; then
			dvd_dev=$(readlink -f "/dev/disk/by-path/$dvd_port")
			echo "SUBSYSTEM==\"block\", KERNEL==\"${dvd_dev#/dev/}\", GROUP=\"console\", MODE=\"0660\", SYMLINK+=\"console-dvd\"" >>"$rules"
			DVD=/dev/console-dvd
		fi
		;;
esac

if [ -n "$DVD" ]; then
	# Disco colocado ou retirado: o console religa, como o Xbox que da boot no
	# jogo ao fechar a bandeja e volta a dashboard quando o disco sai
	dvd_dev=$(readlink -f "$DVD")
	# Sem udisks ninguem consulta a bandeja: o kernel passa a verificar sozinho
	echo 2000 >"/sys/block/${dvd_dev#/dev/}/events_poll_msecs" || log "leitor sem eventos de midia"
	echo "ACTION==\"change\", SUBSYSTEM==\"block\", KERNEL==\"${dvd_dev#/dev/}\", ENV{DISK_MEDIA_CHANGE}==\"1\", RUN+=\"/usr/bin/systemctl --no-block start console-media.service\"" >>"$rules"
	# Botao Eject do leitor: com o xemu usando o leitor o kernel trava a
	# bandeja, entao quem abre e o bandeja.sh
	echo "ACTION==\"change\", SUBSYSTEM==\"block\", KERNEL==\"${dvd_dev#/dev/}\", ENV{DISK_EJECT_REQUEST}==\"1\", RUN+=\"/usr/bin/systemctl --no-block start console-bandeja.service\"" >>"$rules"
fi
echo "$DVD" >"$RUN/dvd"

udevadm control --reload
udevadm trigger --action=change --subsystem-match=block
udevadm settle
python3 "$LIB/hardware.py" "$RUN" "$CONSOLE/config/ports.conf"
. "$RUN/hardware.env"
cat "$RUN/hardware.env" >>"$RUN/env"
export NET_BACKEND NET_INTERFACE
export HDD DVD PROFILE="$RUN/profile" RAM="$ram_opt" HDD_RAW="$hdd_dev" HDD_FATX

# Somente arquivos Xbox da animacao, antes de o emulador abrir o HDD.
# Nao formata, nao instala dashboard, nao altera BIOS nem outros discos.
if [ "$HDD_FATX" = yes ]; then
	[ ! -f "$LIB/platform/firstrun/bootanims/Xbox/BootAnim.xbe" ] || python3 "$LIB/platform/tools/bootanim.py" "$hdd_dev" \
		"$CONSOLE/firmware/xbox/bios.bin" "$LIB/platform/firstrun/bootanims/Xbox" \
		>"$RUN/bootanim.log" 2>&1 || log 'animacao nao instalada; veja bootanim.log'
fi

python3 "$LIB/update-service.py" prepare
"$LIB/platform/configure.sh"
