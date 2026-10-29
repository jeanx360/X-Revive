<div align="center">

<img src="cartucho/overlay/usr/share/console/logo.png" alt="X-Revive — logotipo oficial" width="360">

# X-REVIVE

### O hardware pode morrer. O console não.

**Uma nova vida para o Xbox Clássico usando hardware compatível de PC.**
Preservação, reaproveitamento, engenharia e uma experiência feita para jogar no controle.

[![Status](https://img.shields.io/badge/status-beta%20experimental-9ADD58?style=flat-square&labelColor=102015)](docs/BETA.md)
[![Licença](https://img.shields.io/badge/c%C3%B3digo-GPL--3.0--or--later-9ADD58?style=flat-square&labelColor=102015)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/site-GitHub%20Pages-9ADD58?style=flat-square&labelColor=102015)](https://jeanx360.github.io/X-Revive/)

**[🌐 Site oficial](https://jeanx360.github.io/X-Revive/) · [⬇️ Download da beta](https://github.com/jeanx360/X-Revive/releases/tag/v0.1.0-beta.5-live.6) · [📖 Instalação](docs/BAIXAR-E-INSTALAR.md) · [🛠️ Contribuir](CONTRIBUTING.md)**

</div>

> [!WARNING]
> **Instalar X-Revive apaga o HDD/SSD escolhido.** Para usar um HDD Xbox existente, escolha **LIVE → Protegido**: as alterações ficam na RAM. O reparo de boot só grava após aviso e duas confirmações, quando há espaço reservado fora do FATX. Redimensionamento automático de F não está incluído. [Guia dos modos e limites](docs/LIVE-RECUPERACAO-BETA5-LIVE6.md).

## Por que o X-Revive nasceu?

Tudo começou com um **Xbox Clássico danificado por uma enchente**. Para mim, esse sempre foi um console especial: quase um computador, com uma arquitetura que despertou curiosidade desde o primeiro contato.

Com a placa original danificada e uma placa de notebook antiga disponível, nasceu uma pergunta: **seria possível substituir o hardware do Xbox sem perder a identidade, o HDD e os jogos que já estavam ali?**

A investigação cresceu. O que começou como uma tentativa de recuperar um único console tornou-se o **X-Revive** — uma iniciativa open source para preservar a experiência do Xbox original, reaproveitar componentes de PC e compartilhar pesquisas com a comunidade de retrogaming.

**[Leia a história e os princípios do projeto →](docs/HISTORIA.md)**

## A experiência

A proposta é simples: **ligar o computador e entrar no Xbox.** Um Linux minimalista cuida da inicialização, detecção do hardware e serviços em segundo plano; o [Xemu](https://xemu.app/) executa a plataforma Xbox emulada. A interface e a operação são pensadas para teclado **ou** controle compatível, sem precisar abrir um desktop ou iniciar manualmente um programa.

### O que está disponível na beta pública

| Recurso | Situação |
| --- | --- |
| Imagem USB instaladora para PC x86-64 UEFI | ✅ Publicada |
| Instalação limpa em HDD/SSD dedicado, com FATX para conteúdo Xbox | ✅ Publicada; **destrutiva** |
| Boot direto pelo HDD/SSD após a instalação | ✅ Validado em VM na beta |
| Linux minimalista, Mesa e NVIDIA 550 na mesma imagem | ✅ Publicado; suporte varia conforme o hardware |
| Instalação Rocky5 online ou coleção offline; LIVE por HeXEn/OGXbox/XISO do usuário | ✅ Publicada |
| Dashboard XBMC4Gamers, áudio, rede/FTP e operação via controle | ✅ Funcionalidades com testes documentados |
| EEPROM do usuário ou geração inicial pelo Xemu | ✅ Opcional; identidade preservada no SSD |
| LIVE por mídia ou HDD, interno/USB | ✅ Protegido ou escrita explícita no único disco escolhido |
| Wi-Fi no assistente e teclado virtual | ✅ Incluídos; compatibilidade depende do adaptador |
| Recuperação/manutenção via USB | ✅ Reparo de EFI/rodapé recuperáveis, progresso e diagnóstico |
| Atualizações Xemu assinadas | 🧪 Cliente implementado; **canal público ainda indisponível** |
| Usar HDD original FATX preservando os dados e instalar boot UEFI ao lado | 🧪 LIVE protegido e boot com reserva externa; redução de F ainda não automatizada |
| Usar disco preparado em Xbox físico com modchip | 🧪 Compatibilidade física ainda não conclusivamente validada |
| BIOS totalmente livre e execução direta de XBE sem o Xemu | 🧭 Objetivo de pesquisa de longo prazo |

A compatibilidade de jogos é limitada pelo Xemu, pela configuração e pelo hardware. **Não existe promessa de 100% de compatibilidade.** Veja [o estado de testes da beta](docs/BETA.md) e a [compatibilidade e requisitos](docs/COMPATIBILIDADE.md).

## Download e primeiros passos

**Pré-release beta para testes:** `v0.1.0-beta.5-live.6` · [Página da release](https://github.com/jeanx360/X-Revive/releases/tag/v0.1.0-beta.5-live.6)

| Arquivo | Uso |
| --- | --- |
| **[Baixar imagem instaladora (.img.xz)](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.5-live.6/x-revive-v0.1.0-beta.5-live.6.img.xz)** | Descompactar e gravar em um pendrive de 16 GB ou maior |
| [Estrutura das pastas do usuário (.zip)](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.5-live.6/arquivos-do-usuario.zip) | Preparar a pasta de firmware e arquivos autorizados |
| [Checksums SHA256](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.5-live.6/SHA256SUMS.txt) | Conferir a integridade do download |
| [Todas as releases](https://github.com/jeanx360/X-Revive/releases) | Notas, fontes e versões posteriores |

1. Confira o [guia passo a passo](docs/BAIXAR-E-INSTALAR.md) e os [requisitos](docs/COMPATIBILIDADE.md).
2. Descompacte `.img.xz` e **grave a IMG no pendrive inteiro** (ex.: com [balenaEtcher](https://etcher.balena.io/)). Não basta copiar o arquivo para o USB.
3. Na partição `XREVIVE`, extraia as pastas do usuário e coloque seus próprios arquivos `bios.bin` e `mcpx_1.0.bin`; `eeprom.bin` é opcional. **Nenhum firmware proprietário é fornecido.**
4. Inicie o PC pelo USB em UEFI. Use **Configurar rede Wi-Fi** se necessário; há teclado virtual para controle e entrada por teclado físico.
5. Escolha **LIVE → Protegido** para iniciar por uma mídia ou pelo HDD Xbox sem instalar. Ou escolha **Instalar X-Revive** para uma instalação limpa em disco dedicado, com duas confirmações e apagamento do destino.
6. Para boot direto do HDD existente, siga o [guia de preparação/reparo](docs/LIVE-RECUPERACAO-BETA5-LIVE6.md). Não use a instalação limpa para preservar seu disco. A [beta.4 anterior](https://github.com/jeanx360/X-Revive/releases/tag/v0.1.0-beta.4) permanece disponível.

**Requisitos da beta:** PC x86-64 com UEFI, Secure Boot desativado, pendrive de pelo menos 16 GB, HDD/SSD de teste com pelo menos 32 GiB e menos de 2 TiB, setores lógicos de 512 bytes, firmware Xbox autorizado. Consulte as restrições completas antes de tentar instalar.

**[Guia completo de instalação →](docs/BAIXAR-E-INSTALAR.md)**

## Usar um HDD Xbox existente

O LIVE reconhece FATX nativo ou híbrido em unidades internas e USB. No modo protegido, o disco fica somente leitura e as mudanças vão para RAM; ele também pode iniciar com um HDD virtual descartável. Para instalar dentro de uma mídia Xbox, escolha o modo com escrita e autorize somente o disco selecionado.

O assistente pode preparar/reparar o boot UEFI quando existe área de sistema fora dos volumes Xbox. A existência de boot anterior não impede o reparo: ele é substituído após aviso e confirmações. Se F ocupa o disco todo, é necessária uma migração de geometria, **ainda não automatizada nesta release**. Compatibilidade com Xbox físico exige teste específico.

[Modos, limites e evidências de preservação →](docs/PRESERVACAO-HDD.md)

## O futuro: um console por cartucho

O X-Revive é **exclusivamente dedicado ao Xbox Clássico**. A visão mais ampla é permitir que uma pessoa use o mesmo hardware de PC com **SSDs intercambiáveis**, cada um inicializando seu próprio sistema, com interface e experiência características.

Iniciativas futuras como **PS2-Renew** e **Wii/GC-Boot** seriam projetos independentes, não funcionalidades incorporadas ao X-Revive. Há também uma linha de pesquisa de longo prazo sobre firmware livre, engenharia reversa e técnicas alternativas de execução de XBE/tradução de hardware — **ainda não disponíveis**.

[Visão técnica e limites →](docs/VISAO-UNIVERSAL.md) · [Roadmap vigente →](docs/ROADMAP-ATUAL.md)

## Documentação

**[Comece pelo índice da documentação](docs/INDEX.md)**: separa guias atuais, engenharia, relatórios históricos, licenças e maneiras de contribuir.

- **Para usar:** [instalação](docs/BAIXAR-E-INSTALAR.md), [requisitos](docs/COMPATIBILIDADE.md), [estado da beta](docs/BETA.md), [EEPROM](docs/EEPROM-OPCIONAL.md).
- **Para desenvolver:** [arquitetura atual](docs/ARQUITETURA.md), [hardware/HAL](docs/HARDWARE.md), [build e testes](docs/COMUNIDADE-BUILD.md), [roadmap](docs/ROADMAP-ATUAL.md).
- **Para contribuir:** [CONTRIBUTING](CONTRIBUTING.md), [issues](https://github.com/jeanx360/X-Revive/issues), [licenças e componentes de terceiros](THIRD_PARTY_NOTICES.md).

## Licenças e independência

O código original do projeto é distribuído sob **GPL-3.0-or-later**; componentes e patches de terceiros mantêm suas próprias licenças. Consulte [LICENSE](LICENSE), [NOTICE](NOTICE.md), [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md) e [fontes e licenças da imagem](docs/FONTES-E-LICENCAS.md).

O X-Revive é um projeto **independente**, sem afiliação oficial à Microsoft, Xbox, Xemu, Rocky5 ou Cerbios. BIOS, MCPX, jogos, discos, credenciais e demais arquivos proprietários não são distribuídos pelo projeto.

---

<div align="center"><strong>Preservar o passado. Recriar o hardware. Manter o Xbox vivo.</strong><br><sub>Desenvolvido por Jean Vargas / jeanx360 com a comunidade.</sub></div>
