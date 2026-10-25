# Candidata beta.3 — não publicada

Os primeiros ensaios passaram para instalação sem EEPROM, geração nativa e
persistência após reboot. Um reboot adicional detectou um ciclo no systemd:
`console-eeprom.path → console-prepare.service → basic.target → paths.target`.
A resolução do ciclo podia excluir o job de preparação e deixar somente o logo.

A candidata foi retida. A tag permanece como histórico; a correção e a nova
validação completa estão no [relatório da beta.4](VALIDACAO-PUBLICA-BETA4.md).
