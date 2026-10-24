# Refinamento do boot, DVD e disco unico

## Evidencia fisica anterior, relatada pelo usuario

Na entrega 20261023T032759Z-c17c19a291c8, Xeon E5-2680 v4 + GTX 750:
logo aprovado, R/HeXEn e G/OGXbox iniciaram, audio funcionou, FTP instalou
jogos/homebrew, renderizadores e resolucoes responderam. DVD abriu/fechou pelo
menu Xemu. Dashboard nao movimentava o DVD. O desempenho de jogos pesados na
GTX 750 e limitado. Esse relato nao valida automaticamente as alteracoes abaixo.

## Fonte da correcao e teste virtual

Xemu 0.8.138 ignorava escrita SMC 0x0c, embora a dashboard respondesse sucesso.
Patch minimo sobre bf817de2b0354b7afe5e70efcd4f9c53bc7d4c67 implementa abrir/fechar
e estado/IRQ. Executavel identificado 0.8.138-xrevive-smc1, SHA256
b67d8de170f99bc642ed2e884f844b878a65d8e6635b68b24ff03dc2de719ace.
SDL 3.4.18 vem do subprojeto fixado upstream; nao usar SDL 3.2.10 do Debian,
cuja inicializacao Wayland travou no primeiro ensaio. Vulkan e OpenGL habilitados.

UnleashX recebeu SITE TRAYOPEN/CLOSE duas vezes. Foram exigidos quatro eventos
QMP true,false,true,false e PID Xemu constante. O leitor DVD virtual externo
tambem mudou para aberto/fechado: a cadeia dashboard -> SMC -> QMP -> ioctl
funcionou, sem tocar em leitor fisico. Evidencias em
bancada/standalone-probe/tray-patched-final.log e physical-tray-states.log.
Esse primeiro teste usou o mesmo patch funcional antes do rotulo de versao.

Eventos udev atrasados sem midia poderiam apagar o estado aberto reiniciando
Xemu: adicionados estado tray-open e filtro em media-change.sh. O teste exige
ignorar a notificacao tardia e continuar reiniciando quando nova midia aparece.
Nova confirmacao do mecanismo fisico permanece pendente.

## Prova inicial standalone, em arquivo/VM

Um prototipo com prefixo Xbox 10 GiB, sem USB e sem segundo HDD, iniciou por
UEFI e executou UnleashX. Nesta prova inicial, o runtime novo foi injetado
somente na RAM de uma base antiga; portanto nao e prova de integracao da imagem
final. Os testes seguintes da imagem completa sao registrados separadamente.

- Loop Xbox limitado pelo kernel: leitura no limite retornou EOF; escrita no
  limite retornou ENOSPC. Os bytes iniciais da ESP permaneceram iguais.
- Com Xemu expondo o disco virtual inteiro apenas para QA, Cerbios 3.1 ainda
  respeitou PARTINFO/F de 10 GiB, sem incluir a cauda Linux na unidade F.
- FTP gravou e recuperou 262144 bytes identicos. SHA256 do payload:
  2312394bd99545d9de131c24efb781e765ac1aec243f2ed9347597a793a415e9.
- Os primeiros 16 MiB de SYSTEM mantiveram SHA256
  425bfead042acfd73f7b0431e92a78cf91efb43a4f1bced7d662560833fbce0d.
- Campos MBR foram zerados deliberadamente na VM. O desligamento restaurou-os;
  UEFI reiniciou pelo mesmo SSD e os arquivos E/F continuaram legiveis.

Evidencias: bancada/standalone-probe/{bounds.log,fullview-ftp-final.log,
pre-reboot-proof.log,reboot-uefi.log,reboot-proof.log}. Tudo ocorreu em snapshots;
o HDD virtual de referencia e os discos fisicos ficaram intactos. Isso nao prova
portabilidade fisica num Xbox original nem recuperacao apos qualquer corrupcao.

## Imagens completas e estado da entrega

A entrega anterior fica preservada fora de out. Conjunto final gerado:
20261023T195138Z-f613cf12cef2, fontes
f613cf12cef23cd85c46264c00f2c116568d3ca80f13a535b704d4b8885f8171.
Kernel 6.12.113+deb13-amd64 e NVIDIA 550.163.01-2. Checksums finais ficam no
manifesto cartucho/out/release.json. Publicacao local concluida: exatamente tres
arquivos .img em out, com hashes calculados pelo publicador e manifestos
conferidos apos a troca. O conjunto anterior permanece no backup em cache.
O primeiro rascunho 546e7bfa45fe ficou fora de out apos acrescentar o filtro de
eventos tardios. Nao grava-lo como release final.

No rascunho, o boot UEFI original da universal com R mostrou a confirmacao sob o
logo e chegou ao menu HeXEn; universal com G passou pelo smoke test de servicos,
audio e SHA da ISO OGXbox completa. Captura: bancada/validacao-final/feedback-r.png.

Na versao final, as capturas foram repetidas com UEFI/GRUB originais, sem debug:
universal/R e NVIDIA/G. As mensagens sob o logo e os menus dos utilitarios foram
vistos. Prints selecionados: bancada/validacao-final/feedback-r.png e feedback-g.png.
Logs/capturas completos em bancada/validacao-final/f613cf12/uefi-*.

Smoke tests finais universal/G e NVIDIA/R passaram. O executavel lido de dentro
das imagens correspondeu ao SHA acima e a ISO OGXbox completa correspondeu ao
SHA c171bf98ea1655504c148196091ac50046bdbbf64b350f79cf38ec1b0f82d838.
WAV capturado teve pico 7305 na universal e 8075 na NVIDIA (PCM16, nao silencioso).
Resultados em bancada/validacao-final/f613cf12/{universal-g,nvidia-r}/result.json.

Na standalone final, uma copia QA recebeu somente o arquivo /debug para shell
serial; o runtime de produto permaneceu o da imagem. Um unico SSD virtual, sem
USB e sem HDD adicional. O HeXEn abriu sozinho, e sua propria interface confirmou
e formatou X/Y/Z/C/E e F. As seis assinaturas FATX foram verificadas. SYSTEM
manteve o SHA dos primeiros 16 MiB:
2afc51831363eb1f20f8333801fadbe47f1ff14d4fb81096363597f9642effdb.
Depois foi instalada uma fixture local de dashboard apenas na VM, sem reformatar.
FTP gravou/recuperou o payload identico. A dashboard abriu/fechou duas vezes e
preservou PID mesmo com evento de midia atrasado, usando os scripts ja embarcados
na imagem, sem injecao de correcoes. Evidencias em
bancada/validacao-final/f613cf12/standalone-live/{gui-after.log,final-suite.log}.

O reinicio final tambem passou: UEFI voltou a carregar o sistema, os servicos
ficaram ativos, a animacao foi instalada em E, e os arquivos E/F permaneceram
identicos. MBR e rodape foram validados apos o reinicio. Resultado estruturado e
prova em bancada/validacao-final/f613cf12/standalone-live/{result.json,final-reboot-proof.log}.

O teste adicional de leitor com midia foi feito no prototipo completo: uma ISO
foi inserida no leitor virtual externo, Linux o bloqueou e Xemu abriu o backend
host_device:/dev/sr0. A dashboard abriu sem trocar o PID; ao fechar, a bandeja
fechou e o console reiniciou para a midia, como previsto. Evidencia em
bancada/validacao-final/standalone-live/dvd-media-check.log. Continua sendo um
leitor virtual, nao o mecanismo da bancada fisica.

Os tres artefatos de distribuicao foram inspecionados: nenhum contem /debug.
O prefixo FATX da standalone de distribuicao continua vazio; as formatacoes e
fixtures ficaram nos snapshots de teste. Footer e tabela do arquivo original
foram conferidos novamente em leitura.

## Limites que continuam valendo

31 testes automatizados passaram nesta etapa. Eles nao substituem os testes
fisicos. A standalone padrao e vazia, com prefixo Xbox de 16 GiB e imagem de
26173505536 bytes: destino de teste de pelo menos 32 GB. Nao converte HDD existente,
nao expande F para toda a capacidade e nao e instalador USB. As imagens USB
recusam expor um SSD combinado reconhecido como HDD bruto, para evitar que um
formatador ocupe a area Linux. A compatibilidade Xbox original continua pendente.
