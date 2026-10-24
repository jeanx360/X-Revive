# Validação online/local e diagnóstico da tela preta

**Atualização de 24/10/2026:** após corrigir a estrutura das pastas no USB, o
mantenedor informou que funcionou como esperado e autorizou publicar como beta.
Esse relato não especifica uma nova matriz completa de modos/máquinas. As
pendências de bancada e ausência de Git mencionadas abaixo descrevem o momento
dos ensaios, anterior à preparação da publicação. Veja [BETA](BETA.md).

Relato físico: imagem 730645d7124c demora no logo e termina preta com cursor,
tanto na bancada anterior quanto no Dell G15. Desligamento pelo botão exibe
logo/Desligando. Isso invalida a aceitação física do instalador anterior,
embora os ensaios anteriores com virtio tivessem passado.

A VM com a mesma IMG abriu o instalador usando a seleção SDL padrão. Ao forçar
SDL_VIDEODRIVER=wayland, caminho que launch.sh impunha para NVIDIA, obteve-se
preto com processo da interface ativo. Capturas e serial em
`bancada/diagnostico-tela-preta/`. As tentativas seguintes precisaram encerrar
explicitamente o processo Pygame que estava fora do cgroup por PAM; não
confundir a captura preta durante um stop pendente com um teste de renderer.

Correção candidata: interfaces SDL2 em X11/XWayland com renderer software,
independentemente do backend SDL3 do Xemu. Inicialização só dos subsistemas SDL
necessários, primeira tela sem bloquear na enumeração de discos; sondagem
Vulkan limitada e diagnósticos persistentes no próprio USB.
A imagem física ainda exige novo ensaio; sem seus logs não se pode afirmar
que esta foi a única causa nas duas máquinas.

Baseline e fontes preservadas em cartucho/cache/baseline-730645-antes-online.
Não há Git inicializado no projeto, branch/remote inexistentes. Nenhuma
publicação GitHub. Nenhum SSD/HDD físico é alvo dos ensaios automatizados.

64 testes automatizados passaram antes do primeiro build em
`cartucho/cache/testes-online-prebuild.log`, incluindo assinatura real do
catálogo, adulteração, escape de caminhos, inventário duplicado, links
simbólicos, firmware ausente e firmware alterado sem escrita no destino.
Resultados de integração e identidade final serão acrescentados após ensaio.

## Primeira integração 88262d3e1051

IMG 20261024T161614Z-88262d3e1051 teve instalação offline completa pela UI,
104 pacotes e 98.996 arquivos lidos de volta. Disco virtual 64 GiB,
34a04767, prefixo Xbox 60,81 GiB e UTILS reduzida a 64 MiB contendo o inventário.
Firmware importado conferido por hash; manifesto persistido tem dez dashboards.
`bancada/validacao-online-offline/offline-install-proof.json`,
`cartucho/cache/instalacao-offline-resume.log` e capturas
`confirmation-real-1.png`, `confirmation-real-2-held.png`.

A primeira automação disparava F10 antes de terminar a preparação do plano;
a proteção recusou esse gesto. O ensaio concluído aguardou a tela e usou
holds de 3,5s, com soltura e cancelamento conferidos. Helpers também precisaram
tratar result=null durante jobs e esperar a cópia 9p terminar antes de usar a
serial. Esses problemas de instrumentação não foram corrigidos no produto em
RAM. A ISO copiada foi integralmente validada antes da instalação.

Boot SSD sem USB com cópia privada da BIOS modificada iniciou animação Xbox,
XBMC4Gamers e ALSA RUNNING. SHA BIOS cbe348907016498c7efef5ba9978d5cb30de56a61b602dcf15f655c126e6548e;
original c5e9d940faf66692b56a16f7a7d779445c1c6d9191d7e7e31c1c1e8168da0733 intacto.
O SVG persistiu na BIOS reaberta no editor e só SplashData mudou no JSON de
configuração. O splash BIOS não apareceu nos frames da VM; não alegar
validação visual completa. Provas e limites em `docs/branding/README.md`.

## Candidato final df48d0e06a6f

20261024T163450Z-df48d0e06a6f, fonte
df48d0e06a6fbc3b4302ffa7d799155a7fd8456520702aad4f6e5e7775a832d7.
Acrescentou progresso durante a verificação de pacotes e leitura do inventário
do SSD para manutenção via USB. 64 testes passaram novamente após essas
alterações. Repack usa rootfs Debian/NVIDIA do build local anterior, copiando
os fontes atuais e regenerando identidade/IMG; log `repack-online-final.log`.
A geração exFAT não monta imagens dentro de container rootless. Diretórios
são criados no primeiro boot ou fornecidos pelo dono ao copiar X-Revive.

A cópia QA final muda somente /debug e a partição de arquivos do usuário.
Ela conferiu novamente todos os pacotes offline, com SSD intacto;
`cartucho/cache/final-offline-prepare.log`, `offline-prepare.json` e captura
`offline-ready.png` em `bancada/validacao-online-final/`.
Leitura do inventário instalado por loop limitado e somente leitura retornou
98.996 arquivos e dez dashboards (`final-maintenance-inventory.log`).
O ensaio original de RPC precisava definir PYTHONPATH no auxiliar de QA;
a execução concluída usa o mesmo código do produto, sem alterações em RAM.
O gate online e checksum de entrega seguem pendentes neste ponto do registro.


A preparação online no candidato final baixou **107 arquivos/2.938.150.529 bytes**
por HTTPS diretamente das URLs do catálogo, com verificação de todos os hashes.
Nenhum cache de pacote foi pré-carregado. O servidor local da bancada fornece
apenas os auxiliares de controle/fixtures, não os pacotes Rocky5.
A coleção normalizada produziu **98.996 arquivos/104 pacotes**, manifesto
**3674a346a220e417c4ccb69aa86a0918b686e57e5e5a32a42c19643f4e289470**, igual à ISO.
`cartucho/cache/online-payload-identity.log` e `final-online-controller.log`.
A área ext4 de preparação ocupa 8 GiB no exFAT e ficou com cerca de 471 MiB
livres após normalização. Downloads não consumiram RAM equivalente à coleção.
Controle virtual navegou a escolha de fonte, cancelou confirmação e manteve o
SSD sem escrita com a combinação segurada na segunda tela, até soltar e
confirmar de novo (`NO_WRITE_BEFORE_SECOND_CONFIRM`). A cópia de firmware de
entrada deste ensaio é a BIOS personalizada; o arquivo original ficou intacto.

A instalação online completa do candidato final terminou pelo controle com
**104 pacotes/98.996 arquivos verificados**, disco 1b2fca3b, XBMC4Gamers padrão,
Xbox 60,81 GiB. `bancada/validacao-online-final/install-status.json` e
`cartucho/cache/final-online-controller.log` (`CONTROLLER_INSTALL_PASS`).
O teste usa arquivos regulares de USB e SSD; nenhum disco físico foi alvo.
A base lógica é 14.162.067.456 bytes para reservar a área exFAT de 10 GiB;
a representação comprimida é cerca de 1,20 GiB e corresponde à mesma IMG.

Após desligar o instalador, o host conferiu layout e os três firmwares
importados byte a byte (`integrity-before-boot.json`). SSD **sem USB** iniciou
Xemu/ALSA e XBMC4Gamers no candidato final; identidade df48 e BIOS personalizada
confirmadas. Depois, reboot Linux com R efetivamente segurado abriu manutenção
própria e a lista de dez dashboards: `SSD_NORMAL_AND_R_MAINTENANCE_PASS`,
`cartucho/cache/final-installed-check.log`, `ssd-boot/maintenance-hello.json`,
`normal-dashboard.png`, `r-maintenance.png`, `r-dashboard-list.png`.
Interface e áudio rodaram com virtio/software: isso não substitui GTX750/Dell.
O encerramento final e a igualdade da SYSTEM inteira são conferidos antes de
publicar em out. O splash vetorial da BIOS continua um gate visual pendente;
chegar à dashboard não deve ser apresentado como prova de sua exibição.


## Entrega local

**20261024T163450Z-df48d0e06a6f** publicada localmente em out após todos os gates
acima, com apenas uma IMG. **14.162.067.456 bytes**, SHA256
**b192ae9418e8756a1a968389caffa3db1301ede209ed22c67dfd7b6c9c8a3a69**.
Mesma IMG em zstd: **1.290.868.289 bytes**, SHA256
**b0938a7a1500b427a172142f399d4510c906a0b54c64da65bbab46147fab74a0**.
Descompressão conferida por SHA contra o IMG. `release.json`, metadados,
packages.txt e checksums acompanham. O tamanho lógico reserva espaço vazio
para o proprietário; a base comprimida não contém a coleção.

Encerramento final passou. `integrity-after-shutdown.json`: SYSTEM inteira
**c77c5312576bea98d6042d04afccc821a527c1da1b771ad0e5ac2952ac9e5cf7**
inalterada, layout híbrido válido e Dashloader ainda XBMC4Gamers. Firmwares
importados foram comparados antes do primeiro boot. VMs/container do editor e
servidor auxiliar encerrados. Não houve escrita em mídia física nem publicação
na internet. Próximo gate: repetir GTX750/Dell e conferir splash BIOS.

IA Memory atualizado e lido integralmente de volta:
`notes/xrevive-online-offline-validacao-2026-10-24.md`,
`decisions/xrevive-instalador-online-rocky5-e-importacao-local.md`.
