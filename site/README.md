# Site do X-Revive

Site estático em `site/`, sem dependências de Node ou etapa de compilação. Funciona em GitHub Pages sob `/X-Revive/`.

- `index.html`: conteúdo em português, estrutura e links de download.
- `styles.css`: design responsivo com identidade verde/preta.
- `main.js`: navegação móvel, troca PT/EN e animações com redução de movimento.
- `assets/favicon.svg`: ícone simplificado exclusivo do site.
- `.nojekyll`: dispensa processamento por Jekyll.

A imagem de marca em `assets/logo.png` é uma cópia do arquivo oficial do repositório (`cartucho/overlay/usr/share/console/logo.png`), incluída na publicação para não depender do carregamento externo do logo. O desenho CSS do console é conceitual, não uma captura do produto.

## Teste local

```bash
python3 -m http.server 8080 --directory site
# http://localhost:8080
```

## Publicação

A workflow `.github/workflows/pages.yml` publica o conteúdo de `site/` quando há push para `main`. Habilite **Settings → Pages → Build and deployment → Source: GitHub Actions** se ainda não estiver configurado.

## Como manter atualizado

A URL de download aponta intencionalmente para a beta pública verificada, `v0.1.0-beta.5-live.6`. Antes de mudar a versão ou prometer outro fluxo, revise `docs/BETA.md`, as releases e a matriz de testes. Não exponha o modo de preservação como recurso público antes de uma release que efetivamente o inclua.

Ao atualizar a identidade visual, copie o logo oficial para `site/assets/logo.png`
e confira a imagem em desktop e mobile antes de publicar.
