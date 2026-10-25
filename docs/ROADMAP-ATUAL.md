# Roadmap do X-Revive — estado público em 25/10/2026

O X-Revive é dedicado ao **Xbox Clássico**. Este roadmap é a referência editorial vigente e distingue **entrega pública**, **testes ainda necessários** e **pesquisa futura**. O histórico detalhado de decisões está em [ROADMAP.md](ROADMAP.md) e [ROADMAP-2026-10-23.md](ROADMAP-2026-10-23.md); esses documentos não são instruções da beta atual.

## ✅ Disponível na beta pública v0.1.0-beta.4

- **Uma IMG instaladora** para PC x86-64 UEFI com Mesa e NVIDIA 550 incluídos.
- **Instalação limpa** de HDD/SSD dedicado, com duas confirmações e boot próprio posterior.
- **Coleção Rocky5** obtida online ou carregada de ISO offline **normalizada X-Revive**.
- **FATX** no armazenamento Xbox, XBMC4Gamers como dashboard padrão e manutenção.
- **BIOS e MCPX fornecidos pelo usuário**, com EEPROM opcional (geração pelo Xemu ou importação do backup do usuário).
- Operação do instalador por **teclado ou controle**; suporte documentado a rede/FTP, áudio e funções de bandeja.
- Código, testes, relatórios, fontes e licenças publicados com a release.

**Segurança:** instalação limpa **apaga o disco de destino**; não é migração nem preservação de HDD original.

## 🧪 Em validação ou aprimoramento

- Reproduzir testes da beta.4 em **mais máquinas físicas**, incluindo diferentes GPUs, placas-mãe, unidades de armazenamento e controladores.
- Avaliar compatibilidade de **HDDs Xbox originais** e uso de partições FATX preexistentes, com verificação integral, backup e retorno seguro; **pesquisa fora da beta pública**.
- Validar, em hardware Xbox **real** e BIOS compatível, o uso de discos preparados pelo projeto; não extrapolar resultado de VM.
- Melhorar tratamento de erros, recuperação de energia/boot e apresentação dos diagnósticos.
- Investigar splash visual da BIOS e verificar todos os caminhos de botão Eject/dashboards por leitor real.
- Hospedar e ativar **canal público de atualização Xemu assinado**; o cliente atual não equivale a serviço ativo.
- Registrar cobertura gráfica por GPU e progresso real de jogos, sem prometer desempenho universal.
- Fortalecer reprodutibilidade do build (snapshots e dependências fixadas).

## 🧭 Visão de longo prazo

- Experiência progressivamente mais integrada e fiel ao Xbox original.
- Pesquisa de uma **BIOS/firmware livre**, reduzindo dependência de código proprietário onde isso for técnica e juridicamente viável.
- Investigar arquiteturas alternativas de execução de `.xbe`, reimplementação de APIs e tradução de comportamento da GPU NV2A; objetivo de pesquisa, **não funcionalidade existente nem promessa de 100% de compatibilidade**.
- Reaproveitamento da base de detecção e inicialização em **outros projetos independentes** — por exemplo, PS2-Renew e Wii/GC-Boot — cada um com seu próprio sistema e mídia, sem misturá-los ao X-Revive.
- Protótipo de máquina modular com gabinete reaproveitado e **SSDs intercambiáveis**, operação integral por controle e leitor óptico sujeito à compatibilidade de cada plataforma.

## Como colaborar

Leia [CONTRIBUTING.md](../CONTRIBUTING.md), [COMPATIBILIDADE.md](COMPATIBILIDADE.md) e [PRESERVACAO-HDD.md](PRESERVACAO-HDD.md). Proponha um teste reproduzível por issue e identifique se ele foi realizado em **VM**, **PC físico** ou **Xbox físico**. Sem dados/firmware particulares anexados.

[Índice](INDEX.md) · [Estado da beta](BETA.md) · [Visão multi-cartucho](VISAO-UNIVERSAL.md)
