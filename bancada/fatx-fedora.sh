#!/bin/sh
# Acesso FATX (disco de Xbox) a partir do Fedora de bancada/dev.
# Monta o disco de Xbox no gerenciador de arquivos para copiar games, e ajuda a
# verificar se o HeXEn formatou mesmo o disco.
#
#   sudo bancada/fatx-fedora.sh verificar  /dev/sdX          (SO LEITURA)
#   sudo bancada/fatx-fedora.sh build                        (compila o fatxfs 1x)
#   sudo bancada/fatx-fedora.sh montar     /dev/sdX f ~/xbox-games
#   sudo bancada/fatx-fedora.sh desmontar  ~/xbox-games
#   sudo bancada/fatx-fedora.sh forcar-hexen /dev/sdX        (APAGA so a assinatura
#                 FATX -> no proximo boot o console abre o HeXEn pra reformatar)
#   sudo bancada/fatx-fedora.sh instalar-dash /dev/sdX       (poe a UnleashX embutida
#                 como C:\evoxdash.xbe = boot custom; mantem xboxdash.xbe da MS)
#
# Letras de drive: c (sistema/dashboard), e (dados), f e g (games/homebrew),
# x y z (cache). Games normalmente em f (F:\Games) ou e (E:\Games).
set -eu

# Home do usuario REAL (sob sudo, $HOME vira /root; usamos o do usuario que chamou)
REAL_USER="${SUDO_USER:-$(id -un)}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
SRC="${FATX_SRC:-${REAL_HOME:-$HOME}/fatx}"   # fonte do projeto mborgerson/fatx
FATXFS="$SRC/fatxfs/build/fatxfs"

need_root() { [ "$(id -u)" = 0 ] || { echo "rode com sudo" >&2; exit 1; }; }

# Assinatura FATX nas partricoes X (cache, 0x80000) e C (sistema, 0x8CA80000).
# So LEITURA. Diz se o disco e um disco de Xbox formatado.
cmd_verificar() {
	dev=${1:?uso: verificar /dev/sdX}
	[ -b "$dev" ] || { echo "$dev nao e um dispositivo de bloco" >&2; exit 1; }
	echo "Lendo $dev (somente leitura)..."
	python3 - "$dev" <<'PY'
import sys
dev=sys.argv[1]
parts={'X (cache)':0x80000,'C (sistema)':0x8ca80000,'E (dados)':0xabe80000}
with open(dev,'rb') as f:
    f.seek(0x1be); mbr=f.read(64); sig=f.read(2)
    ptype = mbr[4] if sig==b'\x55\xaa' else None
    found=False
    for name,off in parts.items():
        f.seek(off); magic=f.read(4)
        ok = magic==b'FATX'
        found = found or ok
        print(f"  {name:12} @ {off:#x}: {'FATX ✔' if ok else repr(magic)+' (sem FATX)'}")
print()
if found:
    print("=> E UM DISCO DE XBOX (FATX presente). O HeXEn formatou.")
    if ptype is not None:
        print(f"   (Ainda ha uma tabela de particao de PC no setor 0, tipo {ptype:#x};")
        print("    e so o rotulo velho - o Linux mostra 'NTFS/Documentos' por causa dela,")
        print("    mas o Xbox usa os offsets fixos acima, nao essa tabela.)")
else:
    print("=> NAO achei FATX. Ou o disco nao foi formatado pelo HeXEn, ou foi em")
    print("   outro layout. (Nao escrevi nada; e so leitura.)")
PY
}

cmd_build() {
	need_root
	echo "== instalando dependencias (dnf) =="
	dnf install -y fuse-devel cmake gcc git make pkgconf-pkg-config >/dev/null
	if [ ! -d "$SRC/.git" ]; then
		echo "== baixando fonte em $SRC (como $REAL_USER) =="
		rm -rf "$SRC"
		sudo -u "$REAL_USER" git clone --depth 1 https://github.com/mborgerson/fatx "$SRC"
	fi
	echo "== compilando libfatx =="
	( cd "$SRC/libfatx" && mkdir -p build && cd build && cmake .. >/dev/null && make >/dev/null && make install >/dev/null )
	ldconfig
	echo "== compilando fatxfs =="
	( cd "$SRC/fatxfs" && mkdir -p build && cd build && cmake .. >/dev/null && make >/dev/null )
	[ -x "$FATXFS" ] && echo "pronto: $FATXFS" || { echo "falha ao compilar fatxfs" >&2; exit 1; }
}

cmd_montar() {
	need_root
	dev=${1:?uso: montar /dev/sdX <drive c|e|f|g|x|y|z> <ponto>}
	drive=${2:?falta a letra do drive}
	ponto=${3:?falta o ponto de montagem}
	[ -x "$FATXFS" ] || { echo "fatxfs nao compilado; rode: sudo $0 build" >&2; exit 1; }
	[ -b "$dev" ] || { echo "$dev nao e dispositivo de bloco" >&2; exit 1; }
	mkdir -p "$ponto"
	# allow_other: o seu usuario (nao-root) consegue abrir no gerenciador de arquivos
	"$FATXFS" "$dev" "$ponto" --drive="$drive" -o allow_other
	echo "montado drive $drive de $dev em $ponto"
	echo "copie os games para la (ex.: $ponto/Games). Desmonte com: sudo $0 desmontar $ponto"
}

cmd_desmontar() {
	ponto=${1:?uso: desmontar <ponto>}
	fusermount -u "$ponto" 2>/dev/null || umount "$ponto"
	echo "desmontado $ponto"
}

# Apaga SO as assinaturas FATX (superblocos) das particoes retail. O disco deixa
# de ser reconhecido como FATX -> no proximo boot o console abre o HeXEn para
# reformatar. Util para "voltar ao HeXEn" num disco que ja tem FATX.
cmd_forcar_hexen() {
	need_root
	dev=${1:?uso: forcar-hexen /dev/sdX}
	[ -b "$dev" ] || { echo "$dev nao e dispositivo de bloco" >&2; exit 1; }
	gib=$(( $(blockdev --getsize64 "$dev") / 1073741824 ))
	model=$(cat "/sys/block/$(basename "$dev")/device/model" 2>/dev/null || echo '?')
	echo
	echo "!! Isto vai INVALIDAR o FATX de $dev ($model, ${gib} GiB) !!"
	echo "   O conteudo FATX fica inacessivel (voce vai reformatar no HeXEn)."
	printf "   Digite o tamanho em GiB (%s) para confirmar: " "$gib"
	read ans
	[ "$ans" = "$gib" ] || { echo "cancelado"; exit 1; }
	# Zera 4 KiB no inicio de cada particao (apaga o magic FATX). Offsets reais
	# do libfatx: x y z c e + f(estendida). Basta x e c para o console ver "sem
	# FATX", mas zeramos todas para invalidar de vez.
	for off in 0x80000 0x2ee80000 0x5dc80000 0x8ca80000 0xabe80000 0x1dd156000; do
		dd if=/dev/zero of="$dev" bs=4096 count=1 seek=$(( off / 4096 )) conv=notrunc status=none
	done
	sync
	echo "pronto: assinaturas FATX apagadas. No proximo boot do console -> HeXEn."
}

# Instala a UnleashX embutida do projeto como C:\evoxdash.xbe (a dashboard custom
# que a Cerbios boota), mantendo xboxdash.xbe (MS retail) como alternativa.
cmd_instalar_dash() {
	need_root
	dev=${1:?uso: instalar-dash /dev/sdX}
	[ -b "$dev" ] || { echo "$dev nao e dispositivo de bloco" >&2; exit 1; }
	[ -x "$FATXFS" ] || { echo "fatxfs nao compilado; rode: sudo $0 build" >&2; exit 1; }
	DASH=$(cd "$(dirname "$0")/../plataformas/xbox/firstrun/dash" 2>/dev/null && pwd || true)
	[ -n "$DASH" ] && [ -f "$DASH/default.xbe" ] || { echo "dash embutida nao encontrada em plataformas/xbox/firstrun/dash" >&2; exit 1; }
	pt=$(mktemp -d)
	"$FATXFS" "$dev" "$pt" --drive=c -o allow_other
	echo "instalando UnleashX em C:\\evoxdash.xbe (xboxdash.xbe da MS fica como alternativa)..."
	for f in Config.xml English.xml; do [ -f "$DASH/$f" ] && cp -f "$DASH/$f" "$pt/"; done
	[ -d "$DASH/Skins" ] && cp -rf "$DASH/Skins" "$pt/" 2>/dev/null || true
	cp -f "$DASH/default.xbe" "$pt/evoxdash.xbe"
	sync
	ok=$(python3 - "$pt/evoxdash.xbe" <<'PY'
import sys,struct
d=open(sys.argv[1],'rb').read(0x2000)
base=struct.unpack('<I',d[0x104:0x108])[0]; cert=struct.unpack('<I',d[0x118:0x11c])[0]-base
print(d[cert+0xc:cert+0xc+80].decode('utf-16-le','ignore').split(chr(0))[0])
PY
)
	fusermount -u "$pt" 2>/dev/null || umount "$pt"; rmdir "$pt" 2>/dev/null || true
	echo "evoxdash.xbe agora = '$ok'"
	[ "$ok" = "UnleashX" ] \
		&& echo "OK: a Cerbios vai bootar a UnleashX. xboxdash.xbe (MS) continua como alternativa." \
		|| echo "ATENCAO: verificacao do titulo falhou; confira."
}

cmd=${1:-}; shift 2>/dev/null || true
case "$cmd" in
	verificar)     cmd_verificar "$@" ;;
	build)         cmd_build "$@" ;;
	montar)        cmd_montar "$@" ;;
	desmontar)     cmd_desmontar "$@" ;;
	forcar-hexen)  cmd_forcar_hexen "$@" ;;
	instalar-dash) cmd_instalar_dash "$@" ;;
	*) sed -n '2,22p' "$0"; exit 1 ;;
esac
