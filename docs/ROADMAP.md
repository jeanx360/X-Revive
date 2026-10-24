> Histórico de pesquisa e bancada. O planejamento atual está em [ROADMAP-BETA](ROADMAP-BETA.md).

# Roadmap: melhorias combinadas

> Atualizador Xemu autorizado em 24/10: [especificação e operação](ATUALIZADOR-XEMU.md).

> Registro da etapa anterior. A direção atual é o [instalador próprio, estágio 2](ESTAGIO2-INSTALADOR.md), com uma única IMG de instalação.
Atualizacao 2026-10-23: o [roadmap atual](ROADMAP-2026-10-23.md) registra o
FTP confirmado pelo usuario, o refinamento de R/G, a correcao da dashboard
e a terceira variante standalone experimental. As restricoes antigas de duas
imagens/HDD puro continuam como padrao USB; standalone e uma excecao opt-in.

Registro das melhorias discutidas (2026-10-21), em ordem de prioridade.
O que já foi feito está em VALIDACOES.md.

## 1. Desempenho e fidelidade (Xbox)

| # | Melhoria | Situação | Notas |
|---|----------|----------|-------|
| 1.1 | **Cache de shaders persistente em disco** | **feito** | 3ª partição `CACHE` (ext4). `XDG_DATA_HOME` por máquina (fingerprint da HAL) → xemu grava em `/var/cache/console/<fp>/xdg/xemu/xemu/`. Montada rw no boot por `prepare.sh`; não vai para a RAM. Validado na VM (pasta `shaders` persiste após desligar). |
| 1.2 | **CPU sempre no máximo** | **feito** | `probe.sh` emite `cpu_governor` (performance em desktop/console, schedutil em notebook pelo chassi SMBIOS) e `cpu_isolate`. `prepare.sh` aplica o governador; `run.sh` fixa o xemu com `taskset` deixando a CPU 0 para o sistema (quando ≥6 threads). Só vale onde há cpufreq (não na VM). |
| 1.3 | **Wayland direto (sem XWayland)** | **feito** | `run.sh` usa `SDL_VIDEODRIVER=wayland` quando o cage e as libs estão presentes (precisou de `libwayland-cursor0`). Queda segura para X11 se o init falhar em <5 s. Validado na VM: nenhum Xwayland sobe. |
| 1.4 | **Variante NVIDIA proprietária** | confirmada na bancada (2026-10-23) | Usuario confirmou imagem perfeita na GTX 750 com proprietario Debian 550.163.01-2. Build mantem sempre universal + NVIDIA. Ver `IMAGENS-UNIVERSAL-NVIDIA.md`. |
| 1.5 | **Escala de resolução por jogo** | a fazer | `surface_scale` até 4K. Alguns jogos dão defeito em escala alta, então precisa de exceção por jogo. |
| 1.6 | **Opção 128 MB / cartucho "Ultimate Xbox"** | **parcial** | `ram=128` no `ports.conf` → `configure.sh` → `mem_limit='128'` → xemu `-m 128` (confirmado por log na VM). Mas o dashboard ainda vê 64 MB: o kernel/BIOS precisa ser 128-aware para expor a RAM extra ao software. Falta validar na bancada com título/config 128 MB. Padrão 64. |
| 1.7 | Patches de 60 fps / widescreen | documentar | São patches da comunidade, por jogo. O console só precisa rodá-los (via dashboard/HDD). |

Fixar a versão do xemu continua valendo: atualizar = trocar o número em `versions.env` e gerar a imagem de novo.
KVM nao e suportado para a emulacao Xbox. A excecao atual a usar o executavel
oficial e o patch SMC minimo sobre a mesma versao fixada, com identidade e
proveniencia explicitas: [XEMU-SMC-TRAY.md](XEMU-SMC-TRAY.md).

## 2. Console (comportamento original)

| # | Melhoria | Situação | Notas |
|---|----------|----------|-------|
| 2.1 | **Animação de boot (logo X-Revive → animação → dashboard)** | implementada e validada em VM; falta bancada | BootAnim da Cerbios com cores stock; instalacao limitada aos arquivos Xbox no FATX, backup dos substituidos, sem troca de dashboard. Ver `BOOT-LOGO-OGXBOX.md`. |
| 2.2 | `cerbios.ini` (UDMA, caminhos) | aguarda arquivo | Vem no mesmo pacote. |
| 2.3 | Xored Mini (trainers) | pendente | A libfatx falha com mais de 512 entradas num diretório. Instalar pelo Extras Disc/FTP, ou corrigir a libfatx. |
| 2.4 | Aviso do QEMU "probing guessed raw" no HDD | investigar | Escritas no setor 0 ficam restritas. Até agora não afetou nada. |

## 3. Controles

| # | Melhoria | Situação | Notas |
|---|----------|----------|-------|
| 3.1 | USB com fio (Duke, 360, One, Series) | feito | `xpad` |
| 3.2 | Dongle sem fio original | feito, sem teste físico | `xone` 0.5.8. Firmware via `cartucho/tools/firmware-dongle.sh` (termos da Microsoft). |
| 3.3 | Controle na VM | feito | Passthrough automático. Uma vez: `sudo bancada/permitir-controle.sh`. |
| 3.4 | Bluetooth (One/Series) | a fazer | `xpadneo`, pareamento sem tela: 60 s após ligar. |
| 3.5 | Porta fixa por controle | a fazer | Porta física 1 da carcaça = jogador 1. |

## 4. Leitor de DVD: discos originais de Xbox

Situação atual: troca de disco e Eject funcionam (testado na VM). DVD-R gravado com XISO deve ler em leitor comum.
Os leitores Kreon conhecidos são raros, caros e quase todos IDE.

**Objetivo:** firmware patchado para os leitores SATA do usuário (LG GH24NS25, HL-DT-ST GHA2N), no modelo "extrair firmware → patch → regravar".

**Simplificação-chave:** o xemu não confere os setores de segurança (SS); ele emula o leitor e responde "autêntico". Basta o leitor **ler o disco inteiro além do tamanho declarado** (a partição do jogo depois da de vídeo). Não é preciso reimplementar o Kreon inteiro.

Fases (cada uma com "para ou segue"):

0. **Identificar** chipset/CPU de cada leitor (firmware oficial da LG, revisão atual, fotos da placa) e se o firmware é assinado.
1. **Engenharia reversa do Kreon:** diff entre o firmware original do GDR-8163B e o Kreon. Mapear os comandos novos e os limites removidos.
2. **Engenharia reversa dos leitores alvo:** despachante SCSI, checagem de LBA, leitura da PFI.
3. **Teste sem gravar:** com um disco original, sondar por `sg_raw` comandos de fabricante ou debug que já leiam além do limite.
4. **Patch e gravação** no leitor menos usado, com backup do original e modo de recuperação conhecido. O usuário aceitou o risco de brick (2026-10-21).
5. **Integração:** destrave automático no `prepare.sh` e no udev quando o disco entra.

### Descobertas da pesquisa (2026-10-21)

- **O "custom" do GDR-8163B não é Kreon.** É o firmware original do leitor do Xbox (Hitachi-LG GDR-8050L), gravado no 8163B porque o hardware é igual: transforma o leitor de PC em leitor interno de Xbox. Kreon é para Samsung (SH-D162C/D, SH-D163A/B, quase todos IDE).
- **Protocolo do leitor do Xbox** (gist do Ernegien, PR #1659 do xemu):
  - `READ DVD STRUCTURE` 0xAD, formato 0xFE, devolve o layout de 1636 bytes com a tabela de desafios.
  - `MODE SELECT`/`MODE SENSE` página 0x3E fazem os desafios.
  - No último desafio, partição = 1, e o leitor passa a endereçar a partição do jogo.
  - O xemu não precisa de nada disso.
- **OmniDrive** (RibShark, código aberto, fev/2026, github.com/RibShark/OmniDrive) já é o modelo "firmware original → patch → regravar" para Hitachi-LG com **MediaTek MT1959** (leitores Blu-ray), e lê XGD1. O patch de Xbox (`EnableXGD()` em `src/main.c`, cerca de 25 linhas):
  1. Depois da leitura do TOC de disco de duas camadas, confere DMI = 1 ou 2.
  2. Lê o setor de segurança na PSN `0xFD0210` (camada 1, com 4 tentativas a +0x40) e confere o identificador `0xD1` (XGD1) ou `0xE1` (XGD2/3).
  3. Pega `layer0End` (SS+0x0C) e o último setor, e calcula o tamanho real.
  4. Reescreve a capacidade no TOC em memória.

  Firmware MT1959 tem CMAC, recalculado pelo `scripts/update_cmac.py`. A gravação no Linux é com `redumper flash::mt1959`.
- Compatíveis com o OmniDrive: Blu-ray Hitachi-LG de 2015 em diante, plataforma JB8/JB9 (WH16NS40 nova, BH16NS55/58, WH16NS60, BU40N/BU50N slim etc.). Comuns, baratos, SATA. Os gravadores **DVD** GH24NS/GHA2N **não estão listados**: provavelmente outro chip MediaTek.

**Dois caminhos:**

- **A, rápido:** um Blu-ray LG SATA compatível + OmniDrive. Código aberto, testado pela comunidade Redump. Falta conferir se cabe na baia da carcaça.
- **B, pesquisa (os leitores do usuário):** portar o `EnableXGD()` para o firmware do GH24NS25/GHA2N.
  - Fase 0: chipset/CPU (ARM?), formato e assinatura do firmware oficial da LG, ferramenta de gravação.
  - Precisa achar no firmware alvo: o gancho pós-leitura do TOC, a rotina de leitura por PSN e onde fica a capacidade em memória.

Em paralelo: confirmar os Lite-On iHAS SATA com firmware "0800" (usado pela comunidade Redump) como alternativa e como segundo firmware de referência.

## Boot-time, perfil de hardware e distribuição (discutido 2026-10-22)

**Objetivo de distribuição:** o projeto será compartilhado para outras pessoas
reviverem Xbox antigos quebrados. Hardware do usuário final é **desconhecido**
(nem o próprio dono definiu o hardware do mod ainda). Logo, a imagem padrão tem
que ser **genérica** (drivers amplos). Uma variante "slim" por hardware é uma
IMAGEM SEPARADA, opcional, não o caminho principal.

**Cache de perfil de hardware (já implementado, esclarecer):**
- O perfil JÁ é cacheado no PENDRIVE (partição CONSOLE, `profiles/<fingerprint>.conf`,
  fingerprint = sha1(board|gpu_pci|driver|variante)). No 2º boot da mesma máquina, o `probe.sh`
  acha o cache e PULA a análise pesada (vulkan/tier). É exatamente o "boot mais
  rápido depois do primeiro" — e mora no pendrive, mantendo o disco do Xbox PURO.
- NÃO colocar o perfil no disco FATX do Xbox: o perfil é da MÁQUINA (não do disco),
  e poluiria o disco puro. Mover o pendrive para outra máquina => novo fingerprint
  => re-detecta (correto). Ficar na mesma máquina => reusa (rápido).
- O que o kernel faz todo boot (udev carregar drivers por PCI/USB) é inerente e
  rápido, e é NECESSÁRIO para hotplug (controle/pendrive). Não dá/não vale pular.

**USB sempre monitorado:** udev (hotplug) + SDL no xemu já reconhecem controle/
pendrive plugados a qualquer momento. Mantido.

**Menu do xemu / recursos de manutenção:**
- Em modo kiosk o menu do xemu fica ESCONDIDO (experiência de console).
- Mexer no menu do xemu = forkar/compilar o xemu (quebra o "versão oficial fixada").
  Evitar. Recursos de manutenção/instalação devem ficar no nível Linux/pendrive
  (ex.: Start+Back -> HeXEn) ou na dashboard do Xbox, não no menu do xemu.
- Ideia futura: um MENU DE MANUTENÇÃO no pendrive (nível Linux, no boot) com
  opções tipo "iniciar console", "HeXEn", "formatar", "atualizar sistema".

**Corte do Debian (fazer após teste de bancada):** mascarar timers/serviços inúteis
num console (apt-daily, apt-daily-upgrade, dpkg-db-backup, e2scrub_all, fstrim,
tmpfiles-clean). Boot mais enxuto, sem risco.

## Teste de bancada 2026-10-22 (relatório do usuário) e correções

| Sintoma no teste | Causa | Correção |
|---|---|---|
| **"Só texto", logo não aparece** (até no SSD que já funcionava) | `console-firstrun.service` escrevia na **tty1** ("formatando FATX…"/"disco já preparado…") por cima do splash | **feito** — `console-firstrun` desativado (removido do `enable` e do `After=` do `console.service`). O auto-instalador do lado Linux saiu; não há mais texto por cima do splash. (Se ainda sobrar só texto na bancada, aí é KMS do GPU real: revisar DRM por GPU.) |
| **HeXEn por Start+Back não dá tempo** (controle demora a ser reconhecido no cold-boot) | combo lido cedo demais | **feito** — nova regra: **sem FATX detectado → abre o HeXEn automático** (disco novo/trocado). A pessoa formata/instala dentro do HeXEn. Start+Back fica como alternativa manual. `prepare.sh` exporta `HDD_FATX`; `configure.sh` decide. |
| **1 TB: não cria FATX automático** | formatação pelo libfatx/pyfatx falhava em disco grande | **resolvido por design** — não formatamos mais pelo Linux; o HeXEn formata (robusto p/ qualquer tamanho). |
| **Cerbios erro 13 (UDMA) no 1 TB** | em emulação (sem cabo 80 vias) o IDE do xemu recusa o modo UDMA alto/Auto que o BIOS pede | **parcial / precisa BIOS editável** — ver nota abaixo. |
| **Eject/bandeja do DVD não funciona; talvez nem reconheça o leitor** | provável: leitor não enumerado como `/dev/sr*` (daí `/run/console/dvd` vazio → bandeja não faz nada) | **diagnóstico adicionado** — `prepare.sh` grava `config/leitores-detectados.txt` e loga o leitor achado; `sr_mod`/`cdrom` no initramfs; `bandeja.sh` avisa quando não há leitor. Precisa reconferir na bancada com o arquivo de diagnóstico. |

### UDMA / erro 13 — o que descobri (2026-10-22)

- A config do Cerbios (incl. **UDMA mode**, byte em `CERBIOS-MAIN--`+726 master /
  +727 slave; **UDMA2 = valor `2`**) fica em **texto puro e sem checksum** → um
  BIOS editável pode ter o UDMA fixado em 2 por byte-patch simples e seguro.
- **Porém** o seu **Cerbios 3.1.0 Beta** (256K, Hybrid) guarda esse bloco
  **cifrado**: não tem o marcador `CERBIOS-MAIN--`. O **CerbiosTool 2.0.2** lê os
  bytes crus e procura esse marcador **sem descriptografar**, então **não abre**
  esse BIOS. Ou seja: hoje não dá pra editar o UDMA nem por byte-patch nem pelo
  CerbiosTool 2.0.2.
- **Caminhos p/ fixar UDMA2 (automático de verdade):**
  1. Usar um **Cerbios compatível com o CerbiosTool** (bloco de config em texto),
     setar **UDMA 2 (Default/Stock)** e me passar o `bios.bin` → eu embuto na
     imagem (fica no pendrive, disco continua puro). Ofereço um script headless
     (`cerbios-udma.py`) que faz o byte-patch sem GUI, quando houver BIOS assim.
  2. Enquanto isso: o próprio Cerbios tem **safe mode UDMA2** (liga sozinho em
     erros 9/13, ou segurando **Eject** ao ligar). Vale reconferir se, deixando
     passar o erro, ele cai pra UDMA2 e boota.

## Bancada 2026-10-22 (rodada 2) — diagnóstico e pendências

**Causa do "travou na Cerbios" ACHADA — NÃO era UDMA.** O HeXEn deixou **ele
mesmo** (stub XBE 22 KB, título "HeXEn 2026") como `C:\evoxdash.xbe`, e a dashboard
retail da MS como `xboxdash.xbe`. A Cerbios boota `evoxdash.xbe` → stub → trava.
Confirmado lendo os cabeçalhos XBE do disco via `fatxfs` (ver `bancada/fatx-fedora.sh`).

**GPU da bancada:** **NVIDIA GTX 750 (Maxwell)** + Xeon E5-2680 v4.
A pausa anterior de GPU/Vulkan foi substituida pelo pedido atual: manter duas
imagens, universal e NVIDIA proprietaria para essa bancada. O objetivo imediato
e obter graficos utilizaveis com OpenGL e escala 1. Driver do host: 580.178.04;
driver escolhido para a imagem Debian: 550.163.01-2. A causa e a resolucao dos
sintomas graficos precisam ser confirmadas no boot fisico da nova variante.

**Confirmado funcionando nesta rodada:**
- HeXEn automático abre quando não há FATX (disco novo/trocado). ✔
- Escrita HeXEn/UnleashX → xemu → **disco físico PERSISTE** (FATX gravado de verdade;
  X, C e E com assinatura). Formatar pelo console funciona. ✔
- Boot da dashboard funciona (a MS rodou) → **disco/format/Cerbios OK, não é UDMA**. ✔
- DVD **reconhecido** como leitor (Lite-On iHAS124) no nível Linux. ✔
- `bancada/fatx-fedora.sh`: acessar/copiar/consertar o FATX pelo Fedora (fatxfs). ✔

**Modelo de dashboard (corrigido pelo usuário, regra):** `evoxdash.xbe` = dashboard
**custom** (UnleashX) que a Cerbios boota sempre; `xboxdash.xbe` = **MS retail** como
**alternativa** (saves/menu original), como o modchip que direcionava um ou outro.

**NTFS "fantasma" (por que o disco de PC não some):** o format FATX só grava os
metadados em offsets fixos do Xbox e **não apaga a tabela de partição do PC (setor 0)
nem zera o disco**. Num HDD grande quase vazio, o NTFS antigo sobrevive nas áreas não
tocadas → os dois FS coexistem (perigoso). Num disco já-FATX/vazio não aparece.
Limpeza total = **ação explícita** (nunca automática num disco qualquer).

### Pendências abertas (atacar quando o usuário mandar)

| # | Item | Observação |
|---|------|-----------|
| 1 | **Vídeo: dashboard roda num frame pequeno no canto SUP. ESQUERDO**, não em tela cheia | Usuario confirmou imagem perfeita com variante NVIDIA em 2026-10-23. |
| 2 | **Logo do projeto não aparece** | Causa reproduzida: console=tty3 forcava Plymouth details/texto. Corrigido com console=tty0; logo confirmado no boot UEFI da nova imagem NVIDIA em VM. Falta bancada fisica. Ver `BOOT-LOGO-OGXBOX.md`. |
| 3 | **Menu de config do xemu não é funcional** (mudanças não salvam) | **Correção incluida nas duas imagens; falta bancada.** Preferências de RAM, renderer, escala e vsync são salvas no pendrive por hardware no desligamento normal e restauradas sobre a configuração gerada pela HAL. Ver `docs/CONFIGURACAO-PERSISTENTE.md`. |
| 4 | **DVD tray open/close não dispara ação** | Eject fisico confirmado pelo usuario em 2026-10-23 com a imagem NVIDIA. |
| 5 | **Eject pelo sistema não funciona** | Usuario confirmou acionamento real da bandeja em 2026-10-23. Manter ponte QMP e regressao. |
| 6 | **Som** | Confirmado funcionando pelo usuario na bancada; manter como regressao nas duas imagens. |
| 7 | **Rede** | Usuario confirmou obtencao de IP. FTP fisico ainda nao testado: testar arquivo grande, SHA-256 e velocidade. |
| 8 | **Menu de manutenção no boot** (acessar utilitarios sem Fedora) | R/Start+Back para HeXEn, G para ISO completa OGXbox na mesma janela de oito segundos. Prioridade sobre FATX/DVD e preservacao nos restarts da sessao. Menu completo permanece futuro. |

### A embutir na próxima imagem (já decidido)

- **Garantir boot custom:** se o disco é FATX mas `evoxdash.xbe` está ausente/é o stub
  do HeXEn → instalar a **UnleashX embutida** como `evoxdash.xbe` (mantendo `xboxdash.xbe`).
  Escrita mínima, conteúdo 100% Xbox/FATX (não viola "sem Linux no disco").
- **Log de eventos de bandeja** (#4).
- **Limpeza de disco** como opção explícita (setor 0 / NTFS fantasma).

Ferramenta nova: `bancada/fatx-fedora.sh` (verificar | build | montar | desmontar |
forcar-hexen | instalar-dash) — acesso FATX pelo Fedora, com segurança (lê antes de
escrever, confirma destruição).
