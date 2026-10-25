<div align="center">

<img src="cartucho/overlay/usr/share/console/logo.png" alt="X-Revive — logotipo oficial" width="360">

# X-REVIVE

### O hardware pode morrer. O console não.

**Uma nova vida para o Xbox Clássico usando hardware compatível de PC.**
Preservação, reaproveitamento, engenharia e uma experiência feita para jogar no controle.

[![Status](https://img.shields.io/badge/status-beta%20experimental-9ADD58?style=flat-square&labelColor=102015)](docs/BETA.md)
[![Licença](https://img.shields.io/badge/c%C3%B3digo-GPL--3.0--or--later-9ADD58?style=flat-square&labelColor=102015)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/site-GitHub%20Pages-9ADD58?style=flat-square&labelColor=102015)](https://jeanx360.github.io/X-Revive/)

**[🌐 Site oficial](https://jeanx360.github.io/X-Revive/) · [⬇️ Download da beta](https://github.com/jeanx360/X-Revive/releases/tag/v0.1.0-beta.4) · [📖 Instalação](docs/BAIXAR-E-INSTALAR.md) · [🛠️ Contribuir](CONTRIBUTING.md)**

</div>

> [!WARNING]
> **A beta pública v0.1.0-beta.4 APAGA completamente o HDD/SSD escolhido durante a instalação.** Não conecte seu disco original de Xbox para instalar esta versão. O modo que investiga a preservação de FATX existente está **em testes, fora da release pública**. Faça backups antes de qualquer operação com discos.

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
| Instalação de coleção Rocky5 pela rede ou por ISO *normalizada X-Revive* | ✅ Publicada |
| Dashboard XBMC4Gamers, áudio, rede/FTP e operação via controle | ✅ Funcionalidades com testes documentados |
| EEPROM do usuário ou geração inicial pelo Xemu | ✅ Beta.4; identidade preservada no SSD |
| Recuperação/manutenção via USB | ✅ Publicada |
| Atualizações Xemu assinadas | 🧪 Cliente implementado; **canal público ainda indisponível** |
| Usar HDD original FATX preservando os dados e instalar boot UEFI ao lado | 🧪 Pesquisa de bancada **fora desta beta** |
| Usar disco preparado em Xbox físico com modchip | 🧪 Compatibilidade física ainda não conclusivamente validada |
| BIOS totalmente livre e execução direta de XBE sem o Xemu | 🧭 Objetivo de pesquisa de longo prazo |

A compatibilidade de jogos é limitada pelo Xemu, pela configuração e pelo hardware. **Não existe promessa de 100% de compatibilidade.** Veja [o estado de testes da beta](docs/BETA.md) e a [compatibilidade e requisitos](docs/COMPATIBILIDADE.md).

## Download e primeiros passos

**Versão pública de referência:** `v0.1.0-beta.4` · [Página da release](https://github.com/jeanx360/X-Revive/releases/tag/v0.1.0-beta.4)

| Arquivo | Uso |
| --- | --- |
| **[Baixar imagem instaladora (.img.xz)](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.4/x-revive-v0.1.0-beta.4.img.xz)** | Descompactar e gravar em um pendrive de 16 GB ou maior |
| [Estrutura das pastas do usuário (.zip)](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.4/arquivos-do-usuario.zip) | Preparar a pasta de firmware e arquivos autorizados |
| [Checksums SHA256](https://github.com/jeanx360/X-Revive/releases/download/v0.1.0-beta.4/SHA256SUMS.txt) | Conferir a integridade do download |
| [Todas as releases](https://github.com/jeanx360/X-Revive/releases) | Notas, fontes e versões posteriores |

1. Confira o [guia passo a passo](docs/BAIXAR-E-INSTALAR.md) e os [requisitos](docs/COMPATIBILIDADE.md).
2. Descompacte `.img.xz` e **grave a IMG no pendrive inteiro** (ex.: com [balenaEtcher](https://etcher.balena.io/)). Não basta copiar o arquivo para o USB.
3. Na partição `XREVIVE`, extraia as pastas do usuário e coloque seus próprios arquivos `bios.bin` e `mcpx_1.0.bin`; `eeprom.bin` é opcional. **Nenhum firmware proprietário é fornecido.**
4. Inicie o PC pelo USB em modo UEFI. Escolha a coleção Rocky5 online (com Ethernet/DHCP) ou uma ISO offline no formato exigido pelo X-Revive.
5. Escolha **um HDD/SSD de teste dedicado**, verifique modelo/capacidade e confirme a formatação duas vezes. **Todos os dados do destino serão apagados.**
6. Terminada a instalação, retire o USB e inicie o console pelo HDD/SSD.

**Requisitos da beta:** PC x86-64 com UEFI, Secure Boot desativado, pendrive de pelo menos 16 GB, HDD/SSD de teste com pelo menos 32 GiB e menos de 2 TiB, setores lógicos de 512 bytes, firmware Xbox autorizado. Consulte as restrições completas antes de tentar instalar.

**[Guia completo de instalação →](docs/BAIXAR-E-INSTALAR.md)**

## Preservar um HDD original: pesquisa separada

O motivo original do X-Revive continua sendo sua grande ambição: reaproveitar um HDD do Xbox, com suas partições FATX e biblioteca existente, em hardware diferente. Essa linha de pesquisa estuda o reconhecimento de FATX existente e uma área UEFI que preserve o conteúdo original.

**Isso não corresponde ao instalador da beta.4.** Os resultados ainda precisam ser reproduzidos com procedimentos de integridade, backups e diferentes modelos de disco/firmware antes de serem oferecidos como opção de uso público. O modo de instalação limpa é intencionalmente separado dessa pesquisa.

[Leia os limites e critérios de validação da preservação →](docs/PRESERVACAO-HDD.md)

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
