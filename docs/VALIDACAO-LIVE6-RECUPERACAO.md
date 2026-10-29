# Validação local — beta.5-live.6

Relatório da pré-release beta.5-live.6. Publicação autorizada em 28/10/2026.
As evidências distinguem cada candidata, o HDD físico e suas cópias regulares;
a autorização de publicação não representa novo teste físico de todos os fluxos.

## Identidade

Entrega C7: `20261027T053709Z-552b5d0afd85`.
Fonte SHA256: `552b5d0afd85833eb85d92fe633b970177dfd0874b41053ba6312b56118a587d`.
Versão `0.1.0-beta.5-live.6`; kernel `6.12.113+deb13-amd64`, NVIDIA
`550.163.01-2` e Xemu `0.8.138-xrevive-smc2` preservados.

A imagem pública é sanitizada, sem BIOS, MCPX, EEPROM, firmware privado do
dongle ou ISOs/aplicativos particulares. Os arquivos pessoais foram usados
somente nas mídias virtuais de QA. XREVIVE continua exFAT de 10 GiB, pronta
para copiar arquivos após gravar a imagem.

## Arquivos de entrega

- IMG: 14.162.067.456 bytes; SHA256
  `7a927cea318014b92ca6278bc5cf864dd098844fb7bf1de1b3bf1c4362602737`.
- XZ: 1.351.879.292 bytes; SHA256
  `415b14aa4518d38ead4bc9ead1997573e255a32b44484d8e260688683046e16f`.
- Descompressão integral conferiu tamanho e SHA256 da IMG.
- Somente uma IMG permanece em `cartucho/out/`; protótipos ficam no cache.

## Diagnóstico de campo e disco real

O relato anterior do Dell G15 trouxe falta de espaço para adaptar a coleção,
recusas de manutenção/boot e esperas sem feedback. O controle sem fio desde
o início foi confirmado fisicamente naquela live.5. Não houve logs físicos
para estabelecer a causa exata das esperas; não afirmar que a VM a reproduziu.

Foi examinado o HDD WDC WD10SPZX-21Z10T0, 1.000.204.886.016 bytes. Os SSDs do PC foram identificados separadamente e
não foram alvo dos testes. A tabela PARTINFO informa F até o final do disco;
o cabeçalho GPT antigo no último setor não corresponde a espaço de sistema
independente dos volumes Xbox.

Foi criada uma cópia esparsa de metadados e todos os blocos FATX alocados:
10.809.397.248 bytes em 17 regiões, incluindo tabela inicial e último MiB.
Ela não é uma cópia forense de todos os setores livres. O HDD real foi aberto
**O_RDONLY no host** e entregue à VM por descritor somente leitura. Mesmo um
processo privilegiado na VM não poderia convertê-lo em acesso de escrita.
Nenhum protetor global de discos do appliance foi executado no Linux do PC.

A reserva de 3.424.346.112 bytes, cerca de 3,19 GiB, foi provada somente em
arquivo-clone. Reduzir F muda o tamanho derivado da FAT: foi necessário
reposicionar os dados alocados 208.896 bytes, e não apenas mudar PARTINFO.
Os hashes foram preservados. Não houve migração no HDD físico. A operação não está automatizada nesta
release e exige um procedimento específico de migração e recuperação.

## Ensaios concluídos

| Ensaio | Resultado e limite |
|---|---|
| Fontes C7 | 124 testes passaram; sintaxe dos módulos e `git diff --check` conferidos. Transação systemd e estrutura da imagem verificadas na montagem. |
| HDD físico, C5/C6 | LIVE protegido sem mídia iniciou o XBMC4Gamers e chegou à seleção do perfil existente. Só leitura real no host, loop somente leitura e alterações temporárias em RAM. Não equivale a boot físico no Dell. |
| Interface C6, HDD real protegido | Preparação de hardware deliberadamente lenta apenas na VM. Logo e faixa da barra variaram entre capturas; consultas de estado responderam durante a espera. F1 mostrou histórico; Esc cancelou e liberou sessão/mapeamentos. Registro JSONL de etapas e cancelamento conferido no USB. O script de hardware original foi restaurado. |
| Prazo de configuração C6 | Filho de hardware aguardou deliberadamente além de 90 s. A preparação retornou erro com prazo, serviço continuou respondendo, sessão foi liberada e HDD permaneceu protegido. Instrumentação apenas na VM. |
| HeXEn C6, HDD físico protegido | Boot, áudio ativo e FTP com escrita/leitura de 4 MiB em E, SHA256 `2b07811057df887086f06a67edc6ebf911de8b6741156e7a2eb1416a4b8b1b2e`. Escrita foi para RAM; acesso direto de escrita ao HDD recusado. A rede foi NAT de QA, não Wi-Fi externo. |
| Reserva de espaço, C1 | Clone de 1 TB recebeu boot após o FATX e iniciou XBMC4Gamers sem pendrive. Blocos alocados conferidos após a reserva e após preparar boot, antes da dashboard fazer suas escritas normais. |
| Reparo de rodapé, C6 | Rodapé de clone removido deliberadamente. Manutenção recuperou mapa pela ESP, mostrou aviso e exigiu as duas confirmações. SYSTEM atualizada e boot reconstruído; 15 regiões de metadados/blocos alocados FATX permaneceram idênticas. |
| Reparo de EFI, C7 | Bootloader EFI de clone substituído por conteúdo inválido, rodapé íntegro e inventário de apps ausente. Manutenção reconheceu o HDD e concluiu substituição do sistema/boot após duas confirmações. |
| Preservação e SSD sozinho, C7 | As mesmas 15 regiões FATX permaneceram idênticas após o reparo, antes de iniciar o Xbox. Boot somente pelo SSD, sem pendrive: rootfs/rodapé C7, áudio ativo e tela de perfis XBMC4Gamers com o perfil existente. O arquivo histórico de identificação em CONSOLE permanece o da instalação original; a identidade executada é a de `/usr/share/console/build.json`. |
| Coleção offline, C7 | Boot por DVD virtual `/dev/nbd0` somente leitura, áudio, FTP e proteção do HDD USB virtual passaram no assistente de entrega, reutilizando o USB com menos de 1 GiB livre. |
| OGXbox original, C7 | Boot pelo assistente com HDD virtual temporário, áudio, FTP e EEPROM passaram. Leitura direta da XISO, sem copiar ou modificar a mídia. |
| DVD virtual, C1 | Coleção Rocky5 iniciou, áudio/FTP/proteção passaram com apenas 998 MiB livres no USB. Todos os 4.825.088.000 bytes do DVD virtual corresponderam à imagem adaptada anterior: SHA256 `3c697c8db78565abe9fcbfbc01c19836e17d0103a4bdece28ea843468d6b370e`; zero bytes adicionais usados no USB. |

C7 altera em relação à C6 somente a leitura de informação da manutenção:
a falta de inventário de aplicativos passa a oferecer LIVE/reparo, sem ser
pré-requisito para o boot. UI, driver, configuração, proteção e DVD virtual
mantêm os mesmos fontes da C6. Em relação à C1, `xiso.py` e `live_media.py`
permanecem idênticos; `virtual_disc.py` mudou somente a publicação atômica do
arquivo de prontidão. A composição dos bytes do DVD permanece igual.

## Falhas encontradas e limites

- C5 copiou SYSTEM e regravou o boot, mas reportou falha ao voltar uma partição
  para RO. A tabela estava sendo relida; o disco acabou protegido, porém a
  operação reportou erro. C6 protege primeiro o disco inteiro, depois seus
  filhos, e tolera apenas o desaparecimento de uma partição cujo disco já foi
  protegido. Falha na proteção do disco continua sendo erro. O reparo e dois
  testes de regressão passaram. A sequência exata do evento original não foi
  rastreada no kernel.
- C6 ainda exigia o inventário dos aplicativos de um HDD com boot preparado a
  partir de FATX existente. C7 removeu essa dependência para recuperar boot;
  comparar aplicativos/escolher dashboard instalada ainda requer inventário.
- O primeiro coletor serial de boot antigo podia confundir a confirmação
  assíncrona de início com conclusão; os resultados foram lidos pelo job real.
  Entrada de teclado antes de a interface carregar e a recusa de abrir um
  bloco O_RDWR pelo backend físico também exigiram ajustes somente nos
  coletores de QA. A recusa O_RDWR é o resultado esperado da proteção.
- No perfil XBMC existente, uma tentativa de FTP não recebeu banner dentro do
  prazo. O ensaio de FTP concluído nesta rodada usa HeXEn e nomes relativos
  após `CWD /E`. Não atribuir a ele uma validação FTP desse perfil XBMC.
- Não foram repetidos o pareamento físico do controle, a GPU do Dell, FTP
  externo Wi-Fi, nem o boot no Xbox original. As confirmações anteriores de
  bancada continuam identificadas pela rodada em que ocorreram.

## Evidências locais

Raiz de evidências: `cartucho/cache/live6-field/` (fora da distribuição).

- `physical-before.json`, `physical-preservation.json`, `physical-after-proof.json`:
  mapa real, cópia/hash inicial e conferência de preservação em leitura.
- `reserve-proof.json`, `boot-preservation.json` na pasta de QA C1:
  reserva e preparação somente no clone.
- `identity1.json`, `identity6.json`, `identity7.json`, `tests-final7.log`,
  `build7.log`, `mapper-c1-c7-proof.json` e `hashes-final7.json`:
  identidade e verificações correspondentes.
- `c6-repair-content-proof.json`, `c7-repair-content-proof.json`:
  hashes FATX após reparos, antes de iniciar a dashboard.
- `qa-c6-physical.log`, `qa-c6-timeout-result.log`, `qa-c7-repair-efi.log`,
  `qa-c7-ssd-2.log`, `qa-c7-vdisc.log`, `qa-c7-ogx.log`: resultados nomeados por ensaio.
  A comparação integral do DVD está em
  `bancada/validacao-live6-c1-virtual-rocky/virtual-full-proof.log`.

Capturas e sessões: `bancada/validacao-live6-c6-physical/`,
`validacao-live6-c6-repair/`, `validacao-live6-c7-repair-efi/`,
`validacao-live6-c1-virtual-rocky/`, `validacao-live6-c7-virtual-rocky/` e
`validacao-live6-c7-ogx/`.
Os protótipos C1–C6 não são a imagem de entrega C7.

## Próxima bancada

Regravar o pendrive com a candidata indicada e seguir o
[guia LIVE e recuperação](LIVE-RECUPERACAO-BETA5-LIVE6.md). Conferir no Dell
G15 e Xeon os caminhos protegidos, mídias offline, controle, áudio, FTP e
recuperação em disco com reserva externa ao FATX. O HDD físico de 1 TB não
foi tornado bootável nesta rodada; a migração de sua geometria permanece separada
da autorização de publicar esta pré-release.
