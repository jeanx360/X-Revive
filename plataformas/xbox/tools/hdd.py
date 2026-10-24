#!/usr/bin/env python3
"""Prepara o HDD do Xbox (imagem de disco) a partir do PC.

  hdd.py formatar <imagem>
      Layout retail (X Y Z C E) + F com o resto do disco, clusters de 16 KB.

  hdd.py instalar-smt <imagem> <repo-softmodding-tool> [--dash NOME]
      Instalacao "Hardmod" do Xbox Softmodding Tool (Rocky5), a mesma que o
      Extras Disc faz em consoles com BIOS modificada (Cerbios):
        C:\\evoxdash.xbe + Dashloader.ini   (caminho de dash padrao da Cerbios)
        C:\\Dashboard\\                       (dashboard, padrao UnleashX)
        E:\\Applications\\                    (ferramentas do Extras Disc)
        E:\\UDATA E:\\TDATA E:\\CACHE E:\\Backups F:\\Games

  hdd.py instalar-cerbios <imagem> <pacote-da-cerbios>
      Do pacote de release da Cerbios (pasta extraida do zip):
        BootAnims\\  -> E:\\Cerbios\\BootAnims\\   (animacao de boot; e o caminho
                                                gravado no Cerbios.bin)
        cerbios.ini -> C:\\cerbios.ini            (se existir no pacote)

  hdd.py listar <imagem> [--drive c|e|f]

Por padrao so aceita ARQUIVO (imagem). Para gravar num disco real da bancada,
passe --disco /dev/sdX: ele pede confirmacao e apaga o disco inteiro. Nunca use
no disco de sistema.
Requer pyfatx (pip install pyfatx).
"""
import argparse
import glob
import os
import select
import stat
import struct
import sys
import time
import zipfile

from pyfatx import Fatx
from pyfatx.libfatx import lib

F_OFFSET = 0x1DD156000
FATX_NAME_MAX = 41  # FATX aceita 42, a libfatx so ate 41
RETAIL_CLUSTER_SECTORS = 32  # 16 KB, exigido pelo XAPI nas particoes retail
FORMAT_F_TAKES_ALL = 2  # enum fatx_format da libfatx

APPS = [
    "DVD2Xbox",
    "XBpartitioner",
    "XBPTableWriter",
    "ConfigMagic v1.6.1",
    "EEPROM Backuperer",
    "Chimp261812",
    "Enigmah-X",
]
# Xored Mini fica de fora: 882 trainers numa pasta, e a libfatx falha ao
# crescer um diretorio alem de 512 entradas. Instale pelo Extras Disc ou FTP.


def image_path(path, allow_disk=False, confirm=True):
    st = os.stat(path)
    if stat.S_ISREG(st.st_mode):
        return path, st.st_size
    if stat.S_ISBLK(st.st_mode):
        if not allow_disk:
            sys.exit(f"{path}: e um disco fisico; para gravar nele use --disco")
        size = _blockdev_size(path)
        if confirm:
            _confirm_disk(path, size)
        return path, size
    sys.exit(f"{path}: nao e arquivo comum nem disco de bloco")


def dev_is_fatx(path, size):
    """True se o disco ja tem a assinatura FATX (HDD de Xbox formatado)."""
    with open(path, "rb") as f:
        for off in (0x80000, 0x8CA80000):  # particao X (cache) e C (sistema)
            if off + 4 <= size:
                f.seek(off)
                if f.read(4) == b"FATX":
                    return True
    return False


def dev_is_blank(path, size):
    """True so se o disco esta comprovadamente vazio: sem tabela de particao
    (MBR/GPT) e com o primeiro setor e a area FATX zerados (00 ou FF). Qualquer
    sinal de dado -> False, para nunca apagar disco do usuario por engano."""
    with open(path, "rb") as f:
        def rd(o, n):
            f.seek(o)
            return f.read(n)
        if rd(510, 2) == b"\x55\xaa":       # assinatura de MBR
            return False
        if rd(512, 8) == b"EFI PART":        # cabecalho GPT
            return False
        for off in (0, 0x80000):
            if off + 512 <= size:
                b = rd(off, 512)
                if b.count(b[:1]) != 512 or b[0] not in (0x00, 0xFF):
                    return False
    return True


def _blockdev_size(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)


def _confirm_disk(path, size):
    name = os.path.basename(os.path.realpath(path))
    # Recusa se o disco (ou uma particao dele) estiver montado
    with open("/proc/mounts") as f:
        mounts = f.read()
    if f"/dev/{name}" in mounts:
        sys.exit(f"{path}: ha particao montada; desmonte antes")
    model = ""
    for p in (f"/sys/block/{name}/device/model",):
        try:
            model = open(p).read().strip()
        except OSError:
            pass
    gib = size / 2**30
    sys.stderr.write(
        f"\n!! VAI APAGAR O DISCO INTEIRO !!\n"
        f"  dispositivo: {path}\n"
        f"  modelo:      {model or '?'}\n"
        f"  tamanho:     {gib:.1f} GiB\n"
        f"Digite o tamanho em GiB arredondado ({round(gib)}) para confirmar: ")
    sys.stderr.flush()
    try:
        ans = input().strip()
    except EOFError:
        ans = ""
    if ans != str(round(gib)):
        sys.exit("cancelado")


def open_drive(path, size, drive):
    if drive == "f":
        return Fatx(path, offset=F_OFFSET, size=size - F_OFFSET)
    return Fatx(path, drive=drive)


def exists(fs, path):
    try:
        fs.get_attr(path)
        return True
    except AssertionError:
        return False


def makedirs(fs, path):
    cur = ""
    for part in filter(None, path.split("/")):
        cur += "/" + part
        if not exists(fs, cur):
            fs.mkdir(cur)


def put(fs, path, data):
    name = path.rsplit("/", 1)[-1]
    if len(name) > FATX_NAME_MAX:
        print(f"  ignorado (nome > {FATX_NAME_MAX} caracteres): {path}")
        return
    makedirs(fs, path.rsplit("/", 1)[0])
    if exists(fs, path):
        fs.unlink(path)
    fs.write(path, data)
    if bytes(fs.read(path)) != data:
        sys.exit(f"verificacao falhou: {path}")


def unzip_into(fs, zpath, dest):
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/").rstrip("/")
            if not name or ".." in name.split("/"):
                continue
            target = f"{dest}/{name}"
            if info.is_dir():
                makedirs(fs, target)
            else:
                put(fs, target, z.read(info))


def cmd_format(args):
    path, size = image_path(args.image, getattr(args, 'disco', False))
    if size <= F_OFFSET:
        sys.exit("imagem menor que 8 GB: o Xbox exige no minimo 8 GB")
    fs = lib.pyfatx_open_helper()
    # retail com 16 KB + F com o restante
    if lib.fatx_disk_format(fs, path.encode(), 512, FORMAT_F_TAKES_ALL,
                            RETAIL_CLUSTER_SECTORS) != 0:
        sys.exit("falha ao formatar")
    print(f"formatado: X Y Z C E + F ({(size - F_OFFSET) // 2**20} MiB)")


def cmd_install(args):
    path, size = image_path(args.image, getattr(args, 'disco', False))
    smt = args.smt
    disc = os.path.join(smt, "Extras Disc")
    dashloader = os.path.join(disc, "Hardmod", "dashloader")
    dash_zip = os.path.join(disc, "Softmod", "dashboards", f"{args.dash}.zip")
    for p in (dashloader, dash_zip):
        if not os.path.exists(p):
            sys.exit(f"nao encontrado no Softmodding Tool: {p}")

    c = open_drive(path, size, "c")
    print("C:\\ dashloader")
    for name in sorted(os.listdir(dashloader)):
        with open(os.path.join(dashloader, name), "rb") as f:
            put(c, f"/{name}", f.read())
    print(f"C:\\Dashboard\\ <- {args.dash}")
    unzip_into(c, dash_zip, "/Dashboard")
    del c

    e = open_drive(path, size, "e")
    for d in ("UDATA", "TDATA", "CACHE", "Backups", "Applications"):
        makedirs(e, f"/{d}")
    for app in APPS:
        z = os.path.join(disc, "Softmod", "applications", f"{app}.zip")
        if os.path.exists(z):
            print(f"E:\\Applications\\{app}\\")
            unzip_into(e, z, f"/Applications/{app}")
    del e

    f = open_drive(path, size, "f")
    makedirs(f, "/Games")
    del f
    print("pronto")


def copy_tree(fs, src, dest):
    for dirpath, _, files in os.walk(src):
        rel = os.path.relpath(dirpath, src).replace(os.sep, "/")
        base = dest if rel == "." else f"{dest}/{rel}"
        makedirs(fs, base)
        for name in sorted(files):
            if name.lower() == "thumbs.db":
                continue
            with open(os.path.join(dirpath, name), "rb") as f:
                put(fs, f"{base}/{name}", f.read())


def find(top, name, want_dir):
    for dirpath, dirs, files in os.walk(top):
        for n in (dirs if want_dir else files):
            if n.lower() == name.lower():
                return os.path.join(dirpath, n)
    return None


def cmd_cerbios(args):
    path, size = image_path(args.image, getattr(args, 'disco', False))
    anims = find(args.package, "BootAnims", True)
    ini = find(args.package, "cerbios.ini", False)
    if not anims and not ini:
        sys.exit(f"{args.package}: nem BootAnims nem cerbios.ini encontrados")
    if anims:
        print(f"E:\\Cerbios\\BootAnims\\ <- {anims}")
        e = open_drive(path, size, "e")
        copy_tree(e, anims, "/Cerbios/BootAnims")
        del e
    if ini:
        print(f"C:\\cerbios.ini <- {ini}")
        c = open_drive(path, size, "c")
        with open(ini, "rb") as f:
            put(c, "/cerbios.ini", f.read())
        del c
    print("pronto")


def ask_confirm(prompt, timeout=120):
    """Pergunta sim/nao na tela. Aceita teclado (Y/N) OU controle Xbox
    (A=sim, B=nao), o que vier primeiro. Sem resposta no tempo -> nao."""
    import termios
    import tty
    # Se houver splash de boot cobrindo a tela, esconde para a pergunta aparecer
    try:
        import subprocess
        subprocess.run(["plymouth", "hide-splash"], timeout=3, check=False)
    except Exception:
        pass
    print(prompt, flush=True)
    kb = sys.stdin.fileno()
    old = None
    if sys.stdin.isatty():
        try:
            old = termios.tcgetattr(kb)
            tty.setcbreak(kb)
        except Exception:
            old = None
    ev = {}
    for p in glob.glob("/dev/input/event*"):
        try:
            ev[os.open(p, os.O_RDONLY | os.O_NONBLOCK)] = p
        except OSError:
            pass
    esz = struct.calcsize("llHHi")  # struct input_event (nativo)
    try:
        watch = ([kb] if old is not None else []) + list(ev)
        if not watch:
            return False
        end = time.time() + timeout
        while True:
            r, _, _ = select.select(watch, [], [], max(0.0, end - time.time()))
            if not r:
                return False
            for fd in r:
                if fd == kb:
                    c = os.read(kb, 1).decode("latin-1", "ignore").lower()
                    if c == "y":
                        return True
                    if c == "n":
                        return False
                else:
                    data = os.read(fd, esz * 16)
                    for i in range(0, len(data) - esz + 1, esz):
                        _, _, typ, code, val = struct.unpack("llHHi", data[i:i + esz])
                        if typ == 1 and val == 1:    # EV_KEY, tecla pressionada
                            if code == 304:           # BTN_A (Xbox)
                                return True
                            if code == 305:           # BTN_B (Xbox)
                                return False
    finally:
        if old is not None:
            termios.tcsetattr(kb, termios.TCSADRAIN, old)
        for fd in ev:
            os.close(fd)


def _format_and_install(path, size, dash):
    print("formatando FATX...", flush=True)
    fs = lib.pyfatx_open_helper()
    if lib.fatx_disk_format(fs, path.encode(), 512, FORMAT_F_TAKES_ALL,
                            RETAIL_CLUSTER_SECTORS) != 0:
        sys.exit("falha ao formatar")
    print(f"instalando dashboard...", flush=True)
    c = open_drive(path, size, "c")
    for root, _dirs, files in os.walk(dash):
        rel = os.path.relpath(root, dash)
        base = "" if rel == "." else "/" + rel.replace(os.sep, "/")
        for name in sorted(files):
            # Cerbios boota C:\evoxdash.xbe -> a dashboard entra com esse nome
            out = "evoxdash.xbe" if (rel == "." and name.lower() == "default.xbe") else name
            with open(os.path.join(root, name), "rb") as fsrc:
                put(c, f"{base}/{out}", fsrc.read())
    # Animacao de boot classica do Xbox (Cerbios -> animacao -> dashboard)
    bootanims = os.path.join(os.path.dirname(dash), "bootanims")
    if os.path.isdir(bootanims):
        print("instalando animacao de boot...", flush=True)
        e = open_drive(path, size, "e")
        for root, _d, files in os.walk(bootanims):
            rel = os.path.relpath(root, bootanims)
            base = "/Cerbios/BootAnims" if rel == "." \
                else "/Cerbios/BootAnims/" + rel.replace(os.sep, "/")
            for name in sorted(files):
                with open(os.path.join(root, name), "rb") as fsrc:
                    put(e, f"{base}/{name}", fsrc.read())
    print("pronto: console preparado", flush=True)


def cmd_firstboot(args):
    """Auto-instalador do console no primeiro boot."""
    path, size = image_path(args.device, allow_disk=True, confirm=False)
    if dev_is_fatx(path, size):
        print("disco ja preparado (FATX); nada a fazer")
        return
    if dev_is_blank(path, size):
        print("disco vazio detectado", flush=True)
        _format_and_install(path, size, args.dash)
        return
    # Disco com dados (particao ou conteudo): so formata se o usuario mandar.
    if args.perguntar and ask_confirm(
            "\n  Este disco tem dados. Apagar tudo, formatar e preparar o "
            "console?\n  Teclado: Y = sim / N = nao     Controle: A = sim / "
            "B = nao\n"):
        _format_and_install(path, size, args.dash)
    else:
        print("disco mantido como esta (nao formatado)")


def cmd_list(args):
    path, size = image_path(args.image, getattr(args, 'disco', False))
    fs = open_drive(path, size, args.drive)
    for root, dirs, files in fs.walk("/"):
        for a in files:
            print(f"{root.rstrip('/')}/{a}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("formatar")
    p.add_argument("image")
    p.add_argument("--disco", action="store_true",
                   help="o alvo e um disco de bloco (/dev/sdX); apaga o disco")
    p.set_defaults(func=cmd_format)
    p = sub.add_parser("instalar-smt")
    p.add_argument("image")
    p.add_argument("smt")
    p.add_argument("--dash", default="UnleashX")
    p.add_argument("--disco", action="store_true",
                   help="o alvo e um disco de bloco (/dev/sdX)")
    p.set_defaults(func=cmd_install)
    p = sub.add_parser("instalar-cerbios")
    p.add_argument("image")
    p.add_argument("package")
    p.add_argument("--disco", action="store_true",
                   help="o alvo e um disco de bloco (/dev/sdX)")
    p.set_defaults(func=cmd_cerbios)
    p = sub.add_parser("primeiro-boot")
    p.add_argument("device")
    p.add_argument("dash")
    p.add_argument("--perguntar", action="store_true",
                   help="disco com dados: pergunta na tela antes de formatar")
    p.set_defaults(func=cmd_firstboot)
    p = sub.add_parser("listar")
    p.add_argument("image")
    p.add_argument("--drive", default="c", choices="cef")
    p.add_argument("--disco", action="store_true", help="ler de um disco de bloco")
    p.set_defaults(func=cmd_list)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
