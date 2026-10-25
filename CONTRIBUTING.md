# Contribuir com o X-Revive

Comece por [BETA](docs/BETA.md), [roadmap vigente](docs/ROADMAP-ATUAL.md) e
[build](docs/COMUNIDADE-BUILD.md). Abra uma issue antes de propor mudanças grandes
no layout de disco, instalador ou protocolo de atualização.

Para uma correção: crie uma branch, descreva o comportamento final, adicione
testes quando protegem comportamento relevante e execute:

```sh
python3 -m unittest discover -s tests -v
```

Use Python 3.11 ou posterior, OpenSSL e ferramentas de shell Linux. Os testes
normais não exigem firmware, jogos, imagens ou discos físicos. O teste UIX com
catálogo real é opcional e fica skipped sem o pacote local.

Ensaios destrutivos devem usar **arquivos regulares de disco descartáveis** em VM.
Scripts de bancada incluem nomes locais e fixtures históricas; leia antes de
executar. Não conecte discos pessoais a uma VM de instalação. Distinga resultado
de teste, relato físico e hipótese nas issues/PRs.

Não envie firmware, EEPROM, chaves privadas, senhas, jogos, dashboards binárias,
ISOs ou logs sem revisão. Código original segue GPL-3.0-or-later; patches Xemu
seguem GPL-2.0-or-later. Preserve avisos/autoria de terceiros. Só contribua com
conteúdo que possa licenciar.

Atualize changelog e guias relevantes. Tags beta: `vMAJOR.MINOR.PATCH-beta.N`.
Testes não promovem um candidato ao canal público nem validam todos os jogos.

A documentação pública usa a voz do projeto: descreva funcionalidades, resultados
e limites diretamente. Validações confirmadas em bancada entram como validadas,
sem narrar conversas ou tratar o autor do projeto em terceira pessoa. Preserve a
rastreabilidade técnica nos relatórios e não estenda um resultado a hardware ou
cenários que não foram testados.

A direção vigente está em [INDEX](docs/INDEX.md) e [ROADMAP-ATUAL](docs/ROADMAP-ATUAL.md):
X-Revive dedicado ao Xbox Clássico, preservação de HDD/FATX como pesquisa separada
da instalação limpa publicada, experiência por controle e SSDs intercambiáveis.
Outros consoles pertencem a projetos futuros independentes.
