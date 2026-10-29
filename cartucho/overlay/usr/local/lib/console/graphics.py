"""Choose the GPU driving a connected screen before starting Cage.

PCI enumeration order is not a display policy, especially on Optimus laptops.
Keep the proven single-NVIDIA settings, but do not export NVIDIA's GBM loader
into a compositor running on Intel/AMD. No persistent hardware configuration.
"""
import json
import os
from pathlib import Path
import subprocess
import sys


def cards(root=Path('/sys/class/drm'), devroot=Path('/dev/dri')):
    result=[]
    for card in sorted(root.glob('card[0-9]*')):
        if not card.name[4:].isdigit():continue
        device=card/'device'
        def read(name,default=''):
            try:return (device/name).read_text().strip()
            except OSError:return default
        driver=(device/'driver').resolve().name if (device/'driver').exists() else ''
        connectors=[p for p in root.glob(card.name+'-*') if (p/'status').exists()]
        connected=[p for p in connectors if (p/'status').read_text().strip()=='connected']
        panel=any('-eDP-' in p.name or '-LVDS-' in p.name or '-DSI-' in p.name for p in connected)
        result.append(dict(path=str(devroot/card.name),driver=driver,vendor=read('vendor'),
                           connected=bool(connected),panel=panel,boot=read('boot_vga')=='1'))
    return result


def choose(items):
    usable=[i for i in items if i['driver']]
    return min(usable,key=lambda i:(not i['panel'],not i['connected'],not i['boot'],i['path'])) if usable else None


def environment(items,mode='auto'):
    selected=choose(items);env={}
    if selected:
        # Limit Cage to the display GPU: cross-GPU scanout isn't required to
        # show the installer. Xemu can still enumerate Vulkan render devices.
        env['WLR_DRM_DEVICES']=selected['path']
        if selected['driver'].startswith('nvidia'):
            env.update(GBM_BACKEND='nvidia-drm',__GLX_VENDOR_LIBRARY_NAME='nvidia',
                       WLR_RENDERER='gles2',WLR_NO_HARDWARE_CURSORS='1',
                       SDL_VIDEO_DRIVER='wayland',SDL_VIDEODRIVER='wayland')
    if mode=='compat':env.update(WLR_DRM_NO_MODIFIERS='1')
    return selected,env


def main():
    if sys.argv[1:]==['pci']:
        selected=choose(cards())
        if selected:print((Path('/sys/class/drm')/Path(selected['path']).name/'device').resolve())
        return
    run=Path('/run/console');run.mkdir(exist_ok=True)
    mode=next((w.split('=',1)[1] for w in Path('/proc/cmdline').read_text().split()
               if w.startswith('xrevive.video=')),'auto')
    items=cards();selected,changes=environment(items,mode)
    (run/'graphics.json').write_text(json.dumps(dict(cards=items,selected=selected,mode=mode,environment=changes),indent=2))
    env=dict(os.environ)
    for key in ('GBM_BACKEND','__GLX_VENDOR_LIBRARY_NAME','WLR_RENDERER','WLR_DRM_DEVICES',
                'WLR_DRM_NO_MODIFIERS','SDL_VIDEO_DRIVER','SDL_VIDEODRIVER'):env.pop(key,None)
    env.update(changes)
    app=sys.argv[1:]
    if app and app[0] in ('installer','update'):
        env.update(SDL_VIDEODRIVER='x11',SDL_RENDER_DRIVER='software',PYTHONUNBUFFERED='1')
        env.pop('SDL_VIDEO_DRIVER',None)
        log=os.open(run/'interface.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o644)
        os.dup2(log,1);os.dup2(log,2);os.close(log)
        app=['/usr/bin/python3',f'/usr/local/lib/console/{app[0]}-ui.py']
    else:app=['/usr/local/lib/console/platform/run.sh']
    print('graphics:',json.dumps(dict(selected=selected,mode=mode,environment=changes)),flush=True)
    os.execve('/usr/bin/cage',['cage','--',*app],env)


if __name__=='__main__':main()
