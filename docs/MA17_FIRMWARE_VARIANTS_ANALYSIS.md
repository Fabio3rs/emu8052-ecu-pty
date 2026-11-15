# Fiat Tipo MA1.7: comparação inicial das EPROMs

Este relatório usa offsets da imagem 27C256 e bytes originais. Os nomes dos
arquivos são rótulos de procedência, não identificação comprovada de revisão,
combustível, pressão ou função das tabelas. A análise funcional permanece em
andamento. O relatório completo por intervalo e o mapa visual são gerados por:

**Estado dos ensaios:** o modelo ADC do C517A foi corrigido para ler
`ADDATL` em vez de reutilizar o byte de partida. Números de execução
produzidos antes dessa correção são históricos; a grade G/S88 atualizada
está em `build/ma17-analysis/variants/experiments_adc517a/`. Cada seção
assinala quando seus números foram repetidos. Comparações de bytes ROM e
testes isolados de opcodes permanecem válidos independentemente do ADC.
Uma nova repetição da grade está em
`build/ma17-analysis/variants/experiments_adc10_current/`; cada
`execution.json` agora registra também o SHA-256 do executável do
emulador para permitir identificar exatamente a versão usada.
Os 18 casos dessa repetição mantiveram os mesmos valores de entrada,
ticks observados e medianas P5.0/P5.1/CC3 da grade corrigida
`experiments_adc517a/`; a discrepância abaixo é com a captura anterior
ao conserto do ADC.

```sh
python3 tools/compare_ma17_variants.py
python3 tools/run_ma17_variant_experiments.py
python3 -m unittest discover -s tests -p 'test_compare_ma17_variants.py' -v
```

Saídas: `build/ma17-analysis/variants/comparisons.json`, `differences.svg`,
`matrix_differences.svg`, `matrix_deltas.json`, `candidate_tables.json`,
`pointer_regions.json`, `pointer_catalog_coverage.json`,
`calibration_catalog_expanded.json` e
`diagnostic_tables.json`. No mapa das seis matrizes, cada célula tem tooltip
com offset, byte original, byte da variante e diferença aritmética **bruta
u8**; vermelho é aumento, azul é redução e branco é igualdade. A cor não
representa unidade física nem prova de interpretação assinada.
Os intervalos JSON são
`[start, end_exclusive)`; os
contextos mostram até oito bytes antes e depois das extremidades. A matriz
compara bytes no **mesmo offset**. Um número alto não distingue, sozinho,
recalibração de deslocamento de código ou mudança de revisão.

## Síntese verificável da campanha

| Medida | Resultado | Evidência reproduzível |
| --- | ---: | --- |
| Imagens 27C256 | 6 arquivos, 5 hashes únicos | `comparisons.json`; `A` e `A+` são idênticas |
| Comparações binárias | 15 pares | `python3 tools/compare_ma17_variants.py` |
| Entradas curadas | 137 | `docs/MA17_CALIBRATION_CATALOG.json` |
| Alvos do diretório `7002h..70E9h` | 116 | `pointer_regions.json`; 104 diretos, 8 contidos, 4 não classificados |
| Intervalos não apontados ainda sem função | 3 | `unclassified_nonpointer_intervals` no catálogo |
| Offsets divergentes em `6E00h..7FFFh` | 2399, todos cobertos | `test_catalog_covers_changed_data_pages` |
| Round-trip das seis ROMs | 32768 bytes e zero divergências em cada uma | `python3 -m unittest tests.test_roundtrip_8051` |

As 137 entradas incluem matrizes, curvas, limites, constantes e regiões
sem função demonstrada; **não** são 137 mapas físicos identificados.
Na ROM G, o assembly modular classifica 23.420/32.768 bytes (71,47%) como
instruções, 4.120 (12,57%) como dados explícitos e 5.228 (15,95%) como
`FFh` implícitos. Essa é uma medida de cobertura estrutural do round-trip;
não mede a fração da lógica ou das funções físicas compreendida. O relatório
`build/ma17-analysis/modular/report.json` registra ainda 79 bytes em duas
regiões `DB` ambíguas, que não devem ser promovidas a código só por serem
decodificáveis como instruções.
Há consumidores indicados em 135 entradas e campos de evidência dinâmica
em 114, mas parte dos ensaios antigos antecede a correção ADC descrita
acima. Os papéis digitais de, por exemplo, `7310h`, `7ED9h` e `7581h`
possuem testes causais. A função elétrica de CC3/P1.3 e P5.0/P5.1,
as unidades físicas das matrizes e a execução completa da família A
permanecem abertas. Nenhuma calibração recebeu aqui validação física
direta em ECU real.

### Revalidação da campanha em 15/11/2026

`python3 tools/compare_ma17_variants.py` regenerou os relatórios em
`build/ma17-analysis/variants/`: seis imagens, 15 pares, 137 entradas
expandidas com seis versões e hashes por entrada, e cobertura do diretório
em 104 alvos diretos, oito subvistas e quatro alvos provisórios. Os hashes
atuais das seis ROMs coincidem com `rom_sha256` do catálogo; nem as ROMs
nem os `.inc` apresentam modificações no `git status`.
`python3 -m unittest tests.test_roundtrip_8051` passou 25 testes;
`python3 -m unittest tests.test_compare_ma17_variants.CompareVariantsTests`
passou 52; `ctest --test-dir build --output-on-failure` passou 162.
O ensaio completo da família A em um perfil de hardware validado e a
identificação elétrica de CC3/P1.3 e P5.0/P5.1 seguem abertos.

## Inventário

Todas as seis imagens abaixo têm 32768 bytes, opcode `LJMP` em `0x0000` e
destino de reset `0x0850`. A identidade de periféricos C517A é fundamentada
para a imagem gasolina em [ROUNDTRIP_8051.md](ROUNDTRIP_8051.md); para cada
outra imagem, o mesmo vetor não basta para provar identidade de hardware.

| ID | Imagem | SHA-256 | Soma de bytes mod 65536 |
| --- | --- | --- | --- |
| G | `FiatTipo_MA17_dump_27c256.bin` | `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f` | `8817` |
| A | `tipo 1.6 alcool27c256.bin` | `29403d0044c4d841da46edcce257184894b1eb1185257bddc4a277a32c1ae8e1` | `37A5` |
| A+ | `tipo 1.6 alcool27c256+1.5bar.bin` | `29403d0044c4d841da46edcce257184894b1eb1185257bddc4a277a32c1ae8e1` | `37A5` |
| S88 | `tipo 1.6 alcool27c256 SUN 8817.bin` | `bfa59928ca41695458063835dc1a05a489b9deb5755bb1d7740c22874fdcbe28` | `8817` |
| S37 | `tipo 1.6 alcool27c256 SUN 37a5.bin` | `91ffb89d8293e7058144df474d1e53fa1236875b9dff047784c9cc77306ab6e2` | `37A5` |
| S36 | `tipo 1.6 alcool27c256 SUN 36fd.bin` | `fd6288a06b0618fe8d4fd0561ca8f1feb75bfda1d4cb092041ff64053ffef8a8` | `36FD` |

As cinco variantes vêm de `firmwares_modificados_ma17_tipo/`; `tipo.zip`
contém esses mesmos nomes e três hexdumps textuais (`normal.txt`,
`1.5bar.txt`, `sum36fd.txt`). Após expandir as linhas repetidas marcadas com
`*`, esses hexdumps são idênticos, respectivamente, a `A`, `A+` e `S36`.
Datas internas do ZIP não são prova de origem.
O arquivo homônimo na raiz tem 60 bytes ASCII e não foi usado como ROM.
A coincidência entre `SUN` e a soma de 16 bits é verificável; isso não
comprova que a ECU calcule ou valide essa soma.
O catálogo estruturado em `docs/MA17_CALIBRATION_CATALOG.json` contém
137 entradas nesta revisão; elas não equivalem a 137 funções físicas
confirmadas nem esgotam os 116 alvos do diretório de ponteiros.
Uma auditoria dos campos `confidence.physical_function` encontra 126 entradas
marcadas `unknown`, três `not_applicable` (protocolo ou diretório) e oito
classificações provisórias: quatro `probable RPM axis`, duas `unverified`
e duas `scanner_hypothesis`. Nenhuma função de atuador está confirmada
fisicamente apenas por esta classificação.
O campo genérico `dynamic_evidence` aparece em 113 entradas; as outras 23
também registram evidências em campos mais específicos, muitas vezes de
execução isolada. Esses números descrevem a documentação, não confirmam
funções físicas nem acesso natural a todas as curvas.
O arquivo `pointer_catalog_coverage.json` cruza cada slot desse diretório
com as entradas curadas: 104 slots apontam diretamente para uma entrada,
8 são subvistas contidas em uma entrada maior e 4 permanecem sem
classificação curada. Esses 4 intervalos provisórios são byte a byte
iguais nas seis ROMs; isso não prova que sejam inativos ou que tenham
função conhecida. As cinco subvistas/curvas alteradas que pareciam
ausentes numa comparação só pelo campo `pointer_slot` estão cobertas
por entradas maiores (`74EEh`, `7581h`, `7662h`, `7743h`).

`python3 tools/compare_ma17_variants.py` também gera
`build/ma17-analysis/variants/provisional_pointer_catalog.json` com uma
entrada para cada um desses 4 slots. O registro contém os seis hashes,
endereços, bytes brutos e estatísticas simples, além de marcar dimensões,
consumidor e função como desconhecidos. O fim do intervalo é somente o
próximo alvo do diretório: pode incluir bytes sem uso ou parte de outra
estrutura. A regressão
`test_provisional_pointer_catalog_preserves_all_unclassified_bytes`
confere slots, ponteiros, hashes e bytes contra as ROMs originais. Assim,
o relatório permite escolher alvos para análise sem apresentar os 13
intervalos como tabelas de calibração já demonstradas.

O slot `706Ah→7958h` contém `47 03 04 04 EE FF 9A 24` nas seis
ROMs: cabeçalho de RPM, três incrementos e três valores interpolados.
G/S88 chamam `52F2h` em `15B2h`; A/A+/S37/S36 têm o carregamento do
mesmo ponteiro em `15FDh` e chamam o auxiliar relocado `53B5h`.
No G original emulado, fornecer `40h` apenas ao `MOVC 532Fh/795Dh`
(byte bruto `FFh`) mudou `R2=FFh→40h`, o valor limitado em `15C3h`
de `05h→01h` e a primeira gravação de RAM `59h` de `05h→01h`.
Os dois ensaios de 6 milhões de ticks mantiveram as medianas modeladas
de P5.0/P5.1/CC3 em `1861/1861/4373` ticks. A inspeção dos pulsos
individuais mostrou, porém, que as três primeiras larguras baixas de
`P1.3/CC3` passaram de `5381/5380/5380` para `4373/4372/4372` ticks.
Fornecer os valores nativos de RAM `59h/5Ah` apenas às leituras em
`1D5Ch/1D5Eh` não restaurou as larguras. As leituras anteriores
`MOV R7,59h`/`MOV R5,5Ah` em `1C99h/1C9Bh` alimentam a multiplicação
em `1C9Dh`; fornecer `05h/00h` nesse ponto restaurou exatamente as
três larguras nativas. Fornecer cada byte isoladamente deslocou uma
parte diferente do par `R3:R2` publicado em `1ED3h`. Essa é uma
mediação digital demonstrada no perfil G emulado; `P1.3` é o pino
modelado do processador, sem ligação elétrica confirmada ao bico da ECU.
Capturas em `build/ma17-analysis/variants/curve7958_{dual,early}_*_g/`.
Com ADC fixo, a doação alterou também os primeiros pulsos a 750 e
1.500 RPM; a 3.000 RPM, os três primeiros passaram de
`5381/5381/5381` para `4373/4373/4373` ticks. O resgate em
`1C99h/1C9Bh` restaurou os três valores nativos a 3.000 RPM, enquanto
o mesmo fornecimento no controle nativo foi neutro para esses pulsos.
As medianas de janelas longas podem ocultar esse efeito de partida.
Capturas em `build/ma17-analysis/variants/curve7958_rpm*_g/`.
Com RPM fixo em 1.000, o contraste também persistiu ao mudar apenas
`ADC1=130→40`: os primeiros pulsos nativos `6309/6308/6308` passaram a
`5301/5300/5300` ticks no braço doador; o resgate em 1C99h/1C9Bh
restaurou as larguras e o controle nativo foi neutro. Em ensaios
separados, `ADC3=40` produziu `6405/6404/6404` contra
`4765/4764/4764`, e `ADC6=180` produziu `6901/6900/6900` contra
`3973/3972/3972`. Restaurar `RAM59h:5Ah` nas leituras de
`1C99h/1C9Bh` para os valores nativos estabilizados (`06:00` e
`06:7C`, respectivamente) recuperou exatamente os três primeiros
pulsos em ambos os casos. Os controles nativos conservaram essas
larguras, embora a intervenção constante também alcance a primeira
leitura durante o boot, quando os valores armazenados ainda diferem.
Os números são ticks do harness Fiat, não tempos elétricos medidos na ECU.

Dois slots adjacentes também saíram do conjunto provisório. `7060h→78FDh`
contém cinco linhas idênticas `80 80 81 82`; `7062h→7911h` contém
20 zeros. O código G usa índices de linha de `7054h→7824h` (RAM `70h`)
e coluna de `7056h→782Bh` (RAM `47h`), formando matrizes 5×4.
Em três boots G com ROM inalterada, doar `40h` apenas à leitura `MOVC`
do primeiro byte de `78FDh` mudou a RAM superior `B1h` de `00h` para
`D0h`, sem mudar RAM `58h`; doar `40h` apenas à leitura de `7911h`
mudou RAM `58h` de `00h` para `30h`, mantendo `B1h=00h`.
São destinos internos distintos. O valor `30h` decorre da interpolação,
não de uma cópia direta do byte `40h`, e a função física segue aberta.
O leitor de RAM superior `B1h` em `1893h` foi alcançado em 16 passagens
de um boot G a 1.000 RPM: `B1h=00h` saltou de `1894h` diretamente para
`189Ah`; com a célula `78FDh` fornecida como `40h`, `B1h=D0h` alcançou
`1897h` antes de voltar a `189Ah` porque `2Ch.6=0` no estado observado.
O byte `58h=30h` da outra intervenção ficou disponível, mas as cópias
`18FDh/1906h→RAM[3Ch]` não foram alcançadas nos três braços, nem em
suas extensões a 6 milhões de ticks. As medianas modeladas de P5.0,
P5.1 e CC3 ficaram iguais nessas extensões; nenhuma função elétrica
foi estabelecida por esses ensaios.

O slot `705Eh→78F9h` contém quatro valores idênticos nas seis ROMs:
`00 13 2A 3A`. Em G, o interpolador recebe segmento/fração de RPM do
slot `7056h→782Bh`. O resultado participa da subtração `RAM[6Fh]-R2`
em `3D25h`, se `2Eh.6` e `28h.1` estiverem limpos, e `3D28h` grava o
carry em `RAM[25h].3`. Em boot G a 1.000 RPM, fornecer `80h` apenas ao
retorno de `MOVC 532Fh/78F9h` (byte original `00h`) mudou o primeiro
`R2` de `00h` para `80h` e o byte `25h` de `17h` para `1Fh` após a
comparação. Num estado posterior com `28h.1=1`, a mesma intervenção
mudou `R2`, mas a comparação foi ignorada. `25h.3` é RAM interna;
nenhum pino ou atuador foi identificado por esse resultado.

O slot `7068h→7952h` contém `63 02 5E 2F 10 22` nas seis ROMs.
O cabeçalho seleciona RAM baixa `63h`, os dois bytes seguintes são
incrementos e `7956h/7957h` são valores interpolados. No código G,
`1277h` lê a curva e `1282h` compara o resultado com `RAM[47h]`,
derivada de RPM. Em 33 passagens de um boot G a 1.000 RPM,
fornecer `80h` apenas ao `MOVC 532Fh/7956h` em vez do byte original
`10h` mudou a comparação de `A=10h<28h` para `A=80h≥28h` e o ramo
de `12DEh` para `128Ah`. A ROM e seu hash permaneceram iguais.
`RAM[63h]` é um valor digital processado de ADC3 nesse perfil;
a associação ao sensor e ao pino físico não está comprovada.

O slot `70D6h→79C4h` saiu do conjunto provisório: `47 04` seleciona
RAM baixa `47h` e quatro segmentos; `79C6h..79C9h` são incrementos e
`79CAh..79CDh` são valores interpolados, iguais nas seis ROMs. No G
emulado, `35C2h` gravou `F8:E1h`; fornecer `40h` apenas ao retorno de
`MOVC 532Fh/79CAh` (byte original `83h`) mudou a primeira gravação
`03h→C0h`. O `MOVX` em `35D1h` lê o mesmo endereço para ajustar `R2`.
`F8:E1h` é XRAM endereçada pela página `P2`, não um pino. O efeito
posterior e a função física seguem sem identificação.

O slot `7006h→741Ch` saiu do conjunto provisório após a inspeção do
consumidor G em `15D5h` e do homólogo A em `161Ch`: ambos usam o
interpolador de bytes adjacentes (`5329h` na G, `53ECh` na A), com
resultado em `R2` antes de uma multiplicação. Os dez bytes
`741Ch..7425h` valem `40h` nas seis ROMs. Em opcodes isolados das seis,
índices `00h` e `08h` leem somente esse bloco e devolvem `R2=40h`;
o índice sintético `09h` lê também `7426h`, início da próxima curva.
O teste `ConstantCurve741cInterpolatesAdjacentBytesAtBoundary` fixa
essa fronteira. `JB 2Fh.0` pula a leitura quando o bit vale 1; ela
ocorre com `2Fh.0=0`. A faixa natural de `R5` nesse ramo, o efeito
posterior do produto e qualquer ligação física continuam pendentes.
Em três boots originais G de 2,4 milhões de ticks com roda 60-2 imediata
e sem K-Line, a curva foi lida naturalmente. A 1.000 RPM com
`ADC0/6=40/95` ou `180/247`, `ADC3=80`, houve 21 pares por caso,
com primeiros índices `00h` e `03h`. A 4.000 RPM com `ADC0/6=180/247`
e `ADC3=4`, houve 11 pares, todos de índice `00h`. Os endereços ficaram
em `741Ch..7420h`; nenhum chegou ao bloco seguinte nesses cenários.
As capturas estão em `build/ma17-analysis/variants/constant_741c_*/`;
o teste `test_constant_741c_curve_natural_indices_stay_in_bounds_in_two_states`
reexecuta dois deles. A faixa global do índice permanece desconhecida.

O slot `7016h→74E4h` contém dez bytes idênticos nas seis ROMs:
`73 5A 40 40 40 40 40 40 40 40`. O código G/S88 em `12B2h`
carrega o ponteiro e chama `5238h`; A/S37 chamam `52FBh`. Em
`12BDh`, o índice do `MOVC` é `R5 + R6.7`, sem interpolação, e
`12BEh` grava o byte em `RAM[49h]`. O teste dos opcodes originais
confirmou índices preparados `0/1/8/9` e mostrou que o índice
sintético 10 lê a primeira posição da tabela seguinte (`74EEh`),
`00h` em G/S88/S37/S36 e `10h` em A/A+. A faixa natural ainda não
foi estabelecida. Na G a 1.000 RPM e `ADC0/2/3/6=120/100/4/95`,
`74E4h=73h` foi lido oito vezes em 120.000 ticks. Fornecer `40h`
somente ao retorno do `MOVC` fez `RAM[49h]` receber `40h` e mudou
seis resultados `R2` em `233Bh`, com `RAM[4Dh]=19h`, de `2Fh` para
`25h`. Em 2,4 milhões de ticks a diferença interna persistiu, mas
as medianas de pulsos modelados P5.0/P5.1 e CC3 não mudaram.
Isso não identifica o pino ou atuador físico desse cálculo. Testes:
`SixRom74e4DirectIndexUsesR6HighBitAndBoundaryByte` e
`test_74e4_first_cell_reaches_ram49_and_scaled_r2_in_g`;
capturas: `build/ma17-analysis/variants/74e4_ram49_*/`.

O alvo terminal `70C4h→7F8Dh` é uma exceção de cobertura parcial: a entrada
curada termina em `7F96h`, enquanto o intervalo provisório segue até
`8000h` e inclui bytes de outras regiões. A auditoria registra esse
sufixo `7F96h..7FFFh` explicitamente; não o atribui à curva terminal.
O conjunto de entradas do catálogo cobre o intervalo completo, incluindo
a região sem função classificada; a entrada apontada por `70C4h`, sozinha,
cobre apenas `7F8Dh..7F95h`.
Nesse sufixo, A/A+, S88 e S37/S36 diferem de G em 6/6, 74 e 87/87
bytes, respectivamente. A curva `7F96h..7F9Ch` e os bytes de boot
`7FF6h..7FFFh` têm consumidores identificados; `7F9Dh..7FF5h`
permanece sem função estabelecida.
Regressão: `test_pointer_catalog_coverage_tracks_subviews_and_unknowns`.

O início do boot dá uma pista limitada sobre a revisão A. G e A
configuram os mesmos valores em `WDTREL`, `P1`–`P5`, `SP`, `PSW` e
`SYSCON` em `0850h..0870h`. Entre `0850h` e `09FFh`, os 23 bytes
divergentes são somente operandos de 12 instruções `LCALL`; os cinco
destinos distintos mudam em `+C3h` e seus primeiros 32 bytes coincidem
nos endereços homólogos. Em `0000h..00FFh`, só `003Eh:003Fh` difere:
o `LJMP` do serviço de Timer 2 passa de `58BCh` para `597Fh`, também
`+C3h`. Isso sustenta correspondência do boot inicial e da tabela de
vetores, mas não valida periféricos, relógio, entradas ou todo o fluxo
da revisão A. Por isso `trace_ma17.py --firmware` continua exigindo
código idêntico ao G até `757Fh` para ensaios naturais no perfil Fiat.
O teste `Sab80C517.SixRomResetPrefixConfiguresSamePortsAndSyscon`
executa o reset original das seis imagens até `0883h` e confirma
`P1=FBh`, `P2=F8h`, `P3=E7h`, `P4=EAh`, `P5=0Fh`, `SP=D0h` e
`SYSCON=02h`. `P3` começa em `F7h`, mas o `CLR T0` comum em `0880h`
limpa `P3.4` com `IP0` inicialmente zero no ensaio. Esse teste cobre
somente o prefixo anterior à autoverificação de XRAM.
Em `Sab80C517.SixRomXramSelfTestReachesCommonBootContinuation`, as seis
ROMs também executam a autoverificação em uma CPU isolada com 64 KiB
de XRAM emulada e chegam a `0A3Ah`. Portas, `SP`, `SYSCON` e flags
`2Bh/2Eh` coincidem nesse ponto; `F8:FFh=FFh` em todos os casos.
Isso amplia a equivalência observada do boot, mas não valida o mapa
físico da XRAM nem o perfil completo da revisão A.
O mesmo teste prossegue até `0B30h`: os opcodes `MOVC`/`MOVX` copiam
`7FF6h..7FFFh` para dez posições `F8:xxh` usando os bytes de cada
ROM. `PCON=00h`, `S0CON=91h`, `TMOD=11h`, `TCON=15h`, `T2CON=85h`,
`CCEN=01h`, `IP0=39h`, `IP1=0Ch`, `IEN0=A2h` e `IEN1=30h` coincidem
nas seis execuções isoladas. Seis bytes copiados diferem entre os
grupos G/S88 e A/A+/S37/S36:

| ROM | XRAM | G/S88 | A/A+/S37/S36 |
| --- | --- | ---: | ---: |
| `7FF6h` | `F8:0Fh` | `01h` | `00h` |
| `7FF7h` | `F8:1Eh` | `48h` | `00h` |
| `7FFCh` | `F8:3Fh` | `49h` | `4Ah` |
| `7FFDh` | `F8:4Dh` | `20h` | `19h` |
| `7FFEh` | `F8:8Fh` | `A1h` | `A2h` |
| `7FFFh` | `F8:DEh` | `BFh` | `8Eh` |

O mesmo teste prossegue da inicialização em `0B30h` até `11C4h`, ponto
comum do caminho que produz estado de RPM, nas seis ROMs originais.
Isso comprova alcançabilidade na CPU C517A isolada com XRAM emulada;
não valida as entradas da roda fônica, o clock nem a fiação da revisão A.

Os quatro bytes `7FF8h..7FFBh` coincidem. Depois do boot, a rotina
G/S88 `4A31h..4A7Eh` (A/A+/S37/S36 `4AF4h..4B41h`) compara nove
pares `7FF7h..7FFFh`/XRAM copiados, além de limites em `F8:40h..45h`.
O teste `Sab80C517.SixRomTailBytesGuardXramIntegrity` executa os
opcodes originais nas seis ROMs: cada par igual segue para `4AC5h` ou
`4B88h`; alterar isoladamente qualquer dos nove bytes da XRAM toma
`4A7Eh` ou `4B41h` e, com `IRAM[47h]=0`, retorna ao início `0850h`.
No desvio, o código usa `ROM[72CAh]=96h` e `ROM[72C9h]=20h`, iguais
nas seis imagens: `IRAM[47h]=01h` permite continuar, `96h/20h`
(`IRAM[47h]`/`IRAM[48h]`) reinicia, e `96h/21h` permite continuar.
Os três casos de fronteira também passaram no teste com os opcodes
originais. Assim, uma divergência não implica sempre reinicialização.
`7FF6h`/`F8:0Fh` não entra nessa comparação. Isso identifica uma guarda
de integridade de estado XRAM contra valores da própria ROM. O ensaio
é isolado e não prova que a corrupção ocorra numa execução natural;
o significado físico dos campos e a ligação física da XRAM ainda não
estão estabelecidos.

Um trace opcional de `MOVX` nos dez destinos (`MA17_TRACE_BOOT_XRAM_FIELDS`)
repetiu G e S88 originais a 1.000 RPM, com ADC0/2/3/5/6/7 fixos em
40/220/80/40/95/63 e 2,4 milhões de ticks. Em ambas as ROMs, `0AABh`
copiou os dez bytes originais e `5896h` releu os nove usados na guarda,
com valores idênticos; `F8:0Fh` ficou fora dessa comparação. Nos seis
destinos que diferem entre G e A, não apareceu outro PC leitor nesse
ensaio após excluir a autoverificação XRAM (`55A2h`) e a leitura anterior
à cópia em `092Eh` de `F8:1Eh`. Isso limita os consumidores **observados**,
sem excluir caminhos de outros estados. Para G, relatórios com o trace
ligado/desligado coincidiram em saídas P5, CC3, RAM e cobertura de PC.
Uma repetição G a 4.000 RPM e ADC0/3/6=180/232/247 encontrou o mesmo
conjunto de PCs leitores desses dez campos; a janela continuou em
2,4 milhões de ticks.
Regressão: `test_boot_copies_and_later_guard_reads_original_bytes`;
capturas: `boot_xram_fields_{G,S88}_1000/` e
`boot_xram_fields_G_4000_high_tps/`.

## Matriz de bytes divergentes

| | G | A | A+ | S88 | S37 | S36 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| G | 0 | 19002 | 19002 | 1440 | 19369 | 19374 |
| A | 19002 | 0 | 0 | 20008 | 2328 | 2333 |
| A+ | 19002 | 0 | 0 | 20008 | 2328 | 2333 |
| S88 | 1440 | 20008 | 20008 | 0 | 19368 | 19373 |
| S37 | 19369 | 2328 | 2328 | 19368 | 0 | 5 |
| S36 | 19374 | 2333 | 2333 | 19373 | 5 | 0 |

O resumo abaixo vem de `build/ma17-analysis/variants/comparisons.json`.
Percentuais são de bytes **idênticos no mesmo offset** em 32768 posições,
arredondados a duas casas; intervalos alterados são sequências contíguas
de offsets diferentes, sem alinhamento semântico de código:

| Par | Idênticos | Intervalos alterados | Maior intervalo (bytes) |
| --- | ---: | ---: | ---: |
| G–A | 42,01% | 319 | 414 |
| G–A+ | 42,01% | 319 | 414 |
| G–S88 | 95,61% | 5 | 718 |
| G–S37 | 40,89% | 298 | 717 |
| G–S36 | 40,88% | 302 | 717 |
| A–A+ | 100,00% | 0 | 0 |
| A–S88 | 38,94% | 306 | 568 |
| A–S37 | 92,90% | 17 | 717 |
| A–S36 | 92,88% | 21 | 717 |
| A+–S88 | 38,94% | 306 | 568 |
| A+–S37 | 92,90% | 17 | 717 |
| A+–S36 | 92,88% | 21 | 717 |
| S88–S37 | 40,89% | 300 | 492 |
| S88–S36 | 40,88% | 304 | 492 |
| S37–S36 | 99,98% | 4 | 2 |

`A` e `A+` são duplicatas exatas; o nome `+1.5bar` não permite afirmar uma
alteração de pressão ou estratégia, pois nenhum byte muda. `G` e `S88`
coincidem em `0x0000..0x757F` e divergem em cinco trechos entre
`0x7580` e `0x7FEE`, totalizando 1440 bytes. Esse é o par mais promissor
para estudar efeito de calibração com código inicial idêntico. Ainda falta
demonstrar que nenhum desses trechos seja código alcançável por fluxo indireto.
No assembly da referência, 1366 diferenças pertencem a bytes `DB` e 74
caem na lacuna `FF` de `0x7FA5..0x7FEE`, que permanece não classificada.
`S37` e `S36` compartilham todos os bytes de `6E00h..7FFFh`; suas cinco
diferenças estão próximas do vetor `IEX3`, inclusive seu destino. Elas
não representam versões distintas das calibrações nessa faixa.

`A` e `S37` coincidem em `0x0000..0x6EAA` e diferem em 17 intervalos,
todos em `0x6EAB..0x7FEF`. O maior trecho é `0x7B45..0x7E11` (717 bytes).
Entre eles há `0x7B3E` (um byte), `0x7ED9..0x7F47` (111 bytes) e
`0x7F51..0x7F8D` (61 bytes). Esses endereços são candidatos prioritários
para rastrear `DPTR`/`MOVC`, dimensões e consumidores antes de atribuir
grandezas físicas.

Dois desses 17 intervalos ficam **fora** dos 116 alvos do diretório de
ponteiros e somam 374 dos 2.328 bytes divergentes A–S37 (16,1%):

| Intervalo | A/A+ | S37/S36 | G/S88 | Classificação |
| --- | --- | --- | --- | --- |
| `6EABh..6FC9h` (287 bytes) | `CBh`×286, `D0h` | `FFh`×287 | `FFh`×287 | Não classificado; emitido como `DB` |
| `7199h..71EFh` (87 bytes) | `FFh`×87 | `7Fh`×62, `77h`×20, `76h`, `67h`×4 | `FFh`×87 | Não classificado; emitido como `DB` |

O round-trip representa os bytes alterados com `DB`; nenhum slot
`7002h..70E9h` aponta a esses intervalos. Isso não exclui leituras
indiretas nem prova que sejam preenchimento. Não há trace natural de
A/S37 que identifique consumidor ou função, portanto os dois registros
permanecem fora da contagem de tabelas curadas, em
`unclassified_nonpointer_intervals` no catálogo JSON. A disposição
e os hashes de todas as ROMs são conferidos por
`test_unclassified_nonpointer_intervals_preserve_variant_bytes`.
Uma auditoria de endereço efetivo `MOVC` em 1.820 relatórios encontrou
1.369 com a observação habilitada: 1.090 da G e 279 da S88. Nenhuma
leitura alcançou os dois intervalos acima nem `722Ch`; os outros 451
relatórios não observavam `MOVC`. O comando
`python3 tools/audit_ma17_opaque_reads.py` produz
`build/ma17-analysis/variants/opaque_read_audit.json` e distingue
`MOVC @A+DPTR`, `MOVC @A+PC` e endereços espelhados pelo mapeamento da
EPROM. A regressão sintética é
`test_counts_mapped_dptr_and_pc_reads_separately_from_untraced_files`.
Esse corpus contém apenas G/S88, portanto a ausência de leitura nele
não exclui acesso nas revisões A/S37/S36 nem em estados não ensaiados.

Na página `7200h..72FFh`, 15 bytes diferem entre G/S88 e a família A:
`722Ch`, `7292h..7294h` e `72DFh..72E9h`. Os últimos onze já compõem
limites da máquina de estados A descrita adiante. A seleção serial
homóloga G/S88 `4CA0h..4D0Eh` e A/S37 `4D63h..4DD1h` usa
`DPTR=7200h` e lê `7290h+estado` por `MOVC`; `7292h..7294h` são
`89 13 BC` em G/S88 e `04 94 38` na família A. Um teste com os
opcodes originais das seis ROMs preparou estados 2, 3 e 4 e confirmou
cada byte em `IRAM[45h]` e depois em `S0BUF` pelo escritor serial
`4C78h`/`4D3Bh`. Isso prova a rota digital, sem afirmar em qual etapa
de uma sessão física cada byte é transmitido. **`7294h` tem dois
consumidores conhecidos:** é também o índice zero do bloco de limites
da matriz `7294h..7299h`. Um artefato antigo de round-trip da A
classificava `4D63h` como `DB`; a execução atual do pipeline, sem
`--entry` adicional, emite a rotina como código e remonta 32.768 bytes
com hash idêntico (`build/ma17-analysis/variants/roundtrip_alcohol_serial_control/`).
A execução com `--entry 0x4D63` produziu as mesmas métricas
(`code_bytes=23615`, `data_bytes=4374`, `unclassified_bytes=4779`),
portanto o artefato anterior estava desatualizado. `722Ch=00h` em G/S88
e `9Ch` na família A, preservado como `DB` no round-trip. O único
`MOV A,#2Ch; MOVC` literal encontrado em G/A executa com `DPTR=7300h`
e lê `732Ch`; ainda pode haver índice indireto para `722Ch` em estados
não ensaiados. Esse byte permanece sem consumidor confirmado no catálogo
`opaque_722c`. Catálogo:
`serial_handshake_bytes_7290` e `matrix_conditional_threshold_7294`.

Uma checagem de fluxo dos opcodes G descartou dois outros candidatos
aparentes para `722Ch`. Em `4A05h`, `DPTR=7300h` e `R2=06h`; as seis
chamadas a `5887h` não alteram esses registradores. Se o salto alcançar
`4A8Ch`, seu `MOVC A,@A+DPTR` lê `7306h`. O caminho que carrega
`DPTR=7200h` em `4A83h` salta por cima desse `MOVC`. Na ramificação
iniciada em `3607h`, o `MOVC` de `3643h` usa `DPTR=7200h`, mas a condição
anterior fixa `R7=01h`, produzindo índice `CCh` e leitura de `72CCh`.
Essas exclusões reduzem os candidatos estáticos; não demonstram ausência
de leitura indireta em outras rotinas ou estados.
O interpolador compartilhado em `532Bh` também não fornece um caminho
direto conhecido: seus `MOVC` variáveis em `534Bh/5350h` recebem `DPTR`
da rotina `5238h`, que decodifica um ponteiro big-endian. Os nove
chamadores diretos G carregam slots `70CEh`, `7060h`, `7062h`, `7064h`,
`7066h`, `705Ch`, `7082h`, `7088h` ou `7036h`; seus destinos
originais estão entre `7859h` e `7E16h`. Mesmo somando o índice de oito
bits, esses acessos não alcançam `722Ch`. A conclusão cobre os chamadores
diretos inspecionados, sem substituir uma análise de todos os estados.
O scanner de referência em `ECUMonomotronic.cpp` lê apenas quatro bytes
de chave depois de `55h` e comenta o quarto como `BCh`, enquanto a
sequência bruta G/S88 tem cinco bytes `46 85 89 13 BC` e o documento
`BOSCH_MONOMOTRONIC_PROTOCOL.md` reconhece essa possibilidade.
Em boot completo emulado de G e S88, a injeção de 5 baud fez cada ROM
escrever `55 46 85 89 13 BC` na PTY, em ordem; sem resposta do scanner,
o bloco foi transmitido novamente. Cada `write` retornou 1. O teste
`test_g_s88_full_boot_transmits_five_serial_key_bytes` reproduz a primeira
sequência. Capturas: `build/ma17-analysis/serial_five_key_probe_{g,s88}/`.
Isso confirma os cinco bytes no **perfil Fiat emulado**, mas ainda não
é uma captura elétrica da ECU real nem valida o perfil A em boot completo.
O cliente local `test_pty.py` lia quatro chaves e descartava um byte
pendente antes de enviar `~Key2`. Após passar a ler a quinta chave no
modo PTY, `./run_test.sh` registrou `Key5=BC`, respondeu `7Ah` ao
`Key2=85h`, recebeu os pacotes de identificação e terminou o handshake
com sucesso. O cliente para porta física continua aceitando quatro
chaves porque essa sequência não foi medida no hardware real.

Auditoria de cobertura dos **dados** `6E00h..7FFFh`: 2.399 offsets
divergem em pelo menos uma das seis ROMs, e todos estão dentro de
intervalos do catálogo ou dos registros explicitamente não classificados.
Os 22 offsets antes ausentes foram descritos em três entradas:
`6E00h..6E17h` contém duas strings ASCII de identificação (nove bytes
alterados entre famílias, vistas na resposta PTY da G); `7000h:7001h`
guarda `56B4h` em G/S88 e `5777h` na família A, um deslocamento de
`+C3h` cujo leitor ainda é desconhecido; `72DFh..72E9h` contém onze
limites/constantes da máquina de estados A, já exercitados por testes
isolados de opcodes originais. A regressão
`test_catalog_covers_changed_data_pages` confere a cobertura byte a
byte e os seis dumps. **Cobertura não atribui função física:** a
auditoria exclui o código `0000h..6DFFh` e mantém os intervalos
sem consumidor comprovado como desconhecidos.

## Diretório e três tabelas candidatas

Os 116 pares big endian em `0x7002..0x70E9` apontam para 116 endereços
distintos entre `0x73C0` e `0x7F8D`. Cada slot aponta para o **mesmo**
endereço nas seis imagens. `pointer_regions.json` alinha esses alvos por
slot, preserva bytes brutos e conta diferenças por região. O próximo alvo
em ordem de endereço serve apenas como limite superior **provisório**; a
última região não tem limite inferido. Os 116 registros são candidatos, não
116 funções de calibração identificadas. `S88` altera 14 das 115 regiões
com limite provisório, `A`/`A+` alteram 31 e `S37`/`S36` alteram 17,
sempre em comparação com `G`. O par anterior, em `0x7000`, vale `56B4h`
em `G`/`S88` e `5777h` nas demais; seu papel ainda não foi demonstrado.
Nenhuma das seis imagens contém a sequência literal
`MOV DPTR,#7000h` (`90 70 00`); G carrega `DPTR=7002h` em `4773h` e o
leitor big endian em `523Bh` acessa o primeiro slot desse diretório.
Numa nova execução G/S88, ROM original, 1.500 RPM, ADC0/6=160/380,
2,4 milhões de ticks e `MOVC` ativo, `7002h` foi lido 471/467 vezes,
enquanto `7000h:7001h` não foi lido. Uma auditoria de 1.435 relatórios
com `MOVC` do corpus local G/S88 também não encontrou leitura efetiva
desses dois bytes; o corpus mistura versões do emulador e não contém
boot completo da família A. Isso restringe o uso **observado** do par,
sem excluir cálculo dinâmico de `DPTR`, outro estado ou leitor externo.
Reproduzir: `python3 tools/audit_ma17_directory_prefix.py --output
build/ma17-analysis/variants/directory_prefix_audit.json`; teste:
`test_directory_prefix_audit_detects_effective_movc_reads`. Capturas:
`build/ma17-analysis/variants/directory7000_current_{g,s88}/`.
O alinhamento dos alvos demonstra ausência de deslocamento desses 116
inícios, mas não garante equivalência dos algoritmos que os consomem.

Uma auditoria por byte encontrou 41 alvos apontados com diferenças entre
as ROMs: 36 começam em entradas curadas e cinco são subvisões cobertas
por tabelas maiores (`74F8h`, `7502h`, `7617h`, `76F8h`, `77D9h`).
Todos os bytes divergentes dessas regiões antes de `7F9Dh` estão
cobertos pelo catálogo. Os 87 bytes divergentes restantes ficam na
cauda `7F9Fh..7FFFh`, cujo intervalo candidato herdado de `7F8Dh`
inclui uma região sem classificação funcional e constantes de boot,
não uma tabela única.
Eles se separam em 81 posições de `7F9Fh..7FEFh` e seis bytes de
`7FF6h..7FFFh` copiados no boot. Em `7F9Dh..7FEFh` (83 bytes), G/A/A+
são `FFh` contínuos; S37/S36 preservam dois `FFh` e usam 81 `00h`;
S88 preserva oito `FFh`, depois `11h`×4, `06h`×3, `11h`, `10h`,
`11h`×65 e `FFh`. As seis imagens compartilham
`7FF0h..7FF5h = FF FF FF 07 45 FF`. Esse padrão de lacuna é
compatível com preenchimento ou edição, mas uma leitura indireta
ainda não foi excluída; portanto permanece **não classificado** como
função, embora seus bytes estejam agora registrados no catálogo. O teste
`test_unclassified_rom_tail_gap_has_variant_specific_raw_patterns`
confere cada byte e o tamanho das seis ROMs.
Nos rastros G/S88 `experiments_opcode86_fixed/gate63_tps_40_95/`
(2,4 milhões de ticks por ROM), `MOVC` leu os bytes de boot em
`7FF6h..7FFFh`, mas nenhuma posição de `7F9Dh..7FEFh`. Isso limita
apenas a trajetória testada; acesso por outro estado continua possível.
O teste `test_catalog_accounts_for_changed_pointer_tail_as_unknown_and_boot`
protege essa fronteira; cobertura de bytes não confirma função física.

Das 115 regiões com limite provisório, 75 têm conteúdo igual nas seis
imagens. Em 23, `G/S88/S37/S36` compartilham bytes e `A/A+` formam outro
grupo; isso inclui `70A2h→7ED9h` e `70A6h→7F51h`. Em nove regiões,
`G/A/A+` compartilham bytes, `S88` usa uma segunda versão e `S37/S36`
uma terceira; isso inclui os alvos de `7046h` e `7048h`. Outras oito
regiões apresentam padrões mistos, registrados em `raw_equality_patterns`.
Os padrões são parentesco **de conteúdo da região**, não prova de qual
arquivo veio primeiro nem de qual combustível cada calibração atende.

## Homologia de código entre revisões

`tools/align_ma17_variants.py` cruza as classificações de código de dois
assemblies remontados, procura janelas idênticas de 32 bytes com ocorrência
única em cada ROM e une janelas sobrepostas de mesmo deslocamento. Registra
apenas blocos de pelo menos 64 bytes; valida novamente os bytes completos
de cada bloco. Os JSONs em `build/ma17-analysis/variants/code_alignment_*.json`
incluem hashes das ROMs e dos assemblies para rastreabilidade. Exemplo:

```sh
python3 tools/align_ma17_variants.py FiatTipo_MA17_dump_27c256.bin 'firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin' --reference-asm build/roundtrip/FiatTipo_MA17_dump_27c256/FiatTipo_MA17_dump_27c256.disasm51.asm --variant-asm 'build/ma17-analysis/variants/roundtrip_alcohol/tipo 1.6 alcool27c256.disasm51.asm' --output build/ma17-analysis/variants/code_alignment_gasoline_alcohol.json
```

`G` versus `A` produziu 11013 âncoras e 71 blocos com 12547 bytes de código
idêntico, com deslocamentos `0`, `+28`, `+46`, `+78`, `+184`, `+189` e `+195`.
Os grupos dominantes são `+28` (4760 âncoras), `0` (2159), `+46` (1556),
`+189` (1155) e `+195` (986). Por exemplo, `G:2157h..238Fh` corresponde
exatamente a `A:2173h..23ABh` (`+28`). Isso identifica blocos homólogos,
sem afirmar que cada entrada de procedure do IDA seja válida.

`G` versus `S88` encontrou 18105 bytes em oito blocos, todos no mesmo
offset. `A` versus `S37` encontrou 18300 bytes em oito blocos, também sem
deslocamento. Blocos não alinhados ainda podem ser código equivalente com
operandos ou saltos alterados; nenhuma identidade semântica foi atribuída
automaticamente a eles.

Os pares big endian em `0x70A2`, `0x70A4` e `0x70A6` apontam para
`0x7ED9`, `0x7F15` e `0x7F51` em todas as seis imagens. Os alvos são
adjacentes a 60 bytes de distância; `candidate_tables.json` preserva os
60 valores brutos de cada fatia, hash da ROM, endereço, codificação do
ponteiro, grade bruta 6×10, diferença aritmética bruta por célula, mínimos,
máximos e quantidade de células alteradas por linha. Essa grade descreve
bytes; a interpretação matemática dos valores ainda não foi provada.
Em `A`/`A+` mudam
respectivamente 60, 59 e 60 bytes. Em `S88` não muda nenhum desses 180
bytes. Em `S37`/`S36` apenas a fatia `0x7F15` difere de `G` (60 bytes).
Na fatia `7F15h`, `A`/`A+` preservam uma única célula na quinta linha;
as demais linhas dessas três fatias mudam por completo quando diferem.

### Silhueta das matrizes por revisão

`/usr/bin/python3 tools/plot_ma17_matrices.py --matrix 0x7581 --variant S88`
gera PNG, CSV por célula e resumo JSON em
`build/ma17-analysis/variants/matrix_plots/`. A mesma interface aceita
os seis inícios de `MATRICES` em `tools/compare_ma17_variants.py`, mais
`7B46h`, `7BBEh`, `7C36h`, `7CAEh`, `7D26h` e `7D9Eh`, além das curvas
de 15 células `7E9Dh`, `7EACh` e `7EBBh`; aceita `G`,
`A`, `A+`, `S88`, `S37` e `S36` nos dois lados da comparação.
Os mapas de calor usam a mesma
escala 0–255 para as duas ROMs; o terceiro painel mostra a diferença
**assinada** de bytes e o quarto a média bruta por linha ou o valor de
cada célula nas curvas de uma linha. CSV e JSON
registram endereços e hashes, permitindo conferir a imagem com a ROM.
Nas curvas `7E9Dh/7EACh/7EBBh`, quando os dois lados usam os mesmos
segmentos `7570h`, as colunas recebem o início bruto em `RAM47h`;
quando os segmentos diferem, o gráfico mantém índices e CSV/JSON
registram separadamente os dois conjuntos de limites.

Em [7581h, G/S88](../build/ma17-analysis/variants/matrix_plots/matrix_7581_g_vs_s88.png),
as duas silhuetas têm a mesma forma: todas as 225 células de S88 valem
exatamente G+21. Em [7ED9h, G/A](../build/ma17-analysis/variants/matrix_plots/matrix_7ed9_g_vs_a.png)
e [7F51h, G/A](../build/ma17-analysis/variants/matrix_plots/matrix_7f51_g_vs_a.png),
as 60 células de A e A+ seguem, respectivamente,
`min(255, G+34)` e `min(255, G+38)`. A saturação explica por que
o mapa de diferenças não é uniforme nos valores altos. O resumo JSON
registra `saturated_add_delta`; o teste confere cada byte nas ROMs originais.
Já [7F15h, G/A](../build/ma17-analysis/variants/matrix_plots/matrix_7f15_g_vs_a.png)
mostra um platô de valores altos em G que recua na versão A; o delta
varia de −156 a +27 e 59/60 células mudam. Em
[7F15h, G/S37](../build/ma17-analysis/variants/matrix_plots/matrix_7f15_g_vs_s37.png),
o formato é ainda mais distinto: os 60 bytes S37/S36 de `7F15h`
repetem **exatamente** os 60 bytes de `7ED9h` dessas ROMs e de G;
em A/A+, as duas matrizes internas diferem em nove células, enquanto
em G/S88 diferem nas 60. Isso é evidência de convergência das duas
calibrações selecionáveis em S37/S36, não prova de qual estado é
atingido em uso normal nem de função física idêntica após o lookup.
Uma comparação **interna** de A/A+ mostra algo mais específico:
`7F15h` é igual a `7ED9h` nas primeiras 51 células; nas nove finais
(última linha, colunas 1–9), cada byte de `7F15h` vale `7ED9h−34`.
O [mapa A: 7ED9h versus 7F15h](../build/ma17-analysis/variants/matrix_plots/matrix_7ed9_a_vs_7f15_a.png)
isola essa faixa. As duas tabelas usam o mesmo eixo bruto `upper IRAM[AFh]`;
a última linha começa em `FBh` (251), conforme `7B3Eh`. O padrão é
compatível com uma correção por estado selecionado naquela faixa, mas
não estabelece quando `RAM57h=1` ocorre naturalmente nem qual saída física
esse valor controla. Para reproduzir:
`/usr/bin/python3 tools/plot_ma17_matrices.py --reference-variant A --reference-matrix 0x7ED9 --matrix 0x7F15 --variant A`.
Para `7ED9h`, `7F15h` e `7F51h`, o gráfico agora anota em cada coluna
o início nominal em RPM derivado de `7B32h` e do fator 25 observado no
modelo Fiat. Cada painel superior também anota o início **bruto** de
sua linha e a origem `IRAM[7Dh]` ou `upper IRAM[AFh]`, obtidos de
`7B3Eh`. O CSV e o JSON registram as mesmas coordenadas. As colunas
do mapa de calor mantêm **largura visual igual**, mesmo quando os
intervalos de RPM diferem; linhas e valores das células seguem brutos.
[7ED9h, G/A com eixo nominal](../build/ma17-analysis/variants/matrix_plots/matrix_7ed9_g_vs_a.png)
mostra esse formato. Para `7581h`, `7662h` e `7743h`, os eixos
continuam em índices brutos porque sua escala ainda não foi validada.
Em [7F15h, G/S37](../build/ma17-analysis/variants/matrix_plots/matrix_7f15_g_vs_s37.png),
as linhas homólogas começam em bytes diferentes de `7Dh`; o painel de
diferenças compara **células de ROM por índice**, não resultados sob a
mesma tensão ou o mesmo estado do sensor. A regra de soma saturada é uma
relação entre bytes, não uma escala física validada.

### Alvo terminal `70C4h→7F8Dh`

O inventário anterior parava no maior alvo do diretório sem guardar
seus bytes, pois não existe um ponteiro seguinte para delimitar o fim.
O gerador agora registra `7F8Dh..7FFFh` como **região candidata até o
fim da ROM**; esse intervalo inclui preenchimento e metadados e não é
uma única tabela. O recorte demonstrado pelo código é `7F8Dh..7F95h`:
um cabeçalho de endereço IRAM e contagem `07h`, seguido de sete
incrementos. G/S88/S37/S36 contêm `0F 07 01 01 02 04 08 10 E0`;
A/A+ contêm `35 07 01 01 02 04 08 10 FF`. O vetor seguinte,
`7F96h..7F9Ch`, é `01 01 03 03 04 06 09` nas seis ROMs.

G `3AADh→5279h` e a família de código A `3ADBh→533Ch` resolvem
`70C4h` e retornam um índice em `R3`. Em execução isolada dos opcodes
originais, mudar apenas lower IRAM `0Fh` de `00h` para `80h` alterou
`R3` em G; mudar `35h` não. Na A ocorreu o inverso. Os trechos
decodificadores G `527Ch..52C8h` e A `533Fh..538Bh` são idênticos.
Uma varredura isolada dos 256 valores, fornecidos igualmente às duas
fontes IRAM, encontrou `R3` diferente **exatamente em `00h..1Fh`**
(32 entradas); em `20h..FFh`, os índices coincidiram. A fronteira é
coerente com a mudança do incremento final `E0h→FFh` e foi fixada
como regressão no teste dos opcodes originais.
Os trechos
seguintes comparam `R3` com upper IRAM `83h`, consultam `7F96h`, somam
um valor a upper `8Ch` e chegam à escrita de lower `69h` em G.
O contador `07h` no cabeçalho faz o decodificador devolver `R3` entre
`00h` e `06h`. Nesse ramo, a comparação grava `R3` em `83h`, mantém
um valor anterior menor, ou incrementa esse valor menor em uma unidade;
portanto o `MOVC` com `DPTR=7F96h` só alcança `7F96h..7F9Ch`.
O teste `TerminalCurveLookupStaysWithinSevenBytes` executa os opcodes
originais G/A para as 256 entradas, cinco valores prévios de `83h`
(`00h`, `01h`, `06h`, `07h`, `FFh`) e dois estados de `82h`, confirmando
`A≤06h` e `DPTR=7F96h` imediatamente antes do `MOVC`. Saltos anteriores
para o mesmo opcode usam outro `DPTR`; a prova não cobre possíveis
entradas anômalas com registradores preparados externamente nem outros
leitores indiretos de `7F9Dh..7FF5h`. Esses bytes continuam sem função
atribuída.
O teste `TerminalSegmentHeaderSelectsDifferentIramSource` confirma a
troca da fonte e essa faixa de diferenças em `R3`; não
demonstra a frequência natural dessa rota nem sua função física.
Um segundo teste executa os opcodes originais até a escrita de `69h`.
Com `upper 8Ch=80h`, `upper 82h=01h` e `upper 83h=00h`, a mudança da
entrada selecionada altera `R3`, mas o comparador em `3AB8h`/`3AE9h`
descarta esse índice e `69h` não muda. Com `upper 83h=07h`, o índice
é aceito: mudar `0Fh` em G ou `35h` em A altera `upper 83h`, `8Ch` e
`lower 69h`; mudar o outro endereço IRAM não altera esses valores.
O teste `TerminalSegmentFlowsIntoIram69InIsolatedCode` fixa os dois
ramos. Essa condição inicial é controlada e não demonstra que a ECU
alcance `83h=07h` em operação natural.
Com as duas fontes IRAM iguais a `00h`, `upper 83h=07h`, `upper 8Ch=80h`
e `upper 82h=01h`, a execução isolada até a escrita de `69h` produziu
`7Fh` na G e `7Ah` na A. Na entrada de fronteira `20h`, ambas
produziram `77h`; com `upper 83h=00h`, a entrada `00h` foi mascarada
e ambas produziram o mesmo estado. Os 91 bytes dos caminhos
consumidores coincidem, exceto os dois bytes do endereço da chamada
ao decodificador homólogo, cujos opcodes também coincidem. Com as
fontes iguais, o contraste isola o incremento final `E0h/FFh` no
estado controlado. Ainda não demonstra ocorrência natural nem efeito
nos pinos P5.
Como continuação isolada, os dois resultados `69h=7Fh/7Ah` foram
fornecidos ao **mesmo código original G** em `043Bh..0521h`, com
`31h=59h` e `36h:37h=011Dh`. A recarga calculada em `34h:35h` foi
`4CFEh/34FFh`, respectivamente. O serviço `IEX3` usa esse par em
`0286h` para carregar `TL1/TH1`. O teste
`FirmwareRam69ChangesTimer1ReloadCalculation` fixa os números;
essa cadeia controlada não é uma execução natural da ROM A nem uma
medição de pulso P5.
Em três execuções completas do mesmo firmware G a 1.000 RPM, ADC0..7
bruto `40/130/100/80/90/110/95/63` e 2,4 milhões de ticks,
`MA17_OVERRIDE_RAM69` forneceu `7Fh` ou `7Ah` **antes da leitura em
`043Bh`**, após existir RPM. A mediana do pulso baixo modelado em
P5.0/P5.1 foi `1921/1863` ticks, contra `1861` no controle;
o período mediano ficou em `59400` ticks e CC3 em `3041` ticks nos
três casos. A diferença `7Fh→7Ah` equivale a −58 ticks nesse modelo.
O teste `test_terminal_segment_iram69_values_change_modeled_p5_in_g`
reproduz o contraste e verifica que a ROM G permaneceu intacta.
A intervenção contorna o lookup natural em `7F8Dh`, portanto não prova
que alguma das ROMs produza esse par de valores em operação normal
nem identifica fisicamente o pino P5. Capturas:
`build/ma17-analysis/variants/terminal_7f8d_ram69_{control,7f,7a}_g/`.
Um segundo contrafactual atingiu o próprio decodificador sem modificar
a ROM. `MA17_OVERRIDE_MOVC_AT` agora aceita pontos separados por
vírgula. Em G a 1.000 RPM, entregar `28h` no `MOVC 527Dh/7F8Dh`
faz a rotina ler `RAM[28h]=00h`; entregar também `FFh` no
`MOVC 5289h/7F95h` mudou `R3` de `00h/00h` para `05h/05h` nas duas
visitas. `upper[83h]` passou de `00h/00h` para `00h/01h`. Ainda assim,
`69h` terminou em `9Ah` e a mediana P5.0 ficou em `1861` ticks nas
duas execuções. Os tempos de alguns eventos e histogramas P5 diferem,
portanto a igualdade da mediana não significa traços idênticos. O teste
`test_terminal_segment_dual_movc_override_changes_r3_not_p5_median`
verifica os dois overrides e o hash intacto. Capturas:
`terminal_7f8d_source28_g/` e `terminal_7f8d_source28_finalff_g/`.
Esse ensaio usa `RAM[28h]` como fonte experimental; não representa a
fonte normal da ROM G ou o perfil de hardware A.
Um trace atual da G original, com 1.000 RPM, ADC0..7 bruto
`40/130/100/80/90/110/95/63` e 2,4 milhões de ticks, observou a
rota **naturalmente duas vezes**: `MOVC` leu `7F8Dh=0Fh`, `7F8Eh=07h`
e `7F95h=E0h` duas vezes cada. Em `3AD2h`, leu `7F97h=01h` e
`7F98h=03h` uma vez cada; `upper 83h` era `01h/02h` e `upper 8Ch`
era `9Ch/9Bh` antes dessas leituras. O teste
`test_terminal_segment_and_adjacent_curve_are_read_naturally_in_g`
reproduz o estado. Esse trace, isoladamente, não separa a contribuição da tabela para
`69h` no funcionamento completo nem valida o perfil de hardware A.
Captura: `build/ma17-analysis/variants/terminal_7f8d_natural_g_tps40/`.
No mesmo estado natural da G, uma intervenção exclusivamente no retorno
`MOVC` de `3AD2h/7F97h` e `3AD2h/7F98h` separou a contribuição da curva.
O retorno nativo `01h/03h` produziu `upper[8Ch]=9Bh` após a primeira
leitura e escritas `69h: 9Ch→9Bh→9Ah`. Retornos `00h/00h` mantiveram
`upper[8Ch]=9Ch` nessa passagem e adiaram a escrita até `9Ah`; retornos
`FFh/FFh` produziram `upper[8Ch]=9Ah` logo na primeira passagem e
suprimiram a segunda visita ao `MOVC`. O hash da ROM G ficou intacto.
As três execuções terminaram com `69h=9Ah` e mediana P5.0 de 1.861
ticks; as histórias intermediárias diferiram. Isso confirma efeito
digital transitório da curva sobre `69h` no estado emulado, sem
identificar um efeito físico ou igualdade dos traços completos.
Capturas: `terminal_7f96_movc/`; teste
`test_terminal_7f96_movc_changes_natural_ram69_history`.
Com os demais canais ADC iguais e 2,4 milhões de ticks, uma pequena
matriz adicional registrou visitas `3AADh/3AB3h` em G: zero a 750 RPM
com ADC0 bruto 4; duas a 1.000 RPM com ADC0 4; duas a 1.000 RPM com
ADC0 20; zero a 1.000 RPM com ADC0 200. Nas duas condições que
visitaram a rotina, `0Fh=FEh/FFh` e `R3=06h/06h`. Isso demonstra
dependência do estado ensaiado, sem provar que ADC0 é uma medida
física de TPS. O teste
`test_terminal_segment_access_depends_on_rpm_and_adc0_state_in_g`
reproduz a matriz.
O probe em `3A7Dh` explica o desvio observado com ADC0 200:
`B=0Fh` (`B.3=1`) na única visita, ativando o `JB B.3` em `3A80h` para
`3AA9h`. Com ADC0 4 ou 20 a 1.000 RPM, `B=07h` nas duas visitas
e esse desvio não ocorre. A 750 RPM/ADC0 4, `3A7Dh` nem foi
alcançado nos 2,4 milhões de ticks. Em `3A04h`, as 56 amostras a
750 RPM tinham `R2=upper[8Ch]=9Ch`; a subtração dá zero e o `JNZ`
não alcança `3A1Eh→3A67h`. A 1.000 RPM/ADC0 4, duas amostras tinham
`R2=9Ah` abaixo de `upper[8Ch]=9Ch/9Bh` e seguiram por esse ramo.
O desvio que precede `3AADh` em `3A7Dh..3AACh` consulta `B.3`,
upper IRAM `9Bh/CBh/C9h`, `22h.1` e bits do acumulador lido por
`MOV A,@R0`. Em particular, o caminho até `3AADh` exige `B.3=0`,
`9Bh=CBh=C9h=0`, `22h.1=0` e bits `0/1` desse acumulador zerados;
outros ramos seguem diretamente para `3AD2h` com índice literal.
Portanto, a igualdade `R2=upper[8Ch]` explica a ausência da rota a
750 RPM, e `B.3` explica o desvio com ADC0 200 neste conjunto de
traces. A função física dessas variáveis continua indeterminada.
O valor de `B.3` também tem uma origem rastreável. Em `333Bh/333Fh`,
`2Eh.6` seleciona `28h.1` ou `28h.2` para o carry; `3341h` copia o
carry para `B.3` e grava `B` em upper IRAM `94h`. `3A04h` lê `94h`
de volta para `B`. Nos traços a 1.000 RPM, a última amostra de
`3341h` antes de cada `3A7Dh` tinha `2Eh=84h`: com ADC0 4/20,
`28h=00h`, carry 0 e `94h=07h`; com ADC0 200, `28h=06h`, carry 1 e
`94h=0Fh`. O teste da matriz verifica essa sequência. `1132h..1146h`
é um produtor conhecido de `28h.1/.2` na rotina das duas pistas;
isso ainda não valida a interpretação elétrica desses pares ADC.
Um probe opcional em `3AADh/3AB3h`, com referência à instrução
`MOV A,@R0` do SAB80C517, mediu as duas consultas no mesmo estado:
`lower 0Fh=FEh/FFh`, `lower 35h=FFh` e `R3=06h/06h` após o
decodificador. Em três execuções com a ROM G intacta, o controle foi
comparado com `MOVC 527Dh/7F8Dh→35h` e, separadamente,
`MOVC 5289h/7F95h→FFh`. As duas intervenções foram aplicadas e
registradas. Nenhuma mudou `R3`, o histórico estruturado de RAM,
as observações de lookup, P5, CC3 ou cobertura de PC; `69h` terminou
em `9Ah` e as medianas P5/CC3 ficaram em 1861/3041 ticks.
O teste `test_terminal_segment_a_bytes_are_masked_at_natural_g_inputs`
reproduz essa comparação. Capturas: `terminal_7f8d_factorial/`.
Isso delimita um estado de mascaramento por índice saturado; outros
valores de entrada e o perfil de hardware A permanecem abertos.
Com ADC0..7 bruto `40/130/100/80/90/110/95/63`, partida imediata,
sem sessão K-Line e 2,4 milhões de ticks, a varredura natural da G
registrou a seguinte entrada do decodificador em `3AADh`:

| RPM | Visitas | Faixa observada de `RAM[0Fh]` | `R3` após `3AB3h` |
| ---: | ---: | ---: | --- |
| 1.500 | 6 | `F2h..FDh` | `06h` em todas |
| 2.000 | 8 | `E3h..FDh` | `06h` em todas |
| 3.000 | 11 | `C3h..F9h` | `06h` em todas |
| 4.000 | 15 | `A4h..FEh` | `06h` em todas |

Nenhuma visita observada entrou em `00h..1Fh`, faixa em que o ensaio
isolado distinguiu os bytes terminais de G e A. A conclusão vale para
esses estímulos e essa duração; não demonstra ausência de efeito em
outros estados ou após estabilização maior. O teste
`test_terminal_segment_natural_rpm_sweep_stays_outside_low_input_range`
reproduz a varredura. Capturas:
`build/ma17-analysis/variants/terminal_7f8d_natural_g_rpm{1500,2000,3000,4000}/`.
Uma extensão da condição de 4.000 RPM a **4 milhões de ticks** preservou
as mesmas 15 visitas; a última ocorreu em `tick=308113` e terminou com
`RAM[0Fh]=FEh`, `R3=06h`. Até o fim dessa captura, não houve nova
entrada em `3AADh`. O trace adicional em `3A04h` registrou 362
amostras posteriores à última visita: em todas, `R2=upper[8Ch]=40h`.
Como a subtração em `3A0Eh` resultou em zero, o `JNZ` em `3A10h`
não seguiu para o decodificador. Isso explica a ausência de novas
visitas **nesse estado emulado**, sem provar inatividade geral da
tabela. O teste de regressão verifica a janela estendida e a guarda.
Capturas: `terminal_7f8d_natural_g_rpm4000_long/` e
`terminal_7f8d_natural_g_rpm4000_long_ram69/`.
O recorte terminal curado separa esses 16 bytes das diferenças no
preenchimento e nos metadados finais da EPROM.

Na ROM `G`, o código em `0x3291` carrega `DPTR=#70A2h` e chama `0x5323`;
`0x5228` resolve o ponteiro e `0x532F` lê dois bytes por `MOVC` para
interpolação. Na ROM `G`, `7B32h` declara dez segmentos do eixo `47h` e
`7B3Eh` declara seis do eixo `7Dh`. Em `3291h`, o índice inicial é
`índice_7Dh × 10 + índice_47h`. `532Fh/5333h` leem colunas vizinhas;
`534Bh/5350h` somam `R0=10` e leem a próxima linha. Assim, os 60 bytes
em `7ED9h..7F14h` formam uma matriz **6 linhas × 10 colunas** para
esse consumidor. A seleção da fatia via `RAM[57h]`, a escala numérica
do segundo eixo e a grandeza física da saída ainda exigem análise; a orientação precisa
ser verificada separadamente nas revisões com código diferente.

Para o primeiro eixo, o scanner propõe `RPM=25×IRAM[47h]`. Treze
execuções com as ROMs G e S88 intactas, roda 60−2 e perfil Fiat de
11,88 MHz registraram a escrita em `0EA5h/0EA7h`: G produziu
`47h=1Eh/28h/3Ch/45h/50h/78h/A0h` para
750/1.000/1.500/1.725/2.000/3.000/4.000 RPM; S88 produziu
`1Eh/78h` para 750/3.000 RPM. Nesses pontos, o fator 25 coincide
exatamente com a entrada simulada, inclusive no caso intermediário
1.725 RPM. Em torno desse ponto, G deu `44h` a 1.713 RPM,
`45h` a 1.724 e 1.738 RPM e `46h` a 1.749 RPM. Logo, o fator
25 descreve a escala dos pontos nominais testados, mas não se deve
aplicar truncamento ou arredondamento simples à RPM solicitada para
prever cada transição de byte. A validação cobre o relógio e os pulsos **modelados**; não
mede o oscilador ou a entrada elétrica de uma ECU real. Teste:
`VariantTraceTests.test_rpm47_matches_crank_rate_in_g_and_s88_profiles`.

Os bytes originais de `7B32h` são `47 0A 06 08 0C 18 23 29 28 28
2F 01`: endereço IRAM, dez segmentos e dez incrementos. Executando
`527Ch..52CCh` da ROM G isoladamente para cada entrada `47h=00h..FFh`,
`R3` muda de segmento nos valores brutos `08h`, `10h`, `1Ch`, `34h`,
`57h`, `80h`, `A8h`, `D0h` e `FFh`. O primeiro segmento começa em
`00h`. Multiplicar esses inícios por 25 dá coordenadas **nominais**
de 0, 200, 400, 700, 1.300, 2.175, 3.200, 4.200, 5.200 e 6.375 RPM
para as dez colunas; 6.375 RPM está fora da faixa de 300–6.000 RPM do
gerador atual. São fronteiras do algoritmo e uma conversão candidata
do eixo, sem calibração física da roda ou do oscilador. Teste:
`Sab80C517.FiatRpm7b32SegmentsAllRawValues`.

Na revisão `A/A+`, o consumidor homólogo começa em `32ADh`: consulta
`70AAh→7B32h` e `70ACh→7B3Eh` por `533Ch`, calcula o deslocamento da
linha com passo `0Ah` e chama `53E6h` com o diretório
`70A2h→7ED9h/7F15h/7F51h`. O seletor `57h` é aplicado em `52EBh`.
Os trechos de código `3295h..32D7h`, `52EBh..5308h`,
`533Ch..53A8h` e `53E6h..5429h` são byte a byte iguais em
`A/A+/S37/S36`; o teste estático confere também ponteiros e cabeçalhos.
Isso sustenta a geometria **6×10** nas quatro imagens, mas o segundo
eixo não é uniforme: o primeiro byte do cabeçalho `7B3Eh` é `AFh`
em `A/A+` e `7Dh` em `S37/S36` (e G/S88). O código da revisão A escreve
`AFh` por caminhos adicionais, inclusive `3302h..3326h` com comparação
de `46h` e `47h`. Portanto, transferir a interpretação de compensação
de alimentação de G para A/A+ seria incorreto sem rastrear `AFh`.

O teste `Sab80C517.SixRom7b3eSecondAxisSegmentsAllRawValues` executou
o leitor original de cada revisão para cada byte `00h..FFh` do eixo
selecionado. Os seis inícios de linha em valor bruto são
`0,141,188,220,243,251` em G/A/A+;
`0,133,180,212,235,243` em S88; e
`0,119,166,198,221,229` em S37/S36. Em A/A+ apenas o seletor de
IRAM muda (`7Dh→AFh`); em S88/S37/S36 ele permanece `7Dh`, mas o último
incremento de `7B3Eh` sobe de `05h` para `0Dh`/`1Bh`. Assim, mesmo
quando as células de `7ED9h` são iguais entre G e S88, seus índices
de linha podem divergir para a mesma entrada bruta. A escala física
de `7Dh` e a faixa natural de `AFh` continuam sem validação.

Na ROM Fiat G, `4044h` carrega `IRAM[61h]` e `IRAM[64h]`, chama `5367h`
e grava `IRAM[7Dh]` em `404Bh`. A execução isolada desses opcodes com
66 pares de entradas e divisor não nulo confirmou
`7Dh = min(255, floor(256 × 61h / 64h))`. Com `64h=0`, os mesmos
opcodes retornaram `7Dh=FFh` para todos os onze numeradores testados,
incluindo zero. Esse é um resultado digital da rotina, não prova que
`64h=0` ocorra durante operação normal.
Em execução completa a 1.000 RPM, ADC1 bruto 40/80/160 produziu
`61h=28h/50h/A0h`, `64h=5Ah` e `7Dh=71h/E3h/FFh`. São contagens
digitais; a conversão para tensão física depende da entrada e do
circuito ainda não validados. Teste:
`Sab80C517.Fiat4044StoresSaturatedQ8RatioInIram7d`.

Com a ROM G intacta, 1.000 RPM, ADC1=47 e estímulo ADC4 de 10 bits em
zero, `64h` permaneceu zero durante 2,4 milhões de ticks; `404Bh`
gravou `7Dh=FFh`. `31h` terminou em `10h` e a largura baixa mediana
modelada de P5.0 foi 1.861 ticks. A regressão
`test_adc4_zero_reaches_saturated_7d_in_g` reproduz esse cenário.
Alcançabilidade no emulador não demonstra que a entrada ADC4 física
atinja zero na ECU.

O cálculo local é homólogo nas seis ROMs: G/S88 executam
`4044h→5367h`, e A/A+/S37/S36 executam `4101h→542Ah`.
Com `64h=0` e numeradores `00h`, `01h`, `2Fh` e `FFh`, os opcodes
originais das seis imagens gravaram `7Dh=FFh`. O teste
`Sab80C517.SixRomZeroDivisorSaturatesIram7d` fixa endereços, chamadas
e resultados. A/A+ selecionam `AFh`, não `7Dh`, no cabeçalho da matriz
`7B3Eh`; portanto essa saturação não demonstra uma mudança de linha
nessas duas revisões.

Com `64h=5Ah`, a primeira fronteira de linha (`7Dh=141` na G e
`7Dh=133` na S88) corresponde a ADC1 bruto 50 e 47, respectivamente,
quando `61h` acompanha ADC1. Na ROM G original a 1.000 RPM e ADC7=63,
ADC1=47 deu `7Dh=85h`, `31h=3Fh` e P5.0 baixo mediano de 7.306 ticks.
Entregar somente `0Dh` no retorno do `MOVC` original em `5289h/7B45h`
deu `31h=32h` e 5.792 ticks, preservando `7Dh` e a ROM G. Com ADC1=50,
o mesmo contraste foi `31h=32h`/5.792 contra `2Eh`/5.326 ticks.
Cada braço consultou `7B45h` 230 vezes; o trace manteve o byte original
`05h` como valor da ROM. Este ensaio isola a contribuição digital desse
byte no perfil Fiat emulado; não identifica tensão, bico ou bobina física.
Teste: `VariantTraceTests.test_adc1_7b45_row_boundary_changes_ram31_and_p5_in_g`.
Capturas: `build/ma17-analysis/variants/adc1_7b45_{47,50}_{control,donor}/`.

Um teste de execução **isolada** das ROMs originais começa em `32ADh`
e para após a escrita de `31h` em `32D4h`. Com `47h=28h`, `57h=0`
e o outro eixo fixo, `AFh=20h→C0h` na A muda `31h=9Ah→42h`;
trocar apenas `7Dh` não muda `9Ah`. Em S37, trocar apenas `AFh` não
muda `31h=78h`, enquanto `7Dh=20h→C0h` muda `78h→1Bh`.
O teste `Sab80C517.AlcoholCodeMatrixSecondAxisUsesHeaderSelectedIramByte`
executa os opcodes originais e fixa esses seis resultados. Ele confirma
a seleção efetiva do endereço indicado pelo cabeçalho `7B3Eh` e seu
efeito sobre `31h`; não estabelece quais valores de `AFh` ocorrem em
operação natural nem a função física do eixo na revisão A.

Outro teste inicia diretamente em `3302h` e para em `3329h` nas ROMs
A e S37, sem executar o restante da ECU. A constante original em
`734Eh` é `0Ah` nas duas. Com `46h=28h`, os valores `47h=28h/29h/31h/32h`
produziram `AFh=FFh/00h/00h/FFh`, respectivamente. Nesse caminho,
`AFh=00h` corresponde à diferença `47h−46h` de 1 a 9; a igualdade e
o limite de 10 levam a `FFh`. O teste anterior confirmou que `00h` e
`FFh` geram resultados distintos em `31h` na ROM A. Outros caminhos,
inclusive `34C4h` e `34D5h..34F0h`, também escrevem `AFh`; portanto
essa janela não define sua distribuição durante operação completa.

Um segundo produtor está em `3473h..34B3h`, byte a byte igual nas quatro
ROMs da família A. O `JB F1` em `3479h` testa `PSW.1` (bit `D1h`),
**não** `B.1` (bit `F1h`). Com `PSW.F1=0`, `46h=28h` e `AFh=55h`,
`47h=34h` preserva `AFh`, enquanto `47h=35h` o zera: o limite
consultado é `ROM[734Dh]=0Ch`. Com `PSW.F1=1`, a rotina usa
`ROM[734Eh]=0Ah`; no mesmo estado preparado, `47h=28h` grava `FFh`
e `47h=29h` preserva `55h`. O teste
`Sab80C517.AlcoholCodeUpperAfRpmComparisonUsesTwoRomBounds` executa
os opcodes originais nas quatro ROMs e para antes da guarda seguinte
em `34B3h`. A frequência e a ordem dessas escritas no boot natural
continuam desconhecidas.

No teste contínuo `3473h→34B3h→34CFh`, ainda com `46h=28h`,
`47h=35h` e `PSW.F1=0`, o zero em `AFh` sobreviveu até a saída
`3562h` quando `22h.1=1`, `@B3h.4=0`, `2Fh.0=1` e `B.0=1`.
Limpar apenas `22h.1` desviou para `34C4h`, que substituiu `AFh`
por `FFh` antes de sair em `35CFh`. Os opcodes das quatro ROMs
produziram o mesmo contraste no teste
`Sab80C517.AlcoholCodeUpperAfZeroSurvivesOnlyOpenGate`.
Esse ensaio demonstra a guarda local em estado preparado; não prova
que o zero alcance a matriz em uma execução natural.

Para testar o consumidor, executei em seguida `32ADh..32D6h` nos
mesmos opcodes, retendo apenas `AFh` e igualando `47h=35h`,
`7Dh=20h`, `57h=0` e os demais estados da etapa. A/A+ gravaram
`31h=BAh` com `AFh=00h` e `31h=37h` com `AFh=FFh`.
S37/S36 gravaram `31h=98h` nos dois braços, coerente com o cabeçalho
`7B3Eh` que usa `7Dh` nessas revisões. O mesmo teste de regressão fixa
os quatro resultados. A transição entre as etapas foi preparada pelo
teste; a sequência de chamadas natural e a função física seguem abertas.

O grafo estático do assembly A situa as duas etapas na mesma rotina:
`31B4h` salta a `3296h`, o consumidor começa em `32ADh` e um caminho
posterior alcança o produtor em `3473h`. Na janela `3296h..34D4h`,
há caminho estático `32ADh→3473h`, mas nenhum `3473h→32ADh`.
Logo, `AFh` atualizado ali só pode afetar uma consulta posterior após
nova entrada ou outro caminho externo; o teste em duas etapas simula
essa possibilidade, sem provar que ela ocorra no boot real. O arquivo
`build/ma17-analysis/variants/alcohol_af_matrix_path.json` registra
o filtro de PCs. O grafo não modela a pilha de retorno das chamadas;
regressão: `ControlFlowGraphTests.test_alcohol_monolithic_assembly_maps_matrix_and_af_writer`.

Antes desse cálculo, o trecho de inicialização `0C48h..0C58h` das
quatro ROMs A grava `upper IRAM[AFh]=FFh` e `lower IRAM[7Dh]=C0h`.
Os opcodes originais executados isoladamente confirmam ambos os bytes
em `Sab80C517.AlcoholCodeStartupSeedsUpperAfAndIram7d`. Esse é o
estado semeado pelo trecho, não uma medição do primeiro acesso natural
à matriz; escritas intermediárias ainda podem alterá-lo.

O caminho adicional de `34D5h..34F2h` soma `B0h` a `AFh` somente quando
`AFh≠FFh`, `26h.5=0` e `2Dh.5=1`, saturando em `FFh`. Um teste isolado
em A e S37 confirmou soma `20h+10h→30h`, saturação com `EFh+10h`
ou `F8h+10h`, e ausência de soma quando uma dessas flags bloqueia.
Porém, `B0h` é preenchido em `3D43h..3D55h` por `7040h→7552h`:
os dez bytes `7552h..755Bh` são `FFh` nas **seis** ROMs. Executar essa
consulta nas ROMs A/S37 com `4Eh=00h/04h/48h/88h` produziu `B0h=FFh`.
Com esse valor, a soma permitida leva `AFh` a `FFh` no teste isolado.
Os índices efetivamente usados em operação completa e o papel físico
dessa região toda `FFh` continuam desconhecidos; índices fora da faixa
testada podem alcançar o bloco adjacente.

Um contrafactual preservou a ROM G ou S88 em execução e entregou ao
`MOVC` somente os 60 bytes homólogos de `7ED9h..7F14h` da ROM A.
O script aceitou a doadora por hash entre as seis imagens inventariadas
e confirmou o ponteiro big endian `70A2h→7ED9h` nas duas ROMs.
Com 1.000 RPM, `ADC7=63`, seletor `57h=0` e 2,4 milhões de ticks:

| Código ativo | `31h` próprio→A | P5.0 baixo mediano, próprio→A | CC3 `14h:15h`, próprio→A |
| --- | --- | ---: | ---: |
| G | `10h→32h` | 1861→5792 ticks | 1422→1422 |
| S88 | `10h→32h` | 1921→5852 ticks | 1422→1422 |

Os mesmos valores de `31h` e P5 ocorreram em G com TPS `40/95`, embora
a mediana CC3 dessa condição seja diferente. O trace bruto `MOVC` reteve
os bytes da ROM ativa; a substituição ocorreu só no valor retornado à
CPU. Isso isola um efeito causal da matriz da A sobre `31h` e a largura
P5.0 **modelada** no código G/S88. O código da A não foi executado;
portanto, o ensaio não prevê sua saída completa nem prova a função
elétrica de P5.0. Relatórios:
`build/ma17-analysis/variants/matrix_7ed9_donor/`.

Uma intervenção cruzada na mesma ROM G testou a **mediação por
`IRAM[31h]`**. O override opcional atua imediatamente antes de `0490h`,
onde `MOV direct,direct` copia `31h` para `B` no cálculo do Timer 1;
ele não altera a tabela nem a escrita natural de `31h` em `32B8h`.
Com as mesmas entradas e 2,4 milhões de ticks:

| Tabela entregue por MOVC | `31h` natural | `31h` lido em `0490h` | P5.0/P5.1 baixo mediano |
| --- | --- | --- | ---: |
| G | `10h` | `10h` | 1861 ticks |
| G | `10h` | `32h` forçado | 5792 ticks |
| A | `32h` | `32h` | 5792 ticks |
| A | `32h` | `10h` forçado | 1861 ticks |

O cruzamento reproduz e reverte integralmente a diferença P5 **neste
estado emulado**: `7ED9h` altera `31h`, que media esse efeito no cálculo
do Timer 1. A linha A usa apenas os 60 bytes da matriz como retorno
`MOVC`; o código ativo e o hash continuam sendo G. Outros estados,
escritas de `31h` e a ligação elétrica de P5 às bobinas não são
inferidos por esse teste. Regressão:
`VariantTraceTests.test_7ed9_p5_effect_is_mediated_by_ram31_at_timer1_read`.
Capturas cruzadas: `build/ma17-analysis/variants/ram31_mediation_7ed9_*/`.

O probe em `0490h` continha uma restrição inicial a `47h=28h`, de modo
que tentativas antigas em outras RPMs registravam o override no relatório,
mas **não o aplicavam**. `FirmwareProbes.cpp` agora permite o override
quando `47h≠00h` e registra o byte de RPM real. A escolha de `0490h`
segue o opcode `MOV direct,direct` da ROM G e o manual *SAB 80C517*,
seção *Instruction Set*, p. 217. Após recompilar o emulador, repeti o
cruzamento sem alterar a ROM:

| RPM | `47h` | `31h` G→A | P5 G→A, natural | P5 G+`31h` A / A+`31h` G |
| ---: | --- | --- | --- | --- |
| 750 | `1Eh` | `0Ch→2Eh` | 1940→7181 ticks | 7181 / 1940 ticks |
| 2.000 | `50h` | `1Fh→41h` | 1789→3769 ticks | 3769 / 1789 ticks |

P5.0 e P5.1 deram as mesmas medianas em cada caso, com período fixo
de 79.200/29.700 ticks para 750/2.000 RPM. O resultado confirma a
mediação pelo valor **lido** de `31h` nesses três pontos de RPM testados,
sem provar a conexão elétrica das saídas. Regressão:
`VariantTraceTests.test_7ed9_ram31_mediation_at_750_and_2000_rpm`.

O código em `0490h..049Bh` explica uma parte da escala: carrega `31h`
em `B`, desloca `69h` à direita com carry limpo e subtrai `B` de `A`.
No regime estabilizado de 1.000 RPM, `69h=9Ah`: para `31h=10h/32h`,
o trace pré-`049Bh` mostrou `A=3Dh/1Bh`, com o carry igual nos dois
casos. Em seguida, `04A0h` troca `B` por `1Eh` e `04A3h` multiplica
`A×B`; portanto, a diferença no acumulador continua pelo cálculo,
mesmo quando a flag `22h.7` é igual. O trace é opcional via
`MA17_TRACE_RAM31_GATE=1` e registra `0490h/049Bh` com a referência ao
*Instruction Set* do SAB80C517 no código do probe.

Uma varredura G a 1.000 RPM, `ADC7=63`, período P5 de 59.400 ticks,
com override somente antes de `0490h`, deu:

| `31h` entregue | `00h` | `10h` | `20h` | `32h` | `40h` | `50h` | `80h` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P5 baixo mediano, ticks | 989 | 1861 | 3725 | 5792 | 7424 | 9286 | 14849 |

Para `10h..80h` nesses pontos, `período×31h/512` aproxima a largura
com erro absoluto até 12,5 ticks; `31h=00h` apresenta um piso de 989
ticks. A fórmula é **ajuste empírico local**, não uma reconstrução exata
de todas as operações de multiplicação, saturação e temporização da ROM.
Em 750 RPM, a mesma aproximação erra até 84 ticks, reforçando esse
limite. Regressão: `VariantTraceTests.test_ram31_p5_scaling_has_low_value_floor`.
Capturas: `ram31_response_1000_{00,20,40,50,80}/` e
`ram31_gate_trace_1000_{10,32}/`.

O gráfico `build/ma17-analysis/variants/ram31_p5_response.png` mostra
essas medianas e o resíduo do ajuste, destacando o piso em `00h`.
Para regenerar as capturas e o gráfico a partir da ROM G original:

```sh
for value in 00 10 20 32 40 50 80; do
  MA17_OVERRIDE_RAM31="$value" MA17_OVERRIDE_RAM57=0 MA17_ADC_CH7=63 \
    python3 tools/trace_ma17.py --no-kline-inject --crank-immediate \
      --rpm 1000 --stop-ticks 2400000 --seconds 30 \
      --output-dir "build/ma17-analysis/variants/ram31_response_1000_$value"
done
MPLCONFIGDIR=/tmp /usr/bin/python3 tools/plot_ma17_ram31_response.py
```

O script confere hash da ROM, estímulo, duração, override e período antes
de plotar. Os pontos `10h/32h` usam capturas equivalentes do trace de gate
quando presentes; o gráfico expressa ticks emulados, não duração elétrica
das bobinas.

Com `RAM[57h]=1/2` forçado, o mesmo consumidor `3291h→5323h` escolheu
`7F15h` ou `7F51h`. A busca com RPM e ADCs padrão leu 462 bytes por
matriz; 418 leituras ficaram no par dominante (209 por célula) e 44
atingiram células transitórias no início. Em `7F15h`, o par dominante foi
`7F4Ah/7F4Bh`: `26h/40h` em G/S88 e `0Ch/15h` tanto em A quanto em
S37; S36 compartilha os bytes dessa matriz com S37. Em `7F51h`, foram
`7F86h/7F87h`: `26h/40h` em G/S88 e `4Ch/66h` em A.

| Código ativo | Seletor | Doadora da matriz | `31h` próprio→troca | P5.0 baixo mediano, próprio→troca |
| --- | ---: | --- | --- | ---: |
| G | 1, `7F15h` | A ou S37 | `33h→10h` | 5908→1861 ticks |
| S88 | 1, `7F15h` | A ou S37 | `33h→10h` | 5970→1921 ticks |
| G | 2, `7F51h` | A | `33h→59h` | 5908→10334 ticks |
| S88 | 2, `7F51h` | A | `33h→59h` | 5970→10394 ticks |

As comparações mantiveram o seletor e o código ativo fixos. A mediana
CC3 ficou em 1422 ticks em todos esses pares. Assim, também nessas
matrizes as células alteradas contribuem causalmente para `31h` e P5
**no emulador**, sob modos forçados. Não há observação de seleção natural
de `57h=1/2`, nem execução do código A/S37. Capturas:
`build/ma17-analysis/variants/matrix_7f_donor/`.

Um ensaio separou a diferença **interna da ROM A** entre `7ED9h` e
`7F15h`: o código G e `57h=1` ficaram fixos, e a matriz doadora foi
`A:7F15h`. As três células da última linha efetivamente lidas que
diferem do banco `A:7ED9h` foram substituídas apenas no retorno de
`MOVC`: `7F48h=0Ah→2Ch`, `7F4Ah=0Ch→2Eh` e `7F4Bh=15h→37h`.
As 462 leituras da matriz ocorreram nos dois casos. O resultado final
`31h` mudou de `10h` para `32h` e a largura baixa mediana modelada de
P5.0 de 1.861 para 5.792 ticks; a mediana de CC3 permaneceu em 1.422.
Assim, a faixa de `−34` bytes visível no
[mapa comparativo A:7ED9h/A:7F15h](../build/ma17-analysis/variants/matrix_plots/matrix_7ed9_a_vs_7f15_a.png)
tem efeito digital causal no caminho G testado. A seleção natural de
`57h=1`, o comportamento completo do código A e a ligação física de
P5.0 ainda não estão comprovados. Capturas:
`build/ma17-analysis/variants/7f15_a_bank{1_donor,0_cells}/`;
regressão: `AlcoholBankPairTests.test_last_row_bank_delta_reaches_ram31_and_modeled_p5`.
Uma auditoria dos opcodes originais das seis ROMs encontrou os únicos
`MOV 57h,#imediato` em `0B0Fh` (`00h`), no reinício cíclico
`3B94h` em G/S88 ou `3BC2h` em A/A+/S37/S36 (`00h`), e em
`601Dh` (`5Ah`, rotina de diagnóstico). Há ainda `MOV 57h,B` em
`6078h` no mesmo fluxo de diagnóstico. Nos traces completos atuais
G/S88 com dois degraus TPS, sem override e com hash do executável,
não houve transição de `57h`. Isso reduz a plausibilidade de seleção
natural de bancos 1/2 no caminho do motor ensaiado; escritas indiretas
e outros estados operacionais ainda impedem concluir inacessibilidade.
Regressão: `AlcoholBankPairTests.test_six_roms_direct_immediate_ram57_writers_are_zero_in_engine_code`.

Em ensaio **isolado do próprio código A/S37** (`32ADh..32D5h`), o
diretório `70A2h/70A4h/70A6h` foi selecionado por `57h=0/1/2`, sem
alterar as ROMs. Dentro da ROM A, `7F15h` difere de `7ED9h` apenas
nas nove últimas células; dentro de S37/S36, as duas fatias são
idênticas nos 60 bytes. O teste usa `47h=28h`, eixo secundário `20h`
(`AFh` na A, `7Dh` em S37):

| Código/ROM | `57h=0` | `57h=1` | `57h=2` | saída |
| --- | ---: | ---: | ---: | --- |
| A | `9Ah` | `9Ah` | `ECh` | `RAM[31h]` |
| S37 | `78h` | `78h` | `D8h` | `RAM[31h]` |

A igualdade A entre modos 0/1 nesse ponto não significa matrizes
equivalentes: com `47h=10h` e `AFh=FFh`, o mesmo código A produz
`31h=2Ch` no modo 0 e `0Ah` no modo 1. O teste automatizado varre
pares de `47h/AFh` e fixa esse primeiro par divergente. Trata-se de
execução parcial iniciada no consumidor; não demonstra quando a ECU
seleciona os modos 1/2 em operação normal.

Uma continuação isolada executa o código original de A e S37 em
`043Bh..0521h` após os resultados `31h=9Ah/78h` acima, mantendo
`36h:37h=011Dh` e varrendo `RAM[69h]` de `00h` a `FFh` com o restante
do estado inicial igual. A primeira divergência é em `69h=12h`:
`34h:35h=FFFFh` na A e `12FEh` na S37. Em `69h=FFh`, ambas convergem
em `C0FEh`, embora `22h.7` seja `0/1`. Isso demonstra dependência
local da recarga em algumas entradas e convergência em outras. O trecho
consumidor `043Bh..0521h` é idêntico nas duas ROMs; fornecer apenas o
`31h` da outra variante depois da interpolação permuta `FFFFh/12FEh`
em `69h=12h`. Isso isola `31h` como mediador local, mas não mostra que
`69h=12h` ocorra naturalmente nem identifica a saída física.
No subintervalo `69h=80h..A5h`, as recargas divergem em **todos** os
20 valores `80h..93h` e convergem em `94h..A5h`. O cruzamento de
`31h` também permuta o resultado em `69h=89h`. A ROM G já exibiu
valores de `69h` nessa faixa em outros ensaios; isso não valida a
distribuição natural de `69h` nem o perfil elétrico das ROMs A/S37.

O produtor de `69h` em G/S88 `3AE4h..3B07h` é byte a byte igual ao
trecho A/A+/S37/S36 `3B12h..3B35h`. Todas têm
`ROM[72A2h]=80h` e `ROM[72A7h]=A5h`. Executar os opcodes originais
das seis imagens em isolamento confirmou: com `2Bh.4=0`, `69h` recebe
`min(IRAM superior[8Ch],A5h)` nos exemplos `70h/89h/B0h`;
com `2Bh.4=1`, recebe `80h` para `8Ch=89h/B0h`. Portanto, o produtor
possui um caminho **possível** para `69h=80h`, dentro da faixa
discriminante da recarga. Não foi estabelecido quando a flag `2Bh.4`
está ativa nas variantes A/S37 em execução completa.

A origem da flag aparece no processamento serial: G/S88
`5058h..5095h` e A/A+/S37/S36 `511Bh..5158h` validam o contador em
XRAM `B9h` e o terminador `03h`, depois leem o **ID do frame** em
XRAM `BAh` para `R2`. Com
`R2=38h`, comparam `ROM[728Dh]=64h` a `RAM[47h]`; se
`47h<=64h`, escrevem `42h=08h` e ligam `2Bh.4`. Em teste isolado
dos seis códigos desde a validação do frame, `47h=64h` liga a flag;
`65h`, contador inválido ou terminador inválido levam a `42h=04h`
sem ligá-la. O frame `09h` alcança a instrução que a limpa. O scanner
de referência expõe `04h` como pedido de teste de atuador, mas não
expõe `38h`: os dois IDs não devem ser confundidos. O significado de
`38h` permanece desconhecido fisicamente. Em uma sessão PTY com a ROM G
original, 1.000 RPM e pedido `38h` após o handshake, o trace observou
`5058h→5078h→508Ah→5091h`: `RAM[2Bh]` passou de `20h` para `30h` e
`RAM[42h]` para `08h` no tick 8.926.104. No tick 8.929.751,
`3B06h` escreveu `RAM[69h]=9Ah→80h` com a flag ativa. A ECU respondeu
com frames `DBh` (dado `80h`) e `09h`; o significado físico desse retorno
não foi identificado. A cobertura foi obtida com `MA17_TRACE_SERIAL38=1`
e `MA17_TRACE_PC=1`, parada em 25 milhões de ticks. O efeito digital
confirma a rota serial nesta sessão emulada, sem provar sua função no veículo.
O ACK `09h` limpou `2Bh.4` em `5096h` no tick 9.038.753, e `3B06h`
restaurou `69h=80h→9Ah` no tick 9.042.366. Enquanto `69h=80h`, dois
pulsos baixos completos de cada latch P5.0/P5.1 mediram 1.484 ticks;
os pulsos imediatamente anteriores mediram 1.484/1.485. Os registros
de P5 mudaram `32h:33h/34h:35h` de `12FEh/8BFFh` para `2FFEh/A8FFh`
durante a flag e depois restauraram o par anterior. Os intervalos entre
bordas baixas consecutivas de P5.0 incluíram 59.400, 57.915, 59.400 e
60.886 ticks na transição: há um deslocamento de fase candidato, apesar
da largura baixa estável. O ensaio pareado abaixo testa a repetição
sem `38h`; a atribuição ao Timer 1 e a uma saída física segue aberta.

Execute `python3 tools/probe_ma17_serial38.py` para repetir automaticamente
o controle e o pedido; o script inicia emulador e cliente no mesmo espaço
PTY e requer a `.venv` com as dependências do `test_pty.py`.
Um par de execuções com esse script repetiu o ensaio
com atraso de cliente de 5 s, mesma ROM G e janela de 8–10 milhões de
ticks. O controle só com handshake teve 134 eventos de latch P5,
`69h=9Ah`, recargas `12FEh/8BFFh` e períodos entre bordas baixas
próximos de 59.400 ticks nos dois bits. O pedido `38h`
teve 134 eventos,
`69h=80h` transitoriamente, recargas `2FFEh/A8FFh` e períodos extremos
próximos de 57.915/60.885 ticks nos dois bits. As larguras
baixas permaneceram próximas de 1.484 ticks. Ambos tiveram 603 eventos
no caminho Timer 1, nos PCs `0223h/0252h/0286h/0298h`; somente o ensaio
com `38h` registrou o par `2FFEh/A8FFh` nesses eventos. O relatório
reproduzível
está em `build/ma17-analysis/variants/serial38_probe.json`; o par associa
a troca serial a uma mudança transitória de fase e recarga no modelo,
mas ainda não isola o bit `2Bh.4` do tráfego serial nem identifica os
pinos físicos. Pequenas variações no agendamento mudam alguns períodos
isolados entre execuções; o contraste de recarga e fase se repetiu.
No terceiro braço, o mesmo pedido `38h` atingiu `5091h` e o produtor
`3B06h` escreveu `69h=80h`, mas `MA17_OVERRIDE_RAM69=9A` forneceu `9Ah`
em `043Bh` antes do cálculo do Timer 1. As recargas ficaram apenas em
`12FEh/8BFFh`; ambos os bits P5 voltaram a períodos próximos de
59.400 ticks. Isso demonstra mediação digital pelo valor consumido em
`043Bh` no modelo. A intervenção escreve a própria `RAM[69h]` e
persiste até outra escrita do firmware, portanto não é uma substituição
puramente transitória do operando; a identidade física de P5 continua aberta.

Para repetir a sessão em dois terminais que compartilhem `/dev/pts`, inicie
o emulador abaixo e use o caminho `PTY pronto em:` que ele anunciar no
segundo comando. `--frame38-probe` confirma apenas a troca de frames;
as linhas `[SERIAL38-PATH]` e `[ENGINE-RAM]` confirmam o ramo e o efeito.

```sh
MA17_TRACE_SERIAL38=1 MA17_TRACE_RAM69=1 MA17_CRANK_RPM=1000 \
  MA17_STOP_TICKS=25000000 ./build/emu8051-tty \
  FiatTipo_MA17_dump_27c256.bin --8052
.venv/bin/python test_pty.py /dev/pts/X --frame38-probe
```

Sem injeção K-Line, o harness Fiat atual executou as ROMs originais G
(`a3473435…40f8e1f`) e S88 (`bfa59928…fdcbe28`) por 2,4 milhões
de ticks a 1.000 RPM, com a sonda opcional `MA17_TRACE_RAM69=1`.
Cada ROM teve 230 amostras no produtor `3B06h`, sem atingir o limite
de 2.000 eventos do probe. `2Bh.4` estava limpa em todas: flags
`20h/28h`. Os valores observados em `69h` foram `9Ah/9Ch/A2h` em G
e `89h/90h/99h/9Ch/A2h` em S88. Assim, S88 alcançou `89h` sem a
flag serial nesse cenário, mas nada disso demonstra os valores naturais
das ROMs A/S37. Os relatórios estruturados estão em
`build/ma17-analysis/variants/ram69_serial_flag_current_{g,s88}/execution.json`;
`ram69_producer_observation` distingue contagem, flag, valores e limite
de amostras.

Reprodução a partir da raiz do projeto (adicione `--firmware
'firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin'`
e troque o diretório de saída para `..._s88` no segundo ensaio):

```sh
MA17_TRACE_RAM69=1 python3 tools/trace_ma17.py --no-kline-inject \
  --crank-immediate --rpm 1000 --stop-ticks 2400000 --seconds 30 \
  --output-dir build/ma17-analysis/variants/ram69_serial_flag_current_g
```

Para verificar que o efeito de `7F15h` não depende só do ponto basal,
repetiu-se a troca G←A com `RAM[57h]=1`, `ADC7=63` e 2,4 milhões de
ticks. O SHA-256 da ROM ativa G permaneceu
`a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.

| Estímulo | Leituras `7F15h..7F50h` | `31h` próprio→A | P5.0 baixo mediano, próprio→A | CC3 mediana |
| --- | ---: | --- | ---: | ---: |
| 750 RPM, ADC1=130 | 462 | `27h→0Ch` | 6093→1940 ticks | 1422 |
| 2000 RPM, ADC1=130 | 462 | `52h→1Fh` | 4759→1789 ticks | 1422 |
| 1000 RPM, ADC1=40 | 836 | `D0h→7Fh` | 24136→14731 ticks | 1654 |

As leituras variam com a condição, mas a direção do efeito em P5.0 se
manteve nos três pares. O teste
`test_7f15_donor_effect_persists_across_rpm_and_adc1` reproduz os
resultados; os relatórios estão em
`build/ma17-analysis/variants/matrix_7f15_robustness/` (sufixo
`_allrpm` nos casos 750/2000 RPM). As capturas anteriores desses dois
RPMs, sem o sufixo, precedem a correção do escopo do seletor forçado e
não servem como evidência de ausência de acesso à matriz.

O catálogo curado [MA17_CALIBRATION_CATALOG.json](MA17_CALIBRATION_CATALOG.json)
registra 137 estruturas com hash de cada ROM, ponteiro quando há,
intervalo, formato conhecido, consumidor na gasolina, diferenças por imagem,
evidência estática/dinâmica, confiança e perguntas abertas. Um teste confronta
endereços, hashes e contagens de diferenças diretamente com os seis dumps.
O comando de comparação também gera `calibration_catalog_expanded.json`:
137 entradas × seis versões, cada uma com endereço, hash, bytes originais
e lista das células divergentes em relação a G. Cada delta e percentual
usa aritmética de bytes *u8* brutos; percentual fica nulo quando o byte
de G é zero. Essas diferenças não pressupõem escala física ou sinal.
O gerador recusa ROM cujo tamanho, hash, ponteiro ou contagem divirja
do catálogo curado; o teste automatizado verifica uma diferença da
tabela `7426h` e um caso com denominador zero em `7D26h`.
O inventário automático registra 116 regiões apontadas: 104 com cobertura
direta no catálogo, oito contidas em estruturas catalogadas e quatro ainda
provisórias. A cobertura de ponteiros não estabelece função física. Os eixos
`47h`, `6Fh`, `7Dh`, `62h`, `63h` e `4Eh` possuem vínculo
de código com variáveis internas, mas suas escalas e efeitos finais ainda
exigem prova.

Os ponteiros `7018h`, `701Ah` e `701Eh` levam a três curvas adjacentes de
10 bytes em `744Eh`, `7458h` e `7430h`. A rotina G/S88 em `4916h` usa
`T2CON.1` para escolher `701Eh` ou `7018h`; a homóloga A/A+/S37/S36 em
`49D3h` também pode escolher `701Ah` quando `T2CON.1=0` e `2Bh.7=1`.
Executar os opcodes originais das seis ROMs com `R5=3`, `R6=0` confirmou
os três ponteiros no `MOVC` e os bytes retornados em `R2`. Em rastros
completos G/S88, a curva `744Eh` foi lida naturalmente durante os ensaios
de ADC3; não se observou ainda acesso natural às outras duas curvas.
O processamento posterior pode gravar `4Dh` em G. A origem usual de
`R5/R6` na curva `744Eh` foi rastreada abaixo; o ramo alternativo e a
função física das curvas seguem abertos. Os deltas
entre ROMs estão no catálogo curado, e o teste
`Sab80C517.PostCoolantCurveSelectorUsesThreePointerSlots` conserva a
seleção das três curvas como regressão de leitura digital.

Dentro de cada ROM da família A, `744Eh..7457h` e `7458h..7461h`
são dez bytes iguais. Um teste com código original, `R5=9`, `R6=0` e
`XRAM[6Ch]=B0h` produziu o mesmo `4Dh` para os dois ponteiros:
`99h` em A e `7Fh` em S37. Essa equivalência tem uma borda: o
interpolador também lê a célula seguinte. Com `R5=9` e `R6=80h`,
ele usa `7458h` ou `7462h` como segunda célula e obtém `R2=5Bh/5Ah`
em A, `41h/40h` em S37; esses valores chegam a `4Dh` no estado isolado.
O último índice com fração não nula ainda não foi visto em um fluxo
natural da família A. As regressões
`AlcoholPostCoolantEqualCurvesGiveEqualIsolatedOutput` e
`AlcoholPostCoolantIndexNineFractionCrossesCurveBoundary` guardam as
duas condições sem atribuir função física às curvas.
Varreduras isoladas de todos os 256 bytes possíveis em `RAM[63h]`, nas
quatro ROMs A/A+/S37/S36, executaram o decodificador original
`4830h..483Ch`: `R5` nunca passou de 9 e, quando foi 9, `R6` era zero.
O escritor original `46B6h..46C6h`, varrido com os 256 valores de
`RAM[62h]`, também zerou a fração no seu índice terminal `R5=5` antes
de publicar `R5|R6` em `XRAM[F8:91h]`. Assim, esses dois produtores
locais não geraram a combinação `R5=9,R6≠0` que distingue as bases.
Outros escritores de `XRAM[91h]`, as guardas de seleção e um boot A
validado continuam fora desses ensaios. Regressões:
`AlcoholCodeRam63SegmentClampsIndexNineFraction` e
`AlcoholAirSegmentWriterKeepsTerminalXram91FractionZero`.
O boot original das seis ROMs deixa `F8:91h=AAh` no marco `PC0A3Ah`
após o autoteste de XRAM; em `PC0B30h`, depois da limpeza de partida,
o byte está `00h`. `SixRomXramSelfTestReachesCommonBootContinuation`
confere os dois valores. A janela do autoteste não é uma calibração de
controle nem prova que o ramo alternativo leu esse byte antes da limpeza.

O [manual SAB80C517](../SAB80C517.PDF), seção Timer 2, identifica
`T2CON.1` como `T2I1`: com `T2I1:T2I0=10/11`, o Timer 2 usa contador
externo ou função temporizada por `P1.7`; com `00/01`, fica parado ou
usa o clock interno. Em G/S88 a 1.000 RPM, `ADC0/6=40/95`,
`ADC3=20`, `ADC5=40`, `ADC7=63` e 5 milhões de ticks, `MOVC` leu
`744Eh/744Fh` 1.025/1.021 vezes por endereço, respectivamente, e
nenhuma célula de `7430h` ou `7458h`. Todas as amostras do probe
lambda nesse cenário deram `T2I1=0`. O teste
`test_post_coolant_curve_744e_is_naturally_read_with_t2i1_clear`
fixa hashes, acessos e estado do bit. Isso limita a seleção observada
nesse perfil. Uma auditoria das instruções classificadas nos seis
assemblies remontáveis encontrou somente cinco escritas em `T2CON` por
ROM: `MOV #85h` em 0AF6h, `ORL #85h` em 3B6Ch (G/S88) ou 3B9Ah
(A/A+/S37/S36), `MOV #00h` em 4ABCh ou 4B7Fh e 6320h, e `MOV #11h`
em 6334h. Os bytes são `75 C8 85`, `43 C8 85`, `75 C8 00`,
`75 C8 00`, `75 C8 11`; nenhum liga o bit 1. Também não há escrita
direta em `T2I1` entre essas instruções classificadas. A inicialização
`MOV #85h` limpa o bit, e o `ORL #85h` posterior apenas o preserva.
Assim, a seleção de `7430h`, `7516h`, `7534h`, `743Ah` e `7444h`
dependente de `T2I1=1` está comprovada em execução isolada, mas sua
entrada natural não aparece no código identificado nem nos rastros
testados. Código ainda não classificado ou outro modo de entrada da ROM
impedem declarar esses ramos impossíveis.
Capturas: `post_coolant_t2i1_natural_{g,s88}/`.

**Leitura da primeira célula não equivale a seleção do banco.** Em
partidas atuais G/S88 a 1.000 RPM, ADC3=220 e ADC7=63, por 2,4 milhões
de ticks, `5333h` leu `7430h` 20 vezes em cada ROM com `DPTR=7426h`,
`A=0Ah`; leu também `7534h` 582/581 vezes com `DPTR=752Ah`, `A=0Ah`.
Ambas são leituras da célula seguinte na interpolação de curvas
precedentes. `477Dh` registrou `4Eh=09h` e o ramo de substituição em
`47A3h` não foi visitado; aqui o índice é 9 e a fração `R6=00h`.
O interpolador multiplica a diferença entre células por essa fração,
explicando por que o byte seguinte é consultado mas não contribui para
o resultado nesse estado. Nenhuma das quatro capturas selecionou `DPTR=7430h` ou
`7534h` nesses eventos. Fornecer apenas os respectivos primeiros bytes
da A (`40h` e `62h`) nesses dois `MOVC` não mudou `IRAM[4Dh]`, `79h`,
`7Bh` ou as medianas de CC3 nas duas ROMs; o log confirmou ambas as
substituições e os hashes originais permaneceram iguais. O teste de
regressão também compara cada uma das 149 bordas CC3 por tick e nível:
controle e doação são idênticos em G e S88 nesse estado. Portanto os
acessos observados não demonstram efeito funcional dessas células neste
estado nem entrada natural nos ramos `T2CON.1=1`.
Capturas: `curve_boundary_{current,donor}_{g,s88}/`.
Regressão: `python3 -m unittest tests.test_ma17_curve_boundary`.

O auditor de fronteira agora aceita também as 39 curvas catalogadas com
dez células: `python3 tools/audit_ma17_matrix_boundaries.py --curve
--exclude-overrides`. No corpus atual, 1.236 relatórios passaram pelos
filtros de ROM e intervenção, 792 tinham `MOVC` habilitado, e 14 curvas
originais apresentaram leitura da posição imediatamente seguinte.
`curve_boundary_audit_corpus.json` preserva PC, DPTR, ROM, contagem e
exemplo de captura e reconhece o próximo item mesmo quando ele tem
outro formato, como `799Eh→79A8h`. Com filtro adicional para o
SHA-256 `2f06ac4d…26ecac32` do emulador após o novo probe, restam
dois relatórios, ambos com `MOVC`; o arquivo
`curve_boundary_audit_current.json` registra a leitura de fronteira
`799Eh→79A8h` em G/S88. Nas capturas a 1.000 RPM descritas acima,
`7458h` foi lido 582/581 vezes a partir de `DPTR=744Eh`, sem seleção
observada de `DPTR=7458h`. O corpus sem intervenções também não mostra
seleção direta de `7430h`, `7534h`, `74B2h` ou `7B14h`, embora leia
suas primeiras células a partir de bases anteriores. Em contraste,
`79BAh` tem tanto leituras de fronteira vindas de `79B0h` quanto
leituras com sua própria base. Esses resultados delimitam o corpus;
não provam que os bancos sem seleção observada sejam inacessíveis.

Na ROM G, `4773h` carrega `7002h→73D4h`; a rotina `5279h` lê o endereço
`63h` do cabeçalho e converte `IRAM[63h]` em segmento `R5` e fração
`R6` no nibble alto. `477Fh..47ABh` pode substituir esse par por um
valor de `XRAM[91h]` quando `IRAM[62h]>ROM[7264h]=6Eh`, há uma das
flags `28h.3/.4/.5` ou `29h.3`, e `XRAM[9Eh]` é não zero. Nesse ramo,
`R5=(XRAM[91h]+4)&0Fh` e `R6=XRAM[91h]&F0h`. Em duas partidas G de
2,4 milhões de ticks a 1.000 RPM, `ADC0/6=40/95`, `ADC5=40`,
`ADC7=63`, `ADC3=20/80` produziram respectivamente
`IRAM[63h]=14h/50h`, `R5:R6=00h:00h/03h:20h` em `477Fh`, preservados
em `47ACh`, `491Fh` e `532Fh`. O leitor `532Fh` acessou `744Eh=15h`
ou `7451h=33h`. `47A3h` não apareceu nos conjuntos completos de PCs
e `IRAM[62h]` estava abaixo do limiar `6Eh` no ponto amostrado. Isso
identifica o eixo **digital usual** nesses estados G, sem validar a
escala em °C nem o caminho alternativo nas demais revisões. Regressão:
`test_post_coolant_curve_744e_axis_comes_from_iram63_segment`; capturas
em `post_coolant_axis_adc3_{20,80}/`.

Ao elevar apenas `ADC2` para 220 no mesmo boot G, `IRAM[62h]=DCh`
ultrapassou `ROM[7264h]=6Eh` e o fluxo alcançou `4793h`. A segunda
guarda ainda desviou para `47ACh`: `28h.3/.4/.5` e `29h.3` estavam
zerados nas amostras, e `47A2h` (leitura `MOVX` de `XRAM[91h]`) nem
`47A3h` apareceram no conjunto completo de
PCs. Com `ADC3=20`, `R5:R6` continuou `00h:00h` e o leitor acessou
`744Eh=15h`. Três ensaios adicionais com `ADC2=220` e TPS
`40/95`, `120/180` e `180/247` também entraram em `4793h` sem chegar
à leitura de `XRAM[91h]`; `ADC2=160`, TPS `180/247`, teve o mesmo
resultado. O teste acima cobre `ADC2=220`, e os artefatos restantes
estão em `post_coolant_axis_alt_{idle,mid,wide,wide160}/`. Assim, o
limiar do ar é alcançável nesse modelo, mas a substituição do eixo
depende de flags cuja origem ainda deve ser rastreada.

Uma execução isolada dos **opcodes originais** em `477Fh..47ABh`
preparou `IRAM[62h]=80h`, `XRAM[F8:9Eh]=01h`,
`XRAM[F8:91h]=A3h` e `R5:R6=03h:20h`. Com `28h.3=0`, o salto em
`479Bh` evitou `MOVX` em `47A2h` e conservou o par. Com `28h.3=1`,
o código leu `A3h` e chegou a `47ACh` com `R5:R6=07h:A0h`, de acordo
com `R5=(A3h+4)&0Fh` e `R6=A3h&F0h`. O teste
`Sab80C517.FiatPostCoolantAxisCanSwitchToXram91WhenAirAndFlagsPermit`
fixa a fórmula e a guarda. Esse estado foi preparado; a origem natural
da flag e a função física de `XRAM[91h]` continuam desconhecidas.

Os limites brutos de `ADC3` deram um terceiro resultado. Com `ADC2=220`,
`ADC10_CH3=12` (byte alto `03h`) ou `ADC3=232` (`E8h`), a ROM G ligou
respectivamente `28h.4` em `464Ah` ou `28h.3` em `4656h`. Nas duas
partidas de 2,4 milhões de ticks, `IRAM[62h]=DCh` e `XRAM[F8:9Eh]=78h`
abriram as guardas: `47A2h` leu `XRAM[F8:91h]=34h` e `47ACh` recebeu
`R5:R6=08h:30h`. Porém, os mesmos bits desviaram em `490Bh` para o
valor fixo `ROM[727Fh]=2Eh`, lido por `MOVC` em `4912h` **511 vezes por
ensaio**. `491Fh` e todas as células `7430h..7461h` ficaram sem acesso.
Assim, a origem alternativa do par é naturalmente alcançável no modelo,
mas **não foi eixo ativo da curva `744Eh`** nesses estados. O prefixo
do leitor e `727Fh=2Eh` coincidem nas seis ROMs; o salto seguinte muda
com o layout da revisão. Testes:
`test_coolant_bound_flags_reach_xram91_but_bypass_744e` e
`test_post_coolant_fallback_constant_and_reader_are_homologous`.
Capturas: `post_coolant_axis_bounds_{low,high}/`. A função física do
valor `2Eh` e o significado da condição de falha seguem abertos.

O byte de substituição `XRAM[F8:91h]` também tem produtor rastreável.
`45F9h` carrega `708Eh→73C0h`; o cabeçalho `62 06` seleciona
`IRAM[62h]` e seis incrementos cumulativos (`31 1A 18 20 0F 18`).
Após `5279h`, `4608h` escreve `R5|R6` em `F8:91h` quando `T2I1=0`.
Em três boots G idênticos exceto por `ADC2=120/160/220`, com
`ADC3=232` e 1.000 RPM, `IRAM[62h]=78h/A0h/DCh` e a escrita de
`4608h` publicou `B0h/F1h/34h` perto do tick 13.800. A leitura de
`47A2h` converteu esses bytes em `R5:R6=04h:B0h/05h:F0h/08h:30h`.
O teste de RAM em `55A1h` e a limpeza em `0A51h` também escrevem
`F8:91h` no boot; o rastro distingue esses eventos do produtor de
controle em `4608h`. O diretório `708Eh`, os oito bytes da tabela e
o escritor são homólogos nas seis ROMs após normalizar a chamada
`5279h→533Ch`. Regressões:
`test_air_segment_73c0_and_xram91_producer_are_homologous` e
`test_air_segment_73c0_writes_xram91_before_fault_lookup`; capturas
`xram_f891_adc2_{120,160,220}/`. O scanner chama `62h` de temperatura
do ar; a ligação ADC2→`62h` é digital, e a identidade física e a escala
do sensor ainda não foram verificadas.

No mesmo perfil G, um teste cruzado isolou `MOVC PC52A2h/73C6h`
(`0Fh` original, `1Fh` injetado) da leitura `MOVX PC47A2h/F8:91h`.
Sem injeção, `F8:91h=34h`, `R5:R6=08h:30h` e a mediana de
`RAM[14h:15h]` na entrada de CC3 foi 1.505 ticks. Só fornecer `14h`
em `47A2h` preservou `F8:91h=34h`, mudou `R5:R6` para `08h:10h` e
manteve 1.505 ticks. Só trocar a largura em `73C6h` publicou
`F8:91h=14h`, produziu `08h:10h` e baixou a mediana para 1.491 ticks.
Com essa largura trocada, fornecer `34h` em `47A2h` restaurou
`08h:30h`, mas a mediana continuou 1.491 ticks. O efeito em CC3
ocorre antes ou fora dessa leitura específica de `F8:91h`; o produtor
em `5279h` também entrega `R5:R6` diretamente à chamada em `4612h`:
o interpolador em `5329h..5348h` usa esses registradores, e `461Ch`
publica seu `R2` em `XRAM[F8:02h]` quando `T2I1=0`. A continuação
desse caminho até `RAM[14h:15h]` ainda precisa ser demonstrada.
Os ponteiros `708Ah→73C8h` e `708Ch→73CEh` designam duas curvas de seis
bytes iguais nas seis ROMs. `RAM[2Fh].5` escolhe a primeira quando vale
um; ambas recebem índice `R5` e fração `R6` do segmentador de `RAM[62h]`
em `708Eh→73C0h`. Executar os opcodes originais das seis ROMs desde
`4609h` (G/S88) ou `46C6h` (A/A+/S37/S36), com `R5=1`, `R6=0` e
`T2I1=0`, leu `73C9h=85h` ou `73CFh=83h` e publicou o mesmo byte em
`F8:02h`. O teste `Sab80C517.Pointer708a708cBranchesFeedXramF802`
confirma a seleção e a escrita. A frequência natural de cada ramo,
o alcance do último índice e a função física de `F8:02h` seguem abertos.
O rastro posterior mostrou que `XRAM[F8:02h]` ficou em `97h` com
`73C6h=0Fh` e com a leitura substituída por `1Fh`, descartando uma
mudança desse byte como explicação neste estado. O outro consumidor
observado de `F8:91h` foi `MOVX PC564Ah`, dentro da rotina chamada em
`129Dh`, `154Fh` e `15D2h`. Um segundo cruzamento confirmou a mediação
por **essa** leitura: fornecer `14h` só em `564Ah`, mantendo `73C6h=0Fh`
e `F8:91h=34h`, reduziu a mediana CC3 para 1.491 ticks; fornecer `34h`
só em `564Ah`, com `73C6h` substituído por `1Fh` e `F8:91h=14h`,
restaurou 1.505 ticks. As larguras baixas modeladas de CC3 foram
6.009/5.953 ticks conforme a leitura efetiva em `564Ah`. A cadeia
digital passa, portanto, pelo byte produzido em `4608h` e consumido
em `564Ah` **neste perfil emulado**. O restante do caminho dessa rotina
até `RAM[14h:15h]` e o circuito de saída ainda precisam ser traçados.
Teste: `test_73c6_cc3_effect_is_mediated_by_f891_read_at_564a`;
capturas: `xram_f891_564a_{read14,width_read34}/`.
Lendo o endereço de retorno na pilha 8051, o mesmo boot mostrou três
chamadores de `564Ah`: `129Dh→12A0h`, `154Fh→1552h` e
`15D2h→15D5h`. Substituir `34h→14h` somente no primeiro reduziu a
mediana CC3 de 1.505 para 1.491 ticks; as outras duas substituições
isoladas mantiveram 1.505. Com `73C6h` experimental e `F8:91h=14h`,
fornecer `34h` apenas na chamada de `129Dh` restaurou 1.505 ticks.
Assim, a influência observada passa especificamente pela chamada em
`129Dh`. Logo após ela, o código consulta `7300h` e os ponteiros
`7008h/7004h`, e publica resultados em `RAM[49h]`, RAM **superior**
`[87h]` (escrita indireta `@R0`) e `RAM[4Ah:4Bh]`.
No rastro estável de 21 passagens, fornecer `F8:91h=14h` só nessa
chamada mudou `R5:R6=08h:30h→08h:10h`, RAM superior `[87h]` de
`5Bh→5Ah` e `RAM[4Ah:4Bh]` de `91h:91h→8Ah:8Ah`. `RAM[49h]`
permaneceu `40h` nas passagens estáveis. O diretório `7008h` aponta
para a curva de dez bytes `7426h`; `7004h` aponta para a curva de dez
bytes `7412h`, idêntica nas seis ROMs. A primeira produz o byte em
RAM superior `[87h]`, a segunda os bytes em `4Ah:4Bh`. Ambas são
candidatas intermediárias. O isolamento por `MOVC` distinguiu seus
efeitos no perfil testado: substituir somente `742Fh=60h` por `5Ah` na leitura
`5333h` produziu RAM superior `[87h]=5Ah`, manteve `4Ah:4Bh=91h:91h`
e reduziu a mediana CC3 para 1.491 ticks. Substituir somente
`741Bh=BEh` por `98h` produziu `4Ah:4Bh=8Ah:8Ah`, manteve `[87h]=5Bh`
e CC3 em 1.505 ticks. No cruzamento inverso, fornecer `F8:91h=14h`
na chamada `129Dh` e `742Fh=6Ah` restaurou `[87h]=5Bh` e CC3 em
1.505 ticks, enquanto `4Ah:4Bh` continuou `8Ah:8Ah`. As larguras
baixas modeladas de CC3 acompanharam 6.009/5.953 ticks. Isso apoia
a mediação pela curva `7426h→RAM superior [87h]` **nesse estado
emulado**, sem estabelecer a função física da curva nem a fiação do pino.
O código de `1562h` usa `[87h]` antes de `1644h`, que publica
`R3:R2` em `RAM[59h:5Ah]`; `1D60h` carrega esse par, e `1ED3h`
publica `R3:R2` em `RAM[14h:15h]`. No mesmo par de ensaios,
o byte baixo mais frequente de `59h:5Ah` na entrada de `1D4Bh`
foi `9Dh→8Fh` (99 visitas por braço); em `1DD8h`, `R2` foi
`9Dh→8Fh` (100 visitas), e em `1ED3h`, `R2` foi `E1h→D3h`
(100 visitas). As regressões verificam essas etapas e a mediana
de `RAM[14h:15h]`. Isso sustenta a cadeia digital de calibração até
o agendamento CC3; a unidade física e a carga ligada ao pino seguem
sem identificação.
Na ROM S88, que preserva `7008h→7426h` e os dez bytes da curva,
o mesmo perfil de 1.000 RPM/ADC2=220/ADC3=232 repetiu a mediação:
`742Fh=60h→5Ah` apenas no `MOVC` mudou RAM superior `[87h]`
de `5Bh→5Ah`, o `R2` predominante em `1DD8h` de `51h→44h`,
a mediana de entrada CC3 de 1.429→1.416 ticks e a largura baixa
modelada de 5.705→5.653 ticks. Fornecer `F8:91h=14h` só para a
chamada de `129Dh` reproduziu esses resultados; fornecer também
`742Fh=6Ah` no `MOVC` restaurou `[87h]=5Bh`, `R2=51h`, 1.429 e
5.705 ticks, mantendo `4Ah:4Bh=8Ah:8Ah`. Isso repete a causalidade
digital em uma segunda imagem, com valores absolutos próprios da S88.
Regressão: `test_7426_cc3_mediation_repeats_in_s88`; capturas:
`s88_7426_{base,cell,read14,rescue}/`.
O contraste entre revisões também foi testado sem trocar código: A/A+
guardam `6Ah 70h` em `742Eh:742Fh`, contra `5Ah 60h` em G/S88.
Fornecer apenas esses dois bytes como retorno dos `MOVC` originais
`532Fh/742Eh` e `5333h/742Fh` manteve `R5:R6=08h:30h` e
`RAM[4Ah]=91h`, mas elevou RAM superior `[87h]` de `5Bh→6Bh` nas
duas ROMs receptoras. Em G, o `R2` predominante em `1DD8h` passou
`9Dh→F1h`, a mediana de entrada CC3 `1.505→1.589` ticks e a largura
baixa modelada `6.009→6.345`. Em S88, foram `51h→A0h`,
`1.429→1.508` e `5.705→6.021`. Os hashes das ROMs G/S88 ficaram
intactos; o teste verificou os dois overrides. É um efeito causal
dessas células no perfil de borda `ADC3=232`, não uma medida de
combustível, de tempo físico do injetor ou do funcionamento natural de A.
Regressão: `test_a_cells_change_cc3_in_g_and_s88_at_fixed_adc_state`;
capturas: `7426_A_cells_{G,S88}/`.
Com `ADC3=80`, o caminho consultou outro par da mesma curva:
`7429h:742Ah=1Ah:1Dh` em G/S88, versus `2Ah:2Dh` em A/A+.
Nos rastros de G e S88, todas as amostras de `477Fh` tinham
`RAM[28h]=00h` e `RAM[63h]=50h`; a chamada de `129Dh` usou
`R5:R6=03h:20h`, compatível com o eixo `IRAM[4Eh]` sem o desvio
de `F8:91h`. Fornecer só as duas células A/A+ elevou RAM superior
`[87h]` de `1Ah→2Ah`, mantendo `RAM[4Ah]=0Fh`. Em G, o `R2`
predominante em `1DD8h` mudou `1Bh→6Fh`, a mediana de entrada CC3
`863→947` ticks e a largura baixa modelada `3.441→3.777`.
Em S88, os números foram `F1h→40h`, `821→900` e `3.273→3.589`.
Esse segundo cenário mostra efeito da diferença de calibração também
sem as flags de falha `28h` no ponto observado. Os tempos não são
unidades físicas do bico nem identificam a ligação elétrica de CC3.
Regressão: `test_a_cells_change_cc3_with_clear_coolant_fault_flags`;
capturas: `7426_normal_adc3_80_{base,G_donor,S88_base,S88_donor}/`.
Com os mesmos ADCs e flags `28h=00h` observadas, a resposta persistiu
em 750 e 1.500 RPM. As leituras `MOVC` permaneceram em
`7429h/742Ah`, 17 vezes por endereço a 750 RPM e 13 vezes a 1.500;
o resultado estável em RAM superior `[87h]` foi `1Ah→2Ah` nos quatro
contrastes, enquanto os tempos absolutos dependeram da ROM e da rotação:

| ROM | RPM | Mediana `RAM[14h:15h]`, original → células A | CC3 baixo modelado, original → células A |
| --- | ---: | ---: | ---: |
| G | 750 | 1.044 → 1.146 ticks | 4.165 → 4.573 ticks |
| G | 1.500 | 644 → 704 ticks | 2.565 → 2.804 ticks |
| S88 | 750 | 900 → 987 ticks | 3.589 → 3.937 ticks |
| S88 | 1.500 | 721 → 788 ticks | 2.873 → 3.141 ticks |

As larguras baixas medianas de `P5.0` e `P5.1` permaneceram iguais
entre controle e doação nos três RPMs: G `1.863/1.861/1.824` ticks
em 750/1.000/1.500; S88 `1.863/1.921/1.823`. Os testes verificam
ambos os canais. Essa separação temporal no modelo favorece investigar
CC3 e P5 por caminhos distintos, ainda sem atribuir cargas físicas.
O teste `test_a_cells_effect_persists_at_750_and_1500_rpm` fixa
hashes, endereços lidos, flags, saída da curva e tempos; capturas:
`7426_rpm_{G,S88}_{750,1500}_{base,donor}/`. O resultado reforça o
efeito digital da diferença de calibração em três rotações, sem definir
a função física de CC3.

Com os mesmos ADCs, a leitura de `7429h/742Ah` continuou em 2.000,
3.000 e 4.000 RPM (12, 11 e 10 vezes por endereço, respectivamente).
Nos pontos observados em `477Fh`, `RAM[28h]=00h`; `129Dh` continuou
com `R5:R6=03h:20h`, e a doação das células A mudou RAM superior
`[87h]` de `1Ah→2Ah`, sem mudar `RAM[4Ah]=0Fh`:

| ROM | RPM | Mediana `RAM[14h:15h]`, original → células A | CC3 baixo modelado, original → células A |
| --- | ---: | ---: | ---: |
| G | 2.000 | 534 → 582 ticks | 2.124 → 2.316 ticks |
| G | 3.000 | 399 → 434 ticks | 1.584 → 1.724 ticks |
| G | 4.000 | 337 → 365 ticks | 1.325 → 1.437 ticks |
| S88 | 2.000 | 633 → 691 ticks | 2.520 → 2.752 ticks |
| S88 | 3.000 | 536 → 585 ticks | 2.133 → 2.328 ticks |
| S88 | 4.000 | 515 → 561 ticks | 2.025 → 2.209 ticks |

As larguras medianas de P5.0/P5.1 continuaram iguais dentro de cada
par controle/doação. Os hashes originais também permaneceram iguais.
Regressão: `test_a_cells_effect_persists_at_2000_to_4000_rpm`;
capturas: `7426_highrpm_{G,S88}_{2000,3000,4000}_{base,donor}/`.
O resultado amplia o contraste digital aos seis RPMs planejados, sem
identificar a carga física de CC3/P1.3 ou dos dois pinos P5.

Com rotação fixa de 1.000 RPM e `ADC2=220`, outra varredura de `ADC3`
selecionou pares diferentes da curva `7426h`: `7427h/7428h` para
`ADC3=40` (`R5:R6=01h:B0h`) e `742Bh/742Ch` para `ADC3=160`
(`05h:E0h`). Em ambos os estados, as amostras no PC `477Fh` tinham
`RAM[28h]=00h`. Doar apenas o par da A/A+ consultado em cada estado
elevou RAM superior `[87h]` em `10h` e manteve `RAM[4Ah]`:

| ROM | ADC3 | `[87h]` | Mediana `RAM[14h:15h]` | CC3 baixo modelado | P5.0/P5.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| G | 40 | `08h→18h` | 740→809 | 2.948→3.225 | 1.861→1.861 |
| G | 160 | `36h→46h` | 1.155→1.241 | 4.609→4.953 | 1.861→1.861 |
| S88 | 40 | `08h→18h` | 704→770 | 2.804→3.069 | 1.921→1.921 |
| S88 | 160 | `36h→46h` | 1.097→1.179 | 4.377→4.705 | 1.921→1.921 |

Todos os tempos são ticks emulados. A intervenção é digital em G/S88;
não representa a execução natural de A/A+ nem comprova a ligação física
de CC3 ou dos pinos P5. Regressão:
`test_a_cells_effect_at_two_other_adc3_segments`; capturas:
`7426_adc3_sweep_{G,S88}_{40,160}_{base,donor}/`.
Regressão: `test_7426_output_mediates_f891_cc3_effect_in_g`;
capturas: `path_129d_{742f_5a,741b_98,read14_742f_6a}/`.
Regressão de rastro no teste da chamada `129Dh`;
capturas: `path_129d_{base,read14}/`.
Regressão: `test_f891_cc3_effect_uses_129d_caller_of_564a`;
capturas: `xram_f891_564a_return_{12A0,1552,15D5}/` e
`xram_f891_564a_return_12A0_restore/`.
Isso **não** identifica o pino CC3 como bico nem estabelece a função
física de `73C6h`. Teste:
`test_73c6_width_and_f891_read_have_separate_cc3_effects`.
Capturas: `xram_f891_{adc2_220,73c6_wider,read_14,width_read_34}/`.

Para isolar o efeito desse byte na condição `ADC3=E8h`, quatro execuções
G mantiveram a ROM e os ADCs idênticos: controle, substituição `MOVC`
por seu próprio `2Eh` (controle simulado), por `00h` e por `80h`, somente
em `PC4912h/727Fh`. As leituras brutas ainda registraram `2Eh` e o hash
da ROM não mudou. A primeira escrita de `49ADh` em `IRAM[4Dh]` foi
`2Eh/2Eh/19h/80h`. O `00h` é elevado ao limite `ROM[7279h]=19h` pela
rota `4951h` condicionada por `P4.7`; a função física desse pino segue
desconhecida. Nas 229 visitas estáveis a `233Bh`, `R2` virou
`45h/45h/25h/BAh` e alcançou `2580h`. A mediana da entrada CC3 ficou
em 1.505 ticks e a largura baixa mediana modelada de `P5.0` em 1.861
ticks nos quatro braços. A regressão
`test_post_coolant_727f_fallback_reaches_4d_and_fixed_point` fixa o
efeito interno e os controles; capturas `post_coolant_727f_{base,sham,zero,high}/`.
Não há efeito temporal dessas duas saídas demonstrado neste estado.

No mesmo estado G, uma doação controlada substituiu **somente os
retornos `MOVC` do intervalo de dez bytes `744Eh..7457h`** pelos bytes
da ROM A, com o
ponteiro `7018h→744Eh` e ambos os hashes verificados. `49ADh` mudou
`IRAM[4Dh]=19h→2Fh`; doar a curva idêntica de S88 manteve `19h`.
O leitor original `22F3h` copiou `4Dh` para `R2`. Nas 484 passagens
por `2320h→233Bh` de cada cenário, os opcodes `MUL AB`, rotação e
saturação coincidiram com
`R2_saida=min(BAh, R2_entrada+floor(A_2320×R2_entrada/128))`;
`A_2320=RAM[49h]` nas 968 amostras. Na primeira passagem após um milhão
de ticks, `R2_saida` foi `2Dh→56h`, e o valor chegou a `2580h` com
`P2=F8h`, `R1=42h`. As medianas de P5.0 e do agendamento CC3 foram
iguais nos controles e na doação A: 1.861 e 625,5 ticks brutos,
respectivamente. As 58 escritas em `F8:0Ch` conservaram a mesma
sequência de valores e terminaram em `B6h` nos dois cenários; houve
apenas uma diferença de dois ticks em uma escrita tardia. Isso confirma
efeito **interno** da curva até o cálculo de `R2`, sem efeito isolado
nessas duas medianas nem função física
atribuída. A regressão é
`test_744e_donor_changes_4d_and_fixed_point_consumer`; capturas:
`post_coolant_744e_{baseline,donor_a,donor_s88}/` e
`post_coolant_744e_path_{baseline,donor_a}/`.

Um trace opcional de `MOVX @Ri`, com `P2=F8h`, comparou também os
destinos `F836h/F837h` da rota em `2606h..263Dh`. Controle G e doação
A produziram as mesmas 492 mudanças de valor, com os mesmos PCs
escritores; apenas os ticks de algumas escritas variaram. Portanto,
nessa condição, a alteração interna de `R2` não mudou esses dois
estados XRAM. A regressão acima verifica a sequência; capturas em
`post_coolant_744e_xram_{baseline,donor_a}/`.

Em outro estado, o efeito da mesma curva alcançou a saída **modelada**
`CC3/P1.3`. Com G a 3.000 RPM, ADC0/6=40/95, ADC3/5/7=20/40/63 e
2,4 milhões de ticks, doar apenas os dez retornos `MOVC` de `744Eh`
da ROM A mudou `RAM[4Dh]` de `19h` para `2Fh` e elevou os pulsos CC3
observados de 103 para 228; a largura baixa mediana mudou de 1.129
para 1.150 ticks. Substituir somente a leitura `MOV R2,4Dh` em `22F3h`
por `2Fh` no G original reproduziu 228 pulsos e 1.150 ticks; substituir
essa leitura por `19h` no braço doador restaurou 103 pulsos e 1.129
ticks. As bordas dos braços correspondentes diferiram no máximo dois
ticks, e o hash da ROM ativa permaneceu G nos quatro casos. O controle
leu `ROM[7310h]` 123 vezes, ativou `26h.7` depois do tick 1.156.306 e
parou de gerar bordas CC3; a doação A não leu `7310h` e manteve
`26h.7=0` nas decisões rastreadas. Forçar `R2=2Fh` suprimiu as leituras
de `7310h`; forçar `R2=19h` na doação restaurou as 123 leituras.
Isso confirma `4Dh→R2` como mediador digital da alcançabilidade desse
ramo e dos pulsos nesse cenário; não identifica a função física da curva
nem confirma CC3 como o bico. O limiar físico conhecido de cut-off acima
de 1.500 RPM continua distinto dessa comparação emulada a 3.000 RPM.
Regressão: `test_744e_ram4d_read_mediates_cc3_pulse_count_at_3000_rpm`;
capturas `post_coolant_744e_3000_{control,donor_a,control_r2_2f,donor_r2_19}/`.
Decisões `1F9Bh..2054h` e `2D04h..2D51h` foram capturadas em
`post_coolant_744e_3000_decision_{control,donor_a}/`.

Um sweep pareado com os mesmos ADCs e 2,4 milhões de ticks mostrou
dependência de RPM, sem localizar ainda o ponto exato de transição:

| RPM solicitado | Pulsos CC3 G / doação A | Leituras de `7310h` G / doação A |
| ---: | ---: | ---: |
| 1.500 | 51 / 51 | 121 / 121 |
| 2.000 | 68 / 68 | 122 / 122 |
| 2.500 | 86 / 118 | 122 / 85 |
| 3.000 | 103 / 228 | 123 / 0 |

Reinicializações independentes e o mesmo hash G foram usados em cada
braço. Regressão: `test_744e_donor_cc3_branch_effect_depends_on_rpm`;
capturas `post_coolant_744e_{1500,2000,2500,3000}_{control,donor_a}/`.
O resultado descreve apenas essa combinação de ADC e harness Fiat; não
mede o limiar físico de cut-off nem a função da curva em outras condições.

O caminho intermediário foi isolado em G a 3.000 RPM. O código após
`2593h` grava `F8:31h` em `2796h`; o trace observou `07h→36h→54h`
no controle e `07h→60h→7Eh` com a doação A. Substituir somente a
leitura de `RAM[4Dh]` em `22F3h` trocou também esses valores gravados,
apoiando a cadeia `744Eh→4Dh→R2→F8:31h`. Em `2A8Ch..2A91h`, o
firmware lê `F8:31h` e calcula `(R3−0Ah)−F8:31h`. Perto do tick 266
mil, `R3−0Ah=76h`: o controle subtrai `54h` sem carry; o doador
subtrai `7Eh` com carry e toma `JC 2A45h`. Fornecer `7Eh` só na
leitura de `F8:31h` em `2A8Ch` ao controle reproduziu 228 pulsos CC3,
zero leituras de `7310h` e ausência de `2C49h`; fornecer `36h` à
mesma leitura no doador restaurou 103 pulsos, 123 leituras e `2C49h`.
Uma substituição em outro leitor de `F8:31h`, `33A9h`, não trocou o
ramo neste ensaio. Isso identifica a comparação em `2A8Fh` como
mediadora do estado digital, sem estabelecer o significado elétrico de
CC3 ou a escala física de `744Eh`. Regressão:
`test_744e_f831_comparison_changes_branch_reachability`; capturas
`post_coolant_744e_3000_{xram31_*,branch_*,control_xram31_60,donor_xram31_36,control_xram31_2a8c_60,donor_xram31_2a8c_36}/`.

O desvio em `2A91h` muda a alcançabilidade de uma transição posterior.
No controle, `2B42h` apareceu uma vez no tick 1.146.773 com
`24h=8Eh`, `27h=04h`; os opcodes seguintes ligam `27h.3` e
`24h.5`. A primeira entrada em `2C49h` ocorreu no tick 1.146.823
com `24h=AAh`, `27h=0Eh`, e o `MOVC` leu `7310h`. Com a doação A,
nenhum dos dois PCs foi alcançado nos primeiros 2,4 milhões de ticks.
Forçar `F8:31h=7Eh` na leitura
`2A8Ch` no G também impediu ambos nessa janela; forçar `36h` na
doação restaurou ambos. Assim, a sequência
`F8:31h→2A91h→2B42h→27h.3/24h.5→2C49h`
tem evidência estática e dinâmica no cenário testado. O estado que
leva de cada passagem por `2A45h` à entrada eventual em `2B42h`
ainda requer rastreamento temporal mais fino. Capturas:
`post_coolant_744e_3000_flags_{control,donor_a}/`.
No controle, `F8:39h` passou de `20h` para `2Fh` no tick 1.146.722 e
para `2Eh` no tick 1.146.760; `2B38h` leu então um byte com
`ACC.6=0`, `ACC.5=1` e seguiu para `2B42h`. O doador não entrou em
`2B38h` durante os 2,4 milhões de ticks e conservou `F8:39h=0Fh`
até depois de 2,2 milhões de ticks. Essas diferenças mostram o estado
acumulado antes do gate; não isolam `F8:39h` como causa independente.
Capturas: `post_coolant_744e_3000_xram39_{control,donor_a}/`.

A extensão das mesmas partidas até **5 milhões de ticks** mostrou
que a doação A **atrasa**, mas não elimina, essa sequência:

| Primeira ocorrência | G, tick | G com curva A, tick | Atraso, ticks |
| --- | ---: | ---: | ---: |
| `2AC7h` (`24h=0Ah`) | 317.153 | 2.344.920 | 2.027.767 |
| `2AF9h` (`24h=0Ch` logo depois) | 839.577 | 2.866.953 | 2.027.376 |
| `2B42h` (`27h.3`/`24h.5` logo depois) | 1.146.773 | 3.174.451 | 2.027.678 |
| `2C49h` (entrada da leitura `7310h`) | 1.146.823 | 3.174.501 | 2.027.678 |

As diferenças de atraso entre as quatro etapas ficaram abaixo de 500
ticks, indicando que a maior mudança está no início dessa progressão
de estado, não no tempo entre suas etapas. `26h.7` foi observado ligado
nos ticks 1.156.306/3.183.656; a última borda CC3 ocorreu nos ticks
1.155.750/3.175.552. Em 5 milhões de ticks, G e doação A tiveram
103/307 pulsos CC3 modelados e 377/179 leituras de `7310h`.
O atraso de `2B42h` equivale a cerca de 2,05 segundos na escala de
990.000 ticks/s do harness. Isso descreve a guarda **digital** nesse
estado; não mede a duração física do cut-off do bico. Regressão:
`test_744e_donor_delays_guard_without_removing_it`; capturas
`post_coolant_744e_3000_long_{control,donor_a}/`.

O início tardio acompanha a queda de `F8:31h` até o valor da comparação
em `2A8Fh`: `R3−0Ah=76h`. No G, `2796h` gravou `54h` em `F8:31h`
no tick 265.886 e `2A91h` apresentou carry limpo no tick 266.070.
Com a curva A, o byte desceu de `7Eh` até `76h` no tick 2.201.240;
`2A91h` só então apresentou carry limpo, no tick 2.201.429. A
diferença entre esses primeiros carries limpos explica grande parte
do atraso observado, mas a entrada em `2AC7h` ocorre ainda depois:
51.083 ticks no G e 143.491 no braço doador. O teste longo fixa esses
marcos sem editar a ROM.

O restante vem do contador de quatro bits em `F8:39h`. A rotina original
`550Dh..5570h`, chamada em `2AB3h`, lê esse byte, atualiza o nibble
baixo e devolve o contador em `A`; `2AB7h` só avança quando `A=0`.
Antes da divergência, ambos já haviam contado de `0Fh` até `06h`.
No doador, o carry em `2A91h` levou a `2A45h`, cuja escrita em
`2A4Bh` restaurou `F8:39h` de `06h` para `0Fh` no tick 266.076.
No G, `555Bh` continuou `06h→05h` no tick 266.120. Quando a
comparação do doador voltou a passar, `555Bh` retomou `0Fh→0Eh`
no tick 2.201.473. O primeiro retorno `A=0` em `2AB7h` veio nos
ticks 317.141/2.344.908, seguido da entrada em `2AC7h`.
Isso explica a diferença de espera restante como reinício do
contador digital, sem atribuir unidade física ao nibble.
Regressão: `test_744e_donor_restarts_xram39_nibble_countdown`;
capturas `post_coolant_744e_3000_xram39_{control,donor_a}/`.

No mesmo estado de ADC e 3.000 RPM, doar apenas o primeiro retorno
`MOVC` (`PC532Fh`, `ROM[744Eh]`, `15h→2Fh`) reproduziu a doação dos dez
bytes da curva em 5 milhões de ticks: 307 pulsos CC3 modelados, 179
leituras de `7310h` e primeira passagem por `2B42h` nos ticks
3.174.449/3.174.451. As 614 bordas CC3 pareadas tiveram o mesmo nível
e diferiram em no máximo dois ticks; a última coincidiu. Doar apenas
`ROM[744Fh]` (`1Ch→36h`) manteve o perfil G: 103 pulsos, 377 leituras
de `7310h` e primeira passagem por `2B42h` no tick 1.146.773.
Isso isola a primeira célula como suficiente **nesse estado digital**;
outras células e estados ainda podem ter efeitos próprios. A relação
com o cut-off físico acima de 1.500 RPM segue não demonstrada.
Regressão: `test_744e_first_cell_alone_reproduces_long_guard_delay`;
capturas `post_coolant_744e_3000_long_cell{744e,744f}/`.

No bloco G/S88 `47ACh..47CEh` e no homólogo A/A+/S37/S36
`4869h..488Bh`, cinco curvas de 10 bytes são interpoladas pelo mesmo
leitor. `2Fh.5` e `T2CON.1` selecionam `7038h`, `7094h` ou `703Ah`
para gravar `IRAM[79h]`; `T2CON.1` seleciona `707Ch` ou `70CAh` para
`IRAM[7Bh]`. O teste
`Sab80C517.CoolantFollowupCurvesSelectIram79And7BAcrossSixRoms`
executa os opcodes originais em todas as seis ROMs, confere cada ponteiro
no `MOVC` e os dois destinos em RAM. No índice isolado `R5=3,R6=0`,
A/A+ produzem valores `22h` maiores nas cinco curvas; S37/S36 usam o
código da família A, mas conservam os valores G/S88. Isso separa a
alteração das tabelas da revisão de código nesse estado. A distribuição
natural dos índices e o significado físico permanecem em investigação.
Os blocos de opcodes consumidores são idênticos nas seis ROMs:
`7Bh` multiplica fatores em G `1CB7h` (A-code `1CD3h`) e `79h`
participa de outra cadeia em G `1D02h` (A-code `1D1Eh`). Com os
outros fatores fixados em `80h`, o índice 3 das curvas `752Ah` e
`750Ch` altera, respectivamente, `R1=08h→0Ah` e `B=10h→15h` de
G/S88/S37/S36 para A/A+. O teste
`Sab80C517.Iram79And7BCurvesFeedOriginalMultiplyChains` reproduz
esses dois resultados nas ROMs originais. Naquele ensaio isolado,
o efeito em uma saída temporizada não foi medido.
Em execução natural com 1.000 RPM, ADC2=100, ADC3=80, ADC7=63 e
1,6 milhão de ticks, G/S88 leram `7523h/7524h` (`IRAM[79h]`) e
`752Dh/752Eh` (`IRAM[7Bh]`) em 379/378 pares por curva. Nenhuma das
outras três curvas do grupo foi lida nesse cenário. O teste
`test_iram79_7b_curves_are_naturally_read_in_g_and_s88` verifica os
endereços, valores, PCs de `MOVC` e hashes das ROMs. Capturas:
`build/ma17-analysis/variants/iram79_7b_natural_{g,s88}/`.

### Curva `752Ah` e pulso CC3 após liberação do TPS

O ponteiro big endian `707Ch→752Ah` aponta para dez bytes em cada
ROM. Num degrau **modelado** de ADC0/6=`180/247→40/95` no tick
3.274.600, com 1.000 RPM e ADC1/2/3/4/5/7=`130/140/34/90/110/63`,
G e S88 leram `752Bh/752Ch` 798/796 vezes cada, respectivamente.
Doar apenas os dez bytes originais A dessa curva aos `MOVC` ativos
mudou `RAM[7Bh]=73h→95h` nas duas revisões, mantendo cada hash da ROM.
Em 69 passagens por `1CB7h`, `RAM[7Ah]` ficou não nula naturalmente;
na última, `7Ah=8Ch`, `F8:01h=72h` e `F8:FBh=FFh`. O produto em
`1CDFh` mudou `B=0Eh→12h`.

Nas 129 entradas do agendador CC3, intervalos `RAM[14h:15h]=0000h`
passaram de 2 para 12 em G e de 4 para 12 em S88. Os inícios de
pulso **no modelo** passaram de 127→117 e 125→117, respectivamente;
a mediana global do intervalo CC3 permaneceu 1.104 ticks em G.
No G, a entrada 107 passou de `00CAh` para `0000h`.
Fornecer só `752Bh=95h` no `MOVC 532Fh` deixou `7Bh=93h`, mas
reproduziu os 12 intervalos zero e 117 inícios de pulso da curva
completa. Fornecer só a célula adjacente `752Ch=9Ch` no `MOVC 5333h`
deixou `7Bh=76h`, produziu 4 intervalos zero e 125 inícios.
Assim, ambas as células contribuem à interpolação, mas têm impactos
distintos nesse estado. Os `MOVC` brutos ainda registram os bytes G.
Uma abertura oposta de TPS, com `RAM[7Ah]=00h`, também mudou
`7Bh=66h→88h`, mas deixou `R1=00h` em `1CDFh` e manteve a mediana
CC3. Isso identifica a guarda multiplicativa, sem declarar qual
grandeza física representa `7Ah` ou `7Bh`.

**Pino:** CC3/P1.3 é a saída temporizada do processador modelada
pelo emulador; `7Ah`, `7Bh` e `F8:01h` são memória, não pinos.
A ligação elétrica de CC3/P1.3 ao bico monoponto ou a outro terminal
da ECU ainda não foi verificada. Capturas:
`variants/752a_tps_step_{control,donor}/` e
`variants/752a_{,s88_}tps_release_{control,donor}/`, além de
`variants/752a_tps_release_cell752{b,c}/`.
Regressões: `test_752a_donor_reaches_cc3_on_natural_tps_release` e
`test_752a_donor_repeats_on_s88_tps_release`.

### Interação das curvas `7520h` e `752Ah` sem forçar RAM

Uma sequência de dois degraus ADC0/6, `40/95→180/247` no tick
800.000 e retorno a `40/95` no tick 3.274.600, com G a 1.000 RPM,
produziu simultaneamente `RAM[78h]=0Ch` quando `RAM[7Ah]` recebeu
`FEh` no tick 3.295.712. `7521h/7522h` e `752Bh/752Ch` foram
lidos 795 vezes cada. O teste fatorial forneceu os bytes A apenas
nos dois `MOVC` da primeira curva, nos dez bytes da segunda, ou em
ambas; o hash da ROM G permaneceu original.

| Bytes fornecidos | `79h` | `7Bh` | Mediana CC3 bruta | Intervalos zero | Inícios CC3 modelados |
|---|---:|---:|---:|---:|---:|
| Nenhum | `5Ch` | `73h` | 1.278 ticks | 2 | 127 |
| `7521h/7522h` | `7Eh` | `73h` | 1.342 ticks | 2 | 127 |
| Curva `752Ah` | `5Ch` | `95h` | 1.326 ticks | 12 | 117 |
| Ambos | `7Eh` | `95h` | 1.367 ticks | 10 | 119 |

O retorno alterado de `7520h` chega ao produto em `1D4Bh..1D57h`:
`A` em `1D57h` muda de `B4h` para `FCh` na primeira passagem após
a liberação. Os 69 rastros tardios dessa instrução repetem a diferença.
O efeito combinado **não é a soma simples** das duas intervenções:
com ambas, os intervalos 117 e 118, que `752Ah` isolada zerava,
voltam a `00CAh`. Esse resultado é digital e dependente do estado
simulado; não atribui unidades físicas às curvas.

**Pino:** as contagens são do modelo CC3/P1.3 do SAB80C517A.
`78h`, `79h`, `7Ah` e `7Bh` são RAM interna. A conexão de P1.3
à carga elétrica da ECU ainda precisa ser identificada.
Capturas: `variants/tps_double_step_1000_long{,_7520,_752a,_both}/`;
regressão: `CurvePairTests.test_two_tps_steps_make_both_multiply_factors_nonzero`.

Na S88, a mesma sequência também produziu `78h=0Ch` na primeira
escrita de `7Ah=FEh`, mas a resposta quantitativa foi diferente:

| Bytes fornecidos | Mediana CC3 bruta | Intervalos zero | Inícios CC3 modelados |
|---|---:|---:|---:|
| Nenhum | 1.566 ticks | 2 | 127 |
| `7521h/7522h` | 1.642 ticks | 2 | 127 |
| Curva `752Ah` | 1.606 ticks | 12 | 117 |
| Ambos | 1.698 ticks | 12 | 117 |

O limite `ROM[7218h:7219h]=00C8h` e os opcodes `1EA9h..1ECBh`
são iguais em G e S88. Numa passagem perto do tick 3,59 milhões,
o candidato G em `R3:R2` era `00C8h` com `752Ah` sozinha e
`00CAh` com ambas; a comparação exige que o candidato **supere**
o limite. Com `XRAM[F8:08h].7=0` e `F8:EFh=0`, o empate é zerado,
enquanto `00CAh` é preservado. Na S88, os candidatos respectivos
foram `00C1h` e `00C3h`, ambos abaixo do limite, de modo que os
intervalos 117/118 permaneceram zero. Os bytes da tabela são comuns
entre G e S88; a diferença vem do estado calculado anteriormente.
Capturas: `variants/s88_tps_double_step_{control,7520,752a,both}/`;
regressão: `CurvePairTests.test_s88_pair_stays_below_original_cc3_bound`.
O destino elétrico de CC3/P1.3 continua não demonstrado.

Para localizar a diferença anterior ao limite, mantivemos a ROM S88
original e entregamos as quatro células A das curvas `7520h/752Ah`
somente nas leituras `MOVC` alcançadas. Depois substituímos, uma de
cada vez, os retornos de `7580h` e `7B45h` pelos bytes G. O mesmo
estímulo ADC e a mesma janela de quatro milhões de ticks foram usados.

| Retorno adicional à S88 | Candidato `R3:R2` em `1EA9h` | Intervalos zero | Inícios CC3 modelados | Intervalos 117/118 |
|---|---:|---:|---:|---:|
| Nenhum | `00C3h` | 12 | 117 | `0000h` |
| G `7580h=10h` | `00EAh` | 8 | 121 | `00EAh` |
| G `7B45h=05h` | `00C3h` | 12 | 117 | `0000h` |
| G `7581h` | `00A4h` | 16 | 113 | `0000h` |
| G `7580h` + `7581h` | `00CAh` | 10 | 119 | `00CAh` |
| G `7580h` + `7B45h` | `00EAh` | 8 | 121 | `00EAh` |

Doar `7B46h` isoladamente conservou `00C3h` e 12 zeros; adicioná-la
a `7580h` conservou `00EAh` e oito zeros, embora `RAM[69h]` final
mudasse. O par `7580h+7581h` deu a mesma sequência de **131 valores**
`IRAM[14h:15h]` nas entradas CC3 da G com as duas curvas TPS doadas;
as medianas brutas também foram 1.367 ticks em ambas. Isso delimita
o efeito dessas calibrações no agendador neste estado. Os demais
estados de RAM e saídas P5 não são equivalentes, e o byte `7580h`
isolado não explica a diferença completa. Capturas:
`variants/s88_double_pair_{point,g7580,g7b45,g7580_g7b45,g7581,g7b46,g7580_g7581,g7580_g7b46}/`;
regressão: `CurvePairTests.test_s88_7580_byte_restores_late_cc3_intervals`.

Repetimos o mesmo estímulo TPS e as quatro células A a 1.500 e
3.000 RPM, preservando os hashes originais das ROMs. O par de retornos
G `7580h+7581h` na S88 igualou a sequência **capturada** de
`IRAM[14h:15h]` da G em ambas as rotações:

| RPM | Entradas CC3 capturadas | S88 original versus G: valores diferentes | S88 com `7580h+7581h` versus G | Mediana G/doação | Inícios modelados G/doação |
|---:|---:|---:|---:|---:|---:|
| 1.500 | 196 | 181 | 0 | 1.311 ticks | 179 |
| 3.000 | 200 | 197 | 0 | 1.326 ticks | 356 |

O trace guarda no máximo 200 entradas `CC3-ENTRY`; portanto, a
igualdade a 3.000 RPM cobre as **200 entradas capturadas**, não todos
os 356 pulsos modelados. A contagem de leituras `MOVC` das curvas
também difere em uma ou mais unidades entre braços, e `RAM[69h]`
final continua diferente. A evidência confirma uma equivalência
local de agendamento em três rotações testadas, sem estabelecer
equivalência global dos firmwares ou identidade elétrica do pino.
Capturas: `variants/{s88_1500_pair_point,s88_1500_pair_g7580_g7581,g_1500_pair_both,s88_3000_pair_point,s88_3000_pair_g7580_g7581,g_3000_pair_both}/`;
regressão: `CurvePairTests.test_s88_7580_and_7581_match_g_cc3_entries_at_other_rpms`.

Sem fornecer células da variante A, as ROMs nativas G e S88 mantiveram
o mesmo resultado central: doar à S88 apenas retornos `MOVC` G de
`7580h` e `7581h` igualou todos os valores `CC3-ENTRY` capturados
na janela inicial. As diferenças S88 nativa versus G foram 126/131,
191/196 e 197/200 valores, respectivamente a 1.000, 1.500 e
3.000 RPM; após a doação, foram 0 em cada janela. As medianas brutas
G/doação foram 1.278, 1.274 e 1.307 ticks. A 1.000/1.500 RPM,
as contagens de inícios CC3 modelados também coincidiram (127/189).

A 3.000 RPM, a doação dupla deixou **364** inícios modelados contra
**363** na G. Usando `MA17_TRACE_CC3_AFTER_TICK=2500000` para capturar
o fim da execução, encontramos uma única diferença nas 152 entradas
tardias: no tick 3.560.295, G tinha `IRAM[14h:15h]=0000h` e S88 com
doação dupla tinha `00CFh`. O novo filtro opcional
`MA17_TRACE_78XX_AFTER_TICK=3500000` mostrou o cálculo anterior em
`1EA9h`: `R3:R2=00C8h` na G e `00CFh` na S88, diante do limite
comum `ROM[7218h:7219h]=00C8h`. A G zera o agendamento quando o
candidato empata com o limite; a S88 preserva o valor maior.
Fornecer também os **14 retornos alcançados** da matriz G `7B46h`
à S88 eliminou essa diferença tardia, igualou os 152 valores
capturados e os 363 inícios modelados. Doar `7B45h=05h` não alterou
o resultado. `RAM[69h]` final passou de `67h` para `5Fh`, igual à G,
mas os histogramas P5.0 ainda diferiram. Assim, a equivalência é
específica das observações CC3 neste estado, não dos estados completos
da ECU. Capturas: `variants/{g_native_1000_pair,s88_native_1000_pair,s88_native_1000_g7580_g7581,g_native_1500_pair,s88_native_1500_pair,s88_g7580_g7581_native_1500_pair,g_native_3000_late_math_window,s88_native_3000_g7580_g7581_late_math_window,s88_native_3000_g7580_g7581_g7b46,s88_native_3000_g7580_g7581_g7b45}/`;
regressão: `NativeCalibrationPairTests.test_7b46_closes_one_late_cc3_difference_at_3000_rpm`.

Uma redução das 14 leituras `7B46h` identificou um par de células
na mesma coluna da matriz 8×15: `7B4Fh` (linha 0, coluna 9) e
`7B5Eh` (linha 1, coluna 9), lidas 132 vezes cada nesse cenário.
Os bytes S88 são `68h/63h`; G contém `60h/5Bh`.

| Retorno G adicional na S88 com `7580h+7581h` | `RAM[69h]` final | Candidato tardio em `1EA9h` | Entrada CC3 tardia | Inícios modelados |
|---|---:|---:|---:|---:|
| Nenhum | `67h` | `00CFh` | `00CFh` | 364 |
| `7B4Fh` isolada | `62h` | `00CFh` | `00CFh` | 364 |
| `7B5Eh` isolada | `64h` | `00CFh` | `00CFh` | 364 |
| Ambas | `5Fh` | `00C8h` | `0000h` | 363 |

As duas células juntas bastaram para igualar os 152 valores CC3
tardios da G. As quatro células de leitura mais frequente em outra
posição da matriz (`7BA9h/7BAAh/7BB8h/7BB9h`) não alteraram esse
evento; as demais seis leituras também não bastaram. O resultado
individual mostra que mudar `RAM[69h]` final **não basta**, por si,
para restaurar a comparação em `1EA9h`. A mediação exata entre
interpolação, estados intermediários e limite foi investigada abaixo.
Capturas: `variants/s88_native_3000_{7b4f_only,7b5e_only,7b46_lower,7b46_upper,7b46_hot,7b46_other}/`;
regressão: `NativeCalibrationPairTests.test_7b46_closes_one_late_cc3_difference_at_3000_rpm`.

O assembly original mostra `MOV A,7Ah` em `1CD4h`, seguido de
`MUL AB`. O vetor Timer 0 em `000Bh` leva à rotina `0630h`, que
escreve `RAM[7Ah]` em `07B3h`. No evento tardio, essa escrita muda
`8Dh→85h`. A ordem varia entre os braços:

| Braço | Leitura `1CD4h` | Escrita `07B3h` | `A:B` em `1CDFh` | `XRAM[F8:08h]` | Candidato `1EA9h` |
|---|---:|---:|---:|---:|---:|
| G nativa | tick 3.551.892, `8Dh` | 3.551.998 | `C5:0D` | `72h` | `00C8h` |
| S88 com `7580h+7581h` G | 3.552.010, `85h` | 3.551.997 | `FD:0C` | `73h` | `00CFh` |
| S88 mais `7B4Fh+7B5Eh` G | 3.551.892, `8Dh` | 3.551.998 | `C5:0D` | `72h` | `00C8h` |

Uma intervenção temporizada somente na **leitura** `MOV A,7Ah`
confirmou a mediação imediata. Fornecer `8Dh` à S88, mantendo
`RAM[7Ah]` armazenada em `85h`, fez `A:B=C5:0D`, candidato `00C8h`
e agendamento `0000h`. Fornecer `85h` à G no mesmo ponto produziu
`FD:0C`, `00CFh` e o agendamento extra `00CFh`. O override começa
após o tick 3.551.800 e a execução termina após o evento; a ROM não
é alterada. Isso demonstra que as duas células mudam o **momento da
leitura em relação à atualização pelo Timer 0** neste estado. Um
traço de PC limitado aos ticks 3.551.850–3.552.025 localiza a
preempção: G e S88 com as duas células G passam por `1CB7h` em
3.551.873, leem `7Ah` em `1CD4h` em 3.551.892 e entram no vetor
`000Bh` em 3.551.897. A S88 com apenas `7580h+7581h` G passa por
`1CB7h` em 3.551.877; entra no vetor em 3.551.896 enquanto o PC
está em `1CCFh`, antes de alcançar `1CD4h` em 3.552.010. O caminho
da ISR chega a `07B3h` em 3.551.995–3.551.998. Assim, as duas
células restauram a fase do fluxo principal suficiente para ler o
valor anterior à ISR. Numa segunda janela de 1.001 ticks,
3.550.900–3.551.900, G e S88 com as duas células G têm PCs idênticos
em todos os ticks; a S88 parcial já apresenta defasagem de quatro
ticks na maior parte do trecho. A origem inicial da defasagem é
anterior a essa janela. Na janela 3.274.000–3.275.000, G e S88 com
as duas células G também têm PCs idênticos nos 1.001 ticks; a S88
parcial corresponde predominantemente à G com deslocamento de
**dois ticks na direção oposta**. A defasagem, portanto, evolui
entre essas janelas e não é um atraso fixo por célula. O traço
registra PCs antes
de cada ciclo emulado; PC repetido representa ciclos da mesma
instrução, não execuções adicionais. Capturas:
`variants/{g_native_3000_race,s88_native_3000_race,s88_native_3000_race_lower,g_native_3000_7a85_read_window,s88_native_3000_7a8d_read}/`;
traços de PC: `variants/{g_pcwindow,s88_pcwindow,s88_lower_pcwindow,g_prephase,s88_prephase,s88_lower_prephase,g_release_pc,s88_release_pc,s88_lower_release_pc}/`;
regressão: `NativeCalibrationPairTests.test_7a_read_order_mediates_late_cc3_gate`.

Uma janela intermediária expõe o estágio diferente do fluxo
principal. A rotina original faz `SETB ET0` em `0578h`; o Timer0
pendente é atendido quando o PC está em `057Ah`, antes de concluir
o `RET` nesse endereço. Após a ISR, a execução volta a `057Ah` e
então retorna ao chamador. G e S88 com as
duas células G entram em
`000Bh` no tick 3.510.947, alcançam `07B3h` no 3.511.055 e retornam
pelo PC `057Ah` para `1CA5h` no 3.511.068. A S88 parcial entra no
vetor no 3.510.949, alcança `07B3h` no 3.511.057 e retorna pelo mesmo
PC para `5225h` no 3.511.070, ainda dentro da multiplicação chamada
em `1C9Dh`. Ela então executa `5227h`, retorna a `1CA0h` e passa
por `1CA0h–1CA4h` antes de alcançar `1CA5h` no 3.511.077.
O assembly original confirma essas instruções. O vetor **revela**
endereços de retorno já diferentes, não cria por si a defasagem.
A origem do estágio diferente antes da reabilitação de `ET0` continua
aberta. Capturas:
`variants/{g_7a_prev_pc,s88_7a_prev_pc,s88_lower_7a_prev_pc}/`.

**Comentários de sinais e pinos desta trilha:** `7580h`, `7B45h`,
`7581h` e `7B46h` são regiões de ROM lidas por `MOVC`;
`78h/79h/7Ah/7Bh`, `69h` e `14h:15h`
são RAM interna. ADC0/6 são canais **modelados** usados como estímulo
das duas pistas TPS; a associação de cada canal ao terminal físico
do chicote ainda não foi medida. `CC3` é o periférico de compare do
SAB80C517A e `P1.3/CC3` é o pino da **CPU** modelado para a saída
temporizada. `P5.0/P5.1` são outros pinos de saída da CPU modelados,
com histograma de pulsos distinto nesta comparação. A alteração de
inícios de pulso é observação nesse modelo;
não identifica o terminal externo da ECU, o estágio de potência nem
autoriza chamar a saída de bico ou bobina.

### Gráfico das curvas `750Ch` e `7520h`

O comando `/usr/bin/python3 tools/plot_ma17_curves.py --png` lê os seis
dumps originais, imprime seus SHA-256 e gera
`build/ma17-analysis/variants/curves_750c_7520.svg` e `.png`. O SVG
é gerado apenas com a biblioteca padrão; o PNG usa Matplotlib 3.6.3
do Python do sistema. Neste ambiente, `which python3` aponta para
`.venv/bin/python3`, onde Matplotlib não está instalado. Os dois
painéis exibem os dez bytes brutos por índice para G/S88/S37/S36 e
A/A+, com escala comum de 0 a 255. O SVG mostra endereço e byte em
hexadecimal ao passar o cursor sobre cada ponto. As linhas ajudam a
comparar os valores adjacentes; índice e valor bruto ainda não têm
unidade física demonstrada. A seleção efetiva das curvas depende do
estado `2Fh.5` e, para `750Ch`, também de `T2CON.1`.

O seletor `2Fh.5` deriva de um estado em `IRAM[3Dh]`: em G/S88 os bytes
originais `19D9h: E5 3D B4 02 00 B3 92 7D` fazem `MOV A,3Dh`,
`CJNE A,#02h,+0`, `CPL C`, `MOV 2Fh.5,C`. Assim, o bit vale 1
exatamente para `3Dh>=02h` sem sinal. O teste
`Sab80C517.FiatRam3dThresholdSelectsFlag2f5InOriginalRoms` executa a
sequência das duas ROMs com `3Dh=00h,01h,02h,03h,FFh`. Antes disso,
`186Dh` consulta `DPTR+21h` via `MOVC`; no caminho com `DPTR=7200h`,
`ROM[7221h]=4Bh` nas seis imagens, e `1889h/190Bh` podem gravar esse
resultado em `3Dh` sob guardas de estado.
Em quatro boots completos G/S88 a 1.000 RPM, ADC5=40, ADC7=63 e 1,6
milhão de ticks, o trace em `PC=19B6h` teve 152 amostras por caso.
Com ADC3=4, `3Dh` passou de `01h` a `4Bh` e `2Fh.5` passou de 0 a 1
em ambas as ROMs; com ADC3=80, ambos permaneceram `01h` e 0 nas 152
amostras. As capturas estão em
`build/ma17-analysis/variants/ram3d_selector_{adc3_4,adc3_80,s88_adc3_4,s88_adc3_80}/`,
obtidas com `MA17_TRACE_LAMBDA=1`, `--crank-immediate`, `--rpm 1000`,
`--stop-ticks 1600000` e sem injeção K-Line. O ponto `19B6h` antecede
a gravação do bit na mesma passagem; uma amostra `3Dh=4Bh, 2Fh.5=0`
é coerente com essa ordem. A relação causal entre o estímulo ADC3, as
guardas que carregam `3Dh` e a identidade física do estado ainda requer
investigação. Não atribuímos `2Fh.5` diretamente a um sensor.
Um trace adicional em G, com ADC3=4, capturou a sequência causal:
`PC=186Fh` executa `MOVC` com `DPTR=7200h`, `A=21h` e lê `7221h=4Bh`;
em `1870h` o acumulador vale `4Bh`; em `1889h`, `2Ch.4=1` permite
`MOV 3Dh,A`; em `19D9h`, `3Dh=4Bh` e `2Fh.5=0`; em `19E1h`, o bit já é 1.
S88 reproduziu a mesma sequência. Um contrafactual forneceu `01h`
somente ao retorno do `MOVC 186Fh/7221h`, mantendo os bytes e hashes
das ROMs originais. Em G/S88, `3Dh` permaneceu `01h`, `2Fh.5` ficou 0
e as leituras em `PC=532Fh` com `DPTR=750Ch` caíram de 88/89 para 0;
`DPTR=7520h` recebeu todas essas leituras. O trace bruto de `MOVC`
continuou registrando `7221h=4Bh`. Os pares estão em
`build/ma17-analysis/variants/ram3d_reload_{control,reload01}_{g,s88}/`.
O teste `test_7221_movc_reload_controls_750c_curve_selection` verifica
a origem, a troca de curva e os hashes em ambas as ROMs. Esse resultado
confirma o elo digital `7221h→3Dh→2Fh.5→seleção de curva` nos estados
testados; a origem física da condição `2Ch.4` permanece desconhecida.
O contraste ADC3=4/80 mostrou que `2Ch.4` fica ativo em ambos os casos;
sozinho, esse bit não explica a recarga. Com ADC3=4, o trace em
`17E8h` registrou `63h=04h`, `47h=28h`, `B.0=1` e carry zero:
`ROM[7227h]=2Ch` satisfaz a comparação com `63h`. O fluxo passa por
`182Dh`, reduz `3Ch` de `0Fh` até zero e alcança `186Fh`. Com ADC3=80,
`63h=50h`; a leitura adicional `ROM[7226h]=44h` encontra `47h=28h`,
`B.0=0`, e o carry em `1810h` permanece um. O fluxo volta a gravar
`3Ch=0Fh` em `1825h` sem atingir `182Dh/186Fh` nesses 1,6 milhão de
ticks. Os traces G estão em `ram3d_guard_adc3_{4,80}/`.
Um segundo contrafactual G/S88 manteve ADC3=4, mas forneceu `00h`
somente ao retorno de `MOVC 17D5h/7227h`. A leitura bruta continuou
`2Ch`; o caminho passou então por `17E1h/7226h=44h`, deixou `B.0=0`,
`3Dh=01h` e eliminou as leituras de `750Ch` em `532Fh`. O teste
`test_7227_bound_controls_ram3d_reload_and_750c_selection` cobre
ambas as ROMs e verifica seus hashes. Capturas:
`build/ma17-analysis/variants/ram3d_guard_7227zero_{g,s88}/`.
Isso estabelece, nos cenários testados, o encadeamento digital
`7227h/7226h→B.0→carry→3Ch→7221h→3Dh→2Fh.5→curva`.
Outras flags também entram no carry e podem bloquear esse caminho;
`63h` continua sendo uma variável de temperatura candidata, sem
conversão física validada.

Uma grade adjacente fixou TPS `ADC0/6=40/95`, ADC5=40, ADC7=63 e
1.000 RPM. Em G, ADC3=43/44/45 chegou a `IRAM[63h]=2Bh/2Ch/2Dh`;
`B.0` em `17E8h` foi 1/1/0. G e S88 repetiram a borda 44/45 com
`RAM[28h]=00h`. Nos primeiros 1,6 milhões de ticks, `2Eh.2=1`
ainda impediu a recarga em todos os casos. Em 24 milhões de ticks,
com ADC3=44, G/S88 leram `7221h` 1.324 vezes cada, alcançaram `186Dh`
pela primeira vez perto de 10,443 milhões de ticks e terminaram com
`F8:0Ch=FFh`. Com ADC3=45, não leram `7221h`, não alcançaram `186Dh`
na janela instrumentada e `F8:0Ch` permaneceu `80h`. O fator de RAM
superior `87h` chegou a zero nos dois casos, perto de 10,29/11,31
milhões de ticks em G; sua queda sozinha não explica a diferença.

O contrafactual G mudou somente o retorno de `MOVC 17D5h/7227h`:
fornecer `2Bh` com ADC3=44 retirou todas as leituras de `7221h` e
manteve `F8:0Ch=80h`; fornecer `2Dh` com ADC3=45 gerou 1.224 leituras
de `7221h`, primeira passagem em `186Dh` perto de 11,467 milhões de
ticks e `F8:0Ch=FFh`. O trace bruto conservou `ROM[7227h]=2Ch` e o
hash da ROM ativa. Isso atribui causalmente a borda digital à constante
`7227h` neste perfil, sem calibrar a temperatura física nem demonstrar
o estado de malha fechada de uma ECU real. Teste lento opcional:
`MA17_RUN_SLOW=1` com
`test_7227_boundary_controls_late_lambda_reload`; capturas sob
`ram3d_guard_adc3_boundary_{clean_*,override_*}/`.

Com ADC3=45, a comparação secundária em `17E1h` lê
`ROM[7226h]=44h`. A 1.700 RPM, `RAM[47h]=44h` e `B.0=0` em
`17E8h`; a 1.725 RPM, `47h=45h` e `B.0=1`. Fornecer somente `43h`
como retorno desse `MOVC` a 1.700 RPM liga `B.0`; fornecer `45h` a
1.725 RPM desliga `B.0`. As leituras brutas continuam `44h`, sem
alteração da ROM. Em 24 milhões de ticks, porém, nenhum desses dois
estados originais leu `7221h` ou alcançou `186Dh`, e `F8:0Ch` ficou
em `80h`. `26h.7` está ligado nas passagens tardias por `17F9h` e
também força o carry; portanto, cruzar a guarda de RPM isoladamente
não prova habilitação da correção lambda. Capturas:
`lambda_rpm_second_guard_adc3_45_{1700,1725}_24m/` e
`lambda_rpm_second_guard_adc3_45_override_{1700_43,1725_45}/`.
Outro estado de execução completa, com ADC3=4, ADC5=40, ADC7=63,
1.000 RPM e 2,4 milhões de ticks, selecionou `DPTR=750Ch` em G/S88:
`532Fh/5333h` leram `750Ch=53h` e `750Dh=5Dh` em pelo menos 280 pares.
`79h` terminou em `53h`. Fornecer somente o byte `75h` da ROM A no
`MOVC 532Fh/750Ch`, mantendo cada ROM ativa intacta, levou `79h` a
`75h` e `B` na entrada de injeção `1D4Bh` de `14h` a `1Ch` após 1,3
milhão de ticks. Nesse ponto `78h=00h` e o próximo `MUL AB` mascara
a diferença; CC3 permaneceu com mediana de 1170 ticks e P1.3 com
largura modelada de 4646,5 ticks. O teste
`test_750c_curve_natural_read_changes_iram79_without_cc3_effect`
reproduz o contraste. Isso confirma a leitura e o destino em RAM nesse
estado; não demonstra efeito em uma saída temporizada.
Em 6 milhões de ticks, G com ADC5=40 também manteve as medianas de CC3
e P5 inalteradas. Com ADC5=200, duas execuções G repetiram CC3
513→520,5 ticks e largura P1.3 2040,5→2070,5; S88 mostrou CC3
522→520 e P1.3 2076,5→2068,5. P5.0 não mudou dentro de cada par.
Esses sinais opostos entre ROMs, com `78h` ainda zero nas amostras de
`1D4Bh`, não identificam um efeito da multiplicação por `79h`.
Fixando `78h=80h` apenas na leitura em `1D4Bh`, o byte de `750Ch`
fornecido pela ROM A mudou a mediana CC3 de 1491→1591 ticks em G e
1493→1591 em S88; P1.3 passou de 5934,5→6347 e 5938,5→6346,5
ticks. P5.0 permaneceu igual em cada par. O teste
`test_750c_curve_changes_cc3_with_supplied_ram78_gate` reproduz esse
caminho digital condicional. Ainda não se observou `78h=80h`
naturalmente neste perfil nem se confirmou a ligação física de P1.3.

Um contrafactual manteve G/S88 originais e substituiu somente o valor
retornado por `MOVC` em `PC=532Fh`, endereço `7523h`, de `93h` para
`B5h`. O interpolador gravou `IRAM[79h]=95h→B2h`. Com `78h=00h` no
consumidor `1D4Bh`, os 48 valores de agendamento CC3 em G não mudaram:
`1D4Bh` multiplica `B` por `78h`. Fixando `78h=80h` apenas nesse PC,
os 48 valores cresceram em G e S88; a mediana passou de 1933 para
2018 ticks e a largura baixa modelada em P1.3 de 7720 para 8060 ticks.
O teste `test_iram79_curve_changes_cc3_only_when_ram78_is_nonzero`
verifica os dois controles G, o par S88, os hashes das ROMs e a leitura
bruta `MOVC=93h`. Assim, a tabela `7520h` tem efeito digital **condicional**
no agendamento modelado; não foi demonstrado que `78h=80h` ocorra
naturalmente nesse perfil nem que P1.3 seja fisicamente o bico.
Um contrafactual separado em G alterou `7Bh=81h→9Fh` via `752Dh`, mas
`R1=00h` na entrada de `1D4Bh` e os 48 agendamentos CC3 permaneceram
iguais. Essa observação não descarta efeito de `7Bh` sob outros fatores.
Capturas: `build/ma17-analysis/variants/iram79_7b_differential_{control,iram79,iram7b,ram78_80,ram78_80_79,ram78_80_7b,s88_control,s88_79}/`.

Para procurar a habilitação natural de `78h`, cinco execuções G de
1,6 milhão de ticks variaram TPS digital `ADC0/ADC6=120/95,40/95,180/247`,
ADC3=4 e RPM=3000. Entre 393 e 422 amostras por caso passaram por
`1B34h`, `1B3Dh` e `1B48h`; nenhuma passou por `1BD2h`, `1BFDh`,
`1B77h`, `1C34h` ou `1C7Dh`. `R1=03h` nos quatro casos padrão/baixo
e `09h` no TPS alto; `R7=04h` ou `FFh`. `21h.0/.1` ficaram limpos e
`78h=00h`. Os cinco alvos de 48 bytes apontados por `70E0h..70E8h`,
consultados em `1A34h`, têm mínimo maior que zero nas seis ROMs; isso
assegura apenas o valor inicial positivo de `R1` após o `MOVC`. O teste
`FiveIram78GateTablesSelectOriginalRomBytes` executa os opcodes G de
`19FAh..1A3Ah` com estados preparados e confirma a seleção das cinco
curvas e as leituras nos índices `00h` e `2Fh`. A seleção depende de
`2Fh.5/.4`, `T2I1`, `RAM[62h]`, `RAM[63h]` e bits 4/2 de upper `9Eh`.
O caminho `70E6h` requer `62h>7Ah`; o caminho `70E4h` requer
`63h≤26h` e os dois bits de `9Eh` ligados, após excluir o primeiro.
As cinco curvas agora têm entradas separadas no catálogo, com saída
digital `R1` e função física desconhecida. O teste isolado não prova
que todos esses seletores sejam alcançados no boot natural, nem que
`R4` sempre fique dentro dos 48 bytes. O teste
`test_ram78_gate_stays_closed_in_two_digital_tps_states` fixa os dois
extremos de TPS como regressão. Esses pares ADC são estímulos digitais,
sem validação das duas trilhas físicas. Um ensaio com estímulo de 5 baud
também manteve `78h=00h`, mas não estabeleceu uma sessão serial completa;
por isso não comprova o efeito de uma sessão K-Line ativa. Capturas:
`build/ma17-analysis/variants/ram78_natural_gate_{baseline,tps_low,tps_high,coolant_low,rpm3000}/`
e `ram78_kline_session_g/`.
Dois ensaios G adicionais com ADC0/6=180/247, ADC3=4, ADC5=40,
ADC7=63 e 2,4 milhões de ticks testaram 300 e 6.000 RPM. O `MOVC`
em `1A38h` leu índices `00h/2Ah` a 300 RPM e `00h/2Ah/2Fh` a 6.000,
sempre dentro dos blocos de 48 bytes e com valores `03h/09h/0Bh`
positivos. `78h` permaneceu zero: a 300 RPM não se entrou em `1B34h`;
a 6.000 RPM o fluxo passou dessa guarda para `1B48h`. O teste
`test_rpm_extremes_keep_ram78_zero_and_lookup_in_bounds` reproduz os
dois casos. Um levantamento de 399 relatórios salvos com leitura
instrumentada em `1A38h` também não encontrou valor zero (índices
observados 0..44), mas inclui ensaios repetidos e intervenções;
não constitui prova de inacessibilidade global da guarda.

O limite aritmético global desse caminho foi verificado separadamente.
O cabeçalho `70DEh→79E8h` seleciona `IRAM[47h]` e fornece `B=06h`;
os opcodes originais das seis ROMs devolveram `R3≤05h` para as
256 entradas possíveis. A rotina `52CDh` (ou `5390h` na revisão A)
percorre os seis incrementos `20 10 20 1E 22 70` de trás para frente;
os limites brutos de `47h` para `R3=0..5` são **0, 32, 48, 80,
110, 144** nas seis ROMs. O eixo recebeu entrada própria no catálogo.
No rastro G de 3.000 RPM, o cabeçalho foi lido 230 vezes por `MOVC`.
No perfil emulado Fiat de 11,88 MHz, `47h≈RPM/25` põe esses limites
em aproximadamente **0, 800, 1.200, 2.000, 2.750 e 3.600 RPM**.
Dez execuções G sem alteração da ROM, a ±25 RPM dos cinco limites
não nulos, produziram bytes `47h` imediatamente abaixo e acima de
cada limiar: `1Fh/21h`, `2Fh/31h`, `4Fh/51h`, `6Dh/6Fh` e `8Fh/91h`.
São pontos nominais do modelo 60−2; o clock e a pinagem Renault não
foram usados para converter esses bytes em RPM físicas.
Em G `19DEh..19FAh`, o nibble de `6Ah` fica
em `00h..0Fh` e `R4=nibble×6+R3`, logo `R4≤95` sem saturação.
As 96 posições alcançáveis a partir de **cada** um dos cinco ponteiros
são não nulas nas seis ROMs; parte dessas janelas excede o intervalo
provisório de 48 bytes de cada curva. Os testes
`Iram47SegmentDecoderBoundsR4IndexInSixRoms` e
`test_r1_gate_lookup_windows_are_nonzero_even_with_index_spill`
fixam esses fatos. Ainda não se provou que o índice natural ultrapasse
`2Fh`.

O resultado positivo da ROM **não** garante `R1>0` em `1B34h`:
o acumulador assinado chamado em `1A9Dh..1AB5h` pode limpar `R1` e
ligar `F0` quando uma soma não negativa alcança o limiar. Em opcodes
originais isolados G `5419h` / A `54DCh` de todas as seis ROMs, com
`R1=03h`, `R2=00h` e `R3=7Fh`, amostra `02h` preserva `R1=03h`,
enquanto `03h` produz `R1=00h`. O teste
`SignedAccumulatorCanClearNonzeroTableGateR1` reproduz a fronteira.
Essa é uma rota digital plausível para a guarda `R1=0`; ela não foi
observada nos boots citados e não identifica a função física de `78h`
nem a ligação de qualquer pino.
O probe `MA17_TRACE_RAM78_GATE=1` agora inclui `PC=1A3Ah`, logo após
`MOV R1,A`, além da amostra posterior em `1B34h`. Em G a 1.000 RPM,
`ADC0/6=40/95` e `ADC3=80`, foram 230 amostras iniciais `R1=03h` e
209 posteriores `R1=03h`. A 6.000 RPM, `ADC0/6=180/247` e `ADC3=4`,
foram 231 iniciais (`03h/09h/0Bh`) e 221 posteriores (`09h/0Bh`).
Não apareceu `R1=00h` em nenhum dos dois PCs nesses rastros.
As quantidades diferem porque nem toda passagem alcança `1B34h`;
o relatório não pareia automaticamente as duas fases. Capturas:
`build/ma17-analysis/variants/ram78_gate_r1_{baseline1000,high6000}/`.

Um contrafactual pontual G a 6.000 RPM e 2,4 milhões de ticks separou
três células lidas em `1A38h`, sem modificar a ROM. No controle,
`7ADAh/7ADFh/7A1Fh` devolveram `09h/09h/0Bh` em 10/104/115 leituras;
`R1` não zerou em `1B34h` e `1BFDh` não foi visitado. Fornecer `00h`
somente para `7ADAh` criou dez amostras `R1=00h` em `1A3Ah`, mas
nenhuma chegou à guarda `1B34h`. Fornecer `00h` para `7ADFh` ou
`7A1Fh` produziu `R1=00h` em `1B34h` e 106/116 visitas a `1BFDh`.
Todas essas visitas tinham `R6=00h`, permitindo explicar por que o
trecho `1C19h` desvia antes da atualização de `RAM[78h]` nesse estado.
`RAM[78h]` permaneceu `00h`; a mediana de `RAM[14h:15h]` ficou em
1.169 ticks, a largura baixa modelada de CC3 em 4.789 ticks e a de
P5.0 em 1.847 ticks nos quatro braços. Os bytes e hashes da ROM ativa
permaneceram originais. O teste
`test_r1_lookup_zero_opens_1bfd_without_ram78_at_zero_r6` reproduz os
quatro braços; capturas em `build/ma17-analysis/variants/ram78_gate_7ada_*/`.
Isso demonstra causalidade digital até a guarda, mas não que uma ECU
real alcance `R1=00h` nesse perfil ou que CC3/P5.0 tenham as ligações
físicas presumidas.

O consumidor G `1C19h..1C38h` foi executado isoladamente com os bytes
originais da ROM. `R6=00h` desvia em `1C1Ah` e deixa `78h=00h`.
Com `R6=01h`, os três estados controlados de `2Fh.5` e `T2I1`
selecionam `DPTR=713Fh`, `712Dh` ou `7136h`, respectivamente, antes
da interpolação em `5314h/532Fh`; cada um escreve um valor positivo
em `78h` antes de `1C38h`. O teste
`Ram78ConsumerRequiresNonzeroR6AndSelectsOriginalTable` reproduz a
seleção e a escrita. A entrada direta em `1C19h` é sintética: ela
isola a segunda guarda, sem provar que o fluxo natural satisfaz
simultaneamente `R1=0`, `21h.1=1` e `R6>0`.

**Anotação de pinos neste fluxo:** `T2I1` é o bit `C9h` do periférico
Timer 2 usado como seletor digital da tabela; `1C19h..1C38h` não
escreve diretamente em latch de porta nem em `CC3`. Nas quatro
execuções completas da intervenção anterior, as temporizações
modeladas de P5.0 e CC3 ficaram iguais. Assim, `78h` permanece uma
variável interna sem destino físico identificado; nenhuma ligação
de P5.0, P5.1 ou CC3 a bobina, bico ou atuador é deduzida deste ramo.

As curvas contíguas `712Dh..7147h` foram acrescentadas ao catálogo:
são três blocos de nove bytes iguais nas seis ROMs. O contrafactual
G em boot completo (6.000 RPM simulados, 2,4 milhões de ticks,
`ADC0/2/3/5/6/7=180/100/4/40/247/63`) forneceu `00h` somente ao
retorno de `MOVC 1A38h/7ADFh`, abrindo `1BFDh`. Com `R6=00h`, não
houve escrita em `78h`; com `R6=01h` fornecido somente em `1C19h`,
`1C36h` escreveu `78h`, o leitor `1D4Bh` observou valores não zero e
a mediana de `RAM[14h:15h]` na entrada do agendamento CC3 mudou de
1.169 para 1.414 ticks. Fornecer `78h=00h` somente nesse leitor
restaurou 1.169 ticks. P5.0 manteve largura baixa modelada de 1.847
ticks nos três braços. `test_ram78_r6_gate_reaches_cc3_input_through_1d4b`
reproduz o contraste e a restauração; capturas em
`build/ma17-analysis/variants/ram78_r6_*/`.

**Limite do pino CC3/P1.3:** o braço `R6=01h` teve só três pulsos
completos de CC3 modelados, contra 195 no controle e na restauração;
portanto a mediana de largura desses três pulsos não sustenta uma
conclusão física. O efeito comprovado é sobre o valor digital entregue
ao agendador. As duas intervenções são necessárias neste estado e não
demonstram que a ECU as produza naturalmente. O destino elétrico de
CC3/P1.3 permanece não verificado.

Um **degrau natural de TPS no emulador** removeu a restrição dos dois
testes anteriores. Com G original, 6.000 RPM simulados, `ADC0/6=40/95`
até tick 800.000 e depois `180/247`, as duas entradas de 10 bits
mudaram juntas de `160/380` para `720/988`; `ADC2/3/5/7=100/4/40/63`
permaneceram fixos. Sem substituição de `MOVC` ou registrador, houve
seis visitas a `1C19h` com `R1=00h`, `R6=FFh` e `R4=7Fh`. `1C36h`
gravou `RAM[78h]=FFh` cinco vezes. O `MOVC` original em `532Fh/5333h`
leu `7146h/7147h=FFh` cinco vezes cada, com `DPTR=713Fh`. As leituras
iniciais em `1A38h` vieram de células não zero: `7A1Fh=0Bh` e
`7ADFh=09h`; a rotina acumuladora pode limpar `R1` depois da leitura.
Um degrau inverso no mesmo tick também produziu `R6=FFh`, porém
`R1=03h` na guarda e nenhuma visita a `1C19h`.

Na primeira passagem após a escrita natural, `1D4Bh` leu `78h=FFh`
e `R3:R2` em `1DD8h` foi `07A4h`. Repetir a abertura zerando `78h`
somente em `1D4Bh` preservou a escrita em `1C36h`, mas mudou esse
par para `044Dh`. A mediana global de entrada CC3 ficou em 217 ticks
nos dois braços; os pulsos CC3 completos modelados foram 133/189 e
P5.0 permaneceu em 1.847 ticks. Essa diferença local comprova a
contribuição digital de `78h` no cálculo intermediário, enquanto os
resumos globais não isolam um efeito físico em `CC3/P1.3`. A função
elétrica de `T2I1`, `CC3/P1.3` e P5 continua em aberto. Regressão:
`test_natural_tps_opening_reaches_ram78_curve_and_consumer`; capturas
em `build/ma17-analysis/variants/ram78_tps_step_*/`.

O fator da tabela `73E0h` também foi isolado nesse degrau natural.
`079Ch` leu `73F4h=EEh` 110 vezes; a primeira multiplicação em
`07A1h` reduziu `78h` de `FFh` para `EDh`. Fornecer `00h` somente como
retorno desse `MOVC` manteve os cinco escritores `1C36h` que repõem
`FFh`, mas a primeira passagem por `07A1h` fez `FFh→00h`. As leituras
não zero de `78h` em `1D4Bh` caíram de 51 para cinco no rastro.
Perto do tick 900.000, o par `R3:R2` em `1DD8h` foi `06C5h` com o
fator original e `044Dh` com o fator fornecido. A mediana global de
entrada CC3 continuou em 217 ticks; a contagem de pulsos completos
modelados mudou de 133 para 183, e P5.0 ficou em 1.847 ticks.
É uma relação causal entre a célula `73F4h`, a persistência de `78h`
e um resultado intermediário; a carga ligada a `CC3/P1.3` continua
sem identificação física. A regressão do degrau inclui este braço.

Na S88, que usa o mesmo código de `1C19h` e os mesmos bytes em
`73F4h`, o degrau de abertura também produziu seis visitas com
`R1=00h/R6=FFh` e escreveu `78h=FFh` em `1C36h`. A célula `73F4h`
foi lida 110 vezes. Fornecer `00h` apenas nesse `MOVC` mudou a primeira
escrita em `07A1h` de `FFh→EDh` para `FFh→00h`; o par em `1DD8h` perto
do tick 900.000 mudou de `0793h` para `04D0h`. A mediana global de
entrada CC3 ficou em 340 ticks nos dois braços, a contagem de pulsos
completos modelados em 133 e a largura baixa de P5.0 em 1.843 ticks.
Assim, a contribuição digital da célula se repete em outra calibração,
mas nenhum desses números identifica a carga elétrica de CC3/P1.3.
Teste: `test_s88_tps_opening_73f4_factor_reaches_ram78_consumer`;
capturas em `build/ma17-analysis/variants/ram78_s88_tps_opening_*/`.

Uma perturbação pequena da mesma célula preservou a ordem esperada
nos resultados digitais, com a ROM ativa sempre intacta:

| Valor entregue por `079Ch/73F4h` | Primeiro `78h` após `07A1h` | G: `R3:R2` em `1DD8h` | S88: `R3:R2` em `1DD8h` |
|---|---|---|---|
| `ECh` | `EBh` | `06AFh` | `077Bh` |
| `EEh` original | `EDh` | `06C5h` | `0793h` |
| `F0h` | `EFh` | `06DFh` | `07B0h` |
| `00h` | `00h` | `044Dh` | `04D0h` |

Os pares `R3:R2` foram amostrados perto do tick 900.000 após o mesmo
degrau. Nas quatro condições, a mediana global de entrada CC3 ficou
em 217 ticks para G e 340 para S88; P5.0 ficou em 1.847/1.843 ticks.
Isso caracteriza sensibilidade local no cálculo, sem converter os
valores em tempo de injeção, ângulo ou outra unidade física. Capturas
adicionais: `build/ma17-analysis/variants/ram78_factor_{g,s88}_{ec,f0}/`.

Uma grade de RPM e de amplitude do mesmo degrau delimitou a guarda
em G e S88, sem modificar `MOVC` nem registradores. Os dois canais
partiram de `ADC0/6=40/95`; no tick 800.000 passaram juntos para
`120/180` (abertura intermediária) ou `180/247` (abertura maior).
`ADC2/3/5/7=100/4/40/63` ficou fixo e cada execução durou 2,4 milhões
de ticks:

| RPM simulada | Abertura | Visitas a `1C19h`, G/S88 | `R6` nas visitas | Escritas `1C36h`, G/S88 |
|---:|---|---:|---|---:|
| 1.000 | intermediária | 5/5 | `FF, FC, B6, 9A, 7E` | 1/1 |
| 1.000 | maior | 5/5 | `FF` nas cinco | 2/2 |
| 3.000 | intermediária | 5/5 | `FF, FC, B6, 9A, 7E` | 2/2 |
| 3.000 | maior | 5/5 | `FF` nas cinco | 3/3 |
| 6.000 | intermediária | 5/5 | `FF, FC, B6, 9A, 7E` | 3/3 |
| 6.000 | maior | 6/6 | `FF` nas seis | 5/5 |

Em todas as visitas, `R1=00h`; a primeira escrita de cada execução
produziu `78h=FFh`. As contagens são específicas do instante do degrau
e do horizonte de observação; elas ainda não definem um limiar físico
de borboleta. `test_ram78_tps_step_gate_repeats_across_rpm_and_g_s88`
cobre quatro braços representativos; capturas em
`build/ma17-analysis/variants/ram78_envelope_{g,s88}_*/`.
Essa grade amplia a evidência de ativação digital e não identifica a
carga ligada ao pino `CC3/P1.3`.

Na fronteira de baixa amplitude a 1.000 RPM, o estado inicial de ADC
de 10 bits foi `ADC0/6=160/380`. Um degrau simultâneo para `189/409`
deixou `R1=03h` em `1B34h`; para `190/410` produziu seis amostras
`R1=00h`, cinco visitas a `1C19h` e `78h=97h` em `1C36h`, tanto em
G quanto em S88. Os bytes internos passaram de `60h/66h/70h/6Ah =
2Fh/66h/1Dh/D1h` para `30h/67h/1Eh/E1h`. Em G, variar só ADC0 até
190 com ADC6=409 manteve a guarda fechada; variar só ADC6 até 410 com
ADC0=189 abriu. Os pares de uma trilha só são sondas digitais, não
combinações validadas no conector. O limiar `409→410` vale apenas
nesse estado inicial e com o arredondamento ADC emulado.

O caminho de bytes é `ADC6→66h` em `0744h`, `66h→70h` em `11D1h`,
`70h→6Ah` em `1255h..125Eh` pelo ponteiro big endian `7058h→7970h`,
e `6Ah→R4→R1` em `19DEh..1A38h` antes do acumulador `5419h`.
A tabela `7970h..7979h`, agora catalogada, contém o seletor `0Dh`,
oito segmentos e os incrementos `08 10 10 14 1F 28 4D 28`, iguais
nas seis ROMs. Os testes originais de opcodes confirmam `70h=1Dh/1Eh`
resultando em `6Ah=D1h/E1h`; a regressão de execução completa é
`test_ram78_tps_adc10_boundary_follows_channel6_in_tested_state`.
O trace agregado de `MOVC` nos dois lados da fronteira mostra as mesmas
230 leituras da tabela por `527Dh/5284h/5289h`, com os mesmos endereços
e bytes. A diferença observada entra pelo valor de `70h`, não por uma
célula diferente da tabela. `ADC6` é o canal do modelo: ainda falta
confirmar qual pino analógico e qual trilha do TPS o alimentam na ECU.
Capturas: `build/ma17-analysis/variants/ram78_{tps_adc10,s88_adc10,tps_isolate}_*/`.

Uma célula **diferente entre gasolina e álcool** também ganhou um
consumidor em estado alcançado: no mesmo degrau natural a 6.000 RPM,
`MOVC 532Fh/7520h` lê `4Dh` em G/S88, enquanto A usa `6Fh` nessa
célula. Fornecer `6Fh` só ao `MOVC` de G ou S88 escreve `79h=6Fh`
em `47BEh`, em vez de `4Dh`. O par em `1DD8h` perto do tick 900.000
é G `06C5h→07DCh` e S88 `0793h→08CCh`. Se `78h` for zerado só no
leitor `1D4Bh`, o par fica em `044Dh` em G e `04D0h` em S88 tanto
com a célula original quanto com `6Fh`: isso identifica `78h` como
mediador da diferença local. A mediana global de entrada CC3 ficou
em 217/340 ticks para G/S88 e a largura baixa de P5.0 em
1.847/1.843 ticks nos respectivos quatro braços. A ROM permaneceu
intacta. O vínculo físico de `CC3/P1.3` com bico, bobina ou outro
atuador segue não demonstrado. Regressão:
`test_7520_donor_needs_natural_ram78_at_1d4b`; capturas em
`build/ma17-analysis/variants/ram78_7520_*/`.

O efeito de `7520h` chega à saída temporizada modelada em um estado
natural a **3.000 RPM**: no evento de `058Eh` perto do tick 907.094,
o valor de `RAM[14h:15h]` passa de `07FAh` para `0947h` em G quando
o `MOVC` de `7520h` recebe `6Fh` de A em vez de `4Dh`. O pulso baixo
de `P1.3/CC3` iniciado no tick 907.122 passa de **8.156 para 9.488
ticks**. S88 repete o efeito: `08F0h→0A67h` no agendador e
**9.140→9.885 ticks** no pino modelado. Em G, zerar `78h` apenas na
leitura de `1D4Bh` faz ambos os braços entregarem `0506h` e pulso
de 5.132 ticks; isso identifica `78h` como mediador também no resultado
temporizado. As medianas de toda a execução permaneceram iguais em
cada par (G 1.424; S88 1.592,5), ocultando esse transiente. Em
6.000 RPM, os valores de CC3 mudaram, mas os pulsos modelados perto
do mesmo evento ficaram em aproximadamente 4.935 ticks de uma meia
volta de 4.950 ticks. O registro de `P1.3/CC3` continua sendo um pino
do processador no emulador; a ligação ao bico monoponto não foi medida.
Regressão: `test_7520_donor_changes_local_cc3_pulse_via_ram78_at_3000_rpm`;
capturas em `build/ma17-analysis/variants/ram78_7520_3000_*/`.

O diretório `709Ch/709Eh/70A0h` aponta para três matrizes de 120 bytes
em `7B46h/7BBEh/7C36h`. O código `330Dh` em G/S88 e `3329h` em
A/S37 obtém a linha da tabela `7B28h` (cabeçalho `AEh,08h`), extrai
a coluna do nibble baixo da RAM superior `BCh`, usa 15 como passo de
linha a partir do cabeçalho em `7570h` e calcula `R5=linha*15+coluna`:
o formato é **8 linhas × 15 colunas**. `IRAM[57h]=0/1/2` seleciona
os três ponteiros em `5228h`; o teste
`Sab80C517.FiatStartupMapsUseThreePointerTargetsAndOriginalBytes`
executa as duas ROMs com cada seletor e verifica os endereços lidos
em `532Fh/5333h`. Em um boot natural a 1.000 RPM, somente a primeira
matriz foi lida, uma vez, em `7B46h/7B47h`: `99h/99h` em G e
`A1h/A1h` em S88. Nas **360 células**, S88 usa G+8 módulo 256;
o teste Python verifica a diferença uniforme. A seleção **natural**
dos modos 1/2 e a grandeza física dessas matrizes permanecem abertas.

**Leitura além do último índice nominal.** Em S88 original, 6.000 RPM,
ADC3/5/7=`4/40/63` e TPS ADC0/6=`40/95→180/247` no tick 800.000,
o `MOVC` em `5350h` leu `7BBEh` uma vez e `7D26h` 155 vezes.
Esses são `7B46h+120` e `7CAEh+120`: primeiros bytes das matrizes
seguintes, fora das respectivas grades 8×15. O par anterior em `534Bh`
leu `7BBDh` e `7D25h`. Em G com os mesmos estímulos, esses dois
endereços de borda não foram lidos. No código `527Ch..52CCh`, quando
o segmento de 15 posições termina em índice `0Eh`, a saída de fração
é zerada em `529Ah..52A2h`; no estado S88, `3356h` confirmou
`R5=68h`, `R6=00h` e a coluna 14. A leitura extra ocorre, mas seu
byte não contribui numericamente para a interpolação nesse estado.

Doar `A0h` em vez de `A1h` somente nas duas leituras `5350h` manteve
o sinal da subtração e preservou exatamente os resumos de RAM, P5,
CC3, lookup e cobertura de PC. Doar `00h` somente em `7BBEh` mudou
o sinal: o PC passou por `524Dh` na rotina de multiplicação, a primeira
escrita de `69h` após o degrau atrasou seis ticks e o histograma P5.0
mudou, embora a mediana permanecesse 1.843 ticks. Logo, um byte de
borda com peso numérico zero ainda pode afetar a fase de execução
nesse emulador. A ROM original não foi modificada. Capturas:
`build/ma17-analysis/variants/matrix_120_step_{g,s88,s88_boundary_a0,s88_7bbe00,s88_7d26ff}/`.
Regressão: `tests.test_ma17_matrix_boundary`.

`python3 tools/audit_ma17_matrix_boundaries.py --exclude-overrides` audita
os relatórios `execution.json` pela base em `DPTR`, em vez de atribuir
uma leitura somente pelo endereço efetivo. No corpus local observado,
1.145 relatórios passaram pelo filtro de hash e de campos de override;
737 registraram `MOVC`. Destes, 14 relatórios S88 registraram
`7B46h→7BBEh` (14 leituras) e `7CAEh→7D26h` (2.170 leituras), sempre
em `5350h`; nenhum registrou `MOVC` com `DPTR=7BBEh` ou `DPTR=7D26h`.
São rastros de cenários repetidos e de várias versões do emulador, não
14 estados independentes. Restringindo ao executável SHA-256
`af5239bd…a904c00`, foram 15 rastros com `MOVC`, dos quais 13 exibem
as duas bordas (13 e 2.015 leituras). Os artefatos estão em
`build/ma17-analysis/variants/matrix_boundary_audit_{all_models,current_model}.json`.
O filtro não elimina estímulos ADC ou de pinos experimentais; ausência
de seleção direta nesse corpus não prova inacessibilidade em toda ECU.
Regressão da auditoria: `tests.test_audit_ma17_matrix_boundaries`.

O teste isolado `Sab80C517.AlcoholCodeStartupMatrixIndexUsesBcAndUpperAe`
executa `3329h..335Dh` nas ROMs A e S37: `BCh=03h` ou `15h` com
`AEh=00h` dá linha 0 e colunas 3 ou 5; `BCh=03h`, `AEh=20h` dá linha 2,
coluna 3 e `R5=33`. Isso confirma o cálculo do índice nessas revisões,
sem estabelecer a origem natural de `AEh` nem a escala física dos eixos.

Os mapas de calor de [G/S88 em `7B46h`](../build/ma17-analysis/variants/matrix_plots/matrix_7b46_g_vs_s88.png)
mostram a mesma silhueta com `+8` em todas as 120 células S88. Em
[G/A em `7BBEh`](../build/ma17-analysis/variants/matrix_plots/matrix_7bbe_g_vs_a.png),
118 células diferem (`0..+93` bytes): a média por linha de G varia de
`69,7..119,0`, e a de A de `132,5..145,6`. G tem uma depressão nas linhas
1–2, sobretudo nas colunas 4–13, enquanto A preserva uma superfície
mais uniforme. Essa silhueta localiza onde comparar seletores e trajetórias
de `MOVC`; sozinha, não identifica a grandeza física. As comparações internas
[G `7B46h/7BBEh`](../build/ma17-analysis/variants/matrix_plots/matrix_7b46_g_vs_7bbe_g.png)
e [A `7B46h/7BBEh`](../build/ma17-analysis/variants/matrix_plots/matrix_7b46_a_vs_7bbe_a.png)
separam mudança de banco e mudança de ROM. Cada imagem tem CSV por
célula e JSON com hashes. Esses padrões são bytes brutos; o modo 1
permanece sem seleção natural demonstrada.

Na revisão de código A/S37, um ensaio isolado começa em `3372h`, fixa
`R5=4`, `R6=R4=0` e usa `57h=0/1/2`. O caminho `337Eh→53E6h→52EBh`
aponta para as mesmas três bases; em `53F2h`, o endereço efetivo é
base+4 e `3381h` grava o byte em `R2`:

| ROM ativa | `7B46h+4`, modo 0 | `7BBEh+4`, modo 1 | `7C36h+4`, modo 2 |
| --- | ---: | ---: | ---: |
| A | `8Eh` | `97h` | `77h` |
| S37 | `A4h` | `ADh` | `8Dh` |

`Sab80C517.AlcoholCodeSelectsThreeStartupMatricesAtFixedCell` confere
o DPTR, `ACC=4`, o byte da ROM e `R2` em cada caso. Isso demonstra a
seleção e a diferença funcional nessa célula do interpolador A, sem
executar o cálculo anterior do índice ou estabelecer uma saída física.

Em execução completa da ROM G com `RAM[57h]` forçada em `1378h`, a
1.000 RPM, `ADC0/2/3/6=40/100/20/95` e 2,4 milhões de ticks,
os modos 1 e 2 leram respectivamente **650 células** de `7BBEh` e
`7C36h`. Doar somente as 120 células de `7BBEh` de S88 ou A ao
`MOVC` da G mudou o último `RAM[69h]` do produtor de `66h` para
`6Eh` ou `9Ah`; as medianas dos pulsos baixos **modelados**
P5.0/P5.1 foram `5868/5880,5`, `5885/5884` e `5908/5908` ticks.
No modo 2, doar `7C36h` de S88 mudou `RAM[69h]` de `66h` para
`6Eh` e as medianas de `5868/5880` para `5885/5884` ticks.
O byte bruto registrado pelo `MOVC` e a ROM ativa G não mudaram.

Para testar a mediação no modo 1, fornecer `9Ah` a `RAM[69h]` apenas
no leitor Timer 1 `043Bh`, com a matriz G original, reproduziu as
medianas `5908/5908`. Fornecer `66h` no mesmo ponto com a matriz A
doada restaurou P5.0 para `5868` e P5.1 para `5879` ticks (controle
`5880,5`). O pequeno resíduo em P5.1 impede afirmar equivalência
completa. O ensaio demonstra uma rota digital da matriz até a
temporização P5 sob **seletor forçado**; a ocorrência natural dos modos,
a polaridade elétrica, a ligação dos pinos P5.0/P5.1 aos dois drivers
e a função física da matriz continuam sem verificação. Teste:
`test_forced_7bbe_7c36_donors_reach_p5_through_ram69_in_g`;
capturas: `build/ma17-analysis/variants/7bbe_mode1_*/` e
`build/ma17-analysis/variants/7c36_mode2_*/`.

Repeti o modo 1 com o mesmo código G, ADCs e ROM intacta a 750 e
2.000 RPM. A matriz foi lida 884/460 vezes por cenário; a doação
`A:7BBEh` mudou o último `RAM69h`. A intervenção cruzada
em `043Bh` trocou apenas o valor entregue ao cálculo do Timer 1:

| RPM | `RAM69h` G→doadora A | P5.0/P5.1 G | P5.0/P5.1 doadora A | G com `69h` da doadora | doadora com `69h` G |
| ---: | --- | --- | --- | --- | --- |
| 750 | `81h→9Ch` | `6096/6094` | `6016/6016` | `6016/6016` | `6096/6096` |
| 2.000 | `35h→8Ah` | `4790/4790` | `4760/4760` | `4760/4760` | `4790/4790` |

Valores de P5 são medianas baixas modeladas em ticks; `RAM69h` armazenada
permaneceu própria em cada braço cruzado. A mediana de `14h:15h` no
agendador CC3 ficou em 878/390 nos dois pares de RPM. Assim, `69h`
medeia exatamente P5.0 nesses estados, mas a direção do efeito da
matriz em P5.0 muda entre 750/2.000 RPM e o ensaio anterior a 1.000 RPM.
P5.1 deixa um resíduo de dois ticks em um braço a 750 RPM. Essa relação
não é uma escala física linear. Capturas:
`build/ma17-analysis/variants/7bbe_rpm{750,2000}_*/`;
regressão: `Bank7bbeRpmTests.test_alcohol_donor_ram69_gate_and_p5_at_three_rpms`.

Um trace do código G em `048Eh..049Bh`, com o mesmo seletor forçado,
explica por que a resposta não mantém o mesmo sinal. A rotina desloca
`69h` um bit à direita, subtrai `31h` e grava em `22h.7` se o resultado
é **estritamente positivo**; zero e negativo limpam o bit. Os últimos
eventos observados em cada cenário foram:

| RPM | Matriz | `69h`, `31h` em `049Bh` | `(69h>>1)-31h` | `22h.7` | `TH1:TL1` (`35h:34h`) em `0286h` |
| ---: | --- | --- | ---: | ---: | --- |
| 750 | G / A doadora | `81h,27h` / `9Ch,27h` | `+25` / `+39` | `1` / `1` | `FDE2h` / `FFB2h` |
| 1.000 | G / A doadora | `66h,33h` / `9Ah,33h` | `0` / `+26` | `0` / `1` | `FFFFh` / `FFE2h` |
| 2.000 | G / A doadora | `35h,52h` / `8Ah,52h` | `−56` / `−13` | `0` / `0` | `FF43h` / `FF34h` |

Portanto, 1.000 RPM cruza também a condição lógica em `049Bh`; os
outros dois pares permanecem do mesmo lado. Os valores de recarga são
os últimos observados, não uma fórmula direta para a largura mediana de
P5. O agendamento completo e a ligação física ainda precisam de análise.
Capturas: `build/ma17-analysis/variants/7bbe_gate_rpm{750,1000,2000}_{g,a}/`.

Outros quatro blocos de 120 bytes ficam em `7CAEh`, `7D26h`, `7D9Eh`
e `7E16h`, apontados por `70B6h`, `70B8h`, `70BAh` e `70CEh` em todas as
seis ROMs. G/S88 seleciona a base `70B6h` em `334Dh` quando `2Fh.2=1`; A/S37
usa `2Bh.7` e `2Fh.2` em `3369h..3381h` para escolher entre as bases
`7B46h`, `7BBEh`, `7CAEh` e `7D26h`. Um ensaio isolado das ROMs originais
A/S37 fixa `R5=4`, executa as quatro combinações de flags e confirma em
`53F2h` o DPTR de cada tabela e em `3381h` o byte correspondente em `R2`.
Isso demonstra a seleção e a saída digital do lookup, sem provar quando
os estados surgem naturalmente ou a função física da saída. A rotina
de estado A em `3C7Dh..3D04h` foi ligada ao seletor em outro ensaio
isolado, mantendo o mesmo estado de CPU. Com estado anterior `F9:85h=3`,
contador `F9:84h=40h` e `IRAM[47h]=55h`, a ROM A/S37 escreve estado 4 e
liga `2Bh.7`; com `47h=5Fh`, escreve `13h` e limpa o bit. Preparando
`2Fh.2=1`, `57h=0` e `R5=4`, sem tocar em `2Bh.7` entre as rotinas, o
`MOVC` em `53F2h` lê respectivamente `7D2Ah` e `7CB2h`, e grava o byte
em `R2`. Regressão: `AlcoholStateWindowFeedsUpperAeMatrixSelector`.
Isso confirma a cadeia digital sob estado preparado, sem validar o boot
da família A nem converter `47h` em RPM físico.
A rotina
`5228h` em G e sua homóloga `52EBh` em A têm os mesmos 16 bytes: usam
`RAM[57h]×2` como deslocamento no diretório, leem o destino **big-endian**
e só então consultam a tabela. Com base `70B6h`, os modos `57h=0/1/2`
selecionam `7CAEh/7D26h/7D9Eh`. O teste
`Sab80C517.Pointer70baSelects7d9eWhenModeTwo` executa os opcodes
originais de G, A, S37 e S88 com `57h=2`, confirma `DPTR=7D9Eh` no `MOVC`
e a cópia de `ROM[7DA2h]` para `R2`. Com `T2CON.1=0`, o mesmo percurso
grava o byte em RAM superior `A4h`: `77h` em G/A, `8Dh` em S37 e `7Fh`
em S88. Esse `A4h` é RAM superior, não XRAM `A4h`. Assim,
`70BAh→7D9Eh` possui leitor
e formato 8×15 confirmados nesse estado controlado; falta observar a
seleção natural e o destino funcional de `A4h`. Com `2Bh.7=1` e `2Fh.2=1`,
o código A usa base `70B8h`, que também alcançaria `70BAh` com `57h=1`;
essa combinação não foi executada neste teste.

O [mapa de `7D9Eh`, G/S88](../build/ma17-analysis/variants/matrix_plots/matrix_7d9e_g_vs_s88.png)
mostra que S88 aplica `+8` às primeiras 117 das 120 células e preserva
as três finais (última linha, colunas 12–14). Em
[G/S37](../build/ma17-analysis/variants/matrix_plots/matrix_7d9e_g_vs_s37.png),
S37/S36 aplicam `+22` às primeiras 116 e preservam as quatro finais
(colunas 11–14). O teste confere cada byte nas ROMs originais. A
[comparação interna S88 `7D26h/7D9Eh`](../build/ma17-analysis/variants/matrix_plots/matrix_7d26_s88_vs_7d9e_s88.png)
mostra dez diferenças: as sete células de última coluna já distintas
em G, mais as três células terminais preservadas de `7D9Eh`. O padrão
localiza a edição, mas não demonstra a faixa de entradas alcançável
nem a escala física do resultado interpolado.

Um ensaio completo de G a `ADC0=180`, `ADC6=247`, `ADC2=100`, `ADC3=80`
e `ADC7=63` atingiu naturalmente a guarda `2Fh.2`, mas manteve `57h=0`
e leu `7CAEh`. Forçar `57h=2` em `1378h` fez a ROM original consultar
`7D9Eh`; o próprio código limpou `57h` em `3B94h` a cada ciclo observado.
Com o mesmo seletor forçado nos pares de controle e doador, trocar apenas
os 120 bytes retornados por `MOVC` pela matriz S88 produziu:

| RPM | Leituras `7D9Eh` | `A4h` G→doador | `69h` G→doador | `34h` G→doador | P5 baixo G→doador, ticks |
| ---: | ---: | --- | --- | --- | ---: |
| 750 | 912 | 98h→A0h | A0h→A5h | 7Dh→D9h | 6.017→6.094 |
| 1.000 | 494 | 8Eh→96h | 96h→9Eh | DDh→FAh | 5.910→5.910 |
| 1.500 | 480 | 7Dh→85h | 84h→8Ch | 65h→78h | 5.260→5.234 |

Cada resultado é uma mediana dos latches modelados `P5.0/P5.1` em 2,4
milhões de ticks; o hash da ROM G ativa permaneceu intacto. O contraste
**dentro do modo 2** isola a contribuição dos bytes `7D9Eh`. A diferença
entre modo 0 e modo 2 inclui outras consultas que usam `57h`, por isso não
é uma medida exclusiva dessa matriz. O teste é
`VariantTraceTests.test_mode_one_and_two_select_flag_matrices_and_donors`;
capturas em `build/ma17-analysis/variants/flag_7d9e_mode2_tps180_247/`
e `build/ma17-analysis/variants/flag_7d9e_mode2_rpm_donor/`.

O modo 1 forçado no mesmo cenário de 1.000 RPM leu `7D26h` 494 vezes.
Nessas células amostradas, `7D26h` e `7D9Eh` deram os mesmos bytes e os
mesmos resultados internos; a doação isolada dos 120 bytes S88 em `7D26h`
mudou `A4h=8Eh→96h`, `69h=96h→9Eh` e `34h=DDh→FAh`, com P5 baixo
mediano em 5.910 ticks nos dois casos. Na ROM G, essas duas matrizes
diferem somente em `base+14,+29,+44,+59,+74,+89,+104`: a última coluna
das linhas 0–6. A 750 RPM, `BCh=0Eh` forçado em `330Dh` fez o código
original ler 212 vezes a célula `base+104`, que contém `63h` no modo 1 e
`52h` no modo 2. Nesse contraste entre modos, `A4h` terminou em `18h/14h`,
`69h` em `20h/1Ch`, e P5 baixo mediano em 6.017/6.016 ticks. Como mudar
`57h` altera também outras buscas, esses 1 tick não isolam o efeito da
célula. O teste
`VariantTraceTests.test_mode_one_two_last_column_difference_is_reached`
confere a posição, os bytes lidos e os estados. Capturas:
`build/ma17-analysis/variants/flag_7d26_mode1_tps180_247/` e
`build/ma17-analysis/variants/mode1_mode2_last_column_750_long/`.

`70CEh→7E16h` é lido
diretamente em `3830h` (G) ou
`385Eh` (A), com índice `R5` calculado usando o passo 15 de `7570h`;
seu resultado passa por uma segunda consulta em `7163h` indexada por
`IRAM[70h]` e é escrito em RAM **superior** `CAh`, distinta de XRAM `CAh`.
Na comparação G→A, 118 células internas de `7E16h..7E8Dh` aumentam
exatamente `26` módulo 256; somente os bytes inicial e final continuam
em zero. Um ensaio isolado, com `R5=2`, `R4=R6=0`, `R1=FFh` e `70h=0`,
leu `7E18h=19h` em G e `33h` em A e produziu RAM superior `CAh=17h/31h`.
O teste `Sab80C517.FiatAndAlcoholCodeRead7e16IntoUpperCa` verifica os
opcodes e resultados com as ROMs intactas. Nos 16 traces G/S88 da grade
de temperatura a 1.000 RPM, `ADC7=63` e 2,4 milhões de ticks, não houve
leitura `MOVC` desse bloco; o efeito natural e a função física continuam
abertos. As diferenças G→A são
0/119/0/118 bytes nessas quatro regiões; G→S88 são 120/120/117/0.

O ramo G `37AAh..37C3h` (A `37D8h..37F1h`) usa o ponteiro
`70D4h→7E8Eh` quando `OV=1` e `B.0=1`. A tabela tem 15 bytes nominais,
iguais nas seis ROMs. O índice de `MOVC` é
`(RAM_superior[BCh] & 0Fh) + ((RAM_superior[BCh] >> 7) & 1)`;
o byte lido é gravado em RAM **superior** `8Dh`.
O [gráfico da curva bruta 7E8Eh](../build/ma17-analysis/variants/matrix_plots/curve_7e8e_all_variants.png)
mostra um degrau de `01h` até `05h` no índice 10 e retorno a `01h`
nos índices 12–14. As seis ROMs coincidem célula por célula. O comando
`/usr/bin/python3 tools/plot_ma17_state_curve.py` também gera CSV e JSON
com endereço de cada byte e hash de cada ROM. A forma não define unidade
física nem a frequência natural de cada índice.
Traces completos G/S88
com TPS `40/95` registraram `7E91h=01h` e `7E93h=02h` (índices 3 e 5);
um ensaio experimental S88 com dois degraus TPS registrou `7E95h=03h`
(índice 7). Um teste com os opcodes
originais das seis ROMs confirmou índice e escrita para `BCh=03h/05h/07h/8Ah/8Fh`.
As capturas antigas `tps_gate63_40_95_{g,s88}` não registraram o hash
do executável. No executável atual `1c0b13f3…28804`, um controle G/S88
sem degraus, com os oito ADCs brutos `40/130/100/80/90/110/95/63`,
1.000 RPM e 3,4 milhões de ticks, não leu `7E8Eh` nem RAM superior
`8Dh`. A diferença pode depender de estado ou da versão do modelo;
as leituras antigas de TPS constante permanecem não revalidadas.
O controle atual é reproduzido por
`Matrix7e16ReachabilityTests.test_7e8e_historical_steady_tps_access_is_absent_in_current_model`.
O caso `8Fh` chega ao índice 16 e lê `7E9Eh`, além do intervalo nominal:
é um teste de limite, sem evidência de ocorrência natural.
O leitor posterior de `8Dh` foi identificado no código original:
`377Fh/37C9h` executam `CJNE @R1,#00h` com `R1=8Dh`, e `37DFh`
executa `DEC @R1`. No cenário de 1.500 RPM com P4.6 baixo experimental,
ADC6 `95→220` no tick 200.000 e TPS `40/95→180/247` no tick 1.350.000,
G e S88 têm os mesmos 15 bytes em `7E8Eh`, mas G lê `7E93h=02h`
e S88 lê `7E95h=03h` em `37BFh`, uma vez cada. O código grava o byte
em RAM superior `8Dh` em `37C3h`; depois, G passa por `37C9h` com
`02h→01h→00h`, enquanto S88 passa por `03h→02h→01h→00h`.
Cada passagem positiva chega a `37DFh` para decremento. Isso identifica
`8Dh` como contador de estado **nesse ramo digital** e demonstra uma
passagem adicional em S88 causada pelo índice, sem atribuir unidade de
tempo nem função física. Capturas:
`build/ma17-analysis/variants/upper8d_read_probe_{g,s88}_tps/`;
regressão: `Matrix7e16ReachabilityTests.test_7e8e_index_sets_upper_8d_countdown_differently_in_g_s88`.
Um controle causal com a mesma ROM G, os mesmos ADCs e a mesma roda fônica
substituiu apenas o retorno de `MOVC` em `37BFh/7E93h` de `02h` por `03h`.
O guarda `37C9h` passou de `02h→01h→00h` para `03h→02h→01h→00h`,
com uma execução adicional de `DEC @R1` em `37DFh`. A largura mediana
observada dos pulsos CC3 foi 5.881 ticks em ambos os ensaios; isso não
estabelece ausência de qualquer efeito físico em outras condições.
O resumo P5.0 coincidiu integralmente. Em P5.1, uma única largura
modelada passou de 1.769 para 1.768 ticks; a mediana permaneceu em
1.784 ticks. A diferença de um tick é compatível com o caminho de
instruções adicional, sem demonstrar uma mudança de calibração física.
Captura: `build/ma17-analysis/variants/upper8d_g_override_03/`;
regressão: `Matrix7e16ReachabilityTests.test_7e8e_single_movc_byte_controls_upper_8d_countdown`.
Regressão: `Sab80C517.Pointer70d4IndexesUpperBcAndWritesUpper8d`.

Um estímulo TPS `ADC0/ADC6=40/95→180/247` no tick 200.000, com G,
`ADC2=100`, `ADC3=80`, `ADC7=63`, 1.000 RPM e 2,4 milhões de ticks,
chegou a `3752h` mas não a `3830h`: `2Fh.7` permaneceu zero nas
observações dessa passagem e `RAM[78h]` foi zero em todas as 231 amostras
de `1D4Bh`. O degrau inverso também não leu `7E16h`. São condições
específicas, sem prova de que o ramo seja inalcançável (capturas:
`build/ma17-analysis/variants/7e16_tps_step_low_high/` e
`7e16_tps_step_high_low/`).

Uma intervenção controlada de `RAM78h=80h` somente em `1D4Bh`, com
TPS bruto `40/95→180/247` no tick 200.000, 1.000 RPM e 2,4 milhões
de ticks, fez `21h.1` e `2Fh.7` coincidirem em 41 das 62 passagens
por `3752h`. Ainda assim, não houve leitura de `7E16h`: nas 166
passagens capturadas por `37FBh`, `B.0` estava limpo. Os opcodes em
`37E3h..37FBh` mostram que esse estado seleciona `7300h+60h`, limpa
`F0` e pula o lookup de `70CEh→7E16h`. Logo, as duas flags são
insuficientes nesse cenário; falta identificar um estado que mantenha
`B.0=1` ao entrar na interpolação. A ROM ativa e o executável do
emulador foram verificados por hash. Captura: `7e16_tps_step_ram78/`;
teste `test_7e16_path_needs_state_bit_even_when_two_flags_overlap`.

O bit ausente tem um produtor candidato nos opcodes originais. `36AFh`
carrega `B` da RAM superior `81h`; `36DEh` só entra no caminho que pode
manter `B.0=1` quando `B.5=1`. Em `2E06h`, o firmware G pode gravar
`81h` com `OR 24h` após comparar `ROM[72A6h]+46h` com `47h`, sem
carry e com `XRAM[F8:F9]=0`. `ROM[72A6h]=06h` e `72DEh=96h` nas seis
imagens. No trace do degrau TPS, as 231 amostras em `36DEh` tiveram
`B.5=0`, sem atingir `3701h` ou `371Dh`. Forçar P4.6 baixo a partir
do tick 200.000 fez a G passar por `2D85h`, mas não por `2DC8h/2E06h`.
O código de `2D85h` exige a transição de `2Fh.0` anterior ligado para
atual desligado; o estímulo testado não a produziu. Essas condições
delimitam o próximo experimento, sem identificar a função elétrica de
P4.6. Capturas: `7e16_b_source/` e `7e16_p46_low_step/`; o teste
anterior agora verifica também `B.5` em `36DEh`.

Um teste isolado com os opcodes da ROM G confirma esse produtor e seus
limites: partindo de `2E06h`, `46h=40h`, `47h=48h` e `F8:F9h=0`, o
`MOVC` lê `72A6h=06h`, grava `72DEh=96h` em `F8:FAh` e deixa a RAM
superior `81h=24h`. Igualar `47h` a `46h` ou pôr `F8:F9h=1` impede a
gravação. O `MOV B,@R1` original em `36B1h` copia `81h`; com `F8:FAh=FFh`
preparado, o caminho `36DEh→3701h` liga `B.0`, enquanto os controles
chegam a `3739h`. O teste salta deliberadamente o fluxo entre `2E24h`
e `36AFh`; portanto ainda não demonstra que o produtor seja alcançado
em uma partida natural ou que `3830h` leia `7E16h`.
Teste: `Sab80C517.FiatUpper81StateProducerOpensB5MatrixBranch`.

Um ensaio de fluxo completo, ainda com **P4.6 baixo experimentalmente**,
começa em TPS bruto `40/95` e muda ADC6 para `220` no tick 200.000.
Em 1.000 RPM, `2E06h` é alcançado, mas `46h=2Ah`, `47h=28h` e
`ROM[72A6h]=06h` desviam em `2E0Fh`. Em 1.500 RPM, `47h=3Ch` e o
mesmo código chega a `2E1Ch`, grava `F8:FAh=96h` e passa por `36DEh`
com `B.5=1`. Esse resultado confirma a produção do estado sob o
estímulo controlado. Ainda não há leitura de `7E16h`: em `36FFh`,
`ROM[72D6h]=02h`, RAM superior `C5h=53h` e `70h=53h` deixam carry
limpo e levam a `3739h`. Capturas: `7e16_p46_low_tps_fault_step_probe/`
e `7e16_rpm_1500_branch_probe/`; teste
`test_7e16_state_producer_reaches_original_code_at_higher_rpm`.

Um segundo degrau, após a gravação de `F8:FAh`, desloca TPS bruto
`40/220→180/247` no tick 1.350.000. Com P4.6 baixo experimentalmente,
mas **sem override de RAM**, `C5h` mantém `53h` enquanto `70h` sobe a
`DFh`; `36FFh` fica com carry ligado e alcança `3701h`. A rotina
`3830h` então lê `7E16h` 320 vezes em 3,4 milhões de ticks, em quatro
células distintas. G lê `7E66h/7E67h/7E75h/7E76h` 80 vezes cada;
S88 lê `7E76h/7E77h/7E85h/7E86h` 80 vezes cada, embora os 120 bytes
de `7E16h` sejam idênticos nas duas ROMs. Emparelhando as 80 entradas em
`3830h` com a escrita em `384Ch`, `CAh` superior recebe valores 0..3
em G e 0..5 em S88. Controles sem P4.6
baixo ou sem o primeiro degrau não leem a matriz. Isso estabelece a
seleção digital e a dependência de estado anterior no emulador;
a ligação elétrica de P4.6 e a função física de `CAh` continuam abertas.
Capturas: `7e16_double_tps_step_no_ram78_uca/`,
`7e16_double_tps_step_s88/`, `7e16_double_tps_step_p46_default/` e
`7e16_single_tps_step_p46_low/` em `build/ma17-analysis/variants/`.
O [grafo do ramo 36DEh→3701h](../build/ma17-analysis/variants/7e16_reached_gate.svg)
e seu [relatório de PCs](../build/ma17-analysis/variants/7e16_reached_gate.json)
marcam as instruções observadas nessa passagem.
Teste: `Matrix7e16ReachabilityTests.test_double_tps_step_selects_same_table_at_different_cells`.
Reproduzir com `python3 -m unittest tests.test_ma17_matrix_7e16` após
compilar `build/emu8051-tty`.

O índice desse lookup é verificável nas instruções `380Dh..382Fh`:
`R5 = 15 × (RAM[68h] & 0Fh) + (RAM_superior[BCh] & 0Fh)`, com passo
`0Fh` lido em `7571h`. Nas 80 entradas nativas de `3830h`, G tem
`68h=B5h`, `BCh=05h`, `R5=50h`; S88 tem `68h=86h`, `BCh=96h`,
`R5=60h`. Fornecer só o byte S88 `7580h=25h` às leituras `MOVC` da
ROM G leva `BCh` a `96h`, mas `68h=C5h` e `R5=51h`, deslocando apenas
uma coluna. Fornecer também os 225 bytes de `7581h` da ROM S88 leva
`68h=86h` e `R5=60h`. Com ambas as doações, os 80 pares consecutivos
`(BCh,68h,R5,R1,CAh)` de G coincidem exatamente com S88, sem alterar
nenhuma das duas ROMs. Isso isola o efeito dessas calibrações na seleção
digital observada; não identifica a escala física da matriz `7E16h`.
Capturas: `7e16_index_trace_{g,s88}/`, `7e16_index_g_7580s88/` e
`7e16_index_g_7580_7581_donor_s88/` em `build/ma17-analysis/variants/`.

O elo intermediário aparece em `330Dh..332Fh`: o código segmenta a RAM
superior `AEh` com o cabeçalho `7B28h` e grava o índice compactado em
`68h`. Após o segundo degrau, as 68 amostras estáveis de `AEh` em
`330Dh` são `43h` em G, `44h` em G com apenas `7580h=25h`, e `4Ch`
tanto em G com as duas doações quanto em S88. Em `3830h`, os valores
correspondentes de `68h` são `B5h`, `C5h` e `86h`. O caso com apenas
`7580h` faz uma entrada adicional em `3830h` sem outro grupo completo
de leituras; o teste compara seus 80 grupos `MOVC` concluídos.
Capturas: `7e16_ae_{g,g7580,gboth,s88}/`.

O primeiro consumidor estático de `CAh` superior é `39B2h`: o código
compara esse byte com `B`, conserva o maior, compara em seguida `C9h`
e `CBh` superiores e combina o resultado com `R7` e `R2` antes de
gravar o novo `R2` em `39F4h`. Em `3A48h`, `CAh` também participa da
guarda que escolhe a consulta em `7300h`. Ambos os PCs aparecem na
cobertura dos ensaios de `7E16h`. Instrumentação observacional em
`39B2h`, após tick 1.400.000, registrou 79 passagens em cada ROM: G
apresentou `CAh=00h..03h` e S88 `00h..05h`, enquanto `C8h` superior e
`B` permaneceram `05h`. Portanto, `CAh` não vence o máximo nessa janela.
Nas 78 passagens completas por `39F4h`, o trio `(R2,B,A)` ficou
`(97h,05h,9Ch)` em G e `(99h,05h,9Eh)` em S88. `3A48h` foi alcançado
somente duas vezes após o segundo degrau, ambas com `CAh=00h`. Assim,
os valores da matriz são consumidos, mas seu efeito em `R2` está
mascarado nesse estado; a diferença de `R2` entre ROMs tem outra origem
ainda não isolada. As larguras medianas de P5.0 (G 1767, S88 1765,
G com doação de `7580h`/`7581h` 1785 ticks) e CC3 (6553, 7312 e 7312)
não comprovam efeito físico de `7E16h`. Capturas:
`7e16_ca_consumer_{g,s88}/`; teste:
`Matrix7e16ReachabilityTests.test_double_tps_step_selects_same_table_at_different_cells`.
Um teste isolado com os opcodes originais de `39B2h..39F4h`,
`R2=10h`, `R7=7Fh` e `B=05h` confirma o máximo: `CAh=03h/05h`
produz `R2=15h`, enquanto `CAh=08h` produz `R2=18h`. Isso demonstra
que o consumidor pode transmitir `CAh` quando ela supera os demais
limites, mas não estabelece que tal estado ocorra na partida completa.
O homólogo A em `39E0h..3A22h`, com os mesmos registradores e os valores
`CAh=17h/31h` do ensaio isolado de `7E16h`, produz `R2=27h/41h`.
O runner de partida completa ainda rejeita A, pois seus opcodes antes
de `7580h` diferem dos da ROM G e o perfil dinâmico dessa revisão não
foi validado. Teste:
`Sab80C517.FiatAndAlcoholUpperCaConsumerUsesMaximumBeforeUpdatingR2`.

Para testar especificamente a recalibração G→A em `7E16h`, o runner
agora aceita sua doação pelos 120 bytes da ROM A, com ponteiro `70CEh`
verificado nas duas imagens. Na partida completa **do código G** sob o
mesmo degrau duplo de TPS, 80 leituras da matriz preservaram os endereços
e bytes brutos da ROM G no log, mas o retorno efetivo da interpolação em
`R3` mudou de `38h` para `52h`. Das 80 escritas de `CAh` superior,
54 mudaram: a distribuição G `00h:37, 01h:18, 02h:19, 03h:6` tornou-se
`00h:26, 01h:11, 02h:12, 03h:12, 04h:15, 05h:4`.
Após tick 1.400.000, `B=05h` ainda limita todas as leituras em `39B2h`;
as 78 passagens completas por `39F4h` mantêm `(R2,B,A)=(97h,05h,9Ch)`
nos dois casos. As medianas modeladas de P5.0/P5.1 e CC3 permanecem
iguais entre controle e doação; isso não declara igualdade de todas as
bordas ou histogramas. A ROM G ativa e a ROM A doadora conservam seus
hashes originais. Capturas: `7e16_g_matched/`, `7e16_a_donor_g/`;
teste: `test_alcohol_matrix_donor_changes_upper_ca_but_is_clamped`.

Variar apenas ADC2 bruto de 100 para 200, preservando os dois degraus de
TPS e P4.6 baixo experimental, manteve as 320 leituras de `7E16h`.
Agora `B=00h` nas 78 passagens por `39B2h` após tick 1.400.000; `C9h`
e `CBh` superiores também são zero. As 54 alterações de `CAh` entre G
e G←A alcançam o cálculo seguinte: em `39F4h`, `R2` de entrada é `9Ch`
e `A=9Ch+CAh`, com `CAh` em `00h..03h` no controle e `00h..05h` na
doação. A mediana de P5.1 baixo muda **1775→1784 ticks**; P5.0
permanece 1782 e CC3 6373 ticks nas duas execuções. É um efeito
reproduzível de uma única tabela doadora sobre o pino **modelado** P5.1,
sem comprovação da ligação física ou da mediação específica de `R2`
nesse pino. ADC2=50 forneceu o controle oposto: `B=0Bh` e `CAh≤05h`
continuaram mascarados. Capturas: `7e16_g_adc2_200/`,
`7e16_a_donor_adc2_{50,200}/`; teste:
`test_alcohol_matrix_reaches_r2_when_adc2_lowers_clamp`.

Uma segunda intervenção cruza controle/doação com `CAh` superior zerado
somente no PC `39B2h`, imediatamente antes de `MOV R1,#CAh`/`MOV A,@R1`.
As duas execuções ainda completam 80 leituras da matriz e as 54
diferenças nas escritas prévias de `CAh`; após o zero, `39B2h` vê `CAh=0`
e `39F4h` calcula sempre `A=9Ch`. Os relatórios de *output latches*,
CC3, fase CC3/P5, alterações de RAM de motor e cobertura de PC ficam
iguais entre G e G←A; P5.0/P5.1 baixos têm mediana 1767 ticks nas duas.
Isso estabelece que a diferença modelada de P5.1 depende da passagem
por `CAh` superior nesse ponto. A intervenção não distingue qual ramo
posterior de `CAh` determina cada borda. Capturas:
`7e16_{g,a_donor}_adc2_200_ca_zero/`; o mesmo teste automatizado cobre
as quatro combinações de tabela e intervenção.

O próximo elo está em `3AE4h..3B06h`: `R2` é limitado pelas constantes
de `7200h`/RAM superior `8Ch` e gravado em `69h` em `3B06h`. Com ADC2=200,
`MA17_TRACE_RAM69=1` registrou 78 passagens após tick 1.400.000;
`A`/`8Ch` na escrita cobrem `9Ch..9Fh` no controle e `9Ch..A1h` com a
tabela A. As escritas de `69h` observadas também chegam a `9Fh` versus
`A1h`, embora ambas terminem em `9Ch`; a comparação só do estado final
perderia esse efeito transitório. O serviço de Timer 1 lê `69h` em
`043Bh` e calcula as recargas `34h:35h`.

Um segundo cruzamento fixa `69h=9Ch` **apenas nessa leitura de Timer 1**,
sem impedir as escritas anteriores em `3B06h` nem as leituras de
`7E16h`. Controle e G←A passam a ter as mesmas escritas observadas de
`34h:35h` e medianas P5.0/P5.1 de 1767 ticks; CC3 continua em 6373.
As sequências de alterações de `69h` e alguns eventos individuais de
P5.1 ainda diferem. Portanto, `69h` nessa leitura medeia a diferença
**da mediana**, sem demonstrar igualdade de todas as bordas. Capturas:
`7e16_{g,a_donor}_adc2_200_ram69_path/` e
`7e16_{g,a_donor}_adc2_200_ram69_9c/`; o teste automatizado cobre os
seis braços de doação, zero de `CAh` e leitura fixa de `69h`.

O limite que mascara `CAh` pode ser rastreado até ADC2, mas há duas
fronteiras distintas. O boot G grava ADC2 bruto 50/100/200 em `62h`
como `32h/64h/C8h`; `3C65h..3C73h` usa `62h` para consultar `716Ch`
e escrever RAM superior `CCh`. O consumidor `397Dh..399Ch` chega a
`C8h=0Bh/05h/00h` nesses três pontos, e `39B2h` usa esse valor como
limite `B`. A varredura bruta 100/108/112/116/118/120/122/123/124
produziu `CCh=C8h` de `05/03/03/02/01/01/01/00/00h` após o segundo
degrau. A transição `122→123` usa as **mesmas** células `716Fh=86h` e
`7170h=80h`, com `2Fh.2` ainda ligado. A tabela A em `7E16h` supera
o limite em 25→43 passagens no ponto 122 e em 43→54 no ponto 123
(controle→doação); P5.1 mediano é 1802,5→1793,5 e 1784→1784 ticks,
respectivamente. CC3 permanece 5969 nos quatro braços. A ausência de
diferença na última mediana não significa ausência de efeito interno.

O limite `122→123` também decorre diretamente dos opcodes: `5314h`
aplica `SWAP A; RR A`, separa `R5=A&07h` e `R6=A&F8h`, e `532Fh`
interpola bytes adjacentes com a parte alta do produto com sinal.
Para ADC2 `7Ah`/`7Bh`, `R5=3` e `R6=D0h`/`D8h`; os bytes
`716Fh:7170h=86h:80h` têm diferença `−6`. Assim,
`86h+floor(−6×208/256)=81h` e
`86h+floor(−6×216/256)=80h`; `CPL ACC.7` em `3C6Fh`
grava `CCh=01h`/`00h`. O teste compara essa conta derivada dos bytes
originais com a RAM superior observada, sem atribuir graus Celsius à
fronteira.

Outra fronteira ocorre em `47F1h`: `ROM[72BDh]=7Ch` é comparado com
`62h`. Em ADC2=124, `22h.6=0` e o carry em `3D0Ch` permanece 1; em
ADC2=125, `22h.6=1` habilita a consulta a `ROM[721Dh]=21h` contra
`63h=50h`, e o carry em `3D0Ch` fica 0. `C8h` já é zero nos **dois**
lados; portanto essa troca de flag não explica a abertura inicial do
limite. O scanner classifica `RAM[62h]` como IAT e sua fórmula atual
estima 20,75 °C em bruto 122 e 20,36 °C em 123. Essa é uma pista do
scanner baseada em NTC ajustado, não uma calibração física confirmada
do canal ADC2 ou uma temperatura de transição validada na ECU.
Referência: `Monomotronic-MA1.7-Scanner/src/ECUSerial/SensorDecoders.cpp`;
capturas: `7e16_adc2_cc_sweep_*/`, `7e16_adc2_cc_donor_{122,123}/`,
`7e16_adc2_threshold_{124,125}/`; testes:
`tests.test_ma17_adc2_716c_gate`.

Na ROM G, `3CB1h..3CB7h` forma `PSW.5` a partir do carry de
`R2−IRAM[6Fh]`, mascarado por `2Eh.6` nesse percurso. O único escritor
direto encontrado para `2Fh.2` é `3D0Ch`. Um teste isolado parte de
`3CDAh` com `A=0`, `R0=9Fh`, `XRAM[9Fh]=0`, `22h.6=0` e `2Fh.5=0`:
`PSW.5=1` e `T2CON.1=0` ligam `2Fh.2`; limpar `PSW.5` ou ligar
`T2CON.1` deixa o bit desligado. A seleção natural de `7D9Eh` ainda
precisa também de `57h=2`; nas execuções G/S88 corrigidas já registradas,
esse seletor permaneceu em zero. O teste delimita a guarda digital e não
estabelece que esses estados ocorram juntos durante uma partida real.
O campo `air_gate_observation` de `tools/trace_ma17.py` resume as amostras
opcionais de `MA17_TRACE_AIR_716C_GATE=1`, incluindo contagens por PC,
`2Eh.6` em `3CB7h` e carry antes de `3D0Ch`. O probe do emulador limita
a coleta a 3.000 eventos; o relatório indica quando esse limite é atingido.
Na ROM G intacta, com `ADC7=63`, 1.000 RPM e 400.000 ticks, foram 97
passagens por cada um desses dois PCs, sem `2Eh.6`, `R2<6Fh` ou carry;
o limite não foi atingido. A captura reproduzível está em
`build/ma17-analysis/variants/air_gate_baseline_structured/`.

Uma grade digital TPS/ADC abriu essa guarda sem alterar a ROM: em G, a
1.000 RPM e `ADC7=63`, o par `ADC0=180`, `ADC6=247` produziu `2Eh.6=1`
em `3CB7h` e `R2<IRAM[6Fh]`; com `ADC2=100`, `ADC3=80`, houve 912 leituras
`MOVC` na matriz `7CAEh..7D25h` em 2,4 milhões de ticks, tanto em G
quanto em S88. A variação controlada `ADC2=220`, `ADC3=80` manteve esses
dois termos, mas zerou o carry em `3D0Ch` e não leu a matriz. Mantendo
`ADC2=220` e mudando somente `ADC3` para `20`, o carry reapareceu e
ocorreram 132 leituras em 400 mil ticks. Isso valida os estímulos digitais
dos dois canais de temperatura através do estado `22h.6` e da comparação
com `ROM[721Dh]`; ainda falta calibrar a relação elétrica e térmica.
`VariantTraceTests.test_coolant_adc_opens_flag_selected_matrix_path`
reproduz os dois extremos de ADC3 na ROM original.

No mesmo cenário `ADC2=100`, `ADC3=80`, trocar apenas os 120 bytes
consultados por `MOVC` de `7CAEh` entre G e S88 alterou a escrita em RAM
superior `A4h` feita por `33A4h`: G passou de `9Ah` para `A2h`, e S88
passou de `A1h` para `99h`. Em 2,4 milhões de ticks, o G também mudou a
largura mediana baixa de **ambos** os latches `P5.0/P5.1` de 1.861 para
1.921 ticks, mantendo o período de 59.400 ticks; S88 permaneceu em 1.921
ticks na troca inversa. O teste reproduz esses valores com pelo menos 30
inícios baixos por pino. O opcode em `33A4h` escreve RAM superior
`A4h`, mas `33A5h` troca `R1` para `92h`; portanto, a leitura e possível
decremento em `33BCh` atuam em RAM superior `92h`, não em `A4h`.
Ainda não foi demonstrado que `A4h` medeie a mudança nos latches.
O rastreamento opcional `MA17_TRACE_INDIRECT_IRAM_ADDRESS=A4` agora cobre
os opcodes que leem `@R0/@R1` e `POP/RET/RETI`, sem alterar os operandos.
Com G, ADC0/2/3/6/7=`180/100/80/247/63`, 1.000 RPM e 2,4 milhões de
ticks, não registrou nenhuma leitura de upper `A4h`, tanto no controle
(`A4h=9Ah`, P5.0 baixo=1.861 ticks) quanto com a matriz S88 doada
(`A4h=A2h`, P5.0 baixo=1.921 ticks). O controle positivo no mesmo estado
registrou 458 leituras de upper `92h` em 262 classes, incluindo
`33BCh`/`E7h`.
Assim, `A4h` não medeia a diferença P5 observada **via leitura pela CPU
neste estado emulado**; pode ser cópia de resultado para outro uso ou ter
consumidores em estados ainda não exercitados. Capturas:
`build/ma17-analysis/variants/7cae_{a4_reads_g,a4_reads_g_donor_s88,indirect_read_control_92}/`.
Regressão: `tests.test_ma17_indirect_iram_trace`.
Uma varredura adicional, sempre com a ROM G original e sem K-Line,
também registrou **zero leituras de `A4h`** nas seguintes janelas:

| Estado digital | Ticks | Último `A4h` | P5.0 baixo, ticks |
| --- | ---: | ---: | ---: |
| 750 RPM, ADC0/2/3/6=`180/100/80/247` | 2.400.000 | `9Ah` | 1.860 |
| 1.500 RPM, mesmos ADCs | 2.400.000 | `95h` | 1.767 |
| 2.000 RPM, ADC0/2/3/5/6=`180/40/40/40/247` | 2.400.000 | `86h` | 1.805 |
| 3.000 RPM, mesmos ADCs | 2.400.000 | `74h` | 1.794 |
| 1.000 RPM, ADC0/2/3/5/6=`40/100/20/40/95` | 2.400.000 e 12.000.000 | `97h` | 1.861 |

Todos usam ADC7=`63`; capturas `build/ma17-analysis/variants/a4_read_sweep_*/`.
O resultado restringe a busca de consumidores de `A4h`, mas não prova
ausência em todos os estados, nem atribui função física a essa RAM.
Os SHA-256 das ROMs ativas continuaram os originais;
o mecanismo substitui somente o valor retornado pela leitura, com hash
separado da ROM doadora. As ROMs nativas G/S88 consultam endereços de
células diferentes, portanto a diferença entre suas saídas nativas não se
explica somente pelos bytes da matriz. O teste
`VariantTraceTests.test_7cae_donor_changes_upper_a4_with_original_roms`
verifica o efeito causal digital. O destino elétrico de `P5.0/P5.1` e a
escala física da calibração ainda requerem confirmação. Capturas:
`build/ma17-analysis/variants/air_gate_matrix_7cae_g_s88/` e
`build/ma17-analysis/variants/air_gate_matrix_7cae_donor/`.

Repetindo somente com código G, as mesmas entradas ADC e 2,4 milhões de
ticks, a resposta do latch depende da rotação simulada. Cada mediana abaixo
vale para `P5.0` e `P5.1` após pelo menos 27 intervalos baixos em cada
caso; `A4h` é o último valor registrado em RAM superior.

| RPM injetado | Período P5 (ticks) | Baixo G→G+S88 (ticks) | `A4h` G→G+S88 |
| ---: | ---: | ---: | --- |
| 750 | 79.200 | 1.860→1.940 | 9Ah→A2h |
| 1.000 | 59.400 | 1.861→1.921 | 9Ah→A2h |
| 1.500 | 39.600 | 1.767→1.766 | 95h→9Dh |

A mudança em `A4h` persiste nos três pontos, mas o efeito de largura
praticamente desaparece a 1.500 RPM. Assim, a matriz participa de um
caminho dependente do estado; esses ensaios não autorizam uma correção
fixa em milissegundos para todos os regimes. Capturas adicionais:
`build/ma17-analysis/variants/air_gate_matrix_7cae_rpm_repeat/`.

O par de rastros G a 1.000 RPM restringe o caminho intermediário: a troca
da matriz deixou `IRAM[31h]=10h` igual, mas mudou `IRAM[69h]` de `A2h`
para `A5h` na escrita de `3B06h` e `IRAM[34h]` de `A8h` para `34h` na
escrita de `051Ch` (`35h=FFh` em ambos). O assembly confirma que `0439h`
lê `69h`, multiplica por `0Fh` e usa o resultado no serviço que calcula
as recargas; `051Ch/051Eh` gravam `34h:35h`, que o Timer 1 carrega. Esse
encadeamento é compatível com o contraste dos intervalos baixos em P5.
Em S88, a troca inversa também mudou `69h` (`A5h→A1h`) e `34h`
(`34h→2Fh`), embora a mediana P5 permanecesse 1.921 ticks. Logo, a
coincidência de mudanças em RAM e reload não prova que só `69h` determine
a largura observada; a seleção de caminho e o estado do temporizador
também precisam ser examinados.

Um cruzamento controlado isolou esse elo no G nas três rotações ensaiadas.
O override de `RAM[69h]` age em `043Bh`, antes das leituras no serviço IEX3;
os logs confirmaram `RAM[47h]=1Eh/28h/3Ch` em 750/1.000/1.500 RPM.
O estado de inicialização `47h=00h` foi excluído do override e o teste
verifica que não aparece um marcador de intervenção nesse estado.
Sem doadora, forçar o valor de `69h` observado com a matriz S88 reproduziu
a recarga `34h` e a largura P5 do doador. Com a doadora ativa, forçar o
valor nativo restaurou os dois resultados do G. Os valores abaixo são
recarga final `34h` e mediana baixa de ambos os latches P5, em ticks:

| RPM | G nativo + `69h` do doador | G com doador + `69h` nativo |
| ---: | --- | --- |
| 750 | `A5h` → `17h`, 1.940 | `A2h` → `B2h`, 1.860 |
| 1.000 | `A5h` → `34h`, 1.921 | `A2h` → `A8h`, 1.861 |
| 1.500 | `A4h` → `04h`, 1.766 | `9Ch` → `F1h`, 1.767 |

A ROM ativa permaneceu íntegra. Esse fatorial demonstra mediação por
`69h` **nos três estados digitais ensaiados**, sem provar que seja o único
mediador em todas as condições nem determinar o papel de `A4h`. O teste é
`VariantTraceTests.test_7cae_p5_width_is_mediated_by_ram69_at_tested_rpms`;
capturas em `build/ma17-analysis/variants/air_gate_matrix_7cae_ram69_factorial/`
e `build/ma17-analysis/variants/air_gate_matrix_7cae_ram69_rpm_factorial/`.

O limite provisório pelo próximo alvo do diretório **não é um limite seguro de
tabela**. O exemplo concreto é `7048h→7581h`: `704Eh→7617h` cai 150 bytes
depois da base, exatamente dez linhas de 15 células. O próximo início
independente é `704Ah→7662h`, 225 bytes após `7581h`. O mesmo padrão ocorre
em `7662h/76F8h/7743h` e `7743h/77D9h/7824h`. Na rotina `1344h..1378h`,
o eixo `47h` tem 15 segmentos; o segundo eixo escolhe uma tabela de 11
segmentos em `755Ch` ou de cinco em `7569h`, segundo o bit `2Eh.6`.
A seleção também muda o ponteiro de base para a subvisão de cinco linhas,
com uma linha de transição compartilhada. Assim, as três matrizes são
grades brutas de **15×15**, das quais as subvisões começam na linha 10.
Os dois cabeçalhos em `755Ch` e `7569h` selecionam `IRAM[6Fh]`; seus
respectivos contadores são `0Bh` e `05h`. O scanner associa `6Fh` à
borboleta combinada, ainda sem confirmação funcional neste cenário.
Com o ADC corrigido, dois ensaios G a 1.000 RPM, ADC2/3=`140/34` e
ADC0/6=`40/180` ou `120/180` registraram 386 leituras `MOVC` do
cabeçalho `755Ch=6Fh` em `527Dh`, por caso, em quatro milhões de ticks.
Nenhum acesso a `7569h` apareceu nessas capturas; a ausência vale apenas
para os dois estados testados. Capturas:
`build/ma17-analysis/variants/7939_tps_factor_adc0_{40,120}_adc6_180_control/`.
No mesmo perfil G, com ADC2/3=`140/34`, quatro milhões de ticks e
ADC0/6=`40/220` ou `180/247`, o flag `2Eh.6` estava ativo nas
passagens tardias por `115Fh`. Em cada execução, `527Dh` leu o
cabeçalho `755Ch` uma vez na partida e `7569h` **385 vezes**;
`5289h` também leu os incrementos `756Eh=44h` e `756Fh=4Dh`
385 vezes cada. Esse é acesso natural no emulador G à subvisão de
cinco segmentos, condicionado aos estímulos digitais testados.
Capturas: `build/ma17-analysis/variants/tps_7569_current_{40_220,180_247}/`.
O teste lento `test_iram6f_segment_7569_is_selected_in_corrected_tps_states`
contrasta esses dois casos com `40/180`, que mantém `2Eh.6=0` e
continua lendo `755Ch`. Com ADC0=40 fixo, a varredura de borda
ADC6=`215/216/217/218` leu `7569h` em `0/0/385/385` passagens e
mostrou `R4=D7h/D8h/D9h/DAh` em `115Fh`. O código original em
`118Ch..11A8h` lê `ROM[7568h]=35h`, calcula `−35h+0Dh=D8h` e,
em `11A1h..11A6h`, escolhe o ramo alternativo quando `R4>D8h`
nesse caminho. As capturas estão em
`build/ma17-analysis/variants/tps_7569_boundary_adc6_{215,216,217,218}/`.
A plausibilidade elétrica dos pares TPS
e a frequência dessa seleção numa ECU física permanecem abertas.

Uma grade G de 25 pares ADC0/6, com 1.000 RPM, ADC2/3/7=`140/34/63`
e quatro milhões de ticks por par, mediu o `MOVC` efetivo e o último
`IRAM[6Fh]`. Em cinco células, todas com ADC6=235, o firmware leu o
cabeçalho alternativo `7569h` 385 vezes. Em nove células, leu
`ROM[72A1h]=34h` em `PC116Fh` também 385 vezes e terminou com
`6Fh=27h`; nas outras 11 células selecionou somente `755Ch` após a
partida. O [mapa de ADC0/6 e 6Fh](../build/ma17-analysis/variants/tps_surface_current/tps_surface.png)
mostra os bytes brutos e os bancos; JSON e 25 logs estão em
`build/ma17-analysis/variants/tps_surface_current/`.
Com ADC0=160 ou 200, a borda ADC6=`223→224` mudou `RAM[28h]` de
`06h` para `00h` no probe de `115Fh`, `R4` de `34h` no ramo normal
para `E0h` antes do alternativo e as leituras `755Ch/7569h` de
`386/0` para `1/385`. No ramo alternativo, `11A8h..11B6h` calculou
`max(0,min(255,R2+13)-R3)`; os cinco casos ADC6=235 tiveram
`R3=1Ah`, `R2=ADC0` e `6Fh=ADC0−13`. A
[imagem da borda](../build/ma17-analysis/variants/tps_surface_boundary_current/tps_surface.png)
e os quatro logs preservam as duas linhas ADC0=160/200.
O fallback é causal no estado G ADC0/6=`160/200`: fornecer `34h`
original, `44h` ou `24h` apenas ao retorno `MOVC 116Fh/72A1h`
produziu `6Fh=27h/37h/17h`, mantendo 386 leituras de `755Ch` e a
ROM intacta. Capturas `tps_clamp_{native,sham,plus16,minus16}/`;
regressão `TpsClampTests.test_single_movc_return_controls_fallback_iram6f`.
Esses limites são digitais; as posições físicas das duas pistas TPS e
o comportamento da família A ainda não estão validados.
No mesmo perfil Fiat, a ROM S88 original reproduziu **25/25** bytes
finais de `6Fh`, contagens exatas dos cabeçalhos `755Ch/7569h` e
amostras aritméticas do ramo alternativo da grade G. Os quatro pontos
ADC0=160/200 e ADC6=223/224 também coincidiram, inclusive a fronteira
`386/0→1/385` leituras. A substituição pontual de `72A1h` repetiu em
S88 os quatro resultados G `27h/27h/37h/17h`, com ROMs originais
intactas. Reproduza com
`python3 tools/audit_ma17_tps_surface.py --variant S88`; artefatos
`tps_surface_s88_{current,boundary_current}/`
e `tps_clamp_s88_{native,sham,plus16,minus16}/`. A regressão
`TpsClampTests.test_g_and_s88_share_high_adc0_segment_boundary` cobre
dois pares de borda nas duas ROMs. A equivalência vale para esses
estímulos digitais e para o modelo de hardware Fiat testado.
`python3 tools/compare_ma17_tps_surfaces.py` valida que os estímulos e
o hash do emulador coincidem e registra **zero diferenças** nos 25
pares em `tps_surface_g_s88_comparison.json`; a comparação dos quatro
pontos de borda está em `tps_surface_boundary_g_s88_comparison.json`.
Separadamente, `Sab80C517.SixRomTpsFallbackMovcReadsOriginalByte`
executa `116Dh..1170h` dos seis binários originais com `DPTR=7200h`:
todos leem `ROM[72A1h]=34h` e deixam `R4=34h` em `1171h`. Isso confirma
o leitor local da família A, sem validar seu boot no perfil Fiat.
Na borda `216→217`, o `MOVC` da matriz em `532Fh` leu a mesma
célula `761Ah=AEh`: com `216`, por `DPTR=7581h` e `A=99h`; com
`217`, por `DPTR=7617h` e `A=03h`. Em `217`, o interpolador também
leu a linha seguinte (`7629h=B4h`, `762Ah=B7h`), ausente após a
partida em `216`. Nos rastros G de 1,2 milhão de ticks, `137Bh`
observou `R2:R3=AE0Ah→AEB4h` **antes** de `MOV R2,B; MOV R3,A`.
Após instrumentar também `B` e repetir as condições com a ROM original,
o resultado dominante correto em `A:B` foi `AE00h→B2E0h` (92/107
amostras estáveis em 216; 93/108 em 217). `RAM[48h]` corrente mudou
`41h→43h`, e a mediana do pulso baixo CC3 modelado foi 4744→4869 ticks.
Capturas corrigidas: `build/ma17-analysis/variants/tps_7569_matrix_adc6_{216,217}_ab/`.
Os antigos `R2:R3` são estados intermediários, não o resultado do lookup.
Capturas pré-correção de formato: `build/ma17-analysis/variants/tps_7569_matrix_adc6_{216,217}/`.
ADC6 e os estados intermediários mudam juntos nessa comparação;
ela não isola o efeito causal do ponteiro sobre a saída CC3.
Um teste isolado dos opcodes originais G em `1344h..137Bh` manteve
`RAM[47h]=28h` e `RAM[6Fh]` fixo em `1Bh` ou `CBh`, alternando apenas
`2Eh.6`. Antes da chamada ao interpolador, `DPTR` escolheu `7048h`
ou `704Eh`; o resultado `A:B` em `137Bh` foi diferente nas duas escolhas
para **ambos** os valores fixos de `6Fh`. As duas instruções seguintes
copiam o resultado para `R3:R2`. O teste
`Sab80C517.FiatMatrixSubviewFlagChangesLookupWithFixedIram6f`
confirma o efeito digital do seletor no código original, sem demonstrar
que qualquer um dos estados artificiais reproduza a saída de uma ECU.
Um segundo controle, `Sab80C517.FiatMatrixSubviewPointerAloneChangesLookup`,
inicia no `LCALL 5323h` em `1378h` com ROM, registradores e `RAM[57h]=0`
idênticos. Só o slot inicial de `DPTR` muda de `7048h` para `704Eh`;
o código original resolve `7581h` ou `7617h` em `532Fh` e retorna
valores `A:B` diferentes em `137Bh`. Com índice local `R5=03h`,
as primeiras células lidas são `7584h=26h` e `761Ah=AEh`.
Isso isola a contribuição do ponteiro sob entradas controladas, sem
atribuir ao ensaio uma condição natural de operação ou efeito físico.
Essa geometria foi demonstrada para `G`. Na revisão A/A+/S37/S36, o
bloco `1386h..13CBh` é idêntico entre as quatro ROMs: `2Bh.7` escolhe
`7048h→7581h` ou `704Ah→7662h`, enquanto `2Eh.6` troca esses ponteiros
por `704Eh→7617h` ou `7050h→76F8h`, as visões que começam na linha 10.
O teste isolado `Sab80C517.AlcoholCodeSelectsFourMatrixViewsByFlags`
executa A e S37 com linha 0, coluna 4 e frações zero. Os bytes retornados
pelas quatro escolhas são `25h/25h/ABh/ABh` em A e
`39h/25h/BFh/C2h` em S37. Isso confirma os consumidores e as visões
nessas revisões, sem demonstrar a frequência natural dos flags nem a
função física das matrizes.
O produtor direto de `2Bh.7` aparece em `3CE8h..3D04h`, idêntico nas
quatro ROMs A/A+/S37/S36. Quando o estado anterior em `XRAM F9:85h`
é 4, `ROM[72E9h]=A0h` é comparado com `IRAM[47h]`: valores
`9Fh`/`A0h` ligam `2Bh.7`; `A1h` grava `15h` no estado e limpa o bit.
O teste isolado confirma ambos os ramos nas ROMs A e S37. Com
`XRAM F9:85h=0` e flags `28h.3/29h.3/28h.4` limpos, o bloco
`1339h..1378h` usa `ROM[72DFh..72E2h]=78h,5Ch,13h,0Dh` para colocar
o estado em 1 somente nas faixas `IRAM[63h]=0Eh..13h` e `5Dh..78h`.
Os pontos adjacentes `0Dh/14h/5Ch/79h` dão estado `10h`; ligar `28h.3`
produz estado `20h`. O teste cobre as oito bordas e o bloqueio nas ROMs
A/S37. `63h` é o valor digital já processado do ADC3; a correspondência
em graus Celsius continua hipotética.
Com `RAM[27h]` sem os bits de bloqueio e `2Fh.0=1`, estado 1 e contador
`XRAM F9:84h=0Eh` passam a estado 2 ao alcançar `72E3h=0Fh`.
Estado 2 com contador `31h` passa a estado 3 em `72E4h=32h` quando
`47h≤72E6h=58h`; `47h=59h` produz estado `12h` e limpa `2Bh.7`.
Estado 3 com contador `40h` alcança `72E5h=41h`;
`47h=53h..5Eh` passa pela janela `72E7h=52h`/`72E8h=5Eh`, grava
estado 4 e liga `2Bh.7`. Nos pontos adjacentes `52h` e `5Fh`, grava
estado `13h` e limpa o bit. Esses estados foram preparados no teste;
a entrada natural no estado 1 e a escala física de
`47h` ainda precisam ser determinadas.
Um ensaio integrado preserva a mesma CPU e os bytes originais da ROM
entre os blocos: amostra `A8h=60h` com `A9h=60h` passa por
`46E6h..4815h` e gera `63h=60h`; `1339h..1378h` entra no estado 1;
com `47h=55h` e contadores adiantados para um passo antes de cada
limite, `3C7Dh..3D04h` percorre `1→2→3→4` e liga `2Bh.7`.
Com `6Fh=14h` fixado no teste, `1378h..13C6h` calcula os dois eixos
sem forçar o índice: `R5=36` em A e `38` em S37. Ambas selecionam
`704Ah→7662h`, e `13C6h..13CBh` retorna `R3=1Ch` em A e `31h`
em S37. As tabelas do primeiro eixo são iguais até `757Fh`; o último
byte em `7580h` vale `10h`/`24h` e acompanha a diferença de índice.
O produtor A `1386h` usa `7046h→7570h`, cujo cabeçalho `47h` escolhe
o byte digital `RAM47h`, e grava o segmento/fração em upper IRAM `BCh`.
Na mesma CPU do ensaio, `RAM47h=55h` produziu nibble baixo `BCh=6/8`
em A/S37; repetir somente esse produtor com `47h=28h` deu `3/5`.
O teste varreu depois os **256 valores digitais** de `RAM47h` em ambas
as ROMs: a coluna observada em `BCh&0Fh` coincidiu sempre com o maior
segmento cujo início não excede `47h`. Os inícios brutos, derivados dos
incrementos originais de `7570h`, são:

| ROM | Inícios de coluna para índices 0–14 (`RAM47h` bruto) |
| --- | --- |
| A/A+ e G | `0,25,32,40,50,60,72,88,104,120,140,160,186,212,240` |
| S88 | `0,4,11,19,29,39,51,67,83,99,119,139,165,191,219` |
| S37/S36 | `0,5,12,20,30,40,52,68,84,100,120,140,166,192,220` |

A verificação por execução cobre A e S37; as demais linhas foram
calculadas diretamente das ROMs e conferidas pelo teste do gerador de
gráficos. Isso liga digitalmente `47h` ao índice consumido em `3329h`,
sem fixar a escala de RPM da revisão A em unidades físicas.
O mesmo teste mantém `2Bh.7` produzido nessa CPU após `13CBh` e,
preparando a guarda `22h.1` do leitor separado em `3384h`, executa seus
opcodes originais. A e S37 chegam a `53F2h` com `DPTR=7EACh`, índice
`4` e publicam `99h` em `R2` e upper IRAM `A4h`. Isso conecta o
produtor do flag ao leitor da curva constante em uma sequência controlada;
o salto entre blocos e os contadores adiantados não reproduzem um boot.
O resultado combina a diferença de eixo e os bytes da matriz;
não simula o tempo necessário para os contadores nem comprova uma
transição natural em boot completo, o valor natural de `6Fh=14h` ou
um efeito elétrico no injetor.
Um segundo teste inicia no consumidor `13C6h` com as duas tuplas
`(R5,R6,R4)=(36,D0h,10h)` e `(38,10h,10h)` medidas antes do lookup,
cruzando cada uma com as ROMs originais:

| ROM da matriz `7662h` | Eixo de A | Eixo de S37 |
| --- | ---: | ---: |
| A | `1Ch` | `1Ah` |
| S37 | `33h` | `31h` |

Nesse estado, trocar só a ROM da matriz acrescenta `17h` ao resultado
em ambos os eixos; trocar só a tupla de eixo reduz `02h` em ambas as
ROMs. A diferença líquida entre as combinações próprias é `+15h`
(`1Ch→31h`). Ao prosseguir pelo código original até a escrita em
`1571h`, com `RAM[7Ch]=7Eh` e XRAM auxiliar zerada, `IRAM[48h]` fica:

| ROM da matriz `7662h` | Eixo de A | Eixo de S37 |
| --- | ---: | ---: |
| A | `0Ah` | `09h` |
| S37 | `12h` | `12h` |

O mesmo teste mantém cada valor de `48h`, prepara as entradas auxiliares
da rotina e salta para `1E30h`. Os pares publicados em `RAM[14h:15h]`
em `1EF7h` são:

| ROM da matriz `7662h` | Eixo de A | Eixo de S37 |
| --- | ---: | ---: |
| A | `0130h` | `0140h` |
| S37 | `00F1h` | `00F1h` |

Assim, a diferença conjunta de eixo e células chega ao par publicado
sob as mesmas entradas controladas. A última etapa é um salto preparado
entre rotinas; o teste não demonstra que esse estado ocorra naturalmente.
O bloco `058Eh..05DCh` é byte a byte idêntico nas seis ROMs: ele lê
`14h:15h`, duplica o valor e programa `CCL3:CCH3`. Continuando o teste
com `TH2:TL2=2010h`, os quatro casos acima produzem, na mesma ordem,
`2270h`, `2290h`, `21F2h` e `21F2h` no registrador de comparação.
Com a CPU posta em idle, Timer 2 contando em modo de comparação e a saída
modelada iniciada em nível baixo, a borda alta em P1.3 ocorre após
608/640/482/482 ticks, respectivamente. Isso confirma o agendamento CC3
no código e no modelo do periférico. A inicialização da saída foi
controlada pelo teste; esses números não são largura de pulso da ECU nem
confirmam conexão física ao bico.

O firmware A lê `48h` em `1E34h`. Outro teste percorre o código original
de `1E30h` até a publicação de `RAM[14h:15h]` em `1EEFh`, mantendo
`R3:R2=00C0h`, `DPTR=7200h`, `XRAM[F869h]=40h`, `XRAM[F88Dh]=FFh`,
`XRAM[F808h]=80h` e `IRAM[9Dh]=FFh`. Variar somente `48h` entre os
valores observados acima produz:

| `RAM[48h]` | `R3:R2` em `1E5Ch` | `RAM[14h:15h]` em `1EF7h` |
| ---: | ---: | ---: |
| `09h` | `00A1h` | `0140h` |
| `0Ah` | `0099h` | `0130h` |
| `12h` | `0079h` | `00F1h` |

O ensaio demonstra que, nessas entradas controladas, o valor da matriz
alcança o par publicado pela rotina. O teste parte de `1E30h`, com
estado preparado; não representa a execução natural desde o reset nem
mede duração de CC3 ou pulso do bico. A relação física com o atuador
ainda precisa de rastreamento e validação separados.

Nas matrizes inteiras, `S88` altera 225/225, 211/225 e 211/225 células
em relação a `G`; `A/A+` preservam as matrizes de `7581h` e `7743h`, mas
alteram 209/225 células em `7662h`. A contagem anterior de 150 bytes
alterados em `7581h..7616h` descrevia apenas a parte antes do ponteiro
interno e subestimava a diferença total da matriz.
O catálogo de diferenças por célula mostra que `S88[7581h..7661h]` é
**G+21 em todos os 225 bytes**. Na matriz `7662h`, 204 bytes são G+26;
14 bytes iniciais não mudam e sete células próximas a `FFh` sobem menos,
com saturação aparente. Em `7743h`, os primeiros 14 bytes não mudam e
os outros 211 são G+8. Esses são deltas aritméticos de bytes brutos:
a escala física, eventual sinal e motivo da transformação continuam
desconhecidos. `matrix_deltas.json` contém as grades e distribuições
completas para as seis imagens.

Os mapas [7662h, G/S88](../build/ma17-analysis/variants/matrix_plots/matrix_7662_g_vs_s88.png)
e [7743h, G/S88](../build/ma17-analysis/variants/matrix_plots/matrix_7743_g_vs_s88.png)
permitem verificar a silhueta por linha. A relação exata em cada uma é:
as células de índice 0–13 ficam iguais às de G; a partir do índice 14,
`S88[7662h+i]=min(255,G[7662h+i]+26)` e
`S88[7743h+i]=G[7743h+i]+8`. O teste automatizado confere os 225 bytes
de cada matriz. O [contraste interno S88 7662h/7743h](../build/ma17-analysis/variants/matrix_plots/matrix_7662_s88_vs_7743_s88.png)
mostra que diferenças preexistentes entre as duas tabelas de G também
contribuem; a distância entre os dois estados S88 não é constante.

### Seleção experimental das três matrizes em `7581h..7823h`

Nas 18 execuções corrigidas G/S88 de RPM, ADC e TPS, as 230–231 consultas
à rotina `1378h` por cenário tinham `IRAM[57h]=00h`. Um trace adicional
da ROM G não observou escrita que alterasse `57h` em 2,4 milhões de
ticks. O harness ainda não reproduziu a condição natural que seleciona
`7662h` ou `7743h`.
Uma execução G prolongada até 24 milhões de ticks registrou 2.340
consultas, todas com seletor `00h`, e nenhuma mudança de `57h`.
Outro ensaio enviou o estímulo inicial de 5 baud pela K-Line durante
seis segundos; nas 581 consultas observadas, o seletor também ficou
em zero. Esse ensaio não enviou requisições posteriores do scanner.
Um par novo com o executável SHA-256 `1c0b13f3…28804` executou G e S88
por 12.000.000 ticks cada (cerca de 12,12 s nominais no perfil Fiat),
sem sessão K-Line nem overrides, a 1.000 RPM e ADC0..7 bruto
`100/130/100/20/90/40/155/63`. O rastreador de alterações da IRAM
inferior não registrou transição de `57h` em nenhuma das duas ROMs.
No `MOVC @A+DPTR`, G fez 2.374 leituras com base `7B46h` e S88 fez
4.666; não houve leitura com base `7BBEh`, `7C36h`, `7CAEh`, `7D26h`
ou `7D9Eh` nesse par. As bases distinguem seleção direta de uma leitura
que cruza a borda de outra matriz. Os relatórios em
`build/ma17-analysis/variants/iram57_long_current_{g,s88}/` guardam
os hashes das ROMs, do executável e os 990.000 ticks/s. A ausência de
seleção vale para esse estado emulado e não demonstra que os modos 1/2
sejam inacessíveis em outros estados ou por diagnóstico.
Para reproduzir, fixe `MA17_ADC_CH0..7` nos oito valores acima e execute
`python3 tools/trace_ma17.py --no-kline-inject --crank-immediate --rpm 1000
--stop-ticks 12000000 --seconds 60 --trace-movc --output-dir
build/ma17-analysis/variants/iram57_long_current_g`. Repita com
`--firmware 'firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin'`
e o sufixo `_s88` no diretório de saída. O valor de `--seconds` limita
o tempo de parede; a duração comparável é `--stop-ticks`.
Nos seis binários, as ocorrências verificadas do opcode direto
`MOV 57h,#00h` estão em `0B0Fh` e `3B94h` (G/S88) ou `3BC2h`
(A/A+/S37/S36). Nenhuma ROM contém `MOV 57h,#01h/#02h`. Todas contêm
`MOV 57h,#5Ah` em `601Dh` e `MOV 57h,B` em `6078h`, dentro do modo
diagnóstico alternativo iniciado em `6004h`; essa sequência preserva
o marcador `5Ah` durante o teste de RAM. A busca de opcodes diretos não
elimina possíveis escritas indiretas nem comprova que os modos 1/2 sejam
inatingíveis. `CompareVariantsTests.test_all_six_roms_keep_ram57_direct_writers_separate_from_mode_selector`
verifica os bytes e endereços das seis imagens. Capturas:
`build/ma17-analysis/variants/ram57_long_baseline/` e
`build/ma17-analysis/variants/ram57_kline_probe/`.

Uma grade adicional sem overrides e sem K-Line combinou G/S88,
1.000/3.000 RPM, ADC0/6 `40/95` ou `180/247`, ADC3 `20/232`,
ADC2=160 e ADC7=63, por 2,4 milhões de ticks em cada um dos 16 casos.
Todos alcançaram `1378h`, sem transição de `RAM[57h]`. O comando
`python3 tools/audit_ma17_ram57_grid.py` reproduz a grade e grava
`build/ma17-analysis/variants/ram57_grid_current/ram57_grid.json` mais
um log por caso. O JSON fixa hashes das ROMs e do executável, parâmetros
e duração; o executável medido foi
`c4565e7707815c8afcdb47b9353f8355ca283f8355cf2417d5267bcdc7f0f9ab`.
São estímulos digitais no perfil Fiat, sem validação física das pistas
TPS nem cobertura da família A. A ausência de mudança não exclui seleção
por outros estados ou comandos de diagnóstico.

O estímulo opcional `MA17_OVERRIDE_RAM57=0/1/2` altera esse byte somente
antes de `1378h` em todos os estados de `RAM[47h]`, preservando os bytes
das ROMs.
Com `ADC0/ADC6/ADC7=40/95/63`, 1.000 RPM e 2,4 milhões de ticks,
o trace confirmou leituras `MOVC` da matriz selecionada:

| ROM | `57h` forçado | matriz | resultado dominante em `137Bh` | `48h` final | `14h:15h` mediana | CC3 baixo modelado |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| G | 0 | `7581h` | `59F0h` | `21h` | 763 | 3041 |
| G | 1 | `7662h` | `6E20h` | `28h` | 920 | 3669 |
| G | 2 | `7743h` | `6E20h` | `28h` | 920 | 3669 |
| S88 | 0 | `7581h` | `5530h` | `1Fh` | 727 | 2897 |
| S88 | 1 | `7662h` | `6090h` | `23h` | 815 | 3249 |
| S88 | 2 | `7743h` | `4E90h` | `1Ch` | 675 | 2689 |

Nos modos 1/2, as 920 leituras foram da matriz selecionada, inclusive
antes de `RAM[47h]=28h`. A mudança
do seletor altera também outras consultas que usam `57h`; portanto esta
comparação demonstra o efeito do **estado selecionado**, ainda sem isolar
a contribuição das células de cada matriz. O caminho físico que produz
`57h=1/2` continua desconhecido. Relatórios e hashes estão em
`build/ma17-analysis/variants/ram57_matrix_probe/`; o teste reproduz as
seis linhas da tabela.
As capturas iniciais `selector57_trace/gasoline` e
`selector57_trace/sun8817` são inválidas: a primeira versão do monitor
de `57h` tinha um vetor de histórico curto e gerou eventos espúrios.
O vetor agora deriva o tamanho da lista de endereços; a captura corrigida
é `selector57_trace/gasoline_fixed`.

Para isolar as **células** das matrizes alternativas, outro ensaio manteve
a ROM ativa, `RAM[57h]`, RPM e ADCs constantes e trocou somente o byte
entregue por `MOVC` no intervalo da matriz escolhida pelo byte homólogo
da outra ROM. O trace bruto continuou mostrando o byte da ROM ativa,
e os hashes das duas imagens foram registrados:

| ROM ativa | matriz | origem do byte `MOVC` | lookup dominante, próprio→troca | `48h`, próprio→troca | `14h:15h`, próprio→troca | CC3 baixo, próprio→troca |
| --- | --- | --- | --- | --- | ---: | ---: |
| G | `7662h` | S88 | `6E20h→8820h` | `28h→31h` | 920→1121 | 3669→4473 |
| G | `7743h` | S88 | `6E20h→7620h` | `28h→2Bh` | 920→982 | 3669→3917 |
| S88 | `7662h` | G | `6090h→4690h` | `23h→19h` | 815→613 | 3249→2441 |
| S88 | `7743h` | G | `4E90h→4690h` | `1Ch→19h` | 675→613 | 2689→2441 |

Isso demonstra contribuição causal das diferenças dessas matrizes para
a temporização **modelada** sob os estados `57h=1/2` forçados. Ainda
falta identificar a condição real que coloca a ECU nesses modos e
confirmar a ligação elétrica do CC3 ao atuador. Relatórios:
`build/ma17-analysis/variants/matrix_donor_probe/`.

Para reproduzir um dos pares G/S88 (a ROM ativa continua sendo G):

```sh
MA17_OVERRIDE_RAM57=1 MA17_OVERRIDE_MOVC_MATRIX_BASE=7662 \
MA17_OVERRIDE_MOVC_MATRIX_ROM='firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin' \
MA17_ADC_CH0=40 MA17_ADC_CH6=95 MA17_ADC_CH7=63 \
python3 tools/trace_ma17.py --trace-movc --trace-lookup --no-kline-inject \
  --crank-immediate --rpm 1000 --stop-ticks 2400000 --seconds 30 \
  --output-dir build/ma17-analysis/variants/matrix_donor_probe/reproduction
```

Há uma cadeia de consumo adicional na ROM `G`: após `1378h`, o resultado
da interpolação vai para `R2:R3`; o caminho padrão soma `XRAM[92h:93h]`
em `14C2h`, multiplica por `IRAM[7Ch]` e grava `IRAM[48h]` em `1523h`.
Mais adiante, `1E18h` usa `IRAM[48h]` numa multiplicação antes da escrita
de `IRAM[14h:15h]` em `1ED5h..1ED7h`. Todos esses PCs apareceram no
ensaio de 1.000 RPM, e `IRAM[48h]` terminou em `40h` nas duas ROMs.
O resumo de mudanças da RAM não monitora `14h:15h`; a entrada CC3,
porém, registrou 75 valores não nulos por ROM em 2,4 milhões de ticks.
A cadeia chega à temporização CC3 modelada, ainda sem demonstração causal
do efeito das células alteradas ou da ligação física do pino ao bico.

Um ensaio de TPS com `ADC7=63`, 1.000 RPM e três pares `ADC0/ADC6`
(`120/95`, `40/40`, `180/180`) completou 49 voltas por caso em três
segundos. `IRAM[60h]` e `IRAM[66h]` acompanharam os estímulos, e houve
94 amostras da entrada CC3 em cada execução. Mesmo assim, `IRAM[6Fh]`
terminou em `27h`, `IRAM[48h]` em `40h` e a tabela alternativa `7569h`
não foi lida. O resumo de RAM desse ensaio não monitorava `14h:15h`;
as amostras CC3 não permitem concluir ausência de agendamento.
O resultado delimita o estado alcançado pelo harness nesse intervalo;
não demonstra ausência de dependência do TPS em operação estabilizada.
Uma grade histórica, anterior ao conserto do ADC, indicava que `40/40`
e `180/180` caíam em um caminho de substituição. Com pares `40/95` e
`120/180`, `IRAM[6Fh]` terminava em `53h` e `A8h`, respectivamente.
Esses valores não devem ser misturados com a grade ADC corrigida.

`S37` e `S36` diferem em cinco bytes: `0x004C`, `0x004E`, `0x0050`,
`0x0054` e `0x0055`. Em `S37`, `0x0053..0x0055` contém `02 00 B0`
(`LJMP 00B0h`); em `S36`, contém `02 AA 0D` (`LJMP AA0Dh`). Todo o
conteúdo `6E00h..7FFFh` é idêntico entre essas duas imagens; portanto,
não há diferença de bytes de calibração entre S37 e S36. O destino
`AA0Dh` está além de 32 KiB. Esse vetor corresponde a `IEX3` no mapa C517;
executabilidade e consequência em hardware dependem da variante e do
estado de habilitação. Três bytes `FF` próximos também mudaram. Tratar `S36`
como equivalente funcional de `S37` seria incorreto sem investigar esse vetor.
As cinco mudanças contribuem `−85−5−85+170−163=−168` para a soma de
bytes, exatamente `37A5h→36FDh`. A coincidência com o sufixo do nome
não prova que a edição visasse um checksum. Se o pino A15 da EPROM de
32 KiB não for decodificado, `AA0Dh` espelha `2A0Dh`; nessa imagem,
`2A0Dh` é o **segundo byte** da instrução que começa em `2A0Ch`
(`30 38 04`, `JNB`). O comportamento no hardware real depende da
ligação da EPROM e da habilitação de `IEX3`. O teste
de round-trip atual classifica 22.282 bytes como código na S36 por
entrada natural, contra 23.615 na S37. Com `--entry 0x00B0` adicional,
a S36 também classifica 23.615 bytes como código e remonta os mesmos
32.768 bytes com SHA-256 idêntico; 1.333 bytes do serviço e de rotinas
alcançadas por ele ficam disponíveis para inspeção comparativa. O
vetor S36 continua `LJMP AA0Dh` nos dois assemblies. A entrada manual
**não demonstra** que esse serviço seja alcançável na S36 real. Reproduza
com `python3 tools/roundtrip_8051.py 'firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin' --entry 0x00B0`;
regressão: `test_s36_shared_iex3_code_can_be_inspected_without_changing_vector`.
O teste
`Sab80C517.Sun36Iex3VectorLeaves32KiBRom` arma `EA`, `EX3`,
`IP1.2` (como no boot observado) e `IRCON.IEX3` e executa a interrupção
nas duas ROMs originais. O PC chega a `00B0h` em S37 e `AA0Dh` em S36;
no modelo do emulador, que mascara endereços de código com `7FFFh`,
o próximo byte de S36 seria `ROM[2A0Dh]=38h`, operando de uma instrução
iniciada em `2A0Ch`. Esse ensaio demonstra a divergência do vetor no
modelo de ROM de 32 KiB, não o comportamento elétrico da placa.
O teste usa a prioridade 2 do boot: o emulador atual não seleciona
`IEX3` com prioridade 0 porque inicia a prioridade candidata em zero
e exige `pri > highest_priority` nesse ramo de `core.c`. Essa limitação
não altera o ensaio acima, mas restringe simulações com `IP1.2=IP0.2=0`.
O código comum de S37/S36 em `07B6h..07E2h` contém `SETB IEN1.2` em
`07E1h`, habilitando `EX3` depois de uma condição de estado. Assim, o
vetor alterado pode ser alcançado por uma interrupção habilitada; a
frequência e as pré-condições desse caminho durante partida real ainda
não foram medidas. Essa diferença é de **código de interrupção**, não
uma célula de calibração.

## Ensaio controlado inicial: G versus S88

**Revisão de fidelidade do emulador:** o opcode `86h` (`MOV direct,@R0`)
estava invertido no núcleo e escrevia em `@R0` em vez de ler dele. A
correção possui teste para `86h/87h` e `A6h/A7h`. Medidas de injeção e
da guarda em `1558h` obtidas antes dela são inválidas. Os números de
CC3 abaixo foram refeitos com o núcleo corrigido; os artefatos anteriores
em `build/ma17-analysis/variants/experiments/` servem apenas à auditoria
do erro. A grade válida está em `experiments_opcode86_fixed/`.

`tools/trace_ma17.py` aceita `--firmware` somente quando os 32768 bytes e o
trecho `0x0000..0x757F` coincidem com `G`; o relatório registra o SHA-256
da imagem executada. Para repetir o ensaio, rode duas vezes cada comando:

```sh
python3 tools/trace_ma17.py --seconds 2 --no-kline-inject --crank-immediate --rpm 1000 --output-dir build/ma17-analysis/variants/trace_gasoline
python3 tools/trace_ma17.py --firmware 'firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin' --seconds 2 --no-kline-inject --crank-immediate --rpm 1000 --output-dir build/ma17-analysis/variants/trace_sun8817
```

Com ADCs padrão, ambos os relatórios observaram 58 dentes e duas lacunas
por volta, período de 59400 ticks nos canais P5.0/P5.1 e alternância dos
canais. A mediana da largura baixa em cada canal foi `1861` ticks em `G`
e `1921` em `S88`, nas duas repetições. O teste de 1,2 s capturou uma
fase transitória (`1863` ticks em `S88`), então a regressão usa 2 s.
`RAM[31h]` terminou em `10h` nos dois rastros; essa observação não liga a
diferença de P5 diretamente às três tabelas `0x7ED9..0x7F8C`.
Arquivos `execution.json` e `emulator-trace.log` de cada condição ficam nos
respectivos diretórios de saída. A medição é no emulador, não em hardware
real; a origem da diferença de 60 ticks exige tracing de `MOVC` e teste de
causalidade por região.

## Leituras `MOVC` observadas

O harness aceita `MA17_TRACE_MOVC=1`; `tools/trace_ma17.py --trace-movc`
ativa o recurso e grava em `execution.json` os acessos agregados por PC,
opcode, DPTR, ACC, endereço efetivo, offset mapeado e valor. O wrapper chama
o handler original e valida cada valor contra a ROM carregada. O trace é
opcional e não altera o valor de retorno ou os ciclos da instrução.
Para repetir a comparação, acrescente `--trace-movc` aos dois comandos acima.
`--trace-lookup` agrega o estado no PC `137Bh`, imediatamente após o retorno
de `5323h`: `IRAM[47h]`, `IRAM[6Fh]`, seletor `57h`, flags `2Eh`,
`R0/R4/R5/R6` e resultado `A:B`. As duas instruções seguintes copiam
`B` para `R2` e `A` para `R3`. Os registros são capturados antes dessas
instruções e o modo também é opcional.

No ensaio de 2,2 s a 1.000 RPM, ambas as imagens completaram 35 voltas.
A região alterada `0x7580..0x7661` recebeu 1045 leituras agregadas por
PCs `5289h`, `532Fh`, `5333h`, `534Bh` e `5350h`. Em particular, o
`MOVC` em `5289h`, com `DPTR=7571h` e `ACC=0Fh`, leu `7580h` 209 vezes:
`10h` em `G` e `25h` em `S88`. O diretório `7046h→7570h` e a chamada a
`5279h` em `1344h` ligam essa leitura à tabela cujo cabeçalho seleciona
`IRAM[47h]` (RPM). Isso confirma um acesso dependente da rotina de segmentos;
o significado físico da tabela ainda não foi demonstrado.

O teste `FiatRpmSegmentVariantsChangeMatrixColumnBeforeLookup` executa
apenas `1344h..136Eh` das ROMs originais com `IRAM[47h]=28h` e
`IRAM[6Fh]=27h`. Antes de ler a matriz, `R5` vale `30h` em `G` e `32h`
em `S88`; os 17 bytes da tabela `7570h` diferem somente no último
incremento (`10h` contra `25h`). No trace completo de 1.000 RPM, os
`MOVC` estáveis em `532Fh` confirmam esses índices sobre `DPTR=7581h`.
Portanto, a alteração de `7580h` muda causalmente o índice da matriz
em condição controlada. As células da matriz também diferem entre ROMs,
então a contribuição de cada mudança ao resultado final ainda está aberta.

O `MOVC` em `5289h`, com `DPTR=7B3Fh` e `ACC=06h`, leu `7B45h` 209 vezes:
`05h` em `G` e `0Dh` em `S88`. Esse byte pertence à tabela apontada por
`70ACh→7B3Eh`, cujo cabeçalho seleciona `IRAM[7Dh]`, derivada do ADC de
alimentação. As outras três regiões alteradas tiveram zero leituras neste
cenário; ausência de leitura aqui não prova que sejam inacessíveis em outras
condições. A primeira fatia candidata `7ED9h..7F14h` recebeu 420 leituras
em ambas as imagens e contém bytes iguais. As fatias `7F15h..7F50h` e
`7F51h..7F8Ch` não foram lidas neste ensaio.

`IRAM[31h]` e `IRAM[68h]` terminaram, respectivamente, em `10h` e `75h`
nas duas imagens; `IRAM[69h]` e P5 apresentaram diferenças. O rastreio
e dois contrafactuais controlados da cadeia de `69h` aparecem abaixo.

#### Caminho da tabela de RPM até `IRAM[69h]`

Com 1.000 RPM, `ADC7=63`, 2.400.000 ticks e o núcleo com `MOV 86h/87h`
corrigido, `IRAM[47h]=28h` nas duas ROMs. O código original em `1344h`
consulta o segmento apontado por `7046h→7570h` e grava na RAM superior
`BCh` um índice inteiro e uma fração compactados. No tick 286.675 de G,
`BCh=03h`; no tick 286.690 de S88, `BCh=15h`. O último incremento do
segmento em `7580h` é `10h` em G e `25h` em S88. O teste isolado de
`1344h..136Eh` confirma que esse byte altera a seleção com `47h=28h`.

Em `330Dh..3371h`, o firmware separa os nibbles de `BCh` e chama o
interpolador `5329h` com o ponteiro `70C2h→7ECAh`. Essa tabela de 15
bytes é **idêntica nas seis ROMs**. O `MOVC` em `532Fh` leu `7ECDh=97h`
em G e `7ECFh=86h` em S88; o segundo `MOVC` em `5333h` leu,
respectivamente, `7ECEh=8Eh` e `7ED0h=80h`. Em `3371h`, o resultado
`R2` foi `97h` e `86h`. Logo, neste estado, a diferença de resultado vem
da seleção da mesma tabela, não de uma alteração em seus bytes.
O teste `Sab80C517.FiatRpmSelectorChangesSharedTableLookup` executa
`330Dh..3370h` com os opcodes originais, cruzando **as duas ROMs com os
dois seletores**. Em ambas, `BCh=03h` produz leituras
`7ECDh/7ECEh` e `R2=97h`; `BCh=15h` produz `7ECFh/7ED0h` e
`R2=86h`. Assim, a seleção isolada explica esse resultado, mesmo ao
trocar a ROM que fornece a tabela.

Em `3A04h`, antes da correção, `R2` vale `9Ah` em G e `89h` em S88;
ambas têm RAM superior `8Ch=A2h`. O caminho `3AD2h` lê
`ROM[7344h]=09h` nas duas ROMs. Em `3AE0h`, a escolha intermediária
é `F8h` em G e `F7h` em S88; em `3B06h`, o valor destinado a `69h`
é `9Ah` e `99h`. S88 passa depois por `90h` e `89h`; G estabiliza em
`9Ah`. O ramo com `DPTR=7F96h` não foi observado neste cenário.
O acesso `MOVC A,@A+DPTR` segue a especificação Siemens *SAB 80C517*,
"Instruction Set", p. 222 ([PDF local](../SAB80C517.PDF)); a sonda
`MA17_TRACE_RAM69=1` em `src/ma17/FirmwareProbes.cpp` registra o estado
**antes** da instrução em `3AD2h`. Os traces reproduzíveis estão em
`build/ma17-analysis/variants/ram69_ubc_path_opcode86_fixed/`.

Para testar a contribuição do seletor sem trocar de ROM, o harness aceita
`MA17_OVERRIDE_RPM_SELECTOR=03` ou `15` (hexadecimal). Só na entrada de
`330Dh`, quando `IRAM[47h]=28h`, ele substitui o byte `BCh` da RAM superior;
os bytes da EPROM, os sensores e o restante da RAM são preservados. A intervenção opcional
está em `src/ma17/FirmwareProbes.cpp`, antes da execução do opcode.
Um comando para cada valor é:

```sh
MA17_OVERRIDE_RPM_SELECTOR=15 MA17_ADC_CH7=63 MA17_ADC_CH1=130 \
  .venv/bin/python tools/trace_ma17.py \
  --firmware FiatTipo_MA17_dump_27c256.bin --no-kline-inject \
  --crank-immediate --rpm 1000 --stop-ticks 2400000 --seconds 20 \
  --output-dir build/ma17-analysis/variants/rpm_selector_counterfactual_validated/adc130_15
```

As quatro execuções abaixo usaram **a mesma ROM G**, 1.000 RPM e
`ADC7=63`; a tabela mostra a mediana baixa de P5.0/P5.1, o estado
final e 36 pulsos baixos por canal. A periodicidade mediana foi
59.400 ticks em todos os casos.

| ADC1 | `BCh` forçado | `31h` final | `69h` final | P5 baixo, ticks |
| ---: | ---: | ---: | ---: | ---: |
| 130 | `03h` | `10h` | `9Ah` | 1861 |
| 130 | `15h` | `10h` | `89h` | 1921 |
| 40 | `03h` | `59h` | `9Ah` | 10334 |
| 40 | `15h` | `59h` | `89h` | 10394 |

Portanto, o caminho `7570h → BCh → 7ECAh → 69h → Timer 1 → P5`
explica **60 ticks** de largura P5 nessas duas condições do emulador.
Em `ADC1=130`, coincide com a diferença completa G/S88 (1861/1921).
Em `ADC1=40`, a ROM S88 original mede 9346 ticks contra 10334 em G;
forçar somente o seletor em G produz 10394 ticks. O contraste residual
é analisado no experimento fatorial abaixo. Esses dados não identificam
o circuito físico conectado a P5. Os resultados e logs ficam em
`build/ma17-analysis/variants/rpm_selector_counterfactual_validated/`.

Uma segunda intervenção força **somente `IRAM[69h]` antes da primeira
leitura da rotina em `043Bh`**, quando `IRAM[47h]=28h`; a mesma rotina
volta a ler `69h` em `048Eh`. O opcode `MOV A,direct` em `043Bh` é descrito
no datasheet Siemens *SAB 80C517*, "Instruction Set", p. 215
([PDF local](../SAB80C517.PDF)). Com a mesma ROM G, sensores, RPM e
janela, `MA17_OVERRIDE_RAM69=9A` produziu P5 baixo de 1861 ticks
(`ADC1=130`) e 10334 (`ADC1=40`); `MA17_OVERRIDE_RAM69=89` produziu
1921 e 10394. Assim, trocar apenas o valor consumido de `69h`
reproduziu os **mesmos +60 ticks** do contrafactual de `BCh`. Isso
sustenta `69h` como mediador do efeito nesta condição do harness.
O firmware continua escrevendo seu próprio `9Ah` em `3B06h`, de modo
que a última alteração registrada de `69h` no relatório permanece `9Ah`
mesmo quando a leitura foi forçada a `89h`. Forçar só a segunda leitura
em `048Eh` cria um estado misto e não representa essa intervenção.
Traces: `build/ma17-analysis/variants/ram69_counterfactual_first_read/`.
Como verificação simétrica, forçar `69h=9Ah` antes de `043Bh` na ROM
**S88** reduziu P5 de 1921 para 1861 ticks com `ADC1=130`, mantendo
`31h=10h`; com `ADC1=40`, reduziu de 9346 para 9286 ticks, mantendo
`31h=50h`. A redução foi de **60 ticks em ambas**. Essa inversão
reproduz o efeito de `69h` nas duas ROMs sem alterar nenhum byte da
EPROM. Traces:
`build/ma17-analysis/variants/ram69_counterfactual_s88/`.

O cálculo também lê `IRAM[31h]` em `0490h` (`MOV direct,direct`, manual
SAB80C517, "Instruction Set", p. 217). Com `ADC1=40`, a intervenção
`MA17_OVERRIDE_RAM31` fixa esse valor imediatamente antes da leitura.
O teste `VariantTraceTests.test_original_g_rom_ram31_ram69_factorial_reproduces_s88_p5`
executa os quatro pares abaixo na **mesma ROM G**, com 1.000 RPM,
`ADC7=63`, 2.400.000 ticks e os demais estímulos iguais:

| `31h` lido | `69h` lido | P5 baixo, ticks | Diferença vs G basal |
| ---: | ---: | ---: | ---: |
| `59h` | `9Ah` | 10334 | 0 |
| `50h` | `9Ah` | 9286 | −1048 |
| `59h` | `89h` | 10394 | +60 |
| `50h` | `89h` | 9346 | −988 |

O último caso reproduz **exatamente** a mediana da S88 original em
`ADC1=40`. A diferença de `31h` contribui −1048 ticks e a de `69h`
contribui +60; não houve interação mensurável entre esses dois valores
nesta condição. O teste `3291h..32B8h` liga `7B45h` à diferença de
`31h` em entrada controlada; os contrafactuais anteriores ligam
`7580h` à diferença de `69h`. Isso explica o contraste de P5 no
harness para este estado, sem provar a ligação elétrica de P5 às
bobinas. Traces:
`build/ma17-analysis/variants/ram31_ram69_factorial_g/`.

Para testar os **bytes de calibração na origem**, o wrapper de `MOVC`
aceita `MA17_OVERRIDE_MOVC_7B45` e `MA17_OVERRIDE_MOVC_7580`, sempre
com `--trace-movc`. Ele executa a instrução original em `5289h`, registra
o byte real da ROM e só então substitui o valor entregue em `A` naquele
endereço. A EPROM continua com o mesmo SHA-256; o relatório de `MOVC`
mostra os bytes **originais** (`05h` e `10h`), enquanto o log
`[MOVC-OVERRIDE]` mostra os bytes entregues. Essa operação segue o
`MOVC A,@A+DPTR` do manual SAB80C517, "Instruction Set", p. 222.
Com `ADC1=40`, a mesma ROM G e demais estímulos fixos, a repetição no
emulador atual (`SHA-256=7d56979f9f23e44a4897fc7da9a5203f09a741e8f95f976245706981bd1db70b`)
produziu:

| `7B45h` entregue | `7580h` entregue | `31h` final | `69h` final | P5 baixo, ticks |
| ---: | ---: | ---: | ---: | ---: |
| `05h` | `10h` | `5Dh` | `9Ah` | 10800 |
| `0Dh` | `10h` | `50h` | `9Ah` | 9286 |
| `05h` | `25h` | `5Dh` | `89h` | 10860 |
| `0Dh` | `25h` | `50h` | `89h` | 9346 |

Uma execução sem intervenção e outra fornecendo os próprios bytes
`05h/10h` coincidiram em `31h=5Dh`, `69h=9Ah`, P5=10800 e CC3=6605
ticks. Assim, a intervenção de mesmo byte não alterou o resultado.
As capturas antigas de `two_rom_bytes_factorial_g/`, sem hash do
executável, registravam `31h=59h` e P5=10334 no primeiro caso;
conservam valor histórico, mas não representam este build.
As novas capturas estão em `7b45_adc1_40_current/`.

O último par reproduz a mediana da S88 original. O teste
`VariantTraceTests.test_two_original_rom_bytes_reproduce_s88_p5_without_rom_patch`
verifica os quatro resultados e os bytes reais registrados pelo trace.
Para repetir o último par:

```sh
MA17_OVERRIDE_MOVC_7B45=0D MA17_OVERRIDE_MOVC_7580=25 \
  MA17_ADC_CH7=63 MA17_ADC_CH1=40 \
  .venv/bin/python tools/trace_ma17.py \
  --firmware FiatTipo_MA17_dump_27c256.bin --no-kline-inject \
  --crank-immediate --rpm 1000 --stop-ticks 2400000 --seconds 20 \
  --trace-movc --output-dir build/ma17-analysis/variants/two_rom_bytes_factorial_g/byte_7B45_0D_7580_25
```

Isso estabelece, **para esta condição emulada**, que os dois valores
consultados bastam para reproduzir a diferença de `31h`, `69h` e da
largura mediana de P5 entre G e S88. O efeito físico de P5 continua
sem confirmação no chicote da ECU.
Traces: `build/ma17-analysis/variants/two_rom_bytes_factorial_g/`.

Em `ADC1=80`, condição intermediária com o mesmo RPM e ADC7, G lê
`7B45h` 230 vezes. Controle, `7B45h→0Dh`, ambas as trocas e S88 natural
produziram, respectivamente, `31h/69h=19h/9Ah`, `18h/9Ah`,
`18h/89h` e `18h/89h`; P5 mediano=2909/2793/2853/2853 ticks.
CC3 permaneceu em 5677 ticks nos quatro. A intervenção de dois bytes
também reproduziu a cobertura de PC da S88 (5476 endereços), sem provar
igualdade de todo o estado. Regressão:
`test_7b45_and_7580_separate_ram31_and_ram69_at_intermediate_adc1`.
Capturas: `7b45_adc1_80/`.

Uma extensão manteve `ADC1=130`, `ADC7=63` e 2.400.000 ticks e variou
somente a roda 60−2 de 750 a 4.000 RPM. Em cada RPM, a ROM G original,
a S88 original e G recebendo `7B45h=0Dh` e `7580h=25h` **somente na
leitura MOVC** foram executadas separadamente. Os bytes da ROM G e seu
SHA-256 permaneceram originais. A largura é a mediana baixa de P5.0,
em ticks do emulador:

| RPM | G | S88 | G com duas leituras substituídas | `31h` G/S88 | `69h` G/S88 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 750 | 1940 | 1937 | 1937 | 0Ch/0Ch | 9Fh/91h |
| 1000 | 1861 | 1921 | 1921 | 10h/10h | 9Ah/89h |
| 1500 | 1785 | 1823 | 1823 | 17h/17h | 88h/7Dh |
| 2000 | 1789 | 1820 | 1820 | 1Fh/1Fh | 7Eh/73h |
| 3000 | 1775 | 1769 | 1769 | 2Eh/2Eh | 6Ah/65h |
| 4000 | 1794 | 1793 | 1793 | 3Eh/3Eh | 5Ah/56h |

Nesse valor de ADC1, `31h` já é igual nas duas ROMs. Substituir **apenas**
`7580h=25h` em G reproduziu `31h`, `69h` e P5 da S88 em 750 e 3.000
RPM; o teste automatizado cobre esses dois pontos. A igualdade dos seis
resultados com as duas leituras substituídas ainda se limita ao perfil
emulado e a `ADC1=130`. Cada execução registrou 230 leituras brutas de
`7B45h` e 230 de `7580h` em `5289h`; os valores no relatório MOVC são
os bytes da ROM, antes da intervenção. Traces:
`build/ma17-analysis/variants/two_rom_bytes_rpm_extension/`.

Com 1.000 RPM e ADC1=40, a instrumentação confirma a geometria da matriz:
`DPTR=7ED9h`, `532Fh` lê índice `03h`, `5333h` lê `04h`, `534Bh` lê
`0Dh` e `5350h` lê `0Eh` repetidamente. A distância de dez bytes entre
as duas linhas concorda com o cálculo em `3291h`; o teste de integração
verifica esses quatro acessos diretamente no trace.

### Variação independente de RPM e ADC1

O executor agora usa `--stop-ticks 2400000` em todos os casos; `--seconds
15` é somente o prazo de relógio para detectar travamento. Assim, as
comparações partem da mesma duração lógica, independentemente da carga do
host. O modo encerra o emulador exatamente no tick solicitado e o relatório
registra alvo e valor observado. Todos usam `--trace-movc
--crank-immediate --no-kline-inject`. Largura é a mediana baixa de P5.0
em ticks do emulador; P5.1 apresentou o mesmo valor.
`run_ma17_variant_experiments.py` executa 18 casos em ordem, grava
`build/ma17-analysis/variants/experiments_opcode86_fixed/experiments.json` e
`experiments.csv`, e conserva o `execution.json` e o trace bruto por caso.
Uma execução com o núcleo corrigido produziu os valores abaixo; a coluna
de voltas é igual entre G/S88 em cada cenário.

| RPM | ADC1 | Voltas | `G`: P5 | `S88`: P5 | `G`: 31h | `S88`: 31h |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 750 | 130 | 29 | 1940 | 1937 | 0Ch | 0Ch |
| 1000 | 130 | 39 | 1861 | 1921 | 10h | 10h |
| 2000 | 130 | 79 | 1789 | 1820 | 1Fh | 1Fh |
| 1000 | 40 | 39 | 10334 | 9346 | 59h | 50h |

Com `ADC7=63` e 1.000 RPM, a mesma janela de ticks deu:

| ADC0/ADC6 | `6Fh` G/S88 | `48h` G | `48h` S88 | leituras da matriz 7581h G/S88 | CC3, amostras | P5 G/S88 |
| --- | --- | --- | --- | ---: | ---: | --- |
| 120/95 | 27h | 40h | 40h | 920 | 75 | 1861/1921 |
| 40/95 | 53h | 21h | 1Fh | 920 | 75 | 1861/1921 |
| 120/180 | A8h | 3Bh | 3Bh | 462 | 75 | 1921,5/1863 |

`IRAM[48h]` respondeu ao TPS no ensaio com guarda habilitada e diferiu
entre ROMs sob `40/95`. O trace da entrada CC3 também capturou valores
não nulos de `IRAM[14h:15h]` e pulsos baixos do pino CC3 modelado:

| ADC0/ADC6 | `14h:15h` mediana G/S88 | CC3 baixo mediano, ticks G/S88 |
| --- | ---: | ---: |
| 120/95 | 1422/1422 | 5677/5677 |
| 40/95 | 763/727 | 3041/2897 |
| 120/180 | 1314/1324 | 5245/5285 |

Em `40/95`, a diferença de 36 unidades no agendamento corresponde a
144 ticks na largura modelada. As medianas acima foram revalidadas no
build atual a 2,4 milhões de ticks. As ROMs diferem também em eixos e outros
dados; este ensaio não atribui a diferença do pulso exclusivamente à matriz
nem estabelece a conexão física do CC3 ao bico.

### Modelo ADC do SAB80C517A e interpretação física dos sensores

O [manual Siemens do SAB80C517A, seção ADC, pp. 5-5 a 5-7](https://www.keil.com/dd/docs/datashts/infineon/8xc5x7a_uma.pdf)
identifica `D9h=ADDATH`, `DAh=ADDATL`: escrever `DAh` inicia a
conversão; o resultado de 10 bits é alinhado à esquerda, com os dois bits
baixos em `DAh.7:.6`. O IDA usou o nome `DAPR` de um C517 anterior para
`DAh`, mas os opcodes Fiat em `06DDh` e `0716h..071Bh` escrevem, leem e
arredondam o resultado exatamente como exige o C517A. O simulador antigo
deixava em `DAh` o byte de partida com bit 7 ligado; por isso todas as
leituras IRAM de ADC carregavam um `+1` artificial. O simulador agora lê
ambas as metades, retém o par `ADDATH/ADDATL` até a próxima conversão e
aceita `MA17_ADC10_CHn=0..1023`; `MA17_ADC_CHn` injeta
os oito bits altos com os dois baixos zerados. A conversão ainda é
imediata no emulador; sua latência física não está simulada.

Para testar transitórios, `MA17_ADC10_STEP_CHn=tick:value` aceita até
oito pares separados por vírgula, em ticks estritamente crescentes
(valores digitais de 0 a 1023). Um único par mantém a sintaxe anterior.
Cada valor novo aparece no firmware após a próxima escrita de `ADDATL`
para esse canal. `execution.json` registra a sequência em
`adc_10bit_step_sequences` e conserva o primeiro par em
`adc_10bit_step_values` para compatibilidade. Em G, com 1.000 RPM,
`ADC7=63`, `MA17_ADC10_CH2=400` e
`MA17_ADC10_STEP_CH2=200000:163`, `RAM[62h]` mudou de `64h` para `29h`
na conversão de PC `0744h` após o tick 200.000 (captura:
`build/ma17-analysis/variants/adc_step_10bit_rounding/`). O segundo byte
inclui o arredondamento do bit baixo; a mudança não representa, por si só,
uma temperatura em graus Celsius. O teste
`VariantTraceTests.test_adc10_step_reaches_firmware_on_next_temperature_conversion`
verifica os valores e o SHA-256 da ROM original.

Um teste da ROM original com `ADC10_CH2=ADC10_CH3=160,161,162,163`
observou, respectivamente, `RAM[62h]=RAM[63h]=28h,28h,29h,29h`.
Isso valida os canais de ar/água e o arredondamento digital de `DAh.7`;
não valida a curva de temperatura. O scanner estima temperaturas por
Steinhart–Hart com resistores supostos de 2661 Ω (ar) e 3004 Ω (água),
mas declara que os coeficientes foram ajustados a partir de outro sensor
Bosch e com auxílio de IA. Para validar graus Celsius, faltam pares
medidos resistência/tensão/byte na placa Fiat.

`tools/trace_ma17.py` registra agora os estímulos efetivos em
`adc_10bit_input_values` e seus oito bits altos em `adc_input_values`.
O teste `test_temperature_adc10_stimuli_reach_distinct_firmware_bytes`
injeta `ADC10_CH2=321` e `ADC10_CH3=642`, mesmo com estímulos legados
conflitantes. Na ROM Fiat, o trace confirma `62h=50h` em `0744h` e
`63h=A1h` em `4756h`: o segundo byte inclui o arredondamento do bit baixo.
Isso verifica a prioridade da entrada de 10 bits e a rota digital dos dois
canais; a correspondência em graus Celsius ainda depende de medições físicas.

Um teste com degraus separados reforça a validação do multiplexador: em G
e S88, `ADC10_CH2=ADC10_CH3=160`, `CH2=163` a partir do tick 200.000 e
`CH3=163` a partir de 400.000. Com 1.000 RPM e 700.000 ticks, `62h`
mudou `28h→29h` em 223.958/223.956 (G/S88), antes do degrau de CH3.
O bruto de CH3 em `A8h` mudou no tick 410.318 em ambas as ROMs;
`63h` mudou em 410.817/411.001. O teste
`test_staggered_air_and_coolant_adc_steps_stay_on_separate_channels`
confere essas duas rotas, o arredondamento e os hashes originais. As
capturas estão em `build/ma17-analysis/variants/temp_adc_dual_step_{g,s88}/`.

Há uma distinção entre o byte ADC bruto e o valor de água usado pela
rotina. Em G, a aquisição grava o bruto do canal 3 em IRAM superior
`A8h`; `4629h..4756h` processa esse byte antes de gravar `RAM[63h]`.
As comparações imediatas em `4645h/4651h` encaminham valores **abaixo
de `04h` ou a partir de `E8h`** para `474Eh`, que substitui o valor por
`11h`. Ensaios de 200.000 ticks com `MA17_ADC10_CH3` em 12, 16, 924
e 928 confirmaram os pares bruto→processado `03h→11h`, `04h→04h`,
`E7h→E7h` e `E8h→11h`, respectivamente. O teste automatizado verifica
os PCs `474Eh/4756h` e preserva o SHA-256 da ROM. A variante S88
reproduziu os mesmos quatro pares e o mesmo desvio em `474Eh`, com seu
próprio hash de ROM verificado. Isso é uma regra
digital de faixa válida observada no firmware; não estabelece a
resistência nem a temperatura correspondentes, nem o significado físico
de `11h` em todas as condições. Capturas:
`build/ma17-analysis/variants/adc3_bounds_10bit/` e
`build/ma17-analysis/variants/adc3_high_boundary/` (G) e
`build/ma17-analysis/variants/adc3_bounds_s88/` (S88).
Além da faixa absoluta, G testa a variação positiva em `465Dh..4675h`.
Partindo de `A8h=28h` e aplicando um degrau no tick 1.200.000, o ADC
entregou `33h`, `34h` e `35h` para aumentos de `0Bh`, `0Ch` e `0Dh`.
O firmware gravou respectivamente `RAM[63h]=33h`, `11h` e `11h`:
`4671h` aceita o primeiro e os dois últimos passam pelo substituto
`474Eh`. O degrau inverso `28h→50h` também produziu `63h=11h`.
O teste `test_coolant_upward_step_crosses_firmware_jump_limit` verifica
separadamente o ADC bruto em `A8h`, o byte processado, o PC visitado e
o hash da ROM. Essa fronteira foi observada com as flags iniciais do
ensaio; ainda não identifica o diagnóstico ou a dinâmica em hardware.
Nas ROMs A, A+, S37 e S36, o `CJNE A,#0Ch` homólogo está em `472Bh`
(operando em `472Ch`), contra `466Eh`/`466Fh` em G/S88. Um teste isolado
com os opcodes originais dessas quatro ROMs e amostra anterior `28h`
reproduziu `33h→33h`, `34h→11h` e `35h→11h`. Isso confirma a regra
digital nessa rota, sem pressupor que o boot completo alcance o mesmo
estado nas revisões A.
Nos boots completos G e S88, com `ADC2=400/1023`, `ADC3=160/1023`
inicial, `ADC7=63` e degrau de ADC3 no tick 800.000, o resultado
`33h` em `63h` consultou `MOVC 52A2h→73D8h` e terminou com `4Eh=42h`;
o degrau vizinho para ADC bruto `34h` publicou `63h=11h`, não consultou
`73D8h` e terminou com `4Eh=00h`. Em 2,4 milhões de ticks, a mediana
do agendamento CC3 foi 1228 contra 1160 ticks e a largura modelada
P1.3 foi 4900 contra 4629 ticks nas duas ROMs. O teste
`test_coolant_adc_step_preserves_raw_channel_and_preprocessing_boundary`
verifica os hashes originais, `A8h`, `63h`, `62h`, `MOVC`, `4Eh` e a
ordem das medianas CC3. Esse contraste mede o efeito total do estímulo
ADC3 no estado ensaiado; não separa a contribuição exclusiva de `73D4h`
nem confirma a conexão elétrica de P1.3.
Os decodificadores de temperatura C++ e Python do scanner usam os mesmos
coeficientes Steinhart–Hart e `Rpu=3004 Ω` para o ID `63h`. Como a coleta
diagnóstica lê `RAM[63h]` **após** essa validação, a curva receberia
`11h` no degrau `28h→34h`: cerca de 94,7 °C pela hipótese do scanner.
Aplicá-la diretamente ao ADC bruto `34h` daria cerca de 52,3 °C.
Esses números ilustram a diferença entre byte bruto e byte publicado;
não são temperaturas medidas nem confirmam a calibração analógica.
No mesmo bloco, os opcodes G usam `DPTR=7200h` e leem as constantes
contíguas `7265h..7269h = 31 1E 17 03 04`; os cinco bytes são iguais nas
seis ROMs. O trace G confirmou `468Ah→7265h=31h` e, no degrau aceito
`28h→33h`, `46ABh→7266h=1Eh`. Nos degraus `28h→34h/35h`, o desvio
para `474Eh` antecede a segunda leitura. Substituir apenas o resultado
do `MOVC` em `468Ah/7265h` por `50h`, mantendo o arquivo ROM, impediu a
leitura de `7266h` no degrau aceito; `RAM[63h]` permaneceu `33h`.
Isso confirma uma função de seleção de caminho para `7265h` nesse
estado. Um teste dos **opcodes originais** nas seis ROMs isolou os outros
campos: `R2:R3=22h:20h` lê `7268h=03h` e publica `63h=22h`; com
`30h:20h`, também lê `7267h=17h`, carrega `R5=17h` e publica `63h=20h`.
Começando no caminho `46C6h` (`+BDh` na família A), `R3=40h` e XRAM
`D9h=0` fazem o código ler `7269h=04h` e gravar `D9h=04h`. O teste
`CoolantControlConstants7265To7269UseOriginalOpcodes` verifica os PCs,
registros e saída. Esses estados foram preparados artificialmente;
os 489 relatórios de execução mais curtos examinados até então não
registravam leituras de `7267h..7269h`.
Uma sequência `ADC3=160` (10 bits), `1200000:204,1450000:224` deu
`A8h=28h→33h→38h` em G/S88. No controle, `R5` foi carregado com
`7266h=1Eh`, terminou em `1Dh`, e `63h=38h`; não houve leitura de
`7267h..7269h`. Ao substituir **somente** o resultado de `MOVC` em
`46ABh/7266h` por `01h`, `R5` chegou a zero e o firmware alcançou
`46C6h/46E6h`, leu `7269h/7268h/7267h`, carregou `R5=17h` e publicou
`63h=32h` perto de 2,05 milhões de ticks nas duas ROMs. O hash e os
bytes originais permaneceram iguais. Isso demonstra a guarda por `R5`
e o efeito desse caminho no emulador; com o byte real `1Eh`, a condição
natural exige uma observação muito mais longa. O teste de regressão cobre ambos os
controles, a intervenção, os endereços `MOVC` e o valor publicado.
Mantendo o byte **original** `7266h=1Eh`, os mesmos dois degraus e
1.000 RPM até 70 milhões de ticks, G reduziu XRAM `F8D7h`/`R5` de
`1Eh` a `01h` e alcançou naturalmente `7269h`, `7268h` e `7267h`
uma vez cada. `RAM[63h]` mudou de `38h` para `32h` no tick 67.584.860;
após a passagem, `R5=17h` e XRAM `F8D9h=04h`. A ROM manteve o hash
`a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
Captura: `build/ma17-analysis/variants/coolant_two_step_70m_natural/`.
O teste opcional reproduz o evento até 68 milhões de ticks:
`MA17_RUN_SLOW=1 python3 -m unittest tests.test_compare_ma17_variants.VariantTraceTests.test_original_coolant_counter_reaches_7267_to_7269`.
Essa é uma observação em emulação G, sem sessão K-Line nem validação
física. Na S88, o mesmo cenário de 70 milhões de ticks, também sem
substituições, produziu `63h=38h→32h` no tick 61.440.647 e
`32h→31h` no tick 69.633.515. O trace registrou duas leituras de
`7269h` e uma de `7268h/7267h`; G registrou uma de cada e não mostrou
a segunda mudança até 70 milhões. Os cinco bytes são idênticos nas
duas ROMs. A origem da diferença temporal permanece indeterminada;
ticks emulados ainda não estabelecem uma escala física entre revisões.
Captura S88: `build/ma17-analysis/variants/coolant_two_step_70m_s88/`.
O boot longo das quatro revisões A ainda não foi medido.
O decremento está no código original G/S88 `327Ah..3290h`, deslocado
para `3296h..32ACh` na família A. `T2CON.1=1` salta o bloco;
com `T2CON.1=0`, cada contador XRAM `D7h`/`D9h` é decrementado somente
se não for zero e `RAM[2Dh].4=1`. A rotina de temperatura carrega
`D7h` em `R5`; isso explica a espera longa após a leitura inicial de
`7266h=1Eh`. O teste `CoolantCountersD7AndD9DecayUnderOriginalGuards`
executa esses opcodes nas seis ROMs e verifica as quatro combinações
de guardas e contadores. Com `MA17_TRACE_COOLANT_GATE=1`, em 70 milhões
de ticks ambas executaram 34 decrementos em `F8D7h` pelo PC `3286h`.
O primeiro ocorreu em 2.047.676 (G) e 2.047.691 (S88); os eventos
correspondentes mantiveram praticamente a mesma cadência. Logo, a
diferença entre as primeiras publicações tardias de `RAM[63h]` não
resultou da taxa de decrementos nesse ensaio.
O trace de todas as escritas em `F8D7h` localizou a primeira divergência:
em G, `3286h` grava `0Fh→0Eh` no tick 32.767.376, mas `476Eh` grava
`0Eh→0Fh` no tick 32.768.204. S88 grava `0Fh→0Eh` em 32.767.391 e não
apresenta essa restauração. O código original em `476Eh` persiste `R5`
na XRAM após processar a temperatura; nessa execução G ele persiste uma
cópia anterior ao decremento. Outras restaurações ocorrem mais tarde.
A fase diferente entre as rotinas e sua fidelidade ao hardware real
continuam sem explicação. Capturas:
`build/ma17-analysis/variants/coolant_decay_long_{g,s88}/` e
`build/ma17-analysis/variants/coolant_writes_36m_{g,s88}/`.
O trecho `4629h..4758h` é idêntico em G/S88. Nas quatro ROMs da outra
família, aparece em `46E6h..4815h` (deslocamento `+BDh`). Os 17 bytes
divergentes nesse alinhamento são apenas operandos de nove `LJMP`
internos; cada destino também deslocou `+BDh`. Após normalizar esses
operandos, os 304 bytes coincidem, incluindo os limiares `04h/E8h`,
o valor substituto `11h` e a escrita de `63h`. Um teste verifica âncora
única, opcodes, destinos e igualdade normalizada nas seis ROMs. Isso
estabelece a mesma lógica **estática** nessa rotina. O teste isolado
`Sab80C517.AlcoholCodeUpperA8BoundsBecomeCoolantRam63` executa
`46E6h..4815h` nas ROMs A/S37, com amostra anterior estável em `A9h`:
`A8h=03h/04h/E7h/E8h` produz `63h=11h/04h/E7h/11h`. Apenas G/S88
foram executadas em boot completo com o perfil de hardware atual.
Um segundo teste isolado executa `4830h..483Ch` nas mesmas ROMs. O
ponteiro `7002h→73D4h` consulta `63h`: com `28h`, retorna índice 1,
fração `B0h` e grava `4Eh=B1h`; com `50h`, retorna índice 3, fração
`20h` e grava `4Eh=23h`. São os mesmos resultados observados em G/S88,
agora verificados pelos opcodes da revisão A/S37.

Para a sonda estreita, uma polarização perto de 450–500 mV enquanto fria
ou desconectada é uma hipótese de circuito, ainda sem esquema ou medição
da placa. A escala `raw × 3,9 mV` do scanner associaria essa faixa a
aproximadamente 115–128 códigos. Se o pino ADC recebesse diretamente
0,45–0,50 V com referência de 5 V, o byte alto seria aproximadamente
23–26; portanto esses códigos não demonstram nem descartam a hipótese:
é preciso medir o condicionamento analógico entre conector e ADC, além
da referência `VAREF/VAGND`. A janela neutra digital confirmada da ROM
é uma propriedade do **byte em `RAM[65h]`**, não uma tensão na sonda.

Os resultados dinâmicos antigos que não tenham uma reexecução identificada
permanecem históricos e precisam de repetição para uso quantitativo. As
comparações de bytes de ROM e testes isolados de opcodes não dependem desse
erro de simulação.

### Variação dos canais associados a temperatura

Com 1.000 RPM, `ADC7=63` e 2,4 milhões de ticks, variou-se somente
`ADC2` ou `ADC3` em relação ao padrão. O scanner associa esses canais a
temperatura do ar e da água, respectivamente; as unidades físicas e a
direção térmica de cada valor ADC não foram demonstradas aqui. As duas
ROMs tiveram 39 voltas completas, 920 leituras da matriz `7581h` e 75
amostras de agendamento CC3 em cada cenário.

| ADC2/ADC3 | `48h` G/S88 | `14h:15h` mediana G/S88 | CC3 baixo mediano, ticks G/S88 |
| --- | --- | ---: | ---: |
| 100/80, padrão | 40h/40h | 1422/1422 | 5677/5677 |
| 40/80, ADC2 alterado | 3Ch/3Ch | 1336/1336 | 5333/5333 |
| 100/40, ADC3 alterado | 40h/40h | 1194/1194 | 4764/4764 |

Esta tabela foi repetida após a correção de `ADDATL`; os relatórios G/S88
estão em `build/ma17-analysis/variants/experiments_adc517a/`. Em cada
par, `RAM[62h:63h]` ficou em `64h:50h`, `28h:50h` e `64h:28h`,
respectivamente. A grade usa os mesmos 2,4 milhões de ticks por caso.
O teste `test_temperature_channels_change_cc3_independently_in_g_and_s88`
em `tests/test_compare_ma17_variants.py` reproduz esses três estímulos nas
duas ROMs, confere o SHA-256 carregado, os dois bytes de RAM e a mediana
de CC3. Assim, ele cobre a cadeia digital ADC → firmware → temporizador;
CC3 continua sendo uma saída do modelo, sem validação elétrica na ECU.

Um sweep temporal adicional na **ROM G original**, com 1.000 RPM,
`ADC2=400` e `ADC7=63`, manteve `ADC3=160` até o tick 1.200.000 e
aplicou `180`, `200`, `220`, `200` nos ticks 1.200.000, 1.700.000,
2.200.000 e 2.700.000. O controle manteve `ADC3=160` durante os mesmos
3.200.000 ticks. Ambos usaram `--trace-movc --no-kline-inject
--crank-immediate`, a mesma ROM SHA-256 `a3473435…f8e1f` e 203 bordas
modeladas de CC3. `RAM[63h]` passou por `28h→2Dh→32h→37h→32h`; no
controle permaneceu em `28h`. Cada mediana abaixo usa pulsos cujo início
baixo caiu dentro da janela, incluindo eventuais transientes:

| Janela de ticks | Pulsos | CC3 baixo sweep, ticks | CC3 baixo controle, ticks |
| --- | ---: | ---: | ---: |
| 0–1.200.000 | 34 | 4765 | 4765 |
| 1.200.000–1.700.000 | 17 | 4900 | 4765 |
| 1.700.000–2.200.000 | 17 | 4900 | 4764 |
| 2.200.000–2.700.000 | 17 | 4900 | 4696 |
| 2.700.000–3.200.000 | 16 | 4833 | 4697 |

O código do harness conta um tick por ciclo de máquina; no perfil Fiat
de 11,88 MHz, a conversão nominal é `990 ticks/ms`. Assim, 4900 ticks
equivalem a aproximadamente 4,95 ms **nesse modelo**. O controle também
muda após 2,2 milhões de ticks, portanto a diferença entre séries deve
ser analisada por janela, sem atribuir toda a evolução ao ADC3.
O datasheet do SAB80C517 especifica 12 períodos do oscilador por ciclo
de máquina e instruções de 1, 2 ou 4 ciclos. Logo, 11,88 MHz equivalem
a 990.000 ciclos de máquina por segundo, mas não a uma taxa fixa de
990.000 instruções por segundo. Sweeps podem executar mais lentamente
no computador: compare eventos e estímulos em ticks emulados, aplicando
a conversão de clock apenas para interpretar o tempo físico nominal.
A validade dessa conversão ainda depende da fidelidade dos periféricos e
da confirmação do cristal para a revisão ensaiada.

No perfil Fiat, `tempo_s = ticks / 990000` e
`largura_ms = largura_ticks / 990`. A 1.000 RPM, uma posição da roda
60−2 dura nominalmente 990 ticks e uma volta, 59.400 ticks. Use
`--stop-ticks` para fixar a duração simulada; `--seconds` é apenas o
limite de espera do processo nesse modo. A taxa `[PERF]` mede o ritmo
do computador, sem mudar o RPM dos estímulos agendados em ticks. Esta
equivalência pressupõe sweeps sem entrada externa via PTY agendada em
tempo real. O ADC emulado ainda retorna o resultado sem a latência de
conversão indicada no datasheet; a normalização não corrige essa
limitação temporal do modelo.

A captura agregada registrou 195.573 leituras MOVC no sweep e 195.829 no controle,
com 13 endereços ROM lidos apenas no sweep: `7226h`, `7266h`, `7451h`,
`74ABh`, `74F1h`, `7523h`, `752Dh`, `754Bh`, `7555h`, `79B3h`,
`79BDh`, `79D1h` e `7B0Dh`. São diferenças de cobertura nesse ensaio,
não prova de causalidade individual. Relatórios e logs:
`build/ma17-analysis/variants/coolant_happy_path_{sweep,control}_g/`.
Uma repetição com `--movc-bucket-ticks 100000` preservou exatamente os
totais globais: 195.573/195.829 leituras no sweep/controle. Antes do
primeiro degrau, ambos tiveram as mesmas 73.588 leituras e os mesmos 538
endereços distintos. Dos 13 endereços exclusivos do sweep, dez aparecem
pela primeira vez na janela 1.200.000–1.300.000; `7B0Dh` aparece em
1.300.000–1.400.000, `7266h` em 1.700.000–1.800.000 e `79D1h` em
2.000.000–2.100.000. As contagens por endereço e janela estão em
`build/ma17-analysis/variants/coolant_happy_path_{sweep,control}_bucket_g/`.
Os valores ADC são estímulos digitais plausíveis para exercitar o código;
a correspondência com graus Celsius e a ligação física de CC3 seguem
sem validação. Repetir o sweep nas variantes exige verificar o perfil de
clock e periféricos de cada revisão.

Para reproduzir, execute o mesmo comando duas vezes, retirando apenas a
variável `MA17_ADC10_STEP_CH3` no controle:

```sh
MA17_ADC10_CH2=400 MA17_ADC10_CH3=160 MA17_ADC_CH7=63 \
MA17_ADC10_STEP_CH3=1200000:180,1700000:200,2200000:220,2700000:200 \
python3 tools/trace_ma17.py --firmware FiatTipo_MA17_dump_27c256.bin \
  --trace-movc --movc-bucket-ticks 100000 \
  --no-kline-inject --crank-immediate --rpm 1000 \
  --stop-ticks 3200000 --seconds 60 \
  --output-dir build/ma17-analysis/variants/coolant_happy_path_sweep_bucket_g
```

O gráfico [ADC3 × CC3](../build/ma17-analysis/variants/coolant_happy_path_adc3_cc3.png)
mostra os pulsos individuais, inclusive os três pulsos de partida mais
longos e a queda temporal presente também no controle. Reproduza PNG/SVG com
`MPLCONFIGDIR=build/ma17-analysis/matplotlib /usr/bin/python3
tools/plot_ma17_temporal_sweep.py` seguido dos diretórios de sweep e controle
e `--output-prefix build/ma17-analysis/variants/coolant_happy_path_adc3_cc3`.
O gráfico usa 990.000 ticks/s apenas para o perfil Fiat; a variante Renault
exige perfil próprio antes de qualquer conversão temporal.

No mesmo sweep G, um contrafactual substituiu **apenas o resultado** de
`MOVC` em `PC5333h/ROM7451h`: o byte original `33h` foi entregue ao
firmware como `4Dh`, valor da célula homóloga na ROM A. A leitura ocorreu
469 vezes, e o SHA-256 da ROM G continuou original. Após os quatro
degraus, `RAM[4Dh]` foi `2Ah/2Bh/2Dh/2Bh` na execução nativa e
`2Bh/30h/37h/30h` com a substituição. As **203 bordas de CC3**, com
seus ticks e níveis, foram idênticas entre as duas execuções. Portanto,
esta célula afeta o estado interno nesse cenário, mas não explica sozinha
o aumento de CC3 visto no sweep. A função física de `4Dh` e efeitos em
outros estados seguem abertos. Captura:
`build/ma17-analysis/variants/coolant_happy_path_7451_a_cell_g/`;
regressão: `test_coolant_sweep_buckets_follow_adc_steps_in_original_g`.
Outras duas intervenções de célula única, sempre no `MOVC PC5333h`,
usaram os bytes homólogos da ROM A: `7523h: 93h→B5h` e
`752Dh: 80h→A2h`. No mesmo sweep, a primeira mudou `RAM[79h]` após
os quatro degraus de `75h/79h/7Fh/79h` para `77h/7Fh/8Ch/7Fh`, mas
preservou exatamente as 203 bordas de CC3. A segunda mudou
`RAM[7Bh]` de `7Ah/7Bh/7Ch/7Bh` para `7Dh/82h/89h/82h`;
cinco bordas diferiram entre −1 e +4 ticks e três larguras baixas
diferiram apenas um tick. As cinco medianas de largura por janela
permaneceram iguais. Esses contrastes comprovam os destinos internos
das células e delimitam o efeito em CC3 **neste cenário**, sem excluir
outros regimes como a liberação do TPS. Capturas:
`build/ma17-analysis/variants/coolant_happy_path_{7523,752d}_a_cell_g/`.

### Reprodução diferencial G → S88 no sweep de ADC3

A S88 tem o mesmo código até `757Fh` e conserva os bytes G em
`7451h/7523h/752Dh`. Com o mesmo perfil Fiat, RPM e degraus ADC3, as
duas ROMs escreveram os mesmos valores observados em `RAM[63h]`, `4Dh`,
`79h` e `7Bh`. Os 203 eventos modelados de CC3 mantiveram a mesma ordem
de níveis; as larguras baixas diferiram no máximo um tick, mas só dez
eventos tinham ticks exatamente iguais. Em 185 eventos, a S88 adiantou
26–28 ticks. Quatro contrafactuais no G original isolaram constantes
alteradas naturalmente lidas nesse cenário:

| Resultado fornecido ao `MOVC` G | Eventos CC3 iguais à S88 | Estado adicional |
| --- | ---: | --- |
| Nenhum | 10/203 | Referência G |
| `7580h: 10h→25h` | 198/203 | Restam diferenças de até dois ticks |
| `7B45h: 05h→0Dh` | 10/203 | Deslocamento de fase permanece |
| Ambos | 203/203 | Primeira escrita em upper `A4h` ainda 99h, S88 A1h |
| Ambos + `7B46h/7B47h: 99h→A1h` | 203/203 | `A4h` e demais estados estruturados observados iguais |

As duas primeiras células somadas também reproduziram a cobertura PC,
as 195.052 leituras MOVC e todas as contagens por endereço/janela da S88.
As duas células adicionais reproduziram as observações estruturadas de
RAM, saídas e CC3. O trace MOVC bruto ainda registra os bytes **G** e a
ROM G mantém seu SHA-256; há outros bytes S88 lidos e nenhuma equivalência
global de firmware foi demonstrada. O ensaio identifica a contribuição
digital de `7580h` para a fase e de `7B45h` para o resíduo neste estado;
não identifica o atuador físico. Capturas:
`build/ma17-analysis/variants/coolant_s88_*_donor_g/` e
`coolant_happy_path_sweep_bucket_s88/`; regressão
`test_s88_phase_and_upper_a4_split_across_four_original_movc_bytes`.
O [gráfico das bordas CC3](../build/ma17-analysis/variants/coolant_s88_phase_factorial.png)
mostra os deltas de tick das quatro intervenções contra a S88; a linha
zero representa igualdade de fase no modelo. Reproduza PNG/SVG com:

```sh
MPLCONFIGDIR=build/ma17-analysis/matplotlib /usr/bin/python3 \
  tools/plot_ma17_phase_factorial.py \
  build/ma17-analysis/variants/coolant_happy_path_sweep_bucket_s88 \
  --arm G=build/ma17-analysis/variants/coolant_happy_path_sweep_bucket_g \
  --arm 7580h=build/ma17-analysis/variants/coolant_s88_7580_donor_g \
  --arm 7B45h=build/ma17-analysis/variants/coolant_s88_7b45_donor_g \
  --arm both=build/ma17-analysis/variants/coolant_s88_both_donor_g \
  --output-prefix build/ma17-analysis/variants/coolant_s88_phase_factorial
```

Repetimos a intervenção com **1.500 RPM**, `ADC2=400`, `ADC7=63` e
`ADC3=160→180→200→220→200` nos ticks 900.000, 1.300.000, 1.700.000 e
2.100.000, até 2.400.000 ticks. G e S88 geraram 226 bordas CC3 cada,
com os mesmos níveis em ordem. Diferentemente do deslocamento dominante
perto de 27 ticks a 1.000 RPM, a G nativa já coincidiu com S88 em 215
bordas; a maior divergência foi uma borda alta 136 ticks atrasada logo
após o primeiro degrau. Nesse pulso, a borda baixa ocorreu no mesmo tick
`923127` nas duas ROMs; a largura modelada foi `4901` ticks em G e
`4765` em S88. Portanto, o evento representa também diferença de
**largura de pulso**, não apenas deslocamento de fase. A contagem de
bordas exatamente iguais à S88 foi:

| Valores S88 entregues ao `MOVC` G | Bordas CC3 iguais à S88 |
| --- | ---: |
| Nenhum | 215/226 |
| Só `7580h:25h` | 221/226 |
| Só `7B45h:0Dh` | 211/226 |
| `7580h:25h` e `7B45h:0Dh` | 226/226 |
| Ambos + `7B46h/7B47h:A1h` | 226/226 |

O trace detalha o pulso divergente. `0744h` publicou `28h→2Dh` na RAM
superior `[A8h]` no tick `901838` em todos os braços. Na S88, `475Fh`
restaurou `[A8h]=28h` no tick `901862`; `4756h` só publicou
`RAM[63h]=2Dh` no tick `923594`. Na G nativa, `4756h` publicou `2Dh`
já no tick `903126`. Com apenas `7580h:25h` fornecido ao `MOVC` G, a
publicação de `63h` ocorreu no tick `923597`, acompanhando a S88.
Os opcodes em `4629h..463Ah` (leitura de `[A8h]`), `4752h..4762h`
(publicação em `63h` e `[A8h]`), `1D4Bh`, `1ED3h` e `058Eh` são
idênticos nas duas ROMs. Portanto, a diferença observada decorre da
ordem em que o código alcança essas operações no modelo, não de uma
mudança nesses opcodes. Na entrada CC3 do tick `923099`, G tinha
`RAM[14h:15h]=04CCh`; S88 e G com `7580h:25h` tinham `04AAh`.
A janela de PC `901820:901880` mostrou o mesmo fluxo da ISR de Timer 0,
que atende o ADC em `0716h..0744h`, nas três execuções até `RETI` em
`084Fh` no tick `901852`. No tick
seguinte, a G retomou o primeiro plano em `5246h` (interpolador), S88
em `4697h` e G com `7580h:25h` em `468Eh` (rotina que chega a `4756h`).
Assim, a diferença de tempo entre o produtor ADC e o consumidor vem
da posição do primeiro plano quando a interrupção termina. A S88 e a
doação escrevem de volta o valor antigo de `[A8h]` antes da próxima
publicação em `63h`; a G nativa alcança a publicação com o valor novo.
A diferença bruta é `22h=34`; a diferença de largura do pulso foi
`136=4×34` ticks, consistente com a escala de quatro ticks por unidade
desse agendamento no emulador. Esse evento é mediado pelo instante de
publicação de ADC3 no estado interno. O motivo anterior para a diferença
de fase do primeiro plano ainda precisa ser isolado. Capturas da janela:
`build/ma17-analysis/variants/s88_adc3_latch_pc_{G,S88,G_7580}/`.

O par também igualou a cobertura PC e as 140.578 leituras MOVC totais
da S88, mas conservou `A4h=99h` na primeira escrita. As duas células
adicionais igualaram todas as observações estruturadas de RAM nesse
ensaio, incluindo `A4h=A1h`. O efeito de `7B45h` isolado piorou a
contagem; portanto as células interagem e a atribuição de fase depende
do estado e da rotação. O [gráfico a 1.500 RPM](../build/ma17-analysis/variants/s88_phase_rpm1500_factorial.png)
mostra o evento de 136 ticks e os resíduos pequenos. Capturas:
`build/ma17-analysis/variants/s88_phase_rpm1500_{G,S88,G_7580,G_7B45,G_both,G_four}/`;
regressão `test_s88_phase_cell_pair_reproduces_adc3_sweep_at_1500_rpm`.
O programa e os bytes das duas ROMs permaneceram intactos; os resultados
continuam restritos ao perfil Fiat emulado.

Em **3.000 RPM**, com os mesmos ADCs e degraus de 1.500 RPM, houve 456
bordas CC3 por ROM. A G original coincidiu com a S88 em 427 bordas,
com diferença máxima de quatro ticks; doar apenas `7580h` elevou a
concordância a 435/456, e doar apenas `7B45h` reduziu a 425/456.
As duas células juntas reproduziram **456/456 bordas**, cobertura PC e
as 132.983 leituras MOVC da S88. A primeira escrita upper `A4h` ainda
era `99h` em G e `A1h` em S88; adicionar `7B46h/7B47h:A1h` igualou
também as observações estruturadas de RAM. O [gráfico a 3.000 RPM](../build/ma17-analysis/variants/s88_phase_rpm3000_factorial.png)
mostra resíduos de até quatro ticks e a coincidência com as duas células.
Capturas: `build/ma17-analysis/variants/s88_phase_rpm3000_{G,S88,G_7580,G_7B45,G_both,G_four}/`;
regressão `test_s88_phase_cell_pair_reproduces_adc3_sweep_at_3000_rpm`.
Os ensaios em 1.000, 1.500 e 3.000 RPM confirmam o efeito digital do
par em mais de uma faixa, mas mostram que sua magnitude depende do
regime. Não se pode extrapolar essa coincidência de bordas para todos
os estados do firmware ou para o atuador físico.

Um teste transitório aplicou um único degrau no ADC2 no tick 800.000,
com 1.000 RPM, ADC3 padrão, ADC7=63 e 1,6 milhão de ticks. Em G e S88,
o degrau digital `400→160` (bytes altos `64h→28h`) chegou a `RAM[62h]`
no tick 807.636; `RAM[48h]` mudou `40h→3Ch` nos ticks 816.935 (G) e
816.950 (S88). A programação `14h:15h` apresentou um valor intermediário
`1352` antes de estabilizar em `1336`. O degrau reverso em G restaurou
`RAM[62h]=64h`, `RAM[48h]=40h` e o valor final `1422`.

| ROM e degrau ADC2 | CC3 antes | CC3 intermediário | CC3 final | P1.3 baixo modelado antes → depois, ticks |
| --- | ---: | ---: | ---: | ---: |
| G, 400→160 | 1440 | 1352 | 1336 | ~5749→5333 |
| G, 160→400 | 1352 | 1440 | 1422 | ~5397→5677 |
| S88, 400→160 | 1440 | 1352 | 1336 | ~5749→5332 |
| G, 400 constante | 1440 | — | 1422 | ~5749→5677 |

Os valores anteriores usam a janela 400.000–800.000; os finais,
1.100.000–1.500.000 ticks. O patamar intermediário persiste até cerca
do tick 1.058.000, e o primeiro agendamento final aparece próximo de
1.087.600. O controle com `ADC2=400` constante também mudou CC3 de
`1440` para `1422` nesse momento, sem alteração em `RAM[62h]`. Portanto,
o último patamar não é efeito isolado do degrau de temperatura. Em todos
os quatro cenários, `RAM[87h]` superior caiu `1Ah→18h` em `155Bh` perto
do tick 1.073.000. O código lê `87h` em `1562h`, grava `RAM[59h:5Ah]`
em `1644h/1646h` e lê esse par em `1D60h` antes de calcular a saída.
No degrau G/S88 descendente,
`5Ah` mudou `5Ch→04h` perto do tick 817.000; `59h:5Ah` mudou de
`05h:04h` para `04h:F4h` perto do tick 1.083.260, imediatamente antes
do novo patamar de CC3. No degrau inverso G, `5Ah` mudou `04h→5Ch`
perto de 817.000 e terminou em `4Ah` perto de 1.083.260. Essa
sequência e o controle apontam para a queda temporal de `87h` como
contribuição ao último patamar, mediada por `59h:5Ah`; sua relação causal
exata ainda precisa de isolamento. Os testes
`test_air_adc_step_changes_cc3_schedule_and_modeled_pulse` e
`test_air_adc_step_cc3_late_change_has_constant_adc_control` conferem as
quatro execuções, os hashes originais, os valores de RAM, o agendamento e
as larguras dos pulsos modelados. Capturas:
`build/ma17-analysis/variants/adc2_step_cc3_g/`,
`adc2_step_cc3_g_reverse/`, `adc2_step_cc3_s88/` e
`adc2_cc3_g_constant_control/`.

Para medir ADC2 depois dessa mudança de estado, outro ensaio deslocou
o degrau para o tick 1.200.000, após a queda `87h=1Ah→18h`. O valor
`RAM[62h]` mudou no tick 1.206.996; `RAM[48h]` mudou perto de 1.216.560.
O próximo agendamento CC3, perto de 1.236.100, passou **diretamente**
de `1422` para `1336` em G/S88. O degrau inverso G passou diretamente
de `1336` para `1422`. As larguras baixas modeladas mudaram de cerca
de 5677 para 5333 ticks e vice-versa; não houve patamar `1352/1440`
após o degrau tardio. O teste
`test_air_adc_step_after_87_decay_isolates_cc3_change` verifica as três
execuções e os hashes das ROMs. Capturas:
`build/ma17-analysis/variants/adc2_step_post87_g/`,
`adc2_step_post87_s88/` e `adc2_step_post87_g_reverse/`. Esse contraste
separa o efeito digital de ADC2 do decaimento temporal observado em `87h`;
a grandeza física de CC3/P1.3 continua não validada.

O ensaio complementar `test_coolant_adc_step_changes_cc3_after_87_decay`
fixa ADC2=400, ADC7=63 e 1.000 RPM, e aplica ADC3=320→160 no tick
1.200.000, também após a queda de `87h`. Em G e S88, `RAM[63h]`
passou de `50h` a `28h` em `4756h`, enquanto `RAM[62h]` permaneceu
`64h`. A janela anterior tinha `14h:15h=1422`; a posterior, `1326`.
Controles com ADC3=320 constante permaneceram em `1422` nas duas
janelas. A largura baixa mediana de CC3 modelada caiu de cerca de 5677
para 5293 ticks. Isso verifica a resposta digital dinâmica do canal de
água sem converter esses códigos ADC em graus ou validar o pino físico.

Uma grade adicional, reproduzível com
`python3 tools/run_ma17_variant_experiments.py --temperature-grid --output-dir build/ma17-analysis/variants/temperature_grid_adc517a`,
fixa 1.000 RPM, ADC7=63 e 2,4 milhões de ticks. Cada linha altera
somente um canal em relação a ADC2/ADC3=100/80. G e S88 produziram os
**mesmos** bytes `62h/63h`, `48h` e medianas CC3 abaixo:

| Canal | ADC | `62h:63h` | `48h` | `14h:15h` mediana | P1.3 baixo modelado, ticks |
| --- | ---: | --- | --- | ---: | ---: |
| Ar, ADC2 | 20 | 14h:50h | 3Ah | 1304 | 5205 |
| Ar, ADC2 | 80 | 50h:50h | 3Fh | 1400 | 5589 |
| Ar, ADC2 | 160 | A0h:50h | 42h | 1495 | 5969 |
| Ar, ADC2 | 220 | DCh:50h | 48h | 1616 | 6453 |
| Água, ADC3 | 20 | 64h:14h | 40h | 1096 | 4373 |
| Água, ADC3 | 80 | 64h:50h | 40h | 1422 | 5677 |
| Água, ADC3 | 160 | 64h:A0h | 40h | 1945 | 7769 |
| Água, ADC3 | 220 | 64h:DCh | 40h | 2678 | 10701 |

Houve 39 voltas e 920 leituras da matriz `7581h` por caso. P5.0
permaneceu em 1861 ticks na G e 1921 na S88 em toda esta grade; isso
vale para a janela e o estímulo usados, não para todas as condições.
A curva **assumida pelo scanner** atribuiria aproximadamente 93→−22 °C
a ADC2=20→220 e 88→−24 °C a ADC3=20→220. Esses graus não foram medidos
na ECU: resistores, NTC e condicionamento analógico continuam incertos.
O teste de integração agora refaz também estes pontos digitais.
Um ensaio isolado dos opcodes A/S37 em `4830h..483Ch` confirmou a
varredura de `7002h→73D4h` nos extremos da grade: `63h=14h/50h/A0h/DCh`
produz `(R5,R6,4Eh)=(0,00h,00h)/(3,20h,23h)/
(5,E0h,E5h)/(9,00h,09h)`. No relatório de execução completa G/S88 com
ADC3=20, `4Eh` não apareceu no rastreador de **mudanças** porque seu
valor calculado é `00h`; ausência de evento não significa ausência da
consulta à tabela. As leituras `MOVC` em `73D4h..73DFh` ocorreram.

Para separar o efeito da tabela do efeito total de ADC3, um contrafactual
manteve G e S88 intactas, ADC2=100, ADC3=80, ADC7=63, 1.000 RPM e
2,4 milhões de ticks. Somente o valor devolvido pelo `MOVC` em
`52A2h/73D9h` mudou de `2Ah` para `01h`; o trace bruto continuou a
registrar `2Ah` e os SHA-256 das ROMs permaneceram originais. Nas duas
ROMs, `RAM[63h]` ficou em `50h`, mas `RAM[4Eh]` passou de `23h` para
`F3h`; a escrita em RAM superior `87h` feita por `12CCh` passou de
`1Ah` para `1Dh`. A mediana de `RAM[14h:15h]` mudou de 1422 para
1498, e a largura baixa modelada de CC3/P1.3 de 5677 para 5981 ticks;
P5.0 manteve 1861 ticks em G e 1921 em S88. Isso demonstra uma
contribuição digital causal da leitura segmentada para o agendamento
modelado. O valor `01h` é sintético; o ensaio não calibra temperatura nem
identifica eletricamente o atuador. O teste
`test_coolant_segment_movc_result_changes_cc3_without_rom_patch`
reproduz os quatro cenários. Capturas:
`build/ma17-analysis/variants/coolant_73d4_fraction_{control,override}_{g,s88}/`.
Os opcodes originais de `527Ch..52CCh` mostram uma varredura reversa de
segmentos seguida de quatro passos de divisão por deslocamento e subtração.
Para `63h=50h`, o teste isolado chega a `52A2h` com resíduo `R0=7`,
índice `R3=3` e `A=4`, selecionando a largura `ROM[73D9h]=2Ah` (42).
A fração de quatro bits é `floor(16×7/42)=2`, formando `4Eh=23h`.
Trocar apenas essa leitura por `29h`, `2Bh` ou `30h` manteve `4Eh=23h`
e CC3=1422 no ensaio G; larguras `08h/10h/18h/20h/40h` deram
`4Eh=E3h/73h/43h/33h/13h`, coerentes com a quantização do quociente.
Uma edição real da célula da ROM também afetaria a leitura anterior em
`5289h`, capaz de alterar a seleção do segmento; esses contrafactuais
isolam somente o segundo uso em `52A2h`.

Na revisão A/S37, o consumidor homólogo da tabela `7100h` está em
`46D9h..46E8h`: lê `IRAM[62h]`, carrega `DPTR=7100h` e chama `53D6h`.
O teste isolado com os opcodes originais obtém `IRAM[7Ch]=7Eh` para
`62h=64h` e `76h` para `62h=28h` nas duas ROMs. Com `2Fh.5=1`,
o ramo ignora a tabela e grava `80h`. Isso confirma o consumidor e sua
guarda nessas revisões; ainda não demonstra o percurso completo até CC3
nem a identidade física do sensor em A/S37.
O agendador `06D0h` usa `MOVC A,@A+PC` em `06E1h`: os índices 8 e 7
retornam `62h` e `63h`, selecionando respectivamente ADC2 e ADC3 em
`ADCON0`. Um segundo ensaio isolado injeta um resultado de conversão
em `0716h`: ADC2 grava `IRAM[62h]` em `0744h`; ADC3 redireciona a
gravação para `IRAM` superior `A8h`. A associação de ADC3 a `63h`
passa pelo processamento de faixa em `46E6h..4815h`, não por essa escrita
direta. Os testes isolados não executam a conversão física nem um boot A/S37.

Assim, os dois canais afetam o agendamento CC3 modelado nas duas ROMs sob
estas condições. O efeito do `ADC3` ocorre sem mudança no valor final de
`IRAM[48h]`, indicando que observar apenas esse byte perderia parte da
cadeia. As medianas iguais entre G e S88 não anulam as diferenças de
lookup entre as ROMs nem demonstram qual tabela produz a compensação.
O trace de `MOVC` mostra que mudar `ADC2` deslocou o par lido de
`7103h/7104h` para `7101h/7102h` e outro de `716Fh/7170h` para
`716Dh/716Eh`. No código G, `461Ch` e `3C65h` carregam essas bases com
`IRAM[62h]`. Mudar `ADC3` deslocou a busca de segmentos em `73D4h`,
apontada por `7002h` e consultada em `4773h` com `IRAM[63h]`.
Essas três estruturas têm os mesmos bytes nas seis imagens; sua participação
no cálculo final de CC3 foi isolada para `7100h` em G e S88. Uma
intervenção opcional substituiu **somente o resultado** de `MOVC` em
`7100h..7108h` por `valor+08h`, preservando a ROM, os estímulos ADC e os
bytes brutos registrados pelo trace. Com `ADC2=100`, `RAM[62h]` ficou
`64h`, enquanto `RAM[7Ch]` passou de `7Eh` a `86h`, `RAM[48h]` de `40h`
a `44h`, a mediana de `RAM[14h:15h]` de 1422 a 1508 e a largura baixa
modelada de CC3 de 5677 a 6021 ticks nas duas ROMs. Isso demonstra uma contribuição
causal da tabela `7100h` dentro do emulador, sem fixar sua escala física
ou provar o destino elétrico de CC3. Controle e intervenção:
`build/ma17-analysis/variants/experiments_adc517a/gate63_baseline/gasoline/`
e `build/ma17-analysis/variants/adc2_7100_delta08/` (G) e
`adc2_7100_delta08_s88/` (S88).

A mesma curva `7100h` alcança outro estado usado pelas matrizes de
120 bytes. Na ROM G, `14D9h` lê `7Ch`, `14F0h` consulta a curva
`715Ah..7162h` (nove bytes idênticos nas seis ROMs), `14F8h` chama
a multiplicação em `5259h` e `14FDh` grava o resultado na RAM
superior `AEh` via `@R0`. A revisão A carrega `715Ah` em `153Eh` e
também escreve `@R0` com `R0=AEh`; o percurso completo nessa revisão
continua sem ensaio de boot validado.

Com G a 1.000 RPM, ADC0/6=40/95, ADC3/5/7=20/40/63 e 2,4 milhões
de ticks, o probe imediatamente antes da escrita em `14FDh` registrou
230 passagens. Em 95 delas, `7Ch/ACC` foi `7Eh/21h` com ADC2=100.
Mantendo o ADC2 e fornecendo `valor+08h` apenas aos `MOVC` de `7100h`,
essas 95 passagens tornaram-se `86h/23h`; com ADC2=200, `89h/24h`.
O hash da ROM G e os bytes brutos de `715Ah` não mudaram. O teste
`test_adc2_lookup_reaches_upper_ae_writer_in_fiat` fixa as três
condições. Isso comprova um caminho digital de ADC2 até `AEh` no estado
emulado, mas não estabelece a escala física nem prova que a seleção de
linha de `7B46h` mudou nessas mesmas passagens. De fato, as três
condições fizeram as mesmas 918 leituras `MOVC` de `7B46h`, nos mesmos
endereços; `69h` terminou em `9Ah` e P5.0 manteve mediana de 1861
ticks. A alteração de `AEh` não produziu diferença observável nessa
saída sob essas condições. Capturas:
`upper_ae_source_sweep/`.

Uma varredura de ADC2 encontrou uma fronteira natural do índice. Com
os mesmos estímulos e ADC2=4, o probe em `330Dh` viu `AEh=1Dh` em 95
passagens; o `MOVC` da matriz `7B46h` leu `7B58h` 95 vezes e `R2=96h`
apareceu 95 vezes em `3371h`. Em ADC2=100, essas leituras foram a
`7B67h` e `R2=97h`; `AEh=21h` nas passagens correspondentes.
Mantendo ADC2=100 e somando `F2h` módulo 256 **somente ao retorno dos
MOVC de `7100h`**, as distribuições de `AEh`, endereços da matriz e
`R2` reproduziram exatamente o caso ADC2=4. Esse ensaio separa a
contribuição digital da curva `7100h` da mudança de estímulo ADC.
`IRAM[69h]` terminou em `9Ah` e a mediana P5.0 ficou em 1861 ticks
nos três casos; a mudança de célula não implicou mudança dessa saída.
O teste `test_adc2_7100_crosses_upper_ae_matrix_segment_in_fiat`
reproduz o contraste. A escala física de ADC2 continua hipotética.
Capturas: `upper_ae_index_grid/`.

A repetição na S88, que executa o mesmo bloco consumidor G, mostrou
por que a diferença uniforme `+08h` dos bytes da matriz não se aplica
diretamente ao resultado natural. Com ADC2=100, S88 chegou a
`AEh=1Fh`, `BCh=15h` em 210 passagens por `330Dh`, leu `7B69h` 209
vezes e obteve `R2=92h` em 209 passagens por `3371h`. Em ADC2=4,
`AEh=1Bh` apareceu 95 vezes e 95 leituras migraram para `7B5Ah`.
As duas células S88 contêm `93h`; a distribuição de `R2=92h`
permaneceu igual. `69h=95h` e P5.0=1921 ticks também permaneceram.
Na G, o mesmo par de entradas usa `BCh=03h` e outras células. Logo,
comparar apenas a diferença de byte na mesma posição da ROM omite a
mudança de índices. O teste
`test_s88_adc2_segment_crossing_reads_equal_matrix_cells` fixa o
contraste; a causa completa da diferença G/S88 em `AEh` e `BCh`
continua aberta. Capturas: `upper_ae_index_s88/`.

Um fatorial de 2,4 milhões de ticks separou o último byte do segmento
de RPM (`7580h`: G=`10h`, S88=`25h`) da matriz `7B46h`. O G recebeu
somente os valores **retornados por `MOVC`**, preservando a ROM ativa;
ADC0/2/3/5/6/7=40/100/20/40/95/63 e 1.000 RPM ficaram fixos.
`R2` abaixo é o valor dominante em 209 passagens por `3371h`;
`69h` e `34h` são os últimos valores registrados.

| ROM ativa e intervenção | Célula em `532Fh` | `R2` | `69h` | `34h` | P5.0 baixo, ticks | CC3 baixo, ticks |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| G original | `7B67h` | `97h` | `9Ah` | `8Bh` | 1861 | 2413 |
| G + matriz S88 `7B46h` | `7B67h` | `9Fh` | `A2h` | `A8h` | 1861 | 2412 |
| G + `7580h=25h` | `7B5Ah` | `8Ah` | `8Dh` | `DDh` | 1921 | 1797 |
| G + ambas | `7B5Ah` | `92h` | `95h` | `FAh` | 1921 | 1797 |
| S88 natural | `7B69h` | `92h` | `95h` | `FAh` | 1921 | 2301 |

O byte `7580h` moveu `BCh=03h→15h` na G e mudou também `AEh`;
as duas intervenções juntas reproduziram `R2`, `69h`, a recarga
e a mediana P5 da S88, embora a S88 consultasse outra célula.
`7B5Ah` e `7B69h` valem ambos `93h` na matriz S88. A mediana CC3
continuou diferente, portanto o fatorial explica somente o caminho
observado até P5 nesse estado. A origem da diferença residual em
`AEh` e as outras calibrações que afetam CC3 ainda exigem investigação.
Teste: `test_7580_and_7b46_factorial_separates_p5_from_cc3`;
capturas: `7580_7b46_factorial/`.

A diferença residual em `AEh` e CC3 foi rastreada à matriz `7581h`
nesse mesmo estado. Com G e `7580h=25h`, acrescentar `+15h` somente aos
retornos `MOVC` de `7581h..7661h` mudou a distribuição dominante de
`AEh=17h/18h` para `1Fh`, deslocou a leitura dominante de `7B46h`
de `7B5Ah` para `7B69h` e elevou a mediana CC3 de 1797 para 2300
ticks. Acrescentar também as células S88 de `7B46h` mudou `R2=8Ah`
para `92h`, `69h=8Dh` para `95h` e CC3 para 2301 ticks.

Com as **três** intervenções (`7580h`, `7581h`, `7B46h`), G reproduziu
as distribuições observadas de `AEh/BCh`, leituras da matriz e `R2`
da S88 natural, além dos últimos `69h=95h`, `34h=FAh` e das medianas
P5.0=1921 e CC3=2301 ticks. O teste repetiu esse contraste com
ADC2=4 e 100, conferindo os hashes separados da ROM G ativa e da
doadora S88. Os resumos de lookup, CC3 e cobertura de PCs coincidiram;
os histogramas finos de P5 e algumas histórias de RAM continuaram
diferentes. Assim, a igualdade demonstrada é **dos estados e saídas
selecionados nesses dois estímulos**, sem equivalência global entre
firmwares ou identificação elétrica do bico e das bobinas. Teste:
`test_three_s88_calibrations_match_selected_outputs_at_two_adc2_states`;
capturas: `7580_7581_7b46_factorial/`.

Já a busca em `716Ch` ocorre em `3C65h..3C73h` e grava o resultado em
**IRAM superior CCh** por `MOV @R1,A`. O bloco `398Dh` pode ler esse byte
antes de atualizar IRAM superior C8h, mas nenhum dos 18 casos da grade
G/S88 de 2,4 milhões de ticks executou `398Dh`. Portanto, os acessos
observados a `716Ch` ainda não demonstram efeito dessa tabela na
temporização CC3. A condição de entrada em `398Dh` depende dos desvios
em `397Dh..398Bh`; o estímulo que a abriu é descrito adiante.
Um teste controlado executou os opcodes originais `397Dh..399Eh` em G/S88
e os homólogos `39ABh..39CCh` nas outras quatro ROMs. Com
`B=10h`, `CCh=05h`, `AEh=40h` e `2Fh.2=0`, a comparação com
`ROM[7349h]=5Eh` manteve `C8h=10h`; ligar `2Fh.2` ou elevar
`AEh` a `60h` abriu a guarda e escreveu `C8h=15h` nas seis imagens.
Com a guarda aberta e `CCh=00h`, `C8h` voltou a `10h`.
Isso confirma que `CCh` pode contribuir para `C8h` nesse estado digital,
mas esse teste isolado não mostra a entrada no ramo durante um boot, nem
um efeito de `716Ch` sobre CC3. Teste:
`Sab80C517.AirLookupUpperIramCcReachesC8OnlyWhenGuardOpensInSixRoms`.
Um probe opcional (`MA17_TRACE_AIR_716C_GATE=1`) seguiu essa guarda na
ROM G com `ADC3=80/4/20/160/247` e com quatro pares adicionais de TPS.
No caso basal e no extremo `ADC3=4`, `PSW=02h` em `3CDAh` (bit 5 limpo),
o fluxo passou por `3CE2h→3D0Bh→3D0Ch`, onde `2Fh.2` recebeu zero.
Mesmo depois de `CCh=05h`, não houve execução de `398Dh`. Em ambos,
`ROM[7349h]=5Eh` e a RAM superior `AEh=40h` na maior parte das
passagens por `397Dh`; a comparação de `3980h..398Bh` também não abriu
o ramo. As capturas ficam em `build/ma17-analysis/variants/air_716c_gate/`.
Este resultado delimita os estados testados. Um boot posterior da ROM G
original, sem forçar `P4.6`, com 1.000 RPM, ADC0/6=180/247,
ADC3/5/7=40/40/63 e 2,4 milhões de ticks alcançou `11A8h` e
`398Dh`; o probe registrou 169 passagens por `398Dh` antes de seu
limite de 3.000 eventos. `2Eh.6` estava ligado e `R2<6Fh` em 341
passagens por `3CB7h`. O `MOVC` em `532Fh` leu `716Fh=86h` 11 vezes
e o par em `5333h` leu `7170h=80h` 11 vezes. No estado dominante
observado em `398Dh`, `CCh=C8h=05h`.

No contrafactual com as mesmas entradas, fornecer `8Eh` somente ao
`MOVC 532Fh` para `716Fh` mudou `CCh=C8h` para `0Ch` em `398Dh`.
Em `39F4h`, imediatamente antes de `MOV R2,A`, `R2=9Dh` nos dois
ensaios, enquanto `A` passou de `A2h` para `A9h`; portanto a
alteração também alcança o próximo cálculo em registrador.
O trace continuou a registrar o byte bruto `86h`, e o SHA-256 da ROM
permaneceu igual. O código em `3AE4h..3B06h` usa o valor seguinte para
gravar `RAM[69h]`: `A2h` no controle, `A5h` na intervenção. A última
escrita em `RAM[34h]` por `051Ch` mudou de `A8h` para `34h`.
Em 36 pulsos por canal, a largura baixa mediana dos latches modelados
`P5.0/P5.1` mudou de 1.861 para 1.921 ticks; o período mediano ficou
em 59.400 ticks. A mediana do pulso baixo CC3 modelado permaneceu
4.593 ticks nos dois ensaios.

Um cruzamento com o override de leitura de `RAM[69h]` em `043Bh`
isolou a mediação nesse estado: com `MOVC 716Fh→8Eh`, fornecer
`69h=A2h` restaurou P5 a 1.861 ticks, embora o firmware continuasse
escrevendo `A5h` em `3B06h`. Sem intervir em `716Fh`, fornecer
`69h=A5h` elevou P5 a 1.921 ticks, apesar da escrita nativa de
`A2h`. CC3 manteve 4.593 ticks nos quatro casos. Assim, `716Ch`
altera a temporização modelada de P5 por `CCh→C8h→R2→69h→Timer 1`
nesse perfil emulado. O circuito conectado a P5, a identidade física
do canal ADC2 e a escala da tabela ainda não foram validados. Capturas em
`air_716c_gate/tps_180_247_p46high*/`; teste
`test_air_lookup_716f_changes_p5_through_ram69_in_full_fiat_boot`.
Repetir o par controle/`MOVC→8Eh` com as mesmas entradas em outras
rotações confirmou que o efeito P5 depende do regime:

| RPM | Pulsos baixos por canal | Período P5, ticks | P5 baixo controle→intervenção, ticks | CC3 baixo em ambos, ticks |
| ---: | ---: | ---: | ---: | ---: |
| 750 | 28 | 79.200 | 1.860→1.940 | 4.641 |
| 1.000 | 36 | 59.400 | 1.861→1.921 | 4.593 |
| 1.500 | 56 | 39.600 | 1.767→1.805 | 5.137 |

Todos os pares leram `716Fh` 11 vezes e alcançaram `398Dh`; a escrita
inicial de `69h` em `3B06h` mudou de `A2h` para `A5h`. Em 1.500 RPM
houve escritas posteriores `A1h/A4h`, respectivamente. Assim, os
80/60/38 ticks são efeitos medidos do cenário emulado, sem escala
física atribuída. Capturas `air_716c_gate/rpm{750,1500}_*/`; teste
`test_air_lookup_716f_p5_effect_varies_with_rpm`.
Um fatorial adicional cruzou `716Fh→8Eh` com a doação dos 120 bytes
de `7CAEh` da ROM S88 para os retornos `MOVC` da ROM G ativa, mantendo
os mesmos ADC, 1.000 RPM e ROM G intacta. Cada caso leu a matriz
`7CAEh` 912 vezes. O probe em `3B06h` observou:

| `716Fh→8Eh` | Matriz S88 | IRAM superior `8Ch` | `69h` gravado | P5 baixo mediano, ticks |
| --- | --- | ---: | ---: | ---: |
| Não | Não | `A2h` | `A2h` | 1.861 |
| Sim | Não | `A9h` | `A5h` | 1.921 |
| Não | Sim | `AAh` | `A5h` | 1.921 |
| Sim | Sim | `B1h` | `A5h` | 1.921 |

Os dois efeitos internos somam `07h+08h` antes da limitação. No ramo
observado, `2Bh.4=0` e os opcodes `3AF1h..3B06h` calculam
`RAM[69h]=min(IRAM_superior[8Ch],ROM[72A7h])`.
`ROM[72A7h]=A5h` nas seis imagens, portanto os três estados acima do
limite produzem o mesmo `69h` e a mesma mediana P5. Isso explica por que
as intervenções individuais e combinada não se somam na saída medida;
outros estados de guarda podem usar outra regra. Capturas em
`air_716c_7cae_factorial/ram69_*/`; teste
`test_air_lookup_and_7cae_donor_share_ram69_cap`.
O mesmo fatorial a 1.500 RPM, com os demais estímulos iguais, mostra
onde a limitação passa a atuar:

| `716Fh→8Eh` | Matriz S88 | IRAM superior `8Ch` | `69h` dominante | P5 baixo mediano, ticks |
| --- | --- | ---: | ---: | ---: |
| Não | Não | `9Ch` | `9Ch` | 1.767 |
| Sim | Não | `A3h` | `A3h` | 1.805 |
| Não | Sim | `A4h` | `A4h` | 1.766 |
| Sim | Sim | `ABh` | `A5h` | 1.805 |

Aqui só a combinação ultrapassa `A5h`; a matriz sozinha não é
limitada em `69h`, mas altera a mediana P5 em apenas −1 tick. Assim,
a limitação explica a igualdade `69h=A5h` das três intervenções a
1.000 RPM, porém não explica sozinha a resposta de P5 em outro regime.
O histograma agora gerado pelo tracer mostra que esse −1 tick é
recorrente em P5.0: no controle, 52 de 56 larguras são 1.767 ticks;
com a matriz S88, 50 de 56 são 1.766 ticks. Os primeiros pulsos de
775/815 ticks são transitórios e não definem a mediana. Um probe opcional
(`MA17_TRACE_TIMER1_PATH=1`) em `0223h`, `0252h`, `0286h`, `0298h` e
`0090h` registrou 111 passagens por **cada** carga `0286h`/`0298h`
em 2,4 milhões de ticks, com ou sem a matriz S88. No fim da captura,
o controle tinha `32h:33h=C5FFh` e `34h:35h=F1FEh`; a matriz S88,
`D9FFh` e `04FFh`. O código em `0286h` escreve `TL1←34h, TH1←35h`;
em `0298h`, `TL1←32h, TH1←33h`. Com `TMOD=11h` (Timer 1 modo 1),
essas cargas representam 271/59 contagens até overflow no controle e
252/39 na matriz, respectivamente. O `TCON=15h` observado imediatamente
antes das cargas mostra `TR1=0` nesses pontos; `0237h` liga o timer e
o vetor `001Bh` o desliga. Nos últimos dez pulsos P5.0 emparelhados,
o intervalo da borda baixa em `00A8h` até a carga em `0298h` foi
56 ticks no controle e 75 com a matriz (+19); da carga até a borda
alta em `0098h`, foi 1.711 e 1.691 (−20). A soma dá as larguras
1.767 e 1.766: a mudança líquida de −1 tick resulta desses dois
intervalos opostos. A razão pela qual a matriz desloca a carga em
relação à primeira borda ainda exige seguir a temporização de IEX3.
Este probe não prova a conexão física a uma bobina. Capturas
em `timer1_7cae_path/{control,matrix}/`; teste fatorial automatizado.
O CC3 mediano ficou em 5.137 ticks nos quatro casos. Capturas em
`air_716c_7cae_factorial/rpm1500_*/`.

Em 2.000 RPM, repeti o mesmo fatorial com G intacta,
`ADC0/3/5/6/7=180/40/40/247/63` e 2,4 milhões de ticks. Cada caso
leu `716Fh` 11 vezes e `7CAEh..7D25h` 912 vezes:

| `716Fh→8Eh` | Matriz S88 | `8Ch` dominante | `69h` final | P5.0 baixo mediano | CC3 baixo mediano |
| --- | --- | ---: | ---: | ---: | ---: |
| Não | Não | `92h` | `92h` | 1.805 | 5.173 |
| Sim | Não | `99h` | `99h` | 1.834 | 5.172 |
| Não | Sim | `9Ah` | `9Ah` | 1.805 | 5.173 |
| Sim | Sim | `A1h` | `A1h` | 1.832 | 5.172 |

As contribuições internas continuam `+07h` e `+08h`, e os quatro
valores ficam abaixo do limite `72A7h=A5h`. A matriz isolada muda
`69h` sem mudar a **mediana** P5.0; somada à curva, reduz essa mediana
em 2 ticks em relação à curva isolada. Os histogramas têm, no valor
modal, 66/75 larguras de 1.805 no controle, 63/75 de 1.805 com a
matriz, 63/75 de 1.834 com a curva e 57/75 de 1.832 com ambas.
Portanto, o limite `A5h` não explica a resposta temporal neste estado;
a posição da carga do Timer 1 e os demais estados internos ainda podem
contribuir. Capturas: `air716f_7cae_rpm2000/{control,air,matrix,both}/`;
o teste fatorial agora cobre também 2.000 RPM. Esses valores são ticks
emulados, sem identificação física confirmada das saídas P5.

Para isolar os 2 ticks, alterei somente a leitura de `RAM[69h]` em
`043Bh`, mantendo a doação de `716Fh` nos quatro casos. A escrita
nativa em `3B06h` continuou a produzir `99h` sem matriz e `A1h` com
matriz:

| Matriz S88 | Valor fornecido em `043Bh` | `69h` nativo final | `34h:35h` final | P5.0/P5.1 baixo mediano |
| --- | ---: | ---: | ---: | ---: |
| Não | nativo | `99h` | `9AFFh` | 1.834 |
| Não | `A1h` | `99h` | `A8FFh` | 1.832 |
| Sim | nativo | `A1h` | `A8FFh` | 1.832 |
| Sim | `99h` | `A1h` | `9AFFh` | 1.834 |

O CC3 modelado ficou em 5.172 ticks nos quatro casos. A troca em
ambas as direções mostra que, **neste estado emulado**, o valor de
`69h` consumido pelo cálculo do Timer 1 medeia a diferença de 2 ticks
entre curva isolada e combinação. A igualdade de mediana não implica
histogramas nem estados internos integralmente iguais. Capturas:
`air716f_7cae_rpm2000/{air,air_force_a1,both,both_force_99}/`;
regressão `test_rpm2000_7cae_p5_interaction_is_mediated_by_ram69`.
Com `MA17_TRACE_TIMER1_PATH=1`, os quatro ensaios registraram 299
cargas em `0286h`/`0298h`; cada um dos 75 intervalos baixos P5.0
emparelhados continha uma carga em `0298h`. Os pares finais
`32h:33h/34h:35h` foram `34FFh/9AFFh` quando a leitura recebeu `99h`
e `43FFh/A8FFh` quando recebeu `A1h`. Nos últimos dez pulsos, a mediana
da borda baixa `00A8h` até `0298h` mudou **143→156** ticks, e de
`0298h` até a borda alta `0098h` mudou **1691→1676**: `+13−15=−2`
ticks no intervalo completo. A regressão verifica as cargas e as duas
parcelas; capturas em `timer1_7cae_rpm2000/`. Isso fecha a cadeia
digital até a borda modelada de P5 nesse estado, sem provar a conexão
elétrica do pino.

A família S37/S36 traz uma **terceira calibração** para `7CAEh`: os
120 bytes das duas ROMs são idênticos entre si e cada célula vale
`G+16h` (módulo 256), enquanto S88 vale `G+08h`.

O [mapa gráfico S88/S37 de `7CAEh`](../build/ma17-analysis/variants/matrix_plots/matrix_7cae_s88_vs_s37.png)
mostra silhuetas iguais com deslocamento de **+14 decimal em todas as
120 células**; o CSV registra cada endereço e valor. A forma preservada
é evidência de recalibração numérica desse banco, sem fornecer sua
escala física. Comando: `/usr/bin/python3 tools/plot_ma17_matrices.py
--reference-variant S88 --matrix 0x7CAE --variant S37`.

Ao fornecer somente os retornos `MOVC` dessa matriz S37 à ROM G intacta,
com os mesmos ADC do fatorial acima, houve 912 leituras da região em
cada rotação:

| RPM | IRAM superior `8Ch` dominante | `69h` em `3B06h` | P5.0 baixo mediano | CC3 baixo mediano |
| ---: | ---: | ---: | ---: | ---: |
| 1.000 | `B8h` (`A2h+16h`) | `A5h` | 1.921 ticks | 4.593 ticks |
| 1.500 | `B2h` (`9Ch+16h`) | `A5h` | 1.805 ticks | 5.137 ticks |
| 2.000 | `A8h` (`92h+16h`) | `A5h` | 1.834 ticks | 5.172 ticks |

Nos três estados, `72A7h=A5h` limita o valor que chega a `69h`.
A 1.500 RPM, S88 isolada produziu `A4h` em `8Ch`, ficou abaixo desse
limite e deu 1.766 ticks em P5; S37/S36 cruzam o limite e dão 1.805.
Em 2.000 RPM, S88 isolada ficou em `8Ch=9Ah`, `69h=9Ah` e P5.0=1.805;
S37 cruzou o limite, `69h=A5h` e P5.0=1.834. Somar a intervenção
`716Fh→8Eh` à matriz S37 elevou `8Ch` a `AFh`, mas manteve `69h=A5h`
e a mediana P5.0 em 1.834; CC3 mudou de 5.172 para 5.173 ticks.
Isso testa uma segunda condição saturada no mesmo RPM. A igualdade
da mediana P5.0 não demonstra equivalência dos histogramas, dos
reloads ou do restante do estado.
Isto demonstra uma diferença funcional entre famílias de **bytes de
calibração** sob o código G. Não demonstra que uma ECU S37/S36 completa
teria essas larguras, pois seu código e perfil de hardware diferem.
Capturas: `7cae_s37_donor/rpm{1000,1500}/` e
`7cae_s37_rpm2000/{matrix,both}/`; teste
`test_s37_s36_7cae_calibration_reaches_shared_ram69_cap`.

Uma troca cruzada a 2.000 RPM isolou o valor de `69h` consumido em
`043Bh`, mantendo G como ROM ativa e doando somente `7CAEh..7D25h`:

| Matriz doada | Valor lido em `043Bh` | `69h` nativo final | `32h:33h / 34h:35h` finais | P5.0 baixo mediano |
| --- | ---: | ---: | ---: | ---: |
| S88 | nativo `9Ah` | `9Ah` | `17FFh / 60FFh` | 1.805 |
| S88 | forçado `A5h` | `9Ah` | `C5FFh / 34FFh` | 1.834 |
| S37 | nativo `A5h` | `A5h` | `C5FFh / 34FFh` | 1.834 |
| S37 | forçado `9Ah` | `A5h` | `17FFh / 60FFh` | 1.805 |

Nos últimos dez pulsos, a mediana da borda baixa até a carga em
`0298h` foi 85 ticks no grupo que recebeu `9Ah` e 40 no que recebeu
`A5h`; da carga à borda alta, 1720 e 1794,5 ticks. Os pares finais de
reload e as medianas P5.0 acompanham o valor fornecido nos dois sentidos,
mesmo quando a escrita nativa de `69h` permanece diferente. Isso confirma
que a leitura de `69h` medeia essa diferença **no código G emulado**;
as distribuições de pulsos e demais estados não foram equiparados.
Capturas: `7cae_family_ram69_cross_rpm2000/`; teste
`test_s37_s88_rpm2000_p5_difference_is_mediated_by_ram69`.

Mantive 2.000 RPM, `ADC0/3/5/6/7=180/40/40/247/63` e alterei
apenas o estímulo digital ADC2 para 40 ou 220. Em cada estado comparei
G intacta com os retornos `MOVC` de `7CAEh` fornecidos por S88 ou S37:

| ADC2 | Matriz fornecida | Leituras `7CAEh` / `7B46h` | `8Ch` dominante | `69h` final | P5.0 baixo mediano | CC3 baixo mediano |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 40 | G | 912 / 6 | `94h` | `94h` | 1.805 | 4.865 |
| 40 | S88 | 912 / 6 | `9Ch` | `9Ch` | 1.805 | 4.865 |
| 40 | S37 | 912 / 6 | `AAh` | `A5h` | 1.834 | 4.864 |
| 220 | G | 0 / 918 | `92h` | `92h` | 1.805 | 5.633 |
| 220 | S88 | 0 / 918 | `92h` | `92h` | 1.805 | 5.633 |
| 220 | S37 | 0 / 918 | `92h` | `92h` | 1.805 | 5.633 |

Em ADC2=220, o código G selecionou leituras em `7B46h` e nenhuma
em `7CAEh..7D25h`; as doações nessa região não alteraram os três
resultados medidos. Em ADC2=40, S37 cruzou o limite `72A7h=A5h` e
mudou P5.0 em +29 ticks, enquanto S88 mudou `69h` sem mudar a mediana
P5.0. Isso estabelece uma seleção **condicionada pelo estado ADC2**
nessas entradas digitais, sem comprovar a grandeza física do canal ou
generalizar o resultado a todo o mapa. Capturas:
`7cae_adc2_rpm2000/`; teste
`test_adc2_switches_7cae_donor_effect_at_2000rpm`.

O assembly modular localiza a escolha precisamente: `3D0Ch` grava o
carry em `2Fh.2`; `334Dh` carrega o diretório big-endian `70B6h` e
`3350h` mantém esse ponteiro quando o bit está ligado, ou `3353h`
substitui por `709Ch` quando está desligado. Os primeiros ponteiros
desses diretórios são, respectivamente, `7CAEh` e `7B46h`. No trace
G a 2.000 RPM, ADC2=40 produziu carry=1 em 428/446 passagens por
`3D0Ch` e chegou a `3356h` com DPTR=`70B6h` em 228/230 passagens;
ADC2=220 produziu carry=0 em 451/451 e DPTR=`709Ch` em 230/230.
Assim, a seleção das matrizes é mediada pelo bit `2Fh.2` no código
observado. A cadeia que forma o carry em `3CDAh..3D0Bh` ainda mistura
outros estados, e a identidade física do ADC2 segue sem confirmação.
Capturas: `7cae_adc2_selector_path/`. Os aliases destes pontos e dos
dois diretórios foram adicionados ao exportador modular; uma montagem
isolada preservou 32.768 bytes com zero divergências e SHA-256 igual.

Seguindo o carry no mesmo código G, `47F4h` grava `22h.6` a partir das
comparações em `47E1h..47F3h`. Em ADC2=40, esse bit ficou limpo e
`3CFCh` saltou a leitura de `ROM[721Dh]`; em ADC2=220, ficou ligado,
`3D01h` leu `21h` em `721Dh` e `3D03h` comparou com `IRAM[63h]=28h`.
Como `21h<28h`, o salto em `3D05h` levou a `3D0Bh`, que limpou o carry.
Uma intervenção apenas no retorno do `MOVC` de `3D01h` confirmou o
limite unsigned: fornecer `27h` com ADC2=220 manteve 918 leituras em
`7B46h` e nenhuma em `7CAEh`; fornecer `28h` inverteu para 6 e 912.
Fornecer `00h` em ADC2=40 não alterou o caminho (912 leituras em
`7CAEh`), pois `3D01h` foi contornado. O hash da ROM ativa permaneceu
igual em todos os ensaios. Isso identifica uma guarda e um limiar digital
para estes estados, sem fixar a grandeza física de `63h` ou do ADC2.
Capturas: `7cae_adc2_carry_path/`; teste
`test_721d_movc_threshold_controls_matrix_selector_when_guarded`.

A origem de `22h.6` foi isolada no ramo `47E1h..47F4h`: `47E9h` lê
`ROM[721Ch]=7Fh` e compara com `IRAM[63h]`; quando o retorno é menor,
salta diretamente à escrita do bit. Caso contrário, `47F1h` lê
`ROM[72BDh]=7Ch` e compara com `IRAM[62h]`. No controle G, as leituras
em `47E9h` e `47F1h` ocorreram 42 vezes por cenário. ADC2=40 levou
`62h` a `28h` e ADC2=220 levou a `DCh`, com `63h=28h` fixo.
Fornecer apenas o retorno de `47F1h` como `27h/28h` em ADC2=40 ou
`DBh/DCh` em ADC2=220 selecionou respectivamente `7B46h/7CAEh` em
ambos os pares. Fornecer `27h` em `47E9h` com `63h=28h` selecionou
`7B46h` e suprimiu a leitura de `72BDh`; `28h` manteve `7CAEh` e
permitiu 42 leituras de `72BDh`. Os seis dumps contêm os mesmos
`721Ch=7Fh`, `721Dh=21h` e `72BDh=7Ch`. Os opcodes desse caminho são
idênticos em G/S88; no S88, fornecer `DCh` em ADC2=220 também levou
DPTR a `70B6h`, mas houve 478 leituras em `7CAEh`, contra 912 em G.
O scanner associa `62h` ao ar e `63h` à água; isso é uma pista de
interpretação, não validação elétrica ou térmica desses limiares.
Capturas: `7cae_adc2_72bd_limit/`; teste
`test_721c_72bd_movc_limits_control_matrix_family`.

O caminho tem correspondência local nas outras revisões: os 20 bytes
G/S88 `47E1h..47F4h` são idênticos a A/A+/S37/S36
`489Eh..48B1h`. Assim, `47E9h→48A6h` lê `721Ch` e
`47F1h→48AEh` lê `72BDh`. Os 18 bytes G/S88
`3CFCh..3D0Dh` coincidem com A/A+/S37/S36 `3DB4h..3DC5h`;
o `MOVC` guardado de `721Dh` corresponde a `3D01h→3DB9h`.
Os três bytes de limiar também são iguais nas seis ROMs. A comparação
de opcodes confirma a homologia dessas operações; a causalidade
dinâmica nas revisões A/S37/S36 ainda requer um perfil de hardware
validado. Teste:
`test_matrix_selector_limit_consumers_map_across_code_revisions`.

A diferença de contagem S88/G vem de outro eixo, comum aos seis dumps:
`70A8h` aponta para a tabela segmentada `7B28h` (`AEh`, oito
incrementos). Com ADC2=220, G apresentou `AEh=4Dh`, `R4=90h` e
230/230/229/229 leituras nas instruções `532Fh/5333h/534Bh/5350h`.
S88 apresentou `AEh=57h`, `R4=00h` e 230/230/12/12: `5342h` evita
o segundo par quando `R4=0`. O último incremento `7B31h=AFh` faz a
soma com `AEh` transbordar a partir de `51h`, saturando a fração nessa
extremidade. Uma intervenção só no retorno `MOVC` de `5289h/7B31h`,
de `AFh` para `A8h`, elevou `R4` dominante no S88 de `00h` para
`E0h` e restaurou 229/229 leituras no segundo par. A mediana modelada
P5.0 permaneceu 1.818 ticks; logo, a diferença de quantidade de
leituras não implica por si uma diferença nessa mediana. Os bytes
originais e o hash da ROM S88 foram preservados. Capturas:
`7cae_interpolator_axis/`; teste
`test_s88_axis_fraction_skips_second_matrix_interpolation_pair`.

No mesmo estado de 2.000 RPM e ADC bruto 180/220/40/40/247/63,
`RAM[7Ch]=8Eh` nas últimas 200 passagens por `14FDh` tanto em G quanto
em S88. O código `14D9h..14FDh` e as curvas `7100h`, `715Ah..7162h`
são idênticos, mas as calibrações `7580h` e `7581h` diferem. Um fatorial
de retornos `MOVC`, mantendo a ROM G ativa, separou sua contribuição:

| Condição | `AEh` em `14FDh` | `R4` em `3356h` | Segundo par de leituras `7B46h` (`534Bh/5350h`) |
| --- | --- | --- | --- |
| G original | `4Dh` | `90h` | 229/229 |
| G + `7580h=25h` da S88 | `4Eh` | `B0h` | 229/229 |
| G + matriz `7581h` da S88 | `55h` | `00h` | 12/12 |
| G + ambos os retornos da S88 | `57h` | `00h` | 12/12 |
| S88 original | `57h` | `00h` | 12/12 |

Cada ensaio teve 230/230 leituras no primeiro par. A combinação
reproduziu o estado selecionado da S88 sem alterar o hash da ROM G;
isso atribui a diferença observada de `AEh` a essas duas calibrações
neste estímulo. A escala física e a equivalência global permanecem
indeterminadas. Capturas: `ae_source_2000/`; teste
`test_7580_and_7581_jointly_explain_s88_upper_ae_at_2000rpm`.

Acrescentar à G os retornos da S88 apenas nas oito células de `7B46h`
efetivamente lidas nesse ensaio manteve `AEh=57h`, `R4=00h` e a mesma
contagem de leituras. Com `7580h`, `7581h` e essas células, `69h/34h`
final passou de `87h/A8h` a `8Fh/B7h`, igual à S88 natural; a mediana
P5.0 passou de 1.819 a 1.818 ticks, também igual. A mediana
`RAM[14h:15h]` foi 1.597 nos dois casos, enquanto CC3 ficou em
6.377 ticks na G com as três intervenções e 6.376 na S88. As ROMs
ativas mantiveram seus hashes. A doação restrita a oito células prova
apenas esse caminho observado, e a diferença residual de um tick em
CC3 impede declarar equivalência completa. Captura:
`ae_source_2000/g_triad_cells/`; mesmo teste de regressão.

Uma comparação de todos os endereços `MOVC` lidos apontou `7B45h`
como o único outro byte bruto divergente: G contém `05h`, S88 contém
`0Dh`, e ambas o leram 230 vezes. Fornecer `0Dh` como quarto retorno
à G eliminou o tick residual na mediana CC3 (6.377→6.376) e fez
coincidir exatamente os histogramas P5.0. No relatório `execution.json`,
`output_latches`, `cc3_observation`, `engine_ram_observation` e
`pc_coverage` ficaram iguais aos da S88 natural nesse estado.
Outras seções do trace ainda divergem; o ensaio não demonstra
equivalência global das ROMs. O hash da G ativa permaneceu original.

Em outro estado, 1.000 RPM e ADC0..7 bruto
`100/130/100/20/90/40/155/63`, os 1.200.000 ticks iniciais mostram a
interação oposta: G passa por `3356h` com `AEh=33h`, `R4=00h` em 92
consultas estáveis e pula o segundo par `534Bh/5350h`; S88 tem
`AEh=31h`, `R4=C0h` e executa o par. As leituras `MOVC` da base
`7B46h` em `532Fh/5333h/534Bh/5350h` foram `113/113/20/20` em G
e `113/113/112/112` em S88. O código em `5342h` testa `R4` antes do
segundo par; os bytes do eixo `7B28h` são iguais nas duas ROMs.

| ROM ativa e retornos S88 fornecidos a G | `AEh` estável | `R4` estável | Leituras em cada instrução do segundo par | `69h` final | CC3 baixo mediano, ticks |
| --- | --- | --- | ---: | --- | ---: |
| G original | `33h` | `00h` | 20 | `9Ah` | 3509 |
| G + `7580h` | `29h` | `00h` | 20 | `8Dh` | 2909 |
| G + matriz `7581h` | `3Ah` | `00h` | 20 | `9Dh` | 4001 |
| G + ambos | `31h` | `C0h` | 112 | `8Bh` | 3404,5 |
| G + ambos + 10 células lidas de `7B46h` | `31h` | `C0h` | 112 | `93h` | 3405 |
| G + acima + `7B45h=0Dh` | `31h` | `C0h` | 112 | `93h` | 3405 |
| S88 original | `31h` | `C0h` | 112 | `93h` | 3405 |

Assim, **os dois retornos upstream juntos**, e nenhum deles sozinho,
cruzam a guarda `R4=0` nesse estado. As dez células restauram `69h`,
`34h` e a mediana CC3; com `7B45h`, os objetos `output_latches`,
`cc3_observation`, `engine_ram_observation` e `pc_coverage` ficam
idênticos aos da S88 nesse intervalo. Um par original mais longo de
12 milhões de ticks manteve 1.167/1.167 primeiras leituras por ROM e
20/20 segundos pares em G versus 1.166/1.166 em S88. Os experimentos
fornecem retornos `MOVC` à ROM G sem alterar seus bytes; a identidade
de resumos selecionados não prova equivalência completa nem função
física do pino. Capturas: `7b46_pair_path_{g,g_7580,g_7581,
g_s88_upstream,g_cells,g_cells_7b45,s88}/` e
`iram57_long_current_{g,s88}/`. Regressão:
`tests.test_ma17_7b46_pair`.
Captura: `ae_source_2000/g_triad_7b45/`; o teste acima inclui essa
quarta intervenção.

Repeti as quatro intervenções com os mesmos ADC brutos a 1.500 e
3.000 RPM. As oito células de `7B46h` alcançadas em cada rotação foram
obtidas dos próprios traces: o par dominante migrou de `7BB5h/7BB6h`
para `7BB9h/7BBAh`. Em ambos os regimes, os objetos `output_latches`,
`cc3_observation`, `engine_ram_observation` e `pc_coverage` da G com
retornos S88 coincidiram com os da S88 natural. `69h` final foi
`99h/7Bh`, a mediana P5.0 foi 1.803/1.794 ticks e a mediana CC3
6.237/6.629 ticks, respectivamente. Os hashes das duas ROMs e do
executável do emulador foram registrados; outros campos do relatório
diferem. Capturas: `ae_four_rpm/`; teste
`test_four_s88_movc_calibrations_match_selected_reports_at_other_rpms`.

No ramo alternativo, a 2.000 RPM e ADC0/2/3/5/6/7 =
180/40/40/40/247/63, G e S88 leram seis células de inicialização em
`7B46h` e 912 células em `7CAEh`. Fornecer à G os retornos S88 de
`7580h`, `7B45h`, `7581h` e das oito células efetivamente alcançadas
em `7CAEh` igualou `output_latches`, `cc3_observation`, `pc_coverage`
e o estado final `RAM69h/34h=9Bh/60h` da S88 natural. O histórico
`engine_ram_observation` ainda diferia somente em `A4h`. A doação
adicional dos seis retornos de inicialização de `7B46h` igualou
também esse histórico. As ROMs ativas e o executável do emulador
mantiveram seus hashes; outras seções do relatório ainda divergem.
Essa equivalência se restringe aos objetos observados e ao estado
testado. Captura: `adc2_40_four/`; teste
`test_7cae_branch_needs_7b46_startup_cells_for_matching_ram_history`.

Repeti o mesmo estado ADC a 1.500 e 3.000 RPM. Após fornecer os
retornos S88 de `7580h`, `7B45h` e `7581h`, a G consultou as mesmas
células principais que a S88: 480 leituras em `7CAEh` a 1.500 RPM e
912 a 3.000 RPM, além de seis leituras iniciais de `7B46h` em cada
regime. A doação das células efetivamente alcançadas (6+6 e 8+6,
respectivamente) igualou os quatro objetos selecionados do trace
`execution.json`: `output_latches`, `cc3_observation`,
`engine_ram_observation` e `pc_coverage`. `RAM69h` final foi `A5h` e
`87h`. Hashes das ROMs originais e do executável foram verificados;
as demais seções do relatório e a função elétrica dos pinos continuam
fora dessa conclusão. Captura: `adc2_40_rpm/`; teste
`test_7cae_and_startup_donors_repeat_at_1500_and_3000rpm`.

O bit `2Eh.6` é ligado em `11A8h` e limpo em `11C4h`. Em `3CB7h`, o
firmware define `PSW.5` a partir de `2Eh.6` e da comparação de `R2`
com `6Fh`. No basal, em `ADC1=40`, a 750 RPM e no caso TPS 40/95,
`2Eh.6` ficou limpo e `R2=FFh` em todas as passagens capturadas por
`3CB7h`. Isso explica a guarda fechada nesses ensaios e indica que
alcançar `398Dh` provavelmente exige outro estado interno; forçar só
o canal de temperatura não demonstrou esse caminho.
O trace intermediário confirmou que `ADC2=40` mudou `IRAM[7Ch]` de `7Eh`
para `76h` (escrita em `4629h`) e `IRAM[48h]` de `40h` para `3Ch`
(escrita em `1523h`) nas duas ROMs. O código G usa `7Ch` na multiplicação
de `14D9h` antes de escrever `48h`, e usa `48h` novamente em `1E18h`.
Com `ADC3=40`, `IRAM[4Eh]` mudou de `23h` para `B1h` em `477Dh`, mas
`48h` ficou em `40h`. Há também subtração direta de `IRAM[63h]` em
`1DDCh`, antes da escrita de `14h:15h`; portanto, a mudança de CC3 sob
`ADC3` não pode ser atribuída apenas à tabela `73D4h`.
Em `0781h..07B5h`, `4Eh` também indexa uma estrutura de 50 bytes em
`73E0h..7411h`. Os opcodes dessa rotina são idênticos nas seis ROMs.
Com o padrão, os `MOVC` de `079Ch/07AEh` leram
`F3h/F7h` em `73F7h/7401h`; com `ADC3=40`, leram `F2h/F5h` em
`73F6h/7400h`. O código multiplica `78h` e `7Ah` por esses fatores e
conserva o byte alto do produto. Com o opcode `86h` corrigido, `78h`
permaneceu `00h` nas execuções completas de 2,4 milhões de ticks em G e
S88; os acessos à tabela ocorreram, mas sua contribuição via `78h` foi
nula nessas condições. Um teste isolado executa os opcodes originais
de G, A e S37 com `78h=7Ah=F3h`: `4Eh=23h` produz
`78h=E6h`, `7Ah=EAh`; `4Eh=B1h` produz `78h=E5h`, `7Ah=E8h`.
Outro teste sintético executa `1D4Bh..1DD8h` com `78h=19h/15h` e obtém
diferenças de `0011h/0010h` no par `R3:R2`. Esses testes demonstram a
capacidade da rota quando `78h` é diferente de zero; não atribuem a ela
o contraste CC3 observado. É necessário encontrar uma condição alcançável
que torne `78h` não nulo.
No ensaio de fronteira do ADC3 (`160→208` em 10 bits no tick 800.000),
G e S88 leram `73F4h=EEh` em `079Ch` e `73FEh=F3h` em `07AEh`, 27 vezes
cada. Substituir por `00h` somente o resultado de um desses `MOVC`,
em execuções separadas e com hashes das ROMs originais preservados,
não alterou `4Eh=00h`, a ausência de mudanças em `78h/7Ah`, a mediana
CC3 de 1160 ticks nem a largura modelada P1.3 de 4629 ticks. O teste
`test_coolant_factor_reads_do_not_change_cc3_with_zero_ram78_and_7a`
confirma também que os overrides foram efetivamente usados. Assim,
esses dois fatores não explicam a diferença CC3 do ensaio por meio de
`78h/7Ah` nesse estado; outras rotas de ADC3 e estados com operandos
não nulos permanecem em investigação.

O trace estruturado de `1DD8h` e `1E02h` separou a subtração direta de
`63h` da diferença já existente antes dela. Em cada condição de
temperatura, houve 230 pares de entrada/saída em cada ROM; **todos
preservaram `R2:R3`** nesse trecho. Perto de 2,4 milhões de ticks,
`R2:R3` era `38:05` no padrão e `55:04` com `ADC3=40` na entrada de
`1DD8h`, e ficou igual na respectiva saída `1E02h`.
Nas 18 execuções da grade G/S88, os 229–230 pares capturados por caso
também preservaram `R2:R3`. O código consulta `63h` nesse bloco, mas
ele não explica a diferença desse par de registradores nos estados testados.
Ainda faltam separar as outras rotas anteriores e verificar flags e
consumidores posteriores antes de atribuir à tabela `73E0h` uma parcela
da diferença final da largura CC3.
O contraste de fronteira `ADC3 160→204/208` forneceu uma rota mais
direta. Nos dois casos G/S88, os acessos à tabela `7426h` e a trajetória
da RAM superior `87h` foram iguais. Já `4Fh`, escrito em `4823h`, terminou
em `04h/00h`; o opcode original `E5 4F` em `1588h` o lê antes de
`1644h/1646h` gravarem `59h:5Ah`. Forçar somente essa leitura para
`00h` no caso 204 trocou `5Ah=77h→34h` e a mediana CC3 `1228→1160`;
forçar `04h` no caso 208 produziu a reversão. G e S88 repetiram os
resultados. Assim, a leitura de `4Fh` medeia o contraste digital nesse
estado, embora a identidade física da saída permaneça sem prova.

O slot antes provisório `7036h→7AE0h` cobre 32 bytes `FFh` nas seis
ROMs. O bloco G `3E41h` (A `3EFEh`) consulta o interpolador e, quando
`T2CON.1=0`, grava o resultado na XRAM paginada `F8:7Fh`. O leitor G
`480Dh` usa esse byte como fator após a curva `74EEh`.
Opções de índice preparadas `R5=0/4`, `R4=R6=0` executaram os opcodes
originais de cada ROM e gravaram `FFh`; o alcance natural máximo do
índice não foi demonstrado. Num ensaio G a 1.000 RPM com ADC2/3 de
10 bits `400/160` e ADC3 passando a `204` no tick 800.000, fornecer
`80h` somente ao retorno `MOVC 532Fh/7AE0h` mudou leituras armazenadas
de `F8:7Fh` em `480Dh` de `FFh` para `A0h/80h`. `RAM[4Fh]` final
passou de `04h` a `03h`, `RAM[5Ah]` de `77h` a `66h`, a mediana do
agendamento CC3 de 1228 a 1211 ticks e a largura baixa de P1.3
modelada de 4900 a 4832 ticks. Fornecer `FFh` apenas à leitura
`MOVX 480Dh/F87Fh` restaurou esses quatro resultados, embora a XRAM
gravada permanecesse alterada; fornecer `FFh` no controle foi neutro.
A ROM e os bytes brutos de `MOVC` permaneceram originais. `F8:7Fh`
é XRAM, não pino; a ligação física de `P1.3/CC3` ao bico monoponto
continua sem confirmação. Testes:
`SixRom7036ConstantTableWritesPagedXram7f` e
`test_7ae0_constant_table_reaches_cc3_through_f87f`;
capturas: `build/ma17-analysis/variants/7ae0_coolant_*/`.

Os ponteiros big endian `7030h/7032h/7034h` apontam para três curvas
contíguas de dez bytes em `74EEh/74F8h/7502h`. G/S88/S37/S36 têm
`00 00 04 07 0B 11 16 1A 20 24`, `00 02 05 08 0E 12 16 1A 20 24`
e `00 00 04 07 0B 11 16 1A 20 24`. A/A+ elevam todas as 30 células:
`+10h` na primeira curva e `+22h` nas duas seguintes. G seleciona os
ponteiros em `47E1h..481Ah`, interpola com `R5/R6` derivados de `63h`
e publica `4Fh` em `4823h`. No estado de fronteira, somente entregar
o byte da A em `532Fh/74F0h` (`04h→14h`) ou em `532Fh/74EEh`
(`00h→10h`) tornou `4Fh=10h`, `5Ah=41h` e a mediana CC3=1433 ticks
nas ROMs G e S88, sem editar a ROM. A largura modelada de P1.3 foi
5720 ticks. A seleção natural das outras duas curvas e o efeito da
revisão A em boot completo ainda precisam de um perfil de hardware
validado; esses valores não estabelecem uma grandeza física.
Um teste isolado executou os opcodes originais das seis ROMs para
`63h=33h/11h`, primeiro na rotina segmentada, depois na seleção das
três curvas, com `XRAM[7Fh]=FFh` e flags preparados. Para os ponteiros
`7030h/7032h/7034h`, G/S88/S37/S36 produziram `4Fh=(04h,00h)`,
`(05h,00h)` e `(04h,00h)`; A/A+ produziram `(14h,10h)`, `(27h,22h)`
e `(26h,22h)`. A concordância dentro de cada família, apesar da
revisão de código em S37/S36, associa a diferença ao conteúdo das
curvas nesse estado isolado. O teste
`Sab80C517.CoolantRam4fCurvesFollowCalibrationBytesAcrossCodeRevisions`
fixa os endereços e os resultados. Ele não demonstra que os três modos
ocorrem naturalmente em A/A+.
Nos boots completos G e S88 com ADC7=63, ADC2=160 e ADC3=80,
`DPTR=74F8h` leu `74FBh/74FCh` (índices 3/4) e `4Fh=08h`. Com
ADC2=100 e ADC3=220, o mesmo ponteiro leu `7501h/7502h` (índices
9/10), `4Eh=09h` e `4Fh=24h`. A segunda leitura atravessa o limite
físico entre as curvas, mas **não seleciona `7034h→7502h`**. Ao fornecer
`FFh` somente como retorno de `MOVC 5333h/7502h`, `4Fh`, CC3 e a
largura modelada P1.3 permaneceram `24h`, 2678 e 10701 ticks em ambas
as ROMs; a fração do índice 9 é zero nesse estado. O teste
`test_coolant_curve_7502_read_is_lookahead_from_74f8` protege essa
distinção. Ainda falta encontrar uma condição natural que selecione o
terceiro ponteiro.
O código G em `2D51h` calcula `2Fh.0 = ¬(P4.6 ∨ 27h.0)` e pode limpar
esse bit depois, conforme guardas e `XRAM[A4h]`; `481Ah` só escolhe
`7034h` quando `2Fh.0=1`. O firmware inicializa `P4=EAh` (bit 6 alto),
os traces G/S88 leram `P4=CAh` (bit 6 alto) e os snapshots posteriores
mostram `2Fh.0=0`. Por padrão, o callback usa o latch de P4 para esse bit;
não simula um sinal externo ou a saída de comparação CM6. O manual
SAB80C517 descreve P4.6 como pino bidirecional com função opcional CM6.
A conexão elétrica e o modo efetivo desse pino na ECU ainda precisam
ser identificados antes de atribuir significado físico ao terceiro modo.
O estímulo experimental `MA17_P4_6_FORCE_LOW=1` mantém a trava P4 alta
e força apenas a leitura do pino baixo, conforme o modelo GPIO do manual.
Com 1000 RPM, ADC2=160, ADC3=80 e ADC7=63, G/S88 passam a ler
`DPTR=7502h`, índice 3 (`7505h=07h`), e `4Fh` cai de `08h` para `07h`.
Sob o mesmo estímulo, substituir só o retorno desse `MOVC` pelo byte
`29h` da curva A muda `4Fh` para `25h` e a mediana CC3 de 516→705 ticks
em G e 596→820 em S88. O controle com P4.6 alto produz 1495 ticks em
ambas; essa comparação entre níveis de pino inclui outros caminhos
dependentes de P4.6. O teste
`test_p46_low_selects_third_coolant_curve_and_cell_reaches_cc3` fixa os
resultados do firmware original e do fornecimento pontual do byte.
O manual localiza `TXD0` em P3.1 e `CM6` opcional em P4.6; documentos
anteriores que chamam P4.6 de TXD não estabelecem a ligação da ECU.
Os dados estruturados e os traces individuais ficam em
`build/ma17-analysis/variants/experiments_adc517a/`.

### Matrizes `7831h/7859h/786Dh` e curva `7078h→794Dh`

As seis ROMs têm os mesmos ponteiros e bytes nessas três matrizes e na curva. O trecho
G `3D0Ch..3D42h` usa os segmentadores `7054h→7824h` (`RAM[70h]`) e
`7056h→782Bh` (`RAM[47h]`, derivada de RPM) para formar
`R5=4×linha+coluna`, com passo `R0=4` e frações `R4/R6`. Quando
`T2I1=0`, `XRAM F8:DAh=0` e `RAM[2Fh].5=0`, `3DFAh` seleciona a matriz
de **5×4** bytes em `7859h`; `3E05h` escreve o interpolado em `F8:00h`.
O segundo estágio do helper leu `786Dh`, primeiro byte do alvo seguinte,
no trace: o limite nominal de 20 bytes não é um limite rígido de leitura.

O ramo de `3DDEh..3E05h` também seleciona `705Ah→7831h` quando
`F8:DAh=0` e `RAM[2Fh].5=1`, ou `70D0h→786Dh` quando `F8:DAh≠0`.
Ambas são matrizes de 5×4 bytes idênticas nas seis ROMs e usam os mesmos
eixos e interpolador de `7859h`. Um teste dos opcodes originais G/S88 e
A/A+/S37/S36, com `R5=1` e frações zero, leu respectivamente
`7832h=40h`, `785Ah=4Dh` e `786Eh=2Fh` nos três ramos e escreveu o
byte em `F8:00h`. No trace G de 3,5 milhões de ticks com P4.6 baixo,
`F8:DAh` voltou a zero depois do padrão de inicialização `55/AA`; o
ramo `70D0h` não foi observado. O acesso natural a `705Ah` e `70D0h`
e a fiação de `F8:00h` continuam abertos. Regressão:
`Sab80C517.Pointer705a705c70d0BranchesFeedXramF800`.

Os slots ainda provisórios `7098h→7845h` (20 bytes variados) e
`70D2h→7881h` (20 bytes zero) também aparecem nesse bloco, iguais
nas seis ROMs. Contudo, `JB T2I1` em G `3DDEh`/A `3E9Bh` salta todo o
lookup quando o bit está ligado. Se ele está desligado, os `JNB T2I1`
em G `3DECh/3DF4h` (A `3EA9h/3EB1h`) desviam antes das cargas dos
dois ponteiros. Não há escrita em `T2CON` nesse trecho sem chamadas;
os 40 bytes do bloco são iguais entre G e A, salvo o destino da chamada
final ao interpolador. Executar o primeiro salto com `T2I1=1` nas seis
ROMs chegou diretamente ao ponto após a escrita `F8:00h`; a regressão
`Sab80C517.T2i1GuardSkips7098And70d2PointerPaths` fixa esse resultado.
Logo, esses alvos não têm acesso por **fluxo local ininterrupto**.
Interrupções ou outros leitores indiretos ainda precisam ser examinados;
os bytes permanecem provisórios, sem função de calibração atribuída.

Há bloqueio local semelhante para os slots provisórios
`7082h→78A9h` e `7086h→78D1h`, ambos com 20 zeros nas seis ROMs.
G `3E06h` (A `3EC3h`) pula o bloco até `3E34h` quando `T2I1=1`;
com o bit zero, os `JNB T2I1` em G `3E1Dh/3E28h` pulam as cargas
dos dois ponteiros. A execução isolada do primeiro salto nas seis ROMs
confirma a guarda. Também aqui só está excluído o fluxo local
ininterrupto; referências indiretas e interrupções não foram excluídas.
Regressão: `Sab80C517.T2i1GuardSkips7082And7086PointerPaths`.

Em contraste, `7088h→78E5h` contém 20 bytes `FFh` efetivamente lidos
quando `RAM[7Ah]=0`: G `3E34h..3E40h` (A `3EF1h..3EFDh`) consulta
o ponteiro e escreve o interpolado em `XRAM F8:FBh`. O trace G
`movc_gasoline` registrou 262 leituras de `78E5h` e 262 de `78E6h`
com `DPTR=78E5h`; S88 `movc_sun8817_2s` registrou 495 de cada.
Opções `RAM[7Ah]=0/1` nos opcodes originais das seis ROMs confirmaram
respectivamente a escrita `FFh` e o salto sem escrita. O destino físico
de `F8:FBh` segue desconhecido. Regressão:
`Sab80C517.Pointer7088LoadsFfIntoXramF8fbWhenRam7aIsZero`.
O leitor posterior é `MOVX A,@R0` em G/S88 `1CC5h`, ou na família A
`1CE1h`. Ele multiplica `F8:FBh` por um intermediário derivado de
`RAM[7Bh]` e `F8:01h`; depois `RAM[7Ah]` participa do produto que
termina em `R1`. Em novas execuções G/S88 a 1.000 RPM, ADCs padrão,
sem K-Line e por 2,4 milhões de ticks, cada ROM fez 230 leituras de
`F8:FBh` nesse PC após a escrita `FFh` em `3E40h`. As duas leituras
anteriores em `55A2h` pertencem ao autoteste de XRAM.
Um teste dos opcodes originais nas seis ROMs, com `P2=F8h`,
`RAM[7Bh]=78h` e `F8:01h=61h`, mostrou `R1>0` somente quando
`RAM[7Ah]=80h` e `F8:FBh=FFh`; zerar qualquer um deles deu `R1=0`.
Isso identifica um consumidor digital condicional, sem demonstrar o
papel físico do campo nem a seleção natural desse ramo na família A.
Reprodução: `MA17_TRACE_XRAM_ADDRESS=F8FB python3 tools/trace_ma17.py
--rpm 1000 --crank-immediate --no-kline-inject --stop-ticks 2400000
--output-dir build/ma17-analysis/variants/f8fb_reader_g_current`;
regressão: `Sab80C517.SixRomF8fbReaderFeedsRam7aMultiplyChain`.
Num segundo ensaio, G e S88 originais receberam ADC0..7 brutos
`180/130/140/4/90/200/247/63` e um degrau ADC0/6 para `160/380` no
tick 3.274.600. Em 4 milhões de ticks, cada ROM passou 386 vezes por
`1CB7h`; 69 saídas em `1CDFh` tinham `RAM[7Ah]≠0`. Fornecer `00h`
**somente** à leitura `MOVX 1CC5h/F8:FBh` manteve o byte armazenado
`FFh`, mas reduziu `B` de `0Ch..16h` para `00h` nas 69 saídas. As ROMs
e seus hashes permaneceram originais. Os inícios de pulso CC3 modelados
ficaram em 129 nos dois braços de cada ROM; o menor intervalo bruto
agendado mudou de 226→595 ticks em G e 218→568 em S88. A mediana de
P5.0 permaneceu 1.921/1.863 ticks. Portanto o campo participa
causalmente do cálculo digital nesse estado, mas este ensaio não
identifica sua função física nem demonstra mudança na contagem de pulsos.
Regressão: `python3 -m unittest tests.test_ma17_f8fb_path`; capturas:
`build/ma17-analysis/variants/f8fb_release_*/`.
O contraste aparece no **primeiro ciclo CC3 alinhado depois do degrau**:
em `PC1EA9h`, o candidato `R3:R2` é `00E2h→0265h` na G e
`00DAh→0248h` na S88. A entrada `058Eh` no mesmo tick 3.315.115
recebe esses mesmos valores em `RAM[14h:15h]`. Os intervalos baixos
imediatos do pino CC3 **modelado** foram 892→2.441 ticks na G e
860→2.325 na S88, medidos entre as próximas bordas baixa e alta do
log. Isso confirma uma rota digital até o agendador e a saída CPU
modelada; não confirma a ligação elétrica desse pino ao bico injetor.
O teste de regressão verifica o valor agendado e o aumento local de
largura, além da contagem global de inícios.
Para ligar esse efeito à **curva ROM**, repeti o mesmo cenário fornecendo
`00h` nos dez pares PC/endereço de `MOVC` efetivamente alcançados em
`78E5h..78F8h`: três em `532Fh`, três em `5333h`, dois em `534Bh` e
dois em `5350h`. O valor armazenado em `F8:FBh` permaneceu `00h` e os
69 resultados `B=00h`, o primeiro agendamento `0265h/0248h` e as
larguras modeladas 2.441/2.325 ticks reproduziram a intervenção no
leitor em G/S88. Os hashes das ROMs não mudaram. Alterar só as duas
células iniciais `78E5h/78E6h` falhou em atingir a escrita inicial:
o interpolador usou outros índices naquele momento. A evidência
estabelece a cadeia digital tabela → `F8:FBh` → cálculo → CC3 modelado
sob intervenção; os bytes originais dessa curva são `FFh` nas seis ROMs
e a saída física da ECU continua não identificada. Capturas:
`build/ma17-analysis/variants/f8fb_release_movc_reached00_{g,s88}/`.

Uma auditoria dos `MOVC` em 1.723 artefatos `execution.json` distinguiu
o `DPTR` usado do endereço efetivo. Nenhum registro usou como base o
início de um dos quatro slots ainda provisórios. Porém, o primeiro byte
de três deles foi lido como lookahead da matriz imediatamente anterior:

Reprodução: `python3 tools/audit_ma17_pointer_lookahead.py`. O comando
gera `build/ma17-analysis/variants/pointer_lookahead_audit.json` e a
regressão sintética está em `test_pointer_lookahead_audit_distinguishes_direct_and_crossing_reads`.
O relatório conta somente `MOVC A,@A+DPTR` (`93h`); separa seleção direta
de `DPTR` das leituras cujo endereço efetivo cai no intervalo vizinho.
O corpus contém 1.435 capturas da ROM G e 288 da S88, identificadas
por SHA-256 no relatório; não contém execução completa de A/A+/S37/S36.

| Slot provisório | Byte lido | DPTR da matriz anterior | G | S88 |
| --- | --- | --- | ---: | ---: |
| `7098h→7845h` | `7845h=9Ah` | `7831h` | 22 | 8 |
| `7082h→78A9h` | `78A9h=00h` | `7895h` | 57 | 44 |
| `7086h→78D1h` | `78D1h=00h` | `78BDh` | 7 | 0 |
| `70D2h→7881h` | nenhuma no corpus | nenhuma | 0 | 0 |

Todas as leituras observadas dessas três bordas ocorreram em `PC5350h`
e tocaram somente o primeiro byte do intervalo seguinte. Um teste dos
opcodes originais das seis ROMs fixou `R5=15`, `R0=4`, `R4=80h` e
`R6=0`: o mesmo `MOVC` leu as bordas `7845h`, `78A9h`, `78D1h` e,
em seleção isolada de `70D0h→786Dh`, também `7881h`. Isso demonstra
acesso possível ao primeiro byte de `70D2h` por lookahead, sem
demonstrar seleção direta de seu ponteiro. As contagens somam artefatos
experimentais repetidos, portanto não medem frequência natural na ECU.
Regressão: `Sab80C517.SixRomFinalMatrixRowReadsAdjacentPointerInterval`.

O trecho G `3E51h..3E61h` usa o segmento e a fração de `RAM[70h]`
para interpolar cinco bytes em `794Dh` e escrever `F8:8Dh`. O helper
leria `7952h` como byte adjacente ao índice 4; esse índice não apareceu
na captura analisada. Com P4.6 experimental baixo e duas mudanças de
TPS, o G original leu ambas as estruturas. Fornecer `20h` somente em
`PC=532Fh/785Ch` (original `40h`) mudou a sequência de `F8:00h`
`5A,53,46,A3,46` para `5A,53,36,A3,36`. Fornecer `20h` somente em
`PC=532Fh/794Dh` (original `5Ah`) mudou `F8:8Dh` de
`CD,94,9A,94` para `CD,F7,9A,F7`. As ROMs permaneceram intactas.
Os destinos são campos de XRAM, sem ligação física comprovada.
O código A contém caminhos homólogos em `3EB7h` e `3F0Eh`, ainda sem
execução completa no seu perfil de hardware. Regressão:
`Curve705c7078Tests.test_cell_read_interventions_change_separate_xram_fields`.

### Seleção `797Ah/7982h`, interpolação e XRAM `F8:8Eh`

O código G `3E62h..3E7Eh`, homólogo A em `3F1Fh..3F3Bh`, divide
`RAM[6Ah]`: nibble baixo vira índice `R5` e nibble alto vira fração
`R6`. `RAM[2Fh].0` escolhe o ponteiro big endian `7074h→797Ah` ou
`7076h→7982h`. Após interpolar dois bytes adjacentes, o código grava
`R2` em `MOVX @8Eh` quando `T2I1=0`; com `P2=F8h`, o endereço modelado
é `F8:8Eh`. A função física desse campo e a ligação externa de
P4.6/CM6 ainda não foram verificadas.

Os oito bytes de cada intervalo são idênticos nas seis ROMs:
`03 04 06 0A 14 20 37 64`. Entretanto, o índice 7 consulta também
o byte seguinte. Com base `797Ah`, lê `7981h=64h` e `7982h=03h`;
com base `7982h`, lê `7989h=64h` e `798Ah=40h`. Em execução isolada
dos opcodes originais das seis ROMs, `RAM[6Ah]=82h` produziu `08h` em
`F8:8Eh` nos dois seletores; `87h` produziu `34h` ou `52h`. A diferença
de arredondamento da interpolação negativa faz o primeiro resultado
ser `34h`, não `33h`. O oitavo byte de cada intervalo é comprovado;
seu fim formal ainda é provisório, baseado no próximo alvo do diretório.

Traces G/S88 sem estímulo de P4.6 leram `7982h` como **lookahead** com
`DPTR=797Ah`; logo o endereço isolado não comprova seleção da segunda
curva. Traces com P4.6/CM6 da CPU forçado a baixo leram com
`DPTR=7982h`, comprovando a outra seleção no modelo. Essas capturas
não estabelecem o nível elétrico natural desse pino na ECU. Regressão:
`Sab80C517.Iram6aCurveLookaheadChangesF88eAtLastIndex`.

A execução exaustiva do produtor original `1255h..1260h`, para os 256
valores de `RAM[70h]` nas seis ROMs, retornou `RAM[6Ah]=07h` sempre que
o índice foi 7. Portanto, esse caminho fornece fração zero no ponto em
que o interpolador consulta o nono byte; o caso isolado `87h` ainda não
tem caminho natural demonstrado. Escritas indiretas alternativas em
`RAM[6Ah]` permanecem em aberto. Em duas execuções G intactas a 3.000
RPM com dois degraus de TPS, o trace de `F8:8Eh` registrou a mesma
sequência de mudanças (`55 AA 00 03 05 64 05`) com P4.6 padrão e
forçado a baixo. A segunda execução leu `798Ah` 194 vezes como
lookahead da segunda curva, mas não reproduziu a diferença `34h/52h`
do ensaio isolado. Capturas: `iram6a_default_f88e` e
`iram6a_p46low_f88e` em `build/ma17-analysis/variants/`.

O slot `707Ah` aponta para `798Ah`: oito bytes `40 40 40 53 53 53 53 53`
iguais nas seis ROMs, até o próximo alvo do diretório em `7992h`. No G,
`15CFh..160Eh` consulta esse vetor apenas no ramo `RAM[2Fh].0=0`, após
a guarda `RAM[2Eh].0` e o limite anterior não nulo. O código divide
`RAM[6Ah]` em índice e fração, interpola pelo helper `5329h`, combina o
resultado com o fator lido via `7006h`, satura e publica `R3:R2` em
`RAM[59h:5Ah]` em `1644h/1646h`. A família A contém o homólogo em
`1618h..1655h`. Em traces G intactos a 3.000 RPM, o helper leu a base
`798Ah` 12 vezes com P4.6 padrão e 2 vezes com P4.6 forçado a baixo;
houve também leitura adjacente de `798Ch`. Fornecer `20h` apenas na
leitura `MOVC` de `798Bh` em `PC=532Fh`, mantendo a ROM original,
alterou a publicação inicial de `59h:5Ah` de `05h:00h` para `04h:38h`
e o primeiro intervalo CC3 de `0544h` para `047Ch`. As três primeiras
larguras baixas modeladas de CC3 passaram de `5381/5381/5380` para
`4581/4581/4580` ticks; a quarta permaneceu 1212 e a mediana total,
5217. A evidência é causal no modelo para uma leitura e um estado de
entrada; ainda não identifica fisicamente CC3/P1.3 como o bico. O byte
seguinte em `7992h` pode ser lido pelo interpolador, mas esse acesso no
índice 7 ainda não foi observado. Portanto, o limite de oito bytes é
provisório. Regressão: `Iram6aCurveTraceTests.test_798b_read_changes_early_iram_pair_and_cc3_width`.

### Fatores `79CEh` e `79D8h` na rota de `87h` e CC3

As seis ROMs contêm os mesmos ponteiros big endian `70D8h→79CEh` e
`70DAh→79D8h`, e os respectivos blocos têm os mesmos bytes. Em G/S88,
`153Ah..155Bh` usa o primeiro bloco quando a guarda e o contador em
`1Ah` permitem; um trace a 1.000 RPM leu `79D1h=EEh` e `79D2h=ECh`
uma vez em 1,6 milhão de ticks. Antes da multiplicação em `155Ah`, o
estado era `A=EEh`, `B=1Ah`; `MUL AB` deu `2Ch:18h` e o byte alto
reduziu a RAM superior `87h` para `18h` perto do tick 1.073.000.

O segundo bloco começa em `79D8h` e tem oito bytes até o próximo
ponteiro, `79E0h`. Um teste isolado executou a ROM G original de
`1255h` a `1260h` com todos os 256 valores de entrada em `RAM[70h]`,
PSW no banco 1 e pilha fora dos registradores. A rotina produziu todos
os índices `0..7` e nenhum índice `8`; os bytes de código e dados
relevantes são idênticos em S88. A mesma varredura dos opcodes originais
em A, A+, S37 e S36 também produziu todos os índices `0..7`, sem alcançar
`79E0h`. Isso confirma o limite do caminho `1255h` nas seis imagens;
o ensaio isolado não substitui uma inicialização completa da família A
nem exclui escritores indiretos de `6Ah`. O código G calcula o índice
com `RAM[6Ah]` e lê via `MOVC`
em `1576h` antes de usar `87h` e escrever `59h:5Ah`. Em três cenários
TPS, `6Ah=B1h/53h/07h` levou aos índices `2/3/7` e aos bytes
`FFh/FFh/5Ah`, respectivamente. No último cenário, `ADC0/ADC6=180/247`,
a célula `79DFh=5Ah` foi lida 151 vezes em G e S88. Com `ADC6=247` fixo,
outros estímulos digitais `ADC0=60/100/180` alcançaram naturalmente
`6Ah=15h/06h/07h` e os índices `5/6/7`: `79DDh=DAh`, `79DEh=A6h` e
`79DFh=5Ah`, com 44 leituras por cenário em cada ROM em 500.000 ticks.
Esses pares de ADC não foram validados como posições físicas coerentes
das duas pistas de TPS. O teste
`test_79d8_indices_five_six_seven_are_reached_by_adc_pairs` verifica
os seis traces. O código da família
A usa os mesmos ponteiros e instruções homólogas em `15B0h..15CFh`;
essa rota não foi executada no harness Fiat para A.

Com TPS e ROM fixos, substituí apenas o **resultado** do `MOVC` em
`PC=1576h`, endereço `79DFh`, de `5Ah` por `FFh`. O trace bruto ainda
registra `5Ah`, e os hashes das duas ROMs permanecem originais.
`RAM[48h]` e `87h` não mudaram entre cada par de execuções; `59h:5Ah`
e CC3 mudaram:

| ROM | CC3 original → substituído | P1.3 baixo modelado, ticks |
| --- | ---: | ---: |
| G | 1286→1427 | ~5133→5697 |
| S88 | 1596→1774 | ~6373→7085 |

Esses valores usam a janela de 400.000–800.000 ticks a 1.000 RPM,
`ADC2=100`, `ADC7=63`. O experimento prova influência digital do byte
consultado sobre o agendamento CC3 no modelo, sem identificar a ligação
elétrica de P1.3. O teste
`test_79d8_movc_result_changes_cc3_without_rom_patch` reproduz os pares.
Para repetir a substituição, use `MA17_OVERRIDE_MOVC_AT=1576:79DF:FF`
com `tools/trace_ma17.py --trace-movc`, TPS `MA17_ADC_CH0=180` e
`MA17_ADC_CH6=247`, `MA17_ADC10_CH2=400`, `MA17_ADC_CH7=63`,
`--rpm 1000 --crank-immediate --no-kline-inject --stop-ticks 1600000`.
O valor usa o formato hexadecimal `PC:ENDEREÇO:BYTE`; omita a variável
para obter o controle. A substituição afeta apenas o retorno desse
`MOVC` no emulador, sem editar a EPROM.
Capturas: `build/ma17-analysis/variants/iram87_tps180_247/`,
`iram87_tps180_247_factor_ff/`, `iram87_tps180_247_s88/` e
`iram87_tps180_247_s88_factor_ff/`.

### Segmentador `70DCh→79E0h` e campo XRAM `F8:F2`

As seis ROMs têm o mesmo ponteiro big endian `70DCh→79E0h` e os oito
bytes `63 03 1E 2A 8D 72 7A 81` até o próximo alvo em `79E8h`.
O helper G `52CDh..52ECh` interpreta `63h` como endereço da RAM
inferior, `03h` como contagem e `1E/2A/8D` como incrementos examinados
em ordem reversa. `R3` seleciona `79E5h..79E7h` em `28A9h`; `28AFh`
escreve o valor em XRAM `F8:F2`. A família A tem código homólogo em
`28BBh` com helper `5390h`, ainda sem ensaio completo no seu perfil.

No G original a 3.000 RPM, ADC3=72/73/114/115 deu `RAM[63h]` igual
a `48h/49h/72h/73h`, respectivamente. As leituras passaram de
`79E5h=72h` para `79E6h=7Ah` no limite `49h`, e de `79E6h` para
`79E7h=81h` no limite `73h`; `F8:F2` recebeu os mesmos valores.
Com ADC3=80 e ROM intacta, fornecer apenas `72h` na leitura
`PC=28A9h/79E6h` (valor original `7Ah`) mudou a escrita `28AFh` de
`7Ah` para `72h`. É causalidade digital de uma célula até XRAM, não
identificação de atuador ou escala física de temperatura. O uso
posterior de `F8:F2` e eventual efeito nos pinos continuam abertos.
Regressão: `Segment79e0Tests.test_adc3_segment_boundaries_and_single_read_intervention`.

### Sinal ADC5 e estado interno associado ao byte F8:0Ch

No scanner `Monomotronic-MA1.7-Scanner`, `SensorDecoders.cpp` define
três leituras distintas: comando `00h`, ID `65h` para sonda (`raw × 3,9`
mV); seletor `F8h`, ID `0Ch` para integrador (`(raw−128) × 0,195` %);
e seletor `F8h`, ID `6Ch` para correção de longo prazo
(`int8(raw) × 0,39` %). `SensorCategory.h` apenas agrupa esses campos na
interface. Segundo o autor, o nome "integrador lambda" foi copiado de
outro scanner e **não está confirmado para esta ECU**. Aqui, `F8:0Ch`
designa apenas o byte observado; sua função física permanece hipótese.
As três escalas são convenções do scanner; em particular, o
próprio scanner marca a escala da sonda como não validada em sensor real.
O banco Python `sensor_database.py` usa `raw × 3,87` mV para `65h`,
contra `3,9` no C++; as fórmulas de `F8:0Ch` e `F8:6Ch` concordam.
Para `F8:69h` há divergência maior: C++ usa `raw/256` como razão de
adaptação EVAP, enquanto Python usa `(raw−128) × 0,195` como porcentagem
FTEAD. O endereço é o mesmo, mas a grandeza e o zero são incompatíveis;
nenhuma das duas interpretações está comprovada pelo firmware.
Os IDs `0Ch` e `6Ch` aparecem na tabela de coleta `6E78h` da ROM G
como leituras `MOVX` na página corrente; `F8h` é o seletor do protocolo,
não uma prova independente de que o segundo byte codifica o endereço
alto. Por serem campos de um byte, não há escolha de endian nessa etapa.

O scanner associa `IRAM[65h]` à sonda lambda e `XRAM F8:0Ch` a um
integrador. A agenda ADC da ROM encaminha o canal 5 a `65h`. Nas ROMs G
e S88, com 1.000 RPM, `ADC7=63` e 2,4 milhões de ticks, `ADC5=40/200`
produziu `65h=28h/C8h` em `0744h` com o ADC corrigido. A rotina em `1644h..1687h` lê `65h`,
compara os limites `8Bh`, `6Eh` e `7Ch` e altera flags. No estado basal
`ADC3=80`, `F8:0Ch` foi inicializado em `80h` por `19D2h` e permaneceu
assim; a largura baixa mediana do modelo CC3 foi 5.677 ticks para os
dois valores de ADC5, nas duas ROMs. Isso demonstra a chegada do estímulo
ao firmware, mas não uma correção ativa nesse estado.

A causa de uma conclusão anterior incorreta foi o opcode `86h`
(`MOV direct,@R0`) implementado com a direção invertida no emulador.
A especificação Siemens *SAB 80C517*, seção "Instruction Set", p. 218
([PDF local](../SAB80C517.PDF)), define os opcodes `86h/87h` como
`MOV direct,@Ri`: o byte lido indiretamente é escrito no destino direto.
A instrução em `1558h` lê o fator da RAM superior `87h`; antes da
correção, a instrumentação via um fator sobrescrito artificialmente.
Com o opcode corrigido, o primeiro produto periódico observado em G
com `ADC3=80` é `EEh × 1Bh = 191Ah`, com `OV=1`. O fator `87h` decai
gradualmente, chegando a `01h` perto de 20,5 milhões de ticks; então
`2Eh.2` é limpo. Mesmo em 24 milhões de ticks, `186Dh` não foi alcançado
e `F8:0Ch` continuou `80h`: há outra condição de guarda nessa rota.
O bloco `17C2h..1810h` lê `ROM[7227h]=2Ch` e `ROM[7226h]=44h`.
Com `RAM[63h]=50h` e `RAM[47h]=28h` no caso basal, nenhum dos limites
liga o bit 0 da RAM superior `ABh`; `ORL C,/B.0` mantém o carry ligado
em `17E8h`, bloqueando a entrada em `186Dh` mesmo após `2Eh.2` limpar.
No caso `ADC3=4`, `RAM[63h]=04h`, `ABh.0=1`, e o carry fica limpo.
Um teste executando os opcodes originais confirma as fronteiras: com
`ABh.0` inicialmente zero, o bit liga se `RAM[63h]≤2Ch` ou, no outro
ramo, `RAM[47h]>44h`. A passagem para `186Dh` ainda exige o contador
`3Ch` zerado e as demais flags de `17EDh..1810h` liberadas. A identidade
física de `63h` como temperatura da água vem do scanner.
O carregamento `DPTR=7200h` em `16EBh..1701h` e a guarda
`17C2h..180Fh` são byte a byte idênticos em S88; em A, A+, S37 e S36,
os mesmos blocos aparecem em `1707h..171Dh` e `17DEh..182Bh` (`+1Ch`).
Isso confirma a homologia das instruções e dos dois limiares nas seis
ROMs, sem demonstrar que a rota completa se habilita em todos os perfis.
Uma varredura curta na ROM G, a 1.000 RPM e com os outros ADCs fixos,
cruzou a fronteira sem alterar a ROM:

| ADC3 injetado | `RAM[63h]` | `B.0` em `17EDh` | Carry em `17EDh` |
| ---: | ---: | ---: | ---: |
| 43 | 2Bh | 1 | 0 |
| 44 | 2Ch | 1 | 0 |
| 45 | 2Dh | 0 | 1 |

Os rastros corrigidos estão em
`build/ma17-analysis/variants/lambda_coolant_threshold_adc517a/`.
O scanner C++ e o banco Python usam os mesmos coeficientes Steinhart–Hart
e `Rpu=3004 Ω` para `RAM[63h]`; essa curva atribuiria cerca de **58,5 °C**
ao byte `2Ch`. É uma estimativa do scanner, baseada em sensor e divisor
assumidos, sem aferição da ECU ou prova de que a curva vale para todo
estado elaborado em `63h`. Nos três pontos ensaiados, `63h=ADC3`.

Com o estímulo digital extremo `ADC3=4`, o fator `87h` foi `00h`, não
houve overflow e a rota `186Dh` foi alcançada. Em 2,4 milhões de ticks,
os resultados foram:

| ROM | ADC5 | `F8:0Ch` final | CC3 baixo mediano (ticks) | `IRAM[14:15]` mediano |
| --- | ---: | --- | ---: | ---: |
| G | 40 | CBh | 4.646,5 | 1.170 |
| G | 200 | 68h | 4.333 | 1.086 |
| S88 | 40 | CAh | 4.646,5 | 1.170 |
| S88 | 200 | 6Ch | 4.340 | 1.088 |

Com a emulação ADC corrigida, repeti a ROM G em `ADC0/6=40/95`
(flags TPS `28h=00h`), 1.000 RPM e `ADC7=63`. `ADC3=20` deixou
`IRAM[63h]=14h`; a fórmula **não aferida** do scanner estima ~88,3 °C.
O primeiro `186Dh` ocorreu perto de 1.226.600 ticks para ambos os
valores ADC5. Após 4 milhões de ticks:

| ADC3 | ADC5 | `F8:0Ch` final | `14h:15h` mediana após 1,8 M | Entradas CC3 medidas |
| ---: | ---: | --- | ---: | ---: |
| 20 | 40 | `A8h` | 629 | 75 |
| 20 | 200 | `57h` | 578 | 75 |

Nos dois casos, `28h=00h` em todas as 215 amostras tardias da guarda
`1810h`; o teste
`test_low_tps_without_fault_flags_reaches_lambda_correction` verifica
esses estados e as entradas em `186Dh`. Capturas:
`lambda_adc3_20_tps40_95_{low,high}/`.

O controle mais próximo do limiar, `ADC3=40` (`63h=28h`, ~62,1 °C
pela mesma fórmula provisória), demorou mais: `87h` chegou a zero no
tick 8.240.965 e a primeira passagem por `186Dh` ocorreu perto de
8.394.910. Com `MA17_TRACE_CC3_AFTER_TICK=9000000`, os 101
agendamentos entre 9 e 12 milhões de ticks deram medianas
`14h:15h=654/587` para ADC5=40/200; `F8:0Ch` terminou em `B4h/4Bh`.
Nos rastros de 24 milhões de ticks, as 621/620 amostras tardias de
`1810h` mantiveram `28h=00h`, e `F8:0Ch` saturou em `FFh/00h`.
Esses resultados mostram que ADC5 altera o estado de correção e o
agendamento CC3 sob dois valores de temperatura menos extremos. A
escala física de ADC5, a ligação de CC3 ao terminal 35 e o regime real
de malha fechada continuam sem validação elétrica. Rastros:
`lambda_warm_adc3_40_{low,high}_{24m,late_cc3}/`.

O gráfico `build/ma17-analysis/variants/lambda_adc3_20_tps40_95_response.png`
mostra os bytes brutos `F8:0Ch` e `14h:15h` nos ensaios com `ADC3=20`.
Reproduzir com `MPLCONFIGDIR=/tmp /usr/bin/python3
tools/plot_ma17_lambda_response.py`; o Python do sistema possui Matplotlib.
Os dois sinais divergem gradualmente após a entrada em `186Dh`, mas
esse contraste ADC5 isolado demonstra o **efeito total** da entrada e
não separa o estado associado a `F8:0Ch` de possíveis caminhos paralelos até CC3.

Um ensaio transitório posterior começou em `ADC0/6=40/95`, com
`ADC3=20`, `ADC5=200`, `ADC7=63`, 1.000 RPM e a ROM G intacta. Em
1,8 milhão de ticks, as pistas passaram a `180/247`; em 3,0 milhões,
voltaram a `40/95`. `RAM[60h/66h]` confirmou `28h/5Fh → B4h/F7h →
28h/5Fh`. Nas três janelas seguintes, `28h=00h` em todas as passagens
registradas por `1810h`:

| Janela de ticks | TPS | `1810h` | `186Dh` | `2Fh` em `1810h` | `F8:0Ch` |
| --- | --- | ---: | ---: | --- | --- |
| 1,2–1,8 M | baixo | 58 | 56 | `08h/28h` | desce até `77h` |
| 2,4–3,0 M | alto | 59 | 0 | `ECh` | permanece `80h` |
| 3,6–4,2 M | baixo novamente | 59 | 59 | `A8h` | desce até `71h` |

Em `180Bh..1810h`, quando `2Fh.2=1`, o opcode `ORL C,/2Fh.1`
bloqueia o ramo se `2Fh.1=0`. Isso corresponde ao estado `ECh` na
janela alta. Com o mesmo TPS alto estável desde o reset e `ADC5=200`,
o estado `2Fh=0Ch` também bloqueou `186Dh`; com `ADC5=40`,
`2Fh=2Eh` permitiu a rota. Assim, o bloqueio observado depende do
**estado digital de TPS e ADC5**, e não exige um transitório de TPS.
O ensaio demonstra suspensão e retomada da rota de correção no
emulador, sem validar a estratégia física de malha aberta.
Repetido na variante S88 (SHA-256
`bfa59928ca41695458063835dc1a05a489b9deb5755bb1d7740c22874fdcbe28`),
o mesmo estímulo deu `186Dh=56/0/59` nas três janelas e os mesmos
estados `28h=00h`, `2Fh=ECh` na janela alta; `F8:0Ch` terminou em `65h`
nas duas ROMs. Isso confirma esse comportamento digital compartilhado
em G/S88 sob o perfil do harness Fiat.
Testes: `VariantTraceTests.test_clean_tps_step_suspends_and_restores_lambda_route`
e `VariantTraceTests.test_s88_clean_tps_step_has_same_lambda_gate`.
Capturas: `lambda_tps_clean_step_adc3_20_{40,200}/`,
`lambda_tps_clean_steady_high_adc3_20_{40,200}/` e
`lambda_tps_clean_high_return_{adc3_20_200,s88_adc3_20_200}/`.

Um contraste adicional usou **o mesmo ciclo TPS baixo→alto→baixo**
nas duas pistas, mudando apenas ADC5=40/200. A ROM G original,
`ADC3=20`, `ADC7=63`, 1.000 RPM e cinco milhões de ticks mantiveram
`28h=00h` no guarda `1810h` em ambas as execuções. As entradas em
`186Dh` nas janelas 1,2–1,8 / 2,4–3,0 / 3,6–4,2 milhões foram
`56/59/59` com ADC5=40 e `56/0/59` com ADC5=200. Na janela TPS alta,
`2Fh&06h=06h` e `3Ch=00h` com ADC5=40, contra `04h` e `0Fh` com
ADC5=200. Logo, o mesmo transitório não basta para suprimir a rota:
o estado digital ligado a ADC5 também decide o guarda nesse cenário.
Os bytes finais `F8:0Ch=D6h/65h` são indicadores internos, não uma
medição de mistura. Teste:
`VariantTraceTests.test_clean_tps_cycle_lambda_gate_depends_on_adc5`.
Capturas: `lambda_tps_clean_cycle_adc5_{40,200}/`.

Na ROM S88 original, o mesmo ciclo deu `186Dh=56/60/59` com ADC5=40
e `56/0/59` com ADC5=200. Na janela TPS alta, `28h=00h` nos dois
casos; `2Fh&06h` foi `06h/04h` e `3Ch` foi `00h/0Fh`, como em G.
O byte final `F8:0Ch` também coincidiu entre revisões: `D6h/65h`.
A passagem adicional em `186Dh` com S88/ADC5=40 é um registro duplicado
do mesmo estado nos ticks 2.578.455 e 2.578.461, antes de `1870h`;
há 59 passagens distintas após ignorar essa repetição do probe. A regressão
`test_s88_clean_tps_cycle_keeps_lambda_route_with_adc5_40` cobre a
condição ADC5=40, e o teste S88 anterior cobre ADC5=200.
Capturas: `lambda_tps_clean_cycle_s88_adc5_{40,200}/`.

Para separar movimento da borboleta do estado ADC5, a ROM G foi
executada com TPS **fixo** em `ADC0/6=180/247`; apenas ADC5 alternou
nos ticks 1,8 M e 3,0 M. As amostras de `65h` seguiram cada degrau
(`C8h→28h→C8h` ou `28h→C8h→28h`). Nas janelas 1,2–1,8 /
2,4–3,0 / 3,6–4,2 M, as passagens pós-`MOVC` em `1870h` foram
`0/59/0` para ADC5 `200→40→200` e `56/0/59` na sequência inversa.
Em todas as janelas, `28h=00h`; com ADC5=40, `2Fh&06h=06h`, enquanto
ADC5=200 deu `04h`. Na janela central, o contador `3Ch` ficou em
`00h` após `200→40` e em `0Fh` após `40→200`. O mesmo guarda liga e
desliga sem alteração de TPS: sua passagem por `186Dh` isoladamente
não identifica a estratégia de malha aberta em aceleração forte.
Regressão: `test_high_tps_adc5_cycle_reversibly_gates_lambda_route`.
Capturas: `lambda_adc5_cycle_high_tps_{200_40_200,40_200_40}/`.

O produtor de `2Fh.2` nesse estado foi isolado até outra curva da ROM.
Os ponteiros **big-endian** `7090h→7992h` e `7092h→799Eh` são iguais
nas seis variantes. `7992h..799Dh` é um segmentador de dez intervalos
de `IRAM[47h]` (RPM derivada); `799Eh..79A7h` contém dez valores
`62 81 A0 A0 A0 44 33 2E 2A 28`. Com 1.000 RPM, `47h=28h` e
`532Fh` lê a célula `799Fh=81h`. A rotina `3CB7h` compara o resultado
interpolado `R2` com `IRAM[6Fh]` quando `2Eh.6=1`, preservando o carry
em `PSW.5`; `3D0Ch` copia esse estado para `2Fh.2` no caminho medido.

Na extremidade dessa curva, a leitura adjacente alcança `79A8h`,
primeiro byte de outra estrutura (`709Ah→79A8h`, cabeçalho `47 03`).
Em partidas atuais G/S88 a 6.000 RPM, com ADC6 alterado para 880/1023
no tick 200.000 e `P4.6` modelado baixo, `5333h` leu `79A8h` 359 vezes
por ROM com `DPTR=799Eh` e índice `0Ah`; `527Dh` leu o mesmo endereço
403 vezes usando `DPTR=79A8h` para o cabeçalho. Substituir **somente**
o retorno de `5333h` de `47h` para `00h` manteve `R5=09h`, `R6=00h`,
`R2=28h` e as medianas CC3 de 658/822 ticks em G/S88.
Um teste isolado dos opcodes originais varreu os 256 valores de `47h`
nas seis ROMs: o segmentador `7992h` nunca produziu `R5>9`, e toda
saída com `R5=9` teve `R6=00h`, inclusive `47h=F1h` do cenário acima.
Essa propriedade vale para esse produtor e explica o valor numérico
constante no índice terminal; não elimina outros produtores de `R5/R6`.
No interpolador, o resultado da subtração em `5338h` mudou de `1Fh` para
`D8h`; a rotina assinada em `5246h` tomou o outro ramo. O intervalo
medido de `5338h` até `533Bh` passou de 7 para 13 ticks em ambas as
ROMs. As bordas CC3 individuais mudaram de tick apesar das medianas
iguais. Portanto, fração zero anulou a contribuição **numérica** da
célula seguinte, mas não seu efeito sobre o percurso e o tempo do
firmware no emulador. Isso não identifica função elétrica ou física.
Capturas: `curve_boundary_79a8_probe_{g,s88}_{control,donor}/`;
regressão: `test_zero_fraction_masks_value_but_signed_helper_changes_timing`.

Na ROM G, com TPS estável `180/247`, `ADC3=20`, `ADC5=200` e
`6Fh=A7h`, uma intervenção **somente no retorno do MOVC**
`PC532Fh/799Fh` testou a fronteira sem mudar a EPROM:

| Retorno substituído | `R2` em `3CB7h` | `2Fh.2` | `186Dh` após 1,2 M | `F8:0Ch` em 1,6 M |
| --- | --- | --- | ---: | --- |
| `A6h` | `A6h` | 1 | 0 | `80h` |
| `A7h` | `A7h` | 0 | 37 | `70h` |

Sem intervenção, `R2=81h`, `2Fh.2=1` e não houve entrada tardia em
`186Dh`. O trace `MOVC` ainda registra o byte **original** `81h` nas
duas intervenções. A tentativa de substituir `ROM[721Dh]` em `3D01h`
não teve efeito: nesse cenário `22h.6=0` faz o salto em `3CFCh`
contornar aquela leitura. Logo, `721Dh` não explica a guarda medida.
A curva `799Eh` possui efeito causal no **limiar digital de carga**
sob esse estímulo; a grandeza física de `6Fh` e a estratégia real de
malha aberta seguem sem validação. Teste:
`VariantTraceTests.test_rpm_curve_799f_sets_lambda_gate_at_ram6f_boundary`.
Rastros: `lambda_high_gate_799f_{baseline,override_b0,boundary_A6,boundary_A7}/`
e `lambda_high_gate_721d_override_00/`.

Uma varredura com a ROM G original, TPS `180/247`, `ADC3=20`,
`ADC5=200`, `ADC7=63` e 1,8 milhão de ticks confirmou a dependência
do limiar com a RPM. Entre 1,2 e 1,8 milhão de ticks, `6Fh=A7h` e
`2Eh.6=1` nos seis casos:

| RPM simulada | `47h` | `R2` em `3CB7h` | `186Dh` tardio |
| ---: | --- | --- | ---: |
| 750 | `1Eh` | `72h` | 0 |
| 1.000 | `28h` | `81h` | 0 |
| 1.500 | `3Ch` | `A0h` | 0 |
| 2.000 | `50h` | `A0h` | 0 |
| 3.000 | `78h` | `78h` | 0 |
| 4.000 | `A0h` | `33h` | 0 |

Nos extremos de 750 e 4.000 RPM, mudar somente `ADC5` para `40`
manteve `2Fh.2=1`, ligou `2Fh.1` e produziu 56 entradas tardias em
`186Dh` em cada caso; `F8:0Ch` terminou em `94h/B3h`, contra `80h`
com `ADC5=200`. O teste
`VariantTraceTests.test_rpm_curve_799e_gate_interacts_with_adc5_classifier`
reproduz esses quatro cenários. A curva `799Eh` representa um limiar
digital dependente da RPM; sua forma não corresponde, por si só, a
uma escala física de carga. Rastros: `lambda_gate_rpm_sweep_{rpm}/` e
`lambda_gate_rpm_sweep_{750,4000}_adc5_40/`.

Para repetir a varredura de ADC5=200, a partir da raiz do projeto:

```sh
for rpm in 750 1000 1500 2000 3000 4000; do
  MA17_ADC_CH0=180 MA17_ADC_CH6=247 MA17_ADC_CH3=20 \
  MA17_ADC_CH5=200 MA17_ADC_CH7=63 MA17_TRACE_LAMBDA=1 \
  MA17_TRACE_AIR_716C_GATE=1 python3 tools/trace_ma17.py \
    --no-kline-inject --crank-immediate --rpm "$rpm" \
    --stop-ticks 1800000 --seconds 20 \
    --output-dir "build/ma17-analysis/variants/lambda_gate_rpm_sweep_$rpm"
done
```

Uma varredura da ROM G com `ADC3=4`, `ADC7=63`, 1.000 RPM e a mesma
janela de 2.400.000 ticks localizou fronteiras do classificador de
`IRAM[65h]`. Em todos estes ensaios, o valor estabilizado de `65h` foi
`ADC5+1`; as flags abaixo foram amostradas após 1 milhão de ticks:

| ADC5 | `65h` | `2Ch.3` | `2Fh.1` | `F8:0Ch` final |
| ---: | ---: | ---: | ---: | ---: |
| 108 | 6Dh | 1 | 1 | CBh |
| 109 | 6Eh | 0 | 1 | 80h |
| 133 | 86h | 0 | 1 | 80h |
| 134 | 87h | 1 | 0 | 80h |
| 152 | 99h | 1 | 0 | 80h |
| 153 | 9Ah | 0 | 0 | 6Ah |

O código `1644h..1687h` compara `65h` com `6Eh`, `7Ch` e `8Bh`.
Na inicialização, `0D5Eh..0D73h` copia `ROM[733Fh]=0Ah` para o byte
baixo `E8h` e `ROM[7342h]=0Fh` para `EAh`, lidos nas comparações
superiores; a rotina decrementa `A` quando `2Fh.1` já está ligado.
Isso explica a transição observada entre `86h` e `87h` nesse estado.
O restante do bloco `733Dh..7342h` controla a evolução desses limites:
na inicialização `733Dh=1Eh` vai para o contador `E9h` e `7340h=1Eh`
para `EBh`. Em `16B5h..16CCh`, quando `EBh` chega a zero, a rotina
recarrega `EBh` de `7340h` e subtrai `7341h=01h` de `EAh`, com piso
zero; `16CDh..16EAh` faz o mesmo com `E9h`/`E8h`, usando `733Dh` e
`733Eh=01h`. Um teste dos opcodes originais em `1687h` confirmou os
dois pares: contadores `1` levam `E8h/EAh=0Ah/0Fh` a `09h/0Eh` e
recarregam ambos para `1Eh`; contadores `2` apenas caem para `1`.
São limites e contadores internos da classificação de `65h`. Após a
correção de `ADDATL`, uma execução G com `ADC3=4`, `ADC5=40`, `ADC7=63`,
1.000 RPM e 3,2 milhões de ticks observou `EBh` recarregar `00h→1Eh`
em 3.121.132 ticks e `EAh` cair `0Fh→0Eh` sete ticks depois; `E9h`
recarregou em 3.121.151 ticks e `E8h` caiu `0Ah→09h` em 3.121.158.
O valor final de `RAM[65h]` foi `28h`, e `F8:0Ch` chegou a `D4h`.
Rastro: `build/ma17-analysis/variants/adc517a_rebaseline_lambda/`.
A escala física da sonda e a duração em tempo real de cada decremento
permanecem sem validação elétrica.
O bloco de inicialização `0D59h..0D73h`, os seis bytes `733Dh..7342h`
e a sequência de atualização dos limites são idênticos nas seis ROMs.
A atualização fica em `1687h..16EAh` em G/S88 e em
`16A3h..1706h` em A/A+/S37/S36 (`+1Ch`); o teste de alinhamento
compara os bytes originais em cada posição. A igualdade do código não
prova que a rota seja habilitada com a mesma frequência em todos os
perfis de hardware.
O byte `F8:0Ch` só saiu de `80h` abaixo de `6Eh` ou a partir de `9Ah`
nessa janela; isso não valida tensão física de comutação da sonda.
O teste `test_lambda_adc5_thresholds_and_neutral_intervals` verifica
os seis pares de fronteira. Traces:
`build/ma17-analysis/variants/lambda_adc5_sweep_20261114/`.

O byte `F8:0Ch` é escrito em `19D0h..19D2h` a partir do estado interno
calculado em `R7:R6`/`5Ch:5Dh`. Um rastreio opcional de `MOVX` para esse
endereço, fundamentado na instrução `MOVX A,@Ri` do manual SAB80C517,
p. 224, encontrou **uma única instrução leitora distinta** em 2,4 milhões
de ticks: `55A2h`, na rotina de autoteste da XRAM, que escreve `55h` e
lê de volta para verificar a memória. A primeira tentativa de substituir
essa leitura alterou o autoteste e gerou resultados inválidos; ela foi
descartada. O probe agora preserva obrigatoriamente `55A2h` e só admite
substituição em outra leitura. Com `ADC5=40` e `200`, não houve outra
leitura de `F8:0Ch`; `MA17_OVERRIDE_XRAM_F80C=80` não foi aplicado e
reproduziu exatamente os controles: `F8:0Ch=CBh/68h`, largura CC3
mediana `4646,5/4333` ticks e `IRAM[14:15]=1170/1086`. Logo, nestes
cenários, o **byte armazenado** em `F8:0Ch` não é realimentado ao cálculo
do pulso; o estado interno anterior à escrita ainda pode influenciar
ambos. O teste de regressão confere o autoteste e a ausência de leituras
posteriores. Traces válidos:
`build/ma17-analysis/variants/lambda_f80c_read_intervention/filtered_*/`.
Uma extensão sem intervenção até 12 milhões de ticks manteve o mesmo
conjunto de PCs leitores (`55A2h` somente) para ADC5=40/200, enquanto
`F8:0Ch` alcançou `FBh/00h`. Traces:
`build/ma17-analysis/variants/lambda_f80c_read_intervention/long_*/`.

As instruções em `19B6h..19D2h` convertem o par interno `R7:R6`
(`R7` alto, `R6` baixo) no byte diagnóstico. Para os valores observados,
o resultado entregue à escrita `MOVX` é
`clamp(128 + (signed16(R7:R6) >> 7), 0, 255)`. Em 117 passagens após
1,2 milhão de ticks por cenário, a fórmula coincidiu com `A` em
`19D0h` tanto para ADC5=40 quanto para ADC5=200, incluindo saturação
em `00h`/`FFh`. Por exemplo, `R7:R6=00E5h` produz `81h`, e
`FF1Bh` produz `7Eh`. Isso identifica a codificação numérica do campo;
a conversão do scanner para porcentagem (`0,195` por passo) ainda não
tem escala física validada. `F8:0Ch` é uma projeção do estado interno
nessa rota, não o próprio acumulador de 16 bits.

Em G, estender o estímulo `ADC3=4` a 12 milhões de ticks levou
`F8:0Ch` a `FBh` com `ADC5=40` e a `00h` com `ADC5=200` (este último
por volta de 5,1 milhões de ticks). Os extremos de ADC3 não têm
temperatura física validada. Os dados mostram dependência de ADC5 nessa
rota, mas ainda não isolam quanto da variação de CC3 é causado pelo
estado interno associado a `F8:0Ch`. O nome e a escala do scanner
continuam sem validação em ECU real.

O diretório em `7008h` aponta para dez bytes em `7426h..742Fh`, que o
código G interpola com o estado derivado de `4Eh` e grava em RAM superior
`87h`. A e A+ alteram nove desses dez bytes: `00 03 0A 1A 1D 25 38 4D
5A 60` em G contra `00 13 1A 2A 2D 35 48 5D 6A 70`. O consumidor em
`12BEh` persiste em A com os auxiliares deslocados para `53ECh/56FCh`;
seu guarda homólogo está em `1588h..15B0h`. Um teste executando as ROMs
originais isoladamente em `12BEh` encontrou `87h` maior em `10h` na A
para os mesmos índices de `4Eh=33h` e `C1h`. O efeito sobre a malha
completa de A/A+ ainda depende de um perfil de hardware validado.
O mesmo teste cobre agora as seis ROMs com índices idênticos `20h`,
`33h` e `C1h`. A e A+ coincidem entre si; G e S88 também. S37 e S36,
apesar de usarem a revisão de código A no consumidor, mantêm os bytes
`7426h` de G e reproduzem seus resultados em `87h` nos três índices.
Com `4Eh=20h`, a guarda homóloga mantém `2Eh.2` apenas em A/A+; nas
outras quatro ROMs ela limpa o bit. Nesse estado isolado, portanto, a
diferença acompanha os bytes da calibração através das duas revisões
de código. Isso não demonstra a frequência natural dessa guarda em A.
O diretório `70D8h` aponta para os dez fatores `79CEh..79D7h`, idênticos
nas seis ROMs; o teste dos opcodes de `155Ah..1562h` confirma a dependência
da flag `2Eh.2` do overflow da multiplicação.
Os rastros válidos após a correção do opcode ficam em
`build/ma17-analysis/variants/lambda_opcode86_fixed/`. Os diretórios
`lambda_gate_detail/`, `lambda_gate_s88/`, `lambda_long/`,
`lambda_adc3_scan/` e `lambda_extreme_long/` preservam medições anteriores
somente para auditoria. Os testes reproduzíveis cobrem a guarda
aritmética e a alteração de `F8:0Ch` com o estímulo extremo.

O resumo de `137Bh` mostra o resultado predominante da interpolação:

| ADC0/ADC6 | `R5:R6` G/S88 | `A:B` G | `A:B` S88 |
| --- | --- | --- | --- |
| 120/95 | 30:00 / 32:10 | 37:C0 | 41:C0 |
| 40/95 | 5D:00 / 5F:10 | 5B:40 | 56:40 |
| 120/180 | 8A:00 / 8C:10 | A1:00 | A2:50 |

São valores de registradores, sem conversão física. A diferença em `A:B`
surge antes da cadeia que grava `IRAM[48h]`; no caso `120/180`, o valor
final de `48h` converge para `3Bh`, demonstrando que etapas posteriores
podem ocultar uma diferença da matriz.

O teste `FiatMatrixAndAxisEffectsCanBeSeparatedWithOriginalRoms` executa
o interpolador original `532Fh..5365h` com `R0=0Fh`, `R4=C0h` e os dois
pares `R5/R6` capturados a 1.000 RPM (`30/00` em G, `32/10` em S88).
Usa as duas ROMs **sem alterar bytes**:

| Matriz | Índice/fração | `A:B` |
| --- | --- | --- |
| G | G | `37:C0` |
| S88 | G | `4C:C0` |
| G | S88 | `2C:C0` |
| S88 | S88 | `41:C0` |

Nesse estado, trocar apenas a matriz na entrada da rotina soma `1500h`
ao resultado de 16 bits; trocar apenas o índice/fração subtrai `0B00h`.
O efeito combinado é `+0A00h`, exatamente o contraste capturado em
`137Bh`. Essa separação vale para este conjunto de entradas e para a
aritmética emulada; não atribui unidade física ao valor nem prova qual
alteração domina em outros pontos da matriz.

O teste `FiatMatrixDeltaPersistsAcrossRpmAndTpsLookupStates` repetiu a
avaliação com os registros observados em outros quatro cenários. Em todos,
trocar só a ROM da matriz, preservando índices e frações, somou `1500h`
ao resultado. O efeito da mudança de índice/fração variou:

| Condição | `A:B` G→S88 observado | Efeito da matriz | Efeito índice/fração |
| --- | --- | ---: | ---: |
| 750 RPM, TPS padrão | `49:80→42:C0` | `+1500h` | `−1BC0h` |
| 1.000 RPM, TPS padrão | `37:C0→41:C0` | `+1500h` | `−0B00h` |
| 2.000 RPM, TPS padrão | `20:40→33:40` | `+1500h` | `−0200h` |
| 1.000 RPM, TPS 40/95 | `5B:40→56:40` | `+1500h` | `−1A00h` |
| 1.000 RPM, TPS 120/180 | `A1:00→A2:50` | `+1500h` | `−13B0h` |

Os contrastes são diferenças aritméticas dos registradores de 16 bits no
interpolador. A uniformidade `+1500h` é compatível com os 225 bytes da
matriz S88 elevados em 21 unidades; o resultado final depende também da
seleção feita pelo eixo alterado em `7580h`.

Para medir a contribuição **da matriz no firmware completo**, o probe
`MA17_OVERRIDE_MOVC_7581_DELTA=15` acrescenta `15h` ao byte entregue
em `A` somente nas leituras `MOVC` de `7581h..7661h` pela rotina
`532Fh..5350h`. Os 225 bytes de S88 são exatamente G+`15h` módulo 256.
O trace preserva os valores brutos da ROM G e seu SHA-256; a operação
segue `MOVC A,@A+DPTR` do manual SAB80C517, p. 222. Com 1.000 RPM,
`ADC1=130`, `ADC7=63` e 2.400.000 ticks:

| ADC0/ADC6 | `A:B` dominante G→G+matriz | `48h` final | `14h:15h` mediano | CC3 baixo mediano, ticks |
| --- | --- | --- | ---: | ---: |
| 120/95 | `37:C0→4C:C0` | `40h→40h` | `1422→1422` | `5677→5677` |
| 40/95 | `59:F0→6E:F0` | `21h→28h` | `763→926` | `3041→3693` |
| 120/180 | `A1:00→B6:00` | `3Bh→42h` | `1314→1476` | `5245→5893` |

Nos dois últimos estados, a alteração isolada da matriz acrescentou
163/162 unidades à mediana de `14h:15h` e 652/648 ticks ao pulso CC3
modelado. Esta tabela usa o build atual e a regressão
`test_matrix_7581_read_delta_changes_cc3_at_two_tps_states`; as capturas
antigas sob `matrix_7581_movc_delta/` refletem um estado anterior do
emulador e não servem para reproduzir essas medianas.
No estado TPS padrão, o resultado da interpolação mudou, mas os estados
posteriores medidos permaneceram iguais. O rastreio da ROM G localizou o
desvio: em `1386h`, `RAM[28h].1=1` no estado 120/95 leva a `145Eh`;
`MOVC` em `1461h` lê `ROM[7298h]=AFh`, e o caminho em `147Eh` substitui
`R3:R2` por `AF00h` antes de `14C2h`, tanto com a matriz original quanto
com `+15h`. Em 40/95, `RAM[28h].1=0` pula para `1487h` e preserva
`R3:R2=59F0h/6EF0h` até `14C2h` (matriz original/`+15h`). Portanto, o mascaramento observado
vem da seleção desse segundo valor da ROM; o significado físico de
`RAM[28h].1` e de `7298h` permanece aberto. Os rastros
estão em `build/ma17-analysis/variants/matrix_7581_path/`.
O rastreio posterior localizou o produtor dessa flag **no estado testado**.
Em `0FECh`, `MOVX A,@R0` lê XRAM `F889h` para `B`; em `1049h/104Bh`,
`R2=RAM[60h]` e `R4=RAM[66h]`. Com `R4=5Fh`, o caminho em
`10F3h..1104h` compara `R4−5` com `R2`: `R2=78h` produz carry e
`B.4=1`, enquanto `R2=28h` produz `B.4=0`. `1132h..113Ch` agrega
bits de `B` em `RAM[28h].1`; `115Eh` persiste `B` em `F889h`.
O trace registrou `F889h=00h→10h` em `115Eh` apenas para 120/95.
Esses são bytes processados das duas entradas TPS; a correspondência
elétrica entre canais e pistas continua hipotética.
Em `145Eh..1486h`, o código usa `R5+94h` como índice em `DPTR=7200h`.
O bloco `7294h..7299h` contém `BC 26 3E 68 AF E9` em G/S88 e
`38 26 3E 68 AF E9` na família A. O consumidor de 41 bytes é idêntico
nas seis ROMs, em `145Eh` ou `14ACh` (família A). Com `R5=4`, o byte
`7298h=AFh` é comparado com `R3`; se `AFh≥R3`, `1480h..1484h`
substitui `R3:R2` por `AF00h`. O byte é um **limiar de substituição
condicional** antes das correções seguintes. Na igualdade, a substituição
também zera `R2` mesmo se ele continha fração não nula; portanto não é
um piso numérico estrito para o par `R3:R2`. Outros índices e estados
de guarda não foram isolados.

| Valor entregue por `1461h` | `R3:R2` em `14C2h` | `RAM[48h]` final | Mediana `RAM[14h:15h]` |
| --- | --- | --- | ---: |
| `00h` | `37C0h` | `14h` | 499 |
| `50h` | `5000h` | `1Dh` | 687 |
| `AFh` original | `AF00h` | `40h` | 1422 |
| `C0h` | `C000h` | `46h` | 1554 |

Os quatro ensaios mantiveram G intacta, 1.000 RPM, ADC0/6=120/95 e
ADC7=63. O `MOVC` bruto continuou a registrar `AFh`; a substituição
ocorreu somente no valor entregue à CPU. Traces:
`build/ma17-analysis/variants/matrix_floor_7298_{baseline,00,50,c0}/`.
Um teste isolado executou os opcodes originais nas seis ROMs com
`R5=0` e o resultado interpolado preparado abaixo do limiar: G/S88
substituem `R3:R2` por `BC00h`, enquanto A/A+/S37/S36 usam `3800h`.
Com `R5=4`, todas usam `AF00h`. Repetir o teste com `R3` igual ao
limiar e `R2=C0h` também terminou com `R2=00h` nas seis ROMs. Isso
demonstra o efeito **potencial**
da única célula divergente, mas não mostra que `R5=0` seja alcançado
naturalmente nesse consumidor nem estabelece uma diferença funcional
em condições reais de operação.
Quatro ensaios estáveis G/S88 (TPS ADC0/6=120/95 e 180/247) e dois
degraus G (40/95→120/95 e retorno), todos com 1.000 RPM, ADC7=63 e
2,4 milhões de ticks, não leram `7294h`: quando `145Eh` foi alcançado,
`R5=4` e a leitura foi de `7298h`. Nos degraus, `RAM[27h].7` estava
limpo em todas as passagens registradas por `145Eh`; o código em
`141Ah` só alcança o caminho alternativo `1427h` com esse bit ligado.
Isso limita a observação aos estados ensaiados e não prova que o índice
zero seja impossível. Capturas: `matrix_idx_{g,s88}_*` e
`matrix_idx_step_*` em `build/ma17-analysis/variants/`.
O assembly modular G explicita uma rota **condicional** para esse índice:
`1396h` carrega `R4` de XRAM `A6h` e `R5` de `A5h`; em `1412h`, com
`T2I1=0`, `2Ch.5=0` e `27h.7=1`, o ramo `1427h` preserva `R5=0` quando
`R4=5`, limpa `R4` e lê `ROM[7294h]` em `1461h`. Com `R4=4` e as demais
condições iguais, o ramo incrementa `R4` e troca `R5=0` por `4`, lendo
`7298h`. Os 80 bytes de instruções em G `1412h..1461h` são idênticos
aos de S88 no mesmo endereço e aos da família A em `1460h..14AFh`
(`+4Eh`). O teste `MatrixStateCanPreserveThresholdIndexZeroInSixRoms`
executa os opcodes originais nos dois estados preparados: o índice zero
lê `BCh` em G/S88 e `38h` em A/A+/S37/S36; o índice 4 lê `AFh` nas seis.
Isso demonstra o mesmo caminho **possível** em ambas as famílias, mas
ainda não que `A5h=0` e `A6h=5` coexistam naturalmente com as três
guardas durante o funcionamento completo. A única diferença entre os
124 bytes de G `1396h..1411h` e o trecho A deslocado é o byte baixo de
um `LJMP` cujo destino também se deslocou em `+4Eh`; o perfil de hardware
da revisão A ainda precisa de validação para um ensaio dinâmico completo.
Em uma janela mais longa, G e S88 com ADC3=4, ADC5 10-bit inicial 160
e degraus `2400000:800,4800000:160,7200000:800,9600000:160`, TPS
120/95 e 1.000 RPM alcançaram naturalmente **todos os índices 1 a 5**
em `1461h` durante 12 milhões de ticks. O log de transições
`[MATRIX-INDEX]` mostra os valores de `R5`; o resumo de `MOVC` confirma
leituras de `7295h..7299h`. O ensaio de 22 milhões de ticks com oito
degraus reproduziu esses cinco índices nas duas ROMs, sem leitura de
`7294h`; G com ADC5=40 constante também chegou a 1..5 em 12 milhões
de ticks. Portanto, o degrau não é condição necessária para esses
índices. O índice zero continua sem alcance demonstrado. Capturas:
`matrix_idx_adc5_cycle_{g,s88}/`, `matrix_idx_adc5_cycle8_{g,s88}/`
e `matrix_idx_adc5_constant40_g/` sob `build/ma17-analysis/variants/`.
O teste optativo `MA17_RUN_SLOW=1` reproduz a janela de 12 milhões.
Repeti essa janela em G e S88 com o novo evento opcional `[MATRIX-PRE]`
em `1412h`, que registra mudanças de `R4`, `R5`, `RAM[27h]`, `RAM[2Ch]`
e `T2CON` antes das guardas. O primeiro estado registrado foi
`R4=0, R5=0, 27h=04h, 2Ch=28h, T2CON=85h` nas duas ROMs: `2Ch.5=1`
desvia para o índice 4. Mais tarde `27h.7=1` e `2Ch.5=0` ocorreram,
mas `R5` já era 1..5 e `R4` chegou no máximo a 2 nos estados distintos
registrados. Nenhum registro reuniu `R4=5`, `R5=0`, `27h.7=1`,
`2Ch.5=0` e `T2I1=0`; `MOVC` só leu `7295h..7299h`. O logger registra
transições de estado, não a frequência de visitas. Capturas com hash e
relatório de execução: `matrix_pre_adc5_cycle_{g,s88}/` no mesmo
diretório; o teste lento agora verifica os campos e a ausência dessa
combinação nesses dois cenários. A possibilidade em outros estados
operacionais permanece aberta.
O trace opcional de escritas em XRAM distinguiu `F8:A5h` da RAM superior
indireta `@A5h`. Nos mesmos 12 milhões de ticks, as mudanças de valor
em `F8:A5h` ocorreram em `55A1h` (`00→55h→AAh` no autoteste), `0A51h`
(`AAh→00h` na limpeza) e `14B9h` (`00h→04h` na primeira passagem pela
matriz e depois passos entre 1..5). G e S88 repetiram os três PCs no
teste lento. O código em `1396h` lê precisamente esse endereço via
`MOVX`; `14B9h` regrava `R5` nele. Esse conjunto descreve somente
escritas que **alteraram** o byte no cenário testado; uma escrita do
mesmo valor não aparece no log, e acessos por ponteiros em outros
estados ainda precisam ser examinados. Captura detalhada G:
`matrix_state_writes_adc5_cycle_g/`.
Exemplos reproduzíveis para o estado estável e o degrau ascendente:

```sh
MA17_ADC_CH0=120 MA17_ADC_CH6=95 MA17_ADC_CH7=63 \
MA17_TRACE_MATRIX_PATH=1 python3 tools/trace_ma17.py \
  --no-kline-inject --crank-immediate --rpm 1000 --stop-ticks 2400000 \
  --seconds 25 --trace-movc --output-dir build/ma17-analysis/variants/matrix_idx_g_120_95
MA17_ADC10_CH0=160 MA17_ADC10_STEP_CH0=800000:480 MA17_ADC_CH6=95 \
MA17_ADC_CH7=63 MA17_TRACE_MATRIX_PATH=1 python3 tools/trace_ma17.py \
  --no-kline-inject --crank-immediate --rpm 1000 --stop-ticks 2400000 \
  --seconds 25 --trace-movc --output-dir build/ma17-analysis/variants/matrix_idx_step_40_to_120
```

Para S88, acrescente `--firmware 'firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin'`.
Uma grade adicional de 16 estados G variou TPS ADC0/6=120/95 ou
180/247, ADC2=20/220, ADC3=4/220 e 750/3000 RPM por 600 mil ticks.
Em cada estado, `199Eh` foi alcançado 54 vezes com `PSW.1=0`, sem
passagem por `19A6h`. Os estados não variaram ADC5. Com ADC3=4,
ADC5=40 ou 200, TPS 120/95, ADC7=63 e 1.000 RPM por 2,4 milhões de
ticks, G e S88 alcançaram **naturalmente** `19A6h` (`R7=40h`) ou
`19ACh` (`R7=A6h`) uma vez, respectivamente. Os opcodes idênticos
em `199Eh..19B5h` (família A em `19BAh..19D1h`) usam `PSW.1` e o sinal
de `R7` para ligar `RAM[27h].7` ou `.6`; o teste isolado confirmou
os três caminhos nas seis ROMs. Depois, `145Eh` leu `7299h=E9h`
(`R5=5`, 42 leituras G/S88) ou `7297h=68h` (`R5=3`, 13 G/11 S88).

| ROM | ADC5 | Limiar consultado | `RAM[48h]` final original→`00h` | Mediana de `RAM[14h:15h]` após a transição, original→`00h` |
| --- | ---: | --- | --- | ---: |
| G | 40 | `7299h=E9h` | `56h→14h` | `1566,5→424` |
| S88 | 40 | `7299h=E9h` | `56h→18h` | `1566,5→489,5` |
| G | 200 | `7297h=68h` | `26h→14h` | `669→389,5` |
| S88 | 200 | `7297h=68h` | `26h→18h` | `673,5→451` |

Na mesma janela após a transição, as medianas de largura baixa do
modelo CC3/P1.3 mudaram de 6.225→1.685 ticks (G, ADC5=40),
6.224→1.946 (S88, 40), 2.665→1.547 (G, 200) e 2.682→1.792
(S88, 200). O teste automatizado verifica também essa redução.
O contrafactual forneceu `00h` somente ao `MOVC` em `1461h` para a
célula indicada, preservando o hash da ROM. As medianas usam eventos
`[CC3-ENTRY]` após 2,0 milhões de ticks (ADC5=40) ou 2,3 milhões
(ADC5=200), quando o novo índice já havia sido selecionado. Elas
demonstram influência no agendamento CC3 emulado; não identificam o
atuador físico. Os valores ADC5=40/200 são estímulos digitais; a escala
elétrica da sonda sugerida pelo scanner permanece sem aferição.
Capturas: `matrix_state_lambda_*` e `matrix_threshold_idx{3,5}_*`
em `build/ma17-analysis/variants/`.
A S88 completa com TPS 40/95
produziu `14h:15h=727` e CC3=2897 ticks no build atual: seu efeito líquido difere do
contrafactual por mudanças de índices e outras calibrações. O teste
`test_matrix_7581_read_delta_changes_cc3_at_two_tps_states` verifica
os dois estados ativos, inclusive bytes brutos e hash da ROM. A ligação
física de CC3 ao bico ainda não está confirmada. Traces:
`build/ma17-analysis/variants/matrix_7581_movc_delta/`.

Uma segunda intervenção entregou os 225 bytes **originais** da matriz
S88 ao `MOVC` da ROM G, com o ponteiro `7048h→7581h` e os hashes
verificados. A diferença S88−G é `15h` módulo 256 em todas as células.
No build atual, com TPS 40/95, os relatórios da doação S88 e da
intervenção aritmética `+15h` coincidiram em CC3, RAM de controle,
estados de lookup, saídas e cobertura de PCs: `14h:15h=926`, largura
baixa modelada CC3=3693 ticks, `48h=28h` e `A:B=6E:F0h` no lookup
dominante. O controle G deu `763`, `3041`, `21h` e `59:F0h`.
Isso confirma o efeito dos bytes reais da matriz S88 nesse estado
emulado, sem atribuir unidade física ao pulso. A regressão
`test_s88_matrix_donor_matches_exact_cell_delta_in_g` compara os
relatórios de ambas as intervenções. Capturas:
`matrix_7581_current_{baseline,delta15}_g_tps40_95/` e
`matrix_7581_donor_s88_g_tps40_95/`.

Com a mesma doação S88 e `ADC0/ADC6=120/95`, o lookup dominante mudou
para `4C:C0h`, mas `145Eh` consultou `ROM[7298h]` e o agendamento
permaneceu em `1422` (CC3 modelado: 5677 ticks). Em `120/180`, sem
essa consulta, o lookup dominante foi `B6:00h`, `48h=42h` e o
agendamento chegou a `1476` (5893 ticks). Os dois resultados coincidem
com a intervenção `+15h` do build atual. A regressão
`test_s88_matrix_donor_is_masked_by_tps_guard` cobre ambos; capturas
`matrix_7581_donor_s88_g_tps{120_95,120_180}/`.

Com ADC1=40, ambas as ROMs produziram `IRAM[7Dh]=73h` e consultaram os
mesmos offsets e valores da matriz `7ED9h..7F14h`, mas leram `05h` versus
`0Dh` em `7B45h`. O teste
`Sab80C517.FiatBatterySegmentVariantsChangeIram31WithSameInputs`
executa diretamente a rotina original em `3291h` nas duas ROMs, com
`IRAM[47h]=28h`, `IRAM[7Dh]=73h` e índice de matriz zero. Obteve
`IRAM[31h]=59h` em `G` e `50h` em `S88`. Os oito bytes do cabeçalho/segmentos
em `7B3Eh..7B45h` diferem só no último byte, e os 60 bytes da matriz
selecionada são idênticos. **Confirmado em emulação:** a alteração de
`7B45h` muda a saída da interpolação nessa condição.

O caminho estático `3291h → 32B8h` escreve `31h`; o serviço em `047Ah`
lê `31h` e `69h`, calcula flags e a recarga `34h:35h`; `0286h` carrega o
Timer 1, cujo vetor alterna P5.0/P5.1 em `0090h`. O contraste de P5 em
ADC1=40 é reproduzido no experimento fatorial acima: −1048 ticks por
`31h=59h→50h` e +60 por `69h=9Ah→89h`. O ensaio direto de `MOVC`
acima mostra que os bytes `7B45h` e `7580h` bastam para produzir os
dois estados nesse cenário; outras calibrações `S88` também mudaram,
mas não são necessárias para reproduzir **esta** largura mediana.

Um segundo teste executa `043Bh..0521h` da ROM G original em estado
isolado, mantendo `69h=A8h`, `36h:37h=011Dh` e todos os demais bytes
iguais. Com `31h=59h` (saída G do ensaio anterior), `22h.7=0` e
`34h:35h=69FEh`; com `31h=50h` (saída S88), `22h.7=1` e
`34h:35h=2FFEh`. Assim, **`31h` pode alterar a recarga calculada do
Timer 1** por uma condição explícita em `048Eh..049Ch`. O estado
`69h=A8h` foi escolhido para cruzar essa condição; esse teste isolado
não mede a largura elétrica de P5 nem demonstra que tal estado ocorreu
nos ensaios completos de G/S88. Na grade corrigida de 2,4 milhões de
ticks com `ADC1=40`, os estados finais foram `31h:69h=59h:9Ah` em G
e `50h:89h` em S88; em ambos, `69h>>1` fica abaixo de `31h`.
Logo, essa fronteira específica não explica por si a diferença de P5
observada no fim daqueles ensaios. Os contrafactuais acima isolam 60 ticks
atribuíveis à seleção da tabela de RPM e ao valor de `69h` consumido.
O teste `Sab80C517.FirmwareRam69ChangesTimer1ReloadCalculation` fixa
`31h=59h` e `36h:37h=011Dh` e executa `043Bh..0521h` na ROM G:
trocar somente `69h=9Ah` por `89h`, os valores finais observados em
G/S88, muda a recarga calculada `34h:35h`. Com os demais bytes de RAM
zerados, a recarga intermediária `32h:33h` não mudou nesse contraste.
Esses ensaios comprovam a dependência local; a intervenção em `043Bh`
acima mede a contribuição à largura de P5 no estado completo emulado.

## Confronto com o scanner e diagnóstico

`diagnostic_tables.json` preserva as 27 triplas de falha em
`6E27h..6E77h` e as duas tabelas de dez pares em `6E78h..6E9Fh`.
Esses 121 bytes são idênticos nas seis imagens. Nas triplas, o código é
`low, high, status`; um par `02 06` representa `0602h`, coerente com a
entrada “Erro TPS” em `ECUMonomotronic.cpp`. Nas tabelas de coleta, a ROM
guarda `seletor, endereço`: `00 63` lê IRAM `63h`, enquanto `F8 0C`
seleciona `MOVX` no endereço baixo `0Ch`. A página XRAM efetiva vem do
estado de P2/XPAGE, não do byte `F8` da tabela. O
`KlineCollectionTables.h` do scanner apresenta os mesmos dez slots na
ordem de campos `endereço, seletor`; a inversão de apresentação não altera
a ordem real dos bytes na EPROM.
O teste isolado da ROM G executa o consumidor `4EAFh..4EC6h`; outro
teste executa o consumidor homólogo `4F72h..4F89h` nas ROMs originais
A e S37. Esses 24 bytes de instruções são idênticos nas seis ROMs,
deslocados de `+C3h` nas quatro imagens da família A. Para as duas
tabelas, com dez valores distintos preparados em
IRAM e XRAM `F8xx`, os vinte slots copiados coincidem com a ordem do
scanner. Isso confirma a semântica digital dos seletores nessas três
revisões, sem demonstrar uma sessão K-Line completa em A/S37 ou a
identidade física de cada campo nomeado pelo scanner.
No mesmo estado emulado A/S37, o teste de faixa ADC3 deixa `63h` em
`11h/04h/E7h/11h` para amostras brutas `03h/04h/E7h/E8h`; em seguida,
o primeiro slot `00 63` de `6E78h` copia exatamente esses quatro bytes
para XRAM `F8BBh`. Isso verifica a cadeia digital **ADC3 processado →
RAM[63h] → campo 0 da coleta**, incluindo as duas saturações. O ensaio
parte do resultado ADC em IRAM superior `A8h`; não executa uma sessão
serial K-Line nem determina graus Celsius.
Para ADC2, o teste executa o agendador `06D0h`, injeta o resultado já
convertido em `0716h` e observa `62h=64h`; depois, o quarto slot
`00 62` de `6E7Eh` copia `64h` para `F8BBh` no mesmo estado A/S37.
Isso liga o **canal digital ADC2** ao campo que o scanner chama de IAT,
com a mesma limitação sobre temperatura física e sessão serial completa.

### Estado de falha associado ao atuador de lenta

O scanner atribui `0402h` ao interruptor do atuador e `1A01h` ao
motor; essas descrições vêm da lista externa citada em
`ECUMonomotronic.cpp`, não de uma identificação física feita pelo
scanner. Elas permanecem hipóteses. As quatro triplas
`6E2Ah..6E35h` são byte a byte iguais nas seis ROMs. Na varredura
base da ROM G, elas correspondem aos bits 0..3 de `XRAM[F84Eh]`;
`407Dh` mascara `IRAM[27h]` por `F884h` e `41E5h` publica o resultado.
Para a primeira tripla `02 04 1D`, o trecho G/S88 `29CBh..29D6h`
e o homólogo A/A+/S37/S36 em `29E7h..29F2h` exigem
`RAM[70h]>4Ah` e `XRAM[F83Ch]=00h` antes de `SETB 27h.0`.
Um teste dos opcodes originais nas seis ROMs distinguiu as bordas:
`70h=4Ah` desvia, `70h=4Bh` com `F83Ch=01h` desvia, e
`70h=4Bh` com `F83Ch=00h` arma o bit. Isso isola a condição
digital final, sem identificar o circuito que produz `RAM[70h]`.
Nos boots G com `P4.6` baixo e TPS 40/95 ou 120/180,
`29D0h` foi executado, mas `29D2h` não; nessa janela a comparação
de `RAM[70h]` ainda bloqueou essa origem do erro `0402h`.
O relatório de RAM mostra que `11D1h` estabilizou `70h` em `1Bh`
e `37h`, respectivamente, ambos abaixo de `4Bh`. Esses valores
pertencem ao TPS derivado neste harness, sem escala angular validada.
Com ADC0/6=40/220, ambos os boots G calcularam `6Fh=1Bh` em
`11B6h` e `70h=53h` em `11C0h`. No controle P4.6 alto,
`29F5h` desviou e `F84Eh=04h`; com leitura experimental baixa,
`29D5h` armou `27h.0` no tick 1.187.188 e `41E5h` publicou
`F84Eh=01h` no tick 1.384.046. O contraste confirma a rota
digital até o latch diagnóstico no perfil emulado, sem comprovar
a fiação Fiat. Em uma sessão PTY completa com as mesmas entradas,
`4329h` e `4DFBh` foram alcançados, e o cliente recebeu o frame
`FCh` com `02 04 1D` (`0402h` em little endian). O comando
`MA17_P4_6_FORCE_LOW=1 MA17_ADC_CH0=40 MA17_ADC_CH6=220
MA17_ADC_CH3=40 MA17_ADC_CH5=40 MA17_ADC_CH7=63
MA17_CRANK_IMMEDIATE=1 MA17_EXPECT_FAULT_TRIPLET=02041D
./run_full_test.sh` passou. O status `1Dh` foi preservado literalmente;
a semântica física do código e do pino segue sem validação elétrica. Capturas
`idle_fault_bit0_tps_40_220*/`; teste
`test_tps_derived_bit_zero_fault_needs_experimental_low_p46`.
O trecho `11A8h..11D4h` é idêntico nas seis ROMs. Uma execução
isolada dos opcodes em cada uma confirmou a fórmula saturada do ramo
alternativo, incluindo o piso e o teto de `6Fh/70h`; o teste
`AlternativeRam70FormulaIsIdenticalInSixOriginalRoms` cobre esses
casos. O acesso natural a esse ramo nas revisões A/A+ permanece
dependente de validar o perfil de hardware correspondente.
Com 1.000 RPM, ADC3/5/7=40/40/63 e TPS 40/95, `2B38h` leu
`F839h=2Eh`; `2B42h` ligou `27h.1`, `2B49h` ligou `27h.3` e
`41E5h` publicou `F84Eh=0Eh`. TPS 120/180 não alcançou `2B38h`
e publicou apenas `F84Eh=04h` na janela de 2,4 milhões de ticks.
`F839h` é um estado compactado em nibbles atualizado por `550Dh..556Fh`,
não uma amostra física identificada do interruptor.
Os opcodes consumidores são homólogos: G/S88 usam `2A7Dh`, `2B38h`,
`2B42h/2B49h`, `407Dh` e `41E5h`; A/A+/S37/S36 usam
`2A99h`, `2B54h`, `2B5Eh/2B65h`, `413Ah` e `42A2h`.
Um teste isolado com as seis ROMs originais executou os ramos de
`MOVX F839h` para `0Eh/2Eh/6Eh/AEh` e confirmou os bits 1/3 de
`IRAM[27h]` como `00h/0Ah/00h/02h`, respectivamente. Isso estabelece
a equivalência desse trecho de código, sem pressupor que as revisões
tenham a mesma ligação elétrica ou alcancem o ramo nas mesmas condições.

O `MOVC 2A7Dh` lê a constante `7321h=14h` antes de comparar com `R2`.
Fornecer `FFh` somente nesse retorno impede a passagem por `2B38h`
e mantém `F84Eh=04h` no cenário 40/95. Em outro contrafactual,
substituir somente o byte lido de `F839h` em `2B38h` por `0Eh` ou
`6Eh` mantém `F84Eh=04h`; `AEh` produz `F84Eh=06h`, pois o bit 7
inibe a atribuição de `27h.3`. Os bytes originais da ROM, seus hashes
e as leituras `MOVC` brutas permanecem inalterados. Essa cadeia
comprova a lógica digital do diagnóstico neste perfil emulado; não
identifica os pinos da ponte H nem demonstra que os erros foram
transmitidos em K-Line. Dados em `idle_fault_*` sob
`build/ma17-analysis/variants/`; teste
`test_idle_fault_xram_read_bits_select_two_error_flags`.

A inicialização lê `F847h` em `0CB7h` e copia seus bits 0/1 para
`27h.1/27h.3` em `0CBAh/0CBEh`. No ramo G observado, `0C85h` já
gravou `F847h=80h` antes dessa leitura; isso não demonstra persistência
entre partidas. O bloco `2D21h..2D56h` copia esses
bits de volta para `F847h`; nas ROMs A/A+/S37/S36 ele corresponde a
`2D3Dh..2D72h`. A sequência de cópia em `0CB5h` é idêntica
nas seis ROMs. No trace G, `F847h` começou em `80h` no arranque;
com P4.6 alto e TPS 40/95, passou a `C7h` após a falha, e com P4.6
baixo chegou a `C6h` após o contador zerar. O ramo de decremento em
`2C0Ch` corresponde a `2C28h` nas ROMs A/A+/S37/S36, e o valor
inicial `F83Bh=32h` em `0CABh..0CAFh` também é idêntico nas seis.
`test_idle_fault_state_and_countdown_have_homologous_sites` verifica
essas instruções originais.

Uma captura G adicional (`idle_position_p46low_6m/`) manteve
`F83Dh=07h` após `0C8Dh` durante seis milhões de ticks, embora o
estímulo P4.6 baixo ativasse o ramo temporizado de `27h.3`. Assim,
esse estímulo, isoladamente, não demonstrou atualização do campo que
o scanner chama de posição do atuador.

O trace anterior registrava apenas mudanças de valor. Com
`MA17_TRACE_IDLE_POSITION_ALL=1`, `2494h` apareceu como escritor
recorrente de `F83Dh`: em oito combinações de TPS, ADC2 e ADC3,
houve 117..230 escritas `07h→07h` em 2,4 milhões de ticks. Variar
RPM entre 750 e 4.000 produziu 107..114 escritas, também sem mudança.
`2378h` lê o byte em `R4`, e `23CEh..2490h` contém os ramos que podem
alterá-lo antes de `2494h`. Forçar experimentalmente P4.7 baixo em
dois estados de TPS não mudou o resultado; o pino também pode operar
como CM7. `test_idle_position_equal_writes_are_visible_with_p47_stimulus`
protege a distinção entre ausência de escrita e escrita de valor igual.

Os opcodes originais G/S88 em `23CEh..2494h` e seus homólogos
A/A+/S37/S36 a partir de `23EAh` foram executados isoladamente nas
seis imagens. Com `R4=07h` e `F840h..F845h=66h`, selecionar um dos
ramos por carry gera `F83Dh=06h`, o outro `08h`. `ROM[7301h]=33h`
é o teto do incremento de `R4`; `ROM[7305h]=65h` e
`ROM[7306h]=9Ch` limitam os ajustes opostos de `F840h..F845h`.
Todos os três bytes são iguais nas seis ROMs. O teste
`Sab80C517.IdlePositionR4StepUsesOriginalBoundsInSixRoms` cobre
também `R4=00h/33h` e `F840h=65h/9Ch`. O estado isolado não comprova
que esses ramos foram alcançados em funcionamento normal nem que o
campo corresponda a graus reais do atuador.

No boot G com TPS 40/95 e ADC3=4, `IRAM63h` estabilizou em `04h`,
abaixo do byte `ROM[7358h]=18h`. Mesmo assim, o `JC` em `23AFh`
permaneceu ativo nas 117 observações do trace: `20h.3=1`,
`24h.4=0` e `2Dh.4=0` são três guardas suficientes para impedir
`23CEh`. Com ADC3=80, `63h=50h` acrescenta a guarda do próprio
limite térmico. Capturas `idle_position_gate_*/`; teste
`test_idle_position_gate_has_multiple_active_guards_at_adc3_four`.

Um estímulo temporal `MA17_P4_6_LOW_FROM_TICK=12200000`, com ADC3=4,
TPS 120/180 e 1.000 RPM, abriu a guarda em `23AFh` no tick
12.287.229: `20h.3` já havia sido limpo em `231Ch`, e o carry era
zero. A comparação interna ainda encontrou `R4=R5=07h`. Alterar
apenas `R4` em `23B1h` para `05h` ou `09h` produziu, pelas instruções
originais, `F83Dh=06h` ou `08h` em `2494h`; o controle sem alteração
continuou em `07h`. São contrafactuais digitais, não evidência de
movimento físico. Capturas `idle_position_r4_{05,09}_12_2m/`;
`MA17_RUN_SLOW=1` habilita o teste de regressão de 12,3 milhões de
ticks para ambos os sentidos.

O estímulo **experimental** `P4.6=0`, com a trava de saída preservada,
alterou o percurso em G. Com os mesmos ADC3/5/7 e TPS 40/95 ou
120/180, `F839h` permaneceu em `0Fh` após a inicialização e
`2B38h` não ocorreu em 2,4 milhões de ticks. `2C0Ch` ligou
`27h.3` transitoriamente enquanto `F83Bh` era decrementado de `32h`
até zero. Após `01h→00h` no tick 664.994, a passagem seguinte por
`2C0Ch` manteve `27h.3=1`; `2D56h` salvou esse bit em `F847h.1`
e `41E5h` publicou `F84Eh=08h` perto de 0,873 milhão de ticks nos
dois perfis. Com `P4.6` alto, os resultados
foram `0Eh` e `04h`, respectivamente. P4.6 afeta outras rotas e pode
operar como CM6 no C517A; esse contraste demonstra dependência
digital, sem identificar a ligação elétrica do interruptor. Capturas
em `idle_fault_p46low_tps_*/` e `idle_fault_restore_p46{high,low}/`.

O scanner C++ identifica IRAM `47h` como RPM e IRAM `61h` como amostra de
bateria; a ROM confirma que as tabelas em `7570h` e `7B32h` usam `47h`,
e que `4044h` calcula `7Dh` a partir de `61h` e `64h`. Isso sustenta os
*endereços* envolvidos, mas não valida automaticamente as escalas físicas.
Há fórmulas conflitantes no scanner: `SensorDecoders.cpp` usa `7Dh×0,075`
para tensão, enquanto `sensor_database.py` usa `7Dh×0,0637`; para `61h`,
o C++ usa `61h×0,071+0,64`, e o Python devolve o byte bruto. A rotina
`4044h` demonstra que `7Dh` depende também de `64h`; portanto nenhuma
escala fixa para `7Dh` deve ser aplicada ao catálogo sem verificar o estado
de `64h` e os pontos medidos. O scanner também distingue IRAM `69h`
(avanço candidato, escala inferida) de XRAM `F8:69h` (rótulo EVAP ainda
hipotético); o trace `ENGINE-RAM addr=69` observa **IRAM**, não XRAM.

A agenda ADC da ROM G alimenta `64h` pelo **canal 4**, além do canal 1
que alimenta `61h`. Com ADC1=47, ADC7=63 e 1.000 RPM, variar apenas
ADC4 para 60/90/120 gravou `64h=3Ch/5Ah/78h` em `0744h`, enquanto
`61h=2Fh`. O cálculo original deu `7Dh=C8h/85h/64h`, conforme
`floor(256×47/ADC4)`; `31h=1Eh/3Fh/6Fh` e a mediana baixa de P5.0
foi 3.493/7.306/12.869 ticks. CC3 também mudou. Logo, esse contraste
confirma a dependência digital de `7Dh` e a covariação das saídas, mas
não isola todas as rotas pelas quais ADC4 chega aos periféricos.
Teste: `VariantTraceTests.test_adc4_divisor_changes_7d_axis_and_modeled_p5_in_g`;
capturas: `build/ma17-analysis/variants/adc4_ratio_{60,90,120}/`.

Para separar P5 da outra rota, um contrafactual manteve os mesmos três
estímulos e forneceu `31h=3Fh` **somente** antes da leitura em `0490h`,
no cálculo do Timer 1. Os valores naturais de `31h` continuaram
`1Eh/3Fh/6Fh`, `69h` ficou em `9Ah`, e a largura mediana de P5.0
convergiu para 7.306 ticks nos três cenários. CC3 conservou larguras
distintas de 5.797/6.381/6.605 ticks. Isso identifica `31h` como
mediador do contraste ADC4→P5 **nessa condição emulada**, sem explicar
a rota ADC4→CC3 nem comprovar a conexão elétrica de P5 com bobinas.
Teste: `VariantTraceTests.test_adc4_p5_width_is_mediated_by_ram31_at_timer1_read`;
capturas: `build/ma17-analysis/variants/adc4_ratio_{60,90,120}_ram31_3f/`.

Há uma rota distinta após `7Dh`: o ponteiro `706Ch→7960h` seleciona uma
curva de três segmentos idêntica nas seis ROMs. Na G, o resultado passa
por um ajuste ligado a XRAM `72h` e é gravado em `7Fh` em `4064h`; a
instrução original `MOV A,7Fh` em `1E98h` o consome no cálculo que
precede CC3. Com ADC1/4/7=47/90/63, trocar somente o retorno de
`MOVC 5333h/7966h` de `4Bh` por `80h` mudou `7Fh=7Ah→8Eh` e a largura
mediana modelada de CC3 de 6.381 para 6.541 ticks. `31h=3Fh` e P5.0
em 7.306 ticks ficaram iguais. Entregar `7Fh=7Ah` apenas antes da
leitura em `1E98h` restaurou CC3 a 6.381 ticks com a doação de `7966h`
ativa. Esse cruzamento identifica a rota digital da célula para CC3
nesse estado; função e unidade físicas continuam desconhecidas.
O interpolador leu `7968h`, cabeçalho da curva seguinte, em algumas
passagens de borda: a faixa própria `7960h..7967h` não delimita todos
os bytes que uma interpolação terminal pode consultar. Teste:
`VariantTraceTests.test_7966_movc_cell_reaches_cc3_through_ram7f`;
capturas: `build/ma17-analysis/variants/adc4_{ratio_90_movc,7966_donor_80,7966_donor_80_ram7f_7a}/`.
Executando o consumidor homólogo original nas seis ROMs para cada
`7Dh=00h..FFh`, com XRAM `72h=0`, as 1.536 saídas `7Fh` coincidiram
entre revisões. A curva é monotônica não crescente nesse estado:
`7Dh=0/64→7Fh=150`, `128→131`, `133→122`, `200→49` e
`254/255→34`. A igualdade digital das seis revisões não valida a
escala elétrica do eixo ou a correção XRAM `72h` em operação natural.
Teste: `Sab80C517.SixRom7960LookupMatchesAcrossAllRawRatioBytes`.
O bloco seguinte na G (`4053h..4065h`) e seu homólogo na família A
(`4110h..4122h`) leem `MOVX @R1` com `R1=72h`. Com `P2/XPAGE=F8h`,
144 execuções isoladas dos opcodes originais, cruzando quatro valores de
`7Dh` e seis bytes em XRAM `F8:72h` nas seis ROMs, confirmaram:
`7Fh = clamp(interpolação_7960h(7Dh) + signed8(F8:72h), 0, 255)`.
Foram testados offsets positivos e negativos e saturação nos dois
extremos. A fórmula é digital; a origem e o significado físico de
`F8:72h` ainda precisam ser rastreados. Teste:
`Sab80C517.SixRom7960LookupAddsSignedF872WithSaturation`.

A curva seguinte, `706Eh→7968h`, tem os mesmos oito bytes nas seis ROMs
e três ordenadas `80h`. Na G, `406Fh` grava seu resultado em RAM **superior**
`9Dh`; `MOV A,@R1` em `1E8Bh` lê esse byte com `R1=9Dh`. Entregar
`40h` somente à leitura `MOVC 532Fh/796Eh` (byte original `80h`)
fez `406Fh` gravar `9Dh=4Ch` em vez de `80h` e reduziu a largura
mediana modelada de CC3 de 6.381 para 4.177 ticks. Entregar `80h`
apenas antes do `MOV A,@R1` recuperou 6.381 ticks, embora `406Fh`
continuasse gravando `4Ch`. `7Fh`, `31h` e P5.0 permaneceram iguais.
Isso identifica uma segunda rota digital de compensação na G; as
ordenadas constantes não demonstram sozinhas a intenção física da curva.
Teste: `VariantTraceTests.test_796e_movc_cell_reaches_cc3_through_upper_iram9d`;
capturas: `build/ma17-analysis/variants/adc4_796e_{control,donor,rescue}_uppertrace/`.
Uma varredura isolada da leitura e escrita homólogas nas seis ROMs,
`7Dh=00h..FFh`, produziu `9Dh=80h` em **1.536/1.536** casos. Portanto,
os bytes originais formam um fator digital constante para todo o eixo
testado, inclusive onde o interpolador busca o cabeçalho vizinho como
segundo valor. A intervenção anterior mostra que a rota ainda aceita
outro valor e altera CC3 no modelo; não determina por que a calibração
original foi fixada em `80h`. Teste:
`Sab80C517.SixRom7968LookupReturns80ForEveryRawRatioByte`.

Os slots `70C6h→79B0h` e `70C8h→79BAh` selecionam duas curvas de
dez bytes, idênticas nas seis ROMs. O bloco G `48CCh..48DFh` chama o
interpolador `5329h` para cada curva e grava os resultados em RAM
superior `85h` e `86h` por `MOV @R0,A`; o homólogo A começa em
`4989h` e chama `53ECh`. O teste dos opcodes originais nas seis ROMs
confirmou as duas escritas para índices `R5=0/4/9`, com `R6=0`.
Num boot G de 120.000 ticks a 1.000 RPM, cada primeira célula foi lida
mais de 30 vezes pelo `MOVC 532Fh`. Substituir só o retorno da leitura
`79B0h` de `FFh` por `40h` fez a escrita em `85h` receber `40h` e
deixou `86h=FFh`; a intervenção simétrica em `79BAh` afetou somente
`86h`. A ROM e o byte bruto registrado para cada leitura continuaram
iguais. Os endereços `85h/86h` são **RAM superior por acesso indireto**,
não SFRs nem pinos: os leitores posteriores ainda precisam ser ligados
a uma saída física. Testes:
`SixRom79b0And79baCurvesWriteUpperIram85And86` e
`test_79b0_79ba_movc_cells_independently_write_upper_85_86`;
capturas: `build/ma17-analysis/variants/79b0_79ba_upper_*/`.
O leitor G `37FFh` seleciona `RAM[85h]` quando `B.0=1` e
`RAM[86h]` quando `B.0=0`; `3800h` multiplica o byte selecionado
pelo **byte alto** do produto anterior, não pelo byte baixo. O teste
dos opcodes originais com `RAM[85h/86h]=00h/FFh` confirmou ambos os
ramos e o byte alto resultante em `B`. Há também um leitor condicional
de `85h` em `3672h`, antes da escrita em RAM superior `C9h`.
Num rastro G atual de 2,4 milhões de ticks (`ADC0/6=40/95`,
`ADC3=80`), os escritores `48D5h/48DFh` foram alcançados, mas nenhum
dos leitores `3672h/37FFh` executou; `3699h` gravou `C9h` 230 vezes
por outro caminho. Assim, o vínculo natural dessas curvas com um pino
permanece aberto. Teste: `FiatUpper85And86ReadersSelectSeparateMultipliers`;
captura: `build/ma17-analysis/variants/79b0_79ba_reader_native_g/`.

O alvo `709Ah→79A8h` também combina um eixo segmentado (`47h`, três
segmentos, limites brutos **79/129**) e três ordenadas `FF E6 67`.
Os opcodes originais G/S88 `45EFh..45F8h` e A/S37 `46ACh..46B5h`
produziram, para todos os 256 valores de `47h` nas seis ROMs, a mesma
curva não crescente em `XRAM[F8:A3h]` (`FFh` no início, `67h` no fim).
Em G, o leitor condicional `2027h` usa `F8:A3h` antes da chamada ao
agendador `CC3` em `2036h`. Num rastro G de seis milhões de ticks,
`MOVC 532Fh/79ADh` leu `FFh` 1.436 vezes; entregar `40h` somente
nessa leitura mudou o único `R2:R3` observado em `5469h` de `3A00h`
para `0E00h`. O pulso baixo modelado de `P1.3/CC3` iniciado no tick
5.712.863 passou de **233 para 57 ticks**, embora as medianas globais
de CC3 e P5 não mudassem. O leitor `2027h` encontrou `F8:A3h=FFh`
no controle e `40h` no braço com `MOVC` alterado. Fornecer `FFh`
somente ao `MOVX` desse leitor restaurou `3A00h` e 233 ticks, mesmo
com `F8:A3h` armazenando `40h`; fornecer `FFh` ao controle foi neutro.
Assim, `F8:A3h` media a diferença no modelo. O override de leitura
`MA17_OVERRIDE_XRAM_READ_AT=2027:F8A3:FF` não altera a XRAM armazenada.
Este estado digital (`ADC0/6=120/95`) pode
combinar trilhas TPS incoerentes; a saída física ligada a `P1.3` não
foi medida. Testes: `SixRom79a8RpmCurveWritesF8a3ForAllRawValues` e
`test_79ad_movc_cell_changes_late_cc3_pulse_in_g`; capturas em
`build/ma17-analysis/variants/rpm79a8_long_*/`.

O acesso `2027h` depende do estado anterior, não ocorre em toda volta.
Em duas execuções G de 6 milhões de ticks a 1.000 RPM, com os mesmos
ADC1/2/3/4/5/7=130/100/4/90/40/63, tanto `ADC0/6=120/95` como
`120/180` alcançaram o escritor `45F8h` e a leitura `2016h` de
`XRAM[F8:A2h]`. Apenas `120/95` apresentou `PSW.F0=1` e `23h=2Fh`
em `2011h`: o desvio `203Dh` levou a `204Fh`, que incrementou
`F8:A2h` de `00h` para `01h` no tick 5.702.714. A leitura seguinte
em `2016h` encontrou `01h`, alcançou `2027h`, e `203Ah` zerou o
contador. Em `120/180`, a leitura permaneceu `00h`, sem passagens por
`204Fh` ou `2027h` durante a janela. `F0` é o bit do PSW em `D5h`,
distinto do carry. Isso delimita a condição digital vista no emulador;
o único `SETB 23h.3` no trecho, em `142Eh`, também foi alcançado só
por `120/95`. O ramo `1427h` compara `R4` com `05h` antes dessa
instrução; a causa anterior do estado ainda precisa de rastreamento.
As identidades elétricas das pistas TPS e a função física de `P1.3`
ainda exigem medição. Teste:
`VariantTraceTests.test_f8a2_counter_gates_79a8_reader_in_g`;
capturas: `build/ma17-analysis/variants/rpm79a8_f8a2_gate_*/`.

O slot antes provisório `700Ah→74A8h` contém dez bytes idênticos nas
seis ROMs (`22 22 28 2A 2C 30 34 38 3C 42`). No código G,
`48E3h` testa `T2CON.1`; `48E6h` escolhe esse slot quando o bit é
zero, e `48E9h→5321h` carrega
o ponteiro big endian e interpola bytes adjacentes. No estado G a
1.000 RPM, `RAM57h=R5=R6=00h`, de modo que `532Fh/5333h` lê
`74A8h/74A9h=22h/22h` e `R2=22h` ao retornar em `48ECh`.
Com `P4.7` padrão alto, uma guarda eleva `R2` para `25h` antes da
escrita em `RAM46h` em `48FFh`; forçar somente o pino modelado baixo
preserva `22h`. Fornecer `42h` apenas ao `MOVC 532Fh/74A8h` faz
`RAM46h` receber `42h` nos dois estados de `P4.7`, sem alterar a ROM.
Os blocos homólogos são `4773h/48E9h` em G/S88 e `4830h/49A6h`
em A/A+/S37/S36. Comparações de 16 e 33 bytes dos opcodes originais
encontraram apenas os destinos relocados das chamadas
`5279h→533Ch` e `5321h→53E4h`; o escritor A de `RAM46h` está em
`49BCh`. Isso confirma a correspondência estática nas seis ROMs,
sem demonstrar a execução natural do caminho A sob o harness Fiat.
O ramo alternativo do mesmo seletor usa `7010h→74C6h` quando
`T2CON.1=1`. Essa curva de dez bytes (`22 22 23 24 25 26 28 28 28 28`)
também é idêntica nas seis ROMs. Em execução isolada dos opcodes
originais, `R5=0/4/9` e `R6=0` alcançaram `MOVC` com `DPTR=74C6h`
e gravaram o byte selecionado em `RAM46h` nas seis imagens; com
`T2CON.1=0`, os mesmos casos selecionaram `74A8h`. O bloco que aplica
o piso dependente de `P4.7` é ignorado em `T2CON.1=1`, inclusive
quando o latch do pino está alto. Isso confirma seleção e escritor
sob estado preparado, sem demonstrar quando o modo alternativo é
atingido por uma ECU em funcionamento. Teste:
`Sab80C517.SixRomIram46CurvesSelectSixPointerSlots`.
O mesmo leitor usa `RL` sobre `IRAM57h` para escolher os pares seguintes
do diretório. A execução isolada preparou `IRAM57h=0/1/2` e cobriu
os seis slots, em cada ROM e com `R5=0/4/9`, `R6=0`:

| `T2CON.1` | `IRAM57h` | Slot | Curva | Primeiro/último byte G |
| --- | ---: | --- | --- | --- |
| 0 | 0 | `700Ah` | `74A8h` | `22h/42h` |
| 0 | 1 | `700Ch` | `74B2h` | `24h/3Dh` |
| 0 | 2 | `700Eh` | `74BCh` | `24h/3Bh` |
| 1 | 0 | `7010h` | `74C6h` | `22h/28h` |
| 1 | 1 | `7012h` | `74D0h` | `20h/2Dh` |
| 1 | 2 | `7014h` | `74DAh` | `20h/2Bh` |

Cada intervalo tem dez bytes idênticos nas seis imagens. `IRAM57h`
é inicializado com zero; não foi identificado um produtor normal de
`1/2` nem uma seleção natural de `T2CON.1=1` para esse leitor. Os
casos preparados provam a seleção e a escrita em `RAM46h`, sem
atribuir função física às quatro curvas adicionais.
Uma varredura adicional de `ADC3=4/40/80/160/220`, mantendo as demais
entradas, levou `IRAM63h=04h/28h/50h/A0h/DCh` pelo escritor `4756h`.
O seletor `7002h→73D4h` usa `IRAM63h`, e `R5` percorreu
`0/1/3/5/9`, com frações `R6=00h/B0h/20h/E0h/00h`.
Sete valores intermediários adicionais cobriram os índices
`2/4/6/7/8`; assim, todos os índices `0..9` tiveram leitura original
por `MOVC` em um dos doze perfis. Em `P4.7` forçado baixo,
`RAM46h` recebeu `22h/26h/2Ah/34h/42h` nos cinco exemplos iniciais.
No último índice, `5333h` lê `74B2h`, primeiro byte da tabela seguinte,
mas `R6=0`; esse byte não contribui para o valor observado. Isso
confirma o eixo digital e o alcance dos dez bytes nesta varredura.
Os consumidores de `RAM46h`, a escala física de `ADC3` e a ligação
elétrica de `P4.7` permanecem abertos. Testes:
`test_74a8_movc_and_p47_gate_ram46_in_g` e
`test_74a8_curve_index_tracks_iram63_in_g`; capturas:
`build/ma17-analysis/variants/74a8_ram46_*/` e
`build/ma17-analysis/variants/74a8_adc3_*/`.

Uma execução G mais longa verificou um consumidor posterior de `RAM46h`.
No código `2391h..23AFh`, esse valor entra numa comparação anterior à
rota que pode atualizar `XRAM[F8:3Dh]`. Com `ADC0/6=120/180`,
`ADC3=4`, 1.000 RPM e `P4.6` experimentalmente baixo apenas após o
tick 12.200.000, o controle tinha `RAM46h=25h`; na visita de
`23AFh` com `2Dh=D1h` perto do tick 12.287.229, carry ficou zero
e `23B9h` foi alcançado. Fornecer `42h` somente na leitura
`MOVC 532Fh/74A8h` levou `RAM46h=42h`; na visita correspondente,
carry ficou um e `23B9h` não foi alcançado. Os dois braços também
divergiram em `20h` e `24h`. O teste de resgate entregou `25h` só
à instrução original `MOV A,46h` em `2307h` no braço doador e
restaurou `231Ch` (`CLR 20h.3`) e `23B9h`, embora `RAM46h`
continuasse armazenando `42h`; entregar `25h` ao controle foi neutro.
Em `23A3h`, logo após `SUBB A,47h`, carry foi zero nos quatro braços;
o bit `20h.3` ligado no doador sem resgate é que volta a ligar carry
antes de `JC` em `23AFh`. Portanto, a leitura `2307h` media a
diferença nessa guarda digital. O override
`MA17_OVERRIDE_IRAM_READ_AT=2307:46:25` restaura a IRAM depois do
opcode e não altera a ROM.
Nenhuma mudança de `F8:3Dh` nem movimento físico foi demonstrado.
Teste lento: `test_74a8_cell_changes_late_idle_position_gate_in_g`;
capturas: `build/ma17-analysis/variants/74a8_idle_gate_*/` e
`build/ma17-analysis/variants/74a8_idle_rescue_*/`.

O comentário de `SensorDecoders.cpp` justifica `7Dh×0,075 V` por
`(256/218)×0,0637`, assumindo `64h≈DAh`. O quociente executado pela ROM
exige a razão **inversa** ao transferir uma escala de `61h` para `7Dh`:
para `64h=218`, `61h≈7Dh×218/256`, com quantização. Se os quatro
pontos `61h=156/160/172/181` e 11,67/12,05/12,82/13,50 V publicados
pelo scanner tiverem mesmo divisor 218, a ROM produziria
`7Dh=183/187/201/212`. Nesse caso, `7Dh×0,0637` daria
11,657/11,912/12,804/13,504 V; `7Dh×0,075` daria
13,725/14,025/15,075/15,900 V. A comparação é **condicional**:
o material do scanner não fornece amostras simultâneas de `64h` nem
medições elétricas do canal 4. Nenhum dos fatores foi promovido a escala
física validada no catálogo.

## Saída do injetor e hipótese de carga

Para o **Fiat Tipo 1.6 ie com MA1.7**, a tabela de pinagem do fabricante
da bancada [ECU-TEST, pp. 13–14](https://mofler.com/uploads/attachments/monthly_2014_12/Manual_de-pinagem_ecu_test_2_evolution_nacional.pdf.3521774495bcf2303df240e9ebf3cd7c)
identifica o **terminal 35 do conector da ECU** como `Eletroinjetor 1`.
Uma [medição publicada para o mesmo modelo](https://biblioteca.ismejia.com/files/electricidad/Club%20Saber%20Electr%D0%B2nica%20Nro.%2088.%20Curso%20superior%20de%20electr%D0%B2nica.pdf)
também situa o pulso de injeção no terminal 35. A pinagem atribui
`01`/`19` aos dois pares de bobinas e deixa sem atribuição a entrada
genérica de pressão absoluta. Esses números são **terminais do chicote**,
não endereços de ROM nem pinos do microcontrolador.

O [manual Siemens SAB80C517](../SAB80C517.PDF) atribui `CC3` a `P1.3`.
Na ROM G, os opcodes em `058Eh..05DCh` carregam `CCL3/CCH3` a partir de
`IRAM[14h:15h]` e controlam `P1.3`; a rotina em `1ED3h` publica esse
intervalo. Os testes de 750–2.000 RPM registraram uma borda CC3 por
meio ciclo modelado, separada das duas saídas `P5.0/P5.1`. Variações
controladas de ADC/TPS e de células da matriz `7581h` alteraram o valor
publicado e a temporização CC3. **Ainda não há trilha elétrica da placa
que ligue `P1.3` ao driver do terminal 35**. Portanto, CC3 é candidato
forte a temporizador de injeção, mas os ticks do emulador não são uma
medição de largura elétrica no bico.

Uma grade de fase com a ROM G intacta comparou `850/3000 RPM` e duas
entradas TPS estáveis (`ADC0/6=120/95` ou `40/95`), mantendo os outros
ADC em `ADC1/2/3/4/5/7=130/100/4/90/40/63`, P4.7 baixo
experimentalmente, sem K-Line e com 800.000 ticks por braço. O dente 0
da roda 60−2 alinhou duas voltas em cada janela. As medianas vieram
do relatório `execution.json`:

| RPM | TPS ADC0/6 | `14h:15h` | CC3 baixo, ticks | P5.0 baixo, graus da roda | CC3 baixo, graus da roda |
| ---: | --- | ---: | ---: | ---: | ---: |
| 850 | 120/95 | 1096 | 4373 | 102,6° | 111,7° |
| 850 | 40/95 | 665 | 2649 | 101,9° | 111,7° |
| 3000 | 120/95 | 1096 | 4372 | 61,7° | 113,1° |
| 3000 | 40/95 | 285 | 1128 | 58,0° | 113,1° |

P5.1 iniciou seu pulso baixo cerca de 180° após P5.0 em cada braço.
CC3 teve dois pulsos baixos por volta; sua largura acompanhou a mudança
de `14h:15h`, aproximadamente `4×` o agendamento menos 11–12 ticks.
Em ambos os RPMs, reduzir TPS diminuiu bastante a largura de CC3;
as larguras de P5 mudaram pouco sob o mesmo contraste. A fase de P5
mudou com RPM. Isso fortalece CC3/P1.3 como **candidato ao controle do
bico** e P5.0/P5.1 como **candidatos às duas bobinas**, sem validar a
ligação elétrica na placa. A 3.000 RPM e TPS 40/95 estável ainda houve
67 inícios de pulso CC3: **não apareceu bloqueio de CC3** nessa janela.
Testar cut-off de desaceleração requer transição coerente das pistas TPS
e **interruptor de lenta pressionado**, conforme a condição física
informada para esta ECU. Deve-se observar as guardas do agendador de
CC3, mesmo quando `14h:15h` permanece diferente de zero. O pino da
CPU correspondente ao interruptor ainda não está identificado.
Capturas e gráficos:
`build/ma17-analysis/crank-phase-{850,3000}-{sensors,tps40}/`.

`P4.3` é uma entrada candidata a investigar, pois os opcodes `2374h`
e `4991h` a testam em rotas ligadas ao controle de lenta. Um estímulo
experimental `MA17_P4_3_FORCE_LOW=1` preserva o latch de saída do
SAB80C517. A 3.000 RPM, TPS estável 40/95, 800.000 ticks, o controle
e o braço P4.3 baixo tiveram a mesma mediana `14h:15h=285`, 67
inícios de CC3 e largura baixa de 1.128 ticks. Com TPS 180/247
passando a 40/95 no tick 1.200.000, ambos os braços de 2,4 milhões
de ticks tiveram 93 amostras tardias de `14h:15h`, nenhuma zero, e
207 inícios de CC3. `RAM60h/66h` confirmou a mudança de ADC, mas
`2374h` e `4991h` não foram executados. Este teste **não simula um
interruptor de lenta comprovado** e não exclui P4.3: as duas rotas
condicionais citadas não foram alcançadas. Capturas:
`cutoff-3000-tps-release-{control,p43low}/`;
o teste de regressão do estímulo está em `PortController`.

Há uma cópia digital observável do pino: os 28 bytes em G/S88
`49ADh..49C8h` e A/A+/S37/S36 `4A70h..4A8Bh` são idênticos.
Com `P2=F8h`, a sequência empacota `2Eh.7`, `2Ah.1`, `P4.7`,
`22h.4`, `P4.3`, `P4.1` e `P4.6` nos bits 6..0 e grava
`XRAM[F8E2h]`; o bit 7 fica zero. Um teste dos opcodes originais
confirma a posição de `P4.3` (bit 2) e `P4.6` (bit 0) nas seis ROMs.
No boot G a 1.000 RPM, TPS ADC0/6=40/95 e 2,4 milhões de ticks,
forçar somente `P4.3` baixo mudou as escritas em `49C8h` de
`00→57h→77h` para `00→53h→73h`. A cobertura de PCs e os resumos
modelados de CC3 e saídas coincidiram. Capturas:
`build/ma17-analysis/variants/p4_status_{default,p43low}/`; teste
`test_p43_level_is_copied_to_f8e2_status_bit_in_full_fiat_boot`.
O byte é estado interno de XRAM: ainda não identifica a ligação
elétrica de `P4.3` nem prova que seja o contato de lenta.

O outro leitor de `P4.3` em `2374h` depende do byte em
`ROM[7375h+RAM57h]`. Nos modos `57h=0/1/2`, as seis ROMs têm
`09h/03h/05h`: bit 7 limpo, de modo que a guarda em `236Eh` pula a
consulta do pino. Um teste dos opcodes originais G/S88 `233Bh..2378h`
e A/A+/S37/S36 `2357h..2394h` confirmou `R7=5` nos três modos,
com `P4.3` alto ou baixo, quando `22h.4=1`, `P4.7=1` e `T2I1=0`.
Como prova do ramo, `RAM57h=0Fh` fez `MOVC` ler `7384h=C2h` e
`P4.3` baixo reduziu `R7` de 5 para 4. **Não foi observada seleção
natural do modo `0Fh`**; a experiência não identifica o contato físico.
No segundo leitor, G/S88 `4986h` e família A `4A49h`, os mesmos
opcodes escolheram o diretório `702Ah` para modos `0/1/2` com ambos
os níveis de `P4.3`. No ensaio isolado de modo `0Fh`, `P4.3` alto
escolheu `702Ah` e baixo escolheu `7024h`. Isso delimita a guarda das
curvas alternativas `748Ah/7494h/749Eh` sem demonstrar uso natural:
com `57h=0Fh`, o deslocamento posterior `57h×2` leva de `7024h` a
`7042h→755Ch`, e não a essas três curvas.
Regressão: `FirmwareP43IndexGateRequiresHighRom7375Bit`.
Há outros consumidores do mesmo trio de bytes. Em G/S88 `210Ch`,
o bit 2 do valor `MOVC` escreve `B.4`; o homólogo da família A é
`2128h`. Um ensaio com opcodes originais das seis ROMs, começando com
RAM superior `9Eh=B0h`, limpou `B.4` nos modos 0/1 (`09h/03h`) e o
manteve no modo 2 (`05h`). Num boot G a 1.000 RPM, TPS 40/95 e
2,4 milhões de ticks, `MOVC` leu naturalmente `7375h=09h` em
`210Ch` 11 vezes, `233Fh` 230 vezes e `36BBh` 230 vezes.
Captura: `build/ma17-analysis/variants/mode_flags_7375_g/`; teste
`test_mode_flags_7375_are_read_by_three_fiat_consumers`.
Os demais leitores testam bits 0/1/3 sob outras guardas; o rastro
documenta acesso ao modo zero, não a transição natural entre modos.

Prosseguindo no **mesmo estado de CPU isolado** até o seletor G `1A12h`
(família A `1A2Eh`), `B.4` foi gravado em RAM superior `9Eh` por
`2147h`/`2163h`. Com valor inicial `9Eh=B0h`, `XRAM[F8:10h]=0` e
índice `R4=0`, o resultado nas seis ROMs foi:

| `RAM57h` | `IRAM63h` | `9Eh` após escrita | Diretório → curva | Primeiro byte em `R1` |
| ---: | ---: | ---: | --- | ---: |
| 0/1 | `26h` | `8Ch` | `70E0h→79F0h` | `03h` |
| 2 | `26h` | `9Ch` | `70E4h→7A50h` | `02h` |
| 0/1/2 | `27h` | `8Ch` ou `9Ch` | `70E0h→79F0h` | `03h` |

O limite é `ROM[720Dh]=26h`: acima dele, a escolha do modo 2 não
alcança `7A50h`. O teste original `FirmwareP43IndexGateRequiresHighRom7375Bit`
cobre essa cadeia para G, A, A+, S88, S37 e S36. A execução começa
com entradas preparadas; não demonstra transição natural para modo 2
nem a função física de `R1`.

O leitor de bit 3 em G/S88 `360Eh` (família A `363Ch`) integra outra
cadeia digital. Em execução ligada dos opcodes originais nas seis ROMs,
`2E3Ah` (família A `2E56h`) grava `F8:EFh=max(0,IRAM[6Fh]-F8:31h)`:
entradas preparadas `60h/20h` produzem `40h`; `20h/60h` produzem zero.
Na mesma CPU, com `RAM57h=0` e `XRAM[F9:87h]=4`, `7375h=09h` permite
que `360Eh` leia `F8:EFh`. O bloco usa `ROM[72D0h]=47h`, multiplica
por quatro, satura o produto e limita por `ROM[72CCh]=3Ch`: grava
`3Ch` em RAM superior `C9h`. Com `F8:EFh=0` ou `RAM57h=1/2`
(`03h/05h`, bit 3 limpo), grava zero. O consumidor G `39B2h`/A `39E0h`
leva isso a `R2=4Ch` contra `10h` quando `B=CAh=CBh=0`, `R7=7Fh`
e `R2` inicial é `10h`. Teste:
`FirmwareF8efProducerModeFlagAndC9ConsumerLinkInSixRoms`.

Na execução completa G a 3.000 RPM, com `ADC0/6=180/247→40/95` no
tick 1,2 milhão e `ADC3/5/7=4/40/63`, `F8:EFh` recebeu
`00h→55h→AAh→00h` na inicialização e não voltou a ficar não nulo em
três milhões de ticks. `2D8Eh` foi alcançado, mas `2E3Ah` e `360Eh`
não foram; as 291 visitas registradas a `39B2h` viram `C9h=00h`.
Esse cenário não demonstra que a cadeia preparada ocorra naturalmente.
Captura: `build/ma17-analysis/variants/mode_bit3_f8ef_tps_release_g/`;
teste: `test_f8ef_and_upper_c9_stay_zero_after_fiat_tps_release`.
A função física de `C9h` permanece desconhecida.

Um segundo cenário alcançou o ramo com a ROM G intacta: 3.000 RPM,
`ADC0/6=40/95`, `ADC3/5/7=40/40/63`, 600 mil ticks e **P4.6 baixo
experimental** desde o boot. `2E3Ah` gravou `F8:EFh=14h`; `2DBEh` o
reduziu a `06h`. Sete leituras em `361Ah` viram `06h`, sete leituras
`MOVC` em `360Eh` retornaram `7375h=09h`, `3699h` gravou `C9h=3Ch`
sete vezes e `39B2h` consumiu o mesmo `3Ch`. Nessas passagens,
`39F4h` recebeu `A=9Bh`. Aos 1.000 RPM com o mesmo estímulo, a escrita
de `F9:87h` que abre a guarda em `35F1h` veio após `F8:EFh` ter caído
a zero, e `C9h` permaneceu zero; a diferença é temporal no modelo.

Um contrafactual forneceu zero somente às sete leituras `MOVX` em
`361Ah/F8:EFh`, preservando a ROM e o byte armazenado (`06h`) no log.
As sete escritas `C9h=3Ch` desapareceram e `A` em `39F4h` passou
de `9Bh` a `5Fh` nesses pontos. Os histogramas das larguras P5.0/P5.1
modeladas mudaram, com 22 inícios de pulso em cada pino nos dois braços.
CC3 manteve 46 inícios e mediana de 1.213 ticks. Isso comprova o
efeito digital de `F8:EFh→C9h→R2` nessa condição simulada; ainda falta
traçar a mediação até P5 e identificar a fonte elétrica de P4.6.
Capturas: `mode_bit3_p46low_3000_{control,zero_read}_g/` e
`mode_bit3_f8ef_p46low_{read,f987}_g/` em
`build/ma17-analysis/variants/`; teste:
`test_f8ef_read_reaches_upper_c9_r2_and_p5_with_p46_low`.

`P4.6` é outro candidato, porque `2D57h/2D60h` o leem e a rota
`29D5h` pode armar um dos estados que o scanner chama `0402h`
(interruptor de lenta), sob TPS incompatível. No mesmo degrau
180/247→40/95 a 3.000 RPM, forçar P4.6 baixo desde o boot mudou a
sequência: após 1,2 milhão de ticks, houve 121 inícios baixos de CC3,
contra 100 no controle, e larguras medianas tardias de 1.196 contra
1.188 ticks. As 93 amostras tardias de `14h:15h` também foram todas
não nulas, com mediana 299 em ambos os braços. Logo, P4.6 afeta o
controle modelado, mas este ensaio **não identificou o contato físico**.
Captura `cutoff-3000-tps-release-p46low/`.

Uma captura posterior isolou o trecho tardio do mesmo degrau TPS, com
3.000 RPM e `MA17_TRACE_CC3_AFTER_TICK=1600000`, até 3 milhões de ticks.
No controle, `IRAM[26h].7` passou a 1 entre as entradas consecutivas do
agendador CC3 nos ticks 2.184.194 e 2.194.094; a última borda modelada
de `P1.3/CC3` ocorreu no tick 2.185.454. Quando `P4.6` foi levado a
baixo **somente no tick 1.200.000**, junto com o TPS, `26h.7` mudou
entre 1.877.295 e 1.887.195; a última borda ocorreu em 1.878.528.
Ambas as capturas tiveram 142 entradas em `058Eh` após 1,6 milhão de
ticks, com `CCEN=81h` e `14h:15h` sempre diferente de zero. O desvio
de cerca de 307 mil ticks na cessação das bordas é, portanto, um efeito
digital do estímulo experimental em P4.6, não esgotamento do logger.

O opcode `JB 26h.7` em `0591h` salta sobre o agendamento de CC3; a
rotina em `2050h` atualiza o bit a partir de `F0`, após outras guardas
e cálculos. **O bloqueio de CC3 pelo bit está confirmado no firmware e
nos rastros; a função física de cut-off do bico permanece hipótese.**
Não foi demonstrado que P4.6 seja o interruptor de lenta, nem que a
mudança deste bit decorra somente do contato. Para testar a condição
necessária informada para esta ECU, ainda é preciso identificar o pino
do interruptor e comparar contatos pressionado/solto mantendo iguais
RPM, TPS e demais entradas. Capturas:
`build/ma17-analysis/cutoff-3000-late-{control,p46timed}/`.

O probe opcional `MA17_TRACE_CC3_DECISION=1` registrou os PCs que
alimentam `26h.7`, sem substituir RAM nem alterar a ROM. No controle G,
`2D04h` comparou `R2=38h` com `RAM[47h]=78h`, deixou `CY=1` e leu
`ROM[7331h]=32h`; `2D0Eh` copiou o carry para `26h.4`. Na passagem
seguinte por `1FB4h`, `26h.4` elevou `F0`, que chegou a `26h.7` em
`2052h`. Com P4.6 baixo desde o fechamento do TPS, `2Fh.0=1` e a
passagem que ativou `26h.7` veio de `26h.5`: `1F9Bh` registrou `CY=1`,
`1FB4h` preservou o carry e `2052h` gravou o bit. O estímulo muda a
rota digital; ele não identifica por si só a chave física nem comprova
que `26h.7` seja exclusivamente o estado de cut-off.

| ROM | P4.6 baixo desde o degrau? | Primeira observação após `26h.7=1`, tick | Última borda CC3, tick |
| --- | --- | ---: | ---: |
| G | não | 2.190.344 | 2.185.454 |
| G | sim, experimental | 1.883.240 | 1.878.528 |
| S88 | não | 2.190.366 | 2.185.858 |
| S88 | sim, experimental | 1.883.261 | 1.878.916 |

Os quatro ensaios terminaram no tick 3.000.000 com 142 entradas tardias
em `058Eh` por braço. `058Eh..05DCh`, `1E00h..2054h` e
`2CC0h..2D61h` são byte a byte idênticos em G e S88. As constantes
`7200h+32h..43h` e `7300h+2Fh..31h` também coincidem nas seis ROMs;
isso não autoriza aplicar os mesmos PCs à família A, cujo código em
`1Fxxh` diverge. Capturas:
`build/ma17-analysis/cutoff-{3000,s88}-decision-{control,p46timed}/`.
O teste de regressão do probe verifica que o bit observado após `2052h`
é igual a `F0` na entrada da sequência.

Controle adicional com as mesmas entradas e 3.000 RPM manteve
`ADC0/6=180/247` durante 3 milhões de ticks. Com P4.6 padrão ou
forçado baixo a partir do tick 1.200.000, nenhuma das 142 entradas
tardias em `058Eh` viu `26h.7=1`, e as bordas de CC3 prosseguiram até o
fim da captura. Assim, **P4.6 baixo isolado não foi suficiente para
ativar essa guarda** no estado testado. O degrau de TPS participa da
diferença observada, mas o contato de lenta real ainda não foi
estimulado de modo comprovado. Capturas:
`build/ma17-analysis/cutoff-3000-tpshigh-{control,p46timed}/`.

O trace de `MOVC` alcançou `ROM[7331h]=32h` em `2D0Ah` com
`DPTR=7300h` no cenário G de fechamento do TPS. Em `2D04h`, o código
compara `R2` com `IRAM[47h]`; `MOVC` não muda o carry, que `2D0Eh`
copia para `26h.4`. O byte lido é usado separadamente como recarga
de `XRAM[F826h]` em `2D15h`. Substituir **somente o retorno MOVC** por
`01h` mudou a sequência de F826h de `00→32→31→...` para
`00→01→00→01→...`; as leituras de `7331h` passaram de 2 para 41 em
3 milhões de ticks. `26h.7` ativou no mesmo tick 2.190.344 e a última
borda CC3 permaneceu no tick 2.185.454 nos dois braços. Portanto,
`7331h` é uma **recarga digital confirmada**, sem evidência de que
represente a duração do cut-off ou um tempo físico. Todas as seis ROMs
têm `32h` nesse endereço; o consumidor da família A aparece
estaticamente em `2D26h`, mas sua execução completa exige um perfil
de hardware validado. Capturas:
`build/ma17-analysis/cutoff-3000-xram26-{control,7331-01}/`;
catálogo: `xram_f826_reload_7331`.

O cut-off conhecido **na ECU física ocorre acima de 1.500 RPM**
(informação do proprietário; limiar exato e condições de habilitação ainda
não medidos aqui). Portanto, a transição digital rastreada abaixo não
deve ser chamada de limiar de cut-off físico. No cenário digital G
descrito acima, um sweep de RPM
solicitado ao gerador 60-2 mostrou outra fronteira:

Os ensaios a 1.500 RPM abaixo exercitam esse ramo digital; não são
uma observação de cut-off físico nesse RPM. A validação requer localizar
o contato de lenta e o pino do único bico, medir os pulsos com TPS fechado
e aberto e varrer RPM abaixo e acima de 1.500 em condições térmicas
controladas.

| RPM solicitado | IRAM[47h] | `26h.7` após fechar TPS | Borda CC3 tardia |
|---:|:---:|:---:|:---:|
| 1.400–1.401 | `38h` | não | sim |
| 1.425–1.500 | `39h`–`3Ch` | sim | não |

Um controle adicional manteve as pistas TPS constantes desde o boot,
com ADC1/2/3/4/5/7=520/400/16/360/160/252 em escala de 10 bits.
Com TPS fechado (`ADC0/6=160/380`), G a 1.400 RPM leu `7310h` 178
vezes, conservou `26h.7=0` e gerou bordas CC3 até o tick 2.984.620;
a 1.500 RPM leu `7310h` 180 vezes, ativou `26h.7` e a última borda
ocorreu no tick 1.162.502. Com TPS aberto (`720/988`), não houve
leituras de `7310h` nem ativação de `26h.7` a 1.500 ou 1.600 RPM;
as bordas continuaram até os ticks 2.988.390/2.996.509. Assim, a
passagem pela comparação depende do estado de TPS neste harness, além
do byte de RPM. Isso não identifica o contato de lenta nem converte a
fronteira digital em limiar físico de cut-off. Regressão:
`test_7310_guard_depends_on_tps_state_at_fixed_rpm`; capturas
`build/ma17-analysis/variants/cutoff_{1400,1500,1600}_steady_{closed,open}/`.

Uma grade adicional com G original a 1.500 RPM, ADC1/2/3/4/5/7 fixos
em `520/400/16/360/160/252`, TPS sem degrau e 2 milhões de ticks
mostrou uma **guarda anterior** à comparação com `RAM70h`:

| ADC0/6 bruto | `RAM70h` em `2D0Eh` | `27h.3` e `24h.5` em `2C3Ch` | Alcançou `2C49h`/`2D04h` | Inícios CC3 modelados |
|---:|:---:|:---:|:---:|---:|
| 320/580 | `2Ch` | ambos 1 em passagem tardia | sim/sim | 51 |
| 400/680 | `34h` | ambos 0 | não/não | 93 |

Os dois valores de `RAM70h` são menores que `4Ah`. Assim, o teste
`70h−4Ah` em `2CD3h` não explica a diferença: `2C40h` testa `27h.3`
e `2C43h` testa `24h.5` antes do `MOVC` em `2C4Bh`. A grade de oito
pares ADC0/6, de `160/380` até `720/988`, está em
`build/ma17-analysis/variants/cutoff_tps_grid_*/`; os rastros de flags
em `cutoff_tps_path_{320_580,400_680,560_880}/`. Os pares intermediários
são estímulos digitais exploratórios, sem escala física de TPS validada.
Regressão: `test_tps_state_can_bypass_7310_before_ram70_comparison`.

O produtor original `11C4h..11D1h` recebeu `R4=91h/AAh` nesses dois
cenários, gravou `RAM6Fh=R4−0Dh=84h/9Dh` e
`RAM70h=floor((R4−0Dh)/3)=2Ch/34h`. Em `29A3h`, o firmware copia
`RAM6Fh` para `R2`. Com `R3=80h`, a comparação em `2AB1h` usa
`0Dh+R3=8Dh`: `84h` passa para a máquina de estados, enquanto `9Dh`
toma o desvio para `2A45h`. No primeiro braço, `2AF9h` liga `24h.2`;
depois `2B42h..2B49h` ligam `27h.3` e `24h.5`, permitindo `2C49h`.

Para separar essa leitura do restante do TPS, um contrafactual forneceu
somente o resultado de `MOV R2,6Fh` em `29A3h`, mantendo a ROM e o
valor armazenado em `RAM6Fh` originais:

| ADC0/6 | Leitura `6Fh` fornecida | Passou por `2AF9h`/`2B42h`/`2C49h`/`2D04h` | Decisões `26h.7=1` | Inícios CC3 |
|---:|:---:|:---:|---:|---:|
| 320/580 | original `84h` | sim | 81 | 51 |
| 320/580 | `9Dh` | não | 0 | 93 |
| 400/680 | original `9Dh` | não | 0 | 93 |
| 400/680 | `84h` | sim | 81 | 51 |

Isso confirma `RAM6Fh` como mediador digital desta guarda no modelo G.
Não identifica a posição física do TPS nem prova cut-off do bico.
Capturas `build/ma17-analysis/variants/cutoff_ram6f_*/` e
`cutoff_tps_6fproducer_{320_580,400_680}/`; regressão:
`test_ram6f_read_mediates_tps_pre_movc_gate`.

A ROM S88 original repetiu os quatro braços no mesmo perfil Fiat: os
inícios CC3 foram `51/93/93/51`, e as decisões amostradas com
`26h.7=1` foram `81/0/0/81`. Os PCs `2AF9h`, `2B42h`, `2C49h` e
`2D04h` apareceram somente nos braços de leitura `84h`. Os trechos
originais `11C4h..11D3h`, `299Ah..29A7h`, `2A78h..2AB3h`,
`2AF9h..2B4Eh`, `2C3Ch..2D15h` e `1F9Bh..205Bh` coincidem em
G/S88. Regressão: `test_s88_ram6f_read_repeats_pre_movc_gate`;
capturas: `build/ma17-analysis/variants/cutoff_ram6f_s88_*/`.

Na família A, o produtor `11C4h..11D3h` permanece no mesmo endereço.
Os opcodes de `29A3h` (`MOV R2,6Fh`), `2A78h..2AB3h`, `2AF9h` e
`2B42h..2B4Eh` têm trechos idênticos deslocados em `+1Ch`;
os demais bytes desse caminho incluem destinos de chamadas e saltos
relocalizados. Isso sustenta a correspondência estática, sem demonstrar
o mesmo resultado na execução completa da família A. Regressão:
`test_ram6f_pre_movc_guard_sites_align_across_six_roms`.
Ao forçar P4.6 baixo experimentalmente, a 1.400 RPM com TPS fechado
as leituras de `7310h` aumentaram de 178 para 228, mas `26h.7`
continuou limpo e CC3 seguiu pulsando. A 1.500 RPM com TPS aberto,
as leituras passaram de zero para 60; ainda assim `26h.7` ficou limpo
e houve 143 inícios CC3 nos dois braços. Logo, alcançar `7310h` é
insuficiente para ativar a guarda. No par a 1.500 RPM, o braço com TPS
fechado chegou a `2D04h` no tick 1.167.033: `R2=38h`, `47h=3Ch` e
`CY=1`; `2D0Eh` copiou esse carry para `26h.4`, e `2052h` pôs
`26h.7=1` no tick 1.176.409. O braço aberto com P4.6 baixo também
leu `7310h`, mas em `2CD3h` tinha `RAM70h=DFh`; o teste
`70h−4Ah` tomou `JNC 2D0Dh`, limpou o carry e pulou `2D04h`.
`26h.4` e `26h.7` permaneceram limpos. No braço fechado,
`RAM70h=1Bh` permitiu continuar até `2D04h`. O caminho demonstra a
guarda anterior à comparação de RPM nesse estado. O produtor de
`RAM70h` também divergiu: o braço fechado passou por `11C4h..11D1h`,
com `R4=5Fh`, e gravou `floor((5Fh−0Dh)/3)=1Bh`.
O braço aberto com P4.6 baixo passou por `11A8h..11C0h`;
em `1175h`, `R2=B4h` e `R3=1Ah` dão
`min(FFh,B4h+0Dh)−1Ah+38h=DFh`. Isso liga os dois caminhos de
cálculo ao gate `70h−4Ah`, sem provar a escala física de `70h`.
Essas execuções não identificam P4.6 como
interruptor de lenta. Capturas `cutoff_{1400,1500}_steady_{closed,open}_p46low/`.
Rastros de decisão antecipada:
`cutoff_1500_{closed,open_p46low}_branch_early/` e
`cutoff_1500_{closed,open_p46low}_tps70_source/`.

Uma troca **somente da leitura** `MOV A,70h` em `2CD3h`, a partir do
tick 1.100.000, testou a mediação sem alterar a ROM nem o valor
armazenado em `70h`. No braço fechado a 1.500 RPM, fornecer `DFh` no
lugar de `1Bh` eliminou `2D04h` e a guarda `26h.7`; os inícios CC3
passaram de 51 para 143 em três milhões de ticks. No braço aberto com
P4.6 baixo, fornecer `1Bh` no lugar de `DFh` fez `2D04h` executar e
ligou `26h.7` durante oito decisões entre os ticks 1.114.695 e
1.186.777. O bloqueio foi transitório: os inícios CC3 passaram de
143 para 139, e as bordas continuaram depois do tick 2.900.000.
No tick 1.187.358, `2D0Eh` voltou a ver `CY=0` e limpou `26h.4`;
`2052h` limpou `26h.7` no tick 1.196.607. A persistência ainda
depende de estados adicionais no fluxo de `2Cxxh`.
Assim, `RAM70h` nessa leitura medeia a entrada no ramo, mas não é
suficiente para sustentar a guarda no estado aberto. Regressão:
`test_ram70_read_at_2cd3_mediates_rpm_guard_but_not_persistence`;
capturas `cutoff_1500_{closed_ram70read_df,open_p46low_ram70read_1b}/`.

O fim dessa guarda transitória veio de outro leitor de `70h`.
Com TPS aberto e P4.6 baixo, `29D5h` ligou `27h.0` no tick
1.187.281; `2C24h` limpou `27h.3` no tick 1.187.321,
`2C1Bh` restaurou `F8:3Bh` de `00h` para `32h` e limpou `24h.5`.
A próxima passagem por `2C3Ch` então desviou por `2CCDh→2D0Dh`,
limpando `26h.4` e depois `26h.7`. O opcode em `29CEh` compara
`4Ah−RAM70h`; com `DFh`, o carry permite chegar ao teste de
`F8:3Ch` e a `SETB 27h.0` em `29D5h` quando o byte é zero.

Um fatorial de leituras pontuais após o tick 1.100.000 separou as
duas funções de `RAM70h`, mantendo a ROM G intacta, 1.500 RPM,
TPS aberto e P4.6 baixo experimental:

| Valor fornecido em `2CD3h` / `29CEh` | Decisões com `26h.7=1` | Inícios CC3 em 3 M ticks | Última borda CC3 |
| --- | ---: | ---: | ---: |
| original / original | 0 | 143 | 2.988.390 |
| `1Bh` / original | 8 | 139 | 2.988.306 |
| original / `1Bh` | 0 | 143 | 2.988.372 |
| `1Bh` / `1Bh` | 185 | 48 | 1.106.196 |

O braço duplo não passou por `29D5h` após a intervenção;
`27h.3/24h.5` permaneceram ligados na janela observada e a guarda
persistiu até o fim de 3 M ticks. Assim, a leitura em `2CD3h`
abre a comparação de RPM, enquanto a leitura em `29CEh` pode
acionar uma rota de falha que desfaz esse estado. Essa interação é
digital e condicionada aos estímulos testados; não identifica o
contato de lenta nem a saída física do bico. Regressão:
`test_ram70_read_pair_controls_guard_persistence_with_p46_low`;
capturas `cutoff_1500_open_p46low_ram70read_1b_{29ce,both}/` e
`cutoff_1500_open_p46low_ram70read_1b_{f83b,fault}/`.
O probe opcional `MA17_TRACE_CUTOFF_PATH=1`, com janela definida por
`MA17_TRACE_CC3_AFTER_TICK`, registra esses PCs e flags sem escrever
RAM ou SFR; o teste compara os quatro braços por reinicializações
independentes.

A ROM S88 original, executada separadamente no mesmo perfil Fiat,
reproduziu os 143/139/143/48 inícios CC3 dos quatro braços. As
decisões amostradas com `26h.7=1` foram 0/8/0/186 (G: 0/8/0/185);
no braço duplo, a última borda ocorreu no tick 1.106.738. O bit
`27h.0` surgiu em `29D5h` nos braços controle e `2CD3h` isolado,
mas não nos braços com a substituição em `29CEh`. Os bytes de
`29CBh..29D6h`, `2C0Ch..2D15h`, `1F9Bh..2053h` e `7310h=38h`
são idênticos em G/S88. Essa repetição sustenta a homologia do ramo
nessas duas imagens, sem estender o resultado às quatro ROMs da família
A ou ao circuito físico. Regressão:
`test_s88_ram70_read_pair_repeats_guard_interaction`; capturas
`cutoff_s88_1500_open_p46low_{base,gate,fault,both}/`.

Nas quatro ROMs da família A, o trecho G `29CBh..29D6h` que lê
`RAM70h` em `29CEh` reaparece byte a byte em `29E7h..29F2h`;
o contador `2C0Ch..2C2Bh` reaparece em `2C28h..2C47h`.
O ramo `2C3Ch..2D15h` também se alinha com deslocamento `+1Ch`,
exceto pelos dois bytes de destino dos saltos em `2C48h` e `2C55h`.
O agendador `1F9Bh..205Bh` conserva 189 dos 193 bytes nesse
alinhamento; os quatro bytes diferentes são destinos de duas chamadas.
Isso localiza os homólogos estáticos de `29CEh`, `2CD3h` e `2054h`
em `29EAh`, `2CEFh` e `2070h`, respectivamente. Ainda não demonstra
que a família A percorra esse caminho com o perfil de hardware Fiat,
nem identifica a saída física. Regressão:
`test_ram70_guard_and_fault_sites_align_across_six_roms`.

Em `2C49h`, o firmware carrega `A=10h`; o `MOVC` em `2C4Bh` lê
`ROM[7310h]=38h` com `DPTR=7300h` e põe o resultado em `R2`.
As comparações em `2C7Ch` e `2D04h` usam `IRAM[47h]`, que acompanha
o RPM injetado.
O trecho de 280 bytes `2C49h..2D60h` é idêntico em G/S88. Nas quatro
ROMs da família A, a rotina homóloga fica em `2C65h..2D7Ch` e difere
somente no destino de um `LJMP`: `2CD3h→2CEFh`, também deslocado `+1Ch`.
Assim, o `MOVC` homólogo está em `2C67h` e as comparações em `2C98h` e
`2D20h`; todas as seis ROMs guardam `38h` em `7310h`. A regressão
`test_7310_rpm_bound_consumer_is_relocated_in_a_family` confere esses
bytes. Esta correspondência estática não valida o limiar de cut-off da
família A em execução completa, pois seu perfil de hardware difere.
Um ensaio isolado dos opcodes originais A/A+/S37/S36 preparou
`DPTR=7300h`: `2C67h` leu `7310h=38h` e gravou `R2`. Ao entrar
separadamente nas comparações de `2C98h` e `2D20h`, com a mesma CPU,
`IRAM[47h]=38h` deixou o carry limpo e `39h` o ligou. Regressão:
`AlcoholRpmBoundMovcFeedsRelocatedComparisons`. O teste confirma a
aritmética local; não mede RPM físico nem alcançabilidade no boot A.

Em quatro execuções de 3 milhões de ticks, a leitura
original em 1.400 RPM não ativou `26h.7`, mas fornecer `34h` só no
retorno desse `MOVC` ativou a guarda no tick 2.190.186 e encerrou as
bordas CC3 no tick 2.178.580. Em 1.500 RPM, a leitura original ativou
a guarda no tick 2.190.190, com última borda no tick 2.172.388;
fornecer `3Ch` ao `MOVC` impediu a ativação e manteve bordas até
2,98 milhões de ticks. O hash da ROM permaneceu igual nos quatro casos.
Logo, `7310h` é um limite **digital causal** desse ramo no modelo G,
mas não foi convertido em um limiar físico de cut-off. A divergência
com a observação acima de 1.500 RPM pede validação do tempo da roda,
do sinal real do interruptor de lenta e da saída elétrica do bico;
`CC3` ainda não foi identificado fisicamente como o bico. Capturas:
`build/ma17-analysis/cutoff-rpm-{1400,1401,1425,1450,1475,1499,1500,1501}/`
e `cutoff-rpm-{1400-7310-34,1500-7310-3C}/`;
catálogo: `iram47_branch_bound_7310`.

O mesmo experimento em **S88** reproduziu os quatro estados: em
1.400 RPM, original sem guarda e retorno `34h` com guarda; em 1.500 RPM,
original com guarda e retorno `3Ch` sem guarda. O valor bruto lido
continuou `38h` e o hash S88 não mudou. As últimas bordas CC3 foram,
respectivamente, 2.984.762, 2.178.720, 2.172.600 e 2.984.464 ticks.
Capturas: `build/ma17-analysis/s88-7310-rpm1400-{original,34}/` e
`s88-7310-rpm1500-{original,3C}/`.
Uma medição independente da roda em 1.425 RPM solicitados registrou
72 passagens pela posição zero com período invariável de 41.640 ticks,
equivalente a **1.426,5 RPM** usando 990.000 ticks/s. A quantização do
gerador explica cerca de 1,5 RPM nesse ponto, não a diferença frente
ao relato físico de cut-off acima de 1.500 RPM. Captura:
`build/ma17-analysis/crank-1425-period-check/`.
Forçar P4.7 baixo desde o boot, mantendo o mesmo degrau de TPS, também
não deslocou essa fronteira no G: em 1.400 RPM não houve guarda; em
1.425 e 1.500 RPM houve, com primeiras observações nos ticks 2.190.429
e 2.190.184. P4.7 já participa de outro piso de RPM documentado, mas
sua identidade elétrica não foi estabelecida; este resultado não
identifica o interruptor de lenta. Capturas:
`build/ma17-analysis/cutoff-p47low-rpm{1400,1425,1500}/`.

A hipótese de carga **RPM × TPS** é coerente com a falta de MAP nessa
pinagem e com as dependências digitais já medidas: `IRAM[47h]` acompanha
RPM; as duas pistas TPS alimentam estados usados na matriz `7581h`,
cujo resultado alcança `IRAM[14h:15h]`. Temperaturas, bateria e estado
lambda também alteram o cálculo. Assim, `7581h` é uma matriz candidata
de combustível, sem unidade física ou eixo de carga plenamente validado.
O comportamento informado de malha fechada em cruzeiro/marcha lenta e
aberta sob aceleração forte motivou os contrastes abaixo de TPS, ADC5,
`F8:0Ch` e CC3, mantendo RPM e temperatura constantes. A resposta lambda
sob `ADC3=4` e `ADC3=20` foi observada; a supressão da correção em
aceleração forte **ainda não foi demonstrada** pelos opcodes ou por
medição elétrica. Um TPS alto estável, um degrau de TPS e o retorno à
cruzeiro/marcha lenta são condições distintas; o ensaio do degrau
precisa preservar a coerência entre as duas pistas e evitar flags TPS.

Uma primeira grade **estável**, sem degrau de acelerador, manteve a ROM G,
1.000 RPM, `ADC3=4`, `ADC7=63` e 2,4 milhões de ticks. A mediana de
`14h:15h` abaixo usa somente entradas CC3 após 1,8 milhão de ticks:

| TPS ADC0/6 | ADC5 | `F8:0Ch` final | Passagens em `186Dh` | `2Fh` em `1810h` após 1,8 M | `14h:15h` mediana tardia |
| --- | ---: | --- | ---: | --- | ---: |
| 120/95 | 40 | `CBh` | 115 | `22h` | 1516 |
| 120/95 | 200 | `68h` | 115 | `20h` | 803 |
| 180/247 | 40 | `B0h` | 115 | `2Eh` | 1175 |
| 180/247 | 200 | `80h` | 0 | `0Ch` | 1087 |

No último caso, `2Fh.2=1` e `2Fh.1=0`; os opcodes em `180Bh..1810h`
executam `ORL C,/2Fh.1`, impedindo o salto com carry limpo em `1810h`
e a passagem por `186Dh`. No TPS alto com ADC5=40, `2Fh.1=1` e a
passagem ocorre. O teste
`test_high_tps_lambda_gate_depends_on_adc5_state` reproduz os dois
casos TPS alto. As capturas estão em `build/ma17-analysis/variants/`
sob `lambda_tps_mode_*`. Um TPS alto **estável** não representa
aceleração forte; os dados não permitem chamar o último caso de malha
aberta nem atribuir a diferença de CC3 exclusivamente ao estado `F8:0Ch`.
Um contraste transitório foi tentado com ambas as pistas mudando em `1.200.000`
ticks, de `ADC0/6=120/95` para `180/247`, mantendo `ADC5=40` ou `200`;
as capturas são `lambda_tps_step_low/` e `lambda_tps_step_high/` no mesmo
diretório. O ADC **aceitou** o degrau: `RAM[60h]` mudou `78h→B4h` no
tick 1.202.896 e `RAM[66h]` mudou `5Fh→F7h` no tick 1.204.948.
Porém, até 3,2 milhões de ticks, `RAM[6Fh]`, `70h` e `6Ah` não tiveram
nova **transição de valor** observada; `6Ah` ficou `A0h`, o valor
processado antes do degrau. Nas janelas de 2,4–3,2 milhões de ticks, ambos os casos ainda
passaram por `186Dh` 78 vezes, com `2Fh=22h/20h` e medianas tardias
`14h:15h=444/573` para ADC5=40/200, respectivamente. Os valores
`F8:0Ch` chegaram a `D5h/00h`.

Uma nova janela de probe com `MA17_TRACE_TPS_AFTER_TICK=1200000`
mostrou que `1047h..11D1h` **continua executando** após o degrau e
lê `R2=B4h`, `R4=F7h` de `RAM[60h/66h]`. No ensaio iniciado em
`120/95`, `RAM[28h]=06h` e `B=10h`; o percurso em `1183h..11C4h`
leva `R4` a `34h` e `R2` a zero, mantendo `70h=0Dh`. No ensaio
iniciado diretamente em `180/247`, no mesmo tick, `RAM[28h]=00h` e
`B=00h`; o percurso em `1175h` conserva `R4=F7h`. Isso isola uma
dependência do histórico de TPS na escolha do ramo, sem decidir ainda
se `28h` representa falha, histerese ou outro estado. Rastros:
`lambda_tps_step_high_late_probe/` e
`lambda_tps_wide_high_late_probe/`. Como os estados processados diferem,
este contraste **não** valida malha aberta durante aceleração forte.

O bit persistente foi localizado. No arranque em `120/95`, `115Eh`
escreveu `XRAM[F889h]=10h` no tick 58.299; no arranque direto em
`180/247`, esse byte permaneceu `00h` após o autoteste. Em `0FECh`,
o firmware lê `F889h` para `B`. Com as amostras brutas já iguais
`60h:66h=B4h:F7h`, o caminho de TPS alto em `10B1h..110Ah` conserva
`B.4`; `1132h..1146h` copia essa condição para `28h.1/.2`.
Um teste isolado dos opcodes originais, iniciando em `10B1h` com os
mesmos `R2=B4h`, `R4=F7h` e `28h=06h`, confirmou que `B=00h` limpa
os bits `.1/.2`, enquanto `B=10h` os mantém. Assim, a dependência
do histórico é causal no **estado digital** testado. O significado
físico de `B.4` e a coerência elétrica dos pares ADC continuam abertos;
o experimento não identifica por si só uma estratégia de malha aberta.
Capturas: `tps_f889_step_trace/`, `tps_f889_steady_trace/` e
`tps_flag_origin_{step,steady}/`.

Há uma consequência para a interpretação das calibrações: os testes
anteriores de diagnóstico ligaram `28h.1/.2` à coleta do código TPS
`0602h`; uma sessão PTY com `ADC0/6=120/95` transmitiu esse código.
Portanto, as diferenças de `7581h`, `7294h..7299h` e CC3 medidas nesse
par podem incluir a estratégia para condição de TPS sinalizada como
falha. Devem ser comparadas também em pares cujo `28h.1/.2` permaneça
limpo, antes de inferir uma curva de combustível para operação normal.

O controle `ADC0/6=40/95`, com as mesmas ROM G, 1.000 RPM,
`ADC3=4`, `ADC7=63` e 2,4 milhões de ticks, manteve `28h=00h` nas
59 passagens tardias por `1810h`. Ambos os níveis de ADC5 alcançaram
`186Dh` 115 vezes: `ADC5=40/200` terminou com `F8:0Ch=91h/6Eh`
e mediana tardia de `14h:15h=617/590` em 21 agendamentos CC3 por
caso. `6Ah=B1h` em ambos. Esse par foi o primeiro controle sem flags
TPS. O teste `test_low_tps_without_fault_flags_reaches_lambda_correction`
usa agora `ADC3=20` e quatro milhões de ticks, conforme a medição mais
recente acima. São evidências de dependência digital da entrada atribuída
à sonda mesmo sem flags TPS `.1/.2`; uma condição real de marcha lenta
ainda requer validação do ADC e da pinagem. Rastros anteriores:
`lambda_tps_faultfree_40_95_{low,high}/`.

## Três matrizes de 20 bytes em `7925h`, `7895h` e `78BDh`

O diretório de ponteiros contém `7064h→7925h`, `7080h→7895h` e
`7084h→78BDh`, com 20 bytes em cada alvo. Em A/A+ as **60 células**
valem `G+28h` módulo 256; S88/S37/S36 preservam os bytes G. Os
cabeçalhos `7054h→7824h` (`70 05`) e `7056h→782Bh` (`47 04`) usam
`IRAM[70h]` e `RAM[47h]` como eixos segmentados. O código G em
`3D2Ah..3D37h` forma `R5=R7*4+índice_RPM`, `R0=4`; `532Bh..5366h`
interpola duas linhas e duas colunas. Assim, os 20 bytes formam uma
matriz **5×4**, com frações `R4/R6`.

Os dois eixos agora têm entradas próprias no catálogo. A rotina original
`527Ch` (ou `533Fh` na outra revisão de código) lê os incrementos de
trás para frente e compara a soma com o byte de entrada usando carry de
8 bits. Executá-la nas seis ROMs para **todos os 256 valores** de cada
eixo deu limites brutos `70h`: **37, 68, 130, 250** e `47h`:
**52, 80, 108**. Somar os bytes no sentido em que aparecem na ROM
produziria limites incorretos. Em um rastro G de 3.000 RPM, os dois
cabeçalhos foram lidos 433 vezes cada por `MOVC` em 2,4 milhões de
ticks. O teste `SixRom7824And782bMatrixAxesSegmentAllRawValues` fixa
os limites; a escala física de `70h` e a conversão de `47h` em RPM
para cada clock ainda precisam de validação.

`3DC1h` seleciona `7925h` sob a guarda de `28h.1/.2` e `2Fh.0`,
gravando o resultado em `RAM[6Eh]` em `3DC7h`. O código em `1773h`
leva `6Eh` a `R4`; `184Dh/1854h` usa esse valor numa operação de
16 bits antes de `199Ah` atualizar `RAM[5Ch:5Dh]`. Em `3E14h..3E2Eh`,
outra guarda seleciona `7895h` ou `78BDh`; `3E33h` grava o resultado
por `MOVX @R1`, com `R1=01h` e `P2=F8h` no ensaio G. Não há ainda
identificação física demonstrada para `F8:01h` ou para `6Eh`.

Uma doação isolada de valores `MOVC` da ROM A para a ROM G original,
com `ADC0/6=180/247`, `ADC3/5/7=40/40/63`, 1.500 RPM e 2,4 milhões
de ticks, produziu:

| Matriz doada | Leituras no bloco | Valor final antes da escrita | Saída medida |
| --- | ---: | --- | --- |
| `7895h` | 1.780 | `3E33h`: `61h→89h`, destino `F8:01h` | P5 e CC3 medianos iguais |
| `78BDh` | 0 | ramo não alcançado; `3E33h=61h` | P5 e CC3 medianos iguais |
| `7925h` | 1.780 | `3DC7h`: `6Eh` de `5Ch→84h` | P5 e CC3 medianos iguais |

Um segundo estado natural G mostra efeito da matriz `7895h` sobre a
**contagem** de pulsos modelados. A 1.000 RPM, com `ADC0/6=180/247`,
`ADC3/5/7=34/110/63`, `ADC0/6` passa a `40/95` no tick 3.274.600.
Em quatro milhões de ticks, há 3.160 leituras de `7895h` e nenhuma
de `78BDh`. Doar somente as células A muda `F8:01h=72h→9Ah`, mantendo
o hash da ROM G. Em ambos os braços, 69 de 386 visitas a `1CB7h`
têm `7Ah≠0`. Entre 129 entradas do agendador CC3, os intervalos
`RAM[14h:15h]=0000h` após a transição passam de 2 para 14; os
inícios de pulso no modelo caem de 127 para 115. Na entrada 107,
o candidato G `00CAh` ultrapassa o limite ROM `00C8h` e é publicado,
enquanto o candidato com células A `0044h` fica abaixo e é zerado.
O braço A volta a publicar um intervalo não nulo (`00D5h`) na entrada
119. A mediana global CC3 permanece 4.404 ticks e P5, 1.921 ticks.
Isto mede efeito causal no modelo G, sem identificar fisicamente o
atuador. Capturas: `7895_tps_release_{control,donorA}/`; regressão:
`test_7895_donor_reduces_cc3_events_after_tps_release`.

Uma segunda condição G alcança naturalmente `78BDh`: 1.000 RPM,
`ADC0/6=40/95`, `ADC3/5/7=4/200/63`. Em 2,4 milhões de ticks,
`3E1Ah` ocorre 369 vezes e há 1.736 leituras `MOVC` no bloco. Doar
somente as 20 células A para a execução G preserva o hash da ROM e
altera o último `A` em `3E33h` e o `XRAM[F8:01h]` lido em `1CB7h`
de `72h` para `9Ah`. Com `ADC5=40`, a mesma condição seleciona
`7895h` (1.940 leituras) e não lê `78BDh`. A mediana de P5 permanece
1.861 ticks e a largura modelada de CC3, 2.372 ticks: no consumidor
observado `IRAM[7Ah]=00h`. A função física de `F8:01h` segue em aberto.
Capturas: `78bd_natural_tps40_95_adc3_4_adc5_200{,_donorA}/`;
regressão: `test_78bd_natural_adc5_branch_and_donor_reach_f801`.

Uma transição posterior de TPS também preserva a seleção de `78BDh`
com `IRAM[7Ah]` diferente de zero. A execução G começa com
`ADC0/6=180/247`, `ADC3/5/7=4/200/63` e 1.000 RPM; no tick 3.274.600,
`ADC0/6` passa a `40/95`. Em quatro milhões de ticks há 2.988 leituras
da matriz e 69 de 386 passagens por `1CB7h` têm `7Ah≠0`. Na última,
`7Ah=8Ch`: doar as células A muda `F8:01h=72h→9Ah` e o resultado `B`
em `1CDFh` de `0Ch` para `10h`. O opcode `mov R1,B` em `1CDFh` grava
esse resultado em `R1` logo depois do ponto observado. As medianas
globais continuam P5=1.921 e CC3=4.464 ticks, mas escondem uma
diferença na sequência: o agendador CC3 recebe `RAM[14h:15h]=0000h`
em dez visitas consecutivas na doação A (índices de instrução
3.315.115 a 3.582.432), contra valores não nulos no controle. O
modelo de pino CC3/P1.3 registra 129 inícios de pulso no controle e
119 na doação. O trace localiza a guarda: em `1EA9h`, `R3:R2=00E2h`
no controle e `005Ah` na doação; `ROM[DPTR+18h:19h]` fornece o limite
`00C8h`. O candidato da doação fica abaixo desse limite. Como
`XRAM[F8:08h]=61h` tem bit 7 limpo e `XRAM[F8:EFh]=00h`, o ramo
`1EB9h..1EC7h` zera `R5:R4`; `1ECBh..1ED3h` então publica `0000h`
em `RAM[14h:15h]`. No controle, o código preserva `00E2h`. Isso
explica as dez oportunidades de pulso anuladas no **modelo emulado**;
a ligação física de CC3/P1.3 ainda depende do circuito.
Capturas: `78bd_tps_release_adc3_4_adc5_200_{control,donorA}/`;
regressão: `test_78bd_donor_reaches_nonzero_iram7a_consumer_after_tps_release`.

A correspondência entre revisões foi verificada também por execução
isolada dos opcodes originais nas seis ROMs. O ramo G/S88 em
`3E14h..3E33h` e o ramo A/A+/S37/S36 em `3ED1h..3EF0h` selecionam
`7080h` ou `7084h` conforme `2Ch.4`, com `2Fh.1=0` e `T2I1=0`.
Fixando `R5=2` e as frações de interpolação em zero, a terceira célula
é escrita por `MOVX @R1` em `F8:01h`: `80h/81h` em G/S88/S37/S36 e
`A8h/A9h` em A/A+. O teste
`Sab80C517.SixRom78bdBranchWritesSelectedCellToF801` comprova a
homologia do ramo e das tabelas nesse estado preparado; não demonstra
a seleção durante a inicialização natural do hardware A.

O consumidor também possui correspondência comprovada: o alinhamento
leva `1CB7h/1EA9h/1ED3h` em G para `1CD3h/1EC5h/1EEFh` no código A.
Os opcodes da comparação e publicação, assim como o limite
`ROM[7218h:7219h]=00C8h`, são iguais nas seis imagens. Em execuções
isoladas com os opcodes originais, o candidato `005Ah` publica `0000h`
quando `F8:08h=61h` e `F8:EFh=00h`. O mesmo candidato publica o limite
`00C8h` quando o bit 7 de `F8:08h` está ligado, ou quando
`F8:EFh=01h` e `2Fh.0=1`. Com `F8:EFh=01h` e `2Fh.0=0`, publica zero;
`00E2h` é preservado. Teste:
`Sab80C517.SixRomCc3LowerGatePublishesZeroBelowBound`. O estado
preparado demonstra a guarda comum, sem estabelecer o acesso natural
ou a mesma sequência de pulsos no hardware A.

Um rastreamento adicional localiza onde a diferença de `7925h` se perde
nesse estado. Após tick 1.400.000, 160 passagens por `3DC7h` recebem
`A=5Ch` no controle e `84h` na doação; em 99 passagens por `183Ch`,
`R4` já conserva respectivamente `5Ch`/`84h`. `RAM[2Ch]=38h` deixa
o bit 7 desligado, e o desvio em `1840h` segue sempre para `184Bh`.
Ali `R7:R6=0000h` menos `R5:R4` positivo toma emprestado; o ramo
`1858h` satura o resultado em zero antes de `199Ah`. Nas 98
passagens tardias por `199Ah`, `R7:R6` e `RAM[5Ch:5Dh]` são zero em
ambos os braços, apesar da diferença preservada em `R4`. As estruturas
de eventos P5 e CC3 são iguais entre as execuções. Isso explica o
bloqueio **nessa condição**, sem excluir efeito de `7925h` quando a
entrada anterior `R7:R6` for maior. Capturas:
`7925_ram6e_path_{control,donor}/`; teste:
`tests.test_ma17_matrix_7925`.

Há também uma passagem com entrada positiva em outro estado G:
1.000 RPM, ADC0/6=40/95, ADC2/3=140/34, 4 milhões de ticks.
`7925h` é lida 3.240 vezes; `3DC7h` conserva a diferença, e a
passagem por `183Ch` no tick 3.284.915 recebe `R7:R6=03C0h` com
`R4=13h` no controle ou `3Bh` na doação. Mas `2Ch=A2h` liga o bit 7:
`1843h..1846h` chama `1863h`, que substitui `R5:R4` por
`RAM[5Bh]×20h=1Eh×20h=03C0h` em ambos. `199Ah` encontra
`R7:R6=0000h` nos dois braços. Portanto esta passagem também não
mede o efeito posterior da matriz; ela revela outra guarda que o
mascara. Capturas: `7925_natural_gate_{control,donor}/`; o segundo
teste em `tests.test_ma17_matrix_7925` cobre esse cruzamento.

Um cruzamento adicional muda apenas a decisão do primeiro `JNB 2Ch.7`
em `1840h` que encontra `R7:R6≠0`: o harness zera esse bit durante a
instrução original `30 67 08` e restaura `RAM[2Ch]` logo após o tick.
Os quatro braços combinam tabela G/A com guarda nativa/alterada.
Sem intervenção, `199Ah` recebe `R7:R6=0000h` nas duas tabelas; com
ela, a subtração usa `R4=13h`/`3Bh` e produz `03C0h−0013h=03ADh` ou
`03C0h−003Bh=0385h`, observados em `R7:R6` e, após a escrita, em
`RAM[5Ch:5Dh]`. A doação preserva o SHA da ROM G, e o relatório marca
explicitamente a guarda artificial. Os relatórios estruturados de
P5 e CC3 são iguais **entre os dois braços com guarda alterada**;
o CC3 mediano é 2540,5 ticks neles, contra 2540 nos braços nativos.
Portanto foi isolado um elo digital latente de `7925h` até a RAM, sem
demonstrar efeito físico ou alcance natural dessa rota. Capturas:
`7925_gate_once_{control,donor}_{normal,clear}/`; teste:
`test_one_instruction_gate_exposes_donor_result_in_5c_5d`.

Um degrau simulado nos ADC0/6, canais associados ao TPS, abriu
**a mesma rota sem alterar bit algum da CPU**.
G começa em ADC0/6=180/247, ADC2/3=140/34 e 1.000 RPM; no tick
3.267.000, apenas ADC0/6 passam a 40/95. `199Ah` recebe `0A40h` em
3.274.654, ainda com `5Bh=52h`; o escritor original `3DDCh` reduz
`5Bh` para `1Eh` em 3.280.630. Em 3.284.916, a subtração deixa
`R7:R6=0680h` e limpa `2Ch.7`. Na visita seguinte, em 3.295.357,
`1840h` desvia naturalmente para `184Bh`. Doar só os 20 bytes A de
`7925h` muda `R4=13h→3Bh`, depois `RAM[5Ch:5Dh]=066Dh→0645h`.
Ambos os braços fazem 3.160 leituras `MOVC` no intervalo da matriz.

O efeito digital persiste na trajetória de XRAM `F8:0Ch`: a primeira
transição para `8Bh` ocorre em tick 3.356.561 no controle e
3.315.882 com a tabela A. Um cruzamento somente na leitura original
`MOV R4,6Eh` (`AC 6E`, PC `1773h`) inverte `13h↔3Bh`, restaurando a
RAM fonte após cada instrução. Controle com leitura `3Bh` reproduz
os relatórios estruturados de XRAM, RAM, P5 e CC3 da doação; doação
com leitura `13h` reproduz os do controle. A ROM ativa mantém o hash
G em todos os braços. P5.0/P5.1 medianos são 1921 ticks e CC3 4404
em ambos os mapas; as distribuições individuais de bordas podem variar.
Isso demonstra mediação emulada de `7925h→6Eh→R4→5Ch:5Dh→F8:0Ch`
sob o degrau experimental de TPS, sem identificar a função física de
`F8:0Ch`. Capturas: `7925_tps_release_cross_{control,donor,
control_to_3b,donor_to_13}/`; teste:
`tests.test_ma17_matrix_7925_release`.

Uma repetição do mesmo degrau ADC0/6 fixou ADC5 bruto em `40` ou
`200`, mantendo ADC2/3=140/34 e 1.000 RPM. Em cada par G/G←A,
`7925h` foi lida igualmente (3.164 leituras no ADC5=40; 3.172 no
ADC5=200) e `R4` em `183Ch` diferiu `13h→3Bh`. Com ADC5=40,
`2Ch=AAh` nessa passagem, a sequência de `F8:0Ch` divergiu e os
valores finais aos 4 milhões de ticks foram `98h`/`A2h`. Com
ADC5=200, `2Ch=22h`, `R7:R6=0000h` na mesma região e `F8:0Ch`
permaneceu `80h` nos dois braços. P5.0 mediano ficou em 1921 ticks
e CC3 em 4404 nas quatro execuções. O scanner apresentaria `98h` e
`A2h` como +4,68%/+6,63% pela sua escala *não validada*; isso não
comprova malha fechada nem unidade física da matriz. O cruzamento
`6Eh` em ADC5=40 está descrito logo abaixo. Capturas:
`7925_lambda_factor_{40,200}_{control,donor}/`; teste:
`Matrix7925Adc5Tests.test_adc5_bounds_table_effect_on_f80c_in_tps_release`.

O primeiro cruzamento em ADC5=40 limitava o override de `1773h` a
`2Ch.7=0` e não permutou `F8:0Ch` (`98h/A2h/93h/A8h`). O trace mostrou
por quê: em tick 3.284.882, o caminho `18D9h→1958h` ainda tinha
`2Ch=8Ah`, `R4=13h/3Bh` e entrada `R7:R6=0A40h`; a diferença já
alcançou `R7:R6=0A53h/0A7Bh` em `199Ah`. A intervenção restrita não
atingia essa passagem. O probe agora substitui a leitura original
`MOV R4,6Eh` em **qualquer** estado de `2Ch.7` quando o acumulador
`5Ch:5Dh` é não nulo, restaurando `6Eh` após cada instrução.
Com isso, os quatro braços mantêm 3.164 leituras da matriz e os
finais `F8:0Ch` tornam-se `98h` (G), `A2h` (G←A), `A2h` (G→3Bh) e
`98h` (G←A→13h). Os relatórios estruturados de XRAM, RAM, P5 e
CC3 coincidem em cada par cruzado. O mesmo probe conserva a mediação
bidirecional em ADC5=110. A conclusão é uma mediação **digital no
modelo Fiat**, sem validação da interpretação lambda do scanner.
Capturas: `7925_full_read_cross_{40,110}_{control_to_3b,donor_to_13}/`;
teste: `Matrix7925Adc5Tests.test_adc5_40_all_ram6e_reads_mediate_f80c_trajectory`.

O consumidor de `F8:01h` foi encontrado em `1CB7h..1CDFh`: o código
lê `RAM[7Bh]`, `MOVX @R0=01h`, `MOVX @R0=FBh` e `RAM[7Ah]` numa cadeia
de multiplicações antes de copiar `B` para `R1`. No estado de 1.500
RPM acima, o probe `MA17_TRACE_78XX_PATH=1` observou 232 entradas em
`1CB7h`; nas últimas, `F8:01h=61h→89h` com a doação de `7895h`,
`F8:FBh=FFh` e `7Bh=78h`. Porém `7Ah=00h` em todas as entradas
registradas e `B=00h` em `1CDFh`. Assim, o produto é anulado nesse
estado, explicando por que a mudança digital de `F8:01h` não apareceu
na mediana CC3. Um teste isolado executou os opcodes G originais de
`1CB7h..1CDFh` com `7Bh=78h`, `F8:FBh=FFh` e `F8:01h=61h/89h`:
com `7Ah=00h`, `R1=00h` nos dois casos; com `7Ah=80h`, o segundo valor
de `F8:01h` produziu `R1` maior. Isto confirma um efeito **condicional
no resultado interno**. Os ensaios posteriores de transição TPS com
`7895h` e `78BDh`, descritos acima, alcançam `7Ah≠0` naturalmente
e mostram perda de pulsos no modelo CC3; a ligação física permanece
sem confirmação.

No estado TPS `120/95`, `ADC3/5/7=4/40/63` e 1.000 RPM,
`7925h` foi lida 36 vezes. A doação mudou `3DC7h` de `1Ah` para
`42h` no início, mas, após `28h=06h`, o caminho direto por
`ROM[729Ah]=E5h` entregou `E5h` em ambos. As leituras de
`7298h/7299h` ficaram em 187/42, e P5 e CC3 medianos iguais.
Isso demonstra que a seleção do consumidor mascara a diferença da
calibração nesse estado tardio; não exclui efeitos em outro regime.
Capturas: `a_code_20byte_donors/`; testes
`test_a_code_20_byte_regions_have_separate_consumers_in_g` e
`test_7925_donor_is_bypassed_after_tps_flag_at_120_95`.

Entre 40 intervalos alterados do diretório, dez não se sobrepunham a
uma entrada curada antes desta análise; restam sete, ainda preservados
integralmente em `pointer_regions.json`: `743Ah`, `7444h`, `7462h`,
`746Ch`, `753Eh`, `7939h` e `7EACh`. A sobreposição é apenas um critério
de cobertura, não prova a função de cada região.

### Curva alternativa de 15 bytes em `7EACh`

Os seis diretórios de ponteiros têm `70BCh→7E9Dh` e `70BEh→7EACh`.
O [gráfico A/S37 da curva `7E9Dh`](../build/ma17-analysis/variants/matrix_plots/matrix_7e9d_a_vs_s37.png)
mostra 15 bytes idênticos, mas eixos `RAM47h` diferentes em cada painel.
Com o produtor `1386h` e o leitor `3329h→3384h` originais em estado
preparado, a mesma entrada bruta `RAM47h=40` seleciona índice 3 na A
(`R2=99h`) e índice 5 na S37 (`R2=8Eh`) quando o flag de banco está
limpo. Com o flag ativo, os dois bancos alternativos constantes dão
`R2=99h`. Portanto, bytes de tabela iguais não garantem o mesmo
resultado para a mesma entrada bruta; a relação dessa entrada com RPM
físico ainda não foi validada na revisão S37.
Uma varredura dos 256 valores brutos, executando os mesmos opcodes
originais sob guardas preparadas, encontrou **215 entradas distintas**
no banco padrão, da primeira em `22` à última em `236`.
O banco alternativo `7EACh` resultou em `99h` nas duas ROMs em todas
as entradas. A [curva de transferência A/S37](../build/ma17-analysis/variants/matrix_plots/curve_7e9d_a_s37_transfer.png)
mostra a diferença entre as respostas interpoladas, inclusive onde os
bytes da tabela são iguais. O CSV e o JSON adjacentes registram os 256
resultados e hashes das ROMs. Para reproduzir, execute o teste
`Sab80C517.AlcoholCodeAdc3StateLadderSelectsDifferentMatrixCell` com
`MA17_7E9D_SWEEP_CSV=build/ma17-analysis/variants/matrix_plots/curve_7e9d_a_s37_transfer.csv`
e depois `/usr/bin/python3 tools/plot_ma17_curve_transfer.py
build/ma17-analysis/variants/matrix_plots/curve_7e9d_a_s37_transfer.csv`.
Essa é uma transferência digital em estado preparado; não mede a
frequência natural dos bancos nem uma grandeza física.
As janelas originais `01ABh..01BFh`, `0DD2h..0E04h`,
`0E35h..0EAFh`, `1386h..139Dh`, `3329h..3332h`,
`3384h..33D2h`, `533Ch..538Ch` e `53E4h..540Bh` são byte a byte
idênticas entre A e S37. Elas cobrem cópia/escrita de `47h`, segmentação,
seleção de banco e interpolação neste caminho; já os incrementos do
eixo em `7570h` diferem. Isso fortalece a atribuição da divergência
digital ao eixo neste ensaio, sem demonstrar que as duas ECUs gerem o
mesmo `RAM47h` para o mesmo RPM físico.
Os 14 inícios de segmento não nulos em S37 são exatamente **20
contagens brutas menores** que os correspondentes em A. A varredura
confirma a consequência com opcodes originais: para cada `x=0..235`,
`R2_S37(x, banco padrão) = R2_A(x+20, banco padrão)`; **zero diferenças
em 236 comparações**. O primeiro segmento começa em zero nas duas
ROMs, e a igualdade também vale em `x=0..4` porque ambas as curvas
ficam no platô inicial `99h`. Isso é um alinhamento horizontal da
transferência digital, não uma medida de 20 contagens de RPM.
`7EACh..7EBAh` conserva os 15 bytes G em S88, mas A/A+/S37/S36
substituem todos por `99h`. Na família de código A, `3384h` seleciona
`70BEh` quando `RAM[2Bh].7=1`, senão `70BCh`; `R7` fornece o índice.
Os opcodes A em `3329h..3332h` obtêm `R7=upper IRAM[BCh]&0Fh` e
`R6=upper IRAM[BCh]&F0h`. No teste isolado, `BCh=A0h|índice` produz
`R7=0/3/4/13`; a fração `R6` é zerada antes do lookup para ler uma
célula exata. Os dois bancos dão `99h` nos índices 0 e 3; no índice 4,
`7E9Dh` dá `94h` e `7EACh` dá `99h`; no índice 13, dão `2Bh` e `99h`.
Assim, nas leituras de células exatas a seleção do banco só altera o resultado a partir
do índice 4. A interpolação original antecipa o primeiro efeito: com o
produtor `1386h` e o leitor `3329h→3384h` executados em estado preparado,
os bancos ainda coincidem em `RAM47h=40/41` na A e `20/21` na S37,
mas divergem em `42` e `22`, respectivamente, ainda no segmento 3.
Esses números são contagens digitais brutas, sem conversão física validada.
O [gráfico interno A: `7E9Dh` versus `7EACh`](../build/ma17-analysis/variants/matrix_plots/matrix_7e9d_a_vs_7eac_a.png)
confirma quatro células iniciais iguais e 11 distintas; o maior delta
é +113 bytes na última célula. O eixo horizontal agora mostra o início
bruto em `RAM47h` de cada segmento; as colunas continuam com a mesma
largura visual, embora os intervalos digitais tenham tamanhos diferentes.
O teste integrado da revisão A confirmou
a rota digital `RAM47h→7046h→7570h→upper BCh→R7`; a escala física
desse eixo e a seleção em boot completo permanecem em investigação.
O [gráfico G/A de `7EACh`](../build/ma17-analysis/variants/matrix_plots/matrix_7eac_g_vs_a.png)
mostra a curva G/S88 descendente, de `92h/9Ch` no início até `52h` nas
últimas células, substituída por um platô `99h` nas quatro ROMs da
família A. As 15 células mudam, com delta assinado de −3 a +71 bytes.
O CSV conserva endereços e bytes; o JSON registra os hashes. Para
reproduzir: `/usr/bin/python3 tools/plot_ma17_matrices.py --matrix
0x7EAC --variant A`. O platô orienta a investigação do ramo selecionado;
o gráfico não estabelece eixo, unidade física nem frequência de acesso
em operação normal.
Um teste com opcodes originais das quatro ROMs A, `R7=4`, `R6=0` e
`T2CON.1=0`, alcançou `MOVC` em `53F2h`: com flag limpa leu
`7E9Dh+4=94h`; com flag ativa leu `7EACh+4=99h`. O valor chegou a
`R2` e à upper IRAM `A4h`. Isso comprova a seleção e o destino interno
nesse estado isolado. O teste integrado descrito acima também propaga
o flag produzido em `3C7Dh..3D04h` até este leitor, com a guarda de
entrada preparada. A seleção em boot completo e o significado físico
de `A4h` permanecem em aberto. Uma tentativa de trace completo da ROM A
foi recusada pelo
guardrail de `tools/trace_ma17.py`, que exige código idêntico ao G até
`757Fh`; isso não é evidência de que o ramo seja inacessível na ECU A.
No G, `335Fh` passa `DPTR=70BCh` ao helper `5321h` antes
de `3371h` sobrescrever DPTR. Com P4.6 experimental baixo e 3.000 RPM,
o trace G observou 131 leituras do ponteiro `70BCh` e de
`7E9Dh+9=60h`/`7E9Dh+10=58h`; sem esse estímulo, essa seleção não
ocorreu na janela testada. Isso comprova o acesso G no modelo sob essa
entrada, sem estabelecer o estado elétrico natural de P4.6 na ECU.

O mesmo diretório tem a terceira palavra `70C0h→7EBBh`. Os intervalos
`7E9Dh..7EABh` e `7EBBh..7EC9h` contêm 15 bytes cada, idênticos nas
seis ROMs. Um teste dos opcodes originais G/S88 e A/A+/S37/S36 iniciou
os ramos `335Ch`/`3384h` com `R7=9`, fração `R6=0`, e selecionou
`RAM[57h]=0/1/2`: os ponteiros resultantes foram `7E9Dh`, `7EACh` e
`7EBBh`, com leitura da décima célula e publicação em upper IRAM A4h
quando `T2I1=0`. Para o terceiro intervalo, o byte foi
`7EC4h=5Dh`. O modo 2 foi imposto no ensaio; seu acesso natural neste
caminho e a função física de A4h seguem em aberto. Regressão:
`Sab80C517.Pointer70bcSelectsThreeCurvesWithRam57`.

Um sweep posterior executou o produtor original `1386h` e o leitor
`3329h→3384h` em A e S37 para os **256 valores brutos** de `RAM47h`,
com guardas preparadas, `RAM57h=2` e `RAM2Bh.7=0`. Embora os 15 bytes
de `7EBBh` sejam idênticos, o resultado `R2` difere em 157 entradas
iguais (primeira 1, última 158), por causa do eixo `7570h`. A relação
`S37(x)=A(x+20)` vale de `x=5` a `235`; nos cinco valores `0..4`, ela
falha porque o primeiro segmento tem larguras diferentes e as duas
primeiras células da curva são `88h` e `9Ch`. Isso contrasta com a
curva `7E9Dh`, cujo início plano `99h` preserva a translação desde
`x=0`. Consulte o [gráfico da transferência `7EBBh` A/S37](../build/ma17-analysis/variants/matrix_plots/curve_7ebb_a_s37_transfer.png)
e o CSV/JSON homônimos. O teste
`Sab80C517.AlcoholCodeAdc3StateLadderSelectsDifferentMatrixCell`
exporta o CSV quando `MA17_7EBB_SWEEP_CSV` aponta para o caminho de
saída; `tools/plot_ma17_third_curve_transfer.py` gera o gráfico e as
métricas. Os resultados provam uma diferença digital no estado preparado;
não estabelecem a seleção natural desse modo ou uma escala física.

Nesta etapa da investigação, ainda faltavam seis dos 40 intervalos
alterados: `743Ah`, `7444h`, `7462h`, `746Ch`, `753Eh`, `7939h`.
As seções seguintes documentam esses seis; todos têm entrada curada
na versão atual do catálogo, sem implicar função física confirmada.

### Matriz de 20 bytes em `7939h` e resultado `RAM[5Bh]`

O ponteiro `7066h→7939h` é igual nas seis ROMs. Como as matrizes
`7925h` e `7895h`, esta usa o índice de linha `RAM[70h]` e o índice
de coluna derivado de `RAM[47h]`, em formato 5×4. Os primeiros quatro
bytes e o quinto valem `G+28h` em A/A+; os outros 15 são iguais nas
seis ROMs. S88/S37/S36 conservam todos os 20 valores G. O código G
em `3DD6h` escolhe esta matriz ou o byte direto `ROM[729Bh]` conforme
as flags `28h.1/.2` e `2Fh.0`; `3DDCh` grava o resultado em `5Bh`.
Em `1863h`, `5Bh×20h` forma `R5:R4`, utilizados na aritmética de
`184Bh..1858h`. O primeiro ensaio abaixo não alcançou `1863h`; os
ensaios posteriores registraram a execução desse consumidor.

Os bytes das **seis ROMs** confirmam a homologia da rota, com dois
conjuntos de endereços. O teste
`test_7939_writer_and_ram5b_consumer_are_homologous_in_six_roms`
verifica o ponteiro, a chamada ao interpolador, a gravação de `5Bh`, a
guarda da chamada, a multiplicação, a soma e a escrita diagnóstica:

| ROMs | Escrita `5Bh` | `JB 2Ch.4` / chamada | `5Bh×20h` | Soma | `MOVX F8:0Ch` |
| --- | --- | --- | --- | --- | --- |
| G, S88 | `3DD6h→532Bh`, `3DDCh` | `18B2h` | `1863h` | `1958h` | `19D2h` |
| A, A+, S37, S36 | `3E93h→53EEh`, `3E99h` | `18CEh` | `187Fh` | `1974h` | `19EEh` |

O ponteiro `7066h→7939h` é idêntico; A/A+ alteram cinco células,
enquanto S88/S37/S36 preservam os 20 valores de G. Essa comparação
estabelece a rota **estática** nas revisões. Os efeitos dinâmicos abaixo
foram medidos somente no perfil de hardware G com doação de bytes A;
eles não demonstram que a ROM A percorre a mesma guarda em sua ECU.

O teste isolado `Sab80C517.Fiat7939HomologousLookupAndRam5bMultiply`
executa o código **nativo de cada uma das seis ROMs**, começando na
consulta a `7066h`, com índice linear `R5=0..4`, frações zero e depois
no consumidor `5Bh×20h`. Os cinco resultados foram:

| Índice linear | G/S88/S37/S36: `5Bh→R5:R4` | A/A+: `5Bh→R5:R4` |
| ---: | --- | --- |
| 0 | `13h→0260h` | `3Bh→0760h` |
| 1 | `23h→0460h` | `4Bh→0960h` |
| 2 | `3Dh→07A0h` | `65h→0CA0h` |
| 3 | `52h→0A40h` | `7Ah→0F40h` |
| 4 | `1Fh→03E0h` | `47h→08E0h` |

Cada célula A/A+ acrescenta `28h` ao byte e `0500h` ao produto nesse
estado sem interpolação fracionária. Isso confirma que a diferença chega
ao produto também no código A. O teste não executa o boot, não
valida as entradas físicas e não mede a saída CC3 da revisão A.

Com fração digital `R6=80h`, o mesmo teste isolado obteve:

| Índice linear | G/S88/S37/S36: `5Bh` | A/A+: `5Bh` | Diferença A−G |
| ---: | ---: | ---: | ---: |
| 0 | `1Bh` | `43h` | `28h` |
| 1 | `30h` | `58h` | `28h` |
| 2 | `47h` | `6Fh` | `28h` |
| 3 | `38h` | `60h` | `28h` |
| 4 | `2Bh` | `3Fh` | `14h` |

Para esses cinco pares, o `A` retornado segue
`valor_inicial + floor((próximo − inicial)/2)`. Nos índices 2 e 3, a
diferença entre células é ímpar: `R2` guarda o valor uma unidade maior,
mas `XCH A,R2` devolve o menor em `A`, que é gravado em `5Bh`.
No índice 4, a célula seguinte não foi alterada por A/A+; por isso a
diferença interpolada cai de `28h` para `14h` e a diferença do produto
`5Bh×20h` cai de `0500h` para `0280h`. O índice 3 atravessa o limite
linear entre duas linhas; a execução isolada não demonstra que a fração
`80h` seja alcançável naturalmente nesse limite.

O estado **natural G** em que `1863h` foi chamado usa duas frações.
O probe opcional `MA17_TRACE_7939_INDEX=1` registrou, na última escrita
de `5Bh` antes da chamada, `R0=04h`, índice `R5=00h`, fração da
primeira direção `R6=40h`, da segunda `R4=80h`, `RAM[47h]=28h` e
`RAM[70h]=1Bh`. A primeira interpolação formou `R2=17h` entre
`13h/23h` e `R3=25h` entre `1Fh/37h`; a segunda deu `A=5Bh=1Eh`.
Doar só os bytes A da matriz manteve os índices e as frações, mas deu
`R2=3Fh` entre `3Bh/4Bh`, `R3=43h` entre `47h/37h` e
`A=5Bh=41h`. Assim, a diferença natural `1Eh→41h` é `23h`, menor
que `28h` porque a célula `793Eh=37h` não mudou. O teste isolado
da rota nativa das seis ROMs reproduz os mesmos pares `R2/R3`, `5Bh`
e os produtos `03C0h/0820h` nesse estado digital. A reprodução nativa
isolada da ROM A não prova que seu boot atinja o mesmo estado.
O teste `test_7939_natural_air_input_boundary_mediates_f80c` confere
também a última escrita antes de `1863h`. Capturas:
`build/ma17-analysis/variants/7939_writer_index_{control,donor}/`.

Uma grade G de 4 milhões de ticks manteve ADC2/3=`140/34`, os demais
ADCs iguais e variou apenas RPM ou o par digital TPS ADC0/6. A linha
abaixo mostra o estado **dominante em `3DDCh`**, não uma calibração
em unidades físicas:

| RPM | ADC0/6 | `47h`, `70h` | `R4`, `R5`, `R6` | `5Bh` G→A doada | `1863h` em 4 M |
| ---: | --- | --- | --- | --- | ---: |
| 750 | 40/95 | `1Eh`, `1Bh` | `80h`, `00h`, `00h` | `19h→41h` | 1 |
| 1000 | 40/95 | `28h`, `1Bh` | `80h`, `00h`, `40h` | `1Eh→41h` | 1 |
| 1500 | 40/95 | `3Ch`, `1Bh` | `80h`, `01h`, `40h` | `34h→48h` | 0 |
| 1000 | 120/95 | `28h`, `0Dh` | `00h`, `00h`, `40h` | `9Bh→9Bh` | 1 |
| 1000 | 40/180 | `28h`, `37h` | `90h`, `04h`, `40h` | `3Eh→4Bh` | 1 |
| 1000 | 120/180 | `28h`, `37h` | `90h`, `04h`, `40h` | `3Eh→4Bh` | 1 |
| 1000 | 180/247 | `28h`, `DFh` | `C0h`, `0Ch`, `40h` | `52h→52h` | 1 |

Nos três primeiros pares, a mudança de RPM moveu o índice/fracionamento
da coluna mantendo `70h=1Bh`; as diferenças A−G em `5Bh` foram
`28h`, `23h` e `14h`. Com ADC0/6=`120/95`, o estado estável desviou
para o byte direto `ROM[729Bh]=9Bh` (`28h=06h`), embora 18 consultas
iniciais à matriz ainda tenham ocorrido. Com `180/247`, a matriz leu
células das linhas altas que valem `52h` em ambas as ROMs. A ausência
de `1863h` em 1.500 RPM é limitada a esta janela; nos demais seis
estados houve uma chamada. O teste lento
`test_7939_native_axis_states_and_direct_byte_bypass` confere hashes,
estado final do escritor e chamadas. Capturas:
`build/ma17-analysis/variants/7939_axis_rpm{750,1500}_tps40_95{,_donor}/`
e `7939_axis_rpm1000_tps{120_95,180_247}{,_donor}/`.
Nos dois estados com ADC6=180, `RAM[60h]` acompanha ADC0 (`28h→78h`),
enquanto `RAM[66h]=B4h`, `RAM[6Fh:70h]=A7h:37h` e `28h=00h`
permanecem iguais. A seleção e o resultado da matriz também não mudam.
Capturas: `7939_tps_factor_adc0_{40,120}_adc6_180_{control,donor}/`.
Uma repetição com o probe TPS ativado depois do tick 3.000.000 confirmou
em `11C4h` `R2=28h/78h`, mas `R3=1Ah`, `R4=B4h` e `28h=00h` em
ambos os casos. O ramo normal `11C4h..11D4h` usa `R4`: calcula
`B4h−0Dh=A7h`, depois `A7h/3=37h` com resto `02h`, e grava
`6Fh=A7h`, `70h=37h`. Assim, a igualdade do par deriva do mesmo
`R4` escolhido antes de `11C4h`; o efeito de ADC0 nas decisões anteriores
continua condicionado ao estado. Capturas:
`build/ma17-analysis/variants/7939_tps_flow_late_{40,120}_180/`.
O par ADC0/6 afeta `70h`, flags e seleção da fonte em outros estados;
esta grade não isola qual entrada física define o eixo de linha.

Na ROM G original, com 1.500 RPM, `ADC0/6=180/247`, `ADC3/5/7=40/40/63`
e 2,4 milhões de ticks, houve 1.780 leituras `MOVC` no intervalo.
Doar apenas os valores da matriz A para o `MOVC` alterou o primeiro
acumulador em `3DDCh` de `1Fh` para `47h`, preservando o hash da ROM G.
Nas passagens tardias, ambas leram as células saturadas `52h`;
as medianas modeladas de P5 e CC3 permaneceram 1767/5137 ticks.
O teste `test_7939_donor_reaches_iram5b_only_in_unsaturated_rows`
reproduz esse contraste. Falta alcançar o consumidor posterior e
vincular `5Bh` a uma saída física.

Em 1.500 RPM com `ADC0..7=180/130/100/4/90/40/247/63` e 4 milhões
de ticks, G e G com apenas os 20 bytes de `7939h` doados pela A
mantiveram o contraste inicial em `3DDCh` (`1Fh→47h`) e convergiram
para `52h` nas leituras tardias. Em ambos, a mediana CC3 foi 5495
ticks. O novo probe opcional `MA17_TRACE_RAM5B_GATE=1` registrou
115 visitas a `1840h`, todas com `2Ch.7=0`, desviando da primeira
chamada de `1863h` em `1846h`. Na única visita a `18B2h`, `2Ch=1Ah`
(`2Ch.4=1`), desviando da segunda chamada em `18B5h`. A última
visita a `1840h` precedeu `18B2h`; `1863h` não foi alcançado.
O teste `test_7939_ram5b_consumers_are_gated_at_coolant_four` cobre
as duas execuções e as guardas. Capturas:
`build/ma17-analysis/variants/7939_ram5b_gate_adc3_4_{control,donor}/`.
Essas guardas explicam a ausência de efeito posterior **neste estado**;
a seção abaixo identifica uma condição natural que habilita `1863h`.

Um contrafactual separou o fator de aquecimento da matriz. Em G,
2.000 RPM, ADC0..7 bruto `40/130/100/200/90/40/95/63` e 4 milhões
de ticks, o controle leu `742Dh=4Dh` e `742Eh=5Ah`, manteve `87h=36h`
e não alcançou `1863h`. Entregar `00h` somente nos retornos `MOVC`
de `PC532Fh/742Dh` e `PC5333h/742Eh` fez `87h=00h`, abriu a rota
`186Dh` e alcançou `1863h` uma vez, em `tick=1226678`. Esse override
é artificial; os bytes da EPROM e seu hash ficaram intactos.

Nesse estado controlado, doar apenas `7939h..794Ch` da ROM A mudou
`RAM[5Bh]` na chamada de `1863h` de `47h` para `5Bh`. Para isolar o
consumidor, `MA17_OVERRIDE_RAM5B_READ` fornece um byte apenas à
instrução `MOV A,5Bh` em `1866h` e restaura a RAM após a instrução.
O harness confere os bytes `E5 5B` nesse endereço antes de habilitar
o override, para não aplicar o ensaio a outra revisão de código.
Resultados:

| Matriz `7939h` | Leitura em `1866h` | Mediana CC3 | `F8:0Ch` final | Mediana P5.0 |
| --- | --- | ---: | --- | ---: |
| G | `47h` | 2245 | `F4h` | 1789 |
| A doada | `5Bh` | 2265 | `F9h` | 1789 |
| G, leitura `5Bh` | `5Bh` | 2265 | `F9h` | 1789 |
| A doada, leitura `47h` | `47h` | 2245 | `F4h` | 1789 |

A reversão demonstra que a leitura de `5Bh` em `1866h` medeia o
contraste de CC3 e `F8:0Ch` **nesse estado artificialmente habilitado**.
Não comprova que a ROM A use esse caminho em seu hardware nem a ligação
física de CC3 ao bico. Teste:
`test_7939_ram5b_read_mediates_cc3_when_factor_gate_is_open`.
Capturas: `build/ma17-analysis/variants/7939_ram5b_gate_rpm2000_adc3_200_87zero{,_donor,_control_to_5b,_donor_to_47}/`.

Uma segunda grade alcançou o consumidor **sem override do fator**.
Com a ROM G, 1.000 RPM, ADC0/1/3/4/5/6/7 bruto
`40/130/34/90/40/95/63` e 4 milhões de ticks, variar apenas ADC2
alterou `RAM[62h]` no mesmo valor bruto; `RAM[63h]=22h` permaneceu
fixo. Com ADC2=`128`, `18B2h` viu `2Ch=1Ah` e desviou de `1863h`;
com ADC2=`129`, viu `2Ch=0Ah` e executou `1863h` uma vez. Os bytes
`ROM[721Eh]=7Ah` e `ROM[721Fh]=81h` são comparados em `17ADh/17B9h`;
o segundo `SUBB` preserva o carry da primeira comparação. Essa
fronteira é **digital e condicionada ao estado ensaiado**; não converte
ADC2 em temperatura física. Capturas: `7939_natural_gate_adc3_34_adc2_{128,129}/`.

Com ADC2=`140`, `1863h` ocorreu naturalmente em `tick=3274617` e
`RAM[5Bh]=1Eh` na ROM G. Doar só a matriz `7939h..794Ch` da ROM A
mudou esse byte para `41h`. A intervenção temporária na leitura
`MOV A,5Bh` em `1866h` confirmou a mediação em ambas as direções:

| Matriz | Leitura em `1866h` | `F8:0Ch` final | Mediana CC3 | Mediana P5.0 |
| --- | --- | --- | ---: | ---: |
| G | `1Eh` | `91h` | 2541 | 1861 |
| A doada | `41h` | `9Ah` | 2541 | 1861 |
| G, leitura `41h` | `41h` | `9Ah` | 2541 | 1861 |
| A doada, leitura `1Eh` | `1Eh` | `91h` | 2541 | 1861 |

Assim, a diferença de `7939h` chega a `F8:0Ch` por `5Bh` em uma
condição de entrada natural da ROM G. A mediana global modelada de
CC3 não separou os quatro casos; o significado físico de `F8:0Ch`
continua inferido do scanner. O teste
`test_7939_natural_air_input_boundary_mediates_f80c` reproduz a
fronteira e os quatro contrafactuais. Capturas:
`build/ma17-analysis/variants/7939_natural_gate_adc3_34_adc2_140{,_donor,_control_to_41,_donor_to_1e}/`.

Um probe adicional no mesmo estado seguiu a primeira passagem após
`1863h`. Em `tick=3274628`, o produto `5Bh×20h` era `R5:R4=03C0h`
(G) ou `0820h` (matriz A doada). Como `F0=1` em `18D9h`, a rota de
`1958h` soma `R5:R4` a `R7:R6`, inicialmente zero. Em `199Ah`, o
resultado efetivo foi `R7:R6=03C0h/0820h` e `5Ch:5Dh` recebeu o mesmo
par. A conversão em `19B6h..19D0h` entregou `A=87h/90h` antes do
`MOVX @R0,A` em `19D2h`, coerente com
`clamp(128 + (signed16(R7:R6) >> 7), 0, 255)`.
Doar a matriz e substituir apenas a leitura de `5Bh` em sentidos
opostos permutou os dois resultados de `R5:R4`, `R7:R6` e `A` no mesmo
tick, sem alterar a ROM G. O byte final após 4 milhões de ticks foi
`91h/9Ah`, pois a rotina continua atualizando o estado. O teste acima
agora confere também esses estados intermediários. Capturas:
`build/ma17-analysis/variants/7939_postmul_{control,donor}/`.

Estendendo a mesma condição natural até **12 milhões de ticks**, os quatro
ensaios abaixo mantiveram uma única chamada de `1863h` e o hash original
de G. Cada execução registrou 200 amostras de agendamento CC3, 398
pulsos completos no log e período mediano de 29.700 ticks no modelo:

| Matriz `7939h` | Leitura em `1866h` | Mediana CC3 baixa | Primeiro `F8:0Ch=FFh` |
| --- | --- | ---: | ---: |
| G | `1Eh` | 2726,5 ticks | 11.528.101 |
| A doada | `41h` | 2762,5 ticks | 10.924.151 |
| G, leitura `41h` | `41h` | 2762,5 ticks | 10.924.151 |
| A doada, leitura `1Eh` | `1Eh` | 2726,5 ticks | 11.528.101 |

A mediana agendada de `RAM[14h:15h]` foi **647 em todos**, assim como
seus extremos 630/1348; a mediana de P5.0 permaneceu 1861 ticks. Esse
resumo esconde uma diferença localizada: as primeiras 104 amostras de
agendamento coincidem, mas as 96 seguintes sobem **9 contagens em 38**
e **10 em 58** com a matriz A. As duas leituras cruzadas reproduzem
exatamente as respectivas sequências de 200 valores. Nos pulsos CC3
correspondentes, índices 104..199, a largura doada sobe 36 ticks em 37
casos, 40 em 55, 37 em um e 39 em três; pequenas diferenças de borda
são visíveis mesmo antes da chamada. A partir do pulso 383, as duas
larguras voltam a coincidir após a saturação do estado.

A permutação cruzada confirma que a leitura de `5Bh` medeia a diferença
de agendamento e de CC3 modelada nessa janela prolongada. Ela não
identifica eletricamente CC3 como o bico monoponto. O teste lento
`test_7939_natural_gate_reaches_late_cc3_through_ram5b` reproduz os
quatro casos com `MA17_RUN_SLOW=1`. Capturas:
`build/ma17-analysis/variants/7939_long_{control,donor,control_to_41,donor_to_1e}/`.

As implementações C++ (`SensorDecoders.cpp`) e Python (`sensor_database.py`)
do scanner usam os mesmos coeficientes Steinhart–Hart e supõem pull-ups de
2661 Ω no ar (`RAM[62h]`) e 3004 Ω na água (`RAM[63h]`). Aplicar **essa
hipótese do scanner** aos bytes brutos do ensaio dá ADC2=128/129/140 como
18,41/18,03/13,81 °C e ADC3=34 como 68,11 °C. O par de entradas é
numericamente plausível para ar e motor aquecido. Entretanto, os
coeficientes foram ajustados a partir de outro sensor Bosch e os pull-ups
não foram medidos na ECU Fiat; esses graus Celsius não são uma validação
física da fronteira `128→129` nem da função da matriz `7939h`.

Restam cinco dos 40 intervalos alterados sem entrada curada:
`743Ah`, `7444h`, `7462h`, `746Ch` e `753Eh`.

### Curva do modo 2 em `7462h`

O ponteiro `701Ch→7462h` existe nas seis ROMs. Em G, `4916h` escolhe
o grupo `7018h` quando `T2CON.1=0`; o leitor `5228h` seleciona a
terceira curva pelo índice `RAM[57h]=2`, e `532Fh/5333h` interpolam
dois bytes adjacentes. Todos os dez valores da curva A/A+ são
`G+1Ah`; S88/S37/S36 preservam G. O cálculo em `4922h..49ADh`
termina em `RAM[4Dh]`. O código em `22F3h` lê `4Dh` para aritmética
de ponto fixo já documentada para a curva vizinha `744Eh`.

Com a ROM G intacta, 1.000 RPM, `ADC0/6=120/95`, `ADC7=63` e
intervenção explícita `RAM[57h]=2`, houve 394 leituras `MOVC` em
`7465h/7466h` ao longo de 2,4 milhões de ticks. Doar somente os
valores A para essas leituras mudou a primeira escrita repetida
`RAM[4Dh]=21h→3Bh` em `49ADh`; a escrita inicial `34h` foi igual.
As medianas modeladas P5/CC3 permaneceram 5908/5677 ticks. O teste
`test_7462_mode_two_donor_changes_iram4d` reproduz o contraste.
O modo 2 foi imposto pelo experimento: faltam sua seleção natural e
um efeito físico demonstrado.

Restam quatro intervalos alterados sem entrada curada: `743Ah`,
`7444h`, `746Ch` e `753Eh`.

### Primeira célula de `753Eh` e escrita em XRAM `F806h`

O ponteiro `703Ch→753Eh` existe nas seis ROMs. Esta curva de dez bytes
é toda zero em G/S88/S37/S36; A/A+ alteram somente o primeiro byte
para `22h`. O código G em `47D1h` escolhe `703Ch` quando `T2CON.1=0`
e `2Fh.5=1`, senão escolhe `703Eh→7548h`. `5329h` interpola pares
adjacentes e `47E0h` grava o resultado em XRAM `F806h` (`P2=F8h`,
`R1=06h`). A flag `2Fh.5` é escrita em `19DEh` a partir da comparação
de `RAM[3Dh]` com `02h`, conforme o rastreamento anterior desse contador.

O slot vizinho `703Eh→7548h` contém dez zeros nas seis ROMs. No trace
completo G `movc_gasoline`, o lookup leu `754Bh/754Ch` 280 vezes por
endereço; o trace S88 `movc_sun8817_2s` registrou 512 leituras de cada.
Um teste dos opcodes originais das seis ROMs, com índice e fração zero,
confirmou que `2Fh.5=1` usa `703Ch` e `2Fh.5=0` usa `703Eh`, ambos
escrevendo o resultado em `F8:06h`. A identidade física do campo segue
desconhecida. Regressão:
`Sab80C517.Pointer703c703eBranchesFeedXramF806`.

Na ROM G original, a 1.000 RPM com `ADC0/6=120/95`, `ADC3/5/7=4/40/63`
e 2,4 milhões de ticks, o trace registrou 281 leituras de `753Eh`
em `532Fh` e 281 de `753Fh` em `5333h`. Doar somente os valores A
nesses `MOVC` preservou o hash da ROM G e gerou, em `47E0h`, uma
escrita `F806h:00h→22h` no tick 1.231.225; no controle, `F806h`
permaneceu `00h` após a inicialização. As medianas modeladas P5/CC3
foram iguais nos dois casos: 1861/4646,5 ticks. O teste
`test_753e_first_cell_donor_changes_xram_f806` reproduz o resultado.
Os únicos `MOVX` que leram `F806h` nos dois traces foram os testes
de memória de partida em `55A2h`, antes da escrita alterada. Assim,
não se observou consumidor posterior nesses 2,4 milhões de ticks;
um uso por hardware externo ou em outro estado permanece em aberto.

Um trace G com a mesma doação e estado inicial, estendido a 8 milhões
de ticks, contou 1.616 leituras `MOVC` da célula `753Eh` e a escrita
`F806h:00h→22h` em `47E0h` no tick 1.231.225. As únicas leituras
`MOVX` de `F806h` continuaram sendo as duas verificações da partida em
`55A2h`; nenhuma ocorreu após a escrita alterada. A instrumentação
registra as primeiras mil leituras desse endereço, portanto esse
resultado limita o caminho observado, sem excluir leitura por hardware
externo ou outro estado do firmware. `F8:06h` é endereço XRAM, não
pino identificado. Captura: `variants/f806_long_donor/`.
O harness atual rejeita a ROM A completa porque o prefixo de código
difere de G antes de `757Fh`; a seleção natural da célula `22h` em A
continua pendente de um perfil de hardware validado.

### Quatro curvas neutras `7B00h..7B27h`

Os ponteiros `70AEh/70B0h/70B2h/70B4h` apontam para quatro blocos de
dez bytes `80h`, idênticos nas seis ROMs. O código G em
`483Bh/4874h/48A9h/4896h` chama o interpolador de bytes adjacentes;
o homólogo A está deslocado `+BDh`. Após o lookup, `CPL ACC.7`
transforma `80h` em `00h`: o primeiro ramo escreve RAM **superior**
`CFh`, o segundo combina o resultado com `CFh` e escreve `CEh`, e os
dois últimos podem escrever `CDh` (um deles combina com `D0h`).
O teste dos opcodes originais das seis ROMs, com `R5=3`, `R6=0` e os
acumuladores anteriores zerados, confirmou ambos os `MOVC` de cada
par e a escrita de zero em `CFh/CEh/CDh`.

Os rastros completos já existentes mostram `DPTR=7B00h` em S88,
`7B0Ah` em G e `7B1Eh` em G sob estímulo experimental. Nenhum dos
rastros inspecionados mostrou `DPTR=7B14h`; esse quarto ramo foi
demonstrado apenas em execução isolada. Esses blocos são baselines
digitais neutros nos estados testados. Seus eixos e funções físicas
permanecem abertos. Regressão:
`Sab80C517.FourNeutral70ae70b4CurvesUseAdjacentByteHelper`.

Restam três intervalos alterados sem entrada curada: `743Ah`,
`7444h` e `746Ch`.

### Duas curvas adicionais do grupo `701Eh`: `743Ah` e `7444h`

Os ponteiros `7020h→743Ah` e `7022h→7444h` existem nas seis ROMs.
Ambas são curvas de dez bytes: em A/A+, cada célula é `G+1Ah`;
S88/S37/S36 preservam G. Com `T2CON.1=1`, o código G em `4916h`
e o homólogo A em `49D3h` iniciam pelo grupo de ponteiros `701Eh`.
O leitor usa `RAM[57h]×2`: modo 1 escolhe `7020h`, modo 2 escolhe
`7022h`. `R5/R6` fornecem índice e fração para a interpolação.

O teste `PostCoolantTimer2SelectsBothRaisedCurves` executou os
opcodes originais das seis ROMs com `R5=7`, `R6=0` e os dois modos.
Em `743Ah`, o byte lido virou `R2=82h` em G/S88/S37/S36 e `9Ch`
em A/A+. Em `7444h`, os resultados foram `6Eh` e `88h`. Os
endereços efetivos e os bytes foram conferidos contra cada ROM.
A execução partiu de estado preparado; os traces de boot G/S88
anteriores não observaram leitura natural dessas duas curvas.
O caminho G após `4922h` pode chegar a `RAM[4Dh]`, mas o teste
acima confirma apenas o valor em `R2`.

Resta um dos 40 intervalos alterados do diretório sem entrada curada:
`746Ch`.

### Curva condicional `746Ch` e soma em `RAM[4Dh]`

O ponteiro `702Ah→746Ch` existe nas seis ROMs. Dez bytes são `0Fh`
em G/S88/S37/S36; A/A+ trocam somente o primeiro por `29h`.
O código G `497Ah..49ADh`, homólogo A `4A3Dh..4A70h`, escolhe
condicionalmente o grupo de ponteiros `702Ah` ou o alternativo
`7024h`. O leitor usa `RAM[57h]×2`; o índice da leitura direta é
`R5 + carry(R6.7)`. O byte lido é somado a `R2`, limitado a `BAh`
e gravado em `RAM[4Dh]`.

O teste `Pointer702aFirstCellAddsToIram4dAcrossSixRoms` executou
os opcodes originais a partir de `4997h` em G/S88 e `4A5Ah` na
família A, com `DPTR=702Ah`, `RAM[57h]=0/1/2`, `R5=R6=R2=0`.
Os três ponteiros levam a `746Ch/7476h/7480h`. Em modo zero, `MOVC`
leu `746Ch` e a escrita final em `4Dh` foi `0Fh` nas quatro ROMs
com bytes G ou `29h` em A/A+; nos modos 1 e 2, a primeira célula
comum `05h` chegou a `4Dh` nas seis ROMs. Os intervalos de dez bytes
dos dois modos novos são provisórios, delimitados pelo próximo alvo
do diretório. Esse teste começa **após** as
guardas de `22h.4`, upper IRAM `A5h` e seleção entre grupos;
portanto, não demonstra acesso natural aos modos 1 e 2 nem a função
física da diferença no modo zero.

O grupo alternativo `7024h/7026h/7028h` aponta para três intervalos
candidatos de dez bytes em `748Ah/7494h/749Eh`, iguais nas seis ROMs.
Os limites vêm dos próximos alvos do diretório; o leitor indexado não
impõe esse tamanho por si. Os opcodes
originais de G e da família A, iniciados após as guardas em
`4997h/4A5Ah`, selecionaram cada ponteiro com `RAM[57h]=0/1/2` e
gravaram a primeira célula em `RAM[4Dh]` com `R2=R5=R6=0`:
`08h/03h/03h`. A seleção anterior do grupo `7024h` exige bit 7 do
byte lido em `7375h+RAM[57h]` e P4.3 baixo. Nos modos 0/1/2,
esses bytes originais são `09h/03h/05h`, todos com bit 7 limpo;
portanto, o teste isolado confirma o leitor e a soma, mas não a
seleção natural do grupo. Teste:
`Pointer7024ThreeCurvesAddToIram4dAcrossSixRoms`.

Os 40 intervalos alterados do diretório de ponteiros têm agora ao
menos uma entrada curada; várias entradas ainda registram seleção
natural, consumidor posterior ou função física como desconhecidos.

### Revalidação de capturas antigas com o ADC atual

A grade antiga `experiments_repeat/` usava o callback ADC de 8 bits
(`ADDAT` no log); a grade nova `experiments_adc10_current/` usa
`ADDATH/ADDATL`. Para G, 1.000 RPM, `ADC0/6=120/180`, `ADC7=63`
e 2,4 milhões de ticks, o trace antigo contou 444 leituras de
`746Fh` em `499Fh` e mediana CC3 de 11384,5 ticks. A repetição
atual contou zero leituras em `746Ch..7475h` e mediana CC3 de
5245 ticks. Os números brutos ADC coincidem, mas a conversão de
entrada e a versão do emulador diferem; não se atribui toda a
diferença observada a um único defeito sem ensaio de isolamento.

No trace atual com `MA17_TRACE_RAM4D_PATH=1`, `220Ch` apareceu 230
vezes. `RAM[22h].5` estava ativo em todas, anulando a condição que
escreve `RAM[22h].4`; `4997h` não foi alcançado. O teste
`test_current_adc_path_blocks_746c_when_ram22_bit5_is_set` verifica
esta ausência no estado descrito. O resultado isolado da primeira
célula de `746Ch` continua válido para os opcodes das seis ROMs,
mas sua seleção natural não foi demonstrada.

Quatro estados G adicionais com o ADC atual, cada um por 2,4 milhões
de ticks e `ADC7=63`, produziram o mesmo bloqueio: 1.000 RPM e
`ADC0/6=40/95, ADC3=4`; 1.000 RPM e `120/95, ADC3=4`;
1.500 RPM e `180/247, ADC3=40`; 750 RPM e `40/95, ADC3=80`.
Em cada caso, `RAM[22h].5=1` nas 230 observações de `220Ch`, sem
passagem por `4997h` ou leitura de `746Ch..7475h`. Forçar P4.7
baixo no caso `120/180` alcançou `21F2h`, mas não limpou a guarda
nem alcançou a curva. As capturas estão em `ram4d_gate_grid/`.
No código G, `220Ch` escreve `22h.4` e `220Fh` escreve seu complemento
em P5.3; a função física desse pino continua sem confirmação.
Um novo probe em `21F9h..2211h` confirmou `DPTR=7200h` e 230 passagens
por `220Fh` em cada uma de duas partidas G a 1.000 RPM, com P4.7 padrão
ou forçado baixo. Em ambas, `22h.5=1` bloqueou P5.3 baixo. O teste dos
opcodes originais com estado preparado mostra que P5.3 passa a baixo
somente quando P4.7 está alto, `RAM[63h]` supera `ROM[72C5h]=0Eh`,
`22h.5=0` e `PSW.5=1`. `72C3h..72C5h` foi incluído no catálogo com
evidência separada. P4.7 e P5.3 são candidatos a examinar na hipótese
de pedido/liberação do A/C informada pelo usuário; a fiação, a
polaridade externa e o papel de `22h.5` ainda são desconhecidos.
O probe da rota produtora contou 230 entradas em `21C6h`, nenhuma
em `21CAh` e `28h.1=1` em 229 das entradas de `21C6h`; os opcodes
`2174h..2180h` incluem esse bit na guarda que mantém `22h.5` ativo.
Com TPS experimental `ADC0/6=40/95`, `28h=00h` em todas as 230
entradas de `21C6h`; as primeiras 21 chegam pelo desvio `2Eh.0=1`
em `216Ah`, e as outras 209 passam por `21C2h`. Portanto, há outra
rota de bloqueio mesmo sem `28h.1`. O teste Python fixa essa distinção.
O probe ampliado dessas 209 passagens mostrou `upper IRAM[9Eh]=4Ch`
(`B.6=1`) e `upper IRAM[A6h]` sempre não zero, de `64h` a `50h`.
O salto `2167h` evita então a checagem das flags em `2174h` e vai a
`21C2h`; dali, `2Dh.5` apenas decide se decrementa `A6h` antes de
`21C6h` ligar `22h.5` (20 passagens com `2Dh.5=1`). `A6h` e `9Eh`
são RAM superior endereçada indiretamente, não pinos nem SFRs.
O latch modelado de `P5.3` permanece alto; sua ligação ao pedido ou
à liberação física do A/C ainda não foi estabelecida.
Captura: `variants/p53_guard_audit_lowtps/`.

Estendendo esse estado a **15 milhões de ticks**, `A6h` chegou a zero
perto do tick 10.505.322. O código passou então por `2174h` 440 vezes,
mas `27h.1/.3` permaneceram ligados (`27h=0Eh/8Eh`): `21CAh` nunca
foi alcançado, `P5.3` não caiu e não houve leitura de `746Ch`.
Ao fornecer `0Eh` somente ao `MOVX F8:39h` em `2B38h`, com `ADC3=20`
(`RAM[63h]=14h` no trecho estável), o código original G executou
`21CAh` 439 vezes, com 439 níveis baixos observados no latch P5.3,
e leu `746Ch` 904 vezes por `MOVC`. Sem essa substituição de leitura,
mas com o mesmo `ADC3`, nenhuma dessas leituras da curva ocorreu.
`F8:39h` é estado XRAM compactado; a substituição é uma intervenção
digital, não um sensor físico validado. A fiação de P5.3 permanece aberta.

Nesse estado preparado, `499Fh` leu a primeira célula com
`RAM[57h]=R5=R6=0` e `R2=19h`. Doar somente a curva `746Ch` de A
(`29h` na célula zero; os nove bytes restantes iguais a G) ao `MOVC`
mudou `RAM[4Dh]` de `28h` para `42h` nas visitas pareadas a `233Bh`.
O resultado em `2593h` mudou de `2Ch` para `49h`. Os 152 pulsos baixos
CC3 modelados após o tick 10,5 milhões tiveram larguras idênticas no
controle e na doação; não se observou efeito em CC3 nesse cenário.
Ambas as execuções preservaram o hash da ROM G. Capturas:
`variants/p53_guard_long_adc3_20/`,
`variants/p53_guard_long_fault0e_adc3_20/` e
`variants/p53_guard_long_fault0e_adc3_20_donor746c/`.

Uma grade curta de TPS localizou um caminho **sem substituição de
`F8:39h`**: com `ADC0/6=100/155`, `ADC3/5/7=20/40/63`, 1.000 RPM e
15 milhões de ticks, a ROM G executou `21CAh` 440 vezes, registrou
439 amostras baixas do latch P5.3 e leu `746Ch` 922 vezes. `27h=04h`
e `28h=00h` no estado posterior; `2B38h` não foi visitado. Os pares
TPS `20/70`, `30/85`, `50/105`, `60/115` e `80/135` ainda
produziram `F8:39h=2Eh` e `27h=0Eh` em 2,4 milhões de ticks; `100/155`
terminou com `27h=04h`. Esses valores ADC são estímulos do modelo,
sem validação da correspondência elétrica das duas pistas.

Doar somente `746Ch` de A ao `MOVC` nesse percurso G sem override de
estado interno preservou o SHA da ROM e mudou `RAM[4Dh]` de `28h`
para `42h` em 183 visitas pareadas a `233Bh`; `A` em `2593h` mudou
de `2Ch` para `49h`. Os 152 pulsos CC3 pareados após 10,5 milhões de
ticks tiveram larguras idênticas. Isso estabelece seleção da primeira
célula e efeito interno **na execução completa G emulada**, sem
demonstrar seleção na ROM A completa ou efeito físico no atuador.
O teste `P53GateTests.test_delayed_746c_first_cell_donor_reaches_iram4d`
reproduz esse percurso. Capturas:
`variants/p53_guard_natural_tps100_155/` e
`variants/p53_guard_natural_tps100_155_donor746c/`.

Com os mesmos ADCs e 15 milhões de ticks, a ROM G leu `746Ch`
951/922/876/820 vezes a 750/1.000/1.500/3.000 RPM. `25EDh` não
foi alcançado a 750 ou 1.000 RPM, mas apareceu a 1.500 e 3.000.
Doar a curva A nessas duas rotações ainda mudou `RAM[4Dh]`
`28h→42h` em 193 e 191 amostras pareadas, respectivamente.
Os 227 pulsos CC3 pareados a 1.500 RPM e os 455 a 3.000 RPM após
10,5 milhões de ticks tiveram larguras idênticas; as medianas P5
também ficaram iguais dentro de cada par.

Um probe temporal a 3.000 RPM registrou `25EDh` 1.459 vezes, incluindo
443 após 10,5 milhões de ticks. Doar `746Ch` alterou `R3` em 452
entradas de `25EDh` e 450 passagens por `2606h`, mas o acumulador `A`
em `2606h` permaneceu igual em todas as passagens pareadas. O fluxo
visitou `26C5h` e não alcançou `26D8h`, ramo posterior que ainda pode
usar `R3`. Portanto, a propagação até `R3` foi confirmada; nenhum
efeito de saída foi observado nesses estados. O teste
`P53GateTests.test_746c_downstream_division_is_reached_without_output_change`
reproduz o contraste a 3.000 RPM. Capturas: `variants/746c_rpm_{750,1500,3000}/`,
`variants/746c_rpm_{1500,3000}_donor/` e
`variants/746c_downstream_{1500,3000}_{control,donor}/`.

O probe `MA17_TRACE_RAM4D_BRANCH` separa os bloqueios em `2653h`.
Em G a 3.000 RPM, ADC0/6=100/155 e `P4.6` baixo somente após
10,6 milhões de ticks, ADC2=160/ADC3=80 deixou `2Fh.4=1`, mas
`62h=A0h` mais o limite ROM `733Bh=28h` não ficou abaixo de
`upper IRAM[A8h]=50h`; o fluxo ainda tomou `26C5h`. Com ADC2=20,
`62h=14h`, o mesmo ensaio atingiu `26CBh` 100 vezes e `26D8h` 99
vezes. `P4.6` aqui é **entrada modelada do pino da CPU**, não um
terminal da ECU identificado: o SAB80C517 também oferece CM6 nesse
pino. `62h`, `2Fh.4` e `A8h` são estados de RAM, não pinos.
Nesse estímulo, as 149 leituras de `746Ch..7475h` foram em `746Fh`
(índice 3, byte `0Fh` comum às ROMs); a célula divergente `746Ch`
não foi selecionada. Portanto, alcançar `26D8h` ainda não demonstra
efeito dessa diferença nem identidade física de uma saída.
Capturas: `variants/746c_p46_late_adc2_{160,20}_adc3_80/`.

Uma varredura sem forçar `P4.6`, mantendo ADC0/6=100/155, ADC2=4,
3.000 RPM e 12 milhões de ticks, mediu ADC3=32/40/48. O `MOVC`
com DPTR=`746Ch` leu `746Dh`/`746Eh`/`746Eh` 285/280/290 vezes;
`upper IRAM[A8h]` foi `20h`/`28h`/`30h`. Em ADC3=20, a primeira
célula `746Ch` é lida, mas `A8h=14h` não supera sequer o limite
`733Bh=28h` somado a `62h`. Nos estados testados, a mudança de
ADC3 que abre o limite desloca o índice para células iguais entre
as variantes. Isso **não prova** exclusão para todas as entradas,
estados temporais ou perfis de hardware. Capturas:
`variants/746c_adc3_grid_{32,40,48}/`.
Testes: `P53GateTests.test_p47_input_changes_gate_state_but_bit225_blocks_p53`,
`P53GateTests.test_p46_and_adc2_open_late_26d8_branch` e
`Sab80C517.FiatP53GateUsesP47CoolantThresholdAndBit225`.

### Limite do fatorial `7580h/7581h/7B46h` por estado TPS

Repeti a intervenção de três calibrações S88 sobre a ROM G intacta, com
ADC2/3/5/7=100/20/40/63 e 2,4 milhões de ticks por execução. Com
ADC0/6=40/95, as rotações de 750, 1.500 e 3.000 RPM reproduziram as
distribuições AE/BC, R2 e leituras de células `7B46h` da S88 natural.
Também coincidiram os resumos de lookup, CC3 e cobertura de PC, os valores
finais de `69h/34h` e as medianas modeladas de P5 e CC3. As medianas
P5/CC3 foram, respectivamente, 1863/2508, 1784/1973 e 1785/1489 ticks.

Em 1.000 RPM, `ADC0/6=120/180` manteve os valores finais `69h/34h=97h/86h`
e medianas P5/CC3=1921/4165 ticks; houve diferença de um tick em um
resumo de offset de CC3. Em `ADC0/6=180/247`, a seleção mudou para a matriz
`7CAEh` (912 leituras), enquanto `7B46h` apareceu apenas na inicialização.
A intervenção em `7B46h` deixou R2 dominante em `99h` e `69h/34h=A1h/2Fh`,
contra `A1h` e `A5h/34h` na S88 natural. Doar `7CAEh` no mesmo cenário
recuperou esses valores finais e as medianas P5/CC3=1921/5512,5 ticks.
As contagens de R2 na inicialização e um offset de CC3 ainda diferem.
O teste `test_high_tps_switches_7b46_effect_to_7cae_matrix` cobre essa
troca. Capturas: `build/ma17-analysis/variants/triad_rpm_grid/` e
`triad_tps_grid/`. Estes resultados são digitais; a escala física do TPS
e a equivalência completa dos estados continuam sem demonstração.

Repeti a intervenção com a matriz `7CAEh` em 750 e 1.500 RPM, mantendo
o mesmo estado ADC de TPS alto e 2,4 milhões de ticks. G com valores
`MOVC` da S88 e S88 natural fizeram, respectivamente, 684 e 912 leituras
da matriz em cada rotação. Coincidiram os valores finais `69h/34h`
(`A5h/17h` e `9Eh/ECh`), as medianas P5/CC3 (1940/5138 e 1765/5548
ticks), os resumos estruturados de lookup e CC3, e a cobertura de PC.
Os estados dominantes AE/BC e R2 concordaram; a S88 natural teve uma
observação R2 adicional na inicialização. O teste
`test_high_tps_7cae_donor_matches_selected_outputs_across_rpm`
reproduz esses resultados. Capturas: `triad_high_tps_rpm/`. A diferença
de inicialização impede inferir equivalência de estado completo.

## Validação e próximos testes

### Separação experimental das matrizes `7581h` e `7B46h`

Com a ROM G original, 1.000 RPM, ADC0/6=40/95, ADC3=20, ADC5=40,
ADC7=63 e 4 milhões de ticks, a mediana do pulso CC3 **modelado** foi
2460,5 ticks, `IRAM[69h]` terminou em `9Ah` e P5.0 teve 1861 ticks.
Doar somente as 225 células de `7581h` da S88 elevou CC3 a 2978,5;
`69h` e P5.0 permaneceram iguais. Doar somente as 120 células de
`7B46h` mudou `69h` para `A2h`, sem alterar essas medianas CC3/P5.0.
As duas intervenções conferem ponteiro e hash da ROM doadora; o teste
`test_clean_tps_s88_matrix_donors_separate_cc3_and_ram69` reproduz o
contraste. O resultado identifica caminhos distintos **nesse estado**;
não confirma a ligação elétrica de CC3 ao bico nem a função física de
`7B46h`. Capturas: `lambda_matrix_donors_current/`.

O valor `69h` da matriz `7B46h` foi consumido pela rota do Timer 1:
`34h:35h` passou de `8BFFh` para `A8FFh` e `32h:33h` de `12FEh`
para `2FFEh`. Um override na leitura de `69h` em `043Bh` reproduziu
`34h=A8h` no controle quando forneceu `A2h`; com a matriz doadora,
fornecer `9Ah` restaurou `34h=8Bh`. Nas últimas 20 ocorrências P5.0
emparelhadas, o intervalo da borda baixa em `00A8h` à carga do Timer 1
em `0298h` teve mediana **375→404 ticks**; da carga à borda alta em
`0098h`, **1486→1457 ticks**. As duas variações de 29 ticks se
compensaram, mantendo a largura mediana em 1861 ticks. Portanto, P5
inalterado nesse ensaio **não significa ausência de efeito interno**.
O teste acima agora verifica os dois intervalos. Capturas:
`ram69_7b46_mediation/` e `timer1_7b46_path/`.

Com ADC0..7 bruto `40/130/100/20/90/40/95/63` e 4 milhões de ticks,
repeti a doação exclusiva de `7B46h..7BBDh` em duas rotações. A tabela
mostra medianas dos últimos 20 pulsos P5.0 pareados, em ticks emulados:

| RPM | `7B46h` | `69h` final | Borda baixa → carga T1 | Carga T1 → borda alta | Largura P5.0 |
| ---: | --- | ---: | ---: | ---: | ---: |
| 750 | G | `9Ch` | 386 | 1477 | 1863 |
| 750 | S88 | `A4h` | 424 | 1439 | 1863 |
| 1500 | G | `8Dh` | 17 | 1807 | 1824 |
| 1500 | S88 | `95h` | 36 | 1788 | 1824 |

A mudança de `69h` deslocou a carga de Timer 1 por 38 ticks em 750 RPM
e 19 ticks em 1.500 RPM; o intervalo restante até a borda alta mudou
no sentido oposto, preservando a mediana da largura nesses dois estados.
O teste `test_7b46_timer1_edge_shift_persists_at_750_and_1500_rpm`
verifica hash, tamanho da matriz doada, RAM e tempos dos eventos.
Capturas: `build/ma17-analysis/variants/7b46_timer1_rpm{750,1500}_{control,donor}/`.
Isso confirma um efeito temporal interno condicionado ao estado, mas
continua sem identificar eletricamente a saída P5.0.

O `tools/roundtrip_8051.py` remontou `G`, `A`, `A+`, `S88`, `S37` e
`S36`: 32768 bytes, zero divergências e SHA-256 igual ao original em
todos os casos. Os cinco hashes únicos Fiat selecionam o perfil C517A
com `XPAGE`, `SYSCON` e vetores da família; não houve avisos de SFR
desconhecido nem erros do assembler. A S88 passou de 18.225 para
23.420 bytes classificados como código ao receber seus vetores e SFRs.
A S36 teve 22.282 bytes classificados; seu vetor `53h` aponta para
`AA0Dh` em vez de `00B0h`, exigindo análise própria de alcançabilidade.
A remontagem prova fidelidade dos bytes, não acerto de todas as classificações
estáticas. `test_fiat_calibration_variants_use_c517a_profile` cobre as
cinco imagens modificadas; `G` mantém seu teste separado.

## Comando K-Line `04h` e sequência de saídas na ROM G

O assembly modular reconstruído em
`build/ma17-analysis/modular/` é a referência de instruções e endereços
desta análise; `report.json` registra 32768 bytes, zero divergências e SHA-256
idêntico. O scanner declara `ECU_REQ_ACTUATOR = 04h` em
`ECUMonomotronic.h`, mas não encontrei chamada desse identificador no código
do scanner. O nome do comando é uma pista, não a identificação de um atuador.

No firmware G, `4AD1h` testa `RAM[47h]`: zero seta o bit 0 da **RAM superior
indireta** `@8Ah`; não zero limpa esse bit. Em `50BBh`, o ID `04h` chama
`51C1h`, que rejeita o pedido se `@8Ah.0=0`. Com esse bit ativo, `51C1h`
atualiza o contador `MOVX @C8h` quando `T2I1=0`: zero carrega `08h`, `02h`
vira `01h`, e `01h` vira zero e sinaliza o passo final. A resposta passa
por estado `42h=06h` nos passos intermediários e por `42h=03h` no final.
O estado `06h` entra em `4EFBh` e prepara o frame `F5h` em XRAM `B8h` em
diante; os dois bytes de progresso são `11h/11h` para `C8h=08h` e
`77h/77h` para `C8h=01h`. O teste
`FiatKlineCommand04RequiresStoppedRpmFlagAndCyclesCounter` executa os opcodes
originais de `50BBh` e `4C06h` com estados controlados e confirma essas
transições, a rejeição e os bytes do frame. Ainda não é uma sessão K-Line
completa observada no PTY.

O contador `C8h` também chega a `317Ch` e a `319Bh` quando `@8Ah.0=1`.
Os casos `02h` e `01h` setam `@8Ah.4` e `@8Ah.7`; em `0688h` e `069Bh`
esses bits condicionam P5.2 e P1.1 pelo limiar `RAM[1Ch]=03h`.
Essa ligação é **estática**, ainda sem trace integrado que comprove cada
transição de pino durante o comando `04h`. A função elétrica desses pinos,
o componente acionado e a equivalência da sequência nas revisões A/S88/S37/S36
permanecem não confirmados. As anotações de `50BBh`, `4EFBh` e `319Bh`
ficam em `asm/ma17/semantic_labels.tsv`, que o exportador aplica novamente
ao gerar os includes; os arquivos `.inc` gerados não foram editados.

Próximo ciclo: determinar a origem e o significado de `RAM[28h].1` e
`ROM[7298h]`, testar a interação `716Ch/7CAEh/72A7h` em outros estados
ADC2/RPM e continuar
a separação causal de `73E0h→78h` e confirmar a ligação física do CC3
ao bico. Na rota lambda, verificar as demais flags e o contador `3Ch`
que condicionam a entrada em `186Dh`, e medir o efeito do estado interno
`R7:R6` sobre CC3 sem confundir o byte diagnóstico `F8:0Ch` com realimentação.
Repetir o fatorial `7580h/7581h/7B46h` em outras rotações, pares TPS
sem falha e temperaturas; comparar também os histogramas e a história
de RAM, que não coincidiram integralmente nos dois estados atuais.
Falta distinguir os demais caminhos que alteram P5 em `S88` com `ADC1=40`
e confirmar o circuito conectado a P5. As demais revisões precisam de verificação de perfil antes
de ensaios no harness Fiat.
### Grafo estático do fluxo de controle

`python3 tools/plot_ma17_cfg.py` lê o assembly modular já validado, usa os
comprimentos das instruções da ROM Fiat Tipo e gera
`build/ma17-analysis/cfg_36de.dot` e `.svg`. O intervalo padrão cobre o teste
de `B.4/B.5` em `36DEh` e a preparação da matriz `7E16h`; `--start`, `--end`
(limite exclusivo) e `--output` selecionam outras regiões. O grafo mostra
blocos básicos e arestas de salto, chamada e continuação. Destinos fora da
janela aparecem como nós externos; `JMP @A+DPTR` aparece como destino indireto
pendente. Arestas estáticas descrevem possibilidades, não execução comprovada.

Para restringir o grafo a rotas que poderiam ligar PCs observados, use, por
exemplo, `python3 tools/plot_ma17_cfg.py --pcs 0x36DE 0x36E1 0x3701
--output build/ma17-analysis/cfg_trace_example.svg`. A ordem dos PCs importa.
O `.json` correspondente separa cada par observado, informa os blocos
candidatos e marca pares sem caminho estático dentro da janela. Nós azuis são
observações; os demais são inferências. Chamadas ainda não modelam a pilha de
retorno, e destinos indiretos ou fora da janela exigem análise adicional.
