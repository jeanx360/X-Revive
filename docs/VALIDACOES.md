# Validações de bancada

Cada item é uma hipótese que decide o rumo do projeto. Fazer **em ordem**: se um
falhar, a arquitetura muda antes de investir no resto. Tudo roda na **máquina de
bancada dedicada** (placa Acer), nunca no PC de desenvolvimento.

| #  | Hipótese                                                                  | Como testar                                                     | Se falhar                                   |
|----|---------------------------------------------------------------------------|-----------------------------------------------------------------|---------------------------------------------|
| V1 | xemu oficial roda na bancada com Vulkan na GPU dela                          | Instalar xemu (Flatpak/AppImage), rodar com dumps reais         | Usar renderer OpenGL                        |
| V1b | Qual chave de EEPROM a BIOS aceita (Cerbios e retail)            | Trocar `eeprom.bin` por `eeprom_r1/r2/r3`; ver se o dashboard mostra serial/MAC certos | Usar a que funcionar e documentar |
| V2 | xemu aceita um **dispositivo de bloco** (`/dev/…`) como `hdd_path`        | Disco SATA/USB de teste vazio, apontar `hdd_path` para ele      | Patch mínimo no xemu forçando formato raw   |
| V3 | Disco formatado pelo xemu funciona num Xbox real (e vice-versa)           | HeXEn no xemu → disco no Xbox real via adaptador IDE-SATA       | Documentar como limitação ou emular ATA lock |
| V4 | Erro 07 aparece com BIOS retail e sem HDD                                 | `hdd_path` vazio                                                | Ver comportamento por BIOS                  |
| V5 | Nível de desempenho real da bancada (lista de jogos de referência)           | Medir FPS em 5 jogos escolhidos                                 | Ajustar tabela de níveis                    |
| V6 | xemu aceita leitor físico (`/dev/sr0`) como `dvd_path` e troca de mídia em execução | DVD-R com XISO; ejetar/inserir com o jogo rodando     | `dvd-bridge` converte o disco em ISO temporária |
| V7 | Controles Series/One via USB e BT aparecem nas portas com vibração        | xpad + xpadneo                                                  | —                                           |
| V8 | Tudo sobe dentro do `cage`, sem desktop, em tela cheia                    | `cage -- xemu` num TTY                                          | KMSDRM direto do SDL                        |
| V9 | Imagem Debian live no pendrive faz boot em outra máquina (AMD/Intel)      | Gravar pendrive, testar em 2 PCs diferentes                     | Ajustar drivers na imagem                   |

## Material necessário

- `mcpx_1.0.bin` (falta; não sai de placa 1.6)
- BIOS: Cerbios (ok, variante BFM a confirmar no V1)
- EEPROM: ok, cópias r1/r2/r3 geradas por `plataformas/xbox/tools/eeprom.py`
- Um HDD/SSD SATA de teste vazio (≥ 8 GB) e, se possível, adaptador IDE-SATA
- DVD-R com um jogo em XISO para o V6
- Um pendrive de 8 GB+ para o V9

## Resultados na bancada virtual (VM QEMU/KVM, 2026-10-21)

`bancada/vm.sh`: pendrive como USB, HDD SATA virtual de 10 GB, UEFI, sem
Secure Boot. Não substitui a bancada real (GPU, controles, DVD físico).

| Item | Resultado |
|------|-----------|
| Boot do pendrive | ok: grub → live-boot → console em ~11 s (VM) |
| Partição CONSOLE | ok: perfil gravado, lista de discos sem o pendrive |
| HAL na VM | ok: virtio → OpenGL, nível C |
| V8 (cage + xemu sem desktop) | ok |
| V1 (Cerbios + MCPX no xemu) | ok: Cerbios dá boot |
| V1b (chave EEPROM) | `eeprom_r1.bin` aceito pela Cerbios |
| V2 (disco bruto como HDD) | ok: xemu abre `/dev/console-hdd`. Aviso do QEMU: formato não declarado, escritas no setor 0 restritas. Confirmar na formatação. |
| V4 (HDD virgem) | **Erro 13** (sem dashboard). Cerbios reinicia em modo seguro UDMA2, como documentado. |
| V5 (HDD preparado pelo PC) | ok: `plataformas/xbox/tools/hdd.py` formata FATX (X Y Z C E + F) e instala o modo Hardmod do Xbox Softmodding Tool. Cerbios carrega `C:\evoxdash.xbe` → UnleashX, que mostra C, E e F. Estável por mais de 2 min. |
| Áudio (DSP) | O interpretador do DSP do xemu abortava com "Illegal dsp instruction" assim que a UnleashX abria. Corrigido com `use_dsp_jit = true`. |
| Leitor de DVD (V6, virtual) | ok: Extras Disc do Softmodding Tool (`bancada/extras-disc.sh`) dá boot pelo leitor. Com `host_cdrom` o xemu travava em tela preta; agora usa `host_device`. |
| Troca de disco | ok: Eject → dashboard ("Tray: Empty"); disco de volta → boot do disco. Parar o console leva 0,2 s. Antes eram 90 s, com o xemu sobrevivendo fora do cgroup e segurando o HDD. |
| Controle USB na VM | pendente: passthrough pronto no `vm.sh`, falta a permissão no host (`sudo bancada/permitir-controle.sh`) |
| Animação de boot | ausente: o Cerbios.bin procura `E:\Cerbios\BootAnims\Xbox\BootAnim.xbe`, que vem no pacote de release. Instalar com `hdd.py instalar-cerbios`. |
| Cache de shaders persistente | ok: 3ª partição CACHE (ext4). `XDG_DATA_HOME` por máquina → xemu grava em `/var/cache/console/<fingerprint>/xdg/xemu/xemu/shaders`. Confirmado na partição após desligar. Não vai para a RAM, sobrevive ao boot. |
| Wayland direto (sem XWayland) | ok: faltava `libwayland-cursor0`. Com ela, o xemu usa o backend Wayland do SDL direto no cage; nenhum processo Xwayland sobe. Queda segura para X11 se o init falhar. |
| CPU no máximo | governador vem do perfil (`performance` em desktop/console, `schedutil` em notebook); afinidade reserva a CPU 0 quando há ≥6 threads. Na VM não há cpufreq, então só vale na bancada. |
| RAM 128 MB (Ultimate) | parcial: `ram=128` no ports.conf chega ao xemu (`-m 128`, confirmado por log). O dashboard ainda mostra ~44 MB livres (64 MB): o kernel/BIOS precisa ser 128-aware. Verificar na bancada com título/config que use 128 MB. Padrão 64. |
| HDD auto-detectado (plug-and-go) | ok: `hdd=auto` (padrão). Disco em branco → adota o único disco não-pendrive; disco já FATX → reconhece pela assinatura e dá boot direto na dashboard, sem editar arquivo. Validado na VM nos dois casos. |
| Auto-instalador no 1o boot | ok: disco vazio → `console-firstrun` formata FATX + instala a dashboard (UnleashX enxuta) sozinho → Cerbios 3.1.0 boota direto na dashboard. Validado na VM. Disco com dados: pergunta na tela (teclado Y/N, controle A/B) — lógica implementada; o prompt em si precisa de teclado/controle real para teste final. |
| Cerbios 3.1.0 Hybrid | ok: boota no xemu igual à 2.4.2. Config nova traz `DisableLimitMem` (128 MB real) e `Force480p`. |
| Splash de boot (X-Revive) | ok: plymouth com tema X-Revive (logo + pontos de carregamento) no initramfs (cobre a cópia pra RAM). plymouth-start roda; cage volta a subir com `chvt 1` antes do cage (o splash deixava o VT trocado -> "session not active"). Visual confirmado só na bancada real (virtio-gpu não captura limpo). |
| Fix controle cold-boot | implementado (console-pad re-enumera controle GIP após o emulador subir); validar na bancada. |
| Animação de boot clássica | ok: BootAnim.xbe (Cerbios 3.1) instalado pelo auto-instalador em E:\Cerbios\BootAnims\Xbox\. Validado na VM: Cerbios → animação original do Xbox (célula azul → logo XBOX) → dashboard. |
| Firmware do dongle (projeto) | ok: xone_dongle_02e6/02fe/02f9/091e.bin baixados e incluídos na imagem. |
| Bugs da bancada real (2026-10-22) | corrigidos e validados na VM: (1) erro `/etc/network/interfaces` no init -> overlay `etc/network/interfaces`; (2) **logo não aparecia / tela preta** -> plymouth saía aos 11s (plymouth-quit mascarado; só sai no ExecStartPre do console.service) + drivers DRM/FRAMEBUFFER no initramfs (KMS cedo); (3) "não instalava" era a tela preta (a instalação sempre funcionou). |
| HeXEn 2026 integrado | HeXEn.iso (392MB) na partição CONSOLE. Boot padrão = dashboard. **Start+Back (Select) segurado ao ligar** -> entra no HeXEn (one-shot). held.py lê o combo via EVIOCGKEY; configure.sh seta a flag; run.sh carrega e limpa. |
| CONSOLE 512->640 MiB | para caber o HeXEn. Imagem ~3,9 GB (cabe em 16 GB). |
