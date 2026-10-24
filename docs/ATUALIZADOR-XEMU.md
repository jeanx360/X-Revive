# Atualizador Xemu do X-Revive

Especificação autorizada em 24/10/2026: detectar novas versões, mostrar “Nova atualização disponível” sob o logo, abrir notas segurando U no teclado ou Y no controle, confirmar por Enter/A, baixar e seguir para o Xbox. Esc/B continua sem instalar. R/Start+Back mantém prioridade para manutenção. Sem internet o boot continua; uma oferta assinada já consultada pode ser exibida offline.

O canal distribui **compilações X-Revive**, preservando DVD/SMC e Start+digital para cima. Publicar uma tag upstream não autoriza instalar o binário oficial, que perderia essas correções. Uma nova versão precisa ser compilada e validada antes de entrar no canal. Estado de upstream e disponibilidade de pacote são coisas distintas.

## Plano

1. Cliente assinado, cache de consulta, atalhos, notas e progresso.
2. Instalação atômica de Xemu na CACHE, verificação de ABI/proveniência e recuperação do binário anterior.
3. Ferramentas de empacotamento e consulta ao GitHub, com compilação fixada por commit e patches.
4. Testes de falhas e integração em VM. Preservar a IMG d32d6 de bancada até a nova entrega passar.
5. Configurar hospedagem de produção quando o proprietário/repositório for definido. Não existe endpoint público presumido.

## Limites

A atualização escreve somente `/var/cache/console/updates`. Não formata, não abre o prefixo Xbox e não toca jogos, saves, EEPROM, dashboards, SYSTEM ou firmware. O Xemu 0.8.138 da imagem é recuperação imutável. Uma versão instalada começa em observação: precisa permanecer executando por 30 segundos com QMP respondendo. Falhas repetidas ou interrupção antes dessa confirmação retornam à versão anterior. Isso verifica inicialização, não compatibilidade de cada jogo.

O protocolo usa assinatura Ed25519 sobre JSON canônico e SHA256 do pacote. Chave privada fica fora do repositório e da imagem. O pacote aceita somente cinco arquivos regulares, sem scripts, links ou caminhos arbitrários. Transporte de produção exige HTTPS, inclusive redirecionamentos; HTTP é exclusivamente configuração explícita de bancada.

A primeira instalação do suporte exige uma nova imagem do sistema. As imagens anteriores não ganham um atualizador apenas pela publicação de uma release. Esta funcionalidade atualiza Xemu; não é ainda atualização integral do kernel, drivers ou coleção Rocky5.

## Operação do canal

`python3 cartucho/tools/xemu-update-candidate.py --build` consulta a release estável oficial, resolve a tag até o commit, aplica os patches e compila em container Debian com cache separado por versão. Pode ser agendado no mantenedor/CI; não precisa de BIOS e não publica automaticamente candidatos sem validação. Se os patches deixarem de aplicar, o build falha e o canal estável permanece na versão anterior.

Depois dos testes, `cartucho/build/xemu-update-package.py package --help` descreve os argumentos para produzir o pacote e `latest.json` assinado. `--base-url` deve ser o endereço HTTPS real dos pacotes publicados. A chave privada de desenvolvimento está em `~/.local/share/xrevive/updates/signing-key.pem`, com permissão 0600; nunca adicioná-la ao Git, imagem, servidor de pacotes ou log. Fazer backup privado antes de distribuir uma imagem com essa chave pública. Uma infraestrutura pública exige definir responsável, repositório, assinatura e promoção das releases.

A URL do manifesto pode ser definida no build em `/etc/xrevive-updates.json` ou como dado `updates_url=https://.../latest.json` no `config/ports.conf` da partição CONSOLE. Trocar a URL não muda a chave confiável. Na bancada a configuração explícita `allow_http=true` permite o servidor local; a imagem entregue mantém `false`. Nenhum endereço fictício está embutido.

No boot do SSD, a consulta acontece em paralelo à janela de oito segundos dos atalhos e termina em até sete segundos. A oferta assinada é armazenada para o próximo boot offline. U/Y abre a tela mesmo sem oferta, mostrando o motivo. O Xemu só é baixado depois de A/Enter; sem conexão o usuário pode seguir por B/Esc usando a versão instalada.

Após baixar, o sistema confere assinatura, tamanho, checksum, tipo ELF e bibliotecas; ativa a versão por uma troca atômica do estado e continua o boot. Mantém a versão anterior e remove apenas versões antigas da pasta privada do atualizador depois da confirmação de saúde. Não apaga cache de shaders nem dados pessoais para abrir espaço: falta de espaço é informada e mantém a versão atual.

Se houver regressão de um jogo, iniciar o SSD segurando R/Start+Back, abrir Manutenção → Reverter atualização do Xemu e reiniciar. O pacote revertido não é oferecido novamente; uma correção deve ser publicada com nova sequência e identidade. A versão efetiva selecionada está em `/run/xrevive-update/choice.json`; o manifesto do sistema continua identificando o Xemu original embarcado.

O workflow `.github/workflows/xemu-candidate.yml` fica disponível para execução manual. O agendamento fica desligado até validar o build no GitHub e medir seu custo. Ele executa os testes, resolve a release upstream e compila com os patches, gerando somente um artefato candidato sem assinatura. Permissões de leitura, sem chave privada, firmware ou publicação de releases. Ações oficiais fixadas por commit. A promoção ao canal estável permanece após a validação em bancada; não confundir um workflow preparado com uma execução já concluída no GitHub. Referências: [checkout oficial](https://github.com/actions/checkout), [upload-artifact oficial](https://github.com/actions/upload-artifact).

## Entrega validada

Build 20261024T121602Z-730645d7124c publicado localmente como única IMG em out. Cliente e atualização 138→139 validados em VM, com assinatura, cancelamento, erro de download, preservação de dados, reversão e boot com canal indisponível. [Relatório e checksum](VALIDACAO-ATUALIZADOR-XEMU.md). O canal de produção e a migração de instalações antigas continuam pendentes.
