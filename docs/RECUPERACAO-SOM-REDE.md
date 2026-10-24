# Reparo de recuperacao, DVD, som e rede — 2026-10-22

## Comportamento solicitado

Segurar R durante o carregamento deve abrir o HeXEn mesmo com HDD FATX.
Eject pela dashboard deve abrir o leitor fisico. Som e rede devem funcionar
no appliance, incluindo FTP entre dashboard Xbox e outro PC na LAN.

## Alteracoes

- Janela de oito segundos no boot consulta R e Start+Back repetidamente,
  incluindo teclados/controles que aparecem durante a janela. Segure R desde
  o inicio ate o HeXEn carregar. O atalho prevalece sobre DVD fisico e FATX;
  a selecao permanece durante reinicios do emulador nesta sessao.
- QMP local monitora `DEVICE_TRAY_MOVED` para ligar eject virtual a
  `console-bandeja.service`. O emulador para antes do eject fisico e retorna
  depois. Eventos de midia ficam suspensos durante essa operacao para evitar
  reinicios concorrentes. HeXEn virtual nao ejeta o leitor fisico.
- Rede do Xemu habilitada explicitamente. Ethernet fisica detectada gera
  backend pcap, preferindo a placa com cabo; `console.service` recebe
  CAP_NET_RAW/CAP_NET_ADMIN para captura/injecao sem executar como root.
  systemd-networkd sobe Ethernet/DHCP no Linux. O Xbox usa seu proprio DHCP
  na dashboard e recebe seu proprio IP da LAN. `libpcap` incluida na imagem.
  Offloads GRO/GSO/TSO/LRO e checksum sao desativados na interface escolhida:
  pcap transporta quadros sem os metadados dessas otimizacoes. Na VM, arquivo
  de 64 KiB ficou vazio antes do ajuste e passou com SHA-256 identico depois.
- Sem Ethernet, usa NAT com TCP 2121 encaminhado para 21 do Xbox. Wi-Fi nao
  e configurado automaticamente; precisa de conectividade do host para sair.
- ALSA inicializada com mixer desmutado e saida selecionada. `audio=auto`
  prefere analogica/USB; `audio=hdmi`, `audio=analog` ou `audio=plughw:0,0`
  em `CONSOLE/config/ports.conf` permitem escolher. Variaveis SDL3 selecionam
  ALSA e seu dispositivo. Nao ha servidor de audio de desktop.
- No desligamento normal, diagnosticos de audio/rede, eventos de bandeja e
  ultimas mensagens do console vao para `CONSOLE/config/diagnostico/`.

## FTP na Ethernet

Ligar cabo ao roteador/switch, deixar a dashboard custom com rede DHCP e FTP
habilitados. No PC, conectar ao IP mostrado pela dashboard, porta 21, usando
as credenciais da propria dashboard. A Microsoft retail nao oferece FTP.
Nao usar o IP do Linux nem `10.0.2.15` nesse modo. O HDD existente nao e
alterado por estes reparos; nenhuma configuracao de dashboard e sobrescrita.

## Verificacao e limites

Testes locais exercitam R e combo, entrada tardia/timeout, recuperacao com FATX,
prioridade sobre DVD fisico, reinicio em recuperacao, configuracao TOML da rede,
selecao de Ethernet/ALSA, decisao de eject e os testes de persistencia anteriores.

Aceitacao fisica pendente: R com o HDD FATX; abrir/fechar bandeja na dashboard;
ouvir jogo/dashboard; conferir IP DHCP; transferir arquivo via FTP e conferir
conteudo depois. Teste virtual nao comprova eventos do leitor ou som fisico.

Validacao virtual realizada: R abriu HeXEn com HDD FATX (captura em
`bancada/validacao-r-rede-som/tela.png`), DHCP atribuiu IP proprio ao Xbox,
FTP listou as unidades e transferiu 4 KiB e 64 KiB com comparacao integral.
ALSA abriu em estado RUNNING; audio capturado contem sinal (pico PCM 7334).
O teste de 64 KiB depende do ajuste de offload acima; nao e benchmark de vazao.
Todos os discos da VM usaram snapshot, sem discos fisicos conectados.

## Imagem final

`cartucho/out/console-xbox.img` (unica imagem mantida em out por pedido do usuario),
3.894.411.264 bytes. SHA-256:
`92dab102c112549152e9d4fd02f459ede5a35c8ceb4abbba96a2d1afee23c113`.

GPT verificada sem erros. Hardware.py extraido do SquashFS identico ao fonte;
ethtool presente. A imagem final foi iniciada novamente em VM: R com FATX,
ALSA em RUNNING, DHCP e offloads desativados automaticamente. Upload/download
FTP de 65.536 bytes com conteudo identico, SHA-256
`7daca2095d0438260fa849183dfc67faa459fdf4936e1bc91eec6b281b27e4c2`,
sem ajustar manualmente a configuracao da imagem. Evidencias em
`bancada/validacao-r-rede-som-final/` (serial, captura e JSON do FTP).
Treze testes locais passaram, incluindo ordem stop/eject/start e retorno
do emulador mesmo se eject falhar. Bootloader de producao nao contem shell de
debug: ela foi habilitada apenas na linha de comando da VM de teste.

## Retorno fisico do usuario apos gravacao

- Atalho R confirmado: iniciou o HeXEn com o HDD FATX.
- Rede obteve IP; usuario considera que aparentemente funcionou. FTP fisico
  ainda nao confirmado neste retorno.
- DVD fisico NAO abre, nem pelo Xemu nem pela dashboard. Eject continua aberto;
  os testes virtuais anteriores nao validaram o funcionamento do leitor real.
- Graficos na GTX 750 continuam impedindo uso adequado; nao tratado como resolvido.
- Som nao foi confirmado neste retorno.
- Manter somente `console-xbox.img` em out; copias anteriores e alias removidos
  apos conferir que a imagem atual e o alias tinham o mesmo SHA-256.

## Referencias tecnicas

- https://raw.githubusercontent.com/xemu-project/xemu/v0.8.138/config_spec.yml
- https://raw.githubusercontent.com/xemu-project/xemu/v0.8.138/ui/xemu-net.c
- https://xemu.app/docs/networking/
- https://xemu.app/docs/ftp/
- https://wiki.libsdl.org/SDL3/SDL_HINT_AUDIO_DRIVER
- https://wiki.libsdl.org/SDL3/SDL_HINT_AUDIO_ALSA_DEFAULT_PLAYBACK_DEVICE
