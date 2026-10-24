# Carcaça do Xbox

Fica para depois da bancada (V1–V9). Pontos já definidos:

## Portas de controle

As portas do Xbox original são **USB 1.1** com conector proprietário (5 fios:
VCC, D−, D+, GND e um fio extra para sincronismo de light gun). Basta ligar cada
porta a um header USB interno da placa: os controles originais (Duke/S) funcionam
direto pelo driver `xpad`, sem adaptador. Controles modernos entram pelas USB
traseiras ou por Bluetooth.

## Painel frontal (Power, Eject, LEDs)

O conector da placa do painel frontal muda entre revisões (1.0–1.6). **O pinout
vai ser levantado com multímetro na sua placa**, e não copiado de memória.
Plano:

- Power → `PWR_SW` do header JFP1 da placa (curto momentâneo).
- Eject → GPIO de um microcontrolador USB pequeno (ex.: RP2040) que o
  `dvd-bridge` lê como evento de ejetar. O JFP1 não tem uma entrada livre para isso.
- LEDs verde/vermelho → controlados pelo mesmo microcontrolador para reproduzir
  os padrões do Xbox (verde fixo = ok; vermelho/verde piscando = erro).

## Energia e calor

Fonte interna original não serve. Usar fonte PicoPSU + fonte externa, ou fonte
SFX/Flex dependendo da placa. Preferir hardware de até 65 W (ver HARDWARE.md).
