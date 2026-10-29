# HDD Xbox existente — LIVE e boot experimental

A beta.5-live.6 inclui LIVE e preparação/reparo de boot em layouts reconhecidos.
Não é uma migração automática de qualquer HDD. [Guia](LIVE-RECUPERACAO-BETA5-LIVE6.md).

| Opção | Efeito no disco |
|---|---|
| LIVE protegido, sem mídia ou por ISO | HDD somente leitura, alterações descartáveis na RAM |
| LIVE com acesso de escrita | A mídia Xbox pode instalar/formatar no disco escolhido após duas confirmações |
| Preparar/reparar boot | Atualiza SYSTEM/UEFI fora do FATX, após aviso e duas confirmações |
| Instalar X-Revive | Apaga o destino; não usar para preservar conteúdo existente |

FATX nativo e híbrido, em unidades internas ou USB, podem iniciar sem exigir
inventário de aplicativos do X-Revive. Boot UEFI anterior, íntegro ou quebrado,
é substituído quando o mapa/reserva permite; outros dados PC não são apagados
para forçar essa operação. Rodapé danificado pode ser recuperado pelo mapa da
ESP. Se todo o mapa foi perdido, é necessário diagnóstico específico.

## Quando F ocupa até o final

Espaço livre dentro de F não é área independente para Linux/UEFI. Reduzir F
altera o tamanho derivado da FAT e pode deslocar o início dos dados; mudar só
a tabela PARTINFO pode corromper o acesso. A candidata não faz esse
redimensionamento automaticamente: informa a necessidade e permite LIVE.

A reserva de cerca de 3,19 GiB foi provada em uma cópia de HDD de 1 TB, com
reposicionamento e hashes dos dados alocados preservados. Essa cópia iniciou
sem pendrive. No HDD físico, os ensaios foram somente leitura, sem aplicar a
migração. Isso não é garantia para qualquer geometria ou disco original.

## Evidências e trabalho seguinte

[Validação](VALIDACAO-LIVE6-RECUPERACAO.md): cópia de metadados e todos os blocos
alocados, conferência antes/depois, proteção real por descritor O_RDONLY,
reparo de rodapé/EFI em clones e boot independente.

A migração genérica ainda precisa de backup verificável, planejamento por
geometria, recuperação após interrupção e testes em mais modelos. Uso no Xbox
físico depende também de BIOS, versão, EEPROM e trava ATA; a VM não valida isso.
Manter instalação limpa separada desses testes e preservar os dados originais.
