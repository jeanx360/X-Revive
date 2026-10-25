"""Own console UI: keyboard OR SDL game controller, without a mouse."""
import json
import os
from pathlib import Path
import socket
import time
import threading

import pygame
from pygame._sdl2 import controller

SOCKET='/run/xrevive-installer/control.sock'


def rpc(action,**args):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
        sock.settimeout(30);sock.connect(SOCKET)
        sock.sendall((json.dumps(dict(action=action,**args))+'\n').encode())
        result=json.loads(sock.makefile('r').readline())
    if not result['ok']:raise ValueError(result['error'])
    return result['data']


class Confirmation:
    """Two holds require release before each, including across screen changes."""
    def __init__(self):self.reset()
    def reset(self):self.released=False;self.since=None
    def update(self,pressed,now):
        if not pressed:self.released=True;self.since=None;return False
        if not self.released:return False
        if self.since is None:self.since=now
        if now-self.since>=1.2:self.reset();return True
        return False


class UI:
    def __init__(self):
        print("UI: inicializando SDL2",flush=True)
        pygame.display.init();pygame.font.init();pygame.joystick.init();controller.init()
        self.screen=pygame.display.set_mode((1280,720),pygame.FULLSCREEN|pygame.SCALED)
        print("UI: janela pronta",flush=True)
        pygame.mouse.set_visible(False)
        pygame.display.set_caption('X-Revive — instalação e manutenção')
        self.font=pygame.font.Font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
        self.small=pygame.font.Font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
        self.title_font=pygame.font.Font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',34)
        self.logo=pygame.image.load('/usr/share/console/logo.png').convert_alpha()
        self.logo=pygame.transform.smoothscale(self.logo,(155,155))
        self.pads={};self.rawpads={};self.refresh_pads()
        self.state='loading';self.selected=0;self.confirm=Confirmation();self.plan=None
        self.message='';self.task='';self.target=None;self.disk_action='install';self.last_poll=0
        self.boot={'disks':[],'dashboards':[],'installed':False};self.status={};self.running=True
        self.loaded=None
        def connect():
            for attempt in range(15):
                try:self.loaded=rpc('hello');return
                except Exception as exc:
                    if attempt==14:self.loaded={'error':str(exc)}
                    time.sleep(1)
        threading.Thread(target=connect,daemon=True).start()

    def refresh_pads(self):
        for i in range(pygame.joystick.get_count()):
            try:
                if controller.is_controller(i):
                    pad=controller.Controller(i);self.pads[pad.id]=pad
                else:
                    pad=pygame.joystick.Joystick(i);pad.init();self.rawpads[pad.get_instance_id()]=pad
            except pygame.error:pass

    def combo(self):
        if pygame.key.get_pressed()[pygame.K_F10]:return True
        for pad in self.pads.values():
            try:
                if (pad.get_button(pygame.CONTROLLER_BUTTON_START) and
                    pad.get_axis(pygame.CONTROLLER_AXIS_TRIGGERLEFT)>16000 and
                    pad.get_axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT)>16000):return True
            except pygame.error:pass
        for pad in self.rawpads.values():
            try:
                if pad.get_numbuttons()>7 and pad.get_numaxes()>5 and pad.get_button(7) and pad.get_axis(2)>.5 and pad.get_axis(5)>.5:return True
            except pygame.error:pass
        return False

    def go(self,state):self.state=state;self.selected=0;self.message='';self.confirm.reset()

    def options(self):
        if self.state=='sources':return ['Rocky5 — baixar pela internet','Usar ISO offline do pendrive','Voltar']
        if self.state=='images':return [s['name'] for s in self.boot.get('sources',[])]+['Voltar']
        if self.state=='welcome':return ['Instalar X-Revive no HDD / SSD','Manutenção','Desligar']
        if self.state=='disks':
            return [f"{r['model'] or r['path']} — {r['bytes']/10**9:.1f} GB" for r in self.boot['disks']]+['Voltar']
        if self.state=='maintenance':return ['Comparar arquivos com o pacote original','Reparar boot do X-Revive','Escolher dashboard padrão']+(['Reverter atualização do Xemu'] if self.boot['installed'] else [])+['Voltar']
        if self.state=='dashboards':return [d['name'] for d in self.boot['dashboards']]+['Voltar']
        if self.state in ('complete','error'):return ['Reiniciar','Voltar ao menu','Desligar']
        return []

    def start_task(self,action,**args):
        rpc(action,**args);self.task=action;self.go('progress');self.last_poll=0

    def pick_disk(self,action):
        self.boot=rpc('hello');self.disk_action=action;self.go('disks')

    def accept(self):
        if self.state=='welcome':
            if self.selected==0:self.go('sources')
            elif self.selected==1:
                if self.boot['installed']:self.target='current';self.go('maintenance')
                else:self.pick_disk('maintenance')
            else:rpc('poweroff')
        elif self.state=='sources':
            if self.selected==0:self.start_task('prepare',mode='online')
            elif self.selected==1:
                self.boot=rpc('hello');self.go('images')
                if not self.boot.get('sources'):self.message='Coloque a ISO em XREVIVE / X-Revive / pacotes.'
            else:self.go('welcome')
        elif self.state=='images':
            items=self.boot.get('sources',[])
            if self.selected>=len(items):self.go('sources')
            else:self.start_task('prepare',mode='offline',identity=items[self.selected]['id'])
        elif self.state=='disks':
            if self.selected>=len(self.boot['disks']):self.go('welcome');return
            row=self.boot['disks'][self.selected]
            if not row['available']:self.message=row.get('reason','Disco indisponível');return
            self.target=row['identity']
            if self.disk_action=='install':
                self.plan=rpc('plan',target=self.target);self.go('confirm1')
            else:
                self.boot['dashboards']=rpc('maintenance-info',target=self.target)['dashboards']
                self.go('maintenance')
        elif self.state=='maintenance':
            if self.selected==0:self.start_task('verify',target=self.target)
            elif self.selected==1:self.start_task('repair',target=self.target)
            elif self.selected==2:self.go('dashboards')
            elif self.selected==3 and self.boot['installed']:self.start_task('revert-emulator',target='current')
            else:self.go('welcome')
        elif self.state=='dashboards':
            if self.selected>=len(self.boot['dashboards']):self.go('maintenance')
            else:self.start_task('dashboard',target=self.target,name=self.boot['dashboards'][self.selected]['name'])
        elif self.state in ('complete','error'):
            if self.selected==0:rpc('reboot')
            elif self.selected==1:self.go('welcome')
            else:rpc('poweroff')

    def back(self):
        if self.state in ('confirm1','confirm2'):rpc('cancel');self.go('disks')
        elif self.state=='dashboards':self.go('maintenance')
        elif self.state!='progress':self.go('welcome')

    def event(self,event):
        action=None
        if event.type in (pygame.JOYDEVICEADDED,pygame.CONTROLLERDEVICEADDED):self.refresh_pads()
        if event.type==pygame.CONTROLLERDEVICEREMOVED:self.pads.pop(event.instance_id,None)
        if event.type==pygame.JOYDEVICEREMOVED:self.rawpads.pop(event.instance_id,None)
        if event.type==pygame.KEYDOWN:
            action={pygame.K_UP:'up',pygame.K_DOWN:'down',pygame.K_RETURN:'accept',pygame.K_ESCAPE:'back'}.get(event.key)
        elif event.type==pygame.CONTROLLERBUTTONDOWN:
            action={pygame.CONTROLLER_BUTTON_A:'accept',pygame.CONTROLLER_BUTTON_B:'back',
                    pygame.CONTROLLER_BUTTON_DPAD_UP:'up',pygame.CONTROLLER_BUTTON_DPAD_DOWN:'down'}.get(event.button)
        elif event.type==pygame.JOYBUTTONDOWN and event.instance_id in self.rawpads:
            action={0:'accept',1:'back'}.get(event.button)
        elif event.type==pygame.JOYHATMOTION and event.instance_id in self.rawpads:
            action='up' if event.value[1]>0 else 'down' if event.value[1]<0 else None
        if action=='back':self.back()
        elif action=='accept':self.accept()
        elif action in ('up','down'):
            options=self.options()
            if options:self.selected=(self.selected+(1 if action=='down' else -1))%len(options)

    def text(self,text,y,color=(225,230,228),font=None,x=220):
        font=font or self.font
        for line in str(text).splitlines():
            self.screen.blit(font.render(line,True,color),(x,y));y+=font.get_linesize()+5
        return y

    def draw(self):
        screen=self.screen;screen.fill((9,14,14));screen.blit(self.logo,(35,25))
        self.text('X-REVIVE',43,(102,240,170),self.title_font)
        titles={'loading':'Abrindo instalador...','sources':'De onde instalar os aplicativos?','images':'Escolha a ISO offline','welcome':'Instalação e manutenção','disks':'Escolha o disco de destino',
                'maintenance':'Manutenção do sistema','dashboards':'Dashboard padrão',
                'confirm1':'Confira o disco antes de continuar','confirm2':'ATENÇÃO: TODOS OS DADOS SERÃO APAGADOS',
                'progress':'Preparando seu console','complete':'Concluído','error':'A operação não foi concluída'}
        self.text(titles[self.state],99,(255,100,95) if self.state=='confirm2' else (210,220,216),self.font)
        if self.state in ('confirm1','confirm2'):
            d=self.plan['device'];y=210
            for line in [d['model'],d['path'],'Série: '+(d['serial'] or 'não informada'),
                         f"Disco: {d['bytes']/10**9:.1f} GB — Xbox: {self.plan['xbox_gib']:.2f} GiB",
                         'Instalação completa. Os dados existentes serão apagados.',
                         'Segure LT + RT + Start OU F10 até confirmar.',
                         'Solte os botões antes de confirmar novamente.']:
                y=self.text(line,y)
        elif self.state=='progress':
            self.text(self.status.get('message','Verificando...'),270)
            pygame.draw.rect(screen,(38,52,46),(220,350,840,18),border_radius=6)
            pygame.draw.rect(screen,(90,230,155),(220,350,int(840*self.status.get('progress',0)/100),18),border_radius=6)
            self.text('Aguarde. Mantenha o equipamento ligado e o pendrive conectado.',405,font=self.small)
        else:
            options=self.options();start=max(0,self.selected-6);y=200
            for index in range(start,min(len(options),start+8)):
                if index==self.selected:pygame.draw.rect(screen,(30,70,49),(205,y-4,1030,42),border_radius=8)
                self.text(options[index],y,(160,255,195) if index==self.selected else (210,220,216));y+=48
            if self.state=='complete' and self.task=='install':self.text('Remova o pendrive antes de reiniciar.',y+20,(130,245,175),self.small)
            if self.state=='complete' and self.task=='verify':
                result=self.status.get('result') or {}
                self.text(f"Conferidos: {result.get('checked',0)} — alterados: {result.get('modified',0)} — ausentes: {result.get('missing',0)}",y+20,font=self.small)
                self.text('Configurações e atualizações podem mudar arquivos. Nada foi restaurado.',y+55,font=self.small)
        if self.state=='sources':
            self.text('Firmware: XREVIVE / X-Revive / firmware / xbox',450,font=self.small)
            self.text('BIOS e MCPX obrigatórios • EEPROM opcional',485,font=self.small)
        if self.message:self.text(self.message[:110],615,(255,125,110),self.small,x=40)
        footer=('Instalação em andamento — aguarde a conclusão.' if self.state=='progress' else
                '↑ ↓ / Digital: navegar     Enter / A: escolher     Esc / B: voltar')
        self.text(footer,675,(135,160,145),self.small,x=40)
        pygame.display.flip()

    def run(self):
        clock=pygame.time.Clock()
        while self.running:
            try:
                if self.state=='loading' and self.loaded is not None:
                    if 'error' in self.loaded:self.go('error');self.message=self.loaded['error']
                    else:self.boot=self.loaded;self.go('welcome')
                for event in pygame.event.get():self.event(event)
                now=time.monotonic()
                if self.state in ('confirm1','confirm2') and self.confirm.update(self.combo(),now):
                    step=1 if self.state=='confirm1' else 2
                    rpc('confirm',token=self.plan['token'],step=step)
                    if step==1:self.go('confirm2')
                    else:self.start_task('install',token=self.plan['token'])
                if self.state=='progress' and now-self.last_poll>.5:
                    self.status=rpc('status');self.last_poll=now
                    if not self.status['busy']:
                        if self.status.get('error'):
                            self.go('error');self.message=self.status['error']
                        elif self.task=='prepare':self.pick_disk('install')
                        else:self.go('complete')
                self.draw();clock.tick(30)
            except (ValueError,OSError) as exc:self.message=str(exc);self.draw();clock.tick(10)


if __name__=='__main__':UI().run()
