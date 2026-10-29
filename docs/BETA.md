# Pré-release v0.1.0-beta.5-live.6

IMG para PC x86-64 UEFI com LIVE por mídia/HDD, instalação Rocky5, Wi-Fi,
manutenção e recuperação de boot. [Download e gravação](BAIXAR-E-INSTALAR.md).

## Modos

| Modo | Comportamento |
|---|---|
| LIVE protegido | HDD virtual ou HDD Xbox somente leitura; mudanças temporárias na RAM |
| LIVE instalação/manutenção | Mídia com escrita somente no disco escolhido, após duas confirmações |
| Instalar X-Revive | Instalação limpa: apaga o destino e prepara boot próprio |
| Preparar/reparar boot | Recria sistema/UEFI na área reservada fora do FATX, preservando os volumes Xbox |

F ocupando o disco inteiro não é reduzida automaticamente. Não use a instalação
limpa para preservar jogos existentes. [Preservação e limites](PRESERVACAO-HDD.md).

## Requisitos e operação

- PC x86-64 UEFI; Secure Boot desativado para testar.
- Pendrive ≥16 GB, área XREVIVE exFAT de 10 GiB já pronta.
- Instalação limpa: HDD/SSD dedicado ≥32 GiB, menor que 2 TiB, setores de 512 bytes.
- BIOS e MCPX próprios; EEPROM e animação Xbox opcionais.
- Teclado ou controle. Firmware privado do dongle, se necessário, em
  `X-Revive/firmware/dongle/`.
- Ethernet/DHCP ou Wi-Fi compatível configurado pelo assistente.

Mesa e NVIDIA 550 permanecem na mesma imagem; suporte depende do dispositivo.
O assistente mostra atividade, etapa e tempo; F1/X abre detalhes, Esc/B cancela
preparação quando disponível. Gravações de boot precisam terminar.

## Evidências

124 testes locais passaram na candidata C7. Em VM: Rocky5 offline e OGXbox,
áudio, FTP, proteção e boot do SSD-clone reparado. Um HDD físico de 1 TB foi
usado na VM por descritor somente leitura: HeXEn e transferência FTP em RAM
passaram; hashes de metadados e blocos alocados permaneceram iguais. Animação,
cancelamento, registro de etapas e prazo de 90 s foram exercitados.

Os relatos de campo das etapas anteriores incluem GTX 750, áudio/FTP/bandeja,
boot do assistente e Wi-Fi no Dell G15, e controle sem fio desde o início.
Esses relatos não validam todo hardware ou todo fluxo novo da C7. A publicação
desta pré-release foi autorizada em 28/10/2026. [Relatório](VALIDACAO-LIVE6-RECUPERACAO.md).

## Limitações

- Sem migração automática de F para criar espaço de boot; não alterar só PARTINFO.
- Compatibilidade com Xbox original modchipado exige teste próprio.
- FTP externo por Wi-Fi ainda precisa de teste específico; não confundir com NAT da VM.
- Wi-Fi pessoal temporário; redes corporativas, ocultas e portais não são configurados.
- Canal público de atualização Xemu ainda não ativo; kernel/driver não atualizam por ele.
- Download online e ISO pessoal/cache podem disputar os 10 GiB do USB. O DVD
  virtual offline dispensa a segunda cópia integral, não o armazenamento da origem.
- APT sem snapshot completo e timestamps variáveis; build não é hermético.

Para relatar erro, informe build, hardware, caminho escolhido e última etapa.
Revise os diagnósticos antes de anexar; não envie firmware, chaves ou discos.
A [beta.4 anterior](https://github.com/jeanx360/X-Revive/releases/tag/v0.1.0-beta.4) permanece disponível.
