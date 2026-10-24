# Instalador próprio X-Revive — estágio 2

Etapa atual: [instalação online Rocky5 e ISO local](INSTALADOR-ONLINE.md). As referências à mídia offline abaixo descrevem a baseline anterior.

Entrega local `20261024T051417Z-d32d6edfb5b9`, validada em VM. Evidências e
checksum em [VALIDACAO-ESTAGIO2.md](VALIDACAO-ESTAGIO2.md). O próximo marco é a
bancada física dessa entrega; a baseline f613cf12 permanece preservada no cache.

## Conteúdo offline

O catálogo oficial Rocky5 é suficiente, conforme decisão explícita do usuário.
Não se busca equivalência ao OGXbox. Fontes: `rocky5.lock.json`, repositório
Xbox-Softmodding-Tool e catálogo xbmc4gamers.co.uk. O lock fixa URL, SHA256,
tamanho e inventário de cada pacote. Há 107 arquivos de origem (104 pacotes ZIP,
carregador, exemplo de configuração e atalho do Microsoft Dashboard).
O ZIP original não é executado pelo build. São 98.996 arquivos normalizados;
o manifesto registra o tamanho e SHA256 de cada um.

Inclui dashboards, aplicativos, emuladores, trainers e temas. Não é um pacote
de jogos comerciais. Instalação completa, sem seleção individual de programas.
Firmware e animação Xbox continuam fornecidos localmente pelo proprietário.

Vinte nomes de arquivos TXT de sinopse dos emuladores excedem o limite FATX de
42 bytes. O conteúdo foi preservado com nome abreviado e hash; o manifesto
registra cada correspondência. Isso pode impedir a associação automática dessas
sinopses a seus jogos. Arquivos de metadados Windows `Thumbs.db`/`desktop.ini`
não são instalados. Nenhum executável é omitido por esses tratamentos.

## Organização

- C: arquivos do Microsoft Dashboard e carregador hardmod Rocky5.
- E: UnleashX de recuperação, dados de usuário e animação Cerbios.
- F: dashboards, aplicativos, emuladores, trainers, temas, jogos/homebrew.
- G: disponibilizada em discos grandes quando necessária para dividir a área
  estendida em volumes compatíveis com clusters de até 64 KiB.

XBMC4Gamers é o padrão, com as demais dashboards presentes. A seleção de padrão
modifica `C:\Dashloader.ini`, após conferir que o executável existe, sem
formatar ou reinstalar os programas. Nem todos os programas upstream aceitam
relocação arbitrária; a execução individual das dashboards é parte da validação.
UIX Lite usa recursos na raiz de F:, preservando os arquivos Microsoft de C:.
O build altera exatamente nove referências nativas Partition2→Partition6 de
um executável com SHA256 conhecido; outra versão é recusada para revisão.
O teste virtual confirmou o item Launcher após essa relocação, ausente quando
apenas o executável era movido. Os caminhos e bytes alterados estão em
`cartucho/build/uix-relocate.py`. A Emustation mantém seus próprios cores e
caminhos relativos; o catálogo adicional de emuladores fica em F:\Emulators.

## Fluxo de uso

Gravar a IMG no pendrive inteiro e iniciar pelo UEFI com Secure Boot desativado.
Usar pendrive de pelo menos 16 GB; a capacidade mínima do destino é conferida
com o catálogo real, sendo 32 GB uma referência prática para esta coleção.
O instalador mostra os discos disponíveis. O pendrive de origem não é destino;
discos montados, com swap, em uso ou com setores lógicos incompatíveis são
recusados. Modelo, série e capacidade ficam visíveis antes da confirmação.

Teclado: setas, Enter e Esc. Controle: digital, A e B. Para apagar e instalar,
segurar F10 ou LT+RT+Start em duas telas, soltando entre elas. Manter a combinação
pressionada não confirma a segunda tela. Depois da confirmação, a identidade
do disco é revalidada e os pacotes são conferidos antes da primeira escrita.

O instalador copia o sistema, prepara FATX e grava os arquivos. Lê de volta todo
o conteúdo instalado antes de concluir. O boot UEFI híbrido é gravado por último.
Ao terminar, retirar o pendrive e reiniciar. Não há conversão ou expansão de um
HDD com jogos nesta versão: instalação limpa apaga o destino confirmado.
Os protótipos anteriores de 16 GiB não são adotados nem expandidos
automaticamente pelo novo instalador.

## Capacidade e proteção

O layout usa a capacidade real do disco, arredondada para MiB, reserva as áreas
do X-Revive e entrega o prefixo restante ao Xbox. Não tem o limite fixo de 16 GiB.
O MBR híbrido atual exige disco abaixo de 2 TiB. Discos com setor lógico de
4096 bytes são recusados. O formato físico 512e com setor lógico de 512 bytes é
compatível com a regra, sujeito à validação do hardware.

As partições C/E/X/Y/Z mantêm offsets e tamanhos retail. F/G usam o restante do
prefixo. Xemu acessa um loop com `sizelimit`, impedindo alcançar a área Linux.
Num Xbox físico essa proteção por loop não existe: BIOS e ferramentas devem
respeitar a tabela nativa. Compatibilidade em console original exige ensaio
físico separado; emulação não constitui essa prova.

## Manutenção e acabamento

R ou Start+Back durante o boot do SSD abre a manutenção própria; o logo confirma
que a combinação pode ser solta. O pendrive inicia diretamente no instalador.
Manutenção oferece comparação com o pacote original, reparo UEFI e escolha da
dashboard padrão. A comparação informa arquivos alterados/ausentes sem
restaurar conteúdo: configurações, perfis e atualizações podem mudar arquivos.
Formatação exige a opção de instalação e as duas confirmações.

O menu Xemu usa Start+digital para cima. O tema Plymouth mostra `Desligando...`
quando iniciado em modo de encerramento. HeXEn/OGXbox não integram a nova mídia.
As ISOs anteriores permanecem apenas no cache de desenvolvimento/baselines.
Os módulos Mesa/NVIDIA são incluídos no initrd; a carga inicial NVIDIA segue a
GPU detectada. O arquivo de carga global do pacote Debian é mascarado para
impedir tentativas indevidas em máquinas sem NVIDIA. Esse comportamento foi
conferido em virtio; outras GPUs exigem ensaio físico.

## Evidências disponíveis

`cartucho/cache/rocky5/qa/native-filesystem.json`: C 211, E 223, F 98.560
arquivos escritos e lidos integralmente num arquivo de disco de 64 GiB.
`cartucho/cache/fatx-independent-read.log`: leitura independente por libfatx,
carregador, executáveis das dashboards e diretório com 1.183 trainers.
Esses testes não substituem a validação da instalação gráfica e boot do SSD.

## Atualizações do emulador

A mídia com protocolo de atualização 1 acrescenta U no teclado ou Y no controle durante o boot do SSD. Leia as notas e confirme por A/Enter para atualizar somente Xemu. R/Start+Back continua manutenção e agora oferece reversão do emulador. O canal público ainda precisa ser definido; consulte [operação e limites](ATUALIZADOR-XEMU.md) e [evidências de VM](VALIDACAO-ATUALIZADOR-XEMU.md). A opção Instalar continua sendo instalação limpa, que apaga o destino; não é a forma de atualizar um disco com jogos. Instalações anteriores não recebem o cliente automaticamente.
