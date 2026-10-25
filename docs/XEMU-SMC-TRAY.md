# Bandeja comandada pela dashboard

Abertura/fechamento fisico validados pelo menu Xemu; nenhum
movimento pela dashboard. Na versao upstream 0.8.138, SMC_REG_TRAYEJECT (0x0c)
esta definido, porem nao tem tratamento de escrita. O menu chama qmp_eject e
xbox_smc_update_tray_state diretamente. Uma resposta FTP 200 a SITE TRAYOPEN
nao e prova de movimento; a dashboard pode aceitar a acao sem o SMC executa-la.

O patch pequeno em cartucho/build/patches/xemu-0.8.138-smc-tray.patch implementa
0 para abrir e 1 para fechar. Agenda a operacao no contexto AIO principal e
atualiza o estado SMC/IRQ depois do sucesso. E identificado como
**0.8.138-xrevive-smc1**, baseado exatamente no commit upstream
bf817de2b0354b7afe5e70efcd4f9c53bc7d4c67. Nao e um binario oficial inalterado.

Nao foi adotada a tentativa de observar apenas o barramento I2C externamente:
ela captura abrir, mas deixa o SMC indicando fechado, impedindo a dashboard de
mandar fechar. Tampouco se depende de uma string especifica de log do emulador.

tray-monitor.py traduz DEVICE_TRAY_MOVED em console-bandeja@open/close.service.
Comandos redundantes sao ignorados. A abertura QMP libera o backend de midia;
quando possivel, eject fisico preserva o processo Xemu e o estado da dashboard.
Se o leitor ainda estiver ocupado, existe fallback de parar, ejetar e religar.
O estado aberto tambem filtra eventos udev atrasados sem midia: eles nao podem
reiniciar Xemu e perder o estado SMC depois da ejeicao. Nova midia ainda reinicia.
Ao fechar com nova midia, o console pode reiniciar para inicia-la. Sessoes R/G
nao propagam a ejeicao da ISO virtual ao DVD fisico.

O build recompila a mesma versao, valida o commit e o patch, registra hash do
binario e do patch nos manifestos e inclui licencas/proveniencia em
/usr/share/doc/xrevive-xemu. O AppImage upstream continua validado por SHA como
origem dos recursos; o executavel e substituido pelo recompilado. SDL deve usar
o subprojeto fixado pelo proprio upstream, evitando mudar o comportamento
Wayland para o SDL antigo da distribuicao.

QA deve exigir abrir **e** fechar, eventos QMP nos dois sentidos, estado do
leitor externo e ausencia de reinicio desnecessario; apenas retorno FTP nao basta.
Teste com leitor virtual nao substitui nova confirmacao do mecanismo fisico.

Referencias: [SMC upstream](https://github.com/xemu-project/xemu/blob/v0.8.138/hw/xbox/smbus_xbox_smc.c)
e [menu upstream](https://github.com/xemu-project/xemu/blob/v0.8.138/ui/xemu.c).
