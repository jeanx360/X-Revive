#!/bin/sh
# A GPU ligada a tela pode ser diferente da primeira GPU PCI (notebooks).
set -eu
exec /usr/bin/python3 /usr/local/lib/console/graphics.py "$@"
