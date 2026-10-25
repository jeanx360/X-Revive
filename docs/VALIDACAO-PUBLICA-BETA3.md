# Validação da beta.3 — EEPROM opcional

## Base de hardware

Inicialização, áudio, rede/FTP, instalação de jogos e homebrew e bandeja física
validados em bancada. Mantemos o kernel 6.12.113+deb13-amd64, NVIDIA 550.163.01-2
e Xemu 0.8.138-xrevive-smc2. Os ensaios abaixo cobrem a mudança de EEPROM.

## Integridade e testes

- 72 testes locais aprovados.
- Cópia pública limpa: 72 testes descobertos, 71 aprovados e um UIX opcional
  dispensado por depender de pacote externo.
- Fingerprint da cópia limpa idêntico ao das entradas do build.
- Unidade de persistência verificada com systemd-analyze; avisos existentes
  referem-se aos serviços mascarados de Plymouth/getty.
- IMG.xz descompactada integralmente e conferida por tamanho e SHA256.
- Pacotes Debian idênticos à beta.2: 461 pacotes e as mesmas 331 versões-fonte.
- Sem BIOS/MCPX/EEPROM, executáveis Xbox ou jogos na produção. Os arquivos
  privados foram fornecidos somente a uma cópia QA por 9p somente leitura.

## Instalação sem EEPROM

A entrada QA continha somente BIOS e MCPX, além da ISO normalizada usada nos
ensaios. A interface aceitou a ausência da EEPROM, preparou os 104 pacotes e
permitiu selecionar o SSD virtual após conferir a coleção. A instalação pela
GUI respeitou as duas confirmações e a soltura dos botões.

98.996 arquivos foram gravados e conferidos por leitura de volta, com
`verified=true`. Antes do primeiro boot, a partição CONSOLE do SSD foi lida
externamente: BIOS/MCPX presentes e EEPROM ausente. Nenhum disco físico do host
foi usado como destino dos testes.

## Regressões protegidas

Os testes verificam EEPROM opcional ausente, importação quando fornecida,
recusa de arquivo inválido/link simbólico, gravação inicial atômica, preservação
de identidade existente e espera por uma criação ainda incompleta.
A persistência inicial usa um lock compartilhado com o salvamento de desligamento,
para serializar as janelas de escrita na partição CONSOLE.

Evidências locais: `cartucho/cache/public-release-beta3/` e
`bancada/validacao-publica-beta3/`. Discos e arquivos privados não são publicados.

## Geração nativa e identidade após reboot

O primeiro boot do SSD sem USB iniciou o Xemu com áudio ALSA RUNNING. A EEPROM
foi gerada pelo próprio Xemu e apareceu na partição CONSOLE antes de qualquer
desligamento. A seção de segurança foi decifrada para conferir a identidade;
somente hashes foram registrados, sem expor serial, MAC ou chave HDD.

Um reboot real foi confirmado pela mudança de boot_id. No segundo boot, a
identidade persistida foi idêntica à do primeiro. Marcadores locais:
`XEMU_GENERATION_AND_IMMEDIATE_PERSISTENCE_PASS` e
`EEPROM_IDENTITY_PRESERVED_ACROSS_REBOOT_PASS`.
