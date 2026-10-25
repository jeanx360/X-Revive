# Arquitetura atual — beta pública v0.1.0-beta.4

Esta página descreve a **arquitetura da imagem de instalação pública**, não todas as propostas e protótipos anteriores. Para registros de pesquisa de épocas diferentes, veja [INDEX.md](INDEX.md). Para o projeto de reaproveitamento de HDD Xbox já existente, leia [PRESERVACAO-HDD.md](PRESERVACAO-HDD.md).

## Visão geral

```text
PC x86-64 com UEFI
        │
        ▼
Pendrive instalador X-Revive
        │  firmware Xbox fornecido pelo usuário
        │  catálogo Rocky5 online OU ISO local normalizada
        ▼
Interface de instalação (teclado ou controle)
        │  valida fontes, destino, geometrias e confirmações
        │  ⚠ APAGA o HDD/SSD selecionado
        ▼
HDD/SSD preparado pelo X-Revive
        ├── boot e serviços Linux minimalistas
        ├── sistema/firmware/perfil e dados auxiliares
        └── área Xbox em FATX com dashboard/jogos/apps
        │
        ▼
Boot UEFI diretamente do SSD/HDD
        │
        ▼
Linux (drivers, HAL, áudio, entrada, rede)
        │
        ▼
Xemu com integração X-Revive
        │
        ▼
Dashboard Xbox / jogos e homebrew
```

**O X-Revive não executa XBE nativamente no processador do PC na beta pública.** O [Xemu](https://xemu.app/) emula a plataforma Xbox, incluindo componentes que não existem em PCs genéricos. O Linux cuida da inicialização e integração com hardware do host. O objetivo é **experiência de console dedicada**, não alegar substituição perfeita de toda a eletrônica Xbox.

## Mídia USB e instalação

A release disponibiliza uma única IMG pública (`x-revive-v0.1.0-beta.4.img.xz`) com suporte previsto a Mesa e NVIDIA 550. Ao gravar a IMG em pendrive de pelo menos 16 GB, uma área `XREVIVE` exFAT fica disponível para arquivos do usuário; as demais partições de inicialização e suporte não devem ser modificadas manualmente.

O instalador aceita **dois fluxos de fonte**, que alimentam a instalação limpa:

- **Online:** catálogo Rocky5 com origens fixadas, HTTPS, validação de tamanho e SHA256, Ethernet/DHCP.
- **Offline:** ISO do formato **normalizado X-Revive** com `payload/manifest.json`. ISOs Xbox arbitrárias de HeXEn, OGXbox ou Rocky Extras Disc não são aceitas diretamente.

Arquivos Xbox necessários na beta: `bios.bin`, `mcpx_1.0.bin`; `eeprom.bin` é opcional. Sem EEPROM fornecida, o Xemu gera uma identidade, que o X-Revive preserva no SSD. A animação proprietária também é opcional e não acompanha a IMG.

## Segurança do instalador público

A beta publicada prepara um **disco de teste dedicado**, com setores lógicos de 512 bytes, pelo menos 32 GiB e menos de 2 TiB. Antes da escrita, a interface valida as fontes, apresenta o destino e exige duas confirmações explícitas (com soltura entre elas). Não é dual boot nem importação de disco anterior.

**A instalação apaga completamente o HDD/SSD selecionado**. O fluxo de preservação de FATX existente proposto para pesquisa **não faz parte da beta.4**. Não transponha procedimentos de bancada antigos para o instalador público.

## Sistema instalado

A instalação coloca o sistema de inicialização e os arquivos necessários no HDD/SSD, além do conteúdo Xbox em **FATX**. Após concluir e remover o pendrive, o PC inicia pelo disco e abre a experiência Xbox com XBMC4Gamers como dashboard padrão. A área de utilitários serve para inventário e manutenção; não duplica toda a coleção de aplicativos fora do FATX. A mídia USB continua útil para recuperação.

A inicialização inclui os serviços do Linux mínimo, seleção de driver disponível, configuração e integração com Xemu. A bandeja de DVD, áudio, rede/FTP e controles possuem implementação/testes com limites documentados em [BETA.md](BETA.md). **Leitores comuns de PC não leem automaticamente discos originais de Xbox.**

## HAL: integração e perfis de hardware

A camada HAL detecta componentes, aplica opções do host e prepara o ambiente para o Xemu. É um mecanismo de regras, **não uma IA que gera drivers**. A imagem pode incluir drivers Mesa e NVIDIA, mas depende do dispositivo real e das exigências de Vulkan/OpenGL e do Xemu. Veja [HARDWARE.md](HARDWARE.md).

## Operação e manutenção

| Ação | Teclado | Controle |
| --- | --- | --- |
| Navegar / selecionar / voltar | Setas / Enter / Esc | Direcional / A / B |
| Confirmação destrutiva no instalador | Segurar F10, soltar e repetir | Segurar LT+RT+Start, soltar e repetir |
| Manutenção no boot do SSD | Segurar R | Start+Back |
| Atualizador Xemu | Segurar U | Y |
| Menu do Xemu | Menu da aplicação | Start + direcional para cima |

O **cliente de atualização Xemu** existe, com mecanismos de assinatura e reversão, mas **não há canal público ativo**. Não atualiza kernel, drivers ou firmware.

## Limites e próximos caminhos

A arquitetura de **preservação do HDD Xbox original**, com FATX existente e possível inicialização por USB/RAM ou UEFI no próprio disco, é uma linha experimental separada, sem distribuição pública no release atual. Compatibilidade de HDD com um Xbox físico modchipado também exige validação específica.

O objetivo de longo prazo de firmware livre e pesquisa de execução direta de XBE não deve ser confundido com o funcionamento atual baseado em Xemu.

## Onde está o código

```text
cartucho/build/     receitas, dependências e patches Xemu
cartucho/overlay/   sistema, interface, instalador, manutenção e atualizador
hal/               detecção/adaptação ao hardware do PC
plataformas/xbox/  integração específica de Xbox
bancada/           ferramentas de ensaio, não instruções para produção
 tests/            testes automatizados
 docs/             documentação, evidências e pesquisas históricas
```

[Guia de instalação](BAIXAR-E-INSTALAR.md) · [Estado de validação](BETA.md) · [Roadmap atual](ROADMAP-ATUAL.md)
