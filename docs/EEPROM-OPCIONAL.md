# EEPROM opcional

**Status: mudança aprovada pelo mantenedor; implementação e nova IMG pendentes.**
Esta revisão altera documentação e apresentação no GitHub. Não altera o
instalador nem o comportamento da IMG beta.2 já publicada.

## Comportamento aprovado para a próxima imagem

| Arquivo do usuário | Exigência |
|---|---|
| `bios.bin` | Obrigatório |
| `mcpx_1.0.bin` | Obrigatório |
| `eeprom.bin` | Opcional |

Se o usuário fornecer uma EEPROM válida, ela será importada e preservada.
Se não fornecer, a instalação deverá permitir continuar e deixar o **Xemu gerar
uma EEPROM válida**. A geração criará uma identidade nova, própria daquela
instalação. O arquivo gerado deverá ser persistido no SSD e reutilizado nos boots
seguintes, sem recriação a cada inicialização ou sobrescrita de uma EEPROM existente.

A geração automática de EEPROM é uma funcionalidade do próprio Xemu:
[documentação oficial](https://xemu.app/docs/eeprom/). MCPX e BIOS continuam
necessários no sistema emulado: [arquivos requeridos](https://xemu.app/docs/required-files/).

## Situação da beta.2 disponível para download

O instalador e a preparação do boot ainda verificam a existência dos três
arquivos. Remover apenas a frase da documentação não muda essa verificação.
Portanto, quem baixar a beta.2 ainda precisa fornecer `eeprom.bin`.
O download atual, os seus checksums e as instruções correspondem a essa versão.

## Próxima implementação, após a revisão documental

1. Tornar a EEPROM ausente aceitável na preparação e importação de firmware;
   continuar validando um arquivo quando o usuário o fornecer.
2. Adaptar o primeiro boot para a geração pelo Xemu, sem substituir essa etapa
   por uma EEPROM pessoal ou genérica embutida no projeto.
3. Persistir a EEPROM gerada no SSD e preservar a identidade no desligamento,
   reinício, manutenção e atualização do Xemu.
4. Verificar instalação sem EEPROM, importação com EEPROM, persistência entre
   boots e comportamento com arquivo fornecido inválido.
5. Somente depois publicar uma nova IMG e atualizar os guias/arquivos da release
   para anunciar a EEPROM como opcional na versão efetivamente entregue.
