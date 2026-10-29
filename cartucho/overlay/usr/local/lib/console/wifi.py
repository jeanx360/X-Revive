"""Wi-Fi-only D-Bus client. Volatile credentials never enter argv or disk."""
import hashlib
import time
import uuid

BUS='org.freedesktop.NetworkManager'
ROOT='/org/freedesktop/NetworkManager'
PROPS='org.freedesktop.DBus.Properties'
DEVICE=BUS+'.Device'
WIRELESS=DEVICE+'.Wireless'
AP=BUS+'.AccessPoint'


def security(flags,wpa,rsn):
    auth=wpa|rsn
    if auth&0x200 or auth&0x2000:return 'Corporativa',None,True
    if auth&0x100:return 'WPA/WPA2/WPA3','wpa-psk',True
    if auth&0x400:return 'WPA3','sae',True
    if auth&0x800:return 'OWE','owe',False
    if flags&1:return 'WEP',None,True
    return 'Aberta','',False


def display(text):return ''.join(c if c.isprintable() else ' ' for c in str(text))


class Backend:
    def __init__(self):
        import dbus
        self.d=dbus;self.bus=dbus.SystemBus()
        self.manager=self.bus.get_object(BUS,ROOT)
        self.nm=dbus.Interface(self.manager,BUS)

    def properties(self,path,interface):
        return self.d.Interface(self.bus.get_object(BUS,path),PROPS).GetAll(interface,timeout=4)

    def devices(self):
        rows=[]
        for path in self.nm.GetDevices(timeout=4):
            item=self.properties(path,DEVICE)
            if int(item['DeviceType'])==2:rows.append((str(path),item))
        return rows

    def status(self):
        state=self.properties(ROOT,BUS);devices=self.devices();active=[]
        for path,props in devices:
            if int(props['State'])!=100:continue
            ap=str(self.properties(path,WIRELESS).get('ActiveAccessPoint','/'))
            if ap=='/':continue
            data=self.properties(ap,AP);addresses=[];ip=str(props.get('Ip4Config','/'))
            if ip!='/':addresses=[str(a['address']) for a in self.properties(ip,BUS+'.IP4Config').get('AddressData',[])]
            active.append(dict(interface=str(props['Interface']),ssid=display(bytes(data['Ssid']).decode('utf8','replace')),
                               signal=int(data['Strength']),addresses=addresses))
        blocked=not bool(state['WirelessHardwareEnabled'])
        return dict(available=bool(devices),enabled=bool(state['WirelessEnabled']),blocked=blocked,
                    connected=bool(active),connections=active,
                    message=('Nenhum adaptador Wi-Fi compatível encontrado.' if not devices else
                             'Wi-Fi bloqueado pelo hardware.' if blocked else
                             'Wi-Fi conectado.' if active else 'Selecione uma rede Wi-Fi.'))

    def access_points(self):
        rows=[]
        for path,props in self.devices():
            wireless=self.d.Interface(self.bus.get_object(BUS,path),WIRELESS)
            current=str(self.properties(path,WIRELESS).get('ActiveAccessPoint','/'))
            for apath in wireless.GetAccessPoints(timeout=4):
                data=self.properties(apath,AP);ssid=bytes(data['Ssid'])
                if not ssid:continue
                label,key,secret=security(int(data['Flags']),int(data['WpaFlags']),int(data['RsnFlags']))
                identifier=hashlib.sha256((path+'|'+str(apath)).encode()).hexdigest()
                rows.append(dict(id=identifier,ssid=display(ssid.decode('utf8','replace')),signal=int(data['Strength']),
                                 security=label,supported=key is not None,password=secret,connected=str(apath)==current,
                                 _ssid=ssid,_device=path,_ap=str(apath),_key=key))
        unique={}
        for row in sorted(rows,key=lambda r:(not r['connected'],-r['signal'])):
            unique.setdefault((row['_ssid'],row['security']),row)
        return list(unique.values())

    def scan(self):
        state=self.status()
        if state['blocked'] or not state['available']:return dict(networks=[],**state)
        self.d.Interface(self.manager,PROPS).Set(BUS,'WirelessEnabled',self.d.Boolean(True),timeout=4)
        pending=[]
        for path,props in self.devices():
            before=int(self.properties(path,WIRELESS).get('LastScan',-1))
            pending.append((path,before))
            try:
                self.d.Interface(self.bus.get_object(BUS,path),WIRELESS).RequestScan(self.d.Dictionary({},signature='sv'),timeout=4)
            except self.d.DBusException:pass  # Also await NM's scan already in progress.
        deadline=time.monotonic()+12
        while pending and time.monotonic()<deadline:
            pending=[(path,before) for path,before in pending if int(self.properties(path,WIRELESS).get('LastScan',-1))<=before]
            if pending:time.sleep(.3)
        rows=sorted(self.access_points(),key=lambda r:(not r['connected'],-r['signal'],r['ssid'].casefold()))
        state=self.status()
        if not rows and state['available'] and not state['blocked']:
            state['message']='Nenhuma rede encontrada. Atualize a lista ou confira o sinal.'
        return dict(networks=[{k:v for k,v in r.items() if not k.startswith('_')} for r in rows],**state)

    def connect(self,identity,password):
        row=next((r for r in self.access_points() if r['id']==identity),None)
        if row is None:raise ValueError('A rede não está mais disponível. Atualize a lista.')
        if not row['supported']:raise ValueError('Esta beta suporta redes abertas e WPA/WPA2/WPA3 pessoais; esta rede exige outro método.')
        if not isinstance(password,str) or len(password)>256:raise ValueError('Senha Wi-Fi inválida.')
        if row['password'] and not password:raise ValueError('Informe a senha desta rede.')
        d=self.d
        settings={
            'connection':{'id':'X-Revive Wi-Fi','uuid':str(uuid.uuid4()),'type':'802-11-wireless','autoconnect':d.Boolean(False)},
            '802-11-wireless':{'ssid':d.ByteArray(row['_ssid']),'mode':'infrastructure'},
            'ipv4':{'method':'auto','route-metric':d.Int64(600)},'ipv6':{'method':'auto'}}
        if row['_key']:
            settings['802-11-wireless-security']={'key-mgmt':row['_key']}
            if row['password']:settings['802-11-wireless-security']['psk']=password
        try:
            _,active,_=self.nm.AddAndActivateConnection2(d.Dictionary(settings,signature='sa{sv}'),
                d.ObjectPath(row['_device']),d.ObjectPath(row['_ap']),d.Dictionary({'persist':'volatile'},signature='sv'),timeout=10)
            deadline=time.monotonic()+35
            while time.monotonic()<deadline:
                state=self.properties(row['_device'],DEVICE)
                if int(state['State'])==100 and str(state.get('ActiveConnection'))==str(active):return self.scan()
                if int(state['State'])==120:break
                time.sleep(.5)
            # Stop a timed-out attempt, so it cannot keep retrying the old
            # password while the user edits it or selects another network.
            self.nm.DeactivateConnection(active,timeout=4)
        except d.DBusException:
            raise ValueError('Não foi possível conectar. Confira a senha, o sinal e a segurança da rede.') from None
        raise ValueError('A conexão não foi concluída. Confira a senha e tente novamente.')

    def disconnect(self):
        for path,props in self.devices():
            if int(props['State'])>30:self.d.Interface(self.bus.get_object(BUS,path),DEVICE).Disconnect(timeout=5)
        return self.scan()


def call(action,**args):
    try:return getattr(Backend(),action)(**args)
    except (ImportError,ModuleNotFoundError):raise ValueError('Suporte Wi-Fi indisponível nesta imagem.') from None
    except ValueError:raise
    except Exception:raise ValueError('Wi-Fi indisponível. Verifique o adaptador e tente atualizar as redes.') from None
