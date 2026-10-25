# Mídia X-Revive

Uma IMG instaladora para PC x86-64 UEFI com Mesa e NVIDIA 550 no mesmo sistema.
Pendrive de pelo menos 16 GB. A beta.4 oferece IMG para gravação: [baixar e instalar](../docs/BAIXAR-E-INSTALAR.md).
Avisos e fontes correspondentes acompanham a release.

## Gerar

```sh
PUBLISH_RELEASE=0 cartucho/build/build.sh xbox
```

Build em container Debian; firmware do usuário é fornecido depois no USB, não
no build. A IMG não embute os pacotes Rocky5. O instalador pode baixá-los pela
internet ou ler uma ISO local normalizada. Veja [build](../docs/COMUNIDADE-BUILD.md)
e [instalação](../docs/INSTALADOR-ONLINE.md).

## Iniciar e instalar

Grave a IMG no pendrive inteiro. Copie firmware para
`XREVIVE/X-Revive/firmware/xbox/` (BIOS/MCPX obrigatórios; EEPROM opcional); ISO opcional em `X-Revive/pacotes/`.
Inicie USB UEFI, prepare a fonte, selecione o destino e confirme duas vezes.
A instalação limpa apaga o destino; não é uma atualização de disco com jogos.

Depois o SSD inicia sem USB. R ou Start+Back abre manutenção; Start+digital para
cima abre Xemu; U/Y abre cliente de atualização. O canal público ainda não está
ativo. Xbox físico modchipado e desempenho por GPU exigem testes separados.

## Partições

SYSTEM: boot/kernel/initrd/sistema somente leitura. CONSOLE: firmware/perfis.
CACHE: shaders e versões Xemu. UTILS: metadados mínimos; no SSD, inventário da
coleção para manutenção. XREVIVE: área exFAT do usuário no USB, sem equivalente
necessário no SSD. A coleção é instalada no FATX, não duplicada em UTILS.

Não apague CACHE para fazer manutenção: ela pode guardar o emulador ativo.
O Xemu original continua na SYSTEM como recuperação. Releases históricas com
três variantes e coleção embutida foram substituídas pela mídia instaladora única.
