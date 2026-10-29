# LIVE, mídias locais, discos USB e Wi-Fi — beta.5-live.6

**Pré-release 0.1.0-beta.5-live.6.** [Download](BAIXAR-E-INSTALAR.md).
O guia de [recuperação](LIVE-RECUPERACAO-BETA5-LIVE6.md) explica progresso,
cancelamento e reparo; os relatos anteriores permanecem no relatório.

## Um único assistente

Grave a IMG no pendrive, copie seus arquivos e ligue. O logo abre diretamente
o assistente existente, com as mesmas cores e navegação. Não há seleção prévia
obrigatória entre LIVE protegido e instalador. **Esc** durante o segundo inicial
do carregador abre a alternativa de recuperação de vídeo Intel/AMD.

No assistente: **LIVE → tipo de acesso → mídia → disco → Xbox virtual**.

- **Protegido:** escolha HDD virtual descartável ou um HDD físico. Com disco
  físico, as mudanças ficam em overlay na RAM e o disco permanece somente
  leitura. Formatar dentro do Xbox nesse modo não formata o disco real.
- **Instalação / manutenção:** escolha o HDD/SSD e confirme duas vezes segurando
  **LT + RT + Start** ou **F10**, soltando antes de repetir. Apenas esse disco
  recebe escrita real da mídia Xbox. Cancelar mantém a proteção.
- **Sem mídia:** inicia a dashboard do HDD escolhido; não exige reinstalar apps.

Discos internos e USB são listados pelo mesmo fluxo; não é necessário FATX prévio
no modo por mídia, pois a própria ferramenta Xbox pode preparar um disco vazio.
A lista mostra modelo, capacidade, conexão e formato reconhecido. **Atualizar
discos** detecta dispositivos conectados depois. O próprio pendrive de boot,
discos montados/em uso, dispositivos ATA bloqueados/inacessíveis e dispositivos
sem geometria compatível não são alvos utilizáveis. Troca do disco ou mudança
de metadados invalida a seleção antes da liberação de escrita.

Um HDD X-Revive híbrido reconhecido é limitado ao prefixo Xbox: a região Linux
não é exposta ao convidado. As ferramentas da mídia ainda podem alterar a tabela
Xbox e seus dados; a preparação/reparação do boot de PC continua uma operação
separada do assistente. Não confundir **Instalar X-Revive** (instalação limpa com
boot próprio) com executar uma mídia Xbox em LIVE.

**Limites de RAM:** HDD virtual de 8 GiB com até 1 GiB de mudanças; HDD físico
protegido com até 512 MiB. Instalações grandes devem usar disco dedicado com
escrita autorizada. O SSD pessoal do notebook não deve ser escolhido para testes
de formatação. Preparar um softmod não elimina os requisitos de BIOS, chave
EEPROM, trava ATA e versão do console original; USB aqui é a conexão do disco
ao PC, não emulação de um adaptador USB dentro do Xbox original. Este fluxo
apresenta um dispositivo de bloco ao Xemu e não implementa comandos ATA de
segurança no HDD físico: a indicação de trava no Xbox virtual não valida a
trava real exigida por um Xbox com softmod.

## Firmware e controle sem fio

Em `XREVIVE/X-Revive/firmware/xbox/`, forneça `bios.bin` e `mcpx_1.0.bin`.
`eeprom.bin` é opcional: o Xemu gera e o X-Revive preserva no pendrive quando ausente.

Para o adaptador **Xbox Wireless de Xbox One/Series**, coloque o firmware privado
em **`XREVIVE/X-Revive/firmware/dongle/`**. São aceitos os quatro arquivos conhecidos:

- `xone_dongle_02e6.bin` — adaptador antigo;
- `xone_dongle_02fe.bin` — adaptador novo;
- `xone_dongle_02f9.bin` e `xone_dongle_091e.bin` — variantes integradas.

Pode copiar apenas o de seu modelo ou os quatro. O carregamento ocorre **antes
do assistente**, também no LIVE, verificando hashes e disponibilizando os arquivos
na RAM do Linux. A importação também aceita `firmware/dongle` direto na raiz
XREVIVE. Na instalação completa ou preparação do boot, o firmware fornecido é
preservado na região CONSOLE do SSD para funcionar sem pendrive.

O driver xone já existe na IMG; o firmware proprietário foi retirado da imagem
pública e faltava a importação no runtime. O script
`cartucho/tools/firmware-dongle.sh` obtém os arquivos da Microsoft mediante
aceite dos termos; o binário não vai para o GitHub nem para a IMG sanitizada.
Bluetooth é outro transporte e não está configurado por esse fluxo; receptores
Xbox 360 usam xpad. O pareamento por rádio depende de teste físico.

## Escolher a mídia

Copie imagens com qualquer nome para **`XREVIVE/X-Revive/pacotes/`** ou subpastas;
o layout antigo **`XREVIVE/pacotes/`** também é reconhecido. Extensões `.iso`,
`.xiso` e `.img`, sem filtro de marca/instalador. **Atualizar lista** relê o USB.
A validação só ocorre depois da escolha e o arquivo permanece visível após erro.

- **XISO/XDVDFS:** inicia diretamente, incluindo HeXEn e OGXbox. A árvore é
  percorrida sem presumir a ordenação usada pela ferramenta de criação. Uma
  partição XDVDFS legível também pode ser tentada sem `default.xbe` validado:
  a BIOS da sessão decide o boot, sem bloquear por esse nome no assistente.
- **DVD Xbox completo:** reconhece a partição Xbox em offsets conhecidos e
  apresenta somente essa região ao Xemu, sem alterar o original.
- **ISO9660 com executável Xbox na raiz:** é apresentada por DVD virtual XDVDFS somente leitura.
- **Coleção antiga `rocky5-offline.iso`, com `payload/manifest.json`:** agora
  também funciona no LIVE. Confere a coleção e apresenta um DVD virtual XDVDFS com o
  UnleashX fornecido nela e um menu X-Revive. É uma adaptação da coleção,
  **não o menu original do Rocky5 Extras Disc**. Inclui exploração manual,
  cópia de C/E/F, formatação por volume e acesso aos apps/dashboards/emuladores
  da própria coleção. A cópia da coleção pressupõe volumes formatados, F
  disponível e espaço suficiente; não muda sozinha a geometria de F/G.

Na live.6, a adaptação usa NBD somente leitura: metadados em RAM e conteúdo
lido da ISO original. Não exige outra cópia integral de 4,5 GiB no USB. O caminho
antigo `X-Revive/cache/live-media/` só é fallback para kernels sem NBD e seus
caches verificados podem ser reutilizados. A imagem desta release já inclui NBD.

Na coleção antiga fornecida para o teste, 13 nomes de sinopses TXT precisam de
adaptação para a cópia nativa FATX (pontuação, codificação ou espaço inicial).
Só esses nomes de metadados mudam na mídia gerada: os conteúdos são preservados,
as aplicações e seus recursos não são renomeados, e `XREVIVE-NAMES.json` registra
os caminhos originais, novos nomes e hashes. A ISO original permanece intacta.
Se faltar espaço após uma atualização, somente caches gerados de receitas antigas
da **mesma ISO**, com hash de saída conferido, podem ser removidos para recriar
a versão atual. Arquivos pessoais e caches desconhecidos são preservados.

Uma imagem incompleta, de outro console ou sem executável Xbox ainda pode
falhar; renomear não muda o formato. Não se executa `autorun.exe`/`autorun.inf`
de Windows. O boot Xbox depende do XBE e da BIOS. O OGXbox original fornecido
para esta investigação possui `default.xbe` na raiz; não ficou comprovado que
o erro na cópia da bancada decorreu de outro caminho de autorun.

A opção online permanece **Rocky5 Extras Disc**, com revisão, tamanho e hashes
fixados. BIOS, MCPX, EEPROM, firmware do dongle, apps e ISOs do usuário não
entram na IMG pública.

## Configurar Wi-Fi no assistente

Escolha **Configurar rede Wi-Fi**, na tela inicial ou nas opções de origem dos
aplicativos. O assistente procura redes, mostra nome, intensidade do sinal,
segurança e conexão ativa. Escolha a rede, informe a senha e aguarde a conexão.
O endereço IP aparece após o DHCP.

É possível usar apenas teclado físico ou apenas controle:

- **Assistente:** setas/digital para navegar; Enter/A para escolher; Esc/B para voltar.
- **Senha com teclado físico:** digite normalmente, Backspace apaga, Enter conecta e Esc cancela.
- **Senha com controle:** digital navega no teclado virtual; A insere/escolhe; X apaga e B cancela.
- O teclado virtual tem maiúsculas, minúsculas, símbolos, acentos, espaço,
  apagar, conectar e cancelar. A senha aparece oculta.
- **Rocky5 com teclado:** setas; tecla A confirma, B volta, Enter corresponde a Start.

Esta beta usa conexões Wi-Fi **temporárias, válidas até desligar**. A senha não é
salva em arquivos no pendrive ou no SSD, nem enviada em argumentos de processos
ou incluída nos diagnósticos. Para conectar novamente após reiniciar, informe-a
outra vez.

O gerenciador sem fio não assume a Ethernet, que continua com systemd-networkd.
Com cabo ativo, o Xbox mantém o caminho Ethernet/pcap. Sem cabo ativo, o Xbox usa
NAT, que pode sair pela conexão Wi-Fi do sistema. Isso não cria uma ponte Ethernet
sobre Wi-Fi. FTP entre outro computador e o Xbox por Wi-Fi ainda requer teste
físico próprio; não confundir a conexão do baixador com essa validação.

## Compatibilidade e limites

- Requer adaptador reconhecido pelo kernel e firmware disponível. A imagem inclui
  firmware Intel, Realtek, Atheros, MediaTek e Broadcom; isso não garante suporte
  a todos os modelos.
- Redes abertas, WPA/WPA2/WPA3 pessoais e OWE são previstas. WEP e autenticação
  corporativa/802.1X não são configuradas nesta beta. Redes ocultas não são
  cadastradas manualmente nesta primeira interface.
- Bloqueio físico do rádio, ausência de adaptador, senha recusada e falha de
  conexão devem ser informados na interface. Redes com portal de autenticação
  podem obter IP e ainda exigir uma etapa externa para liberar a internet.
- Wi-Fi e digitação por teclado físico foram confirmados no Dell G15 na live.4.
  O controle sem fio desde o início foi confirmado na etapa live.5; a cobertura
  por cenário consta no relatório da live.6.

## Teste antes da pré-release

1. Confirmar boot e interface no G15 e no Xeon/GTX 750.
2. Conferir as imagens nas pastas principal, antigas e subpastas; escolher mídia
   iniciável e arquivo incompatível, observando erro sem sumir da lista.
3. Conectar ao Wi-Fi pelo teclado físico e pelo controle; conferir senha oculta,
   correção de caracteres, cancelamento, IP e download online.
4. Abrir OGXbox, HeXEn e a coleção Rocky5 offline no modo protegido; conferir
   o HDD virtual e o HDD selecionado com overlay.
5. Conectar um HDD/SSD USB dedicado: selecionar explicitamente o destino, cancelar
   a confirmação, depois autorizar com duas confirmações e testar a mídia.
6. Copiar o firmware do dongle, iniciar com o adaptador conectado, parear e navegar
   por controle no assistente e dentro do Xbox. Repetir conectando depois do boot.
7. Após confirmação, atualizar documentação vigente, site e notas da versão;
   conferir fontes/licenças, checksums e publicar como pré-release beta.

## Referências técnicas

- [NetworkManager: nmcli e operações de rede](https://networkmanager.dev/docs/api/latest/nmcli.html).
- [NetworkManager: API de ativação e conexões voláteis](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/gdbus-org.freedesktop.NetworkManager.html).
- [Kernel Linux: mac80211_hwsim para ensaios isolados](https://kernel.org/doc/html/v5.19/networking/mac80211_hwsim/mac80211_hwsim.html).

- [Driver xone e adaptadores suportados](https://github.com/dlundqvist/xone/tree/v0.5.8).
- [Menus de instalação do Rocky5 Extras Disc](https://github.com/Rocky5/Xbox-Softmodding-Tool/blob/master/Extras%20Disc/hardmod.xml).
