#!/bin/sh
# Detecta o hardware e imprime um perfil (formato chave=valor).
# Uso: probe.sh [diretorio-de-perfis]
# Se o diretorio tiver um perfil para esta maquina, ele e usado; senao, um novo
# e calculado (e gravado, se o diretorio for gravavel).

PROFILES_DIR="${1:-}"

cpu_model=$(sed -n 's/^model name[[:space:]]*: //p' /proc/cpuinfo | head -n1)
cpu_threads=$(grep -c '^processor' /proc/cpuinfo)
cpu_max_mhz=$(( $(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq 2>/dev/null || echo 0) / 1000 ))
mem_mb=$(( $(sed -n 's/^MemTotal:[[:space:]]*\([0-9]*\).*/\1/p' /proc/meminfo) / 1024 ))
board="$(cat /sys/class/dmi/id/board_vendor 2>/dev/null) $(cat /sys/class/dmi/id/board_name 2>/dev/null)"

# Tipo de chassi (SMBIOS): 8-14,30-32 = portatil. Num notebook, o governador
# agressivo esquenta demais; num desktop/console, CPU no maximo ajuda o xemu.
chassis=$(cat /sys/class/dmi/id/chassis_type 2>/dev/null || echo 0)
case "$chassis" in
	8 | 9 | 10 | 11 | 14 | 30 | 31 | 32) laptop=yes ;;
	*) laptop=no ;;
esac

# Primeira GPU de exibicao (classe PCI 0x03xxxx)
gpu_vendor=unknown
gpu_pci=""
gpu_driver=unknown
variant=$(cat /etc/console-variant 2>/dev/null || echo universal)
for dev in /sys/bus/pci/devices/*; do
	case "$(cat "$dev/class")" in 0x03*) ;; *) continue ;; esac
	gpu_pci="$(cat "$dev/vendor"):$(cat "$dev/device")"
	gpu_driver=$(basename "$(readlink -f "$dev/driver")")
	case "$(cat "$dev/vendor")" in
		0x1002) gpu_vendor=amd ;;
		0x8086) gpu_vendor=intel ;;
		0x10de) gpu_vendor=nvidia ;;
		0x1af4) gpu_vendor=virtio ;;
	esac
	break
done

vulkan=no
if command -v vulkaninfo >/dev/null 2>&1; then
	# So conta GPU real; o lavapipe (Vulkan na CPU) aparece como DEVICE_TYPE_CPU
	if timeout 5s vulkaninfo --summary 2>/dev/null | grep -qE 'deviceType *= *PHYSICAL_DEVICE_TYPE_(INTEGRATED|DISCRETE|VIRTUAL)_GPU'; then
		vulkan=yes
	fi
else
	# Sem vulkaninfo: aceita a presenca de um ICD do fabricante da GPU
	case "$gpu_vendor" in
		amd) icd=radeon ;;
		*) icd=$gpu_vendor ;;
	esac
	for f in /usr/share/vulkan/icd.d/"$icd"*.json /etc/vulkan/icd.d/"$icd"*.json; do
		[ -f "$f" ] && vulkan=yes && break
	done
fi

fingerprint=$(printf '%s|%s|%s|%s' "$board" "$gpu_pci" "$gpu_driver" "$variant" | sha1sum | cut -c1-12)

if [ -n "$PROFILES_DIR" ] && [ -f "$PROFILES_DIR/$fingerprint.conf" ]; then
	cat "$PROFILES_DIR/$fingerprint.conf"
	exit 0
fi

# Nivel inicial por heuristica; refinado depois pela bancada (VALIDACOES.md V5).
# Clock maximo por nucleo e o melhor indicador simples para o xemu.
tier=C
if [ "$cpu_threads" -ge 4 ] && [ "$cpu_max_mhz" -ge 3000 ] && [ "$vulkan" = yes ]; then
	tier=B
	if [ "$cpu_max_mhz" -ge 4000 ] && [ "$gpu_vendor" != intel ] && [ "$mem_mb" -ge 7500 ]; then
		tier=A
	fi
fi

case "$tier" in
	A) scale=3 ;;
	B) scale=2 ;;
	*) scale=1 ;;
esac
renderer=OPENGL
[ "$vulkan" = yes ] && renderer=VULKAN
# GTX 750: comecar em OpenGL nativo e escala 1; Vulkan pode ser testado depois.
if [ "$gpu_vendor" = nvidia ] && [ "$gpu_driver" = nvidia ]; then
	renderer=OPENGL
	scale=1
fi

# CPU no maximo no desktop/console; no notebook, deixa o kernel decidir (calor).
cpu_governor=performance
[ "$laptop" = yes ] && cpu_governor=schedutil
# Fixar o xemu em nucleos proprios so compensa com folga de nucleos.
cpu_isolate=no
[ "$cpu_threads" -ge 6 ] && cpu_isolate=yes

profile="fingerprint=$fingerprint
board=$board
cpu_model=$cpu_model
cpu_threads=$cpu_threads
cpu_max_mhz=$cpu_max_mhz
mem_mb=$mem_mb
gpu_vendor=$gpu_vendor
gpu_driver=$gpu_driver
image_variant=$variant
gpu_pci=$gpu_pci
vulkan=$vulkan
laptop=$laptop
tier=$tier
renderer=$renderer
render_scale=$scale
cpu_governor=$cpu_governor
cpu_isolate=$cpu_isolate"

printf '%s\n' "$profile"
if [ -n "$PROFILES_DIR" ] && [ -w "$PROFILES_DIR" ]; then
	printf '%s\n' "$profile" >"$PROFILES_DIR/$fingerprint.conf"
fi
