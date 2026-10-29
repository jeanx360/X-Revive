# Validação local — beta.5-live.4, mídias e Wi-Fi

**Estado:** candidata pronta para novo teste físico; não publicada.
A beta pública permanece na beta.4. Não há confirmação física do Wi-Fi desta
candidata nem de FTP externo pela rede sem fio.

## Identificação da entrega final

- Versão: `0.1.0-beta.5-live.4`.
- Build C4: `20261026T170126Z-8216ea4d396d`.
- Fonte SHA256: `8216ea4d396d830611735c12e180190ec89e17237325f6e12b29e2895653101b`.
- IMG: 14.162.067.456 bytes; SHA256 `26ba6dd47d974a75d536e8da55b5ca48a4044c9ce643c574189efe069792a664`.
- XZ: 1.375.863.872 bytes; SHA256 `30840889c397647168914397ea1477ffa874b84e218ae6c7e517e9711bd3df15`.
- Descompressão integral: tamanho e SHA256 idênticos ao IMG.
- Kernel `6.12.113+deb13-amd64`, NVIDIA `550.163.01-2` e Xemu
  `0.8.138-xrevive-smc2` preservados.
- NetworkManager `1.52.1-1`, wpa_supplicant `2:2.10-24`, python3-dbus,
  regulatory.db e firmware adicional MediaTek/Broadcom incluídos. Ethernet mantém
  systemd-networkd; NetworkManager controla somente Wi-Fi.

## Verificações executadas

**99 testes locais passaram**, incluindo:

- Descoberta recursiva, nomes livres, extensões sem diferenciar maiúsculas e
  minúsculas, pasta antiga no USB, nomes repetidos e rejeição de links externos.
- Listagem antes de validação: arquivo inválido permanece na lista, sem escrita
  no arquivo e sem impedir a seleção de outras mídias.
- Entrada física Unicode e teclado virtual: navegação, maiúsculas, símbolos,
  acentos, espaços, apagar e cancelar.
- PSK em configurações D-Bus voláteis, sem argumentos de processos; erros não
  repetem a senha. A busca espera também uma varredura que o NetworkManager já
  tenha iniciado.
- Regressões de segurança LIVE, EEPROM, confirmação de instalação e escolha da
  GPU conectada à tela, incluindo manutenção dos ajustes da GTX 750.

Sintaxe Python/shell, `git diff --check` e transação systemd completa passaram.
Não foram alterados discos físicos do host, MCP ou hooks de memória.

## Wi-Fi e HeXEn — C4 final

VM `bancada/validacao-live4-final4-wifi/`, com USB de QA, disco regular de dados
GPT/ext4 e dois rádios `mac80211_hwsim`. O AP WPA2 foi isolado em namespace e
configurado com hostapd/DHCP. Essas ferramentas pertencem somente ao ensaio,
não à imagem de produção. A rede física do computador não foi usada para
configurar ou autenticar um adaptador real.

Pelo assistente de produção, sem patches do produto em RAM:

1. Pesquisa de redes, incluindo **Atualizar redes** após a criação dinâmica do AP.
2. Seleção e senha pelo teclado físico, autenticação WPA2 e IP por DHCP.
3. Desconexão, tentativa com senha incorreta e retorno compreensível à lista.
4. Nova tentativa apenas por controle, digitando no teclado virtual e usando X
   para apagar/corrigir um caractere; senha oculta e conexão concluída.
5. Rota de saída confirmada em `wlan1`, origem `10.77.0.28`. Requisição HTTP ao AP
   e download HTTPS real da origem Rocky5 por essa conexão; SHA256 do download
   `934c3e31aa546b89d19d213ed7df6ec9162e90a5e4c293eeb53851d4de8bd728`.
6. Ethernet confirmada como não gerenciada pelo NetworkManager; nenhum perfil
   persistente em `/etc/NetworkManager/system-connections`. O perfil volátil
   pode existir em `/run/NetworkManager`, em RAM. PSKs do teste ausentes do log
   do worker.
7. Retorno ao menu, quatro imagens visíveis em pastas diferentes, erro de formato
   mantendo o arquivo listado e seleção de `servicos/HeXEn qualquer nome.XISO`.
8. HeXEn iniciado, áudio ativo, FTP STOR/RETR no E virtual, EEPROM gerada e
   preservada no USB. HDD do Xbox apenas virtual; disco de dados recusou pwrite
   como root e operações de escrita pelo RPC.

Após desligamento e término da VM, **todos os 1.073.741.824 bytes** do disco de
dados permaneceram idênticos: SHA256
`92273d1de9c917e3b8f717ac62167aaae09751cdbc264ca995961cdecc10eaab`.

Evidências locais: `wifi-state.json`, `wifi-proof-result.log`, `media-list.json`,
`media-proof.json`, `pc-disk-integrity.json`, capturas de senha oculta nos dois
métodos, conexão, erro de senha, lista de mídias, erro de formato e HeXEn.

## OGXbox — regressão C3

VM `bancada/validacao-live4-final-ogx/`, build C3
`20261026T165414Z-6f846063af07`, anterior somente ao refinamento final da espera da
busca Wi-Fi. A descoberta/seleção/boot de mídias é igual à C4.

Selecionada `pacotes/OGXbox teste de usuario.iso`, na pasta antiga da raiz do USB.
As quatro imagens apareceram; o arquivo inválido continuou na lista após o erro.
OGXbox iniciou com áudio e FTP STOR/RETR no HDD virtual. Proteções contra escrita
física e EEPROM passaram. Após desligamento, o disco de dados completo permaneceu
idêntico ao mesmo SHA256 acima. Evidências: `media-list.json`, `media-proof.json`,
`pc-disk-integrity.json` e capturas. Não confundir este ensaio C3 com a identificação
da IMG final C4.

## Limites e publicação

A VM comprova o fluxo de software e o tráfego pelos rádios simulados. Ela não
comprova o adaptador físico do Dell, interferência/sinal reais, WPA3 em hardware,
rede corporativa, portal cativo ou FTP externo por Wi-Fi. Não houve novo teste
físico da GTX 750 neste ciclo. O relato anterior de que o G15 chega ao assistente
não valida automaticamente essas funcionalidades novas.

Aguardar teste físico da C4. Depois, revisar fontes/licenças das novas dependências,
atualizar documentação vigente/site, conferir os artefatos testados e publicar com
marcação **pre-release beta**, mantendo a beta.4 até essa confirmação.

[Guia de uso](LIVE-MIDIAS-WIFI-BETA5.md) · [Rascunho da pré-release](releases/v0.1.0-beta.5-live.4.md)
