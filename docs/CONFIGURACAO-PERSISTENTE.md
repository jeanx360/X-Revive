# Preferências persistentes do Xemu

Reparo autorizado em 2026-10-22, a partir da pendência #3 da rodada 2.

## Requisito e limite

Alterações de RAM (64/128 MB), renderer, escala e vsync feitas no menu do Xemu
devem sobreviver ao desligamento normal e ao próximo boot na mesma máquina.
Manter o HDD FATX sem arquivos Linux e manter os caminhos de firmware, EEPROM,
HDD e DVD sob controle da detecção atual. Não alterar drivers ou tratar os
problemas visuais da GTX 750 nesta correção.

## Implementação

`configure.sh` continua gerando `/run/console/xemu.toml` com valores da HAL e
`ports.conf`. Depois, `tools/preferences.py restore` aplica apenas as quatro
preferências permitidas de `CONSOLE/config/xemu/<fingerprint>.json`. As escolhas
salvas têm precedência sobre esses valores iniciais. Outra máquina começa com
seus próprios padrões. Vulkan salvo só é restaurado quando a HAL informa suporte;
caso contrário, permanece o renderer detectado pela HAL.

O Xemu continua escrevendo a cópia em RAM, inclusive ao reiniciar pelo menu.
No desligamento normal, após o serviço do emulador parar, `save.sh` captura as
preferências válidas e salva no pendrive durante a janela de remount rw usada
também pela EEPROM. EEPROM inalterada não interrompe mais o salvamento.
As gravações de preferências usam arquivo temporário e substituição atômica;
o script tenta devolver o pendrive a ro mesmo ao falhar. Caminhos de dispositivos
e outras chaves do TOML não são importados. Preferências corrompidas são ignoradas
no boot com diagnóstico no journal, preservando os padrões gerados.

Desligamento abrupto pode perder as alterações da sessão. Este reparo não torna
uma BIOS compatível com 128 MB e não adiciona suporte Vulkan à GPU.

## Verificação

Testes automatizados em diretórios temporários, sem discos físicos:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
sh -n plataformas/xbox/configure.sh plataformas/xbox/save.sh
```

Cobrem restauração após boot com novos caminhos de disco, isolamento por hardware,
fallback de renderer, configuração corrompida e execução real de `save.sh` com
remount simulado e EEPROM inalterada. Não substituem teste no Xemu instalado.

## Aceitação pendente

1. Nova imagem gerada em 2026-10-22: `cartucho/out/console-xbox.img`, 3.894.411.264
   bytes. GPT verificada sem erros; scripts `configure.sh`, `save.sh` e
   `preferences.py` extraídos do SquashFS e comparados aos fontes com sucesso.
   Bootloader UEFI, kernel, initramfs, firmware e HeXEn presentes.
   SHA-256: `5900ab4c9edc8d3aa8b6d957c3b229cfa381c170285b35ef27c1439316e00949`.
2. Na bancada, alterar RAM e vsync no menu, desligar normalmente, ligar e conferir
   o menu e `config/xemu/<fingerprint>.json` no pendrive.
3. Repetir com renderer em hardware compatível. Conferir também o restart do menu.
4. Validar EEPROM e boot da dashboard após o ciclo. Não formatar o HDD para testar.

Estado: implementação, testes locais e geração/verificação da imagem concluídos;
boot e aceitação física pendentes. Backup da imagem anterior em
`cartucho/out/console-xbox-anterior-20261022.img`.
