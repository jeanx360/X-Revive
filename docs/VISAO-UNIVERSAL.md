# Visão: console universal por mídia (X-Revive)

Registro da direção do projeto (2026-10-22). Ainda NÃO implementado — é o norte.

Atualizacao 2026-10-23: o usuario autorizou estudar uma terceira variante
standalone, como excecao opcional ao HDD puro descrito abaixo. A regra de disco
Xbox separado continua padrao das duas imagens USB. O novo modo precisa provar
isolamento e compatibilidade antes de tocar em discos reais; nao reutilizar
as proibicoes historicas como veto ao prototipo explicitamente autorizado.
Ver [roadmap atual](ROADMAP-2026-10-23.md).

## 0. Princípios inegociáveis (a alma do projeto)

- **Sistema único, sem Windows.** Nada de SO pesado por trás. Só o mínimo de
  Linux invisível para a máquina virar o console.
- **Não é um emulador "aberto num PC".** É um aparelho que, para quem usa, É o
  console: liga, aparece o logo, a animação, a dashboard — e pronto.
- **A experiência do console REAL é o objetivo final.** Comportamento, boot,
  mídia, controles, manutenção — tudo imita o console de verdade, não um
  programa rodando sobre um desktop.
- Cada decisão de arquitetura serve a isso: invisibilidade do Linux, boot
  direto, mídia como cartucho, portas livres para o console.


## 1. O modelo "um console por mídia" (cartucho)

A ideia central: **cada mídia é um console completo**. Trocar a mídia = trocar de
console, como trocar um cartucho.

- Cartucho do Xbox (SSD/HD com o sistema Xbox), cartucho do PS2, do GameCube/Wii,
  do WiiU, e por aí vai.
- **Um único hardware** físico (uma placa), compatível com controles de Xbox — e,
  idealmente, de Switch e PlayStation também.
- Um **sistema de swap de mídia**: trocar o SSD (ou outra mídia) como se fosse o
  cartucho daquele console.
- Todas as portas da placa — **USB, SATA, NVMe, rede, som, vídeo** — ficam livres
  para o console usar, porque o sistema não precisa ocupar mídia/portas extras.

O Xbox é o **primeiro** (o favorito), quase na reta final.

## 2. XBOX: disco de Xbox PURO + pendrive SEPARADO (regra fixa)

Para o Xbox Clássico isto é **inegociável** e é exatamente como já está feito:

- O **disco (HD/SSD) é um disco de Xbox PURO — 100% compatível** com um Xbox
  original: só partições **FATX**, nada de Linux. Formatável e substituível de
  dentro do console (HeXEn), respondendo como num Xbox de verdade (erros 07/13/16,
  chave da EEPROM, etc.).
- O **instalador/bootável é SEPARADO do disco** (o pendrive). Justamente por isso:
  se o usuário formatar ou **trocar o disco**, ele tem que responder como num Xbox
  real — e isso só é possível se o sistema NÃO estiver no disco.
- **NUNCA instalar o sistema Linux no disco do Xbox.** Isso quebraria a fidelidade.
- O pendrive é o **"console/firmware" + manutenção**: dá boot e, quando precisa,
  carrega o **HeXEn** (disco utilitário). O disco é o **"disco do Xbox"**
  (dashboard, jogos). O **"cartucho" do Xbox = o par pendrive + disco**.

### Formatação: quem formata é o HeXEn, não o Linux (decidido no teste 2026-10-22)

O Linux **nunca** formata o disco. Quando o console **não detecta FATX** (disco
novo ou trocado), ele **abre o HeXEn automaticamente** no boot; a pessoa formata
e instala a dashboard por **dentro do HeXEn**, exatamente como num disco de
manutenção de Xbox real. Assim o disco permanece 100% puro e some a antiga
formatação pelo lado Linux (que era frágil em discos grandes, ex.: 1 TB).
- `prepare.sh` só **lê** a assinatura FATX e exporta `HDD_FATX=yes|no`.
- `configure.sh`: sem FATX → cria a flag `boot-hexen`; `run.sh` carrega o
  `hexen.iso` como disco virtual (o Cerbios dá boot no disco da bandeja).
- Havendo FATX → boota a dashboard normal.
- Alternativa manual: segurar **Start+Back** ao ligar (se o controle já respondeu
  — no cold-boot ele costuma demorar, por isso o automático por "sem FATX").

## 3. Boot mais rápido — SEM tocar na pureza do disco

O primeiro boot é, por natureza, mais lento (faz o que só precisa uma vez):
identificação de hardware (perfil da HAL), formatação mínima do disco, config.

Os boots seguintes devem ser **mais rápidos**, mas a otimização mora **no lado do
pendrive**, nunca no disco do Xbox:
- o **perfil de hardware já fica cacheado no pendrive** (partição CONSOLE,
  `profiles/<fingerprint>.conf`) — nos boots seguintes, não há re-detecção;
- o cache de shaders já é persistente (partição CACHE do pendrive);
- o que dá pra encurtar: pular passos já feitos (detecção, formatação), enxugar o
  sistema/serviços, acelerar/ajustar o `toram`.
- O tempo do boot do **Cerbios → animação → dashboard** é inerente ao Xbox e deve
  ser preservado (é parte da experiência real).

O disco permanece **puro Xbox** o tempo todo.

## 4. Por plataforma (cada console é diferente)

- **Xbox** (atual, favorito, quase fechado): disco FATX puro + pendrive separado +
  Cerbios + xemu. Modelo da seção 2 — **fixo**.
- **PS2, GameCube/Wii, WiiU, etc.** (futuro): **comportamento diferente**, a ser
  definido depois. Cada um tem seu emulador, seu formato de armazenamento e suas
  regras — o modelo de mídia pode não ser o mesmo do Xbox.

O conceito de "um console por mídia / cartucho" se mantém como visão geral (trocar
a mídia = trocar de console), mas **os detalhes de cada console se definem caso a
caso**, respeitando a fidelidade daquela plataforma — como o Xbox exige o disco
puro e o bootável separado.

Objetivo final: um **sistema universal** de consoles num hardware só, com todas as
portas livres, controles modernos — sem abrir mão da fidelidade de cada aparelho.
