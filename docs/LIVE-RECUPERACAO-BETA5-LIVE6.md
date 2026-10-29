# LIVE e recuperação de boot — beta.5-live.6

Pré-release beta.5-live.6 para testes. [Download](BAIXAR-E-INSTALAR.md) e
[resultados com limites](VALIDACAO-LIVE6-RECUPERACAO.md).

## O que mudou

O assistente continua respondendo enquanto prepara a sessão. O logo pulsa e uma
faixa luminosa percorre a barra. A tela mostra etapa, tempo e se o serviço está
respondendo; a animação, sozinha, não significa que o trabalho avançou.

- **F1 no teclado / X no controle:** mostrar ou ocultar as últimas etapas.
- **Esc / B:** cancelar a preparação quando essa etapa permite. Aguarde a
  liberação da sessão antes de retirar o disco.
- Gravações de instalação ou reparo do boot precisam terminar; não oferecem
  cancelamento no meio da escrita.
- Etapas de configuração têm limites de tempo. Se uma delas falhar, a mensagem
  permite voltar e os detalhes ajudam a localizar a espera.

O pendrive guarda um registro de etapas em
`XREVIVE/X-Revive/diagnosticos/operacoes/<identificador>.jsonl`. Esse registro
contém tempo, mensagem da etapa e percentual; não inclui senha Wi-Fi nem
argumentos das operações. Se o pendrive estiver cheio ou não permitir gravar,
o registro pode ficar incompleto. Em um relato, informe também a build da
imagem, a opção escolhida e em qual etapa parou.

## Iniciar o HDD sem instalar

1. Grave a IMG no pendrive e copie seus arquivos para a partição **XREVIVE**.
   BIOS e MCPX: `X-Revive/firmware/xbox/`; EEPROM opcional. Firmware do dongle:
   `X-Revive/firmware/dongle/`, quando necessário.
2. Abra **LIVE → Protegido → Iniciar dashboard do HDD — sem mídia**.
3. Escolha o HDD Xbox, interno ou USB. FATX nativo e disco híbrido X-Revive são
   reconhecidos; a presença de UEFI não impede o LIVE.
4. O Xbox usa as dashboards e jogos existentes. As alterações da sessão vão
   para RAM, com limite de 512 MiB, e se perdem ao desligar. O HDD permanece
   somente leitura. Esse modo não serve para instalar jogos permanentemente.

Para iniciar por uma mídia, escolha **Usar mídia do pendrive** e selecione o
arquivo da lista. Coloque ISO/XISO em `X-Revive/pacotes/` ou suas subpastas, sem
nome obrigatório. HeXEn e OGXbox XDVDFS continuam sendo lidos diretamente.
A coleção Rocky5 ISO9660 pode ser apresentada como um DVD virtual somente
leitura: a mídia original fica intacta e não exige uma segunda cópia integral
de aproximadamente 4,5 GiB. O driver NBD necessário já integra esta imagem.

**LIVE → Instalação / manutenção** é o modo que autoriza a mídia Xbox a escrever
no HDD escolhido, depois das duas confirmações. Use-o somente quando quiser
que as ações executadas dentro da mídia alterem aquele disco. Outros discos e
o pendrive de origem permanecem excluídos. O HDD virtual temporário continua
disponível no modo protegido, sem selecionar disco físico.

O download online do Rocky5 ainda precisa de espaço para seus arquivos e
cache; a ausência de cópia integral adicional se refere à adaptação offline.

## Preparar ou reparar boot automático

Use **Preparar boot de HDD Xbox existente**, escolha o HDD e depois
**Preparar / reparar boot automático do X-Revive**. A manutenção também
reconhece um HDD nativo/híbrido sem exigir assinatura standalone íntegra.

Se existir boot, o assistente avisa que será substituído/atualizado, mesmo que
esteja íntegro. Confirme o disco nas duas telas segurando **LT + RT + Start**
ou **F10**, soltando entre as confirmações. O reparo a partir do pendrive
atualiza a região SYSTEM, recria o carregador UEFI e os registros de boot,
preservando os volumes FATX, dashboards, jogos, configurações e EEPROM.
Vídeo, áudio e rede são detectados novamente ao iniciar neste computador.

Uma assinatura de rodapé danificada pode ser recuperada pelo mapa preservado
na partição de sistema. Se todo o mapa foi perdido ou existem partições de
PC com dados na área proposta, é necessário examiná-las antes de gravar.
Cabeçalhos GPT antigos fora dos volumes Xbox não devem sobrepor o novo mapa;
assinaturas dentro do FATX não são apagadas pelo reparo.

**Espaço livre dentro de F: não é uma partição de boot.** Se F ocupa o disco
inteiro, criar o sistema exige uma migração que reduza/reorganize esse volume.
Esta candidata não executa essa migração automaticamente. Ela explica a
necessidade e permite continuar em LIVE. O teste de reserva de cerca de
3,19 GiB no HDD de 1 TB foi realizado em uma cópia; não foi aplicado ao disco
físico nessa rodada de validação. Não apague/formate F para contornar a
mensagem.

## Próximo teste de bancada

No Dell G15, repetir HDD USB protegido sem mídia, HeXEn/OGXbox/Rocky5 offline,
cancelamento durante preparação, detalhes e recuperação de boot em um disco
com área de sistema já reservada. Conferir controle sem fio desde o assistente,
áudio e FTP real pela rede usada. A simulação em VM e a leitura do HDD físico
não substituem o teste de GPU, Wi-Fi e USB no Dell.

Veja a [validação desta candidata](VALIDACAO-LIVE6-RECUPERACAO.md) e o
[guia de gravação](BAIXAR-E-INSTALAR.md). O pendrive continua com XREVIVE exFAT
pronta para copiar os arquivos, sem um ciclo obrigatório de primeiro boot e
retorno ao PC. A IMG bruta continua maior que o download compactado.
