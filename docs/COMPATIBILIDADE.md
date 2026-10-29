# Compatibilidade e requisitos — X-Revive beta.5-live.6

**Referência:** `v0.1.0-beta.5-live.6`, conforme a release GitHub. Esta página descreve **o que se sabe**, não uma garantia universal. Veja os [resultados de bancada e VM](BETA.md).

> A instalação limpa apaga o destino. LIVE protegido e preparação/reparo de boot têm fluxos separados; [limites](PRESERVACAO-HDD.md).

## Requisitos da beta pública

| Componente | Requisito conhecido | Observação |
| --- | --- | --- |
| CPU | PC **x86-64** | Desempenho do Xemu varia; muitos núcleos não compensam baixa velocidade por núcleo |
| Boot | **UEFI** | Secure Boot **não validado** nesta beta: desative para testar |
| USB | Pendrive de **16 GB ou mais** | O instalador usa uma área `XREVIVE` exFAT para arquivos do usuário |
| Destino | HDD/SSD **dedicado** com pelo menos **32 GiB**, menor que **2 TiB** | Exige setores lógicos de **512 bytes**; destino será integralmente apagado |
| Gráficos | GPU e drivers suportados pela imagem | Mesa e driver proprietário NVIDIA **550** incluídos na beta; não implica compatibilidade com todas as placas |
| Controle | Controle compatível, ou teclado | Firmware de Xbox Wireless Adapter fornecido pelo usuário; importação antes da interface |
| Rede | Ethernet/DHCP ou Wi-Fi pessoal compatível | Wi-Fi no assistente, conforme adaptador e firmware |
| Firmware Xbox | `bios.bin` e `mcpx_1.0.bin` fornecidos pelo usuário | `eeprom.bin` é opcional, mas a identidade original depende de seu backup |

A documentação da beta recomenda reservar pelo menos 16 GB livres no computador usado para descompactar a IMG antes da gravação.

## O que foi efetivamente testado

As evidências públicas em [BETA.md](BETA.md), [VALIDACAO-ONLINE-2026-10-24.md](VALIDACAO-ONLINE-2026-10-24.md) e [ROADMAP-2026-10-23.md](ROADMAP-2026-10-23.md) incluem:

- **VM:** instalação online/offline, boot pelo SSD, dashboard, áudio, seleção pelo controle e confirmações destrutivas.
- **Bancada física:** inicialização, áudio, rede/FTP, instalação de jogos/homebrew e abertura/fechamento da bandeja de DVD.
- **GTX 750:** suporte validado na bancada com o driver proprietário NVIDIA 550; não generalizar para todas as GPUs NVIDIA.
- **Xbox original com modchip:** experiência e compatibilidade física com discos preparados **ainda não conclusivamente comprovadas** na beta pública.

Não há matriz publicada que autorize declarar desempenho satisfatório em todos os jogos, todas as GPUs Intel/AMD/NVIDIA ou em qualquer notebook antigo.

## Detecção automática não significa compatibilidade universal

O projeto possui uma camada de adaptação de hardware (HAL) para identificar componentes e selecionar perfis/serviços disponíveis. Ela reduz etapas manuais, mas **não fabrica suporte quando o driver ou os recursos gráficos necessários não existem**. Os jogos também dependem da compatibilidade do Xemu.

Para testar um hardware novo, informe CPU, GPU, RAM, versão da BIOS/UEFI, modo de boot, versão X-Revive, controlador usado, resultado de áudio/vídeo e, se houver falha, os logs sem arquivos privados.

## Arquivos e restrições legais

A IMG inclui software e drivers, mas **não fornece** BIOS, MCPX, EEPROM pessoal, jogos ou a animação original proprietária. O modo online baixa recursos a partir de origens e hashes documentados; isso não altera direitos ou licenças de terceiros. Consulte [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md).

[Voltar ao índice](INDEX.md) · [Guia de instalação](BAIXAR-E-INSTALAR.md) · [Relatar um problema](https://github.com/jeanx360/X-Revive/issues)
