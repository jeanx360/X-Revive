# Roadmap do X-Revive — 28/10/2026

X-Revive dedicado ao Xbox Clássico. Pré-release atual: **v0.1.0-beta.5-live.6**.

## Disponível

- Uma IMG Mesa/NVIDIA com XREVIVE pronta; baixar, gravar, copiar arquivos e iniciar.
- Instalação limpa Rocky5 online/coleção offline e boot próprio do SSD.
- LIVE protegido ou escrita explícita em HDD/SSD interno/USB, por mídia do usuário ou HDD sem mídia.
- Wi-Fi no assistente, teclado físico/virtual e importação do firmware do dongle.
- Interface responsiva, etapas/tempo, animação, detalhes e cancelamento da preparação.
- Preparação/reparo de UEFI em área fora do FATX, inclusive mapas recuperáveis.
- EEPROM opcional, áudio/rede/FTP e bandeja integrados ao Xemu com patches próprios.

## Próximas prioridades

1. Ampliar a matriz física Dell/Xeon e outros PCs, mídias, USB, Wi-Fi/FTP e controle.
2. Projetar migração de HDD com F até o final, preservando dados e com recuperação
   de interrupção. Reserva em clone já demonstrada; não é automática na release.
3. Testar discos preparados em Xbox original e registrar BIOS, EEPROM e trava ATA.
4. Ativar canal público Xemu com manifesto assinado e ofertas validadas.
5. Melhorar cobertura de GPU, tratamento de falhas e reprodutibilidade do build.

A área pessoal continua fixa em 10 GiB; expansão automática para todo pendrive
maior permanece pendente. O fluxo que exigia primeiro boot e retorno ao PC foi
rejeitado. A instalação limpa apaga o destino; LIVE e reparo têm escolhas próprias.

## Visão futura

Experiência de console fiel, pesquisa de firmware livre e arquiteturas de
execução XBE, sem prometer compatibilidade total. PS2-Renew/Wii-GC seriam
projetos separados; SSDs intercambiáveis e gabinete modular permanecem visão.

[Validação](VALIDACAO-LIVE6-RECUPERACAO.md) · [Limites da preservação](PRESERVACAO-HDD.md) ·
[Contribuir](../CONTRIBUTING.md) · [Histórico](ROADMAP.md)
