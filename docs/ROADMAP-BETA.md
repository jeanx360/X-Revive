# Roadmap da beta

## Base entregue

Instalador próprio; uma IMG Mesa/NVIDIA; Rocky5 online; ISO X-Revive offline;
firmware separado; SSD com boot independente e FATX; manutenção por R;
Start+digital para cima para Xemu; bandeja física; logos de boot/desligamento;
cliente Xemu assinado com reversão. Validação em bancada concluída.

## EEPROM opcional — beta.3

Instalar com BIOS e MCPX. A EEPROM é importada quando fornecida ou gerada pelo
Xemu quando ausente, com identidade preservada no SSD. [Funcionamento](EEPROM-OPCIONAL.md).

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
