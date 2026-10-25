# Baixar, gravar e instalar o X-Revive

**[BAIXAR A IMG PRONTA — beta.4 · 1,27 GB](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.4/x-revive-v0.1.0-beta.4.img.xz)**

Não precisa compilar, criar conta nem fazer login para baixar. Use os links
abaixo ou [abra a release](https://github.com/jeanx360/X-Revive/releases/tag/v0.1.0-beta.4)
e expanda **Assets** para ver os arquivos:

| Arquivo | Para que serve |
|---|---|
| [x-revive-v0.1.0-beta.4.img.xz](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.4/x-revive-v0.1.0-beta.4.img.xz) | Imagem instaladora para o pendrive |
| [SHA256SUMS.txt](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.4/SHA256SUMS.txt) | Conferir integridade dos downloads |
| [arquivos-do-usuario.zip](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.4/arquivos-do-usuario.zip) | Pastas vazias e instruções para seus arquivos |
| [LEIA-ME.txt](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.4/LEIA-ME.txt) | Guia curto que pode ser guardado no PC |

`Source code` e `sources-*` são para estudar/recompilar. **Não grave esses arquivos
como instalador.** A IMG contém Linux, drivers, Xemu e nosso instalador; não contém
BIOS/MCPX/EEPROM, coleção de aplicativos ou jogos.

**Na beta.4, a EEPROM é opcional.** BIOS e MCPX continuam obrigatórios.
Sem `eeprom.bin`, o Xemu gera a identidade no primeiro boot e ela fica preservada
no SSD. [Detalhes](EEPROM-OPCIONAL.md). A beta.2 antiga ainda exigia os três arquivos.

## 1. Preparar

PC x86-64 UEFI, pendrive de pelo menos 16 GB e HDD/SSD dedicado de teste com pelo
menos 32 GiB. O destino precisa ter setores lógicos de 512 bytes e ser menor que
2 TiB. Use teclado ou controle com fio; o firmware do Xbox Wireless Adapter não
é fornecido nesta entrega. Para instalação online, conecte Ethernet com DHCP.
Reserve pelo menos 16 GB livres no computador para descompactar a IMG.
Secure Boot deve estar desativado; essa configuração não é validada nesta beta.

Confira o SHA256 da imagem compactada com a linha correspondente de SHA256SUMS:

Linux:

```sh
sha256sum x-revive-v0.1.0-beta.4.img.xz
```

PowerShell no Windows:

```powershell
Get-FileHash .\x-revive-v0.1.0-beta.4.img.xz -Algorithm SHA256
```

Os 64 dígitos devem coincidir, sem diferença entre maiúsculas/minúsculas.

## 2. Gravar no pendrive

Descompacte `.img.xz` com [7-Zip](https://www.7-zip.org/) ou ferramenta compatível.
No Linux também pode usar:

```sh
xz -dk x-revive-v0.1.0-beta.4.img.xz
```

O resultado é `x-revive-v0.1.0-beta.4.img`. Use um dos aplicativos abaixo.
A gravação apaga o pendrive. Não selecione seu SSD/HDD do PC.
Copiar a IMG como arquivo para dentro do pendrive não o torna inicializável.
Aguarde a verificação da ferramenta; depois ejete e reconecte o USB no PC.

### Aplicativos para gravar o pendrive

| Aplicativo | Sistema no qual você grava | Como usar com o X-Revive |
|---|---|---|
| **[balenaEtcher — recomendado](https://etcher.balena.io/)** | Windows, Linux e macOS | **Flash from file** → IMG descompactada → **Select target** → pendrive → **Flash!**; aguarde a validação |
| [Raspberry Pi Imager](https://www.raspberrypi.com/software/) | Windows, Linux e macOS | Na seleção de sistema, **Use Custom / Usar imagem personalizada** → nossa IMG descompactada → pendrive; não escolha Raspberry Pi OS nem aplique personalizações de outro sistema |
| [Discos do GNOME](https://apps.gnome.org/DiskUtility/) | Linux com GNOME | Selecione o pendrive inteiro e use **Restaurar imagem de disco…** para gravar nossa IMG descompactada |

O nome Raspberry Pi Imager é do gravador; a imagem X-Revive continua destinada a
PC x86-64 UEFI, sem suporte anunciado a Raspberry Pi. As alternativas são
orientações de gravação; não houve ensaio novo de cada aplicativo/sistema nesta
revisão documental. Use a gravação de imagem completa, sem extrair arquivos para
um pendrive formatado nem recriar suas partições manualmente.

Referências oficiais: [Etcher](https://etcher.balena.io/),
[Imager e opção Use Custom](https://www.raspberrypi.com/documentation/computers/getting-started.html#installing-the-operating-system),
[Discos do GNOME](https://apps.gnome.org/DiskUtility/).

## 3. Colocar seus arquivos

Abra a partição **XREVIVE**. Extraia `arquivos-do-usuario.zip` para a raiz dela.
Tem que existir uma única pasta `X-Revive`, com esta estrutura:

```text
XREVIVE/
  X-Revive/
    firmware/
      xbox/
        bios.bin          # 256, 512 ou 1024 KiB
        mcpx_1.0.bin       # 512 bytes, MCPX 1.0
        eeprom.bin        # opcional: 256 bytes
      bootanims/Xbox/     # opcional
        BootAnim.xbe
        bootanim.ini
    pacotes/              # opcional
      sua-colecao.iso
```

Forneça BIOS e MCPX obtidos de forma autorizada e compatíveis com o
[Xemu](https://xemu.app/docs/required-files/). Para usar uma identidade existente,
copie também sua EEPROM de 256 bytes. Se não fornecer esse arquivo, o Xemu
criará uma EEPROM válida no primeiro boot; o sistema a grava no SSD e a reutiliza
nas próximas inicializações. Um arquivo fornecido com tamanho inválido é recusado.
Não renomeie arquivos aleatórios nem use uma EEPROM de terceiros.
Não coloque `firmware` e `pacotes` soltos na raiz, nem crie `X-Revive/X-Revive`.
A pasta opcional de animação só é usada quando seus arquivos são fornecidos.

Não formate SYSTEM, CONSOLE, CACHE ou UTILS se o Windows oferecer fazê-lo. Só
XREVIVE é a área de arquivos do usuário. Ejete o USB com segurança após copiar.

## 4. Instalar

Inicie o PC pelo pendrive em modo UEFI e escolha **Instalar**.

- **Rocky5 — baixar pela internet:** usa as origens do catálogo, confere os hashes
  e prepara a coleção no próprio USB. Não exige ISO. Pode demorar conforme rede/USB.
- **Usar ISO offline do pendrive:** escolhe uma ISO **normalizada X-Revive**, com
  `payload/manifest.json`. ISOs originais de HeXEn/OGXbox/Extras Disc não são
  compatíveis automaticamente. O projeto não distribui a coleção de aplicativos em ISO.

Firmware e todos os pacotes são conferidos antes da seleção do destino.
Confira modelo/capacidade do HDD/SSD. **A instalação apaga esse destino**, inclusive
outro sistema ou jogos existentes; não é migração nem dual boot. Confirme
segurando F10, solte e confirme novamente na segunda tela. No controle, use
LT+RT+Start, solte e repita. Antes da segunda confirmação é possível cancelar.

Espere instalação e leitura de volta terminarem. Desligue, retire o pendrive e
inicie pelo HDD/SSD. Xbox Classic: logo X-Revive → animação, se fornecida e
habilitada na BIOS → XBMC4Gamers. O pendrive continua útil para manutenção.

## Área pessoal pronta após gravar

A IMG já contém a partição exFAT `XREVIVE` formatada. Depois de gravar,
abra essa partição no PC, extraia as pastas do usuário e copie seus arquivos
antes de iniciar o X-Revive. Não há boot intermediário para criar a área pessoal.

O download tem cerca de **1,27 GB**; descompactada, a IMG ocupa **14,16 GB**,
incluindo **10 GiB fixos** para arquivos pessoais. A compactação reduz o download,
mas o gravador escreve a imagem completa. Em pendrives maiores, a área XREVIVE
continua com 10 GiB; o espaço adicional não é incorporado automaticamente.

## Uso e recuperação

R no boot do SSD (ou Start+Back) abre manutenção. Start+digital para cima abre o
menu do Xemu. U/Y abre o cliente de atualização; **canal público ainda não ativo**.
A instalação não faz flash de BIOS do PC nem do Xbox.

A área XREVIVE tem 10 GiB. Em USB de 16 GB, ISO offline e cache online de 8 GiB
não cabem juntos. Para alternar, com o instalador desligado, retire só a cópia da
ISO do USB antes do online; para voltar ao offline, retire só
`X-Revive/cache/rocky5-stage.ext4` e copie sua ISO. Preserve os originais no PC.

Se algo falhar, use os [diagnósticos](INSTALADOR-ONLINE.md#tela-preta-e-logs) e o
modelo de bug. Não anexe firmware/EEPROM/chaves. [Limitações da beta](BETA.md).
