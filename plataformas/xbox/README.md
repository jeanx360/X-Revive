# Plataforma Xbox Clássico

Xemu de fábrica na bancada: 0.8.138-xrevive-smc2, compilado com patches X-Revive
para bandeja SMC e menu Start+digital para cima. Versão efetiva está no manifesto
do build; uma atualização pode selecionar outra versão na CACHE.

## Firmware do usuário

Forneça no USB `XREVIVE/X-Revive/firmware/xbox/`:

```text
bios.bin       BIOS compatível: 256, 512 ou 1024 KiB
mcpx_1.0.bin   boot ROM MCPX 1.0: 512 bytes
eeprom.bin     OPCIONAL: EEPROM do usuário, 256 bytes
```

BIOS e MCPX são obrigatórios. Sem EEPROM fornecida, o próprio Xemu gera uma no
primeiro boot e o X-Revive a preserva imediatamente no SSD para os próximos boots.
Uma EEPROM fornecida é importada e preservada. Nenhum desses arquivos está no
Git. Os arquivos fornecidos são validados e importados para CONSOLE na instalação.
A EEPROM contém a identidade do console: não publique seu conteúdo.
Compatibilidade entre revisão do console, BIOS, MCPX e EEPROM exige arquivos
adequados; não se deve converter identidade ou trocar BIOS às cegas.

Animação Cerbios opcional: `firmware/bootanims/Xbox/BootAnim.xbe` e `bootanim.ini`.
Não incluímos o executável. O SVG X-Revive é arte, não uma BIOS alternativa aberta.
A personalização privada de BIOS não concede direitos de distribuição.

## Coleção e disco

O instalador baixa Rocky5 ou lê ISO normalizada; instala em modo hardmod, sem
exploit/nkpatcher nem flash de firmware. XBMC4Gamers é o padrão.

- C: Microsoft Dashboard 5960 e Dashloader Rocky5 (`evoxdash.xbe`).
- E: recuperação, UDATA/TDATA e animação opcional.
- F: dashboards, apps, emuladores e trainers.
- G: divisão da área estendida quando necessária.

`C:\Dashloader.ini` seleciona dashboard. A manutenção verifica o executável e
altera essa configuração. O gravador FATX escreve e lê de volta todos os arquivos.
O disco híbrido mantém prefixo nativo e sistema PC reservado no final, exposto
com limite ao emulador. Não confundir coexistência acidental de NTFS/FATX com
particionamento seguro. Instalação apaga o destino após duas confirmações.

Limites atuais: UEFI, setores lógicos de 512 bytes, disco menor que 2 TiB.
A capacidade máxima anunciada pelo Cerbios não amplia esses limites do projeto.
Compatibilidade com Xbox original modchipado requer validação física separada;
formatadores externos podem ignorar e destruir a região do sistema PC.

`tools/hdd.py` e importador antigo de animação são ferramentas históricas, não o
instalador atual. Os assets locais em firstrun são privados/ignorados e não entram
na mídia nova. Veja [guia](../../docs/INSTALADOR-ONLINE.md) e
[estado da beta](../../docs/BETA.md).
