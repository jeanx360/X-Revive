# Teste na bancada real (hardware dedicado)

Passo a passo para rodar o console numa máquina de verdade: boot pelo pendrive,
instalador por DVD comum, HDD num SSD limpo. Nunca faça este teste no PC de
desenvolvimento usando os discos do dia a dia.

## 0. A imagem (já está pronta)

`cartucho/out/console-xbox.img` (~3,6 GB), três partições (SYSTEM, CONSOLE,
CACHE), com o firmware já embutido em CONSOLE (`mcpx_1.0.bin`, `bios.bin`,
`eeprom.bin`). Se quiser garantir que é a última versão:

```sh
cartucho/build/build.sh xbox ~/Downloads/xbox-console
```

## 1. Gravar o pendrive (≥ 8 GB)

Plugue o pendrive e descubra o dispositivo **com cuidado**:

```sh
lsblk -do NAME,SIZE,MODEL,TRAN     # ache o pendrive pelo tamanho/USB
```

Grave (troque `sdX` pelo pendrive — confira duas vezes, o dd apaga tudo):

```sh
sudo dd if=cartucho/out/console-xbox.img of=/dev/sdX bs=4M conv=fsync status=progress
sync
```

## 2. Gravar o DVD do instalador (Softmodding Tool Extras Disc)

Use `bancada/vm/extras-disc.iso` (658 MB). É uma imagem XISO; grave **como imagem
de disco**, não como "dados":

- GUI: Brasero ou K3b → *Gravar imagem* → escolha o `.iso`.
- CLI: `growisofs -dvd-compat -Z /dev/sr0=bancada/vm/extras-disc.iso`

Prefira **DVD-R**. Esse disco traz o XBPartitioner (formata FATX) e os
instaladores de dashboard.

## 3. Montar a bancada

Na máquina dedicada, conecte:
- o **pendrive** (boot),
- o **SSD 120 GB limpo** numa porta SATA (será o HDD do Xbox),
- um **leitor/gravador de DVD** com o disco do passo 2.

Na UEFI: **Secure Boot desligado**, boot por USB habilitado (pendrive como
primeira opção).

## 4. Primeiro boot (sem configurar nada)

Ligue com o SSD já conectado. O console **acha o HDD sozinho** (`hdd=auto` é o
padrão): se o disco já estiver formatado em FATX ele o reconhece na hora; se
estiver em branco e for o único disco além do pendrive, ele o adota. Não precisa
editar arquivo nenhum.

Com o SSD em branco, a Cerbios mostra o erro de HDD (esperado) — é o passo 5 que
formata. Só precisaria mexer no `config/ports.conf` em caso raro: máquina com
vários discos e nenhum formatado (aí o console não chuta; veja
`config/discos-detectados.txt` e fixe `hdd=<porta>`). Para 128 MB, `ram=128`.

## 5. Formatar e instalar (automatico)

Nao precisa fazer nada: no primeiro boot com o SSD **vazio**, o console formata
em FATX e instala a dashboard sozinho, e ja cai nela. Se o SSD tiver dados
(particao/conteudo), aparece uma pergunta na tela: **Teclado Y/N** ou
**Controle A (sim) / B (nao)**. Disco ja formatado e reconhecido na hora.

Se preferir preparar pelo PC (opcional), o `hdd.py --disco` continua existindo.

## 6. Boot final e teste do leitor

Ligue com o pendrive + SSD já preparado. Esperado:
- Cerbios → (animação, se instalada) → **dashboard** carregada do SSD.
- Insira o DVD do instalador: o console deve dar boot nele (leitor comum lendo o
  disco → xemu → Cerbios). Tirar o disco volta para a dashboard; o botão Eject
  abre a bandeja e volta para a dashboard.

Isso fecha o teste: boot pelo pendrive, HDD real em FATX, dashboard rodando,
leitor de DVD funcionando.

## 7. Modo diagnóstico (se algo travar)

Crie um arquivo vazio chamado `debug` na raiz da partição **SYSTEM** do pendrive
(de qualquer PC). No próximo boot o console manda log detalhado para a tela e
para a serial (`console=ttyS0,115200`), útil se ele não chegar à dashboard.
Apague o arquivo para voltar ao modo silencioso.

Leitor comum **não lê disco original de Xbox** (só DVD-R gravado, vídeo, áudio e
discos utilitários). Para ler disco original, ver docs/ROADMAP.md (OmniDrive/Kreon
em leitor compatível).
