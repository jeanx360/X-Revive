# Documentação do X-Revive

Este é o índice **vigente para a versão pública v0.1.0-beta.4**. Ele distingue instruções de usuário, documentação de engenharia, experimentos ainda não distribuídos e registros históricos. Consulte primeiro o [estado da beta](BETA.md).

> **Segurança:** a beta.4 executa **instalação limpa com apagamento do disco selecionado**. O projeto de preservação de HDD original com FATX existente **não** faz parte dessa release. Não use o HDD original para testar o instalador público.

## Quero usar a beta publicada

| Guia | Conteúdo |
| --- | --- |
| [Baixar e instalar](BAIXAR-E-INSTALAR.md) | IMG correta, pendrive, firmware do usuário, instalação e manutenção |
| [Compatibilidade](COMPATIBILIDADE.md) | Requisitos verificáveis, GPUs, limites e o que não está garantido |
| [Estado da beta](BETA.md) | Testes publicados, limitações e funcionalidades |
| [EEPROM opcional](EEPROM-OPCIONAL.md) | Importação de identidade existente ou geração pelo Xemu |
| [Instalador online/offline](INSTALADOR-ONLINE.md) | Fluxo detalhado, ISO normalizada, logs e recuperação |
| [Releases](releases/v0.1.0-beta.4.md) | Inventário da versão pública beta.4 |

## Quero conhecer e desenvolver

| Documento | Conteúdo |
| --- | --- |
| [A origem do projeto](HISTORIA.md) | O Xbox da enchente, o notebook antigo e a missão de preservação |
| [Arquitetura atual](ARQUITETURA.md) | Funcionamento da beta pública: USB, instalador, SSD, FATX, Xemu |
| [Hardware e HAL](HARDWARE.md) | Compatibilidade de hardware e detecção de drivers |
| [Roadmap vigente](ROADMAP-ATUAL.md) | Entregue, em validação e pesquisa futura |
| [Pesquisa de preservação](PRESERVACAO-HDD.md) | Pesquisa sobre reaproveitamento de HDD FATX existente |
| [Visão multi-cartucho](VISAO-UNIVERSAL.md) | Futuras plataformas independentes, sem confundir com a beta atual |
| [Build e testes](COMUNIDADE-BUILD.md) | Como reproduzir testes e trabalhar no projeto |
| [Como contribuir](../CONTRIBUTING.md) | Regras de contribuição, testes, terceiros e issues |

## Licenças e material de terceiros

[LICENSE](../LICENSE) · [NOTICE](../NOTICE.md) · [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) · [Fontes e licenças da IMG](FONTES-E-LICENCAS.md)

Nenhuma versão pública do projeto distribui BIOS/MCPX originais, jogos, EEPROM de terceiros ou outros dados particulares. O nome e as artes do projeto possuem tratamento próprio conforme os avisos de licença.

## Registros históricos e relatórios

Os documentos a seguir registram **decisões, testes e propostas da época em que foram escritos**. Alguns mencionam arquiteturas antigas (várias IMG, HDD FATX separado, HeXEn/OGXbox embutidos, diferentes drivers ou fluxos de instalação). **Não os utilize como instruções de instalação da beta pública atual.** São preservados para rastreabilidade:

- [ROADMAP-BETA.md](ROADMAP-BETA.md), [ROADMAP.md](ROADMAP.md) e [ROADMAP-2026-10-23.md](ROADMAP-2026-10-23.md): planejamento anterior e decisões de bancada.
- [STANDALONE-EXPERIMENTAL.md](STANDALONE-EXPERIMENTAL.md): estudo do disco único com FATX e boot UEFI, **não equivale ao modo de preservação pronto para download**.
- [IMAGENS-UNIVERSAL-NVIDIA.md](IMAGENS-UNIVERSAL-NVIDIA.md), [ESTAGIO2-INSTALADOR.md](ESTAGIO2-INSTALADOR.md), [INSTALADOR-ROCKY5.md](INSTALADOR-ROCKY5.md): etapas históricas de imagem e instalação.
- [VALIDACOES.md](VALIDACOES.md), [BANCADA-REAL.md](BANCADA-REAL.md) e arquivos `VALIDACAO-*.md`: evidências com data, ambiente, condições e limites próprios.
- [Branding técnico](branding/README.md), [patch da bandeja](XEMU-SMC-TRAY.md), [atualizador](ATUALIZADOR-XEMU.md): estudos e implementação específica.

**Regra editorial:** quando a documentação histórica divergir da beta, prevalecem `README.md`, `BETA.md`, `BAIXAR-E-INSTALAR.md`, `ARQUITETURA.md` e a release publicada. O código e os testes devem ser usados como referência final ao alterar uma funcionalidade.
