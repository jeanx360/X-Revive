# EEPROM opcional

A partir da **beta.4**, é possível instalar sem fornecer `eeprom.bin`.

| Arquivo | Exigência |
|---|---|
| `bios.bin` | Obrigatório |
| `mcpx_1.0.bin` | Obrigatório |
| `eeprom.bin` | Opcional, para importar uma identidade existente |

## Sem EEPROM fornecida

O Xemu gera uma EEPROM válida no primeiro boot. O X-Revive preserva o arquivo no
SSD assim que ele é criado. A mesma identidade é usada nos próximos boots,
reinícios, manutenção e atualizações; não há uma EEPROM pessoal embutida na IMG.
As alterações de configurações feitas durante a sessão são salvas no desligamento.

## Com EEPROM fornecida

Copie seu arquivo de 256 bytes para `XREVIVE/X-Revive/firmware/xbox/eeprom.bin`.
Ele é importado na instalação e usado no boot. O processo de geração automática
não substitui uma identidade já existente. Arquivos com tamanho inválido ou
links simbólicos são recusados antes da seleção do disco de destino.

## Versões anteriores

As betas.1 e .2 exigiam o fornecimento dos três arquivos. A geração automática é
funcionalidade do [Xemu](https://xemu.app/docs/eeprom/); a beta.4 adapta o instalador
e a persistência do X-Revive para utilizá-la. BIOS e MCPX permanecem separados e
necessários: [arquivos requeridos](https://xemu.app/docs/required-files/).
