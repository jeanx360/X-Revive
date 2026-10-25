# Apresentação pública — validação em 25/10/2026

Site publicado: **https://jeanx360.github.io/X-Revive/**.
Integração: [PR #1](https://github.com/jeanx360/X-Revive/pull/1), commit
`a279efb8faf271efc47fc40f8cb8918fca70b247`.
[Publicação aprovada no GitHub Actions](https://github.com/jeanx360/X-Revive/actions/runs/40192225357).
[Testes da main aprovados](https://github.com/jeanx360/X-Revive/actions/runs/40192225345).

## Conteúdo e escopo

A apresentação mantém a identidade visual, a história de origem e a organização
PT/EN do pacote de apresentação. O índice e o roadmap vigentes estão em
[INDEX.md](INDEX.md) e [ROADMAP-ATUAL.md](ROADMAP-ATUAL.md).

X-Revive permanece dedicado ao Xbox Clássico. Preservação de HDD/FATX existente
é pesquisa separada da instalação limpa da beta.4. A experiência por controle e
a visão de SSDs como cartuchos orientam o projeto; outras plataformas pertencem
a iniciativas futuras independentes.

Código do instalador, emulador, testes, IMG beta.4, tags, licenças e relatórios
históricos foram preservados. A publicação inclui apenas apresentação,
documentação e o fluxo estático do GitHub Pages.

## Revisões aplicadas

- Texto na voz do projeto e resultados confirmados apresentados como validados.
- Pesquisa de preservação identificada sem afirmar um instalador não destrutivo disponível.
- Logo oficial incluído no site, sem depender de carregamento pelo GitHub Raw.
- Correção de transbordamento horizontal em telas estreitas.
- Rótulos do menu em inglês, fechamento por Escape e retorno do foco.
- Conteúdo legível com JavaScript desativado e respeito a movimento reduzido.
- GitHub Actions fixadas por commit, publicação de `site/` e credenciais de checkout não persistidas.

## Verificações realizadas

Chromium local e no endereço público, em **320, 375, 390, 768, 1024 e 1440 px**:
PT/EN, persistência do idioma após recarregar, menu móvel, navegação por âncoras,
teclado/Escape, carregamento do logo, ausência de rolagem horizontal da página,
movimento reduzido e conteúdo sem JavaScript. Nenhum erro JavaScript ou falha
de requisição foi registrado nesses ensaios.

HTML, CSS, JavaScript, favicon e logo foram baixados do site público com HTTP 200
e comparados por SHA256 aos arquivos revisados. Links internos da documentação,
âncoras e referência à IMG beta.4 conferidos. Sintaxe JavaScript e diff aprovados.

Evidências locais: `cartucho/cache/site-publicacao-20261025/`, incluindo relatórios
do navegador, capturas, hashes dos arquivos de origem e da publicação.
