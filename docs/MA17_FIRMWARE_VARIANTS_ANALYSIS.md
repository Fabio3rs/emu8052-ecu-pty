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
`pointer_regions.json`, `calibration_catalog_expanded.json` e
`diagnostic_tables.json`. No mapa das seis matrizes, cada célula tem tooltip
com offset, byte original, byte da variante e diferença aritmética **bruta
u8**; vermelho é aumento, azul é redução e branco é igualdade. A cor não
representa unidade física nem prova de interpretação assinada.
Os intervalos JSON são
`[start, end_exclusive)`; os
contextos mostram até oito bytes antes e depois das extremidades. A matriz
compara bytes no **mesmo offset**. Um número alto não distingue, sozinho,
recalibração de deslocamento de código ou mudança de revisão.

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
64 entradas curadas nesta revisão; elas não equivalem a 64 funções físicas
confirmadas nem esgotam os 116 alvos do diretório de ponteiros.

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

`A` e `S37` coincidem em `0x0000..0x6EAA` e diferem em 17 intervalos,
todos em `0x6EAB..0x7FEF`. O maior trecho é `0x7B45..0x7E11` (717 bytes).
Entre eles há `0x7B3E` (um byte), `0x7ED9..0x7F47` (111 bytes) e
`0x7F51..0x7F8D` (61 bytes). Esses endereços são candidatos prioritários
para rastrear `DPTR`/`MOVC`, dimensões e consumidores antes de atribuir
grandezas físicas.

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
O alinhamento dos alvos demonstra ausência de deslocamento desses 116
inícios, mas não garante equivalência dos algoritmos que os consomem.

Uma auditoria por byte encontrou 41 alvos apontados com diferenças entre
as ROMs: 36 começam em entradas curadas e cinco são subvisões cobertas
por tabelas maiores (`74F8h`, `7502h`, `7617h`, `76F8h`, `77D9h`).
Todos os bytes divergentes dessas regiões antes de `7F9Dh` estão
cobertos pelo catálogo. Os 87 bytes divergentes restantes ficam na
cauda `7F9Fh..7FFFh`, cujo intervalo candidato herdado de `7F8Dh`
inclui preenchimento e identificação, não uma tabela comprovada.
O teste `test_curated_catalog_covers_changed_pointer_data_before_rom_tail`
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
os seis inícios de `MATRICES` em `tools/compare_ma17_variants.py` e as
variantes `A`, `A+`, `S88`, `S37`, `S36`. Os mapas de calor usam a mesma
escala 0–255 para as duas ROMs; o terceiro painel mostra a diferença
**assinada** de bytes e o quarto a média bruta por linha. CSV e JSON
registram endereços e hashes, permitindo conferir a imagem com a ROM.

Em [7581h, G/S88](../build/ma17-analysis/variants/matrix_plots/matrix_7581_g_vs_s88.png),
as duas silhuetas têm a mesma forma: todas as 225 células de S88 valem
exatamente G+21. Já [7F15h, G/A](../build/ma17-analysis/variants/matrix_plots/matrix_7f15_g_vs_a.png)
mostra um platô de valores altos em G que recua na versão A; o delta
varia de −156 a +27 e 59/60 células mudam. Em
[7F15h, G/S37](../build/ma17-analysis/variants/matrix_plots/matrix_7f15_g_vs_s37.png),
o formato é ainda mais distinto: os 60 bytes S37/S36 de `7F15h`
repetem **exatamente** os 60 bytes de `7ED9h` dessas ROMs e de G;
em A/A+, as duas matrizes internas diferem em nove células, enquanto
em G/S88 diferem nas 60. Isso é evidência de convergência das duas
calibrações selecionáveis em S37/S36, não prova de qual estado é
atingido em uso normal nem de função física idêntica após o lookup.
Todos os eixos dos gráficos continuam em índices e bytes brutos.

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
e a grandeza física da saída ainda exigem análise; a orientação precisa
ser verificada separadamente nas revisões com código diferente.

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
registra 43 estruturas prioritárias com hash de cada ROM, ponteiro quando há,
intervalo, formato conhecido, consumidor na gasolina, diferenças por imagem,
evidência estática/dinâmica, confiança e perguntas abertas. Um teste confronta
endereços, hashes e contagens de diferenças diretamente com os seis dumps.
O comando de comparação também gera `calibration_catalog_expanded.json`:
43 entradas × seis versões, cada uma com endereço, hash, bytes originais
e lista das células divergentes em relação a G. Cada delta e percentual
usa aritmética de bytes *u8* brutos; percentual fica nulo quando o byte
de G é zero. Essas diferenças não pressupõem escala física ou sinal.
O gerador recusa ROM cujo tamanho, hash, ponteiro ou contagem divirja
do catálogo curado; o teste automatizado verifica uma diferença da
tabela `7426h` e um caso com denominador zero em `7D26h`.
O inventário automático registra 116 regiões apontadas, incluindo outras
candidatas ainda não curadas, sem função física atribuída. Atualmente há
**zero funções físicas confirmadas** para essas 43 estruturas; os eixos
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
O processamento posterior pode gravar `4Dh` em G, mas a origem completa
de `R5/R6` e a função física dessas curvas seguem abertas. Os deltas
entre ROMs estão no catálogo curado, e o teste
`Sab80C517.PostCoolantCurveSelectorUsesThreePointerSlots` conserva a
seleção das três curvas como regressão de leitura digital.

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
nesse perfil; não exclui outra configuração de Timer 2 em hardware.
Capturas: `post_coolant_t2i1_natural_{g,s88}/`.

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
esses dois resultados nas ROMs originais. O efeito em uma saída
temporizada permanece sem prova.
Em execução natural com 1.000 RPM, ADC2=100, ADC3=80, ADC7=63 e
1,6 milhão de ticks, G/S88 leram `7523h/7524h` (`IRAM[79h]`) e
`752Dh/752Eh` (`IRAM[7Bh]`) em 379/378 pares por curva. Nenhuma das
outras três curvas do grupo foi lida nesse cenário. O teste
`test_iram79_7b_curves_are_naturally_read_in_g_and_s88` verifica os
endereços, valores, PCs de `MOVC` e hashes das ROMs. Capturas:
`build/ma17-analysis/variants/iram79_7b_natural_{g,s88}/`.

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
explica `R1` positivo enquanto o índice permanece dentro desses blocos,
sem estabelecer o limite global de `R4`. O teste
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
o teste Python verifica a diferença uniforme. Os modos 1/2 e a
grandeza física dessas matrizes permanecem sem observação em execução
completa.

O teste isolado `Sab80C517.AlcoholCodeStartupMatrixIndexUsesBcAndUpperAe`
executa `3329h..335Dh` nas ROMs A e S37: `BCh=03h` ou `15h` com
`AEh=00h` dá linha 0 e colunas 3 ou 5; `BCh=03h`, `AEh=20h` dá linha 2,
coluna 3 e `R5=33`. Isso confirma o cálculo do índice nessas revisões,
sem estabelecer a origem natural de `AEh` nem a escala física dos eixos.

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

Outros quatro blocos de 120 bytes ficam em `7CAEh`, `7D26h`, `7D9Eh`
e `7E16h`, apontados por `70B6h`, `70B8h`, `70BAh` e `70CEh` em todas as
seis ROMs. G/S88 seleciona a base `70B6h` em `334Dh` quando `2Fh.2=1`; A/S37
usa `2Bh.7` e `2Fh.2` em `3369h..3381h` para escolher entre as bases
`7B46h`, `7BBEh`, `7CAEh` e `7D26h`. Um ensaio isolado das ROMs originais
A/S37 fixa `R5=4`, executa as quatro combinações de flags e confirma em
`53F2h` o DPTR de cada tabela e em `3381h` o byte correspondente em `R2`.
Isso demonstra a seleção e a saída digital do lookup, sem provar quando
os estados surgem naturalmente ou a função física da saída. A rotina
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
(`LJMP 00B0h`); em `S36`, contém `02 AA 0D` (`LJMP AA0Dh`). O destino
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
ligação da EPROM e da habilitação de `IEX3`; não foi ensaiado.
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
`G+16h` (módulo 256), enquanto S88 vale `G+08h`. Ao fornecer somente
os retornos `MOVC` dessa matriz S37 à ROM G intacta, com os mesmos ADC
do fatorial acima, houve 912 leituras da região em cada rotação:

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

### Sinal ADC5 e estado observado da correção lambda

No scanner `Monomotronic-MA1.7-Scanner`, `SensorDecoders.cpp` define
três leituras distintas: comando `00h`, ID `65h` para sonda (`raw × 3,9`
mV); seletor `F8h`, ID `0Ch` para integrador (`(raw−128) × 0,195` %);
e seletor `F8h`, ID `6Ch` para correção de longo prazo
(`int8(raw) × 0,39` %). `SensorCategory.h` apenas agrupa esses campos na
interface. As três escalas são convenções do scanner; em particular, o
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
não separa o integrador lambda de possíveis caminhos paralelos até CC3.

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
O integrador só saiu de `80h` abaixo de `6Eh` ou a partir de `9Ah`
nessa janela; isso não valida tensão física de comutação da sonda.
O teste `test_lambda_adc5_thresholds_and_neutral_intervals` verifica
os seis pares de fronteira. Traces:
`build/ma17-analysis/variants/lambda_adc5_sweep_20261114/`.

O byte `F8:0Ch` é escrito em `19D0h..19D2h` a partir do estado interno
calculado em `R6:R7`/`5Dh:5Ch`. Um rastreio opcional de `MOVX` para esse
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
integrador. O nome físico do byte vem do scanner; falta validação em
ECU real.

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
motor, mas sua descrição ainda é hipótese física. As quatro triplas
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
aberta nem atribuir a diferença de CC3 exclusivamente ao integrador.
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

`3DC1h` seleciona `7925h` sob a guarda de `28h.1/.2` e `2Fh.0`,
gravando o resultado em `RAM[6Eh]` em `3DC7h`. O código em `1773h`
leva `6Eh` a `R4`; `184Dh/1854h` usa esse valor numa operação de
16 bits antes de `199Ah` atualizar `RAM[5Dh:5Ch]`. Em `3E14h..3E2Eh`,
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
no resultado interno**; ainda falta alcançar `7Ah≠0` num boot natural
e medir se o efeito prossegue até uma saída modelada.

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
`7EACh..7EBAh` conserva os 15 bytes G em S88, mas A/A+/S37/S36
substituem todos por `99h`. Na família de código A, `3384h` seleciona
`70BEh` quando `RAM[2Bh].7=1`, senão `70BCh`; `R7` fornece o índice.
Um teste com opcodes originais das quatro ROMs A, `R7=4`, `R6=0` e
`T2CON.1=0`, alcançou `MOVC` em `53F2h`: com flag limpa leu
`7E9Dh+4=94h`; com flag ativa leu `7EACh+4=99h`. O valor chegou a
`R2` e à upper IRAM `A4h`. Isso comprova a seleção e o destino interno
nesse estado isolado. A origem natural da flag, o significado físico
de `A4h` e a seleção durante um boot A com hardware correto permanecem
em aberto. No caminho G inspecionado em `335Fh`, `DPTR=70BCh` é
sobrescrito em `3371h`; o ponteiro, por si só, não comprova uma leitura.

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
família A, com `DPTR=702Ah`, `RAM[57h]=0`, `R5=R6=R2=0`.
`MOVC` leu `746Ch` e a escrita final em `4Dh` foi `0Fh` nas quatro
ROMs com bytes G ou `29h` em A/A+. Esse teste começa **após** as
guardas de `22h.4`, upper IRAM `A5h` e seleção entre grupos;
portanto, não demonstra que o primeiro byte seja lido em operação
natural. O efeito físico da diferença permanece desconhecido.

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
em P5.3; a pinagem física do atuador continua sem confirmação.

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

O `tools/roundtrip_8051.py` remontou `A`, `S88`, `S37` e `S36`: 32768 bytes,
zero divergências e SHA-256 igual ao original em todos os casos. O perfil de
SFR específico do Fiat só é aplicado ao hash de `G`; os outros desmontam
com avisos para `91h` e `B1h`, que precisam de confirmação por revisão.
A remontagem prova fidelidade dos bytes, não acerto de todas as classificações
estáticas. `G` permanece coberto pelo teste de regressão existente.

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
