# Arquitetura

## 1. Princípio

O comportamento de console vem do **emulador LLE (xemu)**: ele já emula BIOS,
EEPROM, HDD IDE, leitor DVD e portas de controle do Xbox. O trabalho deste
projeto é **ligar cada peça física do PC ao componente virtual certo** e esconder
o Linux.

```
 PEÇA FÍSICA                    CAMADA DO PROJETO                     XEMU (console virtual)
 ─────────────                  ─────────────────                     ──────────────────────
 Pendrive / part. CONSOLE  ──▶  monta firmware/ ro                ──▶ MCPX boot ROM, Flash BIOS, EEPROM
 Porta SATA designada      ──▶  udev by-path → /dev/console-hdd   ──▶ IDE0 Master (HDD)
 Leitor DVD                ──▶  udev → /dev/console-dvd + daemon  ──▶ IDE0 Slave (DVD) + bandeja
 Controles USB/Bluetooth   ──▶  xpad / xpadneo / hid + SDL        ──▶ Portas 1–4 (Duke/S virtual)
 GPU/CPU (qualquer)        ──▶  HAL: perfil de hardware            ──▶ renderer, escala, áudio
 Botão Power/Eject/LED     ──▶  ACPI + gpio/serial (ver CARCACA)   ──▶ desligar / ejetar
```

## 2. O pendrive ("cartucho")

Três partições:

| Partição    | Formato         | Conteúdo                                                   | Montagem          |
|-------------|-----------------|------------------------------------------------------------|-------------------|
| `p1 SYSTEM` | FAT32 (ESP)     | kernel + initramfs + `system.squashfs` (sistema inteiro)   | lida e copiada p/ RAM |
| `p2 CONSOLE`| FAT32           | `firmware/` (mcpx, bios, eeprom), `profiles/`, `config/`   | ro; rw só p/ gravar perfil |
| `p3 CACHE`  | ext4            | cache de shaders e dados do xemu, uma pasta por máquina    | rw; persistente, não vai p/ RAM |

- `p1` pode ser regravada a qualquer momento (atualização do "sistema") sem
  perder a identidade do console.
- `p2` é o equivalente à **EEPROM + chips de BIOS** de um Xbox real. É FAT32 para
  você copiar os dumps de qualquer PC. O `eeprom.bin` é a identidade do console
  (serial, MAC, HDD key): é ele que faz o HDD ser "deste console".
- `p3` guarda o cache de shaders compilado para a GPU daquela máquina (pasta por
  `fingerprint` da HAL). Fica no pendrive, não na RAM, então sobrevive ao boot: o
  jogo roda liso desde o início, sem as travadinhas da primeira vez. É descartável
  (se apagar, o xemu regenera). O xemu é apontado para lá via `XDG_DATA_HOME`.
- O sistema roda inteiro da RAM (`toram`). Puxar o pendrive com o console ligado
  não corrompe nada; o próximo boot simplesmente não acontece, como um Xbox sem BIOS.

## 3. Boot

```
Power → UEFI (fast boot, logo desligado)
  → kernel + initramfs do pendrive → squashfs para RAM
  → hal/probe: detecta CPU/GPU/áudio/portas, escolhe ou carrega perfil
  → udev: cria /dev/console-hdd (só a porta SATA designada) e /dev/console-dvd
  → gera /run/console/xemu.toml (firmware + discos + perfil)
  → cage (compositor kiosk, sem cursor) → xemu em tela cheia
  → animação verde do Xbox
```

Nada de tela de login, nada de cursor, nada de mensagens do kernel (`quiet
loglevel=0 vt.global_cursor_default=0`, splash preto).

## 4. HDD físico

- A porta SATA é escolhida **pelo caminho físico** (`/dev/disk/by-path/pci-…-ata-N`),
  nunca por `/dev/sdX`. O pendrive e qualquer outro disco ficam invisíveis ao console.
- Configuração do vínculo fica em `CONSOLE/config/ports.conf`, gerado por um
  assistente de primeiro boot ("plugue o HDD do console na porta desejada").
- Sem disco na porta: o xemu sobe sem HDD e o kernel do Xbox mostra o erro real
  (com BIOS retail: erro 07; com Cerbios/PrometheOS: tela própria deles).
- Disco virgem: boot por DVD de utilitário (HeXEn etc.) particiona em FATX.
- Portabilidade para um Xbox real exige: mesmo `eeprom.bin` do console real,
  disco travado (ATA lock) ou BIOS modificada que aceite disco destravado, e LBA48
  para discos > 137 GB. Ver VALIDACOES.md V3.

## 5. Leitor de DVD

Limitação física importante: **um leitor de DVD de PC comum não lê discos
originais de Xbox** (setores de segurança/partição de jogo escondida). Opções:

| Mídia                         | Leitor comum | Leitor com firmware Kreon (ex.: Samsung SH-D162, LiteOn iHAS) |
|-------------------------------|--------------|------------------------------------------------------------|
| DVD-R gravado (XISO)          | funciona     | funciona                                                   |
| Disco original de fábrica     | não lê o jogo | lê (é o que se usa para fazer backup)                      |
| DVD de vídeo / CD de áudio    | funciona     | funciona                                                   |

Troca de disco (implementado, testado na VM):

- Com disco na bandeja, o `run.sh` passa o leitor ao xemu como
  `host_device:/dev/srN`. O driver `host_cdrom` do QEMU trava o xemu na leitura.
  Bandeja vazia: o console liga com o leitor vazio.
- O kernel verifica a bandeja a cada 2 s (`events_poll_msecs`, já que não há
  udisks). Disco colocado → udev religa o console, como o Xbox que dá boot no
  jogo ao fechar a bandeja.
- Botão Eject do leitor: enquanto o xemu usa o leitor, o kernel trava a
  bandeja. O pedido de ejeção (`DISK_EJECT_REQUEST`) aciona o
  `console-bandeja.service`: ele desliga o emulador, abre a bandeja e religa o
  console sem disco, que volta para a dashboard.
- O live-boot só procura o sistema na partição SYSTEM (`live-media=`), nunca no
  disco do leitor.

## 6. Controles

Implementado:

- USB com fio: `xpad` do kernel, para Duke/S original (as portas da carcaça
  são USB), 360, One e Series. O usuário `console` está no grupo `input`. O
  SDL entrega os controles ao xemu (`auto_bind`), que os liga às portas 1–4 na
  ordem de conexão, com vibração.
- Dongle sem fio original (Xbox Wireless Adapter 02e6/02fe/02f9/091e): driver
  `xone` v0.5.8, compilado no build para o kernel da imagem. Só os módulos do
  dongle: o `xone_wired` fica de fora para o `xpad` continuar ativo, porque o
  Duke original precisa dele. O `mt76x2u` fica na blacklist porque também
  reconheceria o dongle. O firmware é da Microsoft e só entra na imagem se
  baixado com `cartucho/tools/firmware-dongle.sh`.

A fazer:

- Bluetooth (`xpadneo`, One/Series via BT) e pareamento sem tela: segurar o
  botão de sync; o console aceita pareamento por 60 s após ligar.
- Porta fixa por controle (porta 1 da carcaça = jogador 1).

## 7. O que mudei em relação à spec original (Gemini)

| Spec original                          | Mudança                                                   | Motivo |
|----------------------------------------|-----------------------------------------------------------|--------|
| Alpine Linux                           | Debian stable mínimo (live-build, squashfs, toram)        | Alpine usa musl: não roda driver proprietário NVIDIA nem os binários oficiais do xemu. Debian roda em qualquer GPU. |
| Fork do xemu "headless"                | xemu oficial + `xemu.toml` gerado no boot; patch só se a bancada provar necessidade | Fork é manutenção eterna. O xemu já tem tela cheia e não precisa de desktop dentro do `cage`. |
| KMS puro / `-display curses`           | `cage` (kiosk Wayland)                                    | curses é modo texto. `cage` dá tela cheia + Vulkan + sem cursor de forma estável. |
| KVM obrigatório                        | Removido                                                  | O xemu emula a CPU por TCG; o gargalo é a GPU NV2A, não a CPU de 733 MHz. |
| `chmod 666 /dev/sda`                   | Regra udev por caminho físico + grupo dedicado           | `sda` muda entre boots; erro aqui apaga o disco errado. |
| Boot < 3 s                             | Meta 8–15 s até a animação verde                          | O POST do UEFI sozinho já leva 5–15 s. |
| Linha de comando estilo QEMU           | `xemu.toml` (`[sys.files]`)                               | É a forma suportada do xemu atual. |
| Hardware fixo                          | Camada HAL com perfis                                     | Mesmo pendrive em Xeon, Ryzen ou Intel (ver HARDWARE.md). |
| PS2 com mesmo modelo de disco          | Plataforma separada, modelo próprio                       | PCSX2 não usa HD bruto como o Xbox; vira outro "cartucho". |

## 8. Vários consoles, um hardware

O hardware na sala é sempre o mesmo. **Cada pendrive é um console**:

```
pendrive "XBOX"  → sistema base + plataforma xbox  + CONSOLE/ (mcpx, bios, eeprom)
pendrive "PS2"   → sistema base + plataforma ps2   + CONSOLE/ (bios do PS2, memory cards)
pendrive "PS1"   → sistema base + plataforma ps1   + CONSOLE/ (bios do PS1, memory cards)
```

- O **sistema base** (kernel, drivers, HAL, udev, controles, `cage`) é idêntico
  em todos.
- A **plataforma** (`plataformas/<nome>/`) define o emulador e como cada peça
  física vira peça virtual: o que é o HDD, o que é o DVD, onde ficam os saves.
- A **partição CONSOLE** guarda a identidade daquele console específico.
- O disco SATA também é do console: trocar de console é trocar o par
  pendrive + disco, como um cartucho com seu cartão de memória.

Na imagem, isso significa um único script de build com parâmetro de plataforma:
`cartucho/build/build.sh xbox`.

## 9. Limite honesto

"Igual ao console real" está limitado pela compatibilidade do xemu: a maioria do
catálogo roda bem, mas alguns jogos ainda têm falhas gráficas ou de desempenho em
qualquer hardware. O projeto garante o **comportamento físico** (BIOS, HDD, DVD,
controles); a fidelidade de cada jogo vem do xemu e melhora a cada versão dele.
