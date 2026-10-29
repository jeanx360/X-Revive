# Validação local — beta.5-live.5

A release pública continua beta.4. Esta candidata precisa da confirmação física
correspondente antes de push, tag, pré-release ou atualização do site.

## Imagem de entrega

- Versão: `0.1.0-beta.5-live.5`.
- Candidata C6: `20261027T003429Z-56899de0a324`.
- Fonte SHA256: `56899de0a32414a5ad629535de9e2468997c117c34d8bba1c5d63b8a98a66d54`.
- IMG: 14.162.067.456 bytes; SHA256
  `147db43a1b28eda8e4d7627ee1fa0bcc7fbe7dcbfac8463cbf07f9e6209f34df`.
- XZ: 1.351.811.600 bytes (aproximadamente 1,35 GB); SHA256
  `bcf526d82aa0d0eb023948f45e1bdadaf61d126cc9c3d0c44e7d31d51d1154a8`.
- Descompressão integral reproduziu tamanho e SHA256 da IMG.
- Kernel `6.12.113+deb13-amd64`, NVIDIA `550.163.01-2` e Xemu
  `0.8.138-xrevive-smc2` preservados. Partição XREVIVE exFAT pronta, 10 GiB.
- IMG sanitizada: sem BIOS, MCPX, EEPROM, firmware privado do dongle, aplicações
  Xbox ou ISOs pessoais. Arquivos particulares só entram nas cópias virtuais
  de QA, nunca na imagem de distribuição.

## Relato físico que motivou a revisão

Na live.4, o Dell G15 abriu rapidamente o assistente; Wi-Fi e teclado físico
funcionaram. HeXEn iniciou. O dongle não funcionou e duas mídias falharam:
`default.xbe` ausente e recusa da coleção de instalação. O OGXbox original
indicado tem `default.xbe` na raiz e passou no inspetor antigo; a causa exata
do erro na cópia do pendrive não foi reproduzida. A coleção `rocky5-offline.iso`
é ISO9660 com `payload/manifest.json`, recusada explicitamente pelo LIVE antigo.
Agora recebe adaptação no cache, preservando o original.

## Resultados e identidade de cada ensaio

| Ensaio | Evidência e limite |
|---|---|
| Verificação local | 111 testes C6 passaram; sintaxe e `git diff --check`; transação systemd e GPT conferidas na montagem. Fonte coincide com a identidade da IMG. |
| C6 OGXbox original, HDD virtual | Boot pela interface unificada, áudio, FTP STOR/RETR, EEPROM e proteção do disco de dados. |
| C6 HeXEn, HDD USB protegido | Boot, áudio, FTP e EEPROM; HDD somente leitura com qcow2 em RAM; escritas diretas nos discos protegidos recusadas. |
| C5 coleção Rocky5 offline + leitor C6 | Adaptação ISO9660 → XDVDFS, menu e XBE conferidos por FTP; escrita somente no HDD USB escolhido após duas confirmações. Cópia nativa concluída; 98.996 arquivos, 4.665.442.926 bytes, todos os SHA256 correspondem à ISO original, incluindo 49 arquivos vazios e 13 nomes de sinopses adaptados. |
| C5 USB conectado após o assistente | HDD Xbox virtual de 24 GiB foi reconhecido e protegido automaticamente; escolhido pelo fluxo normal, com controle virtual presente antes de iniciar o Xbox. |
| C5 segundo USB conectado durante a sessão com escrita | Disco de dados novo recebeu RO automaticamente; o HDD autorizado permaneceu RW, sem expor outro disco ao Xbox. |
| C5 adaptador físico Microsoft | `045e:02fe` passado reversivelmente à VM; firmware importado antes da interface, xone vinculado e ativação do rádio/pareamento aceita. Sem controle físico ativo: navegação pareada no Dell ainda precisa de teste. |
| C5 instalação normal completa | SSD USB virtual vazio de 24 GiB; 104 pacotes e 98.996 arquivos gravados e verificados; disco de dados separado com hash integral preservado. |

C6 acrescenta somente o tratamento de arquivo FATX vazio ao código da C5.
O Xbox pode gravar tamanho zero com cluster inicial zero, enquanto nosso leitor
anterior tentava percorrer uma cadeia inexistente e emitia `cadeia FATX inválida`.
A correção aceita o arquivo vazio; arquivo não vazio com cluster zero continua
sendo rejeitado. O teste de regressão cobre os dois casos. A conferência final
do HDD foi feita em leitura, com a VM desligada, usando o leitor corrigido.
O erro no coletor antigo não era evidência de corrupção da cópia: os hashes
integrais posteriores e a tela nativa "Concluído" registram o resultado completo.

O modo com escrita apresenta um dispositivo de bloco ao Xbox para a mídia
escolhida pelo usuário. A instalação normal do sistema, com boot próprio de PC,
é outro caminho. Todos os HDDs/SSDs de QA são arquivos regulares QEMU. A única
passagem de hardware foi o adaptador de controle, sem mudar permissões do host.

## Ensaios anteriores e regressões encontradas

Os protótipos anteriores não são artefatos de entrega. Seus resultados continuam
identificados pela build em que ocorreram:

- **C4 instalação normal completa:** SSD USB virtual vazio de 24 GiB, 104 pacotes
  e 98.996 arquivos gravados e verificados; disco de dados preservado; firmware
  do dongle copiado ao SSD.
- **C4 SSD sem pendrive:** boot próprio, áudio, EEPROM e firmware do dongle a
  partir de CONSOLE; tela inicial XBMC4Gamers de adicionar usuário. FTP login e
  `CWD /E` seguido de STOR/RETR relativos passaram. Rádio físico também aceitou
  ativação com firmware vindo do SSD.
- **C3 Wi-Fi:** teclado físico, senha oculta, desconectar, senha errada, recuperar
  por controle virtual, WPA2/DHCP e download HTTPS real, usando mac80211_hwsim
  isolado. Não substitui o teste físico de Wi-Fi/FTP desta candidata.
- **C4 reprovada em teste tardio:** o udev não encontrava `blockdev` no PATH;
  discos conectados depois podiam ficar RW. C5 usa caminhos absolutos e repetiu
  o ensaio real de conexão antes e durante a sessão.
- **C4 cópia nativa interrompida:** `f/Emulators/amiga/Synopsis/Bun for Barney, A.txt`
  foi lido do DVD com SHA correto, mas a criação no FATX foi recusada. Não era
  falta de espaço nem limite de entradas do diretório. A receita 2 adapta apenas
  nomes de sinopses TXT incompatíveis, mantendo cada conteúdo e registrando
  as 13 renomeações em `XREVIVE-NAMES.json`; aplicações e recursos ficam intactos.

A receita 2 também invalida o cache gerado antigo. Se precisar de espaço, remove
somente cache de receita anterior da mesma origem cujo hash de saída confere;
a ISO pessoal e arquivos desconhecidos permanecem intactos.

## Integridade e evidências locais

Nos ensaios C5/C6 HeXEn, todos os 12 GiB do HDD protegido permaneceram idênticos. O hash é
`914b13d2f0ec79ad04ca5df977d13a84b56c108ca27e6245e8ef4cb6fcdcffc6`.
O disco de dados GPT/ext4 de 1 GiB tem SHA256
`92273d1de9c917e3b8f717ac62167aaae09751cdbc264ca995961cdecc10eaab`.
No modo com escrita, o HDD escolhido deve mudar: a integridade exigida se aplica
aos discos excluídos. Os guards de C5 OGX, coleção (inicial e tardio) e instalação normal ficaram idênticos; resultados integrais nos JSON de QA.

- `cartucho/cache/live5-unified/identity6.json`, `hashes-final6.json`,
  `tests-c6.log`, `build6.log` e `qa-c6-*.log`; `identity5.json` identifica
  os ensaios C5.
- `bancada/validacao-live5-c6-ogx/` e `validacao-live5-c6-hexen/`: boot final.
- `bancada/validacao-live5-c5-instalacao/`: instalação completa C5.
- `bancada/validacao-live5-c5-ogx/`: sessão, guards, rádio físico e capturas.
- `bancada/validacao-live5-c5-hexen/`: HDD USB protegido, FTP e integridade.
- `bancada/validacao-live5-c5-colecao/`: hotplug, duas confirmações, menu,
  cópia nativa, `native-full-verification.json`, conferência e integridade
  dos discos excluídos.
- `bancada/validacao-live5-final-instalacao/`: instalação **C4**, `ssd-boot` e
  `ssd-boot2`, firmware no SSD, tela XBMC4Gamers e FTP.
- `bancada/validacao-live5-final-wifi-ogx/`: Wi-Fi **C3**.
- `bancada/validacao-live5-c4-colecao-hotplug/`: erros tardios reais do protótipo.

Pastas antigas com "final" no nome não substituem a identidade real da build.
Os dados particulares e discos virtuais de QA não são arquivos de distribuição.

## Particularidades da instrumentação

Pulsos curtos de controle podem ser perdidos pela emulação aninhada com vídeo
por software; os menus foram inspecionados antes de confirmar. Coletores
assíncronos aguardam arquivos de resultado, pois a janela serial é curta.
No XBMC FileZilla, `STOR /E/arquivo` era interpretado na raiz virtual e recusado;
`CWD /E` com nomes relativos funcionou. A preferência `net_interface=none` só
foi aplicada nos pendrives virtuais para o NAT aninhado; o padrão público segue
automático. Nenhuma dessas adaptações de QA altera a IMG pública.

## Pendências de bancada e publicação

Regravar o pendrive com C6; copiar firmware Xbox e do dongle; testar pareamento
e navegação real no Dell e no Xeon, OGXbox/HeXEn/Rocky5 offline, proteção de disco
e escrita somente em HDD/SSD USB dedicado. FTP externo via Wi-Fi merece teste
próprio: a conexão HTTPS/NAT na VM não o substitui.

Xbox original exige teste separado de BIOS, versão do console, EEPROM e trava
ATA. O fluxo não bloqueia/desbloqueia o HDD físico: indicação de trava no Xbox
virtual não prova trava real. Após a confirmação física, revisar inventário de
fontes/licenças das novas dependências, atualizar site/downloads e publicar
como **pré-release beta**.
