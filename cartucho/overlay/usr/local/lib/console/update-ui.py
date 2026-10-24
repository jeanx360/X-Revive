"""Console update screen: U/Y opens; Enter/A confirms; Esc/B continues."""
import json
import socket
import textwrap
import time

import pygame
from pygame._sdl2 import controller


def rpc(action, **args):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(3); sock.connect('/run/xrevive-update/control.sock')
        sock.sendall((json.dumps(dict(action=action, **args))+'\n').encode())
        data = json.loads(sock.makefile('r').readline())
    if not data['ok']: raise ValueError(data['error'])
    return data['data']


def main():
    pygame.display.init(); pygame.font.init(); pygame.joystick.init(); controller.init()
    screen = pygame.display.set_mode((1280,720), pygame.FULLSCREEN|pygame.SCALED)
    pygame.mouse.set_visible(False); pygame.display.set_caption('X-Revive — atualização do Xemu')
    font = pygame.font.Font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
    small = pygame.font.Font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
    title = pygame.font.Font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',34)
    logo = pygame.image.load('/usr/share/console/logo.png').convert_alpha()
    logo = pygame.transform.smoothscale(logo,(120,120))
    pads = {}; raw = {}; scroll = 0; last = 0; status = {}; error = ''
    clock = pygame.time.Clock()
    def refresh():
        for index in range(pygame.joystick.get_count()):
            try:
                if controller.is_controller(index):
                    pad = controller.Controller(index); pads[pad.id] = pad
                else:
                    pad = pygame.joystick.Joystick(index); pad.init(); raw[pad.get_instance_id()] = pad
            except pygame.error: pass
    refresh()
    while True:
        if time.monotonic()-last>.4:
            try: status=rpc('status'); error=''
            except (OSError,ValueError) as exc: error=str(exc)
            last=time.monotonic()
        release=status.get('release')
        lines=[]
        if release:
            for line in release['changelog'].splitlines(): lines.extend(textwrap.wrap(line,89) or [''])
        for event in pygame.event.get():
            action=None
            if event.type in (pygame.JOYDEVICEADDED,pygame.CONTROLLERDEVICEADDED):refresh()
            if event.type==pygame.CONTROLLERDEVICEREMOVED:pads.pop(event.instance_id,None)
            if event.type==pygame.JOYDEVICEREMOVED:raw.pop(event.instance_id,None)
            if event.type==pygame.KEYDOWN:
                action={pygame.K_RETURN:'accept',pygame.K_ESCAPE:'back',pygame.K_UP:'up',pygame.K_DOWN:'down'}.get(event.key)
            elif event.type==pygame.CONTROLLERBUTTONDOWN:
                action={pygame.CONTROLLER_BUTTON_A:'accept',pygame.CONTROLLER_BUTTON_B:'back',pygame.CONTROLLER_BUTTON_DPAD_UP:'up',pygame.CONTROLLER_BUTTON_DPAD_DOWN:'down'}.get(event.button)
            elif event.type==pygame.JOYBUTTONDOWN and event.instance_id in raw:
                action={0:'accept',1:'back'}.get(event.button)
            elif event.type==pygame.JOYHATMOTION and event.instance_id in raw:
                action='up' if event.value[1]>0 else 'down' if event.value[1]<0 else None
            if action in ('up','down'):scroll=max(0,min(max(0,len(lines)-10),scroll+(1 if action=='down' else -1)))
            if status.get('phase') not in ('downloading','complete'):
                try:
                    if action=='back' or (action=='accept' and not release):rpc('continue');return
                    if action=='accept' and release:rpc('apply',identity=release['sha256']);last=0
                except (OSError,ValueError) as exc:error=str(exc)
        screen.fill((10,16,20));screen.blit(logo,(52,42))
        def text(message,y,style=font,color=(225,230,228)):
            screen.blit(style.render(str(message),True,color),(220,y))
        text('Atualização do Xemu',56,title,(120,235,156))
        text('Instalado: '+status.get('current','...'),110,small)
        if release:
            text('Nova versão: '+release['version'],146,font,(120,235,156))
            for i,line in enumerate(lines[scroll:scroll+10]):text(line,205+i*30,small)
            if len(lines)>10:text('↑ / ↓ ou digital para ler todas as novidades',525,small)
        else:
            text(status.get('channel',{}).get('message','Nenhuma atualização disponível.'),210,small)
        message=error or status.get('message','')
        if message:
            for i,line in enumerate(textwrap.wrap(message,84)[:2]):text(line,560+i*27,small,(245,199,110))
        if status.get('phase')=='downloading':text('Atualizando... '+str(status.get('progress',0))+'%',650)
        elif status.get('phase')=='complete':text('Concluído. Iniciando Xbox...',650)
        else:text(('A / Enter: atualizar     B / Esc: continuar' if release else 'A / Enter ou B / Esc: continuar'),650)
        pygame.display.flip();clock.tick(30)


if __name__=='__main__':main()
