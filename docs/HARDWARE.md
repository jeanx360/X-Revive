# Hardware e camada de adaptação — X-Revive beta.4

Este documento é uma **orientação técnica da versão pública atual**, não uma lista de hardware universalmente certificado. Requisitos completos: [COMPATIBILIDADE.md](COMPATIBILIDADE.md).

## O que faz a HAL

A HAL (Hardware Abstraction Layer) detecta características da máquina, como CPU, GPU, áudio, dispositivos e interfaces relevantes, e adapta a configuração do Linux/Xemu conforme os recursos disponíveis. Perfis podem reduzir etapas repetidas de detecção na mesma máquina, quando o fluxo usado os preserva.

**Não é aprendizagem de IA e não torna toda GPU compatível.** Seu papel é identificar e selecionar mecanismos suportados pelos drivers incluídos e pela emulação.

## Driver gráfico na imagem publicada

A beta.4 contém **Mesa** e **NVIDIA proprietário 550** na mesma imagem, incluindo suporte validado na bancada com **GeForce GTX 750**. Não confunda com documentos experimentais antigos que citam várias imagens de instalação, NVIDIA 580 ou planos de suporte universal.

| Família | Caminho previsto | Limite |
| --- | --- | --- |
| GPUs AMD suportadas pelo Mesa | Driver Mesa presente | Exigências do renderer e da GPU variam |
| GPUs Intel suportadas pelo Mesa | Driver Mesa presente | GPUs integradas antigas podem não oferecer desempenho suficiente |
| GPUs NVIDIA compatíveis com a linha incluída | NVIDIA proprietário 550 na beta.4 | Não implica suporte a qualquer modelo ou geração NVIDIA |
| Outros dispositivos | Não presumir suporte | Testar drivers, boot, áudio, controle e Xemu por modelo |

Uma placa fraca pode conseguir abrir a dashboard, mas falhar no desempenho de jogos. A compatibilidade do Xemu não é eliminada por usar um PC rápido.

## Mínimos publicados para instalar

- Máquina **x86-64 com UEFI**; Secure Boot não validado nesta beta.
- Pendrive **≥16 GB** e HDD/SSD dedicado **≥32 GiB e <2 TiB**, com setores lógicos de 512 bytes.
- Teclado ou controle com fio compatível; Ethernet/DHCP para preparar a coleção online.
- Firmware autorizado: BIOS e MCPX obrigatórios, EEPROM opcional.

**Não existe uma especificação pública mínima de FPS garantido para todos os jogos.** Celeron N4000/N4020 e outros computadores modestos podem ser úteis para testes de boot e dashboard, mas precisam ser validados antes de anunciar experiência jogável.

## Equipamentos e resultados registrados

Os relatórios de bancada incluem testes com **Xeon E5-2680 v4 + GTX 750**, além de ensaios virtualizados. Os testes documentam áudio, rede/FTP, dashboard e funções de bandeja, com resultados associados às builds específicas. Leia [BETA.md](BETA.md) e os relatórios datados: um teste realizado num build anterior não é garantia de que toda função permaneça perfeita em qualquer sistema.

A ideia de usar uma placa de notebook dentro da carcaça original do Xbox é parte da origem do projeto e dos planos de modificação física. **Não apresente o hardware da carcaça como plataforma certificada sem resultados próprios publicados.**

## Leitor óptico e controles

A integração de bandeja física foi testada em bancada, mas leitura de **discos originais do Xbox** exige drive, firmware e mecanismo compatíveis: um DVD de PC comum não acessa automaticamente essas mídias. Para controle sem fio, a beta pública não inclui firmware do adaptador Xbox Wireless; comece com controle USB ou teclado.

## Como contribuir com a matriz

Abra uma [issue](https://github.com/jeanx360/X-Revive/issues) com:

- CPU, RAM, GPU (modelo exato e ID PCI quando disponível), placa-mãe e versão de UEFI;
- monitor/TV, modo gráfico, controle e leitor óptico;
- versão exata do X-Revive e cenário testado (boot, instalação, dashboard, jogo, FTP, áudio);
- resultado, passos para reproduzir e logs revisados, **sem firmware, EEPROM, HDD key ou dados pessoais**.

[Índice](INDEX.md) · [Arquitetura](ARQUITETURA.md) · [Beta](BETA.md)
