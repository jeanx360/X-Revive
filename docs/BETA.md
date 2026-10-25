# Beta v0.1.0-beta.4

Beta para PC x86-64 UEFI, com IMG pronta para gravar, instalação Rocky5 online
ou ISO local normalizada, manutenção e EEPROM opcional.

## Requisitos atuais

- PC x86-64 com boot UEFI; Secure Boot não é uma configuração validada.
- Pendrive de 16 GB ou maior. A área de dados do instalador é exFAT.
- HDD/SSD de teste dedicado, pelo menos 32 GiB, menor que 2 TiB e setores lógicos de 512 bytes.
- Teclado ou controle compatível. Cabo de rede e DHCP para instalação online.
- BIOS e MCPX fornecidos pelo usuário; EEPROM e animação Xbox opcionais.

**EEPROM opcional na beta.4:** forneça sua EEPROM ou deixe o Xemu gerar uma nova.
A identidade é preservada no SSD. [Detalhes](EEPROM-OPCIONAL.md).

A mídia reúne Mesa e NVIDIA 550, incluindo suporte à GTX 750 da bancada. Isso
não significa suporte a toda NVIDIA antiga ou futura. Desempenho depende da
emulação e do hardware. Não há interface de seleção de Wi-Fi.

## O que foi verificado

| Evidência | Resultado e limite |
|---|---|
| Testes da beta.4 | 72 passaram na bancada, incluindo limpeza pública, coleta de fontes e fingerprint sem assets particulares |
| Testes automatizados da base df48 | 64 testes passaram com fixtures locais; no clone público, o teste UIX com pacote real é opcional |
| Cópia limpa dos fontes públicos da beta.4 | 72 testes descobertos: 71 passaram e 1 skipped (UIX sem pacote real), sem firmware ou executáveis Xbox privados |
| VM, instalação offline completa | 104 pacotes / 98.996 arquivos, leitura de volta; SSD intacto antes das confirmações |
| VM, download online real | 107 arquivos HTTPS, hashes conferidos e coleção equivalente à offline |
| VM, operação por controle | Preparação online, cancelamento, duas confirmações com soltura, instalação completa |
| VM, boot só pelo SSD | Dashboard, áudio, manutenção por R e inventário de dez dashboards |
| Bancada física | Inicialização, áudio, rede/FTP, jogos/homebrew e bandeja física validados |
| Xbox original modchipado | Objetivo experimental; não há novo teste físico conclusivo desta beta |
| Splash personalizado da BIOS | Cópia reaberta no editor e boot em VM; o splash não apareceu nas capturas. Exibição permanece pendente |

O [relatório técnico](VALIDACAO-ONLINE-2026-10-24.md) distingue as etapas e os
problemas de instrumentação. Caches, discos de VM, capturas e logs citados são
arquivos locais de bancada, não fazem parte do clone público.

## Limitações conhecidas

- Instalação limpa: não preserva jogos ou outro sistema existente no destino.
- Offline aceita somente ISO normalizada com `payload/manifest.json`, não qualquer ISO Xbox.
- ISO de teste e cache online de 8 GiB não cabem juntos na área XREVIVE de 10 GiB.
- Cliente Xemu validado localmente; canal público de atualização ainda pendente.
- Firmware do Xbox Wireless Adapter não incluído: use teclado ou controle com fio nesta entrega pública.
- Atualização integral, migração preservando dados e importadores de outros discos não implementados.
- Downloads dependem das origens fixadas; se mudarem, os hashes impedem instalar conteúdo diferente silenciosamente.
- Build ainda não hermético: APT sem snapshot completo, wheel pyfatx sem hash fixado e timestamps variáveis.

## Relatar um problema

Use o modelo de bug do GitHub, informe build, hardware e passos. A mídia salva
diagnósticos em `X-Revive/diagnosticos/<boot-id>/`. Revise antes de anexar: podem
incluir modelos/séries de discos e dados de rede. Não anexe BIOS, MCPX, EEPROM,
chaves de assinatura, jogos ou discos inteiros.
