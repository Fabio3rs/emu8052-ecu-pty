# Investigação do déficit de potência ROM MA1.7 × planta SEVEL

Estado: concluída (goal CURVES_STUDY). Números das tabelas vêm de `docs/dyno/investigation/*.csv`
via `tools/power_gap_report.py`; nada foi digitado à mão. Nada foi enviado ao remoto.

## A. Resumo executivo

O déficit entre a planta isolada (60,07 kW a 6000 RPM) e a ROM (39,21 kW) é de 20,9 kW (34,7 %);
a 3000 RPM é de 9,5 kW (23,3 %). Ele **não** vem de uma estratégia de redução de potência da ROM.
Quatro causas, todas medidas por intervenção isolada (Tabela 2):

1. **Bomba-d'água (erro de extrapolação do modelo, dominante acima de 4000 RPM).** O modelo F-45
   usa torque ∝ ω² com 0,5 N·m a 925 RPM de virabrequim; a potência cresce com ω³ e chega a
   ~13 kW (21 N·m) a 6000 RPM. É irreal para uma bomba automotiva (ordem de 0,3–1 kW). Desligar a
   bomba recupera 13,3 kW; uma bomba hipotética 25x mais fraca (x0,04, 1,2 N·m a 6000 RPM) recupera
   12,8 kW. O alternador (0,36 N·m a 6000 RPM) é irrelevante (0,3 kW).
2. **Força de centelha escala o torque do pulso (inconsistência interna, ~4–5 kW).** `Combustion::spark`
   queima o combustível inteiro quando a carga relativa da bobina é ≥ 0,8, mas multiplica o torque
   do pulso por `min(1, força)`. A ROM carrega a bobina por ~1,8 ms (força média 0,905–0,932, vem de
   dwell/2 ms), perdendo 7–10 % de torque indicado; a planta isolada usa força 1,0.
3. **Temperatura do ar de admissão (cenário, ~1–3 kW).** A ROM roda com ar de admissão aquecido
   (35–37 °C no ponto medido, contra 20 °C na planta isolada). É diferença física legítima do cenário.
4. **Avanço da ROM abaixo do MBT estimado (~1 kW).** A ROM avança 7–13° a menos que o MBT da planta, mas
   a função f_advance é suave (k = 3,5e-4): forçar MBT dá só +0,9 a +1,3 kW. O MBT é estimativa
   do modelo, não referência absoluta.

Fechamento: ROM com bomba x0,04, força saturada e avanço = MBT atinge 97,1 / 99,4 / 100,4 / 99,6 %
da planta isolada a 36 °C em 1500 / 3000 / 4500 / 6000 RPM (Tabela 3). O déficit está explicado;
nenhuma autoadaptação ou proteção da ROM foi necessária (e nenhuma foi demonstrada).

Nenhum parâmetro foi alterado: as intervenções são flags `--exp` desligadas por padrão e a ROM original
reproduz bit a bit os pontos de `docs/dyno/rom/sweep_tdc120.csv` (31,3103 kW a 3000 RPM).

## B. Metodologia

- Código: base `d55bb67` + working tree com as flags `--exp` (manifest dos CSVs registra o SHA e `code_dirty=True`).
- ROM: `FiatTipo_MA17_dump_27c256.bin` (imagem G), SHA-256 `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`, nunca modificada.
- Cenário: E22, borboleta 90° (pedal 40,27 mm), vazamento 9 mm², acessórios ligados, água 90 °C, PMS 120°,
  `--dyno-scenario`; 40 ciclos de medição, estabilização ±2 % por 1 s, critérios da bancada (±1 % RPM,
  freio sem saturar, |ΔE_cin|/W_freio < 1 %, resíduo < 0,5 %). Todos os pontos: ACCEPTED.
- Intervenções (`--exp chave=valor`, padrão = original): `acc_alt_scale`, `acc_pump_scale`, `adv_force_mbt`,
  `adv_offset_deg` (eficiência avaliada no MBT + deslocamento; **a posição angular do pulso não muda**),
  `spark_torque_saturate` (torque do pulso proporcional a `burn_fraction` em vez da força bruta),
  `dyno_settle_ticks` (tempo de marcha lenta livre). A instrumentação adicional (VE, ar/cilindro, MBT, eta,
  resíduo, força de centelha, IRAM 66h/47h/61h/65h, XRAM F8E8) só acrescenta campos ao JSON.
- Planta isolada: `sevel-dyno` com as mesmas condições, ambiente 20 e 36 °C (`tools/power_gap_isolated.sh`).
  A planta isolada **não inclui acessórios**; a de 36 °C aproxima o ar de admissão medido na ROM
  (35–37 °C) e é uma comparação aproximada.
- Limitações: 4 pontos de RPM (1500/3000/4500/6000); parcelas de uma variável por vez não somam
  exatamente o total (residual, Tabela 2); bomba x0,04 é hipótese ilustrativa, não medida.
- Reprodução: `python3 tools/power_gap_matrix.py build/emu8051-tty FiatTipo_MA17_dump_27c256.bin --out docs/dyno/investigation/matrix.csv`
  e `python3 tools/power_gap_report.py`.

## C. Decomposição energética

### Tabela 1 - isolada (sem ROM) contra ROM, potencia de eixo

| RPM | isolada 20 C [kW] | isolada 36 C [kW] | ROM original [kW] | deficit total [kW] | deficit [%] |
|---:|---:|---:|---:|---:|---:|
| 1500 | 19.74 | 18.61 | 14.81 | 4.93 | 25.0 |
| 3000 | 40.80 | 38.54 | 31.31 | 9.49 | 23.3 |
| 4500 | 56.75 | 53.75 | 42.43 | 14.32 | 25.2 |
| 6000 | 60.07 | 58.41 | 39.21 | 20.86 | 34.7 |

### Tabela 2 - decomposicao por intervencao isolada a partir da ROM original (kW)

Cada coluna e o ganho de potencia ao aplicar UMA intervencao sobre a ROM original. 'Residual' = deficit total - soma das parcelas (interacoes e efeitos nao isolados).

| RPM | ar de admissao 20->36 C | bomba x0,04 (hip.) | alternador off | forca centelha saturada | avanco = MBT | soma | residual |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1500 | 1.13 | 0.17 | 0.23 | 1.78 | 1.18 | 4.50 | 0.43 |
| 3000 | 2.26 | 1.57 | 0.24 | 4.18 | 1.12 | 9.38 | 0.11 |
| 4500 | 3.00 | 5.33 | 0.14 | 5.05 | 0.91 | 14.43 | -0.10 |
| 6000 | 1.66 | 12.76 | 0.31 | 5.15 | 1.32 | 21.21 | -0.35 |

### Tabela 3 - fechamento: ROM com bomba x0,04 + forca saturada + avanco MBT contra isolada a 36 C

| RPM | ROM combinada [kW] | isolada 36 C [kW] | razao |
|---:|---:|---:|---:|
| 1500 | 18.07 | 18.61 | 97.1 % |
| 3000 | 38.32 | 38.54 | 99.4 % |
| 4500 | 53.96 | 53.75 | 100.4 % |
| 6000 | 58.20 | 58.41 | 99.6 % |

### Tabela 4 - acessorios (torque medio no virabrequim, N.m)

| RPM | modelo atual | alternador off | bomba off | ambos off | bomba x0,04 |
|---:|---:|---:|---:|---:|---:|
| 1500 | 2.76 | 1.31 | 1.45 | 0.00 | 1.50 |
| 3000 | 5.98 | 5.26 | 0.72 | 0.00 | 0.93 |
| 4500 | 12.33 | 11.85 | 0.48 | 0.00 | 0.96 |
| 6000 | 21.40 | 21.04 | 0.36 | 0.00 | 1.20 |

### Tabela 5 - estado da ROM e mistura (original)

| RPM | avanco ROM [graus] | MBT planta [graus] | forca centelha media | eta_i | VE amb. | ar [mg/cil] | lambda | IRAM66 TPS1 | XRAM F8E8 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1500 | 7.12 | 20.46 | 0.909 | 0.3350 | 0.8403 | 394.4 | 0.9995 | 238 | 5 |
| 3000 | 18.56 | 27.36 | 0.905 | 0.3454 | 0.9109 | 427.6 | 1.0052 | 238 | 6 |
| 4500 | 25.58 | 32.38 | 0.921 | 0.3455 | 0.9009 | 422.9 | 1.0004 | 238 | 6 |
| 6000 | 29.35 | 36.35 | 0.932 | 0.3420 | 0.7939 | 372.6 | 0.9959 | 238 | 6 |

### Tabela 6 - historico (tempo de marcha lenta livre antes do degrau de pedal)

| RPM | 6 M ticks [kW] | 12 M (padrao) [kW] | 24 M [kW] | avanco 6M / 12M / 24M [graus] | XRAM F8E8 6M / 12M / 24M |
|---:|---:|---:|---:|---:|---:|
| 1500 | 14.89 | 14.81 | 14.81 | 7.16 / 7.12 / 7.13 | 7 / 5 / 2 |
| 3000 | 31.38 | 31.31 | 31.23 | 18.56 / 18.56 / 18.57 | 8 / 6 / 2 |
| 4500 | 42.55 | 42.43 | 42.28 | 25.63 / 25.58 / 25.56 | 8 / 6 / 2 |
| 6000 | 39.22 | 39.21 | 39.20 | 29.42 / 29.35 / 29.34 | 8 / 6 / 2 |

### Tabela 7 - sensibilidade ao avanco (retardo a partir do MBT, kW)

| RPM | original | MBT | MBT-5 | MBT-10 |
|---:|---:|---:|---:|---:|
| 1500 | 14.81 | 15.99 | 15.82 | 15.32 |
| 3000 | 31.31 | 32.43 | 32.10 | 31.02 |
| 4500 | 42.43 | 43.33 | 42.80 | 41.22 |
| 6000 | 39.21 | 40.54 | 39.91 | 38.02 |

## D. Hipóteses investigadas

| Hipótese | Motivação | Experimento | Resultado | Interpretação | Confiança | Estado |
|---|---|---|---|---|---|---|
| Acessórios consomem 13 kW a 6000 RPM por erro de modelo | 21,4 N·m a 6000 RPM é incompatível com hardware real | Alternador off, bomba off, ambos off, bomba x0,04 | Bomba responde por 21,0 de 21,4 N·m; bomba off +13,3 kW, x0,04 +12,8 kW; alternador off +0,3 kW | Extrapolação de ω² de uma referência a 925 RPM; usuário também considerou 13 kW exagerado | Alta (causal, medido) | Confirmada |
| Alternador mal dimensionado | Alternador é a carga clássica | Escala 0 e fórmula; 13,8–14,4 V (14,0 V no modelo) | 0,36 N·m a 6000 RPM; a tensão 13,8–14,4 V muda < 3 % disso | Irrelevante para o déficit. Nota: a fórmula divide por `alternator_ratio`, o torque no virabrequim fica metade de P/(η·ω); mesmo corrigida, < 1 N·m | Alta | Refutada como causa do déficit |
| Torque do pulso escalado pela força da bobina | Indicado ROM menor que o esperado só por ar e avanço | `spark_torque_saturate`; força média medida 0,905–0,932 | +4,2 kW (3000) a +5,2 kW (6000); indicado 125,6 → 138,9 N·m a 3000 | Torque proporcional à carga da bobina enquanto a queima já é total acima de 0,8; força = dwell/2 ms, sem tensão nem saturação de corrente | Média-alta (efeito medido; a lei física correta é desconhecida) | Confirmada como inconsistência de implementação |
| ROM avança menos que o MBT | 18,6° contra 27,4° a 3000 RPM | Eficiência avaliada no MBT, MBT-5, MBT-10 | +0,9 a +1,3 kW; retardo de 10° custa ~1,4 kW a 3000 | Parcela pequena; MBT é estimativa do modelo | Média | Parcialmente sustentada (pequena) |
| Diferença de ar admitido | VE 0,911 contra 0,949 a 3000 | Planta isolada a 20 e 36 °C | 36 °C reproduz ar (423 contra 428 mg/cil) | Ar de admissão aquecido na ROM; diferença de cenário | Média-alta | Confirmada |
| Mistura pobre/rica ou WOT sem enriquecimento | λ ROM ≈ 1,00 em toda a varredura | Leitura de λ, ar e combustível | λ 0,996–1,005; planta isolada também usa λ = 1; eta_i quase igual | Não é parcela do déficit com este modelo; ausência de enriquecimento de plena carga na ROM **não** foi avaliada | Média | Inconclusiva quanto à estratégia da ROM; refutada como causa do déficit |
| Histórico de funcionamento (adaptação) | Hipótese do proprietário | Marcha lenta livre de 6 M, 12 M, 24 M ticks | Potência varia < 0,6 %, avanço < 0,1°; XRAM F8E8 (contador de tabela lambda) varia 2–8 | Há estado de ROM que muda com o tempo, sem efeito mensurável na potência | Média (3 históricos, 4 RPM) | Refutada para este ponto |
| Bancada/freio perturba a ROM | Oscilação de RPM | Critérios de aceitação, resíduo de energia | Todos ACCEPTED; resíduo ~1e-13; saturação 0 | Medição consistente | Alta | Refutada |
| ROM não reconhece plena carga (TPS2 < F0h) | Avanço 7–13° abaixo do MBT; limiar F0h em `1047h` | IRAM 60h forçado a 5 V a partir do degrau de pedal | 6Dh.0 liga; avanço +5,6 a +8,0°; potência +0,2 a +1,1 kW | O modelo de TPS não alcança o limiar de 4,71 V a 90°; o recurso existe na ROM | Média-alta (cadeia medida; semântica do bit hipotética) | Confirmada (efeito), semântica em aberto |
| Sensores de temperatura (água × ar) invertidos | Pedido do proprietário | DTC transmitido na K-line com aberto/curto em ADC2 e ADC3; limites e limiares | ADC3 → 0A02, ADC2 → 0B02; limiares coerentes | Atribuição consistente com a ROM e com o carro real (ar desligado → 0B02, informado pelo proprietário) | Alta | Refutada |
| Dependência de TPS parcial/histórico térmico | Fase 4 | Pedal 30–100 %; água 60/75/105 °C; sonda forçada; reinícios mornos | Ver tabelas P1, P3, P4, P5 | Sem enriquecimento nem adaptação que reduza potência; anomalia de estol a 75 °C | Média | Inconclusiva na parte térmica |
| PMS assumido altera o avanço | PMS não confirmado | Varredura 117/120/123 (GOAL_DYNO_ROM) | Já documentada: picos 42,4–44,3 kW | Resposta ao PMS assumido, não determina o PMS físico | Média | Inconclusiva |

## E. Comportamento adaptativo da ROM

Reproduzir: `python3 tools/power_gap_phase4.py ...`, `python3 tools/ntc_fault_probe.py ...`,
`python3 tools/power_gap_phase4_report.py`; teste `PhysicalDiagnostics.NtcSensorIdentity`.

### E.1 Confirmado no assembly (ROM Fiat G, `FiatTipo_MA17_dump_27c256.asm` e `asm/ma17/semantic_labels.tsv`)

- `1047h` (`process_tps_tracks_60_66_to_derived_70`): lê IRAM 60h (TPS trilha 2, ADC0) em R2 e IRAM 66h (trilha 1, ADC6) em R4.
  Em `CJNE R2,#F0h` / `JC`, se **IRAM 60h >= F0h** (4,71 V) liga `B.7`, `PSW.5` e `IRAM 6Dh.0`; R4 é comparado com `FAh` e `07h`.
  O bit 0 de IRAM 6Dh é lido de volta em `109Ah` (`JBC ACC.0`). Esse é o único teste de "TPS muito aberto" encontrado; a
  semântica ("plena carga") é hipótese, não nome demonstrado.
- `0721h` (`route_adc_sample_to_iram_or_upper_a8`): a amostra do canal que alimenta IRAM 62h fora de 04h..F7h é substituída por 79h
  e liga `28h.7/.6`; a do canal 63h vai para a IRAM superior A8h, sem substituto.
- Limiares por sensor: `ROM[721Dh]=27h` comparado com IRAM 63h (`3D01h`, seletor de matriz `2Fh.2`), `63h<1Ah` em `4095h`
  (habilitações de R4/R2), `ROM[72BDh]=7Ch` comparado com IRAM 62h (`47F1h`). Os de 63h ficam na faixa quente do NTC de água
  (valor baixo = quente: 19 a 90 °C), o de 62h na faixa ambiente (114 a 24 °C).
- Memória de falhas: XRAM F84Eh..F850h (24 bits), contadores F851h..F85Bh (confirma a falha ao chegar a 0Ah), tabela de
  registros em `6E27h` (3 bytes por falha) copiada para XRAM CDh..CFh, `515Bh` apaga F84Eh..F860h por comando 05h.
- Não foi encontrada rotina de autoaprendizado de TPS mínimo/máximo nem adaptação de combustível que dependa do tempo
  de funcionamento, além do contador de limite da tabela lambda (XRAM F8E8h) e das posições do inventário
  (correção de longo prazo, aditivo de marcha lenta). Busca textual no assembly, não varredura semântica completa.

### E.2 Observado na execução

### Tabela P1 - abertura de pedal (fracao do curso 40,27 mm = 90 graus), freio mantendo a rotacao

| RPM | pedal | borboleta [rad] | IRAM 60h (TPS2) | IRAM 66h (TPS1) | potencia [kW] | avanco [graus] | lambda | injecao [mg] |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3000 | 0.3 | 0.443 | 36 | 238 | 5.27 | 28.52 | 0.9965 | 2108 |
| 3000 | 0.5 | 0.765 | 92 | 238 | 24.98 | 22.84 | 0.9966 | 4302 |
| 3000 | 0.7 | 1.088 | 147 | 238 | 30.28 | 19.36 | 0.9949 | 4981 |
| 3000 | 0.8 | 1.249 | 175 | 238 | 30.88 | 18.57 | 1.0068 | 5020 |
| 3000 | 0.9 | 1.410 | 203 | 238 | 31.33 | 18.57 | 1.0049 | 5075 |
| 3000 | 0.95 | 1.490 | 216 | 238 | 31.31 | 18.57 | 1.0052 | 5074 |
| 3000 | 1.0 | 1.571 | 230 | 238 | 31.31 | 18.56 | 1.0052 | 5074 |
| 6000 | 0.3 | - | - | - | INVALID:timeout | - | - | - |
| 6000 | 0.5 | 0.765 | 92 | 238 | 9.73 | 31.45 | 0.7885 | 3513 |
| 6000 | 0.7 | 1.088 | 147 | 238 | 32.74 | 29.29 | 0.9420 | 4286 |
| 6000 | 0.8 | 1.249 | 175 | 238 | 37.29 | 29.34 | 0.9954 | 4353 |
| 6000 | 0.9 | 1.410 | 203 | 238 | 39.29 | 29.35 | 0.9959 | 4480 |
| 6000 | 0.95 | 1.490 | 216 | 238 | 39.30 | 29.35 | 0.9958 | 4480 |
| 6000 | 1.0 | 1.571 | 230 | 238 | 39.21 | 29.35 | 0.9959 | 4480 |

### Tabela P2 - contrafactual: ADC0 (IRAM 60h, TPS trilha 2) forcado a 5 V a partir do degrau de pedal

| RPM | IRAM 60h orig. | IRAM 6Dh orig. | avanco orig. | potencia orig. | IRAM 60h forcado | IRAM 6Dh forcado | avanco forcado | potencia forcada | variacao avanco | variacao potencia |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1500 | 230 | 60 | 7.12 | 14.81 | 255 | 61 | 15.14 | 15.95 | +8.02 | +1.14 |
| 3000 | 230 | 60 | 18.56 | 31.31 | 255 | 61 | 26.05 | 32.03 | +7.48 | +0.72 |
| 4500 | 230 | 60 | 25.58 | 42.43 | 255 | 61 | 33.53 | 43.32 | +7.95 | +0.90 |
| 6000 | 230 | 60 | 29.35 | 39.21 | 255 | 61 | 34.97 | 39.42 | +5.62 | +0.21 |

### Tabela P3 - estado termico (temperatura da agua inicial)

| RPM | agua [C] | resultado | potencia [kW] | avanco [graus] | lambda |
|---:|---:|---|---:|---:|---:|
| 3000 | 60 | ACCEPTED | 31.89 | 19.29 | 1.0030 |
| 3000 | 75 | INVALID:stall | - | - | - |
| 3000 | 105 | ACCEPTED | 30.90 | 18.39 | 1.0042 |
| 6000 | 60 | ACCEPTED | 39.17 | 30.04 | 0.9971 |
| 6000 | 75 | INVALID:stall | - | - | - |
| 6000 | 105 | ACCEPTED | 38.69 | 28.98 | 0.9991 |

### Tabela P4 - sonda lambda mantida (ADC5), a partir de 2 M ticks

| RPM | ADC5 | potencia [kW] | avanco [graus] | lambda dos cilindros |
|---:|---|---:|---:|---:|
| 3000 | 1000mV | 31.41 | 18.43 | 0.9806 |
| 3000 | 2600mV | 29.37 | 18.65 | 1.0819 |
| 3000 | 4000mV | 30.34 | 18.64 | 1.0499 |
| 6000 | 1000mV | 38.96 | 29.33 | 1.0041 |
| 6000 | 2600mV | 36.90 | 29.34 | 1.0488 |
| 6000 | 4000mV | 38.02 | 29.34 | 1.0263 |

### Tabela P5 - reinicios mornos encadeados (XRAM retida F800h-FBFFh salva e recarregada, POF=0)

| passo | RPM | potencia [kW] | avanco [graus] | lambda | XRAM F8E8 |
|---|---:|---:|---:|---:|---:|
| fresh_saved | 3000 | 31.31 | 18.56 | 1.0052 | 6 |
| warm_after_3000 | 6000 | 39.30 | 29.34 | 0.9960 | 6 |
| warm_after_6000 | 1500 | 14.80 | 7.12 | 0.9996 | 5 |
| warm_after_1500 | 3000 | 31.33 | 18.58 | 1.0048 | 6 |
| warm_repeat_3000 | 3000 | 31.30 | 18.57 | 1.0052 | 6 |

### Tabela P6 - NTC forcado (a partir de 8 M ticks): IRAM 62h/63h e bits de falha XRAM 4Eh-50h

Os bits sao reais (lidos da XRAM retida). A coluna de DTC e a decodificacao ingenua da tabela 6E27h por indice de bit e esta **incorreta** para os bits de F84F (ver secao de sensores): o teste `PhysicalDiagnostics.NtcSensorIdentity` usa o DTC realmente transmitido pela ROM na K-line.

| caso | IRAM 62h | IRAM 63h | bits de falha |
|---|---:|---:|---|
| base | 72 | 19 | - |
| ect_0.0V | 72 | 17 | F84F.4 |
| air_0.0V | 121 | 19 | F84F.7 |
| ect_0.1V | 72 | 5 | - |
| air_0.1V | 5 | 19 | - |
| ect_0.2V | 72 | 10 | - |
| air_0.2V | 10 | 19 | - |
| ect_0.3V | 72 | 15 | - |
| air_0.3V | 15 | 19 | - |
| ect_0.5V | 72 | 26 | - |
| air_0.5V | 26 | 19 | - |
| ect_4.5V | 72 | 17 | F84F.5 |
| air_4.5V | 230 | 19 | - |
| ect_4.8V | 72 | 17 | F84F.3 |
| air_4.8V | 246 | 19 | - |
| ect_5.0V | 72 | 17 | F84F.3 |
| air_5.0V | 121 | 19 | F84F.6 |

### Tabela P7 - troca ADC2 <-> ADC3 (`--exp swap_ntc=1`): marcha lenta livre, 60 M ticks, ultimos 20 intervalos

| caso | RPM medio | RPM min / max | IRAM 62h | IRAM 63h | agua [C] | ar [C] | avanco [graus] | bits de falha F84E-50 |
|---|---:|---|---:|---:|---:|---:|---:|---|
| idle_base_90 | 911.7 | 910.4 / 912.3 | 74 | 19 | 91.3 | 42.6 | 8.41 | 00 00 00 |
| idle_swap_90 | 1081.4 | 1080.6 / 1082.9 | 18 | 74 | 91.9 | 42.2 | 8.13 | 00 00 00 |
| idle_base_100 | 911.4 | 910.0 / 912.0 | 69 | 20 | 89.3 | 44.9 | 8.47 | 00 00 00 |
| idle_swap_100 | 1072.1 | 1071.0 / 1073.7 | 20 | 70 | 89.5 | 44.6 | 8.32 | 00 00 00 |

### Tabela P8 - troca ADC2 <-> ADC3: pontos de plena carga

| RPM | caso | resultado | potencia [kW] | avanco [graus] | lambda |
|---:|---|---|---:|---:|---:|
| 1500 | base | ACCEPTED | 14.81 | 7.12 | 0.9995 |
| 1500 | swap | ACCEPTED | 15.10 | 7.47 | 0.9798 |
| 1500 | swap_100C | ACCEPTED | 14.65 | 7.66 | 0.9913 |
| 3000 | base | ACCEPTED | 31.31 | 18.56 | 1.0052 |
| 3000 | swap | ACCEPTED | 31.52 | 17.95 | 1.0034 |
| 3000 | swap_100C | ACCEPTED | 31.30 | 17.94 | 1.0061 |
| 6000 | base | ACCEPTED | 39.21 | 29.35 | 0.9959 |
| 6000 | swap | ACCEPTED | 38.61 | 27.38 | 0.9805 |
| 6000 | swap_100C | ACCEPTED | 38.61 | 27.38 | 0.9790 |

### Tabela P9 - marcha lenta contra tensao forcada em um NTC por vez (aplicada desde a partida; medido em 36-48 M ticks)

| canal | tensao [V] | IRAM 62h | IRAM 63h | RPM | combustivel [g/s] | avanco [graus] | lambda dos cilindros |
|---|---:|---:|---:|---:|---:|---:|---:|
| referencia | - | 73 | 19 | 911.1 | 0.2263 | 8.49 | 1.011 |
| ADC3 (agua) | 0.4 | 73 | 21 | 911.1 | 0.2263 | 8.49 | 1.011 |
| ADC3 (agua) | 0.6 | 73 | 31 | 938.8 | 0.2281 | 8.2 | 1.009 |
| ADC3 (agua) | 0.8 | 74 | 41 | 1012.7 | 0.2507 | 7.72 | 1.001 |
| ADC3 (agua) | 1.0 | 74 | 51 | 1098.8 | 0.367 | 7.16 | 0.76 |
| ADC3 (agua) | 1.4 | 74 | 72 | 1111.7 | 0.3916 | 7.71 | 0.735 |
| ADC3 (agua) | 1.8 | 74 | 92 | 1138.6 | 0.4031 | 7.56 | 0.721 |
| ADC3 (agua) | 2.2 | 74 | 113 | 1170.2 | 0.4369 | 7.85 | 0.689 |
| ADC3 (agua) | 2.8 | 75 | 143 | 1240.8 | 0.5279 | 9.62 | 0.617 |
| ADC3 (agua) | 3.5 | 76 | 179 | 1437.7 | 0.7247 | 10.36 | 0.533 |
| ADC2 (ar) | 0.4 | 21 | 19 | 917.8 | 0.2292 | 8.34 | 1.018 |
| ADC2 (ar) | 0.6 | 31 | 19 | 914.6 | 0.2281 | 8.37 | 1.012 |
| ADC2 (ar) | 0.8 | 41 | 19 | 915.2 | 0.2292 | 8.31 | 1.007 |
| ADC2 (ar) | 1.0 | 51 | 19 | 910.8 | 0.226 | 8.51 | 1.009 |
| ADC2 (ar) | 1.4 | 72 | 19 | 908.4 | 0.2245 | 8.78 | 1.01 |
| ADC2 (ar) | 1.8 | 92 | 19 | 908.4 | 0.2247 | 8.8 | 1.006 |
| ADC2 (ar) | 2.2 | 113 | 19 | 909.7 | 0.2276 | 8.92 | 0.994 |
| ADC2 (ar) | 2.8 | 143 | 19 | 906.9 | 0.2253 | 8.66 | 0.993 |
| ADC2 (ar) | 3.5 | 179 | 19 | 906.2 | 0.2258 | 8.77 | 0.99 |

### Tabela P10 - o mesmo, mas em degrau a 10 M ticks (a ROM rejeita o salto na agua)

| canal | tensao [V] | IRAM 62h | IRAM 63h | RPM |
|---|---:|---:|---:|---:|
| ADC3 (agua) | 0.4 | 73 | 21 | 911.1 |
| ADC3 (agua) | 0.6 | 73 | 17 | 907.5 |
| ADC3 (agua) | 0.8 | 73 | 17 | 907.5 |
| ADC3 (agua) | 1.0 | 73 | 17 | 907.5 |
| ADC3 (agua) | 1.4 | 73 | 17 | 907.5 |
| ADC3 (agua) | 1.8 | 73 | 17 | 907.5 |
| ADC3 (agua) | 2.2 | 73 | 17 | 907.5 |
| ADC3 (agua) | 2.8 | 73 | 17 | 907.5 |
| ADC3 (agua) | 3.5 | 73 | 17 | 907.5 |
| ADC2 (ar) | 0.4 | 21 | 19 | 914.9 |
| ADC2 (ar) | 0.6 | 31 | 19 | 914.5 |
| ADC2 (ar) | 0.8 | 41 | 19 | 914.9 |
| ADC2 (ar) | 1.0 | 51 | 19 | 914.8 |
| ADC2 (ar) | 1.4 | 72 | 19 | 911.1 |
| ADC2 (ar) | 1.8 | 92 | 19 | 908.1 |
| ADC2 (ar) | 2.2 | 113 | 19 | 909.5 |
| ADC2 (ar) | 2.8 | 143 | 19 | 906.1 |
| ADC2 (ar) | 3.5 | 179 | 19 | 906.7 |

Leitura dos resultados:

1. **Reconhecimento de plena carga (cadeia causal medida).** No modelo elétrico atual a trilha 2 do TPS chega a 4,5 V a 90°
   (IRAM 60h = 230 = E6h, **abaixo de F0h**), então IRAM 6Dh.0 nunca é ligado (6Dh = 60h). Forçar ADC0 a 5 V (IRAM 60h = 255)
   liga o bit (6Dh = 61h) e a ROM passa a **avançar de +5,6° a +8,0°** (3000 RPM: 18,6° → 26,0°, perto do MBT de 27,4°),
   com ganho de potência de apenas 0,2 a 1,1 kW (Tabela P2). Cadeia: IRAM 60h >= F0h → IRAM 6Dh.0 → avanço maior → trabalho
   indicado maior. Limite da evidência: a forçagem a 5 V pode ter outros efeitos (é também o nível de "curto ao VCC"); o
   nexo direto bit → rotina de avanço não foi rastreado instrução a instrução. E o limiar F0h (4,71 V) só importa se o TPS
   real chegar lá a 90°; a curva elétrica do modelo é estimativa de bancada ("não é medição deste corpo de borboleta").
2. **Trilha 1 do TPS satura em 24° no modelo** (IRAM 66h = 238 para qualquer pedal >= 30 %, Tabela P1). Portanto IRAM 66h não
   distingue plena carga; **corrijo minha leitura anterior**, que tratava 238 como "TPS saturado em plena carga".
3. **Sem enriquecimento de plena carga:** λ = 0,99 a 1,01 de pedal 70 % a 100 % (Tabela P1); a ROM está em malha fechada
   (forçar a sonda muda λ de 0,98 a 1,08, Tabela P4). Em meia carga a 6000 RPM λ cai a 0,79 (pedal 50 %, 6000 RPM, fora da faixa útil).
   Sem evidência de enriquecimento por TPS no regime testado.
4. **Estado térmico:** 60 °C e 105 °C mudam potência em menos de 2 % e avanço em ≤ 0,9°. Água a 75 °C **estola** o motor em 3000 e
   6000 RPM (`INVALID:stall`), anomalia não explicada: o limiar `ROM[721Dh]=27h` em IRAM 63h cai nesta faixa (~75 °C);
   hipótese, não demonstrada, de que a troca da matriz de avanço/combustível nesse limiar desestabiliza a marcha lenta
   da bancada (ver G).
5. **Histórico e reinícios:** marcha lenta livre de 6, 12 e 24 M ticks, sequência de pontos encadeados 3000 → 6000 → 1500 → 3000
   com XRAM retida recarregada em partida morna (POF = 0) e repetição do ponto: potência varia ≤ 0,6 %, avanço ≤ 0,03° (Tabela P5,
   Tabela 6). A reinicialização **sem** estado retido é o próprio ponto "fresh_saved" (partida fria de RAM); a diferença
   para as mornas é desprezível. Itens 3 e 5 dos experimentos temporais (carga parcial prolongada, longas operações em
   várias temperaturas) foram cobertos apenas por esta cadeia, não por horas de simulação.
6. **Autoadaptação não demonstrada:** nenhum caso exibiu a cadeia estado → rotina → avanço/combustível → potência, com exceção
   do limiar de TPS2 do item 1 (que é condição de sensor, não adaptação).

### E.3 Identificação dos sensores de temperatura (água × ar)

Pedido do proprietário: checar se ar e água estão trocados, via tabelas de DTC, limites e endereços.

- Atribuição atual: ADC3 → IRAM 63h → água (ECT); ADC2 → IRAM 62h → ar (IAT).
- Prova pela ROM (K-line, DTC realmente transmitido, fonte dos rótulos: fiat-tipo.ru): ECT aberto (ADC3 = 5 V) → `02 0A 1E`
  (0A02, líquido); ECT em curto (0 V) → `02 0A 1D`; ar aberto (ADC2 = 5 V) → `02 0B 1E` (0B02, ar); ar em curto → `02 0B 1D`.
  Teste de regressão `PhysicalDiagnostics.NtcSensorIdentity` (passa). **Não há inversão** entre canais ADC e rótulos de DTC.
- **Confirmação em hardware real (informada pelo proprietário, captura de vídeo do scanner, não reproduzível aqui):** com o conector do
  sensor de temperatura do **ar** desligado no carro, o scanner listou `0B02` ("Sensor de temperatura do ar, circuito aberto ou curto")
  como DTC armazenado (junto de 0302 ativo, 0402 e 1A01 armazenados). É o mesmo código que o emulador transmite ao abrir o ADC2 (IRAM 62h).
  Portanto ADC2/IRAM 62h = ar tem apoio independente do hardware.
- Limites medidos: IRAM 62h válido de 04h a F7h (0,1 V → 5, 4,8 V → 246 sem falha; 0 V e 5 V → falha e substituto 79h = 121);
  IRAM 63h: 0 V → falha de curto, 4,5 V e >= 4,8 V → falhas de circuito aberto/limite alto (bits distintos), 0,1–0,5 V → sem falha.
- Os limiares das tabelas de calibração são coerentes com a identificação (água na faixa quente, ar na ambiente).
- Cautela: minha primeira decodificação direta da tabela `6E27h` pelo índice do bit (R3 → 6E27h + 3·R3) previu DTC errado
  para os bits de F84F (ECT aberto → F84F.3 que, lido assim, daria 0602); a ROM de fato transmite 0A02/1E. A indexação real
  inclui o deslocamento R7 e não foi decodificada por completo. Vale o oráculo da K-line, não a leitura ingênua.
- **Contrafactual de troca de canais (pedido do proprietário):** `--exp swap_ntc=1` faz o ADC2 ler o NTC da água e o ADC3 o do ar.
  A ROM **não entra em pane**: nenhum bit de falha (F84Eh..F850h = 0), sem estol, plena carga aceita (Tabelas P7 e P8).
  Com a troca, IRAM 62h vale 18–20 (ar "a 90–100 °C" fica dentro da faixa válida 04h..F7h, sem falha) e IRAM 63h vale ~70–74
  ("água fria"); a ROM então **sobe a marcha lenta de ~912 para ~1080 RPM** e reduz o avanço (3000 RPM: 18,6° → 17,9°; 6000 RPM:
  29,4° → 27,4°; λ 0,996 → 0,98), uma reação coerente com IRAM 63h ser a temperatura do líquido de arrefecimento; o proprietário confirma que o carro
  real sobe a marcha lenta com água fria (informação do proprietário, sem medição aqui). Nenhuma falha dispara, então o
  swap não se denuncia por DTC, mas mostra que o sistema real "continuaria funcionando" com os sensores
  trocados, só com calibração errada. Observação: o modelo térmico regula a água a ~90 °C (termostato), então o caso "100 °C"
  termina em ~89,5 °C; leituras equivalentes a 100–115 °C só foram testadas por tensão forçada (Tabela P6).
- **Qual canal move a marcha lenta (Tabela P9, um NTC por vez, valor aplicado desde a partida):** só a **água** (ADC3 / IRAM 63h)
  responde. De 0,4 V (quente, IRAM 63h = 21) a 3,5 V (frio, 179) a marcha lenta sobe de 911 para 1438 RPM, o combustível de
  0,226 para 0,725 g/s e o λ cai de 1,01 para 0,53 (enriquecimento de partida a frio); com 1,4 V (IRAM 63h = 72) a ROM dá
  ~1112 RPM, o mesmo valor do caso de troca de canais (~1080 a 1072 RPM), o que atribui o aumento do swap à leitura de 63h e não à de 62h.
  O **ar** (ADC2 / IRAM 62h, 21 a 179) não altera a marcha lenta (906 a 918 RPM) e só desloca λ e avanço levemente (λ 1,01 → 0,99,
  avanço 8,3° → 8,9°). Isso confirma, pelo comportamento da ROM, ADC3/IRAM 63h = água e ADC2/IRAM 62h = ar, e concorda com o
  carro real (marcha lenta alta com água fria, informado pelo proprietário; a direção "frio = marcha lenta alta" é a esperada).
  Assimetria adicional (Tabela P10): em degrau a 10 M ticks a ROM **rejeita** o salto da água (IRAM 63h trava em 17 para qualquer
  tensão ≥ 0,6 V, sem efeito na marcha lenta) mas **segue** o ar (IRAM 62h acompanha a tensão). É coerente com a água real
  nunca saltar e o ar poder variar bruscamente (observação do proprietário); o mecanismo exato do filtro não foi decodificado.
- Limite: não verifiquei a curva NTC (resistência × temperatura) contra um sensor real, nem a polaridade física do divisor; o
  teste funcional "água fria enriquece" foi inconclusivo (a malha fechada de λ mascara; marcha lenta de 908–915 RPM em todos os casos).

## F. Achados de implementação

1. `AccessoryParams::pump_nm_at_ref = 0,5 N·m a 925 RPM` com lei ω² extrapola para 13 kW a 6000 RPM.
2. `Combustion::spark`: queima total a partir de força 0,8, torque proporcional à força bruta; inconsistente com o comentário "Normal coil charge can ignite the full charge".
3. `accessory_torque_nm` divide a parcela do alternador por `alternator_ratio` (deveria ser P/(η·ω_virabrequim)); efeito < 1 N·m.
4. Dyno isolado exclui acessórios e usa ar a 20 °C; a comparação ROM × isolada precisa dos mesmos acessórios e da mesma temperatura.
5. Ajuste: nenhum ajuste foi aplicado ao comportamento padrão. As correções 1 e 2 estão disponíveis como
   flags e não foram adotadas porque alterariam o modelo calibrado (a VE foi ajustada com força 1,0 e
   sem acessórios) e exigiriam recalibração/revalidação decididas pelo proprietário.

Regressão: `ctest` completo, 350 de 350 testes passam com as flags `--exp` presentes (padrão desligado); os testes `PowerGap.*` verificam os invariantes acima.

## G. Questões em aberto

- Ordem de grandeza real da bomba-d'água e razão de polias (medição no carro ou ficha técnica).
- Lei de energia/carga da bobina e seu efeito físico no torque (hoje proporcional ao dwell).
- Tensão real da trilha 2 do TPS a 90° no carro (o limiar F0h da ROM = 4,71 V decide se o recurso de maior avanço, IRAM 6Dh.0, liga).
- Qual rotina consome IRAM 6Dh.0 para elevar o avanço (nexo medido, não rastreado instrução a instrução) e se há enriquecimento por TPS:
  nenhum foi observado até 100 % de pedal, mas só com TPS2 abaixo de F0h ou forçado a 5 V.
- Estol com água a 75 °C na bancada (60 e 105 °C não estolam): mecanismo desconhecido (limiar `ROM[721Dh]=27h` é hipótese).
- Decodificação completa do deslocamento R7 da tabela de DTC `6E27h`; polaridade física dos divisores NTC e curvas reais.
- Reinicialização com e sem RAM retida (item 6 e 7 dos experimentos temporais) e histórico de longa duração.
- Temperatura de admissão real do carro em plena carga (modelo térmico não validado).
- Avanço real do motor (PMS físico) e MBT medido em dinamômetro.
- Canal P5.0/P5.1 e atrasos do estágio de ignição: só a hipótese vigente foi mantida, sem teste novo.

## H. Recomendações

1. Substituir o modelo da bomba por uma curva limitada (potência de dezenas a poucas centenas de W) e recalibrar o conjunto; maior ganho (até 13 kW a 6000 RPM).
2. Decidir a lei do torque × carga da bobina; a opção `spark_torque_saturate` mostra +4–5 kW.
3. Padronizar a comparação isolada × ROM (acessórios, temperatura do ar, força de centelha).
4. Medir a tensão real da trilha 2 do TPS a 90° e, se passar de 4,71 V, ajustar a curva elétrica do TPS (a ROM ganha 5,6–8° de avanço).
   Rastrear o consumo de IRAM 6Dh.0 e investigar o estol a 75 °C.
5. Repetir a matriz com mais pontos de RPM e com 117/123° de PMS.
