# Validação do instalador X-Revive — estágio 2

> Entrega posterior com atualizador Xemu: [validação 730645d7124c](VALIDACAO-ATUALIZADOR-XEMU.md). As evidências d32d6 abaixo permanecem como histórico do estágio 2.
## Identificação

Entrega local publicada: `20261024T051417Z-d32d6edfb5b9`.
Fontes: `d32d6edfb5b9ee108df2534630d680f78d928523660cd3359e3a8eaa511cbb39`.
A revisão cc1918 também concluiu instalação completa por controle. O ajuste
final d32d6 mascara a carga global NVIDIA do pacote Debian, mantendo a seleção
por GPU. `GENERIC_VIDEO_PASS` foi obtido no boot virtio dessa revisão.
Catálogo normalizado: 98.996 arquivos, 4.665.442.926 bytes de conteúdo,
104 ZIPs e três arquivos auxiliares fixados em lock. Dez dashboards.
Manifesto SHA256:
`3674a346a220e417c4ccb69aa86a0918b686e57e5e5a32a42c19643f4e289470`.

A baseline anterior f613cf12 continua preservada. Não há escrita em discos
físicos do host nesta validação. O diretório não possui repositório Git
inicializado; não existe branch/commit local a citar.

## Testes automatizados

`cartucho/cache/testes-estagio2-entrega.log`: 46 testes passaram. Abrangem limites do
FATX, diretórios com mais de 512 entradas, escrita limitada à partição,
configuração substituída sem nova alocação, confirmação dupla com soltura,
catálogo inválido, destino trocado/redimensionado, mídia de origem bloqueada,
partição filha montada, divisão F/G e publicação de uma IMG preservando baseline.
A relocação UIX recusa binário desconhecido e altera somente nove bytes no
executável com hash conhecido. Sintaxe Python e shell conferida.

## Evidência inicial em arquivos e VM

Primeiro protótipo: `20261024T015957Z-33ef580d1131`, não publicado. Algumas
correções foram aplicadas apenas à RAM da VM antes de consolidar as fontes:
hierarquia do lsblk, plano de espaço rápido e montagem inicial do instalador.
Esses ensaios não constituem validação da imagem consolidada sem intervenções.

- Instalação pela interface com teclado em SSD virtual de 64 GiB, com duas
  confirmações separadas e conferência de todos os arquivos antes do boot.
- Boot UEFI desse SSD sozinho, sem pendrive, abrindo XBMC4Gamers 2.3.
- Layout: prefixo Xbox de aproximadamente 54,62 GiB, excedendo o protótipo
  anterior de 16 GiB; UnleashX reconheceu mais de 42 GB livres em F:.
- FTP ida/volta de 262.144 bytes com SHA256
  `2312394bd99545d9de131c24efb781e765ac1aec243f2ed9347597a793a415e9`.
  Ensaio usa NAT dentro da VM, sem provar a rede física do novo build.
- Start+Back não abriu o menu do Xemu; Start+digital para cima abriu.
- As dez dashboards chegaram à interface ou boas-vindas: XBMC4Gamers,
  XBMC4Xbox, Emustation, User Interface X, UIX Lite, Microsoft 5960,
  EvolutionX, Avalaunch e as duas variantes UnleashX. Capturas `matrix-*.png`.
- Desligamento Linux mostrou logo e `Desligando...`; captura
  `ssd-boot/poweroff-008.png`. Após encerrar, o hash dos primeiros 16 MiB
  da área SYSTEM e a tabela híbrida continuaram válidos (`integrity-after.json`).
- UIX Lite: mover apenas o executável carregava recursos Microsoft. A versão
  relocada para recursos em F: abriu com Launcher; C: Microsoft ficou intacto.

Evidências: `bancada/validacao-estagio2/`, capturas em `ssd-boot/`, logs
`cartucho/cache/installed-ssd-boot.log` e `dashboard-matrix.log`.

O escritor FATX também gravou/leu integralmente 98.994 arquivos do primeiro
catálogo em um arquivo de 64 GiB, em 213 segundos. Uma leitura independente com
libfatx/pyfatx confirmou carregador, executáveis e 1.183 trainers, incluindo
entradas além da posição 512. Arquivos:
`cartucho/cache/rocky5/qa/native-filesystem.json` e
`cartucho/cache/fatx-independent-read.log`.

## Instalação completa e manutenção do candidato bbae0462

`controller-final-install.log` + `controller-final-install-resumed.log`:
instalação por controle passou com `verified=true`, 104 pacotes e 98.996
arquivos. Cancelar não escreveu; segurar a combinação não confirmou duas vezes.
A leitura do terminal de QA precisou ser sincronizada com flock após duas
consultas concorrentes; o processo de instalação seguiu independente e nenhum
código do produto foi corrigido na RAM desse ensaio.

`recovery-bbae-boot.log`: R abriu manutenção no SSD sem pendrive.
`maintenance-bbae-ui.log`: teclado navegou pelo reparo UEFI e pela troca de
padrão para UnleashX. Hashes dos executáveis C/E/F, tabela híbrida e os 1.183
trainers foram preservados; a troca alterou Dashloader.ini. Capturas em
`bancada/validacao-estagio2-final/ssd-boot/maintenance-*.png`.

## Regressões comprovadas

O SSD bbae reiniciou em UnleashX após a escolha pelo menu. O ensaio de FTP e
bandeja passou com arquivo de ida/volta conferido por SHA256 e quatro transições
`[true,false,true,false]`, sem reiniciar o emulador, inclusive após notificação
atrasada de mídia. SYSTEM e tabela híbrida foram preservados.
`bancada/validacao-estagio2-final/ssd-boot/postinstall-regression.log`.

`SITE SHUTDOWN`, tratado pela dashboard, emitiu QMP `guest=true`,
`reason=guest-shutdown` e encerrou a VM Linux. O arquivo FTP permaneceu íntegro
após desligar, assim como a área SYSTEM e o boot híbrido;
`persistence-after-shutdown.json` e `serial.log` nessa mesma pasta.

Na revisão cc1918, a instalação completa por controle passou; a tela de
encerramento manteve `Desligando...` até o último quadro capturado
(`bancada/validacao-estagio2-cc1918/poweroff-027.png`). As tentativas de carga
NVIDIA persistiram no log por causa de `/etc/modules-load.d/nvidia.conf`,
criado pelas alternativas do Debian. A revisão d32d6 mascara esse arquivo;
a checagem inicial na VM confirmou ausência de NVRM e presença dos módulos
NVIDIA, Nouveau, AMD e Intel no initrd.

## Entrega final d32d6

A instalação completa por controle passou com `verified=true`, 104 pacotes e
98.996 arquivos; `cartucho/cache/controller-entrega-install.log`.
`cartucho/cache/installed-entrega-check.log` confirmou boot UEFI do SSD sem USB,
XBMC4Gamers de fábrica, binário esperado, animação presente e stream ALSA RUNNING.
A checagem de vídeo também passou no SSD sem mensagens NVRM.

`cartucho/cache/recovery-entrega-boot.log`: R abriu a manutenção própria no SSD.
Após desligar pelo menu com teclado, a tabela híbrida e o hash dos primeiros
16 MiB de SYSTEM permaneceram íntegros; o padrão continuou XBMC4Gamers.
Evidência: `bancada/validacao-estagio2-entrega/ssd-boot/integrity-after.json`.
Capturas: `xbox-startup-04.png`, `recovery-ready.png` e `poweroff-008.png`
nessa mesma pasta. Não houve correção de código em RAM nesse teste final.

A IMG publicada não contém `/debug`; apenas cópias de QA recebem esse arquivo.
O payload não contém arquivos ISO. Firmware pessoal segue privado.
`out` contém uma única IMG. As três imagens anteriores foram preservadas em
`cartucho/cache/retired-before-20261024T051417Z-d32d6edfb5b9/`, além das
baselines anteriores. As VMs e o servidor HTTP temporário de QA foram encerrados.

- Imagem: `cartucho/out/console-xbox-installer.img`.
- Tamanho: 10.068.426.752 bytes (9,38 GiB); pendrive de pelo menos 16 GB.
- SHA256: `6d0bdeeb6c99e7e982592c72f030595697816af2ce763af606031fbd4340275b`.
- Manifesto: `cartucho/out/release.json`, acompanhado de checksum, metadados
  e lista de pacotes Debian.

## Próximo marco

Testar a entrega identificada acima na GTX750: instalar pelo USB no SSD escolhido,
reiniciar sem USB, conferir logo/animação, R manutenção, menu Start+digital para
cima, áudio, FTP e eject físico. A instalação é limpa e apaga o destino confirmado.
Compatibilidade no Xbox original modchipado é um ensaio físico separado.
Antes de publicação comunitária: revisar licenças/artefatos privados e preparar
somente os fontes autorizados; GitHub ainda não foi publicado.

## Limites de evidência

Boot de dashboard não é teste de cada jogo, aplicativo, tema ou emulador.
Não foram adicionados jogos/ROMs comerciais. GPU NVIDIA 550 e Mesa na mesma
mídia exigem teste físico na GTX750 e em outras famílias de GPU. O relato do
usuário de áudio, FTP e eject físico da etapa anterior permanece válido como
relato daquela entrega; não equivale a novo ensaio físico deste candidato.
Discos híbridos em Xbox original modchipado exigem validação física própria.
O formato atual é MBR abaixo de 2 TiB e setores lógicos de 512 bytes.
