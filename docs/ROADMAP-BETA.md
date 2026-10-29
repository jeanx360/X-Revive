# Roadmap da beta

## Etapa publicada — beta.5-live.6

1. Corrigir as esperas do LIVE: RPC fora do ciclo de desenho, consultas de
   estado independentes, configuração com prazos e cancelamento cooperativo.
   Mostrar animação, etapa, tempo, detalhes e diagnóstico no pendrive.
2. Aceitar manutenção de HDD FATX nativo/híbrido e recuperar/substituir boot
   existente, após aviso e confirmação do disco, preservando os volumes Xbox.
   UEFI coexistente não impede o LIVE. Reidentificar o hardware ao iniciar.
3. Apresentar a coleção offline como DVD virtual somente leitura, sem exigir
   uma segunda cópia integral de aproximadamente 4,5 GiB no USB.
4. Validar a nova candidata em VM e no HDD físico conectado em leitura;
   conferir hashes dos metadados e blocos alocados. Reserva e reparo em
   cópias regulares antes de qualquer mudança de geometria no disco real.
5. Repetir a bancada no Dell G15 e Xeon. Publicação autorizada em 28/10/2026;
   ampliar a matriz física sem extrapolar os resultados já registrados.

O controle Xbox sem fio desde o início foi confirmado no Dell na live.5.
Essa mesma rodada relatou falhas de manutenção, falta de espaço para adaptar
mídia e esperas sem feedback; não foi aprovação completa para publicação.
O HDD real de 1 TB tem F até o final. A reserva de cerca de 3,19 GiB foi
provada em clone; a migração física aguarda autorização específica e não é
automática nesta candidata. Guia: [LIVE e recuperação](LIVE-RECUPERACAO-BETA5-LIVE6.md).
Resultados e limites: [validação local](VALIDACAO-LIVE6-RECUPERACAO.md).

## Etapa anterior — beta.5-live.5

1. Consolidar o LIVE no assistente: protegido com HDD virtual ou overlay,
   ou escrita explícita em um único HDD/SSD interno/USB após duas confirmações.
2. Corrigir boot de mídias livres e aceitar a coleção Rocky5 offline por adaptação
   no cache, preservando o original. Não exigir FATX prévio para uma mídia prepará-lo.
3. Importar firmware privado do dongle antes da interface, também no LIVE, e
   preservar no SSD instalado. Confirmar rádio/pareamento em bancada.
4. Validar na VM acesso USB, proteção dos outros discos, mídia selecionada,
   formatação/instalação pelo convidado, FTP e regressões de instalação normal.
5. Após teste físico desta candidata, revisar fontes/licenças e publicar uma
   **pré-release beta**, atualizando site e links. Sem promoção antecipada.

Implementação local pronta; 111 testes locais passaram. Instalação normal e
cópia nativa da coleção verificaram 98.996 arquivos. A entrega continua beta,
pendente da confirmação física desta candidata. [Evidências](VALIDACAO-LIVE5-UNIFICADO.md).

Boot rápido do assistente, Wi-Fi, teclado físico e HeXEn foram confirmados no
Dell G15 na live.4. Dongle e outras mídias falharam nesse teste; isso não é
validação completa nem aprovação da live.5. Guia: [LIVE e Wi-Fi](LIVE-MIDIAS-WIFI-BETA5.md).

## Base entregue

Instalador próprio; uma IMG Mesa/NVIDIA; Rocky5 online; ISO X-Revive offline;
firmware separado; SSD com boot independente e FATX; manutenção por R;
Start+digital para cima para Xemu; bandeja física; logos de boot/desligamento;
cliente Xemu assinado com reversão. Validação em bancada concluída.

## EEPROM opcional — beta.4

Instalar com BIOS e MCPX. A EEPROM é importada quando fornecida ou gerada pelo
Xemu quando ausente, com identidade preservada no SSD. [Funcionamento](EEPROM-OPCIONAL.md).

## Publicação dos fontes — concluída

Fontes publicados como `v0.1.0-beta.1`, com guias, limitações, licenças, modelos de
issues e testes no GitHub. Excluir dados pessoais, firmwares, ISOs, caches,
dashboards e discos de bancada. Correções terão commits, changelog e evidências.

## Distribuição binária — concluída na beta.2

Beta.2 publicada com IMG limpa, inventário/licenças e fontes correspondentes
para o sistema e Xemu modificado, SHA256, versões, lista de pacotes e notas. Não distribuir a ISO particular ou
firmware particular como se fosse asset público.

## Prioridade 3 — operar as atualizações

Definir URLs HTTPS reais, hospedar manifesto/catálogo assinado, proteger e fazer
backup privado da chave, validar ofertas e promover Xemu após QA. O CI prepara
candidatos sem assinatura; não substitui patches X-Revive por release genérica.
Atualização de Xemu e nova imagem de sistema são fluxos distintos.

## Prioridade 4 — ampliar a validação e polir

Documentar online/offline por máquina, repetir FTP com arquivo grande e hash,
bandeja com/sem mídia, perda de energia e recuperação. Investigar splash BIOS.
Testar Xbox original separadamente sem prometer equivalência física a partir
da VM. Registrar limites de cada família de GPU.

## Etapas futuras

APT snapshot e dependências totalmente fixadas; atualização integral; ampliar
Wi-Fi e formatos de mídia; migração preservando dados após
projeto/testes específicos. Outros consoles permanecem visão futura.
