# Boot X-Revive, animacao Xbox e discos de utilitarios

## Pedido e escopo (2026-10-23)

Graficos e eject fisico validados em bancada na imagem
NVIDIA anterior. Audio e R tambem confirmados; FTP fisico ainda nao testado.
Manter arquitetura e o par de imagens, corrigir splash, incluir OGXbox completo
via G e manter HeXEn via R. Boot normal desejado: logo X-Revive, animacao Xbox,
dashboard atual do HDD. Nenhuma dashboard e imposta por esta alteracao.

## Diagnostico do logo

O tema, PNGs e plugin script ja estavam no initramfs. O log do Plymouth mostrou
que `console=tty3` era classificado como console nao padrao e forcava details
(texto), sem selecionar o renderizador grafico. Com `console=tty0`, a mesma
base exibiu o logo na VM. O GRUB da imagem foi corrigido; `/debug` continua
permitindo diagnostico com texto por escolha explicita.

Evidencia apos a troca de console: `bancada/diagnostico-splash/diagnostico.log`
(carregamento do tema x-revive) e `tela-10.png`. A validacao da entrega inclui o boot UEFI real da VM,
pois o smoke test antigo iniciava o kernel diretamente e nao testava o splash.

## OGXbox e atalhos

ISO fornecida pelo usuario, preservada inteira:

- `OGXBox Cerbios Disc.iso`, 4.699.979.776 bytes.
- SHA-256: `c171bf98ea1655504c148196091ac50046bdbbf64b350f79cf38ec1b0f82d838`.
- Inspecao XDVDFS: 4.359 arquivos e 499 tabelas de diretorio; `default.xbe`
  presente na raiz. Inventario em `cartucho/cache/ogxbox-inventory.json`.

A quarta particao `UTILS` (ext4, 4.864 MiB) guarda `ogxbox.iso`; montagem
somente leitura em `/utils`, fora do squashfs e do toram. CONSOLE permanece
FAT32 e CACHE continua separado. As imagens passam a exigir pendrive >=16 GB.
O hash da ISO tambem integra os metadados do par; o build recusa ISO ausente.

`cartucho/build/build.sh xbox ~/Downloads/xbox-console [caminho/ogxbox.iso]`
usa `cartucho/cache/ogxbox.iso` quando o terceiro argumento e omitido.

Uma unica janela de oito segundos consulta o estado atual de todos os inputs:

- G: OGXbox, inclusive com HDD ja FATX ou ainda novo.
- R ou Start+Back: HeXEn. Se as duas escolhas forem mantidas juntas, prevalece
  a recuperacao HeXEn.
- Sem atalho: dashboard; sem FATX, mantem HeXEn automatico.

O disco selecionado permanece nos restarts da sessao. Eventos do DVD fisico
nao interrompem a sessao de nenhum dos utilitarios; eject virtual nesses modos
nao aciona a bandeja fisica. A logica do leitor no boot normal foi preservada.

## Animacao antes da dashboard

`general.skip_boot_anim=false` fica explicito no xemu. A Cerbios 3.1.0 usa um
XBE externo em `E:\Cerbios\BootAnims\Xbox\BootAnim.xbe`; apenas configurar
o emulador nao cria esse arquivo no HDD. O BootAnim do pacote local da propria
Cerbios foi mantido e a configuracao foi trocada por `STOCK_COLOURS_bootanim.ini`
(verde, camera original, sem wireframe, marca original). E a recriacao fornecida
pela Cerbios; nao e uma troca por BIOS retail da Microsoft.

Antes de abrir o xemu, `bootanim.py` instala/confere apenas os dois arquivos
de animacao no E: FATX. Se existir `E:\Cerbios\cerbios.ini`, ajusta somente
BootAnimPath; nao injeta um INI inteiro, preservando DashPath, DriveSetup e todas
as outras preferencias. Os arquivos substituidos ganham uma copia
`.xrevive.bak` no mesmo diretorio. Arquivos iguais nao sao regravados.

Guardas: hash da BIOS 3.1.0 auditada, assinaturas FATX de C/E, tamanho retail,
recusa de disco/particoes montados, escrita temporaria e leitura de conferencia.
BIOS desconhecida ou HDD nao FATX: nenhuma instalacao automatica. Nao formata,
nao altera setor 0, jogos, saves, dashboard ou BIOS. Somente arquivos Xbox no HDD.
Log: `/run/console/bootanim.log`, salvo em `CONSOLE/config/diagnostico/` no
desligamento normal. Os testes virtuais usam snapshots de todos os discos.

## Verificacao executada

1. Testes de selecao G/R, FATX, prioridade, reinicio, rede/audio/eject e protecao
   da publicacao; guardas e backups do instalador de animacao.
2. Build do par, GPT com quatro particoes, identidade da ISO inteira nas duas.
3. VM: logo grafico, R abre HeXEn, G abre OGXbox, boot normal mostra animacao
   verde e dashboard; capturar telas e logs. Som permanece ativo.
4. Bancada: confirmar logo e sequencia visual na GTX 750; depois FTP fisico.

Entrega: `20261023T032759Z-c17c19a291c8`, fontes
`c17c19a291c847f5235653f67942fdffe4bd059bad3fcaefb3a8a8f8e223806e`.
Kernel `6.12.113+deb13-amd64`, NVIDIA `550.163.01-2`.

- 21 testes passaram (`cartucho/cache/testes-logo-ogxbox.log`); sintaxe shell
  conferida. Incluem escolha G/R, preservacao de dashboard/INI, backups,
  idempotencia e recusa de HDD nao FATX/BIOS desconhecida, alem das regressoes.
- GPT das duas imagens com quatro particoes verificada. As duas tem
  8.994.684.928 bytes, mesmo build/fontes/ISO. Somente duas `.img` em out.
- Universal com R: logo, animacao verde e menu HeXEn; G: menu OGXbox.
- NVIDIA com G: logo, animacao verde e menu OGXbox. A ISO foi lida inteira
  dentro da VM; SHA-256 igual ao original. Veja `media-check.log`.
- NVIDIA por UEFI/GRUB, sem linha de comando de debug e sem atalho: logo nas
  capturas de 25/40 segundos e dashboard UnleashX do HDD aos 90 segundos.
  A animacao verde esta registrada nas capturas dos boots dos utilitarios;
  as capturas UEFI espacadas nao registraram seu trecho intermediario.
- Audio WAV com sinal em todos os quatro cenarios. DHCP apareceu nos menus
  dos utilitarios. O dashboard do HDD virtual exibiu IP 0.0.0.0; sua configuracao
  de rede nao foi alterada. Nenhum teste FTP fisico foi realizado.

Evidencias em `bancada/validacao-boot/`: `universal-r`, `universal-g`, `nvidia-g`
e `uefi-nvidia`, com telas PNG/PPM, comandos QEMU, WAV, resultados e logs.
As VMs usaram snapshots, sem escrita nas imagens oficiais ou no HDD original
de bancada virtual. A validacao nova e virtual (virtio/software), sem passagem
da GTX 750 fisica; a confirmacao do fluxo visual no hardware continua pendente.

Checksums das imagens:

```
2a7e2c18b6447bc3ce760a4e3aa96dc36390633b20226435a39cdfde8de79d58  console-xbox-universal.img
d414d08f2cc991f44fe366b1194347198e03ad7906984951f8731528841db15d  console-xbox-nvidia.img
```

O par anterior validado em bancada foi preservado fora de out em
`cartucho/cache/baseline-dual-funcional-20261023/`.

Referencias primarias:
- xemu 0.8.138, configuracao: https://github.com/xemu-project/xemu/blob/v0.8.138/config_spec.yml
- Cerbios: pacote local `~/Downloads/Cerbios.zip`, release V3.1.0 Beta,
  `Cerbios/cerbios.ini` e `Cerbios/BootAnims/Xbox/STOCK_COLOURS_bootanim.ini`.
- Plymouth (device manager): https://gitlab.freedesktop.org/plymouth/plymouth/-/blob/main/src/libply-splash-core/ply-device-manager.c
