# Disco unico: prototipo experimental

> Registro da etapa anterior. A direção atual é o [instalador próprio, estágio 2](ESTAGIO2-INSTALADOR.md), com uma única IMG de instalação.
Esta variante testa o SSD como cartucho completo: UEFI inicia Linux/Xemu e o
mesmo disco contem as particoes FATX em seus offsets Xbox nativos. Nao depende
de um arquivo HDD virtual em ext4. As imagens USB universal e NVIDIA continuam
operacionais e independentes deste modo.

**Nao e um instalador para converter HDD existente.** A imagem e preparada para
um disco de teste vazio, com capacidade minima de 32 GB. Gravar uma imagem bruta
substitui os dados do destino. Nesta rodada nenhum dispositivo fisico e gravado,
formatado ou reparticionado automaticamente. O incidente historico NTFS/FATX
nao demonstra espaco livre: assinaturas sobrepostas podem coexistir com dados
corrompidos ou perder dados na proxima escrita.

## Tres variantes

| Arquivo em cartucho/out | Uso |
| --- | --- |
| console-xbox-universal.img | USB; drivers Mesa, hardware moderno suportado |
| console-xbox-nvidia.img | USB; NVIDIA proprietario 550, bancada GTX 750 |
| console-xbox-standalone.img | SSD/HDD de teste vazio; experimental; base NVIDIA com fallback Mesa |

Um build gera as tres com a mesma identidade, kernel, utilitarios e emulador.
A terceira reutiliza a base NVIDIA para incluir a bancada antiga; seu rootfs
declara a base nvidia para a HAL, e os manifestos CONSOLE e layout identificam
standalone/experimental. Isso nao representa suporte a toda GPU existente.

## Layout e protecao

| Regiao | Posicao / tamanho padrao |
| --- | --- |
| Xbox nativo | 0 a 16 GiB; C/E/X/Y/Z e F com limites nesta area |
| SYSTEM (ESP FAT32) | depois do prefixo Xbox; 2048 MiB |
| CONSOLE (FAT32) | depois de SYSTEM; 640 MiB |
| CACHE (ext4) | depois de CONSOLE; 1024 MiB |
| UTILS (ext4) | depois de CACHE; 4864 MiB |
| Rodape e reserva | ultimo MiB; manifesto duplicado com CRC |

O padrao oferece **16 GiB totais ao Xbox**, incluindo particoes retail; F tem
o restante dessa area. Um SSD maior nao e expandido automaticamente. O gerador
aceita --guest-gib para preparar outro tamanho em arquivo, antes da instalacao.
O prototipo MBR limita o tamanho total a menos de 2 TiB.

O setor zero contem PARTINFO nativo (14 entradas de 32 bytes a partir do byte48)
e apenas a quarta entrada MBR, tipo EF, apontando para SYSTEM. Campos MBR
utilizados ficam nas duas ultimas entradas Xbox **inativas** e apos a tabela.
Entradas Xbox ativas 1 a 12 sao preservadas; uso das entradas 13/14 e recusado.
Nao se usa GPT: suas estruturas atingiriam a tabela/area Xbox.

Somente o parametro de boot xrevive.standalone=1 ativa este modo. O runtime
confere PARTUUID, geometria da ESP, manifesto e rodape, e valida limites de todas
as entradas Xbox ativas. Mapeia CONSOLE/CACHE/UTILS por offsets. O Xbox recebe
um loop de offset zero com **sizelimit**, nunca o disco completo. O kernel
recusa escritas alem do prefixo Xbox, mesmo se um formatador guest tentar usa-las.
Manifesto privado de desligamento fica em /run/xrevive-standalone, root 0700.

Depois de fechar Xemu, o desligamento pode restaurar somente os campos MBR/UEFI
se o guest reescreveu PARTINFO. Antes, valida novamente rodape e todas as entradas.
Se PARTINFO desapareceu ou alguma entrada invade o sistema, recusa o reparo;
nao adivinha limites nem migra particoes. Queda de energia durante reformatacao
pode exigir recuperacao: nao equivale a um esquema transacional completo.

## Primeiro boot e portabilidade

O prefixo padrao vem sem FATX: HeXEn inicia para a pessoa formatar/instalar pela
interface Xbox. R continua forcando HeXEn, G inicia OGXbox. Uma imagem semeada
com HDD virtual e usada exclusivamente na QA, nao substitui o artefato vazio.

Os offsets nativos e PARTINFO permitem investigar uso do SSD em Xbox original
com BIOS compativel com essa tabela. Cerbios 3.1 e a BIOS alvo dos testes virtuais.
**Compatibilidade fisica ainda nao comprovada.** Modchip por si so nao garante
que qualquer BIOS/formatador respeite o limite de F. Fora do X-Revive, o loop
Linux nao existe: um formatador no Xbox original pode ocupar o final do disco
e destruir o sistema. Nao usar formatacao de disco inteiro ali antes da validacao.

Ainda falta transformar isto num instalador: reservar espaco em HDD ja cheio,
migrar dados com copia recuperavel, detectar capacidade, recuperar MBR pelo USB
sem ambiguidade e validar BIOS/hardware reais. Nao sera criada uma particao de
boot automaticamente no desligamento de um HDD antigo sem essa preparacao.

As imagens USB recusam entregar um SSD standalone reconhecido como HDD bruto
ao emulador: sem esse bloqueio, um formatador iniciado pelo USB poderia usar
tambem a area Linux. A deteccao verifica o setor combinado e reconhece a perda
do MBR quando PARTINFO ainda aponta para a ESP SYSTEM. Isto nao e recuperacao
de qualquer corrupcao. O instalador/reparo standalone via USB e uma proxima
etapa; nesta entrega, iniciar o SSD pela propria UEFI para manter o limite.

## Reproducao

O build normal gera as tres variantes. Para um arquivo experimental separado:

```sh
python3 cartucho/build/standalone-image.py \
  cartucho/out/console-xbox-nvidia.img /caminho/novo-standalone.img --guest-gib 16
```

O destino deve ser novo; O_EXCL recusa sobrescrita e symlinks. Fonte e seed
devem ser arquivos regulares; dispositivos fisicos nao sao aceitos. Use ambiente
Debian com grub-efi-amd64-bin, mtools e fdisk. --seed-hdd e apenas para QA.

Evidencias e resultados da entrega sao registrados em ROADMAP-2026-10-23.md.
Referencias primarias: [PARTINFO do XBPartitioner](https://github.com/opcow/XBpartitioner/blob/main/partition.h)
e [MBR/ESP na especificacao UEFI](https://uefi.org/specs/UEFI/2.10/05_GUID_Partition_Table_Format.html).
