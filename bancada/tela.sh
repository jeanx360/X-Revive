#!/bin/sh
# Captura a tela da VM da bancada: bancada/tela.sh [saida.png]
set -eu
vm=$(cd "$(dirname "$0")" && pwd)/vm
out=${1:-$vm/tela.png}
python3 -I - "$vm/monitor.sock" "$vm/tela.ppm" <<'PY'
import socket, sys, time
s = socket.socket(socket.AF_UNIX)
s.connect(sys.argv[1])
s.sendall(f"screendump {sys.argv[2]}\n".encode())
time.sleep(1.5)
s.close()
PY
python3 -I - "$vm/tela.ppm" "$out" <<'PY'
import sys, zlib, struct
data = open(sys.argv[1], "rb").read()
parts = data.split(maxsplit=4)
w, h = int(parts[1]), int(parts[2])
px = parts[4]
raw = b"".join(b"\0" + px[y*w*3:(y+1)*w*3] for y in range(h))
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
open(sys.argv[2], "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
PY
echo "$out"
