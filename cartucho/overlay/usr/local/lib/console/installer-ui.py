"""Own console UI: keyboard OR SDL game controller, without a mouse."""
import json
import os
from pathlib import Path
import socket
import time
import threading
import math
import uuid
from ui_rpc import Calls

import pygame
from pygame._sdl2 import controller
from on_screen_keyboard import Keyboard

SOCKET='/run/xrevive-installer/control.sock'


def rpc(action,**args):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
        sock.settimeout(3 if action=='status' else 30);sock.connect(SOCKET)
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
        self.calls=Calls(rpc);self.details=False;self.operation_id=None
        self.task_ack=False;self.last_response=time.monotonic();self.pending_since=time.monotonic()
        self.live_access='protected';self.live_media={'mode':'offline','identity':None}
        self.wireless={'networks':[]};self.wifi_return='welcome';self.wifi_target=None;self.entry=Keyboard()
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
        if self.state=='live-mode':return ['Protegido — alterações temporárias, sem gravar no HDD','Instalação / manutenção — acesso ao HDD selecionado','Voltar']
        if self.state=='sandbox-sources':return ['Rocky5 Extras Disc — baixar pela internet','Usar mídia do pendrive','Iniciar dashboard do HDD — sem mídia','Configurar rede Wi-Fi','Voltar']
        if self.state=='sandbox-images':return [s['name'] for s in self.boot.get('live_images',[])]+['Atualizar lista','Voltar']
        if self.state=='sources':return ['Rocky5 — baixar pela internet','Usar ISO offline do pendrive','Configurar rede Wi-Fi','Voltar']
        if self.state=='images':return [s['name'] for s in self.boot.get('sources',[])]+['Atualizar lista','Voltar']
        if self.state=='wifi':
            return [r['ssid']+f" — {r['signal']}% — {r['security']}"+(' — conectada' if r['connected'] else '') for r in self.wireless.get('networks',[])]+['Atualizar redes','Desconectar Wi-Fi','Voltar']
        if self.state=='welcome':
            if self.boot.get('safe_live'):return ['LIVE — mídias do usuário','Configurar rede Wi-Fi','Desligar']
            return ([] if self.boot['installed'] else ['LIVE — iniciar Xbox por mídia ou HDD'])+['Instalar X-Revive no HDD / SSD','Manutenção']+([] if self.boot['installed'] else ['Preparar boot de HDD Xbox existente'])+['Configurar rede Wi-Fi','Desligar']
        if self.state=='media-disks':
            rows=self.boot.get('media_disks',[])
            virtual=['HDD virtual temporário — nenhum disco físico'] if self.live_access=='protected' and self.live_media['mode']!='hdd' else []
            return virtual+[f"{r['model'] or r['path']} — {r['bytes']/10**9:.1f} GB — {r.get('transport') or 'interno'} — {r.get('kind','indisponível')}" for r in rows]+['Atualizar discos','Voltar']
        if self.state=='live-disks':
            return [f"{r['model'] or r['path']} — {r['bytes']/10**9:.1f} GB"+(' — indisponível' if not r['available'] else '') for r in self.boot.get('live_disks',[])]+['Voltar']
        if self.state=='live-choice':return ['Apenas iniciar em LIVE — sem gravar no HDD','Preparar / reparar boot automático do X-Revive','Voltar']
        if self.state=='disks':
            return [f"{r['model'] or r['path']} — {r['bytes']/10**9:.1f} GB" for r in self.boot['disks']]+['Voltar']
        if self.state=='maintenance':return ['Comparar arquivos com o pacote original','Reparar boot do X-Revive','Escolher dashboard padrão']+(['Reverter atualização do Xemu'] if self.boot['installed'] else [])+['Voltar']
        if self.state=='dashboards':return [d['name'] for d in self.boot['dashboards']]+['Voltar']
        if self.state in ('complete','error'):return ['Reiniciar','Voltar ao menu','Desligar']
        return []

    def call(self,action,success=None,failure=None,**args):
        self.pending_since=time.monotonic()
        return self.calls.submit('control',action,success,failure or self.call_error,**args)

    def call_error(self,error):self.message=str(error)

    def refresh_boot(self,state):
        def ready(data):self.boot=data;self.go(state)
        self.call('hello',ready)

    def refresh_disks(self,action,key,state):
        def ready(data):self.boot[key]=data['disks'];self.go(state)
        self.call(action,ready)

    def start_task(self,action,**args):
        self.task=action;self.operation_id=uuid.uuid4().hex;self.task_ack=False
        self.status=dict(busy=True,message='Preparando a operação...',progress=0)
        self.go('progress');self.last_poll=0;self.last_response=time.monotonic()
        def accepted(_):self.task_ack=True
        def failed(exc):
            if isinstance(exc,OSError):
                self.task_ack=True;self.message='Início sem confirmação; consultando o serviço, sem repetir a operação.'
            else:self.go('error');self.message=str(exc)
        self.call(action,accepted,failed,operation_id=self.operation_id,**args)

    def pick_disk(self,action):
        self.disk_action=action;self.refresh_boot('disks')

    def accept(self):
        if self.options() and self.options()[self.selected]=='Configurar rede Wi-Fi':
            self.wifi_return=self.state;self.start_task('wifi-scan');return
        if self.state=='welcome':
            if self.boot.get('safe_live'):
                if self.selected==0:self.go('sandbox-sources')
                else:self.call('poweroff')
                return
            choice=self.options()[self.selected]
            if choice.startswith('LIVE'):self.go('live-mode')
            elif choice.startswith('Instalar'):self.go('sources')
            elif choice=='Manutenção':
                if self.boot['installed']:self.target='current';self.go('maintenance')
                else:self.pick_disk('maintenance')
            elif choice.startswith('Preparar boot'):
                self.refresh_disks('live-disks','live_disks','live-disks')
            else:self.call('poweroff')
        elif self.state=='live-mode':
            if self.selected<2:
                self.live_access='protected' if self.selected==0 else 'write';self.go('sandbox-sources')
            else:self.go('welcome')
        elif self.state=='sandbox-sources':
            if self.selected==0:self.choose_live_media('online')
            elif self.selected==1:
                self.refresh_boot('sandbox-images')
            elif self.selected==2:self.choose_live_media('hdd')
            else:self.go('live-mode')
        elif self.state=='sandbox-images':
            items=self.boot.get('live_images',[])
            if self.selected==len(items):self.refresh_boot('sandbox-images')
            elif self.selected>len(items):self.go('sandbox-sources')
            else:self.choose_live_media('offline',items[self.selected]['id'])
        elif self.state=='media-disks':
            rows=self.boot.get('media_disks',[])
            virtual=self.live_access=='protected' and self.live_media['mode']!='hdd'
            if virtual and self.selected==0:
                self.start_task('sandbox-start',**self.live_media);return
            index=self.selected-int(virtual)
            if index==len(rows):self.refresh_disks('media-disks','media_disks','media-disks');return
            if index>len(rows):self.go('sandbox-sources');return
            row=rows[index]
            if not row['available']:self.message=row.get('reason','Disco indisponível');return
            def ready(plan):
                self.plan=plan
                if self.live_access=='write':self.go('media-confirm1')
                else:self.start_task('media-start',token=plan['token'])
            self.call('media-plan',ready,target=row['identity'],access=self.live_access,**self.live_media)
        elif self.state=='wifi':
            rows=self.wireless.get('networks',[])
            if self.selected<len(rows):
                self.wifi_target=rows[self.selected]
                if not self.wifi_target['supported']:self.message='Esta rede exige um método de autenticação ainda não suportado.'
                elif self.wifi_target['password']:
                    self.entry=Keyboard();self.go('wifi-password');pygame.key.start_text_input()
                else:self.connect_wifi()
            elif self.selected==len(rows):self.start_task('wifi-scan')
            elif self.selected==len(rows)+1:self.start_task('wifi-disconnect')
            else:self.go(self.wifi_return)
        elif self.state=='live-disks':
            rows=self.boot.get('live_disks',[])
            if self.selected>=len(rows):self.go('welcome');return
            row=rows[self.selected]
            if not row['available']:self.message=row.get('reason','HDD não suportado');return
            self.target=row['identity']
            def ready(plan):self.plan=plan;self.go('live-choice')
            self.call('live-plan',ready,target=row['identity'])
        elif self.state=='live-choice':
            if self.selected==0:self.start_task('live-start',token=self.plan['token'],mode='protected')
            elif self.selected==1:
                if self.plan['boot']['available']:self.go('live-boot-confirm1')
                else:self.message=self.plan['boot']['message']
            else:self.call('cancel',lambda _:self.go('live-disks'))
        elif self.state=='sources':
            if self.selected==0:self.start_task('prepare',mode='online')
            elif self.selected==1:
                self.refresh_boot('images')
            else:self.go('welcome')
        elif self.state=='images':
            items=self.boot.get('sources',[])
            if self.selected==len(items):self.refresh_boot('images')
            elif self.selected>len(items):self.go('sources')
            else:self.start_task('prepare',mode='offline',identity=items[self.selected]['id'])
        elif self.state=='disks':
            if self.selected>=len(self.boot['disks']):self.go('welcome');return
            row=self.boot['disks'][self.selected]
            if not row['available']:self.message=row.get('reason','Disco indisponível');return
            self.target=row['identity']
            if self.disk_action=='install':
                def ready(plan):self.plan=plan;self.go('confirm1')
                self.call('plan',ready,target=self.target)
            else:
                def ready(data):
                    if data.get('native'):
                        self.plan=data['plan'];self.go('live-choice')
                        self.message='HDD Xbox reconhecido. Inicie em LIVE ou prepare/repare seu boot.'
                    else:self.boot['dashboards']=data['dashboards'];self.go('maintenance')
                self.call('maintenance-info',ready,target=self.target)
        elif self.state=='maintenance':
            if self.selected==0:self.start_task('verify',target=self.target)
            elif self.selected==1:
                if self.target=='current':self.start_task('repair',target=self.target)
                else:
                    def ready(plan):
                        self.plan=plan
                        if plan['boot']['available']:self.go('live-boot-confirm1')
                        else:self.message=plan['boot']['message']
                    self.call('live-plan',ready,target=self.target)
            elif self.selected==2:self.go('dashboards')
            elif self.selected==3 and self.boot['installed']:self.start_task('revert-emulator',target='current')
            else:self.go('welcome')
        elif self.state=='dashboards':
            if self.selected>=len(self.boot['dashboards']):self.go('maintenance')
            else:self.start_task('dashboard',target=self.target,name=self.boot['dashboards'][self.selected]['name'])
        elif self.state in ('complete','error'):
            if self.selected==0:self.call('reboot')
            elif self.selected==1:self.go('welcome')
            else:self.call('poweroff')

    def connect_wifi(self):
        password=self.entry.text;self.entry.clear();pygame.key.stop_text_input()
        self.start_task('wifi-connect',identity=self.wifi_target['id'],password=password)

    def choose_live_media(self,mode,identity=None):
        self.live_media=dict(mode=mode,identity=identity)
        if self.boot.get('safe_live'):
            self.start_task('sandbox-start',**self.live_media);return
        self.refresh_disks('media-disks','media_disks','media-disks')

    def back(self):
        if self.state=='progress':
            if self.status.get('cancellable'):
                self.call('task-cancel',lambda _:setattr(self,'message','Cancelando a preparação; aguarde liberar o HDD.'),operation_id=self.operation_id)
            else:self.message='Aguarde esta etapa terminar. F1 / X mostra os detalhes.'
            return
        if self.state=='wifi-password':self.entry.clear();pygame.key.stop_text_input();self.go('wifi')
        elif self.state=='wifi':self.go(self.wifi_return)
        elif self.state=='sandbox-images':self.go('sandbox-sources')
        elif self.state in ('media-confirm1','media-confirm2'):self.call('cancel',lambda _:self.go('media-disks'))
        elif self.state=='media-disks':self.call('cancel',lambda _:self.go('sandbox-sources'))
        elif self.state=='sandbox-sources':self.go('live-mode')
        elif self.state=='images':self.go('sources')
        elif self.state in ('confirm1','confirm2'):self.call('cancel',lambda _:self.go('disks'))
        elif self.state in ('live-boot-confirm1','live-boot-confirm2'):
            self.call('live-boot-cancel',lambda _:self.go('live-choice'),token=self.plan['token'])
        elif self.state=='live-choice':self.call('cancel',lambda _:self.go('live-disks'))
        elif self.state=='dashboards':self.go('maintenance')
        elif self.state not in ('progress','live-starting'):self.go('welcome')

    def event(self,event):
        action=None
        if event.type in (pygame.JOYDEVICEADDED,pygame.CONTROLLERDEVICEADDED):self.refresh_pads();return
        if event.type==pygame.CONTROLLERDEVICEREMOVED:self.pads.pop(event.instance_id,None);return
        if event.type==pygame.JOYDEVICEREMOVED:self.rawpads.pop(event.instance_id,None);return
        if self.state in ('progress','live-starting') and (
            event.type==pygame.KEYDOWN and event.key==pygame.K_F1 or
            event.type==pygame.CONTROLLERBUTTONDOWN and event.button==pygame.CONTROLLER_BUTTON_X or
            event.type==pygame.JOYBUTTONDOWN and event.instance_id in self.rawpads and event.button==2):
            self.details=not self.details;return
        if 'control' in self.calls.pending:return
        if self.state=='wifi-password':
            if event.type==pygame.TEXTINPUT:self.entry.insert(event.text);return
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_RETURN:self.connect_wifi()
                elif event.key==pygame.K_ESCAPE:self.back()
                elif event.key==pygame.K_BACKSPACE:self.entry.erase()
                elif event.key in (pygame.K_LEFT,pygame.K_RIGHT):self.entry.move(dx=1 if event.key==pygame.K_RIGHT else -1)
                elif event.key in (pygame.K_UP,pygame.K_DOWN):self.entry.move(dy=1 if event.key==pygame.K_DOWN else -1)
                return
        if event.type in (pygame.JOYDEVICEADDED,pygame.CONTROLLERDEVICEADDED):self.refresh_pads()
        if event.type==pygame.CONTROLLERDEVICEREMOVED:self.pads.pop(event.instance_id,None)
        if event.type==pygame.JOYDEVICEREMOVED:self.rawpads.pop(event.instance_id,None)
        if event.type==pygame.KEYDOWN:
            action={pygame.K_UP:'up',pygame.K_DOWN:'down',pygame.K_RETURN:'accept',pygame.K_ESCAPE:'back'}.get(event.key)
        elif event.type==pygame.CONTROLLERBUTTONDOWN:
            action={pygame.CONTROLLER_BUTTON_A:'accept',pygame.CONTROLLER_BUTTON_B:'back',
                    pygame.CONTROLLER_BUTTON_DPAD_UP:'up',pygame.CONTROLLER_BUTTON_DPAD_DOWN:'down',
                    pygame.CONTROLLER_BUTTON_DPAD_LEFT:'left',pygame.CONTROLLER_BUTTON_DPAD_RIGHT:'right',
                    pygame.CONTROLLER_BUTTON_X:'erase'}.get(event.button)
        elif event.type==pygame.JOYBUTTONDOWN and event.instance_id in self.rawpads:
            action={0:'accept',1:'back',2:'erase'}.get(event.button)
        elif event.type==pygame.JOYHATMOTION and event.instance_id in self.rawpads:
            action='up' if event.value[1]>0 else 'down' if event.value[1]<0 else 'right' if event.value[0]>0 else 'left' if event.value[0]<0 else None
        if self.state=='wifi-password':
            if action=='back':self.back()
            elif action=='erase':self.entry.erase()
            elif action in ('left','right'):self.entry.move(dx=1 if action=='right' else -1)
            elif action in ('up','down'):self.entry.move(dy=1 if action=='down' else -1)
            elif action=='accept':
                choice=self.entry.choose()
                if choice=='Conectar':self.connect_wifi()
                elif choice=='Cancelar':self.back()
            return
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

    def fit(self,text,width=1000,font=None):
        font=font or self.font;text=str(text)
        if font.size(text)[0]<=width:return text
        while text and font.size(text+'…')[0]>width:text=text[:-1]
        return text+'…'

    def draw(self):
        screen=self.screen;screen.fill((9,14,14));screen.blit(self.logo,(35,25))
        active=self.state in ('loading','progress','live-starting') or bool(self.calls.pending)
        if active:
            glow=self.logo.copy();glow.set_alpha(int(160+80*math.sin(time.monotonic()*3)))
            pygame.draw.rect(screen,(9,14,14),(35,25,155,155));screen.blit(glow,(35,25))
        self.text('X-REVIVE',43,(102,240,170),self.title_font)
        titles={'loading':'Abrindo instalador...','sources':'De onde instalar os aplicativos?','images':'Escolha a ISO offline','welcome':'Instalação e manutenção','disks':'Escolha o disco de destino',
                'live-mode':'Como deseja usar o Xbox em LIVE?',
                'sandbox-sources':'LIVE — escolha como iniciar o Xbox',
                'sandbox-images':'Escolha a mídia do pendrive',
                'media-disks':'Escolha o HDD / SSD — interno ou USB',
                'media-confirm1':'Autorizar acesso ao disco selecionado',
                'media-confirm2':'Confirme novamente — a mídia poderá apagar dados',
                'wifi':'Configurar rede Wi-Fi','wifi-password':'Conectar à rede Wi-Fi',
                'live-disks':'Escolha o HDD Xbox existente','live-choice':'Iniciar pelo pendrive — sem instalar',
                'live-boot-confirm1':'Preparar boot automático — confira o HDD',
                'live-boot-confirm2':'Confirme novamente a preparação do boot',
                'live-starting':'Iniciando o Xbox em modo LIVE...',
                'maintenance':'Manutenção do sistema','dashboards':'Dashboard padrão',
                'confirm1':'Confira o disco antes de continuar','confirm2':'ATENÇÃO: TODOS OS DADOS SERÃO APAGADOS',
                'progress':'Configurando rede Wi-Fi' if self.task.startswith('wifi-') else 'Preparando seu console','complete':'Concluído','error':'A operação não foi concluída'}
        self.text(titles[self.state],99,(255,100,95) if self.state=='confirm2' else (210,220,216),self.font)
        if self.state=='wifi-password':
            self.text(self.fit(self.wifi_target['ssid']),175,font=self.small)
            self.text(self.fit('•'*len(self.entry.text)),220,(160,255,195))
            for row,keys in enumerate(self.entry.rows()):
                width=1030/len(keys)
                for col,key in enumerate(keys):
                    x=205+int(col*width);y=280+row*46
                    color=(30,95,60) if (row,col)==(self.entry.row,self.entry.col) else (25,42,35)
                    pygame.draw.rect(screen,color,(x,y,int(width)-5,40),border_radius=7)
                    rendered=self.small.render(key,True,(200,240,215));screen.blit(rendered,(x+int((width-rendered.get_width())/2),y+8))
        elif self.state in ('media-confirm1','media-confirm2'):
            d=self.plan['device'];y=200
            for line in [self.fit(d['model']+' — '+d['path']),
                         'Série: '+(d['serial'] or 'não informada'),
                         f"Capacidade: {d['bytes']/10**9:.1f} GB — {self.plan['kind']}",
                         'A mídia Xbox terá acesso de escrita a este disco.',
                         'Formatar ou instalar dentro do Xbox altera seus dados reais.',
                         'Os demais discos continuam protegidos. O pendrive está excluído.',
                         'Segure LT + RT + Start OU F10 para confirmar.',
                         'Solte os botões antes de confirmar novamente.',
                         'Esc / B: cancelar sem liberar acesso.']:
                y=self.text(line,y,font=self.small)
        elif self.state in ('live-boot-confirm1','live-boot-confirm2'):
            d=self.plan['device'];y=200
            for line in [d['model'],d['path'],f"Capacidade: {d['bytes']/10**9:.1f} GB",
                         self.fit(self.plan['boot']['message']),
                         'Somente o boot/sistema X-Revive será preparado neste HDD.',
                         'FATX, dashboards, aplicativos e jogos serão preservados.',
                         'Essa escolha grava no HDD. Apenas LIVE não grava nele.',
                         'Segure LT + RT + Start OU F10 para confirmar.',
                         'Solte os botões antes da segunda confirmação.',
                         'Esc / B: voltar sem preparar.']:
                y=self.text(line,y)
        elif self.state in ('confirm1','confirm2'):
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
            elapsed=int(self.status.get('elapsed',time.monotonic()-self.pending_since))
            since=int(time.monotonic()-self.last_response)
            self.text(f'Tempo: {elapsed//60:02}:{elapsed%60:02}  •  '+('Serviço respondendo' if since<6 else f'Sem resposta do serviço há {since}s'),400,font=self.small)
            idle=int(self.status.get('idle_seconds',0))
            if idle>=20:self.text(f'Etapa sem nova atualização há {idle}s. Consulte os detalhes.',435,(235,195,110),self.small)
            if self.details:
                y=475
                for item in self.status.get('history',[])[-4:]:y=self.text(self.fit(str(item['elapsed'])+'s — '+item['message'],font=self.small),y,font=self.small)
            else:self.text('F1 / X: detalhes   •   Esc / B: cancelar quando disponível',490,font=self.small)
        else:
            options=self.options();start=max(0,self.selected-6);y=200
            for index in range(start,min(len(options),start+8)):
                if index==self.selected:pygame.draw.rect(screen,(30,70,49),(205,y-4,1030,42),border_radius=8)
                self.text(self.fit(options[index]),y,(160,255,195) if index==self.selected else (210,220,216));y+=48
            if self.state=='complete' and self.task=='install':self.text('Remova o pendrive antes de reiniciar.',y+20,(130,245,175),self.small)
            if self.state=='complete' and self.task=='verify':
                result=self.status.get('result') or {}
                self.text(f"Conferidos: {result.get('checked',0)} — alterados: {result.get('modified',0)} — ausentes: {result.get('missing',0)}",y+20,font=self.small)
                self.text('Configurações e atualizações podem mudar arquivos. Nada foi restaurado.',y+55,font=self.small)
        if self.state in ('sources','sandbox-sources'):
            self.text('Firmware: XREVIVE / X-Revive / firmware / xbox',450,font=self.small)
            self.text('BIOS e MCPX obrigatórios • EEPROM opcional',485,font=self.small)
        if self.state=='sandbox-sources':
            self.text('Protegido: alterações temporárias.' if self.live_access=='protected' else 'Escrita: somente no HDD escolhido após duas confirmações.',570,font=self.small)
        if self.state=='media-disks':
            self.text('Protegido: nada será gravado no HDD físico.' if self.live_access=='protected' else 'Escrita: escolha com atenção o disco para instalação/manutenção.',590,font=self.small,x=40)
        if self.state=='welcome' and self.boot.get('safe_live'):
            self.text('LIVE SEGURO: discos internos protegidos contra gravação.',440,(130,245,175),self.small)
            self.text('A mídia usa um HDD virtual. Nenhum disco físico será selecionado.',480,font=self.small)
        if self.state=='wifi':
            info=self.wireless.get('connections',[])
            label=('Conectado: '+info[0]['ssid']+' — '+', '.join(info[0]['addresses'])) if info else self.wireless.get('message','')
            self.text(self.fit(label,font=self.small),575,(130,245,175),self.small,x=40)
        if self.state=='sandbox-images':
            self.text('Imagens em pacotes e subpastas. O formato será verificado ao escolher.',575,font=self.small,x=40)
        if self.state=='live-choice':
            d=self.plan['device']
            self.text(f"{d['model']} — {d['bytes']/10**9:.1f} GB — {d['path']}",425,font=self.small)
            self.text('LIVE: alterações na RAM (até 512 MiB), perdidas ao desligar.',465,font=self.small)
            self.text('HDD FATX nativo ou híbrido são aceitos; UEFI não impede o LIVE.',500,font=self.small)
            self.text('Firmware: XREVIVE / X-Revive / firmware / xbox. Sem baixar apps.',535,font=self.small)
        if self.state=='live-disks':
            self.text('Somente HDD Xbox FATX reconhecido pode iniciar. O USB está excluído.',590,font=self.small,x=40)
        if self.message:
            words=self.message.split();lines=['']
            for word in words:
                if self.small.size(lines[-1]+' '+word)[0]>1190 and len(lines)<2:lines.append('')
                lines[-1]=(lines[-1]+' '+word).strip()
            self.text('\n'.join(self.fit(line,1190,self.small) for line in lines),615,(255,125,110),self.small,x=40)
        if active:
            # Indeterminate activity is independent of percentage and transport.
            y=350 if self.state=='progress' else 650
            if self.state!='progress':pygame.draw.rect(screen,(38,52,46),(220,y,840,8),border_radius=4)
            x=220+int((time.monotonic()*210)%740)
            pygame.draw.rect(screen,(175,255,210),(x,y,100,8 if self.state!='progress' else 18),border_radius=4)
        if 'control' in self.calls.pending and self.state!='progress':
            self.text('Processando sua escolha... '+str(int(time.monotonic()-self.pending_since))+'s',600,font=self.small)
        footer=('Aguarde a configuração da rede Wi-Fi.' if self.state=='progress' and self.task.startswith('wifi-') else
                'Operação em andamento — aguarde a conclusão.' if self.state=='progress' else
                'Digital: navegar  A: digitar  X: apagar  B: voltar  •  Teclado físico: digitar / Enter: conectar' if self.state=='wifi-password' else
                '↑ ↓ / Digital: navegar     Enter / A: escolher     Esc / B: voltar')
        self.text(footer,675,(135,160,145),self.small,x=40)
        pygame.display.flip()

    def run(self):
        clock=pygame.time.Clock()
        while self.running:
            try:
                self.calls.poll()
                if self.state=='loading' and self.loaded is not None:
                    if 'error' in self.loaded:self.go('error');self.message=self.loaded['error']
                    else:self.boot=self.loaded;self.go('welcome')
                for event in pygame.event.get():self.event(event)
                now=time.monotonic()
                if 'control' not in self.calls.pending and self.state in ('live-boot-confirm1','live-boot-confirm2') and self.confirm.update(self.combo(),now):
                    step=1 if self.state=='live-boot-confirm1' else 2
                    def confirmed(_,step=step):
                        if step==1:self.go('live-boot-confirm2')
                        else:self.start_task('live-boot-prepare',token=self.plan['token'])
                    self.call('live-boot-confirm',confirmed,token=self.plan['token'],step=step)
                if 'control' not in self.calls.pending and self.state in ('media-confirm1','media-confirm2') and self.confirm.update(self.combo(),now):
                    step=1 if self.state=='media-confirm1' else 2
                    def confirmed(_,step=step):
                        if step==1:self.go('media-confirm2')
                        else:self.start_task('media-start',token=self.plan['token'])
                    self.call('media-confirm',confirmed,token=self.plan['token'],step=step)
                if 'control' not in self.calls.pending and self.state in ('confirm1','confirm2') and self.confirm.update(self.combo(),now):
                    step=1 if self.state=='confirm1' else 2
                    def confirmed(_,step=step):
                        if step==1:self.go('confirm2')
                        else:self.start_task('install',token=self.plan['token'])
                    self.call('confirm',confirmed,token=self.plan['token'],step=step)
                if self.state=='progress' and self.task_ack and now-self.last_poll>.5 and 'control' not in self.calls.pending:
                    self.calls.submit('status','status',self.receive_status,self.call_error);self.last_poll=now
                self.draw();clock.tick(30)
            except (ValueError,OSError) as exc:self.message=str(exc);self.draw();clock.tick(10)

    def receive_status(self,status):
        self.last_response=time.monotonic()
        if status.get('job_id')!=self.operation_id:
            if not status.get('busy'):
                self.go('error');self.message='O serviço não confirmou o início da operação. Volte ao menu e tente novamente.'
            return
        self.status=status
        if status['busy']:return
        if status.get('cancelled'):self.go('welcome');self.message=status['message']
        elif status.get('error'):
            self.go('wifi' if self.task.startswith('wifi-') else 'media-disks' if self.task in ('sandbox-start','media-start') else 'error');self.message=status['error']
        elif self.task.startswith('wifi-'):self.wireless=status.get('result') or {};self.go('wifi')
        elif self.task=='prepare':self.pick_disk('install')
        elif self.task in ('live-start','sandbox-start','media-start'):
            self.task_ack=False;self.call('live-launch',lambda _:self.go('live-starting'))
        elif self.task=='live-boot-prepare':
            def ready(plan):
                self.plan=plan;self.go('live-choice');self.message='Boot preparado. Você pode iniciar em LIVE ou reiniciar pelo HDD.'
            self.task_ack=False;self.call('live-plan',ready,target=self.target)
        else:self.go('complete')


if __name__=='__main__':UI().run()
