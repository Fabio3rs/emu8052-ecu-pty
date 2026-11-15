# Round-trip dos firmwares MA1.7 Fiat Tipo e Renault Clio

O perfil de SFRs, os vetores adicionais e o mapa semântico deste projeto
pertencem ao dump **Fiat Tipo** `FiatTipo_MA17_dump_27c256.bin` (27C256,
32 KiB). O dump **Renault Clio** `.ori` (64 KiB) serve como teste adicional
de desmontagem e remontagem MCS-51. As ECUs compartilham a família MA1.7,
mas não se deve transferir entre elas clock, portas, periféricos ou aliases
de funções sem conferir o firmware e o hardware de cada uma.

## Reproduzir

Na raiz do repositório, com `asm51/asm51` compilado e `disasm51` 1.0.2
instalado em `.venv`:

```sh
make -C asm51
python3 tools/roundtrip_8051.py FiatTipo_MA17_dump_27c256.bin
python3 tools/roundtrip_8051.py Renault_Clio_1.6__0261204510_1037355887_Bosch_1997_.ori
python3 -m unittest discover -s tests -p 'test_roundtrip_8051.py' -v
```

O comando grava `*.disasm51.asm` (saída original), `*.asm` (fonte editável),
`*.rebuilt.bin`, `sab80c517.mcu` e `report.json` em
`build/roundtrip/FiatTipo_MA17_dump_27c256/`. O dump de entrada é apenas lido.
Use `--output-dir` para outro destino; `--entry`, `--indirect` e
`--no-return-from` encaminham descobertas da análise de fluxo ao disassembler.
Não se usa `--force`: ele decodifica também tabelas e calibração como código.

O script executa o `disasm51` do `.venv` com `PYTHONPATH` apontando para
`disasm51/src`, para usar as correções versionadas sem modificar `.venv`.
Converte as diretivas ASEM-51 `$nomod51`, `$include` e `cseg` para as
declarações `DATA`/`BIT` aceitas por `asm51 -n`. Os bytes não emitidos em
lacunas `ORG` são `FF`, preenchidos pelo `asm51`; o último `FF` de uma ROM
é emitido explicitamente pelo `disasm51` para preservar o tamanho binário.
O script monta com `asm51 -f bin`, compara todos os offsets e registra hashes,
tamanhos, primeiro erro e grupos de divergência. Nenhum byte é corrigido após
a montagem.
O `asm51/parser.y` foi corrigido para aceitar `AJMP` e `ACALL` em qualquer
página válida de 2 KiB, inclusive quando o PC cruza uma fronteira de página.

## Processador e análise estática

O listing `FiatTipoIDAFullDump_27c256.asm` registra o mesmo SHA-256 do dump
e usa o processador **C517**. O manual `SAB80C517.txt` e `reg517.h` confirmam
`IEN1=B8h`, `T2CON=C8h`, `P4=E8h` e `WDTREL=86h`. São diferentes de nomes
atribuídos pelo mapa genérico 8052. `S0RELL=AAh` e `S0RELH=BAh` constam no
manual, mas faltam em `reg517.h`; o script os acrescenta às definições.
O firmware usa `PUSH 91h` em 0638h e `MOV B1h,#02h` em 086Ah.
Na variante **SAB80C517A**, esses SFRs são `XPAGE=91h` e `SYSCON=B1h`:
`SYSCON.XMAP0=0` habilita XRAM interna em F800h..FFFFh; uma escrita em `P2`
também carrega `XPAGE`. O perfil acrescenta os dois nomes de byte sem
confundi-los com endereços de bit, como `TXD=B1h`. O [datasheet oficial da
Infineon](https://www.infineon.com/assets/row/public/documents/10/57/infineon-d80517a-ds-en.pdf),
seção "Accesses to XRAM", documenta esse comportamento. Isso identifica
recursos da variante A usados pelo código, mas não substitui a identificação
física do chip na placa.

O SAB80C517A não tem ROM interna; a EPROM externa de 32 KiB é compatível com
esse arranjo. O SAB83C517A-5 tem ROM interna de 32 KiB, mas também pode
buscar código externo conforme o estado de EA.
O dump e o listing IDA não identificam, por si só, a marcação física do chip.
O mapa de periféricos usado aqui inclui os recursos de XRAM do C517A.

O perfil C517A Fiat é selecionado pelos cinco hashes únicos de `G`,
`A`/`A+`, `S88`, `S37` e `S36` registrados em
`docs/MA17_CALIBRATION_CATALOG.json`; o nome do arquivo não determina
o perfil. As seis imagens usam `XPAGE=91h` e `SYSCON=B1h` no boot e
possuem os mesmos endereços de vetor não apagados. A S36 muda o destino
do vetor em `53h`, preservando seu endereço. O Renault permanece em seu
perfil separado. O perfil Fiat adiciona os vetores conferidos com o
listing IDA, além do
reset. Os 12.469 inícios de instrução marcados pelo IDA ficam dentro das
regiões que o `disasm51` classifica como código. Isso é uma checagem cruzada,
não prova que toda classificação do IDA ou do `disasm51` esteja correta.
Saltos indiretos e rotinas que alteram o endereço de retorno podem requerer
`--indirect`, `--entry` ou `--no-return-from` em outros firmwares.

Com esse perfil, as seis imagens Fiat remontam 32.768 bytes sem divergências,
avisos de SFR desconhecido ou erros do assembler. A classificação estática
produz 23.420 bytes de código em G/S88, 23.615 em A/A+/S37 e 22.282
em S36; a diferença de S36 coincide com a mudança de destino do vetor
`53h` e requer análise de alcançabilidade própria. Esses números não
demonstram que todo código executável tenha sido descoberto.

## Resultado observado

| Campo | Valor |
| --- | ---: |
| original_size / rebuilt_size | 32768 / 32768 |
| mismatched_bytes | 0 |
| sha256_equal / roundtrip | true / PASS |
| code_bytes | 23420 |
| data_bytes | 4117 |
| unclassified_bytes | 5231 |

`unclassified_bytes` conta bytes omitidos em lacunas `ORG` (preenchimento
`FF`), não instruções comprovadas. Fidelidade binária e qualidade da análise
estática são medidas distintas. O assembly contém instruções e diretivas `DB`;
uma tabela apontada com `--indirect` usa `DW` big endian.

O arquivo chamado `tipo 1.6 alcool27c256.bin` neste checkout tem 60 bytes
de texto ASCII e hash `25f5db1babd2c91913ea0b60c0a27afd1f56a52c99f87fb3499242acfa50c310`.
Seu listing IDA declara um dump de 32 KiB com outro hash. Portanto ele não
entra nos testes como firmware. O Renault `.ori` tem 65.536 bytes e hash
`cf0c841d924bfc740ffbe825d7b87d9df22cfa7f3bfcfa4eafe7765e03795412`;
passou com 20.452 bytes de código, 14.015 de dados, 31.069 não classificados
e zero divergências. Seu listing IDA indica `AT89S8252`; isso não concorda
com a identificação da revisão MA1.7 informada para a ECU. O round-trip
confirma compatibilidade com a ISA MCS-51 usada, sem resolver a identidade
física dos periféricos. O clock Renault foi descrito como aparentemente
próximo do dobro do Fiat, mas a frequência exata e o mapa de portas ainda
carecem de confirmação; não são parâmetros do emulador Fiat. Três ROMs
sintéticas cobrem saltos, ordem de
operandos, páginas de 2 KiB, tabelas indiretas e preenchimento final.
