#!/bin/sh
# Ajustes NVIDIA so na variante dedicada E com o driver proprietario carregado.
set -eu
variant=$(cat /etc/console-variant 2>/dev/null || echo universal)
if [ -d /sys/module/nvidia_drm ] && grep -q '^gpu_driver=nvidia$' /run/console/profile 2>/dev/null; then
    export GBM_BACKEND=nvidia-drm __GLX_VENDOR_LIBRARY_NAME=nvidia
    export WLR_RENDERER=gles2 WLR_NO_HARDWARE_CURSORS=1
    export SDL_VIDEO_DRIVER=wayland SDL_VIDEODRIVER=wayland
fi
# SDL2/Pygame SCALED hangs in set_mode under forced Wayland (reproduced
# even with virtio). Xemu uses its own SDL3 and retains native Wayland.
case "${1:-}" in
    installer|update)
        export SDL_VIDEODRIVER=x11 SDL_RENDER_DRIVER=software PYTHONUNBUFFERED=1
        exec >>/run/console/interface.log 2>&1
        echo "interface=$1 SDL2=x11 renderer=software"
        unset SDL_VIDEO_DRIVER
        exec /usr/bin/cage -- /usr/bin/python3 "/usr/local/lib/console/${1}-ui.py"
        ;;
esac
exec /usr/bin/cage -- /usr/local/lib/console/platform/run.sh
