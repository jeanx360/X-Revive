# Validação da preparação pública beta.2

A base df48 recebeu relato físico positivo do mantenedor. Esta preparação pública
mantém o binário Xemu e os drivers, separando arquivos particulares. Não equivale
a um novo teste de todas as máquinas físicas. Nenhum disco físico do host foi
alvo do build ou dos testes automatizados.

## Conteúdo e integridade

- 461 pacotes Debian inventariados, com seus 461 avisos de copyright disponíveis.
- 331 versões-fonte, incluindo Built-Using/Static-Built-Using, 1.052 arquivos
  baixados e conferidos por tamanho/SHA256 dos índices deb-src autenticados.
- Fontes Xemu com dependências/submódulos, xone e pyfatx preparados separadamente.
- Sem BIOS/MCPX/EEPROM, executáveis Xbox, ISO de aplicativos ou jogos na IMG.
- Firmware do Xbox Wireless Adapter e chave privada MOK do DKMS retirados do staging.
- Busca de chaves privadas em etc/root/home/var/lib/dkms sem ocorrências.
- Bibliotecas antigas da AppImage retiradas; resolução das bibliotecas Xemu por
  ldd idêntica antes/depois. Hash do binário permanece
  `892784091cc4263ad3449beef70f3fb17b431cc896498069f4df8f489d233034`.
- Partição CONSOLE sem firmware; SYSTEM sem arquivo de debug. Os discos de QA
  são cópias separadas e somente essas recebem debug/arquivos particulares.
- IMG.xz descompactada e conferida por tamanho/SHA256 contra a IMG inteira.
- ZIP de pastas do usuário conferido: nenhuma BIOS, EEPROM, ISO ou chave incluída.

## Ensaios

68 testes passaram na bancada, incluindo novas verificações de limpeza pública,
recusa de caminhos simbólicos e coleta exata de fontes com campos Debian vazios.
O fingerprint passa a ignorar assets privados antigos que não entram no sistema
e inclui os avisos legais copiados para a IMG. Não depende de recriar os assets
privados para ser reproduzido por um clone público.

A IMG pública iniciou UEFI/GRUB e abriu a interface sem firmware. Ao escolher
instalação online nessa condição, exibiu o pedido de bios.bin antes de criar o
staging ou alterar o SSD de teste. Depois, uma cópia QA recebeu firmware/ISO do
mantenedor por compartilhamento somente leitura, sem inseri-los na produção.

A verificação offline concluiu 104 pacotes e 98.996 arquivos sem modificar o
SSD de destino. O auxiliar de teclado precisou aguardar a tela do plano e repetir
uma retenção de F10 após a atualização visual do guest; nenhum ajuste de produto
foi aplicado em RAM para contornar confirmações. A instalação foi operada pela
GUI, sem RPC de mutação. Resultado final e boot SSD são registrados abaixo.

Evidências detalhadas locais: `bancada/validacao-publica-beta2/` e
`cartucho/cache/public-release-beta2/`. Logs/discos particulares não entram no Git.
As notas da release registram hashes e limites. O canal público de atualização
Xemu, o splash BIOS e Xbox físico continuam itens separados da publicação da IMG.

## Instalação completa da IMG pública

A cópia QA instalou 104 pacotes / 98.996 arquivos e conferiu a leitura de volta
com `verified=true`, num arquivo regular de SSD de 32 GiB. O prefixo Xbox ficou
com aproximadamente 28,81 GiB e o restante reservado ao sistema. Firmware e ISO
foram fornecidos apenas à cópia QA. A IMG de produção permaneceu intacta.

Na cópia limpa dos fontes: 68 testes descobertos, 67 passaram e 1 skipped
(UIX com pacote externo não fornecido). O fingerprint dessa cópia coincidiu com
o usado para gerar a IMG pública: não há dependência dos assets privados antigos.
