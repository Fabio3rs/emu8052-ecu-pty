# Investigação do déficit de potência ROM MA1.7 × planta SEVEL

Estado: concluída (goal CURVES_STUDY). Números das tabelas vêm de `docs/dyno/investigation/*.csv`
via `tools/power_gap_report.py`; nada foi digitado à mão. Nada foi enviado ao remoto.

## A. Resumo executivo

> **Atualização:** as correções F-1 (bomba) e F-2 (força de centelha) foram aplicadas ao padrão (seção I). Com elas, o déficit da ROM contra a planta isolada cai de 23–35 % para 5–15 % (pico de 58,07 kW a 5500 RPM). O texto abaixo descreve o diagnóstico antes da correção.

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
| ROM não reconhece plena carga (TPS2 < F0h) | Avanço 7–13° abaixo do MBT; limiar F0h em `1047h` | Degrau de ADC0 a 5 V (P2, P13, P19) e curva contínua da trilha 2 até 5 V (P18) | Degrau com T1 baixa: falha F84F.2 e avanço +7,5° (fallback do TPS); curva contínua: sem falha, `6Dh.0` liga a 4,7 V, avanço/λ/potência inalterados | O ganho de avanço era o modo de falha do TPS (contradição entre pistas); plena carga com TPS2 alto não altera esta ROM | Alta (duas formas de forçar, teste de regressão) | Refutada (leitura anterior corrigida)
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
- **Inventário dinâmico de escritas na página retida (`MA17_XRAM_WRITE_PROFILE`, `tools/xram_write_inventory.py`, `docs/dyno/investigation/xram_write_inventory.csv`).** Em 14 cenários
  (marcha lenta, partida a 20 e 50 °C, carga parcial, plena carga a 1500/3000/6000 RPM, ECT aberto, ar aberto, TPS2 em degrau, interruptor de lenta aberto, motor do batente desconectado,
  sonda lambda travada pobre e rica) a ROM escreve em 400 dos 1024 endereços de F800h a FBFFh. Por número de mudanças de valor por execução: 3 endereços de rascunho por ciclo,
  14 dinâmicos, 339 de estado lento e 44 só de inicialização/quase constantes. A classificação é por contagem e **não** prova adaptação
  (muitos endereços de estado lento são buffers e contadores); serve de índice para quem decodificar as rotinas. Cada linha traz os PCs que escrevem (±1 instrução).
- **Regra de falha do TPS (`1047h`..`1150h`, decodificação parcial).** Limiares por pista geram os bits B.0–B.7 (TPS2 ≥ F0h liga B.7 e `6Dh.0`; TPS1 é comparado com FAh e 07h); `RAM_28.1` = OR de B.0–B.4 e
  `RAM_28.2` = OR de B.4–B.7; esses flags são debouncados por contadores (confirmação em 0Ah) para os bits de F84F e, ligados, selecionam o TPS de fallback `ROM[72A1h]` e zeram R2. Condições por limiar lidas em `1047h`..`110Ch` (R2 = IRAM 60h = TPS2, R4 = IRAM 66h = TPS1; volts = código × 5/255), atribuições de bit por leitura do assembly e não verificadas
  instrução a instrução em simulação:
  - TPS1 < 07h (0,14 V): `B.0` (pista 1 em curto ao GND/aberta).
  - TPS2 ≥ F0h (4,71 V): `B.7`, `PSW.5` e `6Dh.0`; com TPS1 ≥ FAh (4,90 V) também `B.3`.
  - TPS1 ≥ DCh (4,31 V) com TPS2 < 12h (0,35 V): `B.2`/`B.6` (pista 1 alta com pista 2 baixa, contradição).
  - TPS1 < DFh (4,37 V) com TPS2 ≥ 8Dh (2,76 V): `B.1`/`B.5` (pista 2 alta sem a pista 1 no topo, contradição).
  - TPS2 > TPS1 − 5 na faixa intermediária: `B.4` (pistas fora de proporção).
  Agregação: `RAM_28.1` = OR(B.0..B.4), `RAM_28.2` = OR(B.4..B.7), depois debounce (confirmação em 0Ah).
  Confirmações dinâmicas: TPS2 em 5 V com a pista 1 baixa liga F84F.2 (regra B.1/B.5); TPS1 em 5 V com a pista 2 baixa liga F84F.1 (B.2/B.6); curvas contínuas com TPS1 ≥ DFh e
  TPS2 até 5 V não ligam falha (Tabelas P18–P20). **Caso dos dois canais em 5 V, resolvido por experimento** (`tps_both_open_timing.csv`, 3000 RPM): aplicados com a borboleta fechada (interruptor de lenta fechado, ocioso a 8 M ticks ou início da
  rampa a 12,0 M) ligam F84F = 06h (bits 1 e 2) e levam ao fallback (avanço 26,05°, λ 1,275, 28,09 kW); aplicados depois que a borboleta abriu (rampa a 12,1 M, 12,5 M ou 13,5 M ticks) **não** ligam
  falha e deixam avanço (18,56–18,59°), λ (1,002–1,003) e potência (37,07–37,08 kW) normais. A falha depende, portanto, de os valores do TPS contradizerem o estado real da borboleta/interruptor de lenta,
  e não só dos valores das duas pistas entre si; o caso de 2,5 V é coerente com a regra de pistas fora de proporção (B.4). O pull-up de sinal ausente é hardware interno da ECU (informação do proprietário): sem TPS conectado a entrada analógica é puxada a ~5 V, o que no emulador equivale a `--tps-open-mv 5000` nos dois canais e fica coberto por esse experimento; não é lógica da ROM nem recurso do emulador em operação normal, portanto não há o que decodificar no firmware. A regra de plausibilidade fica caracterizada, não provada instrução a instrução.
- **Salvar/restaurar da correção de longo prazo** (`1722h`..`176Dh`, IRAM A7h-ABh): quando `RAM_27.6` está ligado e `B.1` limpo, o byte XRAM F86Ch (correção de
  combustível de longo prazo, posição 5 da coleta F4) é copiado para a IRAM superior @AAh; após uma contagem regressiva em IRAM @97h (decrementada com
  `RAM_2D.5` e `.6`) e `RAM_29.5` ligado, o valor salvo é escrito de volta em F86Ch. É a única escrita direta de F86Ch na ROM, um mecanismo de
  congelar/restaurar a adaptação, com semântica das condições (`27h.6`, `2Fh.1`) não identificada. Demais variáveis adaptativas da coleta: F80Ch
  (escrita em `19D0h`), F83Dh (inicialização no reset, `0C86h` com valor lido da ROM por `MOVC`, e escrita em `2491h`) e F869h (somente leituras diretas). Decisão do proprietário: a varredura semântica completa da ROM não é necessária agora, pois nenhuma contradição explícita foi identificada. Varredura mecânica dos padrões
  `MOV R0/R1,#addr` + `MOVX`; escritas via ponteiros calculados podem não aparecer.
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

### Tabela P11 - reinicio no meio da execucao (marcha lenta, reboot a 30 M ticks; janelas 22-30 M antes e 50-60 M depois)

| caso | RPM antes | RPM depois | avanco antes/depois [graus] | lambda antes/depois | bytes retidos F800h-FBFFh diferentes do caso sem reboot |
|---|---:|---:|---|---|---:|
| no_reboot | 908.6 | 912.1 | 8.62 / 8.43 | 1.004 / 1.006 | 0 |
| warm_reboot_30M | 908.6 | 934.1 | 8.62 / 8.21 | 1.004 / 1.006 | 42 |
| cold_reboot_30M | 908.6 | 905.8 | 8.62 / 8.71 | 1.004 / 1.005 | 30 |

Bytes retidos que diferem apos o reinicio frio (sem estado retido) em relacao ao caso sem reboot: F80B:3C->3B F80C:49->44 F82C:04->0E F82D:35->2F F831:3C->3B F832:3B->3A F833:3B->3A F834:3B->3A F836:04->0F F83D:07->0C F840:8D->87 F841:8D->87 F842:8D->87 F843:8D->87 F844:8D->87 F845:8D->87 F848:3B->3A F867:70->C4 F868:FD->AD F869:01->00 F888:79->88 F897:10->1F F8D5:01->00 F8E8:00->01 F8E9:1E->08 F8EA:00->06 F8EB:1E->08 F8EC:A7->D2 F8F5:26->3B F8FE:9C->98

### Tabela P12 - plena carga apos reinicio a 5 M ticks (antes do degrau de pedal a 12 M)

| RPM | caso | potencia [kW] | avanco [graus] | lambda |
|---:|---|---:|---:|---:|
| 1500 | no_reboot | 14.81 | 7.12 | 0.9995 |
| 1500 | warm_reboot_5M | 14.81 | 7.12 | 0.9985 |
| 1500 | cold_reboot_5M | 14.83 | 7.13 | 0.9985 |
| 3000 | no_reboot | 31.31 | 18.56 | 1.0052 |
| 3000 | warm_reboot_5M | 31.31 | 18.57 | 1.0054 |
| 3000 | cold_reboot_5M | 31.34 | 18.57 | 1.0039 |
| 6000 | no_reboot | 39.21 | 29.35 | 0.9959 |
| 6000 | warm_reboot_5M | 39.24 | 29.34 | 0.9951 |
| 6000 | cold_reboot_5M | 39.24 | 29.34 | 0.9950 |

### Tabela P13 - TPS2 (ADC0) forcado em degrau a 12 M ticks, 3000 RPM, plena carga

| tensao [V] | IRAM 60h | IRAM 6Dh | avanco [graus] | lambda | potencia [kW] |
|---:|---:|---:|---:|---:|---:|
| 4.5 | 230 | 52 | 26.05 | 0.9901 | 32.41 |
| 4.6 | 235 | 52 | 26.05 | 0.9901 | 32.41 |
| 4.65 | 238 | 52 | 26.05 | 0.9901 | 32.41 |
| 4.7 | 241 | 61 | 26.05 | 0.9995 | 32.05 |
| 4.71 | 241 | 61 | 26.05 | 0.9995 | 32.05 |
| 4.72 | 242 | 61 | 26.05 | 0.9995 | 32.05 |
| 4.75 | 243 | 61 | 26.05 | 0.9995 | 32.05 |
| 4.8 | 246 | 61 | 26.05 | 0.9995 | 32.05 |
| 5.0 | 255 | 61 | 26.05 | 1.0005 | 32.03 |

Bits de falha ligados pelo degrau (diferenca da XRAM retida contra o caso sem forcagem): 4,5 V -> F84F:00->04 F856:00->0A F885:00->04; 5,0 V -> F84F:00->04 F856:00->0A F885:00->04.

### Tabela P14 - enriquecimento de plena carga: malha lambda travada nos extremos (ADC5 0 mV = pobre -> ROM enriquece ao maximo; 4500 mV = rico -> ROM empobrece ao maximo)

| RPM | ADC5 | pedal | TPS2 | resultado | lambda dos cilindros | ar [mg/cil] | combustivel injetado [mg] | avanco [graus] |
|---:|---:|---:|---|---|---:|---:|---:|---:|
| 3000 | 0mV | 0.5 | model | ACCEPTED | 1.001 | 359.3 | 4220 | 22.65 |
| 3000 | 0mV | 0.5 | 5V | INVALID:fuel_cut | - | - | - | - |
| 3000 | 0mV | 0.7 | model | ACCEPTED | 1.036 | 414.0 | 4700 | 20.47 |
| 3000 | 0mV | 0.7 | 5V | INVALID:fuel_cut | - | - | - | - |
| 3000 | 0mV | 1.0 | model | ACCEPTED | 0.981 | 427.3 | 5124 | 18.43 |
| 3000 | 0mV | 1.0 | 5V | INVALID:fuel_cut | - | - | - | - |
| 3000 | 4500mV | 0.5 | model | INVALID:rpm_out_of_band | - | - | - | - |
| 3000 | 4500mV | 0.5 | 5V | INVALID:stall | - | - | - | - |
| 3000 | 4500mV | 0.7 | model | INVALID:rpm_out_of_band | - | - | - | - |
| 3000 | 4500mV | 0.7 | 5V | INVALID:stall | - | - | - | - |
| 3000 | 4500mV | 1.0 | model | ACCEPTED | 1.050 | 427.2 | 4869 | 18.64 |
| 3000 | 4500mV | 1.0 | 5V | INVALID:stall | - | - | - | - |
| 4500 | 0mV | 0.5 | model | ACCEPTED | 0.952 | 295.5 | 3655 | 30.69 |
| 4500 | 0mV | 0.5 | 5V | INVALID:fuel_cut | - | - | - | - |
| 4500 | 0mV | 0.7 | model | ACCEPTED | 1.046 | 394.2 | 4434 | 28.23 |
| 4500 | 0mV | 0.7 | 5V | INVALID:fuel_cut | - | - | - | - |
| 4500 | 0mV | 1.0 | model | ACCEPTED | 0.992 | 423.1 | 5019 | 25.57 |
| 4500 | 0mV | 1.0 | 5V | INVALID:fuel_cut | - | - | - | - |
| 4500 | 4500mV | 0.5 | model | INVALID:rpm_out_of_band | - | - | - | - |
| 4500 | 4500mV | 0.5 | 5V | INVALID:stall | - | - | - | - |
| 4500 | 4500mV | 0.7 | model | INVALID:rpm_out_of_band | - | - | - | - |
| 4500 | 4500mV | 0.7 | 5V | INVALID:stall | - | - | - | - |
| 4500 | 4500mV | 1.0 | model | ACCEPTED | 1.051 | 423.0 | 4816 | 25.57 |
| 4500 | 4500mV | 1.0 | 5V | INVALID:stall | - | - | - | - |

### Tabela P15 - janela de agua 65-90 C (bancada padrao: arranque de 495 000 ticks) e pontos com arranque de 1,5 M ticks

| agua [C] | resultado com arranque padrao, 3000 RPM |
|---:|---|
| 65 | ACCEPTED |
| 70 | INVALID:stall |
| 72 | INVALID:stall |
| 74 | INVALID:stall |
| 75 | INVALID:stall |
| 76 | INVALID:stall |
| 78 | INVALID:stall |
| 80 | INVALID:stall |
| 85 | ACCEPTED |
| 90 | ACCEPTED |

| caso (arranque 1,5 M ticks) | RPM | resultado | potencia [kW] | avanco [graus] | lambda |
|---|---:|---|---:|---:|---:|
| coolant=70 starter=1.5M | 3000 | ACCEPTED | 31.47 | 19.01 | 1.0031 |
| coolant=70 starter=1.5M | 6000 | ACCEPTED | 39.23 | 29.87 | 0.9902 |
| coolant=75 starter=1.5M | 3000 | ACCEPTED | 31.39 | 18.84 | 1.0045 |
| coolant=75 starter=1.5M | 6000 | ACCEPTED | 39.08 | 29.67 | 0.9868 |
| coolant=80 starter=1.5M | 3000 | ACCEPTED | 31.28 | 18.70 | 1.0064 |
| coolant=80 starter=1.5M | 6000 | ACCEPTED | 38.94 | 29.67 | 0.9976 |

### Tabela P16 - limiar ROM[721Dh] em copia temporaria da ROM (original = 21h; arquivo original intocado), 3000 RPM

| caso | resultado | potencia [kW] |
|---|---|---:|
| 721D=00 coolant=70C | INVALID:stall | - |
| 721D=00 coolant=75C | INVALID:stall | - |
| 721D=00 coolant=80C | INVALID:stall | - |
| 721D=00 coolant=90C | ACCEPTED | 31.34 |
| 721D=FF coolant=70C | INVALID:stall | - |
| 721D=FF coolant=75C | INVALID:stall | - |
| 721D=FF coolant=80C | INVALID:stall | - |
| 721D=FF coolant=90C | ACCEPTED | 31.33 |
| 721D=60 coolant=70C | INVALID:stall | - |
| 721D=60 coolant=75C | INVALID:stall | - |
| 721D=60 coolant=80C | INVALID:stall | - |
| 721D=60 coolant=90C | ACCEPTED | 31.31 |
| original coolant=70C | INVALID:stall | - |
| original coolant=75C | INVALID:stall | - |
| original coolant=80C | INVALID:stall | - |

### Tabela P17 - historico longo: 300 M ticks (~5 min simulados) de marcha lenta, XRAM retida carregada em pontos de plena carga

| janela [M ticks] | RPM | avanco [graus] | lambda | combustivel [g/s] | agua [C] |
|---|---:|---:|---:|---:|---:|
| 0-50 | 914.0 | 8.46 | 0.993 | 0.2317 | 91.1 |
| 50-100 | 912.1 | 8.44 | 1.005 | 0.2276 | 91.9 |
| 100-150 | 911.6 | 8.51 | 1.006 | 0.2273 | 88.8 |
| 150-200 | 910.8 | 8.53 | 1.006 | 0.2272 | 88.1 |
| 200-250 | 910.9 | 8.61 | 1.004 | 0.2277 | 87.9 |
| 250-300 | 910.6 | 8.65 | 1.005 | 0.2275 | 87.9 |

| RPM | estado inicial | potencia [kW] | avanco [graus] | lambda |
|---:|---|---:|---:|---:|
| 1500 | fresh | 14.81 | 7.12 | 0.9995 |
| 1500 | after_5min_idle | 14.78 | 7.47 | 1.0071 |
| 3000 | fresh | 31.31 | 18.56 | 1.0052 |
| 3000 | after_5min_idle | 31.19 | 18.56 | 1.0064 |
| 6000 | fresh | 39.21 | 29.35 | 0.9959 |
| 6000 | after_5min_idle | 39.06 | 29.34 | 0.9972 |

### Tabela P18 - curva continua da trilha 2 chegando a V a 90 graus (`--exp tps2_end_v`), sem degrau

| V final [V] | RPM | IRAM 60h | IRAM 6Dh | avanco [graus] | lambda | potencia [kW] | bits de falha F84E-50 |
|---:|---:|---:|---:|---:|---:|---:|---|
| 4.5 | 1500 | 230 | 60 | 7.13 | 0.9992 | 14.82 | 00 00 00 |
| 4.5 | 3000 | 230 | 60 | 18.57 | 1.0052 | 31.32 | 00 00 00 |
| 4.5 | 4500 | 230 | 60 | 25.58 | 1.0006 | 42.38 | 00 00 00 |
| 4.5 | 6000 | 230 | 60 | 29.35 | 0.9959 | 39.21 | 00 00 00 |
| 4.65 | 1500 | 238 | 60 | 7.13 | 0.9997 | 14.81 | 00 00 00 |
| 4.65 | 3000 | 238 | 60 | 18.56 | 1.0052 | 31.32 | 00 00 00 |
| 4.65 | 4500 | 238 | 60 | 25.58 | 1.0006 | 42.40 | 00 00 00 |
| 4.65 | 6000 | 238 | 60 | 29.34 | 0.9959 | 39.30 | 00 00 00 |
| 4.7 | 1500 | 241 | 61 | 7.13 | 0.9993 | 14.82 | 00 00 00 |
| 4.7 | 3000 | 241 | 61 | 18.56 | 1.0052 | 31.31 | 00 00 00 |
| 4.7 | 4500 | 241 | 61 | 25.57 | 1.0006 | 42.39 | 00 00 00 |
| 4.7 | 6000 | 241 | 61 | 29.35 | 0.9959 | 39.29 | 00 00 00 |
| 4.75 | 1500 | 243 | 61 | 7.13 | 0.9993 | 14.82 | 00 00 00 |
| 4.75 | 3000 | 243 | 61 | 18.57 | 1.0052 | 31.32 | 00 00 00 |
| 4.75 | 4500 | 243 | 61 | 25.58 | 1.0006 | 42.42 | 00 00 00 |
| 4.75 | 6000 | 243 | 61 | 29.34 | 0.9959 | 39.30 | 00 00 00 |
| 4.8 | 1500 | 246 | 61 | 7.13 | 0.9993 | 14.82 | 00 00 00 |
| 4.8 | 3000 | 246 | 61 | 18.56 | 1.0052 | 31.32 | 00 00 00 |
| 4.8 | 4500 | 246 | 61 | 25.57 | 1.0006 | 42.43 | 00 00 00 |
| 4.8 | 6000 | 246 | 61 | 29.35 | 0.9959 | 39.26 | 00 00 00 |
| 5.0 | 1500 | 255 | 61 | 7.12 | 0.9995 | 14.81 | 00 00 00 |
| 5.0 | 3000 | 255 | 61 | 18.57 | 1.0053 | 31.32 | 00 00 00 |
| 5.0 | 4500 | 255 | 61 | 25.57 | 1.0006 | 42.43 | 00 00 00 |
| 5.0 | 6000 | 255 | 61 | 29.35 | 0.9959 | 39.21 | 00 00 00 |

### Tabela P19 - TPS2 forcado a 5 V em instantes diferentes (3000 RPM, degrau de pedal a 12 M ticks, rampa de 0,2 s)

| instante | IRAM 60h | IRAM 6Dh | bits de falha F84E-50 | avanco [graus] | lambda | potencia [kW] |
|---|---:|---:|---|---:|---:|---:|
| T1_closed_(idle)_force_at_8M | 255 | 61 | 00 04 00 | 26.05 | 0.9946 | 32.14 |
| ramp_start_12.0M | 255 | 61 | 00 04 00 | 26.05 | 1.0005 | 32.03 |
| ramp_mid_12.1M | 255 | 61 | 00 00 00 | 18.56 | 1.0062 | 31.29 |
| ramp_end_T1_high_12.5M | 255 | 61 | 00 00 00 | 18.57 | 1.0052 | 31.32 |
| steady_WOT_13.5M | 255 | 61 | 00 00 00 | 18.57 | 1.0052 | 31.31 |

### Tabela P20 - as duas trilhas em seus valores finais (`--exp tps1_end_v` = trilha 1 aos 24 graus; `tps2_end_v` = trilha 2 aos 90 graus; "model" = curva do modelo: 4,65 V e 4,5 V)

| T1 final | T2 final | RPM | IRAM 66h | IRAM 60h | IRAM 6Dh | avanco [graus] | lambda | potencia [kW] | falhas F84E-50 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| model | model | 3000 | 238 | 230 | 60 | 18.56 | 1.0052 | 31.31 | 00 00 00 |
| model | model | 6000 | 238 | 230 | 60 | 29.35 | 0.9959 | 39.21 | 00 00 00 |
| model | 4.8 | 3000 | 238 | 246 | 61 | 18.56 | 1.0052 | 31.32 | 00 00 00 |
| model | 4.8 | 6000 | 238 | 246 | 61 | 29.35 | 0.9959 | 39.26 | 00 00 00 |
| model | 5.0 | 3000 | 238 | 255 | 61 | 18.57 | 1.0053 | 31.32 | 00 00 00 |
| model | 5.0 | 6000 | 238 | 255 | 61 | 29.35 | 0.9959 | 39.21 | 00 00 00 |
| 4.9 | model | 3000 | 251 | 230 | 60 | 18.57 | 1.0051 | 31.33 | 00 00 00 |
| 4.9 | model | 6000 | 251 | 230 | 60 | 29.34 | 0.9959 | 39.29 | 00 00 00 |
| 4.9 | 4.8 | 3000 | 251 | 246 | 61 | 18.57 | 1.0058 | 31.32 | 00 00 00 |
| 4.9 | 4.8 | 6000 | 251 | 246 | 61 | 29.34 | 0.9959 | 39.27 | 00 00 00 |
| 4.9 | 5.0 | 3000 | 251 | 255 | 61 | 18.57 | 1.0047 | 31.35 | 00 00 00 |
| 4.9 | 5.0 | 6000 | 251 | 255 | 61 | 29.34 | 0.9959 | 39.30 | 00 00 00 |
| 5.0 | model | 3000 | 255 | 230 | 60 | 18.57 | 1.0046 | 31.34 | 00 00 00 |
| 5.0 | model | 6000 | 255 | 230 | 60 | 29.34 | 0.9959 | 39.31 | 00 00 00 |
| 5.0 | 4.8 | 3000 | 255 | 246 | 61 | 18.58 | 1.0048 | 31.32 | 00 00 00 |
| 5.0 | 4.8 | 6000 | 255 | 246 | 61 | 29.34 | 0.9959 | 39.30 | 00 00 00 |
| 5.0 | 5.0 | 3000 | 255 | 255 | 61 | 18.57 | 1.0049 | 31.31 | 00 00 00 |
| 5.0 | 5.0 | 6000 | 255 | 255 | 61 | 29.34 | 0.9959 | 39.30 | 00 00 00 |

### Tabela P21 - TPS ratiometrico (alimentacao do TPS = referencia do ADC) e curvas em porcentagem da pista

| caso | RPM | IRAM 66h | IRAM 60h | avanco [graus] | potencia [kW] | falhas F84E-50 |
|---|---:|---:|---:|---:|---:|---|
| supply 5.0 V (reference) | 3000 | 238 | 230 | 18.56 | 31.31 | 00 00 00 |
| supply 4.7 V, ADC Vref follows (ratiometric) | 3000 | 238 | 230 | 18.56 | 31.31 | 00 00 00 |
| supply 4.7 V, ADC Vref fixed 5.0 V | 3000 | 224 | 216 | 18.57 | 31.33 | 00 00 00 |
| supply 5.3 V, ADC Vref follows (ratiometric) | 3000 | 238 | 230 | 18.56 | 31.31 | 00 00 00 |
| supply 5.3 V, ADC Vref fixed 5.0 V | 3000 | 252 | 244 | 18.58 | 31.31 | 00 00 00 |
| supply 5.0 V (reference) | 6000 | 238 | 230 | 29.35 | 39.21 | 00 00 00 |
| supply 4.7 V, ADC Vref follows (ratiometric) | 6000 | 238 | 230 | 29.35 | 39.21 | 00 00 00 |
| supply 4.7 V, ADC Vref fixed 5.0 V | 6000 | 224 | 216 | 29.34 | 39.30 | 00 00 00 |
| supply 5.3 V, ADC Vref follows (ratiometric) | 6000 | 238 | 230 | 29.35 | 39.21 | 00 00 00 |
| supply 5.3 V, ADC Vref fixed 5.0 V | 6000 | 252 | 244 | 29.34 | 39.31 | 00 00 00 |
| percent-of-track curves (T1 0-24 deg, T2 18-90 deg) | 1500 | 255 | 255 | 7.12 | 14.81 | 00 00 00 |
| percent-of-track curves (T1 0-24 deg, T2 18-90 deg) | 3000 | 255 | 255 | 18.57 | 31.29 | 00 00 00 |
| percent-of-track curves (T1 0-24 deg, T2 18-90 deg) | 6000 | 255 | 255 | 29.34 | 39.22 | 00 00 00 |

### Tabela P22 - falhas do conjunto lenta/TPS com a bancada ignorando a falha diagnostica (corte indevido acima de ~1500 RPM, relato do proprietario)

| falha (a partir de 2 M ticks) | RPM | resultado | RPM medio | potencia [kW] | avanco [graus] | lambda | falhas F84E-50 |
|---|---:|---|---:|---:|---:|---:|---|
| idle_contact_open | 1500 | ACCEPTED | 1500 | 14.80 | 7.11 | 0.9994 | 02 00 00 |
| idle_contact_open | 2000 | ACCEPTED | 2001 | 20.75 | 10.99 | 0.9966 | 02 00 00 |
| idle_contact_open | 3000 | ACCEPTED | 3000 | 31.24 | 18.56 | 1.0072 | 02 00 00 |
| idle_contact_closed | 1500 | ACCEPTED | 1500 | 14.80 | 7.10 | 0.9992 | 01 00 00 |
| idle_contact_closed | 2000 | ACCEPTED | 2001 | 20.71 | 11.08 | 0.9962 | 01 00 00 |
| idle_contact_closed | 3000 | ACCEPTED | 3001 | 31.45 | 18.59 | 1.0025 | 01 00 00 |
| idle_motor_disconnected | 1500 | ACCEPTED | 1499 | 14.80 | 7.12 | 0.9990 | 08 00 00 |
| idle_motor_disconnected | 2000 | ACCEPTED | 2001 | 20.76 | 10.97 | 0.9963 | 08 00 00 |
| idle_motor_disconnected | 3000 | ACCEPTED | 3000 | 31.28 | 18.56 | 1.0058 | 08 00 00 |
| idle_motor_disc+tps2_high | 1500 | ACCEPTED | 1500 | 15.96 | 15.13 | 0.9940 | 00 04 00 |
| idle_motor_disc+tps2_high | 2000 | ACCEPTED | 2000 | 21.51 | 18.91 | 0.9961 | 00 04 00 |
| idle_motor_disc+tps2_high | 3000 | ACCEPTED | 3000 | 32.05 | 26.05 | 0.9997 | 00 04 00 |
| tps_both_open_0V | 1500 | ACCEPTED | 1508 | 14.54 | 15.15 | 1.0883 | 00 02 00 |
| tps_both_open_0V | 2000 | ACCEPTED | 2010 | 18.00 | 19.00 | 1.1702 | 00 02 00 |
| tps_both_open_0V | 3000 | ACCEPTED | 3001 | 23.10 | 26.05 | 1.2707 | 00 02 00 |

### Tabela P23 - calibracoes de marcha lenta e em carga: variaveis retidas apos 300 M ticks de marcha lenta e apos 200 M ticks sob carga parcial (45 N.m)

| variavel retida | marcha lenta | sob carga |
|---|---:|---:|
| F80Ch (integrador lambda) | 76 | 97 |
| F83Dh (posicao do atuador de lenta) | 7 | 10 |
| F86Ch (correcao de longo prazo) | 250 | 249 |
| F86Fh (aditivo de lenta) | 0 | 0 |
| F869h (purga) | 8 | 7 |
| F8E8h (limite da tabela lambda) | 0 | 0 |
| F8E9h (contador da tabela lambda) | 30 | 30 |

### Tabela P24 - historico de ~20 min simulados (1,2 bilhao de ticks) de marcha lenta, estado retido carregado em pontos de plena carga (o rotulo `after_5min_idle` do CSV significa depois desse historico longo)

| janela [M ticks] | RPM | avanco [graus] | lambda | combustivel [g/s] | agua [C] |
|---|---:|---:|---:|---:|---:|
| 0-200 | 912.1 | 8.48 | 1.003 | 0.2284 | 91.1 |
| 200-400 | 910.7 | 8.63 | 1.005 | 0.2275 | 87.9 |
| 400-600 | 910.5 | 8.62 | 1.005 | 0.2275 | 87.8 |
| 600-800 | 910.9 | 8.66 | 0.998 | 0.229 | 87.8 |
| 800-1000 | 911.0 | 8.62 | 0.997 | 0.2293 | 87.8 |
| 1000-1200 | 910.8 | 8.61 | 0.998 | 0.229 | 87.8 |

| RPM | estado inicial | potencia [kW] | variacao [%] | avanco [graus] | lambda |
|---:|---|---:|---:|---:|---:|
| 1500 | fresh | 14.81 | +0.00 | 7.12 | 0.9995 |
| 1500 | after_5min_idle | 14.78 | -0.20 | 8.24 | 1.0143 |
| 3000 | fresh | 31.31 | +0.00 | 18.56 | 1.0052 |
| 3000 | after_5min_idle | 31.25 | -0.18 | 18.64 | 1.0083 |
| 6000 | fresh | 39.21 | +0.00 | 29.35 | 0.9959 |
| 6000 | after_5min_idle | 38.79 | -1.08 | 29.36 | 1.0047 |

### Tabela P25 - enriquecimento de plena carga em toda a faixa de rotacao: lambda dos cilindros com a sonda travada pobre (0 mV, a ROM enriquece ao maximo), neutra (2500 mV) e rica (4500 mV)

| RPM | sonda pobre 0 mV | neutra 2500 mV | rica 4500 mV |
|---:|---:|---:|---:|
| 1500 | 0.9472 | 1.0812 | 1.0427 |
| 2000 | 0.9981 | 1.1049 | 1.0659 |
| 2500 | 0.9783 | 1.0917 | 1.0544 |
| 3000 | 0.9705 | 1.0820 | 1.0496 |
| 3500 | 0.9446 | 1.0520 | 1.0226 |
| 4000 | 0.9469 | 1.0524 | 1.0243 |
| 4500 | 0.9753 | 1.0792 | 1.0507 |
| 5000 | 0.9788 | 1.0710 | 1.0446 |
| 5500 | 0.9772 | 1.0482 | 1.0239 |
| 6000 | 0.9949 | 1.0501 | 1.0263 |

Menor lambda com enriquecimento maximo da malha em plena carga: 0.9446.

### Tabela P26 - formato do mapa base de combustivel: lambda dos cilindros contra pedal e rotacao, com a sonda travada pobre (0 mV) e rica (4500 mV) desde 2 M ticks; '-' = o motor nao sustenta o ponto

| RPM | pedal | lambda sonda pobre | lambda sonda rica | ponto medio |
|---:|---:|---:|---:|---:|
| 1500 | 0.5 | 0.9591 | - | - |
| 1500 | 0.6 | 1.0012 | - | - |
| 1500 | 0.7 | 1.0133 | - | - |
| 1500 | 0.8 | 0.9479 | 1.0443 | 0.9961 |
| 1500 | 0.9 | 0.948 | 1.0452 | 0.9966 |
| 1500 | 1.0 | 0.9472 | 1.0427 | 0.995 |
| 2000 | 0.5 | 1.0045 | - | - |
| 2000 | 0.6 | 1.0423 | - | - |
| 2000 | 0.7 | 1.0573 | - | - |
| 2000 | 0.8 | 0.9952 | 1.0613 | 1.0282 |
| 2000 | 0.9 | 0.9984 | 1.0658 | 1.0321 |
| 2000 | 1.0 | 0.9981 | 1.0659 | 1.032 |
| 3000 | 0.5 | 0.966 | - | - |
| 3000 | 0.6 | 0.9796 | - | - |
| 3000 | 0.7 | 0.9998 | - | - |
| 3000 | 0.8 | 0.9676 | 1.0458 | 1.0067 |
| 3000 | 0.9 | 0.971 | 1.0496 | 1.0103 |
| 3000 | 1.0 | 0.9705 | 1.0496 | 1.0101 |
| 4000 | 0.5 | 0.954 | - | - |
| 4000 | 0.6 | 0.9709 | - | - |
| 4000 | 0.7 | 0.9898 | - | - |
| 4000 | 0.8 | 0.9532 | 1.0297 | 0.9915 |
| 4000 | 0.9 | 0.9485 | 1.0242 | 0.9864 |
| 4000 | 1.0 | 0.9469 | 1.0243 | 0.9856 |
| 5000 | 0.5 | 0.8563 | - | - |
| 5000 | 0.6 | 0.912 | - | - |
| 5000 | 0.7 | 0.9061 | 1.0004 | 0.9532 |
| 5000 | 0.8 | 0.9694 | 1.0327 | 1.001 |
| 5000 | 0.9 | 0.9795 | 1.0446 | 1.012 |
| 5000 | 1.0 | 0.9788 | 1.0446 | 1.0117 |
| 6000 | 0.5 | 0.7466 | 0.7886 | 0.7676 |
| 6000 | 0.6 | 0.8067 | 0.8594 | 0.8331 |
| 6000 | 0.7 | 0.8982 | 0.9424 | 0.9203 |
| 6000 | 0.8 | 0.9709 | 1.0028 | 0.9869 |
| 6000 | 0.9 | 0.9955 | 1.0264 | 1.011 |
| 6000 | 1.0 | 0.9949 | 1.0263 | 1.0106 |

### Tabela P27 - eixo de carga derivada (IRAM 70h) contra o pedal (borboleta de 90 graus = pedal 1,0)

| RPM | pedal | IRAM 60h (TPS2) | IRAM 70h | lambda | avanco [graus] |
|---:|---:|---:|---:|---:|---:|
| 1500 | 0.3 | 36 | 79 | 0.9857 | 10.80 |
| 1500 | 0.5 | 92 | 135 | 0.9967 | 9.10 |
| 1500 | 0.6 | 120 | 163 | 0.9965 | 9.79 |
| 1500 | 0.7 | 147 | 190 | 0.9984 | 9.79 |
| 1500 | 0.8 | 175 | 218 | 0.9996 | 7.31 |
| 1500 | 0.9 | 203 | 246 | 1.0001 | 7.10 |
| 1500 | 1.0 | 230 | 255 | 1.0001 | 7.10 |
| 3000 | 0.3 | 36 | 79 | 1.0001 | 28.52 |
| 3000 | 0.5 | 92 | 135 | 0.9952 | 22.82 |
| 3000 | 0.6 | 120 | 163 | 0.9921 | 21.44 |
| 3000 | 0.7 | 147 | 190 | 0.9988 | 20.43 |
| 3000 | 0.8 | 175 | 218 | 1.0033 | 18.56 |
| 3000 | 0.9 | 203 | 246 | 1.0027 | 18.57 |
| 3000 | 1.0 | 230 | 255 | 1.0023 | 18.59 |
| 6000 | 0.5 | 92 | 135 | 0.7885 | 31.45 |
| 6000 | 0.6 | 120 | 163 | 0.8592 | 29.48 |
| 6000 | 0.7 | 147 | 190 | 0.9423 | 29.29 |
| 6000 | 0.8 | 175 | 218 | 0.9959 | 29.34 |
| 6000 | 0.9 | 203 | 246 | 0.9977 | 29.34 |
| 6000 | 1.0 | 230 | 255 | 0.9977 | 29.34 |

### Tabela P28 - a ROM segue a sonda em plena carga? Sonda travada so depois da rampa do pedal (12,5 M ticks) contra desde o ocioso (2 M ticks); janela de 200 ciclos

| RPM | sonda | travada a partir de | lambda | potencia [kW] |
|---:|---|---|---:|---:|
| 3000 | livre | - | 1.0043 | 37.25 |
| 3000 | 0 mV | depois da rampa (12,5 M) | 0.9905 | 36.74 |
| 3000 | 0 mV | ocioso (2 M) | 1.0381 | 36.25 |
| 3000 | 4500 mV | depois da rampa (12,5 M) | 1.0551 | 35.94 |
| 3000 | 4500 mV | ocioso (2 M) | 1.0551 | 35.94 |
| 5000 | livre | - | 1.0044 | 56.70 |
| 5000 | 0 mV | depois da rampa (12,5 M) | 0.9817 | 56.95 |
| 5000 | 0 mV | ocioso (2 M) | 1.0335 | 55.33 |
| 5000 | 4500 mV | depois da rampa (12,5 M) | 1.0479 | 54.86 |
| 5000 | 4500 mV | ocioso (2 M) | 1.0479 | 54.86 |

### Tabela P29 - enriquecimento de aceleracao: tip-in de ocioso (pedal 30 mm a 10 M ticks, motor sem freio), lambda dos cilindros por janela de 1 ciclo, de 10,2 M a 10,9 M ticks

| caso | lambda minimo | RPM no minimo | lambda a ~3000 RPM | lambda a ~4500 RPM |
|---|---:|---:|---:|---:|
| sonda livre, degrau | 0.758 | 1720 | 0.939 | 1.103 |
| sonda livre, rampa de 0,8 s | 0.796 | 1891 | 0.834 | 0.832 |
| sonda travada rica (4500 mV), degrau | 0.825 | 1751 | 0.998 | 1.137 |
| sonda travada pobre (0 mV), degrau | 0.773 | 1759 | 0.877 | 0.923 |

Leitura dos resultados:

1. **Reconhecimento de plena carga: hipótese anterior REFUTADA; o que vale é a consistência entre as trilhas.**
   Primeira leitura (Tabela P2): forçar ADC0 a 5 V elevou o avanço em 5,6–8,0°. Duas verificações a corrigem:
   - Curva **contínua** da trilha 2 chegando a 4,5, 4,65, 4,7, 4,75, 4,8 ou 5,0 V a 90° (Tabela P18, `--exp tps2_end_v`, coerente com a descrição do
     proprietário: trilha 2 de 18° a 90°, de 0 V a ~4,7–5 V): **nenhuma falha liga** (F84E–F850 = 0), o bit `6Dh.0` liga a partir de 4,7 V
     (IRAM 60h = 241), e avanço (18,56° a 3000 RPM), λ e potência **não mudam** em nenhum RPM testado.
   - Forçar ADC0 a 5 V em **degrau** (Tabela P19): com a borboleta ainda fechada (ocioso ou início da rampa) liga F84F.2 e o contador F856h = 0Ah, a falha
     `0602/1E` do teste `KlineFaultHistory`, e o avanço vai a 26,05° (fallback do TPS, `R4=ROM[72A1h]`, `116Dh`, cai num ponto de menor carga do mapa);
     forçado depois que a trilha 1 já está alta (a partir de 12,1 M ticks) não gera falha e o avanço fica em 18,56°.
   Interpretação (hipótese do proprietário, compatível com os dados, não provada no assembly): a ROM verifica a **contradição entre pistas**
   (pista 1 baixa com pista 2 alta; o pull-up de sinal ausente levaria a pista 2 a 5 V). Logo o avanço de 26° é o modo de falha do TPS e **não** um
   reconhecimento de plena carga, e um TPS real que chegue a 4,7–5 V a 90° (consistente com a pista 1 alta) não muda a potência desta ROM.
   Com as duas pistas em seus valores finais descritos pelo proprietário (pista 1 em VCC acima de 24°: IRAM 66h = 251–255, acima do `FAh` que `1047h` compara; pista 2 até 4,8–5,0 V a 90°),
   a Tabela P20 mostra nenhuma falha e avanço, λ e potência inalterados (≤ 0,1 %) em 3000 e 6000 RPM: o modelo elétrico do TPS (4,65 V e 4,5 V) não afeta a conclusão.
   Teste de regressão: `PhysicalDiagnostics.Tps2TrackConsistency`. O mapa de avanço contra a carga é o da Tabela P1 (3000 RPM: 28,5°, 22,8°, 19,4°
   para pedal 30, 50, 70 %; 18,57° constante de 80 a 100 %).
2. **Trilha 1 do TPS satura em 24° no modelo** (IRAM 66h = 238 para qualquer pedal >= 30 %, Tabela P1). Portanto IRAM 66h não
   distingue plena carga; **corrijo minha leitura anterior**, que tratava 238 como "TPS saturado em plena carga".
3. **Sem enriquecimento de plena carga:** λ = 0,99 a 1,01 de pedal 70 % a 100 % (Tabela P1); a ROM está em malha fechada
   (forçar a sonda muda λ de 0,98 a 1,08, Tabela P4). Em meia carga a 6000 RPM λ cai a 0,79 (pedal 50 %, 6000 RPM, fora da faixa útil).
   Sem evidência de enriquecimento por TPS no regime testado. **Teste com a malha lambda travada nos extremos (Tabela P14):** com a sonda
   dizendo "pobre" o tempo todo (ADC5 = 0 mV) a ROM enriquece ao máximo e atinge só λ = 0,98 (3000 RPM) e 0,99 (4500 RPM) em plena carga;
   com "rico" (4500 mV) vai a λ = 1,05. A autoridade total da malha em plena carga é ≈ ±3 %, centrada acima de 1,0; um enriquecimento de
   plena carga (λ ≈ 0,85–0,9) não aparece em nenhum dos dois extremos, nem em nenhuma rotação de 1500 a 6000 RPM (Tabela P25: o menor λ com enriquecimento máximo da malha é 0,9446, a 3500 RPM). A interpretação é de que **esta ROM não tem enriquecimento de plena carga** dentro do
   alcance do integrador; não exclui lógica ativada por condição não testada (carga, rotação ou temperatura fora da faixa).
4. **Estado térmico e o "estol" a 70–80 °C (resolvido).** Água a 60, 65, 85, 90 e 105 °C mudam a potência em ≤ 2 % e o avanço em ≤ 0,9°. Entre 70 e 80 °C o ponto
   saía `INVALID:stall`. Investigado: nessa faixa o motor **não pega** com o arranque padrão da bancada (495 000 ticks ≈ 0,5 s; nenhuma janela de planta, bit F850.1 ligado);
   com 1,5 M ticks de arranque ele pega, marcha lenta de 909–912 RPM, e a plena carga é normal (Tabelas P15; 3000 RPM 31,3–31,5 kW, 6000 RPM 38,9–39,2 kW).
   A hipótese anterior de que o limiar `ROM[721Dh]` (21h no arquivo) causasse o estol foi **refutada**: modificar esse byte numa cópia temporária da ROM (00h, 60h, FFh) não mudou a janela (Tabela P16).
   O mecanismo (a ROM precisa de arranque mais longo nessa faixa, provavelmente lógica de partida) não foi decodificado; é artefato do tempo de arranque do cenário e não afeta a plena carga.
5. **Histórico e reinícios (itens 6 e 7 dos experimentos temporais, agora como experimentos separados):**
   - *Item 6, reinício com estado retido:* `MA17_WARM_REBOOT_TICK` (reinício da CPU preservando toda a RAM) no meio da marcha
     lenta e partida morna encadeada (Tabela P5, POF = 0). Marcha lenta 908,6 → 934,1 RPM (+2,8 %), avanço 8,62° → 8,21°; plena carga
     após reboot a 5 M ticks: |Δpotência| ≤ 0,03 kW (Tabela P12).
   - *Item 7, reinício sem estado retido:* nova variável `MA17_COLD_REBOOT_TICK` (reinício com a XRAM F800h–FBFFh zerada e POF = 1).
     Marcha lenta 908,6 → 905,8 RPM; plena carga após o reboot: |Δpotência| ≤ 0,04 kW, |Δavanço| ≤ 0,01° (Tabela P12).
   - Os dois reinícios deixam 42 (morno) e 30 (frio) bytes retidos diferentes do caso sem reboot (Tabela P11), com destaque
     para F80Ch (estado do integrador lambda), F83Dh (posição do atuador de marcha lenta: 07h → 0Ch no reboot frio),
     F869h (adaptação de purga) e F8E8h/F8E9h (contador da tabela lambda). Não variaram F86Ch (correção de longo prazo) e F86Fh
     (aditivo de marcha lenta). A potência de plena carga não depende desse estado (≤ 0,1 %).
   - *Histórico longo (~5 min simulados):* 300 M ticks de marcha lenta com XRAM retida e depois pontos de plena carga com esse estado (Tabela P17): marcha lenta
     de 914 a 911 RPM, avanço 8,46° → 8,65°, λ ≈ 1,005; plena carga com estado longo vs fresco: −0,03 a −0,15 kW (−0,3 % a −0,4 %), avanço ≤ 0,35°.
   - *Histórico de ~20 min simulados (1,2 bilhão de ticks, Tabela P24):* marcha lenta estável (912 → ~910 RPM); plena carga com o estado retido desse histórico contra estado fresco:
     −0,2 % (1500 e 3000 RPM) e −1,1 % (6000 RPM), avanço de 1500 RPM de 7,12° para 8,24°. Uma adaptação lenta existe e é pequena; nenhuma redução relevante de potência.
   - Histórico por tempo de marcha lenta (6, 12, 24 M ticks) e temperatura da água (60/105 °C): ≤ 2 % (Tabelas 6 e P3). Carga parcial
     prolongada e longas operações em várias temperaturas: cobertas só por esta cadeia de pontos, não por horas simuladas.
6. **Autoadaptação não demonstrada:** nenhum caso exibiu a cadeia estado → rotina → avanço/combustível → potência, com exceção
   do limiar de TPS2 do item 1 (que é condição de sensor, não adaptação).

7. **TPS ratiométrico (observação do proprietário: o TPS e o Vref do ADC vêm do mesmo 5 V da ECU).** Tabela P21: com a alimentação do TPS em 4,7 ou 5,3 V e o Vref do ADC
   seguindo-a, os códigos (IRAM 66h = 238, IRAM 60h = 230) e os resultados são idênticos aos de 5,0 V; com o Vref fixo em 5,0 V os códigos escalam (224/216 e 252/244)
   e a potência muda ≤ 0,3 %. Curvas em porcentagem da pista (T1 0–100 % em 0–24°, T2 0–100 % em 18–90°, `--exp tps_linear_fraction=1`): IRAM 66h e 60h = 255 a 90°,
   sem falha e sem mudança de avanço ou potência (≤ 0,1 %). Opções: `tps_supply_v`, `tps_ratiometric`, `tps_linear_fraction`. A curva do modelo por tensão absoluta não altera a conclusão.
8. **Corte indevido por TPS ou lenta (relato do proprietário: TPS problemático, ou atuador + interruptor de lenta, faz a ROM cortar por volta de 1500 RPM).** Tabela P22, com a
   bancada ignorando a falha diagnóstica (`--exp dyno_ignore_diag=1`): interruptor de lenta aberto, fechado ou atuador desconectado **não** cortam combustível a 1500, 2000 ou 3000 RPM no
   emulador (a potência e o λ ficam normais); TPS aberto em 0 V dá avanço de fallback de 26° e λ pobre (1,09 a 1,27, −26 % de potência a 3000 RPM), mas também sem corte. O relato **não foi reproduzido**, e isso é o esperado (informação do proprietário: o corte a ~1500 RPM é a própria ECU com defeito de sensor; com os sensores emulados corretamente ele não deve ocorrer no emulador).
   **Corte de desaceleração esperado (reproduzido):** com rotação alta e o pedal solto (borboleta no batente), a ROM corta o combustível até a rotação cair a ~1500 RPM. Pedal aberto 30 mm a 8 M ticks e solto a 14 M ticks, janelas de 2 ciclos (`dfco_release_fine.csv`):
   combustível 0 e torque indicado 0 de 6702 RPM (14069087 ticks) até 1806 RPM (16571634 ticks); a injeção volta na janela seguinte (RPM médio 1611, 0.3249 g/s) e a marcha lenta se restabelece em ~900 RPM.
   Isso é compatível com o limiar de ~1500 RPM informado (resolução limitada: janelas de médias).
   Casos adicionais com o TPS em 0 V ou preso em valores de "fechado" não são realistas (0 V é falha, e o TPS no batente acompanha o batente móvel pelo atuador de lenta; um TPS preso quebra a
   malha de posição da lenta) e não são interpretados; em alguns a borboleta nem abriu ou o motor não pegou. Informação do proprietário: o atuador é um batente dinâmico de rosca sem fim com motor DC e há um interruptor de lenta que identifica o TPS no batente; a ECU opera em
   malha fechada TPS ↔ atuador enquanto o interruptor está pressionado (borboleta no batente); toda aceleração intencional puxa o cabo, vence a folga (1 mm no simulador) e só então move a borboleta.
   Tudo isso está modelado (`ThrottleAssembly`, `IdleActuator`). Em aberto: reproduzir o corte com TPS que acompanha o batente e atuador/interruptor realmente defeituosos.
9. **Autocalibração durante a operação, marcha lenta e em carga (Tabela P23).** Variáveis retidas após 300 M ticks de marcha lenta e após 200 M ticks sob carga parcial: o integrador lambda F80Ch
   (76 → 97) e a posição do atuador de lenta F83Dh (7 → 10) variam com o regime; a correção de longo prazo F86Ch varia 1 passo (250 → 249) sob carga; F86Fh (aditivo de lenta) e F8E8h/F8E9h
   não variam; sem falhas. O efeito mensurável na plena carga do estado longo é ≤ 0,4 % (Tabela P17). Conclusão: existe adaptação lenta e pequena (lenta e carga), sem relação causal demonstrada com a potência.

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
- **Tabela de DTC decodificada (`4329h`–`4431h`, `tools/dtc_table_decode.py`).** A entrada é `6E27h + 3·R3 + R7`, com R7 ∈ {0, 3, 6, 9} escolhido pela própria rotina:
  R3 ≥ 12 → 9; R3 = 11 → 6 ou 9; R3 = 9 e 10 → 0, 3 ou 6; R3 ≤ 8 → 0 (R7 é a variante dentro do grupo, ligada ao contador em IRAM @A7h e aos bits de `89h`). Isso explica o
  "deslocamento de 3 entradas" que medi. As seis pares falha → DTC transmitidos pela ROM conferem com a decodificação (tabela abaixo).

| grupo R3 | bit XRAM | R7 (bytes) | entrada | DTC / status |
|---:|---|---:|---|---|
| 1 | F84E.0 | 0 | 6E2A | 0402/1D |
| 2 | F84E.1 | 0 | 6E2D | 0402/1E |
| 3 | F84E.2 | 0 | 6E30 | 0402/1E |
| 4 | F84E.3 | 0 | 6E33 | 1A01/1B |
| 5 | F84E.4 | 0 | 6E36 | 3102/0A |
| 6 | F84E.5 | 0 | 6E39 | 3102/09 |
| 7 | F84E.6 | 0 | 6E3C | 1902/0B |
| 8 | F84E.7 | 0 | 6E3F | 1902/08 |
| 9 | F84F.0 | 0 | 6E42 | 0602/1B |
| 9 | F84F.0 | 3 | 6E45 | 0602/1B |
| 9 | F84F.0 | 6 | 6E48 | 0602/1C |
| 10 | F84F.1 | 0 | 6E45 | 0602/1B |
| 10 | F84F.1 | 3 | 6E48 | 0602/1C |
| 10 | F84F.1 | 6 | 6E4B | 0602/1F |
| 11 | F84F.2 | 6 | 6E4E | 0602/1D |
| 11 | F84F.2 | 9 | 6E51 | 0602/1E |
| 12 | F84F.3 | 9 | 6E54 | 0A02/1E |
| 13 | F84F.4 | 9 | 6E57 | 0A02/1D |
| 14 | F84F.5 | 9 | 6E5A | 0A02/9E |
| 15 | F84F.6 | 9 | 6E5D | 0B02/1E |
| 16 | F84F.7 | 9 | 6E60 | 0B02/1D |
| 17 | F850.0 | 9 | 6E63 | 0D02/03 |
| 18 | F850.1 | 9 | 6E66 | 0302/03 |
| 19 | F850.2 | 9 | 6E69 | FFFF/00 |
| 20 | F850.3 | 9 | 6E6C | 0A02/1B |
| 21 | F850.4 | 9 | 6E6F | 0D02/1D |
| 22 | F850.5 | 9 | 6E72 | 0D02/1C |
| 23 | F850.6 | 9 | 6E75 | 0303/03 |
| 24 | F850.7 | 9 | 6E78 | 6300/00 |

Validacao contra os DTC transmitidos pela ROM na K-line:

| caso | R3 | R7 | decodificado | transmitido | confere |
|---|---:|---:|---|---|---|
| ECT aberto (ADC3 5 V) | 12 | 9 | 0A02/1E | 0A02/1E | sim |
| ECT em curto (0 V) | 13 | 9 | 0A02/1D | 0A02/1D | sim |
| ar aberto (ADC2 5 V) | 15 | 9 | 0B02/1E | 0B02/1E | sim |
| ar em curto (0 V) | 16 | 9 | 0B02/1D | 0B02/1D | sim |
| TPS2 alto (F84F.2) | 11 | 9 | 0602/1E | 0602/1E | sim |
| TPS1 alto (F84E.3) | 4 | 0 | 1A01/1B | 1A01/1B | sim |

- Cautela (superada pela decodificação acima): minha primeira decodificação direta da tabela `6E27h` pelo índice do bit (R3 → 6E27h + 3·R3) previu DTC errado
  para os bits de F84F (ECT aberto → F84F.3 que, lido assim, daria 0602); a ROM de fato transmite 0A02/1E. A indexação real
  inclui R7, agora decodificado.
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

### E.4 Enriquecimento: plena carga em regime, aceleração e uso da sonda (investigação da ROM, autorizada pelo proprietário)

Perguntas do proprietário: (1) a ECU deixa de usar a sonda lambda em plena carga? (2) com variação de carga ela costuma ignorar a lambda e enriquecer a mistura.

1. **Plena carga em regime: a ROM segue a sonda e não enriquece.** Sonda travada rica só **depois** de a borboleta abrir (12,5 M ticks) leva o λ de 1,004 a 1,055 (3000 RPM) e de 1,004 a 1,048 (5000 RPM), os mesmos valores de quando a
   trava vem desde o ocioso (Tabela P28): a malha continua ativa em plena carga. Com a sonda travada pobre depois da rampa o λ só cai a 0,9905 (3000 RPM) e 0,9817 (5000 RPM): a autoridade de enriquecimento
   da malha é menor que a de empobrecimento. Em toda a faixa de 1500 a 6000 RPM o λ de plena carga fica entre 0,945 e 1,066 nos dois extremos (Tabelas P25 e P26); entre 80 % e 100 % de pedal o λ é constante (a carga derivada IRAM 70h
   vai de 218 a 255 e satura, Tabela P27), logo não há zona de enriquecimento de plena carga no mapa base nem na malha.
2. **Enriquecimento de aceleração: existe.** Em tip-in de ocioso (Tabela P29) o λ cai a 0,758 (cerca de 25 % mais rico) por ~0,4 s enquanto a rotação passa de ~1300 a ~2000 RPM e volta a ~0,94 em 3000 RPM; em rampa de pedal de 0,8 s o λ fica em
   0,83 durante toda a rampa (0,834 a 3000 RPM e 0,832 a 4500 RPM). É o comportamento esperado de uma bomba de aceleração por variação de carga.
3. **Na variação de carga a ROM não ignora a sonda:** com a sonda travada rica o mínimo do transiente sobe de 0,758 para 0,825 e o λ vai a 1,137 a 4500 RPM; com a sonda travada pobre o λ fica em 0,877 a 3000 RPM e 0,923 a 4500 RPM
   (contra 0,939 e 1,103 com a sonda livre). A correção da sonda se soma ao enriquecimento transitório; a hipótese "a ECU ignora a lambda durante a variação de carga" **não** se sustenta nesta ROM com este estímulo.
4. **Conclusão:** esta ROM não tem enriquecimento de potência de plena carga em regime (o λ de plena carga é ~1,0 em toda a faixa) e tem enriquecimento de aceleração que a sonda ainda modula. Limite: o teste é com a calibração
   desta ROM e o modelo de ar do simulador; um mapa de combustível que dependesse de variável não exercitada (rotação acima de 6000 RPM, temperatura fora de 60–105 °C) não está coberto. O texto das seções D e E que dizia que o enriquecimento
   não estava resolvido refere-se ao regime; o transiente está agora demonstrado.

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
- Tensão real da trilha 2 do TPS a 90° no carro: deixou de afetar a potência (Tabela P18), só decide se IRAM 6Dh.0 liga; o pull-up de TPS ausente e a regra exata
  de contradição entre pistas não foram decodificados.
- Qual rotina consome IRAM 6Dh.0 para elevar o avanço (nexo medido, não rastreado instrução a instrução) e se há enriquecimento por TPS:
  nenhum foi observado até 100 % de pedal, mas só com TPS2 abaixo de F0h ou forçado a 5 V.
- Janela 70–80 °C: a ROM precisa de arranque maior que 0,5 s para pegar (Tabela P15); o mecanismo de partida não foi decodificado. Não é pane nem limiar `721Dh`.
- Polaridade física dos divisores NTC e curvas reais; o grupo R3 = 17–24 (F850) não teve gatilho de sensor exercitado, só decodificado da tabela.
- Histórico de longa duração (horas) e carga parcial prolongada; a lógica de congelar/restaurar F86Ch (`1722h`) não teve suas condições (`27h.6`, `2Fh.1`) decodificadas.
- Temperatura de admissão real do carro em plena carga (modelo térmico não validado).
- Avanço real do motor (PMS físico) e MBT medido em dinamômetro.
- Canal P5.0/P5.1 e atrasos do estágio de ignição: só a hipótese vigente foi mantida, sem teste novo.

- Calibração do TPS pelo procedimento de regulagem do manual: a arquitetura de aceleração está modelada e respeitada pela bancada (puxão do cabo 0 a 40,27 mm = folga de 1 mm + raio × 90°;
  ângulo do cabo = (puxão − folga)/raio; borboleta = máx(cabo, batente); interruptor de lenta abre quando o cabo se afasta do batente; batente móvel pelo motor DC, 4° estimado em `SEVEL_COSIM_PROGRESS.md`),
  mas a calibração elétrica já existe e é a do manual MA1.7 (Alfatest), do material de bancada e da ROM (`SEVEL_COSIM_PROGRESS.md`, seção do perfil de bancada): o dyno usa `--tps-bench-profile` (pista 1 em 0,27 V a 0°, 1,00 V a 4° e 4,65 V a 24°; pista 2 de 0 V até 18° a ~4,5 V a 90°), dentro das faixas de referência (pista 1: 0,20–0,27 V fechada, ~1,00 V na lenta, 4,50–4,80 V acima de 24°; pista 2: 4,30–4,60 V na abertura total) e ancorada no par ADC 40/95 aceito pela ROM no batente estimado de 4°. São referências de sistema, não medições deste corpo de borboleta; o que falta é a medição própria da regulagem no carro.

## H. Recomendações

1. Substituir o modelo da bomba por uma curva limitada (potência de dezenas a poucas centenas de W) e recalibrar o conjunto; maior ganho (até 13 kW a 6000 RPM).
2. Decidir a lei do torque × carga da bobina; a opção `spark_torque_saturate` mostra +4–5 kW.
3. Padronizar a comparação isolada × ROM (acessórios, temperatura do ar, força de centelha).
4. Medir a tensão real das duas trilhas do TPS (curva elétrica do modelo é estimativa) e decodificar a regra de contradição entre pistas e o consumo de IRAM 6Dh.0.
   Investigar por que a janela 70–80 °C exige arranque mais longo.
5. Calibrar o TPS e a posição do êmbolo do batente pelo procedimento de regulagem do manual (tensão no batente, curvas das duas pistas) e refazer os testes de aceleração (cabo → folga → TPS) e de falha de lenta/TPS.
6. Repetir a matriz com mais pontos de RPM e com 117/123° de PMS.

## I. Correções aplicadas ao padrão (autorizadas pelo proprietário)

Duas correções saíram de flags `--exp` para o padrão do modelo, com os achados F-1 e F-2 da seção F:

- **F-1, bomba-d'água:** `AccessoryParams::pump_nm_at_ref` de 0,5 para 0,02 N·m a 925 RPM (≈ 0,5 kW a 6000 RPM, dentro de 0,3–1 kW; estimativa a trocar pela curva real). O modelo anterior chegava a ~13 kW.
- **F-2, força de centelha:** o torque do pulso segue a fração de queima (`força / 0,8`, limitada a 1) e não a força bruta. `--exp spark_torque_legacy=1` restaura a lei anterior.

Não foi necessário recalibrar a VE: a planta isolada usa força 1,0 e não inclui acessórios, então não muda (`docs/dyno/fase2` permanece válido). A correção do alternador (`alternator_ratio` dividindo o torque) ficou de fora, pois pesa < 1 N·m.

Resultado, regenerado a partir dos CSVs (`tools/power_gap_postfix.py`; `docs/dyno/rom/` regenerado; o CSV de antes está em `docs/dyno/investigation/pre_fix_sweep_tdc120.csv`):

| RPM | isolada 20 C [kW] | ROM antes da correcao [kW] | ROM apos a correcao [kW] | deficit antes [%] | deficit apos [%] | torque de eixo apos [N.m] | acessorios apos [N.m] |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1500 | 19.74 | 14.81 | 16.79 | 25.0 | 15.0 | 106.8 | 1.50 |
| 3000 | 40.80 | 31.31 | 37.08 | 23.3 | 9.1 | 118.0 | 0.93 |
| 4500 | 56.75 | 42.43 | 52.86 | 25.2 | 6.9 | 112.1 | 0.96 |
| 6000 | 60.07 | 39.21 | 57.00 | 34.7 | 5.1 | 90.7 | 1.20 |

Varredura completa da ROM apos a correcao (PMS 120 graus):

| RPM | potencia [kW] | torque [N.m] | avanco [graus] | lambda | estado |
|---:|---:|---:|---:|---:|---|
| 1500 | 16.79 | 106.8 | 7.10 | 1.0001 | ACCEPTED |
| 2000 | 23.37 | 111.4 | 10.99 | 0.9951 | ACCEPTED |
| 2500 | 29.67 | 113.2 | 13.78 | 0.9953 | ACCEPTED |
| 3000 | 37.08 | 118.0 | 18.59 | 1.0023 | ACCEPTED |
| 3500 | 43.03 | 117.4 | 21.07 | 1.0007 | ACCEPTED |
| 4000 | 48.42 | 115.6 | 23.76 | 1.0007 | ACCEPTED |
| 4500 | 52.86 | 112.1 | 25.53 | 1.0005 | ACCEPTED |
| 5000 | 56.71 | 108.2 | 26.99 | 0.9976 | ACCEPTED |
| 5500 | 58.07 | 100.8 | 27.95 | 0.9972 | ACCEPTED |
| 6000 | 57.00 | 90.7 | 29.34 | 0.9977 | ACCEPTED |

Pico da ROM em PMS 120°: 58,07 kW a 5500 RPM (isolada: 61,64 kW; referência ABNT: 60,4 kW a 6000 RPM, de motor e combustível diferentes). A varredura é 30/30 ACCEPTED.

**Efeitos nos testes (suíte 352/352 após a atualização):** os testes que codificavam a lei antiga foram atualizados com justificativa no próprio código: bomba (`PhysicsLosses.AccessoryTorqueAtIdleAndHighSpeed`) e força de centelha
(`Combustion.WeakSparkLeavesFuelAndOxygenForExhaust`); limiares de transiente em `test_ignition_phase.py`, `test_adc4_ratio.py`, `test_fuel_blend_closed_loop.py`, `test_lambda_table_to_cc3.py`,
`test_lambda_active_path.py` e `test_physical_idle.py`. Em `test_physical_idle.py` o mínimo de 10 mrad do batente, que antes não gerava falha, agora aciona a falha F84E = 8 (a marcha lenta quente precisa de menos ar com o torque corrigido)
e a velocidade do atuador que acompanha o pedal passou de (40, 50] para (37, 40] mm/s. Nenhuma asserção foi removida; cada limiar atualizado traz o valor medido.

**Limitação:** as tabelas das seções C a E foram geradas antes da correção (`matrix_pre_fix.csv`, `decomposition_pre_fix.md`, Tabelas P1–P24) e continuam válidas como diagnóstico; reproduzem-se com
`--exp spark_torque_legacy=1 --exp acc_pump_scale=25`.

