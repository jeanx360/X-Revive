# Preservação de HDD Xbox original — pesquisa experimental

**Estado:** pesquisa experimental de bancada. **Não disponível na imagem pública `v0.1.0-beta.4`.** Este documento explica o objetivo, os riscos e os testes necessários; **não é um tutorial de conversão de disco**.

## Por que isso existe?

O X-Revive nasceu de um Xbox Clássico danificado por enchente. A intenção original é usar outro hardware sem perder o HDD, os dados FATX, jogos, dashboards e, quando for possível recuperar, a identidade da máquina.

A pesquisa parte da inicialização do ambiente por USB/RAM e do reconhecimento de FATX existente, e investiga uma área de boot UEFI no mesmo disco sem sobrescrever o conteúdo original. Os protótipos históricos e a instalação limpa não demonstram, por si só, a preservação de um HDD original. Essa abordagem ainda precisa de um procedimento reproduzível e de verificação integral.

## O que é diferente da beta pública

| Aspecto | Beta pública beta.4 | Pesquisa de preservação |
| --- | --- | --- |
| Disco de destino | Novo ou descartável | HDD original, possivelmente com dados exclusivos |
| Operação | **Instalação limpa: apaga o disco** | Objetivo: identificar FATX e preservar o conteúdo existente |
| Boot | USB para instalar e SSD/HDD para usar | Investigação de USB/RAM e boot UEFI opcional |
| Garantia de integridade | Duas confirmações antes da instalação limpa | **Ainda não há garantia pública para o modo de preservação** |
| Disponibilidade | IMG distribuída nas releases | Pesquisa de bancada, fora da beta.4 |

**Não conecte seu HDD original para instalar a beta.4.**

## Premissas técnicas que devem ser demonstradas

A estrutura FATX do Xbox original não é uma tabela GPT comum. Suas informações de particionamento e o setor de boot do PC podem compartilhar endereços e comportamentos de forma específica. Uma leitura aparentemente correta depois de alterar partições Linux **não prova**, por si só, que todas as regiões, assinaturas, backups e caminhos de recuperação estejam seguros.

Antes de distribuir esse modo, a equipe deve demonstrar, em discos representativos e imagens-clone descartáveis:

1. Reconhecimento **somente leitura** de FATX e da geometria real, incluindo variações, partições estendidas e tabelas/BIOS relevantes.
2. Cópia integral e **backup verificável antes da primeira escrita**. Se houver sinais de degradação física, priorizar imagem forense/recuperação em vez de experimentar sobre o original.
3. Mapa de regiões usadas e reservadas, com comparação dos setores relevantes **antes e depois** da intervenção UEFI; nenhum campo necessário ao Xbox pode ser alterado silenciosamente.
4. Inventário e hashes verificáveis dos dados, com checagem de integridade e boot depois da modificação.
5. Reinicializações repetidas, diferentes firmwares/BIOS, falhas de energia e método documentado de retorno ao estado anterior.
6. Quando declarado compatível: ensaio **físico** no Xbox modchipado, com BIOS compatível e sem formatadores que possam ocupar a região UEFI do PC.
7. Mensagens inequívocas de risco e confirmação; nenhuma operação destrutiva automática em discos existentes.

## EEPROM e bloqueio ATA

O backup `eeprom.bin` de uma máquina existente pode ser necessário para recuperar sua identidade e a chave associada ao HDD. **Ter um backup não significa automaticamente que o HDD esteja desbloqueado**. Algumas unidades possuem ATA Security e precisam de procedimentos específicos, seguros e compatíveis. Não divulgue EEPROM, HDD key, dumps, números de série ou conteúdo privado em issues e logs públicos.

## Segurança editorial

Enquanto não houver release própria e matriz de validação pública, qualquer conteúdo no README ou site deve chamar esse recurso de **pesquisa experimental**. Evite frases como “zero risco”, “preserva qualquer HDD”, “100% compatível com Xbox físico” ou “um clique sem perdas”.

[Estado da beta](BETA.md) · [Arquitetura atual](ARQUITETURA.md) · [Índice](INDEX.md)
