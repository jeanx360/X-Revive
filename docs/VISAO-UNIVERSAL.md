# Visão de longo prazo: consoles independentes por cartucho

Este documento descreve uma **visão futura**, não funcionalidades da beta pública. O projeto **X-Revive é dedicado somente ao Xbox Clássico**.

## A ideia

Uma carcaça de console ou PC compacto reúne placa-mãe, CPU, GPU, RAM, controles, conectores e, quando compatível, leitor óptico. A pessoa insere um **SSD/HDD intercambiável** e liga. Cada mídia inicia seu próprio sistema, já configurado para proporcionar a experiência daquela plataforma.

A inspiração surgiu da reconstrução de um Xbox Clássico danificado por enchente, utilizando a carcaça original e hardware de notebook/PC reaproveitado. A ideia cresceu para um conceito de máquina modular — mas **não depende de uma carcaça Xbox**: a comunidade poderá construir os próprios gabinetes e adaptações.

## Projetos separados, identidade própria

| Projeto | Plataforma | Estado |
| --- | --- | --- |
| **X-Revive** | Xbox Clássico | Beta pública e pesquisa de preservação de HDD |
| **PS2-Renew** | PlayStation 2 | Conceito futuro independente |
| **Wii/GC-Boot** | Wii e GameCube | Conceito futuro independente |
| Outros sistemas, inclusive Windows | Conforme cada SSD | Possibilidades futuras, sem compromisso de integração à mesma base |

Cada projeto terá licença, requisitos, releases, documentação e matriz de compatibilidade próprios. O X-Revive **não vira um menu multiemulador** por causa dessa visão.

## Princípios de experiência

1. **Download, gravação, preparação, uso:** o usuário não deveria precisar configurar manualmente dezenas de drivers ou abrir um emulador num desktop.
2. **Controle na mão:** navegação, manutenção e operação pelo controle quando o hardware suporta; teclado como alternativa.
3. **Boot dedicado:** ligar a máquina significa entrar na experiência do sistema escolhido.
4. **SSD como cartucho:** trocar a mídia com o equipamento **desligado**; cada mídia é um sistema independente.
5. **Aproveitar hardware comum:** perfis automáticos e drivers integrados para famílias compatíveis, **sem alegar suporte a todos os PCs**.
6. **Preservação responsável:** preferir backup e integridade verificável a modificar dados originais sem controle.

## Componentes potencialmente reutilizáveis

Detecção de hardware e perfis (HAL), seleção de driver, diagnósticos, interface de manutenção, atalhos de controle, ferramentas de build e procedimentos de testes poderão inspirar outros sistemas. Mas as diferenças entre Xbox, PlayStation, GameCube e Wii exigem arquiteturas específicas. **Um drive comum não lê automaticamente a mídia original de todos esses consoles.**

## Pesquisa exclusiva do Xbox

A visão de BIOS/firmware livre e tradução mais direta de execução `.xbe` pertence ao X-Revive, como objetivo de longo prazo. O projeto utiliza **Xemu atualmente**. A execução de programas x86 do Xbox em PCs genéricos exige reproduzir comportamento de kernel, GPU NV2A, memória, I/O, temporização e demais componentes. Otimizações e abordagens híbridas **não garantem por si só compatibilidade absoluta**.

Esta é uma direção para pesquisa, compartilhamento de conhecimento e colaboração — não uma promessa de cronograma nem de funcionalidades já concluídas.

[Voltar ao README](../README.md) · [Roadmap](ROADMAP-ATUAL.md) · [Arquitetura da beta](ARQUITETURA.md)
