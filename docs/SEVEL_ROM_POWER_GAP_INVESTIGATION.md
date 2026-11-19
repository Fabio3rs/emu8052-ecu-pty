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
| PMS assumido altera o avanço | PMS não confirmado | Varredura 117/120/123 (GOAL_DYNO_ROM) | Já documentada: picos 42,4–44,3 kW | Resposta ao PMS assumido, não determina o PMS físico | Média | Inconclusiva |

## E. Comportamento adaptativo da ROM

- **Confirmado no assembly:** nada novo foi desmontado neste goal. O inventário anterior
  (`MA17_SEMANTIC_INVENTORY.md`) lista adaptação de purga EVAP, correção de combustível de longo prazo
  e aditivo de marcha lenta como posições da tabela de transmissão (descrições do scanner, não provadas).
- **Observado na execução:** com a borboleta a 90° a ROM lê IRAM 66h (TPS trilha 1) = 238 em todos os
  pontos (saturada), IRAM 61h = 166 (bateria), e opera em malha fechada de lambda (IRAM 65h oscilando
  105–153, λ ≈ 1,00). O contador XRAM F8E8 termina em 2–8 conforme o histórico. A potência não depende
  do histórico testado (Tabela 6).
- **Sem evidência:** modo conservador, limitação por diagnóstico ou proteção. Nenhuma cadeia causal
  estado → rotina → avanço/combustível → trabalho foi encontrada; não foi pesquisada exaustivamente
  (ver G).

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
- A ROM tem enriquecimento de plena carga ou corte de avanço por detonação? Exige análise de assembly
  das rotinas de carga e experimentos com TPS/carga contrafactual, não feitos aqui.
- Reinicialização com e sem RAM retida (item 6 e 7 dos experimentos temporais) e histórico de longa duração.
- Temperatura de admissão real do carro em plena carga (modelo térmico não validado).
- Avanço real do motor (PMS físico) e MBT medido em dinamômetro.
- Canal P5.0/P5.1 e atrasos do estágio de ignição: só a hipótese vigente foi mantida, sem teste novo.

## H. Recomendações

1. Substituir o modelo da bomba por uma curva limitada (potência de dezenas a poucas centenas de W) e recalibrar o conjunto; maior ganho (até 13 kW a 6000 RPM).
2. Decidir a lei do torque × carga da bobina; a opção `spark_torque_saturate` mostra +4–5 kW.
3. Padronizar a comparação isolada × ROM (acessórios, temperatura do ar, força de centelha).
4. Investigar no assembly a estratégia de plena carga (enriquecimento, avanço) e o conteúdo de F8E8.
5. Repetir a matriz com mais pontos de RPM e com 117/123° de PMS.
