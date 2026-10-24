# Roadmap da beta

## Base entregue

Instalador próprio; uma IMG Mesa/NVIDIA; Rocky5 online; ISO X-Revive offline;
firmware separado; SSD com boot independente e FATX; manutenção por R;
Start+digital para cima para Xemu; bandeja física; logos de boot/desligamento;
cliente Xemu assinado com reversão. Relatório físico recebido em 24/10/2026.

## Próxima mudança — EEPROM opcional

Primeiro revisar documentação, download público e instruções de gravação no
GitHub. Em seguida, tornar `eeprom.bin` opcional: importar quando fornecida ou
permitir a geração pelo Xemu, persistindo a identidade uma única vez no SSD.
BIOS e MCPX continuam obrigatórios. [Plano e critérios](EEPROM-OPCIONAL.md).
Nenhuma nova IMG é compilada durante esta revisão documental.

## Publicação dos fontes — concluída

Fontes publicados como `v0.1.0-beta.1`, com guias, limitações, licenças, modelos de
issues e testes no GitHub. Excluir dados pessoais, firmwares, ISOs, caches,
dashboards e discos de bancada. Correções terão commits, changelog e evidências.

## Distribuição binária — concluída na beta.2

Beta.2 publicada com IMG limpa, inventário/licenças e fontes correspondentes
para o sistema e Xemu modificado, SHA256, versões, lista de pacotes e notas. Não distribuir a ISO particular ou
firmware do mantenedor como se fossem assets públicos.

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

APT snapshot e dependências totalmente fixadas; atualização integral; interface
Wi-Fi; importadores explícitos de outras mídias; migração preservando dados após
projeto/testes específicos. Outros consoles permanecem visão futura.
