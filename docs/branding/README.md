# Logos X-Revive

- Plymouth: BOOT enviado anteriormente, mantido na mídia.
- Instalador e atualizador: PNG sem sufixo do usuário, em
  `cartucho/overlay/usr/share/console/logo.png`.
- `x-revive-bios-reference.png`: referência raster enviada pelo usuário.
- `x-revive-bios-original.svg`: SVG enviado, preservado sem alteração.
- `x-revive-bios.svg`: cópia compatível com NanoSVG/Cerbios: texto convertido
  em curvas, clones expandidos, arcos convertidos em Bézier. Filtros e padrão
  que o renderizador não representa foram removidos/substituídos por cor sólida.
  A aparência é vetorial simplificada; não reproduz a textura fotográfica PNG.

Preparação em Cerbios Tool V3.1.0 oficial, num container com display virtual,
sem acessar o desktop ou flash de hardware. Original fornecido permaneceu
montado somente para leitura. BIOS e EEPROM não são assets públicos.

Cópia privada personalizada: `cartucho/cache/cerbios-tool-v3/x-revive-cerbios.bin`.
Reaberta no editor: todas as configurações exportadas coincidiram com o
original, exceto SplashData. Verificação em `verification.json`; prévia em
`reloaded-bios.png`. O simples ato de salvar o original no editor já muda
55.192 bytes por reempacotamento; a comparação de offsets brutos não deve ser
interpretada como equivalência de configurações. Boot real em emulação precisa
ser registrado no gate antes de adotar a cópia nos arquivos da bancada.

A cópia personalizada iniciou a animação Xbox e XBMC4Gamers em SSD virtual sem USB,
com o SHA de firmware conferido. O splash BIOS não apareceu nas capturas dessa
VM: a aplicação do SVG foi confirmada reabrindo a BIOS no editor, mas a exibição
ainda é um gate visual separado. Não afirmar que o emblema apareceu no Xbox
sem essa evidência. Original em Downloads permanece intacto; a pasta particular
de arquivos da bancada recebeu a cópia personalizada como bios.bin.
