# Fontes e licenças das imagens públicas

As betas.2 e .3 usam as mesmas versões dos pacotes Debian e do Xemu.
Cada release disponibiliza esses fontes e a tag correspondente ao código X-Revive.

Os avisos estão na própria IMG em `/usr/share/doc/` e
`/usr/share/common-licenses/`; a release oferece também `licencas-e-avisos.zip`.
O código original do X-Revive usa GPL-3.0-or-later. Xemu/QEMU, Linux, drivers,
firmware de hardware e demais componentes conservam suas próprias licenças.
[Escopo e terceiros](../THIRD_PARTY_NOTICES.md).

## Arquivos para recompilar

Esses arquivos não são necessários para instalar o sistema:

- `sources-debian-01.tar.zst` e `sources-debian-02.tar.zst`: pacotes-fonte exatos,
  `.dsc`, originais e patches Debian de 331 versões, cobrindo os 461 pacotes
  instalados e dependências Built-Using / Static-Built-Using.
- `sources.json`: URLs, nomes, tamanhos e SHA256, obtidos dos índices deb-src
  autenticados do Debian e conferidos em cada download.
- `coverage.json`: cobertura da coleta; nenhuma versão solicitada ausente.
- `sources-xemu-0.8.138-xrevive.tar.zst`: árvore usada para compilar Xemu,
  incluindo dependências/submódulos, patches e identidade do compilador.
- `xone-0.5.8.tar.gz` e `pyfatx-0.0.8.tar.gz`: fontes das dependências externas
  adicionais. O pyfatx sdist inclui o código C do libfatx.
- O `Source code` da tag beta.2 contém nossos scripts, receitas, patches e testes.

Os dois arquivos Debian são arquivos tar independentes, não pedaços de um único
stream. Extraia ambos na mesma pasta. Exemplo Linux:

```sh
mkdir fontes
cd fontes
tar --zstd -xf ../sources-debian-01.tar.zst
tar --zstd -xf ../sources-debian-02.tar.zst
```

`debian/` contém os pacotes. `dpkg-source -x` extrai um `.dsc` junto dos arquivos
correspondentes; a construção segue as instruções do pacote Debian. Nosso
coletor está em `cartucho/tools/collect-release-sources.py`; ele exige índices
deb-src autenticados e não troca silenciosamente uma versão por outra.

A árvore Xemu registra o commit
`bf817de2b0354b7afe5e70efcd4f9c53bc7d4c67`, com mudanças SMC/menu. O binário continua
`0.8.138-xrevive-smc2`; compilar uma release upstream sem os patches não reproduz
seu comportamento. [Receita da imagem](COMUNIDADE-BUILD.md).

A IMG pública remove as bibliotecas antigas não usadas da AppImage e utiliza
as bibliotecas Debian já carregadas pelo binário, sem mudar o conjunto resolvido
por ldd. Não contém firmware Xbox, coleção Rocky5, firmware do Xbox Wireless
Adapter nem a chave privada MOK gerada no build. O driver NVIDIA e os firmwares
Debian não livres não são apresentados como código GPL; seus avisos são preservados.

O build ainda não é hermético: esta publicação fornece as versões e fontes da
entrega efetiva, mas não promete igualdade de timestamps ou assinatura DKMS numa
recompilação. A chave MOK privada da bancada não é necessária nem distribuída.
