# Validação do atualizador Xemu — 24/10/2026

Projeto local console-appliance, sem Git inicializado. Todas as gravações de instalação, configuração de teste e falhas induzidas ocorreram em arquivos regulares de SSD/USB QEMU. Nenhum disco físico do host foi alvo. Não houve publicação no GitHub.

## Implementação e versões

Cliente e fluxo em [ATUALIZADOR-XEMU.md](ATUALIZADOR-XEMU.md). Xemu original imutável 0.8.138-xrevive-smc2; pacote testado 0.8.139-xrevive-smc2, commit upstream aa54c34cae1c09410d74c69a44210a9867fe2d16. SHA256 do binário 139: 9618befa89bce0e88713d759cbf36ec8004e17ec6becbcbe1b9c0a2d2bca55b4. Patches SMC/menu são os mesmos hashes da baseline, reaplicados com git apply --check à release 139.

60 testes de regressão passaram em `cartucho/cache/testes-atualizador-entrega.log`: assinatura alterada, pacote incompleto, caminhos proibidos, ABI incompatível, falta de espaço, oferta trocada, replay, interrupção antes da troca de estado, versão corrompida, recuperação e U/Y com prioridade de R. Compilação e testes upstream em `xemu-update-139-tested-build.log`; seis testes de VSH carryover e vinte de PTIMER passaram nos arquivos TAP de `cartucho/cache/xemu-update-0.8.139/`.

## Primeira integração

Candidato 20261024T113838Z-0e06910b5ce4 foi usado para integração, sem publicação em out porque os scripts de empacotamento e o transporte foram ajustados durante o build. A IMG de bancada anterior d32d6 permaneceu preservada. A implementação atual tem o build final 20261024T121602Z-730645d7124c, fontes 730645d7124c038fea5c25abe5cfcf930c4333bd2be8a3a8ebfbbbf957f51854; validação final/entrega registrada abaixo quando concluída.

A cópia QA muda somente a configuração do canal para HTTP local e omite xattrs SELinux na recompactação. Arquivos de código permanecem iguais ao candidato correspondente. A imagem de produção mantém HTTPS obrigatório e URL vazia; não existe hospedagem pública definida. Cópias QA recebem também o console de depuração do procedimento já existente. Servidor local atende apenas os pacotes e auxiliares de QA, sem firmware, chave privada ou SSDs.

Na VM, a própria interface instalou 104 pacotes/98.996 arquivos com controle, cancelamento e dupla confirmação sem escrita antecipada. Resultado `bancada/validacao-atualizador/install-status.json`. SSD UEFI sem USB iniciou e detectou uma oferta assinada durante o logo. `ssd-boot/notice-26.png` mostra o aviso; `update-notes.png` mostra notas e instruções A/Enter/B/Esc. O atalho U foi acionado no boot; os pulsos iniciais curtos do teste foram ampliados para representar uma tecla segurada.

Esc cancelou e manteve o emulador original sem estado ativo. Em nova abertura, A do controle confirmou download, verificação, ativação e retorno direto ao Xbox no mesmo boot. `update-health.txt` confirma versão 139, processo no caminho versionado e pending=null após 30 segundos/QMP. `update-emulator-139-proof.log` comprova SHA do executável, PID do QMP e stream ALSA RUNNING. Isso confirma inicialização e áudio ativo, não cada jogo ou qualidade sonora física.

`update-invariants-at-confirm.log` e `update-invariants-after.log` conferiram a SYSTEM inteira, MBR, executáveis C/E/F, Dashloader.ini, EEPROM, BIOS, MCPX e marcador de cache pessoal. SHA SYSTEM inteira ea2258a3f8bed5033e7b87fae4072d3ba4d2ecd7ff3b3732532f27fbfdfa60c8 permaneceu igual. Os arquivos Xbox verificados e o padrão de dashboard permaneceram iguais. Comparação feita imediatamente antes de A e após o boot atualizado; operações posteriores de manutenção têm escopo separado.

R abriu manutenção com a versão instalada. Reparar UEFI e escolher UnleashX passaram sem formatar ou mudar executáveis C/E/F, tabela ou 1.183 trainers; somente a configuração do carregador mudou na escolha. `update-maintenance-resumed.log` é o ensaio concluído; o primeiro verificador auxiliar precisava esperar a leitura terminar e foi corrigido. Não houve correção de código do produto em RAM.

Com UnleashX e 139: FTP de ida/volta de 262.144 bytes, SHA256 2312394bd99545d9de131c24efb781e765ac1aec243f2ed9347597a793a415e9; quatro comandos de bandeja produziram [true,false,true,false], PID 1301 preservado e evento atrasado de mídia tolerado. `update-regression-139-resumed.log` e `ssd-boot/regression-139.txt`. Para NAT da VM, é necessário parar o emulador antes de editar `/run/console/xemu.toml`, pois ele salva a configuração ao sair. Isso é configuração de bancada, não alteração do backend PCAP entregue para hardware físico.

Controle virtual abriu o menu Xemu com Start+digital para cima (`updated139-start-up.png`); Start+Back não abriu esse menu (`updated139-back-start.png`). Atalho Y no boot coberto pelos testes evdev; ensaio físico com controle fica pendente.

## Recuperação e entrega

O ensaio de falhas completo passou em `cartucho/cache/update-session-failure.log`: observação rearmada com duas cópias assinadas válidas da mesma 139, ambas conferidas por hash; Cage encerrado nas tentativas 1 e 2 antes da confirmação. A terceira partida selecionou automaticamente a revisão anterior 4a25b7f8..., pending=null e motivo de rollback registrado. Este teste cobre o ciclo systemd/limpeza dos processos versionados e evita confundir a tentativa interna Wayland→X11 com uma partida nova. Configuração de falha exclusiva da VM, sem modificação do código do produto. A reversão manual seguinte também passou em `update-manual-revert-final.log`: R → manutenção → reverter, active=null e emulador original novamente selecionado. O arquivo FTP e a tabela híbrida permaneceram válidos (`FTP_USER_FILE_AND_LAYOUT_PRESERVED`). O gate da IMG final e a entrega estão registrados abaixo. Pacotes de revisão local usados para falhas induzidas contêm a mesma compilação válida 139; não representam uma nova release upstream. A instrumentação inicial contava processos auxiliares e não era prova de duas partidas falhas; o ensaio válido deve contar reinícios completos da sessão.

## Limites

Canal público, execução do workflow no GitHub e bancada física da nova imagem não realizados. Imagens antigas não recebem o cliente automaticamente. A nova IMG continua sendo instalador de instalação limpa; não usar como migração preservando um HDD com jogos. O atualizador Xemu, depois de instalado, conserva as regiões Xbox; atualização integral do Linux/kernel/drivers e migração do cliente para instalações antigas são tarefas separadas.


## Gate da imagem final 730645d7124c

A cópia QA derivada da IMG final instalou a coleção inteira pelo controle em outro SSD virtual de 64 GiB, disco 089fcdae, 104 pacotes/98.996 arquivos verificados, XBMC4Gamers padrão. `bancada/validacao-atualizador-entrega/install-status.json` e capturas de instalação. Código do produto sem alterações em RAM; apenas configuração explícita do canal local e debug da cópia QA.

Boot SSD sem USB e oferta assinada passaram (`update-entrega-normal.log`). U abriu notas. Enter confirmou uma tentativa com pacote temporariamente indisponível: HTTP 404 exibido, nenhum estado de ativação criado e Esc voltou ao Xemu original (`update-entrega-download-error.log`, `ssd-boot/download-error.png`). O pacote foi restaurado e A do controle confirmou atualização real 138→139 (`update-entrega-apply.log`), com PID 1147, assinatura/hash, QMP e pending=null. `update-entrega-emulator.log` confirma binário 9618befa... e ALSA RUNNING.

`update-entrega-before.log` e `update-entrega-after.log` conferiram SYSTEM inteira SHA256 9eb4a0fa42212694b9f6fb1efb1bf174227b87167e8dc5092cd95fbe869a436b inalterada, além de MBR, arquivos C/E/F, padrão XBMC4Gamers, EEPROM, BIOS/MCPX e marcador de cache do usuário. Atualização não reinstalou dashboards nem formatou partições.

A automação local `cartucho/tools/xemu-update-candidate.py --build` foi executada: resolveu release/commit oficial e conferiu SHA do compilado em cache. Log `update-candidate-automation.log`. O workflow GitHub foi validado como YAML e usa ações oficiais fixadas por commit, porém não foi executado remotamente e não publica candidatos sem validação.


Boot adicional com o servidor do canal desligado manteve a versão 139 ativa, pending=null e console.service ativo: `update-entrega-offline.log` e `offline-boot/offline-persistence.txt`. Após desligar, verificação independente no host confirmou rodapé/tabela híbrida, padrão XBMC4Gamers e SYSTEM inteira inalterada (`integrity-after-shutdown.json`). VMs e servidor temporário encerrados.

Entrega local atual: **20261024T121602Z-730645d7124c**, única IMG `cartucho/out/console-xbox-installer.img`, **10.068.426.752 bytes**, SHA256 **9f9a9b1e4c6fdfbf6101b611377d01e1da7bbfc1d155199fe9cd68554f97700f**. Metadados, checksum, pacotes e release.json acompanham a IMG. Baseline d32d6 preservada em `cartucho/cache/baseline-antes-atualizador/`, com fontes e metadados.

O emulador embutido de recuperação continua 138. O pacote 139 está validado no canal local, não publicado na internet. A imagem distribuída tem URL vazia e HTTPS obrigatório; a configuração local das cópias de QA não está na entrega. A infraestrutura pública depende de definir o repositório/endereço e a promoção dos pacotes validados. Antes de distribuir, preservar a chave de assinatura fora do Git e da IMG.
