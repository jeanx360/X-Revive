# Estágio 2: instalação X-Revive com Rocky5

Etapa atual: [instalação online Rocky5 e ISO local](INSTALADOR-ONLINE.md). As referências à mídia offline abaixo descrevem a baseline anterior.

Decisão autorizada pelo usuário; IA Memory:
`decisions/xrevive-estagio2-instalador-rocky5.md`,
`01a16b8d-bf8a-7f40-aa52-2ae555da309e`.

## Especificação aceita

- Uma IMG para pendrive, com perfis de vídeo internos e instalação offline.
- Instalação limpa no disco escolhido explicitamente, nunca em disco automático.
- Mostrar modelo, série, capacidade e espaço Xbox antes de qualquer escrita.
- Bloquear mídia de origem, discos montados, em uso e setores incompatíveis.
- Dupla confirmação: LT+RT+Start ou equivalente de teclado; exigir liberação.
- Capacidade variável, boot UEFI e FATX nativo com áreas Linux protegidas.
- Instalar a coleção Rocky5 pertinente completa, sem seleção de pacotes.
- XBMC4Gamers padrão; demais dashboards coexistem, troca altera carregador.
- Teclado ou controle independentes em todas as telas, inclusive confirmação.
- R e acesso equivalente por controle abrem manutenção própria.
- Reparo e troca de dashboard não formatam; reinstalação é ação separada.
- Menu Xemu: Start+digital para cima. Encerramento: logo e `Desligando...`.
- Manter correção DVD, rede/FTP, áudio e animação Xbox.
- Não incluir HeXEn/OGXbox na nova distribuição após comprovar substituição.

## Plano

1. Preservar imagens/fontes da entrega f613cf12 e registrar a decisão. Feito.
2. Obter catálogo Rocky5 completo, fixar origens/hashes e validar pacotes.
3. Implementar instalação FATX completa e seletor do carregador em arquivo.
4. Implementar layout variável e proteções de destino/boot e recuperação.
5. Interface própria para teclado/joystick, serviço privilegiado limitado.
6. Integrar mídia única e perfis de vídeo, atalhos e desligamento.
7. Validar instalação limpa, reinício sem USB, FTP, espaço, DVD e manutenção.
8. Publicar artefato local somente após as verificações; atualizar memória.

## Critérios de aceitação

Testar destinos incorretos sem escrita, retirada/troca do disco durante seleção,
cancelamento das duas confirmações, soltura obrigatória entre confirmações,
catálogo corrompido/sem espaço, todos os arquivos FATX instalados e legíveis,
diretórios com mais de 512 entradas (trainers), boot com todas as dashboards,
capacidade maior que 16 GiB, integridade da área UEFI, boot por SSD isolado,
controle e teclado, R manutenção e persistência depois de desligar.

Discos físicos do host não fazem parte da execução automatizada. Compatibilidade
em Xbox original requer teste físico próprio; sucesso em Xemu não a comprova.
Não implementar migração de disco com jogos implicitamente. Não escolher uma
versão de desenvolvimento só por ser mais recente que uma estável.

## Progresso

Etapas 1 a 8 implementadas, com entrega local única d32d6 e baselines preservadas.
Resultados e recortes de cada ensaio em [VALIDACAO-ESTAGIO2.md](VALIDACAO-ESTAGIO2.md).
O software foi validado em arquivos/VM; bancada física da nova entrega é o
próximo marco. A compatibilidade em Xbox original continua experimental.
A instalação atual é limpa; atualização preservando jogos não foi implementada.
