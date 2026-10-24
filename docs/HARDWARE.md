# Hardware

## 1. Camada de adaptação (HAL)

Não é "aprendizado" no sentido de IA. É uma camada **determinística** que roda a
cada boot, antes do emulador:

1. **Detecta**: CPU (modelo, núcleos, clock), GPU (fabricante, PCI ID, Vulkan
   disponível), saída de áudio, portas SATA, leitor óptico.
2. **Identifica a máquina** por uma impressão digital (DMI da placa + PCI ID da GPU).
3. **Carrega o perfil** dessa máquina de `CONSOLE/profiles/<impressao>.conf`. Se não
   existir, cria um a partir da tabela de níveis abaixo.
4. **Gera a configuração** do xemu (renderer Vulkan/OpenGL, escala de resolução,
   vsync, dispositivo de áudio).

Resultado: o **mesmo pendrive** liga num Xeon, num Ryzen ou num Intel. Cada
máquina ganha o seu perfil e o pendrive guarda todos. O "console" (EEPROM, HDD)
não muda, só o ajuste de desempenho.

Uma calibração opcional (rodar uma cena de teste e medir quadros) pode refinar o
perfil depois, mas o nível inicial já tem que funcionar sem ela.

### Níveis

| Nível | Critério aproximado                                                  | Ajuste                                   |
|-------|----------------------------------------------------------------------|------------------------------------------|
| A     | CPU com single-thread ≥ Ryzen 3000 / Intel 9ª ger.; GPU Vulkan 1.3 forte | Escala 3×–4× (até 4K), Vulkan            |
| B     | Single-thread ≥ Haswell / Ryzen 1000; GPU Vulkan 1.1+ ou GL 4.x        | Escala 1×–2× (480p–960p), Vulkan ou GL   |
| C     | Abaixo de B                                                          | Escala 1×; aviso de desempenho no perfil |

Os critérios exatos saem da bancada (VALIDACOES.md V5), não de suposição.

## 2. Mínimo para "comportamento perfeito"

Para a parte física (BIOS, HDD, DVD, controles) qualquer x86-64 com UEFI, uma
porta SATA livre e USB serve. O que varia é o desempenho dos jogos:

- **Mínimo jogável**: 4 núcleos, single-thread nível Haswell (2013+), GPU com
  Vulkan 1.1 ou OpenGL 4.0, 4 GB RAM.
- **Recomendado (resolução nativa sem engasgos na maioria dos jogos)**: Ryzen 5
  3400G/5600G ou Intel 10ª ger.+, 8 GB dual-channel.
- O emulador usa poucas threads com força; 28 threads não ajudam muito, clock
  alto por núcleo ajuda.

## 3. Driver gráfico por fabricante

| GPU                       | Driver                     | Observação                                      |
|---------------------------|----------------------------|-------------------------------------------------|
| AMD (Vega, RDNA)          | Mesa RADV (no squashfs)    | Melhor caso para appliance: tudo open source.   |
| Intel (UHD, Iris Xe, Arc) | Mesa ANV                   | Bom.                                            |
| NVIDIA Maxwell/Pascal     | proprietário série 580     | 580 é a última série que suporta essas GPUs.    |
| NVIDIA Turing+            | proprietário ou Mesa NVK   |                                                 |

O pendrive leva **todos** os drivers; a HAL só escolhe. Por isso o sistema
precisa ser glibc (Debian), não Alpine.

## 4. Por que não dá para rodar "nativo"

O raciocínio "o Xbox é fraco, então um PC moderno roda o sistema dele direto" só
vale para a CPU: o Pentium III do Xbox é x86, igual ao PC. O resto do console não
existe num PC:

- **GPU NV2A**: chip NVIDIA feito sob medida. Jogos e kernel do Xbox escrevem
  direto nos registradores dela. Nenhuma GPU de PC entende esses comandos, então
  cada comando precisa ser traduzido para Vulkan/OpenGL em tempo real. É aqui que
  vai quase todo o custo.
- **MCPX**: áudio (DSP próprio), USB, rede, IDE e o boot ROM. Também é emulado.
- **Memória unificada de 64 MB** compartilhada CPU/GPU, com timings que os jogos
  assumem.

Emular um chip com fidelidade custa muitas vezes mais do que o chip original.
Por isso um PC "20× mais rápido" que o Xbox fica só no limite.

## 5. Máquinas do projeto

- **PC de desenvolvimento** (Xeon E5-2680 v4 + GTX 750): só escrita de código e
  geração da imagem. **Nenhum teste de hardware roda nele.**
- **Bancada / alvo final**: placa-mãe Acer NB8609_PCB_MB_V4 (notebook), montada
  na carcaça do Xbox Clássico.

### Placa Acer NB8609_PCB_MB_V4 (Aspire A315-34)

- CPU: Intel Celeron N4000 / N4020 (Gemini Lake, **2 núcleos / 2 threads**,
  1,1 GHz base, até 2,6–2,8 GHz em burst, sem AVX)
- GPU: Intel UHD 600 (12 EUs), Vulkan pelo Mesa ANV
- RAM: DDR4 soldada + 1 slot SODIMM
- Saídas: 1 HDMI, 2 USB; sem drive óptico

Avaliação para o **Xbox (xemu)**: **abaixo do nível C**. Deve dar boot (animação,
dashboard, HeXEn), o que já serve para validar o comportamento físico (BIOS no
pendrive, HDD SATA, erros 07/13, controles). Jogar fica lento na maior parte do
catálogo. Para PS2 (PCSX2) a situação é parecida ou pior.

Uso recomendado desta placa:

1. **Bancada de comportamento**: provar V2, V3, V4, V6, V7, V8 e V9, que
   dependem de funcionar e não de desempenho.
2. **Consoles mais leves** como cartuchos próprios (ver tabela abaixo).
3. Quando houver uma placa mais forte, o mesmo pendrive passa a rodar Xbox de
   verdade sem mudar nada no projeto.

Leitor DVD: a placa não tem drive óptico. O leitor entra por USB (slim USB ou
SATA com adaptador) e é tratado do mesmo jeito pelo `dvd-bridge`.

### Que console cada nível de hardware aguenta (estimativa)

| Console          | Emulador     | Celeron N4000 (esta placa) | Nível B   | Nível A |
|------------------|--------------|----------------------------|-----------|---------|
| SNES / Mega Drive| libretro     | perfeito                   | perfeito  | perfeito |
| PS1              | DuckStation  | bom                        | perfeito  | perfeito |
| N64              | Mupen64Plus  | a maioria                  | bom       | bom     |
| Dreamcast        | Flycast      | parte do catálogo          | bom       | perfeito |
| PS2              | PCSX2        | muito limitado             | bom       | perfeito |
| Xbox Clássico    | xemu         | só boot/dashboard          | bom       | perfeito |
| GameCube         | Dolphin      | muito limitado             | bom       | perfeito |

A coluna desta placa precisa ser confirmada na bancada.

## 6. Identidade do console (backup do Xbox danificado)

O Xbox Clássico tem **dois** chips relevantes, não uma NAND:

| Chip              | O que é                          | Onde está no backup?            |
|-------------------|----------------------------------|---------------------------------|
| Flash TSOP/LPC    | BIOS (256 KB / 1 MB)             | provavelmente é o "backup da nand" |
| EEPROM (24LC02)   | 256 bytes: serial, MAC, **HDD key** | precisa conferir              |
| Boot ROM do MCPX  | 512 bytes **dentro** do chip MCPX | não sai do backup da flash      |

O `eeprom.bin` é o que liga o HDD a este console. Se o HDD original desse Xbox
ainda existir, com o EEPROM certo ele pode continuar sendo "o HD deste console".
