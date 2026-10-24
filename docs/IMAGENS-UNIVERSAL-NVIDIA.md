# Entrega em duas imagens

Documento historico da primeira entrega dupla. Atualizacao: o usuario depois
confirmou FTP fisico com instalacao de jogos/homebrew; eject funciona pelo menu
Xemu, mas a dashboard ainda exigia correcao. A entrega atual passa a incluir
uma terceira variante standalone experimental: ver [roadmap atual](ROADMAP-2026-10-23.md).

## Requisito e plano aprovado

Manter arquitetura atual e gerar duas imagens a cada entrega de roadmap/bugs:
universal e NVIDIA para a bancada Xeon E5-2680 v4 + GTX 750 (10de:1381).
Som e R estao confirmados no hardware; IP foi obtido. FTP fisico ainda precisa
de teste pratico. Eject e graficos da variante NVIDIA foram confirmados pelo
usuario em 2026-10-23. Este documento registra a primeira entrega; o trabalho trata
do build duplo e do perfil grafico, sem declarar esses itens resolvidos.

## Implementacao

`cartucho/build/build.sh xbox ~/Downloads/xbox-console` gera sempre as duas:

- `out/console-xbox-universal.img`: drivers amplos, HAL automatica, sem pacote
  proprietario NVIDIA. Universal significa imagem generica, nao garantia de
  compatibilidade com todo hardware.
- `out/console-xbox-nvidia.img`: mesma base, acrescentando NVIDIA proprietario
  550.163.01-2 do Debian trixie, DKMS para o kernel da imagem, EGL/GBM/Wayland,
  ICD Vulkan e KMS cedo no initramfs. Comeca em OpenGL e escala 1 na NVIDIA.
  O driver nvidia-open nao e usado: a GTX 750 e Maxwell.

O host Fedora atualmente usa 580.178.04; nada e instalado ou trocado nele.
O build usa os pacotes Debian e valida o vermagic dos modulos para o kernel
embarcado. Secure Boot deve permanecer desligado, como nas imagens anteriores.

Uma base comum e construida, a universal e emitida, e so depois os pacotes
NVIDIA sao acrescentados para emitir a segunda variante. Um build_id e um
hash dos fontes identificam o par em `out/release.json` e dentro das imagens
(`CONSOLE/config/build.json`, `/usr/share/console/build.json`). Cada variante
tem checksum e lista dos pacotes instalados. Cache de perfil inclui variante
e driver para nao reutilizar decisoes de nouveau com o driver proprietario.

A saida temporaria fica em cache/pair.*, fora de out. As duas imagens precisam
terminar e ter identidades compativeis antes de substituir a entrega anterior.
O manifesto release.json e publicado por ultimo; depois de uma interrupcao
durante publicacao, seus checksums devem ser conferidos antes de gravar.
Manter apenas as duas imagens oficiais em out, sem aliases ou copias antigas.

## Aceitacao

1. Testes de regressao: R/FATX, audio, configuracao de rede, persistencia e eject.
2. Teste de publicacao: par incompleto/divergente nao substitui entrega existente.
3. Build: GPT das duas imagens, pacotes e modulos NVIDIA, initramfs e identidades.
4. Boot virtual das duas variantes como smoke test; nao comprova aceleracao GTX.
5. Bancada NVIDIA: gravar variante dedicada, conferir nvidia-smi, driver em uso,
   dashboard em tela cheia e desempenho utilizavel, preservando som, rede e R.
6. FTP fisico ainda precisa de teste; eject do DVD foi confirmado na bancada.

## Entrega gerada e verificacoes

Par `20261023T021009Z-aa2fe991c108`, kernel `6.12.113+deb13-amd64`.
As duas imagens tem 3.894.411.264 bytes; os hashes completos estao em
`cartucho/out/release.json` e nos arquivos `.img.sha256`.

- 15 testes automatizados passaram, incluindo rejeicao de publicacao de par
  incompleto/divergente e preservacao da entrega anterior.
- GPT das duas imagens verificada no build; fontes ainda correspondem ao hash
  registrado no manifesto apos a geracao.
- DKMS NVIDIA 550.163.01-2 compilado para o kernel embarcado. Os quatro modulos
  proprietarios (nvidia, modeset, uvm e drm) foram conferidos no initramfs.
- Ambas iniciaram em VM KVM/virtio com HDD FATX em snapshot. R foi detectado,
  a animacao do HeXEn apareceu, os servicos permaneceram ativos e a interface
  Linux recebeu IP via DHCP. Captura WAV teve sinal nas duas variantes.
- Evidencias: `bancada/validacao-dual/{universal,nvidia}/`, com `result.json`,
  `serial.log`, `checks.log`, `audio-result.json`, `audio.wav` e `tela.png`.
  Reproduzir com `python3 bancada/smoke-image.py universal` e depois `nvidia`.

O smoke test inicia diretamente o kernel/initrd extraidos das imagens; nao
valida o caminho UEFI/GRUB, nem passa a GTX 750 fisica para a VM. Nao comprova
aceleracao NVIDIA, splash fisico, menu completo do HeXEn ou FTP entre PCs.
Posteriormente o usuario confirmou graficos perfeitos e eject fisico funcionando
nessa entrega. FTP fisico permanece pendente. A proxima entrega corrige logo,
adiciona G/OGXbox completo e prepara animacao Xbox: ver `BOOT-LOGO-OGXBOX.md`.

Referencias:
- https://packages.debian.org/trixie/nvidia-driver
- https://download.nvidia.com/XFree86/Linux-x86_64/550.163.01/README/supportedchips.html
- https://download.nvidia.com/XFree86/Linux-x86_64/550.163.01/README/gbm.html
