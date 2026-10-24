#!/usr/bin/env python3
"""Le e converte o EEPROM (256 bytes) do Xbox Classico.

  eeprom.py info    <eeprom.bin>
  eeprom.py convert <entrada.bin> <saida.bin> --to r1|r2|r3

A conversao re-criptografa a secao de seguranca (confounder, HDD key, regiao)
com a chave de outra versao de kernel, mantendo serial, MAC e HDD key.
O arquivo de entrada nunca e alterado.

Chaves e algoritmo: xemu hw/xbox/eeprom_generation.c (LGPL-2.1).
"""
import argparse
import struct
import sys

# Estado SHA-1 apos o primeiro bloco (512 bits) para cada versao de kernel
VERSIONS = {
    "r1": ("retail 1.0",
           (0x72127625, 0x336472B9, 0xBE609BEA, 0xF55E226B, 0x99958DAC),
           (0x76441D41, 0x4DE82659, 0x2E8EF85E, 0xB256FACA, 0xC4FE2DE8)),
    "r2": ("retail 1.1-1.4",
           (0x39B06E79, 0xC9BD25E8, 0xDBC6B498, 0x40B4389D, 0x86BBD7ED),
           (0x9B49BED3, 0x84B430FC, 0x6B8749CD, 0xEBFE5FE5, 0xD96E7393)),
    "r3": ("retail 1.6",
           (0x8058763A, 0xF97D4E0E, 0x865A9762, 0x8A3D920D, 0x08995B2C),
           (0x01075307, 0xA2F1E037, 0x1186EEEA, 0x88DA9992, 0x168A5609)),
    "debug": ("debug",
              (0x85F9E51A, 0xE04613D2, 0x6D86A50C, 0x77C32E3C, 0x4BD717A4),
              (0x5D7A9C6B, 0xE1922BEB, 0xB82CCDBC, 0x3137AB34, 0x486B52B3)),
}

VIDEO = {0x00400100: "NTSC-M", 0x00400200: "NTSC-J",
         0x00800300: "PAL-I", 0x00400400: "PAL-M"}
REGION = {1: "America do Norte", 2: "Japao", 4: "Europa/Australia",
          0x80000000: "fabrica"}


def _rol(x, n):
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF


def _compress(h, blk):
    w = list(struct.unpack(">16I", blk)) + [0] * 64
    for i in range(16, 80):
        w[i] = _rol(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1)
    a, b, c, d, e = h
    for i in range(80):
        if i < 20:
            f, k = (b & c) | (~b & d), 0x5A827999
        elif i < 40:
            f, k = b ^ c ^ d, 0x6ED9EBA1
        elif i < 60:
            f, k = (b & c) | (b & d) | (c & d), 0x8F1BBCDC
        else:
            f, k = b ^ c ^ d, 0xCA62C1D6
        a, b, c, d, e = (_rol(a, 5) + f + e + k + w[i]) & 0xFFFFFFFF, a, _rol(b, 30), c, d
    return [(x + y) & 0xFFFFFFFF for x, y in zip(h, (a, b, c, d, e))]


def _sha1_from(state, data):
    total = 64 + len(data)
    msg = data + b"\x80" + b"\0" * ((55 - total) % 64) + struct.pack(">Q", total * 8)
    h = list(state)
    for i in range(0, len(msg), 64):
        h = _compress(h, msg[i:i + 64])
    return struct.pack(">5I", *h)


def _hmac(ver, data):
    _, first, second = VERSIONS[ver]
    return _sha1_from(second, _sha1_from(first, data))


def _rc4(key, data):
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 255
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = bytearray()
    for byte in data:
        i = (i + 1) & 255
        j = (j + s[i]) & 255
        s[i], s[j] = s[j], s[i]
        out.append(byte ^ s[(s[i] + s[j]) & 255])
    return bytes(out)


def _crc(data):
    hi = lo = 0
    for (v,) in struct.iter_unpack("<I", data):
        total = (hi << 32) | lo
        hi = ((total + v) >> 32) & 0xFFFFFFFF
        lo = (lo + v) & 0xFFFFFFFF
    return ~(hi + lo) & 0xFFFFFFFF


def decrypt(raw):
    """Retorna (versao, secao_em_claro) ou (None, None)."""
    for ver in VERSIONS:
        plain = _rc4(_hmac(ver, raw[:20]), raw[0x14:0x30])
        if _hmac(ver, plain) == raw[:20]:
            return ver, plain
    return None, None


def encrypt(raw, plain, ver):
    digest = _hmac(ver, plain)
    return digest + _rc4(_hmac(ver, digest), plain) + raw[0x30:]


def load(path):
    raw = open(path, "rb").read()
    if len(raw) != 256:
        sys.exit(f"{path}: {len(raw)} bytes; um EEPROM do Xbox tem 256")
    return raw


def cmd_info(args):
    raw = load(args.file)
    ver, plain = decrypt(raw)
    factory_ok = _crc(raw[0x34:0x60]) == struct.unpack("<I", raw[0x30:0x34])[0]
    user_ok = _crc(raw[0x64:0xC0]) == struct.unpack("<I", raw[0x60:0x64])[0]
    video = struct.unpack("<I", raw[0x58:0x5C])[0]
    print(f"checksum fabrica: {'ok' if factory_ok else 'INVALIDO'}")
    print(f"checksum usuario: {'ok' if user_ok else 'INVALIDO'}")
    print(f"serial:           {raw[0x34:0x40].decode('ascii', 'replace')}")
    print(f"MAC:              {':'.join(f'{b:02x}' for b in raw[0x40:0x46])}")
    print(f"video:            {VIDEO.get(video, hex(video))}")
    if ver is None:
        print("seguranca:        nao decifra com nenhuma chave conhecida")
        return 1
    region = struct.unpack("<I", plain[24:28])[0]
    print(f"seguranca:        ok, chave {ver} ({VERSIONS[ver][0]})")
    print(f"regiao:           {REGION.get(region, hex(region))}")
    if args.show_key:
        print(f"HDD key:          {plain[8:24].hex().upper()}")
    return 0


def cmd_convert(args):
    raw = load(args.input)
    ver, plain = decrypt(raw)
    if ver is None:
        sys.exit("secao de seguranca nao decifra; nada a converter")
    out = encrypt(raw, plain, args.to)
    if decrypt(out) != (args.to, plain):
        sys.exit("verificacao da conversao falhou")
    with open(args.output, "xb") as f:
        f.write(out)
    print(f"{args.input} ({ver}) -> {args.output} ({args.to}), HDD key/serial/MAC preservados")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("info")
    i.add_argument("file")
    i.add_argument("--show-key", action="store_true", help="mostra a HDD key")
    i.set_defaults(func=cmd_info)
    c = sub.add_parser("convert")
    c.add_argument("input")
    c.add_argument("output")
    c.add_argument("--to", required=True, choices=sorted(VERSIONS))
    c.set_defaults(func=cmd_convert)
    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
