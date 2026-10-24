# Correção de inicialização e instalação online/local

Pedido de bancada de 24/10/2026: USB fica no logo e depois preto com cursor,
também no Dell G15. Primeiro reproduzir, depois migrar a mídia.

Critérios: interface utilizável por teclado OU controle, Rocky5 online direto
nas origens do catálogo aprovado, importação offline reconhecida e validada,
firmware do usuário, validação completa ANTES das duas confirmações de disco.
Nunca formatar ao escolher origem ou preparar downloads. Preservar boot híbrido,
SMC DVD, Start+Up, recuperação R, atualizador independente do Xemu e GTX750.

Área XREVIVE em exFAT no USB: X-Revive/firmware/xbox, X-Revive/pacotes,
X-Revive/cache e X-Revive/diagnosticos. Instalação armazena firmware uma vez.
Coleção e staging permanecem no USB; destino instalado guarda o manifesto
para manutenção, sem duplicar os arquivos de aplicativos na região Linux.

A primeira importação suportada deve ser explicitamente identificada. Não
prometer compatibilidade genérica com qualquer ISO/IMG do OGX/HeXEn/AID.
Arte BOOT permanece Plymouth; arte sem sufixo nas telas do instalador.
PNG BIOS é referência, Cerbios exige SVG vetorial sem raster/fontes.

Gates: reprodução da regressão, testes de segurança de extração/catálogo,
nenhuma escrita no destino antes de validação/dupla confirmação, erro de rede
recuperável, instalação online e offline em SSD regular de VM, boot só pelo
SSD, layout protegido e identidade final da IMG. Hardware físico precisa
novo ensaio do usuário; VM não o substitui.
