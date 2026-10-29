# Changelog

## v0.1.0-beta.5-live.6 — 28/10/2026

- LIVE unificado por mídia ou HDD, com disco virtual/protegido ou escrita explícita em um alvo.
- Wi-Fi, teclado virtual e importação do firmware do dongle antes da interface.
- Progresso animado com etapas/tempo, detalhes, cancelamento e diagnósticos persistentes.
- Recuperação/substituição do boot UEFI em mapa reconhecido, independente do inventário de apps.
- DVD virtual offline sem segunda cópia integral da coleção; mídias XDVDFS diretas.
- 124 testes locais e ensaios de boot/áudio/FTP/proteção/reparo documentados.
- F até o final ainda exige migração específica; redimensionamento automático não incluído.


## Validação e documentação — 2026-10-25

- Beta.4 testada em bancada física e funcionando como esperado.
- Mantidos a imagem, a tag e os checksums da release existente.
- Documentado o fluxo com XREVIVE já formatada, sem boot intermediário.
- Esclarecidos os tamanhos compactado/descompactado e os 10 GiB fixos de dados.
- Priorizados modo LIVE e preservação de HDD Xbox existente, ainda pendentes.
- Auxiliares de bancada com capacidade USB/RAM configuráveis, detecção de falha
  da VM e espera pela conclusão da cópia dos arquivos de teste.

## v0.1.0-beta.4 — 2026-10-24

- EEPROM fornecida pelo usuário opcional; geração nativa pelo Xemu quando ausente.
- Persistência inicial imediata no SSD e reutilização da identidade nos próximos boots.
- BIOS e MCPX continuam obrigatórios; importação de EEPROM existente preservada.
- Interface, guia e pastas do usuário atualizados para os dois fluxos.
- Apresentação pública na voz do projeto e links de download destacados.
- Persistência da EEPROM sem ciclo na inicialização; compilação verifica a transação completa do systemd.

## v0.1.0-beta.3 — candidata não publicada

Retida na validação de reboot por conflito de ordem de inicialização. A tag foi
preservada para rastreabilidade; a imagem corrigida é a beta.4.

## v0.1.0-beta.2 — 2026-10-24

- IMG pública compactada para gravação, com checksum e guia para usuários.
- Modelo de pastas do pendrive sem firmware incluído.
- Removidos firmware do Xbox Wireless Adapter, chave MOK privada e bibliotecas antigas não usadas da AppImage.
- Mesmo Xemu modificado e drivers da bancada; nenhum jogo ou firmware Xbox embutido.
- Fontes Debian exatos, incluindo Built-Using, fontes Xemu/dependências e avisos de licença na release.
- Preparo de imagens futuras aplica a mesma separação de arquivos locais.

## v0.1.0-beta.1 — 2026-10-24

Primeira publicação dos fontes, após retorno positivo de bancada.

- Instalador próprio com Rocky5 online e ISO local normalizada.
- Firmware do usuário separado da mídia base em área exFAT.
- Sistema e FATX no mesmo HDD/SSD, instalação com duas confirmações.
- Manutenção e escolha de dashboard, padrão XBMC4Gamers.
- Bandeja física e patches Xemu SMC / Start+digital para cima.
- UI SDL2/X11, primeira tela sem esperar enumeração e logs no USB.
- Logos de boot/interface e personalização privada de BIOS.
- Cliente Xemu com assinatura, confirmação e reversão; canal público pendente.
- Documentação, testes, contribuições, licenças e limites da beta.

A IMG de bancada é `20261024T163450Z-df48d0e06a6f`; documentação/Git foram
preparados depois desse build. Esta prerelease publica fontes, não a IMG nem
os pacotes particulares dos ensaios.
