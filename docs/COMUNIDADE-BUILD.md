# Build e publicação para a comunidade

Esta beta publica fontes. Leia [terceiros e distribuição](../THIRD_PARTY_NOTICES.md)
antes de redistribuir uma imagem compilada. Nenhum firmware pessoal, ISO, pacote
de aplicativos ou chave privada faz parte do Git.

## Build local

Host Linux x86-64 com Podman, Python 3.11+, Git e espaço livre para sistema,
compilador, caches e imagens (reserve pelo menos 40 GiB; não é um limite de pico
medido). A imagem lógica atual tem cerca de 13,2 GiB. Rede é necessária para
obter pacotes Debian, Xemu e dependências. O container não instala drivers no host.

```sh
git clone https://github.com/jeanx360/X-Revive.git
cd X-Revive
PUBLISH_RELEASE=0 cartucho/build/build.sh xbox
```

O build **não exige BIOS/MCPX/EEPROM** e não embute coleção Rocky5. Não copie
firmware nem executáveis Xbox para os fontes. O segundo argumento histórico do
build não é necessário; os firmwares entram depois pela partição XREVIVE.

`PUBLISH_RELEASE=0` preserva o candidato em `cartucho/cache/pair.*`, sem substituir
`out`. Depois de QA, o publicador local de `cartucho/build/release.py` confere a
identidade e os arquivos do conjunto. Rodar o build sem essa variável publica
localmente em `cartucho/out/`; isso **não envia nada ao GitHub**. Mantenha somente
uma IMG atual em out, com baselines guardadas separadamente no cache.

O conjunto inclui IMG, SHA256, JSON de versões, lista de pacotes e release.json.
A compressão `.img.zst`, quando produzida, contém a mesma imagem; descompacte
antes de gravar com uma ferramenta que não suporte esse formato diretamente.
Grave no pendrive inteiro, nunca num disco com dados a preservar.

## Dependências e reprodução

`versions.env`, `xemu-smc.sh`, os patches e `rocky5.lock.json` registram versões,
commits, URLs e hashes. O catálogo Rocky5 é consumido durante a instalação, não
baixado para dentro da IMG. O Xemu modificado é compilado do commit fixado;
um binário oficial genérico não preserva o patch da bandeja e do menu.

APT ainda acompanha os repositórios Debian sem snapshot completo. O wheel
pyfatx 0.0.8 precisa de hash fixado e timestamps ainda variam. Não se promete
build bit a bit idêntico. Consulte os metadados gerados para a versão efetiva.
Um cache contendo firmware opcional do dongle pode incorporá-lo ao build;
revise seu conteúdo antes de qualquer distribuição.

O fingerprint da entrega df48 foi calculado sobre os arquivos locais da bancada,
incluindo assets históricos privados depois excluídos do sistema. O clone público
não inclui esses arquivos e produzirá outro fingerprint; não recrie executáveis
privados apenas para igualar o hash. A tag Git identifica os fontes publicados.

## Online e offline

Firmware é fornecido pelo proprietário no pendrive, conforme o
[guia de instalação](INSTALADOR-ONLINE.md). O instalador verifica firmware e coleção
antes de permitir selecionar/apagar o SSD. Online usa catálogo assinado com 107
origens e prepara 104 pacotes. Para offline, forneça ISO9660/Rock Ridge com
`payload/manifest.json` e árvore normalizada. A ISO particular da bancada não é
publicada. HeXEn/OGXbox/Extras Disc originais exigiriam outros importadores.

Para preparar uma coleção local com arquivos cujo uso seja autorizado:

```sh
python3 cartucho/build/rocky5.py
python3 cartucho/build/rocky5-payload.py --help
```

Confira as opções da receita e use um diretório de saída novo. Após normalizar,
a ISO pode ser criada com o comando documentado no guia. Isso baixa conteúdo de
terceiros e não lhe concede uma licença de redistribuição.

## Testes

```sh
python3 -m unittest discover -s tests -v
```

Não exige discos físicos, firmware pessoal ou cache de aplicativos. O teste UIX
com pacote real é opcional e fica skipped num clone limpo. A fixture de animação
é sintética. Os testes de disco criam somente arquivos regulares temporários.
Os workflows não recebem chave privada nem publicam atualizações automaticamente.

Scripts `bancada/` são ferramentas de ensaios específicos; alguns têm caminhos
locais, dependem de QEMU/KVM/OVMF e de fixtures privadas. Leia antes de executar,
adapte só para arquivos regulares descartáveis e não conecte discos do host.
Capturas/logs mencionados nos relatórios são provas locais, não arquivos do Git.

## Manutenção das releases

Correções entram em branch/PR, testes e changelog. Uma tag beta identifica fontes;
a prerelease descreve o que realmente foi validado. Binários só são anexados após
preparar licenças/fontes correspondentes. Não envie `cartucho/cache`, `out`, discos,
firmwares, ISOs ou chaves. A chave pública pode estar no Git; a privada nunca.

O workflow Xemu é manual nesta primeira beta. Ele resolve upstream, compila com
patches e gera candidato sem assinatura. Promoção exige QA e assinatura local.
O canal público de atualizações e o catálogo remoto ainda estão desativados.
