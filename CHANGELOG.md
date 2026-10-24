# Changelog

## Não lançado — revisão documental

- Download público da IMG, guia, pastas e checksum destacados no início do README.
- Recomendações de balenaEtcher, Raspberry Pi Imager e Discos do GNOME.
- EEPROM opcional aprovada como próxima mudança; implementação e nova IMG pendentes. A beta.2 atual ainda exige os três arquivos.
- Nenhum binário ou artefato de instalação alterado nesta revisão.

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
