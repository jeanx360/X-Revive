# Terceiros e distribuição

A beta.2 distribui uma IMG pública, fontes, patches e avisos de licença.
Não distribui a coleção Rocky5, firmware Xbox, jogos, dumps pessoais ou executáveis Xbox.
A licença do projeto não concede direitos sobre esses materiais.

| Componente | Origem / licença | Tratamento |
|---|---|---|
| Xemu / QEMU | [Xemu](https://github.com/xemu-project/xemu), GPL-2.0-or-later e licenças dos arquivos/dependências upstream | Receitas e dois patches publicados; binários não incluídos neste repositório |
| Debian, Linux, Mesa, SDL, Cage, Python e demais pacotes | [Debian](https://www.debian.org/legal/licenses/); licenças próprias por pacote/arquivo | Obtidos no build; preservar avisos e disponibilizar fontes correspondentes aplicáveis antes de distribuir uma IMG |
| NVIDIA 550 | [Pacote Debian](https://packages.debian.org/trixie/nvidia-driver) e termos NVIDIA | Driver proprietário obtido no build; não é relicenciado como GPL |
| xone | [dlundqvist/xone](https://github.com/dlundqvist/xone), GPL-2.0 | Fonte obtida na versão fixada pelo build; firmware do adaptador é separado |
| pyfatx | [XboxDev/fatx](https://github.com/XboxDev/fatx), GPL-2.0 (LICENSE.txt; conferir versão obtida) | Dependência de build/runtime; não há cópia do wheel no Git |
| Rocky5 / XBMC4Gamers e coleção de aplicativos | [Xbox Softmodding Tool](https://github.com/Rocky5/Xbox-Softmodding-Tool), [XBMC4Gamers](https://github.com/Rocky5/XBMC4Gamers) e origens no catálogo | O Git contém URLs, hashes e receitas. A GPL de um projeto não cobre automaticamente todos os pacotes, dashboards, trainers ou skins da coleção |
| Cerbios / BootAnim / MCPX / EEPROM / BIOS | Fornecidos pelo usuário; [arquivos requeridos pelo Xemu](https://xemu.app/docs/required-files/) | Não incluídos no Git nem no instalador base; personalizar uma BIOS não cria autorização de redistribuição |
| Logos X-Revive | Artes fornecidas pelo mantenedor | Exibição no projeto; escopo separado da licença do código, conforme NOTICE.md |

O catálogo online contém material com termos distintos, inclusive Microsoft
Dashboard. Um link de download não elimina direitos ou restrições do material
baixado. O X-Revive não afirma que o acesso público a um pacote autoriza seu uso
ou redistribuição. As assinaturas conferem autenticidade e integridade, não uma
licença de distribuição.

## Entrega binária beta.2

A IMG inclui os pacotes Debian e seus avisos em `/usr/share/doc/` e
`/usr/share/common-licenses/`. A release disponibiliza o inventário de versões,
os pacotes-fonte exatos (incluindo Built-Using), os fontes do Xemu com dependências
e os scripts/patches de construção. Arquivos `sources-*` são para estudar ou
recompilar; não são necessários para instalar.

Foram excluídos o firmware opcional do dongle Xbox Wireless, a chave privada MOK
gerada por DKMS e as bibliotecas antigas da AppImage que não eram usadas pelo
Xemu compilado. O binário Xemu e os drivers da bancada permanecem os mesmos.
A licença NVIDIA incluída no pacote permite distribuição para sistemas com
licença aberta, sob suas condições; as bibliotecas proprietárias não foram
modificadas. O aviso completo acompanha o pacote, sem relicenciamento como GPL.

O cliente de atualização estar pronto não significa que exista um canal público
ou uma oferta de atualização publicada. A IMG beta.1 de bancada continua sendo
um artefato local; a beta.2 identifica a preparação pública.
