# Instalação Rocky5 online e ISO local

Para baixar e usar sem compilar, siga [Baixar e instalar](BAIXAR-E-INSTALAR.md).
A beta.3 é a preparação pública da base de bancada descrita abaixo.

Na beta.3, forneça BIOS e MCPX; a **EEPROM é opcional**, com geração pelo Xemu
quando ausente e persistência no SSD. [Como funciona](EEPROM-OPCIONAL.md).
Inicialização, áudio, FTP, jogos/homebrew e bandeja física validados em bancada.
[Validação e histórico](BETA.md).

Esta etapa substitui o conteúdo offline embutido da mídia 730645d7124c.
A correção de inicialização e os gates da nova entrega estão descritos no
relatório de validação correspondente. Instalação continua limpa, com duas
confirmações: não é migração preservando jogos de um disco antigo.

## Preparar o pendrive

Gravar `cartucho/out/console-xbox-installer.img` no pendrive inteiro (16 GB ou
maior). A partição **XREVIVE**, em exFAT, fica acessível no Linux e Windows.
ExFAT aceita a ISO offline maior que 4 GiB. As pastas são criadas no primeiro boot; antes dele, também é possível copiar a pasta X-Revive completa organizada para a bancada. SYSTEM é o boot UEFI; não editar.
O tamanho lógico da IMG inclui a área vazia de arquivos do proprietário; isso
não significa que ela contenha 10 GiB de aplicativos ou firmware.

Copiar para `XREVIVE/X-Revive/firmware/xbox/`:

- `bios.bin` (256, 512 ou 1024 KiB);
- `mcpx_1.0.bin` (512 bytes);
- `eeprom.bin` (opcional, 256 bytes, para importar sua identidade).

O instalador base não fornece esses arquivos. Crie as pastas ou copie sua
árvore X-Revive organizada. Arquivos pessoais não são distribuídos pelo projeto.
Para a animação Xbox do Cerbios, forneça
opcionalmente `firmware/bootanims/Xbox/BootAnim.xbe` e `bootanim.ini`.
Na instalação online, ela é incorporada à coleção. Uma ISO normalizada pode conter
a animação do usuário; ela não é distribuída pelo projeto. BIOS e MCPX são importados para o SSD. A EEPROM é importada quando fornecida
ou gerada pelo Xemu no primeiro boot, mantendo a identidade no SSD.

## Online

Conectar cabo de rede com DHCP, iniciar USB UEFI e escolher Instalar →
Rocky5 — baixar pela internet. Não há dependência de cadastro ou navegador.
Os 107 arquivos de origem vêm das URLs HTTPS fixadas do catálogo Rocky5/GitHub,
com tamanho/SHA256 conferidos. As receitas preparam 104 pacotes Xbox.
O catálogo incluso é assinado e funciona sem serviço X-Revive hospedado.
`/etc/xrevive-packages.json` permite um futuro catálogo remoto assinado;
nenhuma URL pública própria foi inventada nesta entrega.

Os downloads e a normalização ficam dentro de `X-Revive/cache/rocky5-stage.ext4`,
no pendrive, com 8 GiB. A coleção inteira não é carregada na RAM. Uma nova
preparação reaproveita arquivos completos cujo hash confere; não há retomada
parcial de um arquivo interrompido. Erros aparecem na tela e permitem tentar
novamente. Depois da conferência, escolher disco e confirmar duas vezes.

## Offline

A ISO usada na bancada é particular e não está disponível no GitHub.
Prepare sua ISO normalizada a partir de arquivos cujo uso seja autorizado.
Copiar para `XREVIVE/X-Revive/pacotes/rocky5-offline.iso`, ou qualquer nome `.iso`.
Escolher Instalar → Usar ISO offline do pendrive → nome da ISO.
A ISO é montada somente para leitura; não é iniciada como console e não executa
scripts no Linux. O inventário inteiro e seus hashes são conferidos antes
que a tela permita selecionar e apagar um disco.

O formato inicial suportado é uma **ISO9660/Rock Ridge com árvore X-Revive
normalizada em `payload/` e `payload/manifest.json`**. Não é compatibilidade
universal com as ISOs originais de HeXEn, OGXbox, Rocky Extras Disc ou AID.
Essas exigiriam adaptadores de instalação próprios. A mídia recusa uma ISO
sem o manifesto esperado em vez de instalar silenciosamente outro conteúdo.

Em pendrive de 16 GB, para testar online e offline alternadamente, retire a ISO
pelo PC antes de preparar o online; para voltar ao offline, retire somente
`rocky5-stage.ext4` pelo PC e copie a ISO. Faça isso com o instalador desligado.
Os arquivos originais e o backup no computador permanecem preservados.

Para reproduzir a ISO a partir de uma coleção normalizada já verificada:

```sh
genisoimage -R -J -joliet-long -iso-level 3 -V XREVIVE_ROCKY5 \
  -o rocky5-offline.iso -graft-points payload=/caminho/da/colecao
```

## Segurança do disco e manutenção

Selecionar fonte, baixar ou conferir arquivos não modifica o SSD de destino.
Somente após a validação vêm modelo/série/capacidade e duas confirmações por
F10 ou LT+RT+Start, exigindo soltar entre elas. O USB de origem e discos em uso
são bloqueados. Identidades são revalidadas antes da escrita.

O SSD recebe o sistema, firmware, FATX nativo e os aplicativos; a área UTILS
guarda só o inventário da coleção para manutenção. Não duplica todos os apps
no lado Linux. O espaço restante compatível fica disponível ao Xbox.
XBMC4Gamers é o padrão. R / Start+Back no boot abre a manutenção; U / Y continua
reservado ao atualizador independente do Xemu, cujo canal público ainda está
pendente. Start+digital para cima abre o menu Xemu.

## Tela preta e logs

A interface Pygame usa SDL2/X11 via XWayland, com renderer de interface em
software. Xemu mantém sua própria SDL3 e o caminho gráfico anterior. A UI
apresenta o logo antes de esperar a enumeração de discos e a resposta do worker.
A sondagem Vulkan tem timeout de cinco segundos.

Logs persistentes do USB em `X-Revive/diagnosticos/<boot-id>/`: serviços,
hardware, discos, perfil, identidade do build e log da interface. Não copiam
BIOS/MCPX/EEPROM. São gravados após o início e no desligamento normal.

O Plymouth mantém o logo BOOT. Instalador e atualizador usam o logo sem sufixo.
`docs/branding/x-revive-bios-reference.png` preserva a arte BIOS enviada. O
editor Cerbios V3 exige SVG vetorial sem raster/fontes. O SVG fornecido depois
foi preparado e aplicado numa cópia particular da BIOS; veja
[logos e verificação](branding/README.md). O original permanece intacto.
