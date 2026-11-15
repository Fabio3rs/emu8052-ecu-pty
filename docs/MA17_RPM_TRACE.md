# Inventário de rotação — Fiat Tipo MA1.7, ROM G

Este inventário usa o [assembly modular](../build/ma17-analysis/modular/)
e o [catálogo de calibrações](MA17_CALIBRATION_CATALOG.json). Endereços são
offsets da ROM G; as outras cinco imagens têm deslocamentos de código e
devem ser consultadas pelo ponteiro, não pelo mesmo PC. `47h × 25 RPM` é a
escala observada no scanner e confirmada nos estímulos abaixo; a grandeza
física de outras variáveis e a ligação dos pinos ainda exigem medição.

## Origem, estado e comparações

| Item | Trace de dados ou comparação | Evidência / interpretação |
| --- | --- | --- |
| Roda 60-2 → `RAM[47h]` | `IEX3` 0053h→00B0h, captura Timer 2; cálculo chega a 0EA5h e escrita termina em 0EA7h | `47h` passou de `00h` a `20h`, `22h`, `24h` com estímulos de 800, 850 e 900 RPM. O firmware zera `47h` em 0871h no boot. |
| Falta de RPM | 4AA2h testa `47h=0`; 4AB7h volta a 0850h | Caminho de reinicialização do laço, não reset físico da CPU. |
| Curva candidata a referência | `7002h→73D4h` segmenta `RAM[63h]` em índice `R5` e fração `R6`; `700Ah→74A8h` é lida em 532Fh/5333h; 48E9h chama interpolador e 48FFh grava `R2` em `46h` | Em `RAM[63h]=04h`, `74A8h=22h`; pela escala do scanner, 850 RPM. `63h` veio de ADC3 no perfil emulado, mas a escala de temperatura não foi medida. |
| Piso condicionado por P4.7 | 48ECh testa P4.7; com `T2I1=0`, lê `ROM[7200h+76h+RAM57h]`, compara com `R2` e guarda o maior em `46h` | Com `RAM57h=0`, `ROM[7276h]=25h` = 925 RPM na escala do scanner. A fonte elétrica de P4.7 é desconhecida. |
| Comparação direta | 32E6h: `MOV A,46h; SUBB A,47h`; se `46h<47h`, usa `ROM[7300h+4Eh]` como margem adicional e testa outra vez | É um comparador de valor derivado de tabela com rotação medida. O efeito físico do ramo ainda precisa ser rastreado. |
| Guarda de posição | 2307h lê `46h`; o resultado controla 231Ch (`CLR 20h.3`) e a guarda 23AFh que precede 23B9h | Intervenção apenas na leitura de 2307h resgatou o ramo; não foi observada mudança física do atuador de lenta. |
| Limiar de regime | 4095h..40D6h compara `47h` com `50h` (2.000 RPM pela escala do scanner), junto de `63h`, `70h`, flags e XRAM F8:88h | Teste de fronteiras dos opcodes originais; a função das flags segue aberta. |
| Limiar condicionado por temperatura | `7068h→7952h` parte de `63h`; em 1282h o resultado é comparado com `47h` | Trocar só o retorno MOVC em 532Fh/7956h de `10h` para `80h` inverteu o ramo em 33 passagens. |
| Outros limites de RPM | `ROM[7226h:7228h]=44h,2Ch` participa da guarda lambda secundária; 3E06h usa constante ROM contra `47h` | 1.700/1.100 RPM são conversões nominais, não metas de marcha lenta. A semântica do caminho lambda continua candidata. |

## Tabelas com eixo RPM ou valor derivado de RPM

| Diretório → ROM | Estrutura e consumidor observado |
| --- | --- |
| `7046h→7570h` | Segmentador de 15 posições com cabeçalho `47h`; fornece coluna a matrizes `7581h`, `7662h`, `7743h` e índice superior `BCh`. |
| `7048h/704Ah/704Ch→7581h/7662h/7743h` | Três matrizes 15×15 com eixo de RPM e outro eixo associado a `6Fh`. `7581h`/`7662h` têm rota digital até `48h`, `14h:15h` e agendador CC3; identidade física da saída pendente. |
| `7056h→782Bh` | Segmentador de 4 posições, cabeçalho `47h`; coluna das matrizes 5×4 abaixo. |
| `705A/705C/7060/7062/7080/7084/7064/7066/70D0h` | Matrizes 5×4 em `7831/7859/78FD/7911/7895/78BD/7925/7939/786Dh`; cruzam segmento de `70h` com segmento de RPM. Resultados observados incluem RAM superior `B1h`, RAM `58h`, `5Bh` e XRAM F8:01h. `70h` é candidato TPS, sem escala física confirmada. |
| `705Eh→78F9h` | Curva derivada do segmento de RPM de `782Bh`; altera `25h.3` em caminho testado. |
| `706Ah→7958h` | Curva com cabeçalho `47h`; intervenção MOVC mudou `59h` e três larguras iniciais do P1.3/CC3 modelado a 1.000 RPM. |
| `7090h→7992h`, `7092h→799Eh` | Segmentador de 10 posições com cabeçalho `47h` e curva de limite; o resultado chega à guarda `2Fh.2`/correção lambda em caminho observado. Função física por confirmar. |
| `709Ah→79A8h`, `70D6h→79C4h` | Curvas de RPM com cabeçalho `47h`; a primeira chega a XRAM F8:A3h e a segunda a XRAM F8:E1h em ensaios catalogados. |
| `70AAh→7B32h` | Segmentador de 10 posições, cabeçalho `47h`; coluna das matrizes 6×10 `7ED9h`, `7F15h`, `7F51h`, com resultado em `31h`. A cadeia `31h→Timer 1→P5.0/1` foi observada. |
| `70DEh→79E8h` | Segmentador de RPM em seis faixas; participa da seleção das curvas `79F0h`, `7A20h`, `7A50h`, `7A80h`, `7AB0h`. |
| `709Ch/709Eh/70A0h→7B46h/7BBEh/7C36h` | Matrizes 8×15; índice de coluna ligado ao segmento `7570h`. `7B46h` tem intervenção causal até `69h` e timing CC3 no emulador; outras seleções exigem rastreio. |
| `70B6h/70B8h/70BAh/70CEh→7CAEh/7D26h/7D9Eh/7E16h` | Matrizes 8×15 também usam o índice superior `BCh` derivado do segmentador de RPM; o outro eixo varia por caminho. Não atribuir todas ao mesmo atuador. |
| `70C2h→7ECAh` | Tabela de 15 bytes indexada pelo segmento de `47h`/`BCh`. |

As seis curvas que escrevem **`46h`** são separadas das tabelas cujo eixo é
RPM: `700A/700C/700E/7010/7012/7014h` apontam, respectivamente, para
`74A8/74B2/74BC/74C6/74D0/74DAh`. O seletor usa `T2CON.1` e `RAM57h`;
o índice vem de `63h`, não de `47h`. Os seis blocos são idênticos nas seis
ROMs catalogadas. Só o primeiro foi observado no boot G aqui; os demais
foram exercitados com estados de registradores preparados.

### Comparação de bytes entre as seis imagens catalogadas

Contagem de células diferentes em relação à G, obtida dos campos
`different_bytes_vs_G` do catálogo; não é uma comparação de execução.

| Estrutura | A / A+ | S88 | S37 / S36 |
| --- | ---: | ---: | ---: |
| Referência `74A8h` (10 bytes) | 0 / 0 | 0 | 0 / 0 |
| Segmento RPM `7570h` (15 bytes) | 0 / 0 | 1 | 1 / 1 |
| Segmentos RPM `782Bh`, `7B32h`, `7992h`, `79E8h` | 0 / 0 | 0 | 0 / 0 |
| Matriz `7581h` (225 bytes) | 0 / 0 | 225 | 225 / 225 |
| Matriz `7662h` (225 bytes) | 209 / 209 | 211 | 223 / 223 |
| Matriz `7B46h` (120 bytes) | 0 / 0 | 120 | 120 / 120 |
| Matriz `7ED9h` (60 bytes) | 60 / 60 | 0 | 0 / 0 |
| Matriz `7895h` (20 bytes) | 20 / 20 | 0 | 0 / 0 |
| Matriz `7939h` (20 bytes) | 5 / 5 | 0 | 0 / 0 |

As famílias A e S diferem nas calibrações e nas revisões de código; os
ensaios de boot completo acima são **somente da G**. Igualdade dos bytes
de uma curva não comprova igualdade de seleção ou de efeito no hardware.

## Sweep reproduzido

`python3 tools/trace_ma17.py --firmware FiatTipo_MA17_dump_27c256.bin
--no-kline-inject --crank-immediate --rpm 850 --trace-movc
--stop-ticks 1200000 --seconds 20 --output-dir build/ma17-analysis/rpm-850`

O sweep usou ADC0..7=`120,130,100,4,90,40,95,63`, `MA17_TRACE_RAM46_TABLE=1`,
sem K-Line. O segundo estado adicionou `MA17_P4_7_FORCE_LOW=1`, que é um
estímulo elétrico **experimental**; os seis relatórios estão em
`build/ma17-analysis/rpm-target-trace/`. Valor em `46h` vem da última linha
`[RAM46-TABLE] PC=48FF`; `47h` vem de `rpm_observation.ram47_changes`.

| RPM injetado | `47h` medido | `46h`, P4.7 padrão | `46h`, P4.7 baixo | `46h−47h` padrão/baixo |
| ---: | ---: | ---: | ---: | ---: |
| 800 | `20h` | `25h` | `22h` | +5 / +2 (125 / 50 RPM nominais) |
| 850 | `22h` | `25h` | `22h` | +3 / 0 (75 / 0 RPM nominais) |
| 900 | `24h` | `25h` | `22h` | +1 / −2 (25 / −50 RPM nominais) |

O teste existente `test_74a8_movc_and_p47_gate_ram46_in_g` troca só a leitura
MOVC de `74A8h` por `42h` e confirma `46h=42h` nos dois estados de P4.7,
preservando hash e bytes da ROM. Assim, a propagação tabela→`46h` está
comprovada no emulador. **Não está comprovado** que 850 RPM seja o alvo real
com motor quente: ADC3=4 não foi calibrado em temperatura, P4.7 não foi
medido na placa e `46h` participa de mais de uma guarda.

### Pedido de ar-condicionado como hipótese operacional

O usuário relata que a ECU eleva um pouco a lenta quando o A/C é pedido.
No estado G ensaiado, `P4.7=1` aplica o piso `ROM[7276h]=25h` ao valor
`22h` da curva; a diferença é **75 RPM nominais**. Para `RAM57h=1/2`,
os pisos adjacentes `ROM[7277h/7278h]=2Eh/30h` são 1.150/1.200 RPM
nominais, mas a seleção natural desses estados não foi observada.
O mesmo P4.7 participa de `21D4h..220Fh`, uma lógica que escreve P5.3
sob outras guardas. Essa coincidência torna P4.7 um candidato a sinal
relacionado ao A/C, **sem identificar** pedido, autorização da embreagem,
polaridade ou pino físico. Nos boots testados, `22h.5` bloqueou a saída
P5.3; nenhum ensaio comprovou aumento da rotação física ou movimento
do batente causado pelo piso de `46h`.

No par G a 850 RPM/2,4 milhões de ticks, com ADC0..7 fixos em
`40,130,100,4,90,40,95,63`, apenas o estímulo experimental P4.7 mudou:
`RAM[46h]` foi `25h` no estado padrão e `22h` com P4.7 baixo; `47h`
ficou `22h` em ambos. Em 230 passagens por `2211h` após a escrita, por braço,
`22h.5` ficou ligado e o latch `P5.3` alto. O teste
`test_p47_floor_at_850_rpm_is_masked_at_p53_output` reproduz o contraste;
relatórios em `build/ma17-analysis/variants/ac_candidate_850/`.

## Hipótese de recuo do atuador de lenta

A sequência física informada pelo usuário é: interruptor no batente,
TPS em faixa válida e rotação fora da referência. No firmware há uma
cadeia compatível com **parte** desse controle, mas ainda faltam as
associações elétricas:

1. `48E9h..48FFh` obtém `46h` da curva e do piso condicionado por P4.7.
2. `22AAh`, `2307h` e `2391h..23AFh` comparam `46h` e `47h` com margens
   lidas por `MOVC` da base `7300h`; `23AFh` combina também `28h.1`,
   `24h.4`, `20h.3`, `2Dh.4`, `2Eh.0`, `F1` e outras guardas.
3. Quando a guarda permite, `2378h` lê XRAM `F8:3Dh` em `R4`, o bloco
   `23CEh..2490h` pode aumentar ou diminuir esse valor e `2494h` o grava.
   O scanner o chama de posição de lenta, ainda como hipótese.

No boot G com TPS lógico ADC0/6=40/95 e ADC3=4, `23AFh` ficou bloqueado
por `20h.3=1`, `24h.4=0` e `2Dh.4=0`; reduzir só a entrada de
temperatura não moveu `F8:3Dh`. Em outro ensaio com TPS 120/180,
ADC3=4 e P4.6 baixo **experimentalmente** após 12,2 milhões de ticks,
a guarda abriu, mas `R4=R5=07h` não pediu mudança. Intervenções isoladas
em `R4` para `05h` ou `09h` fizeram o código original gravar
`07h→06h` ou `07h→08h` em `F8:3Dh`, respectivamente. Isso confirma
passos digitais em duas direções, sem identificar qual recua o motor.

Ainda não foi localizado o pino do interruptor de batente, nem demonstrado
que uma flag específica represente esse interruptor ou a faixa válida das
duas pistas TPS. A direção da ponte H e o movimento físico do atuador
também permanecem sem medição. Consulte os rastros e testes de
`idle_position_*` em [MA17_SEMANTIC_INVENTORY.md](MA17_SEMANTIC_INVENTORY.md).
O cut-off de desaceleração conhecido desta ECU ocorre acima de 1.500 RPM
com o interruptor de lenta pressionado; TPS baixo isolado não satisfaz
essa condição. O bloqueio digital de CC3 observado perto de 1.425 RPM
não estabelece o limiar físico do corte do bico.
O teste experimental de P4.3 baixo está documentado em
[MA17_FIRMWARE_VARIANTS_ANALYSIS.md](MA17_FIRMWARE_VARIANTS_ANALYSIS.md),
sem associar ainda esse bit ao contato físico.

## Sinais da CPU por posição da roda 60−2

O trace Fiat G a 850 RPM agora pode marcar cada passagem pelo dente 0 com
`MA17_TRACE_CRANK_PHASE=1`. O gráfico usa três marcas consecutivas para
alinhar duas voltas de 360° e mostra P5.0, P5.1, P1.1 e a saída modelada
de CC3 em uma janela de 720°:

`build/ma17-analysis/crank-phase-850-sensors/pins_720deg.png`

No estado testado (ADC0..7 em 10 bits = 480,520,400,16,360,160,380,252;
P4.7 forçado baixo experimentalmente), os pulsos baixos de **P5.0**
começaram a ~102,6° e ~462,6°; os de **P5.1** a ~282,6° e ~642,6°.
São alternados por 180° e repetem a cada volta. **P5.0 e P5.1 são
provavelmente sinais de controle do sistema de ignição interno da ECU**,
compatíveis com duas bobinas wasted spark. Essa função **ainda não foi
confirmada fisicamente** no chicote ou estágio de potência; os nomes no
gráfico são pinos/latches modelados da CPU, não pinos do conector. CC3
teve quatro pulsos baixos, aproximadamente a 111,7°, 291,7°, 471,7° e
651,7°, mas sua função elétrica também permanece não identificada.
O sinal P1.1 teve outro padrão e não recebeu atribuição física.
As bordas baixas de P5.0 vieram de `00A6h` e as altas de `0096h`;
para P5.1, de `00ABh` e `009Eh`, respectivamente. O início baixo
de CC3 ocorreu após `05D3h` no modelo de captura/compare.

A roda 60−2 informa ângulo de virabrequim módulo 360°; como a ECU usa
wasted spark e não tem referência de comando, as duas metades de 720°
são apresentadas apenas para observar a repetição em um motor 4T.

Reprodução do trace e gráfico (firmware Fiat G; valores ADC acima):

```sh
MA17_TRACE_CRANK_PHASE=1 MA17_P4_7_FORCE_LOW=1 \
MA17_ADC10_CH0=480 MA17_ADC10_CH1=520 MA17_ADC10_CH2=400 \
MA17_ADC10_CH3=16 MA17_ADC10_CH4=360 MA17_ADC10_CH5=160 \
MA17_ADC10_CH6=380 MA17_ADC10_CH7=252 \
/usr/bin/python3 tools/trace_ma17.py --crank-immediate --no-kline-inject \
  --rpm 850 --stop-ticks 800000 --seconds 45 \
  --output-dir build/ma17-analysis/crank-phase-850-sensors
/usr/bin/python3 tools/plot_ma17_crank_pins.py \
  build/ma17-analysis/crank-phase-850-sensors/emulator-trace.log \
  --output build/ma17-analysis/crank-phase-850-sensors/pins_720deg.png
```

O comando salva também CSV com tempos, ângulos e bordas, e JSON com
referências e contagens. A saída de CC3 depende do estado dos sensores;
uma janela sem eventos de CC3 não demonstra ausência desse sinal.
