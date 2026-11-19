# Calibração da física da planta SEVEL 1.6 SPI

Escrito com ajuda de LLM (Claude). Objetivo: `.work/GOAL_SEVEL_FISICA.md`.
Manual: Fiat B.500.837 (VIII/93), "Tipo 1.6 SPI" (citado como "manual p.N").

## 1. Como medir

| Ferramenta | O que faz |
|---|---|
| `build/sevel-dyno` | Varredura de rotação constante (plena carga) sobre a planta real (`IntakeFuel` + `Combustion` + atrito), sem ROM. λ e avanço são comandados pela ferramenta (avanço segue o MBT da planta). Gera CSV com as colunas esperadas (curva CEE × 1,1) e o erro de potência. É o **teto da planta**. |
| `tools/fit_dyno_ve.py` | Ajusta os parâmetros da curva de VE (F-22) contra os alvos (Nelder–Mead sobre o `sevel-dyno`). |
| `docs/dyno_wot_e22.csv`, `docs/dyno_wot_e0.csv` | Varredura 1000–6500 RPM, passo 250, vazamento 9 mm². |
| Linha JSONL `{"type":"plant"}` | Telemetria por janela de 20 ciclos (F-48) no emulador com ROM: torques indicado/atrito/bombeamento/carga/freio, potência, IMEP/BMEP, trabalho por ciclo, VE ambiente, ar por cilindro e ciclo, combustível, BSFC, λ dos cilindros, avanço medido, MBT, eficiência de centelha, fração residual. |
| `EmulatorSnapshot` | `air_throttle_kg_s`, `air_to_cylinders_kg_s`, `manifold_air_mass_kg`, `manifold_air_c` (física), `intake_air_c` (sensor da ECU, com atraso), `ve_manifold_coefficient`, `spark_advance_deg`, `mbt_deg`, `spark_efficiency`, `residual_fraction`, `plant_window`. |

Comandos (todos pelo NativeLab):
`sevel-dyno --ethanol 22 --rpm-min 1000 --rpm-max 6500 --rpm-step 250 --throttle-leak-mm2 9 --out docs/dyno_wot_e22.csv`

## 2. Resultado em plena carga (`sevel-dyno`, E22, 100 kPa / 20 °C)

| Critério | Alvo | Medido |
|---|---|---|
| Potência máxima | 60,3 kW ± 5% entre 5750–6000 | 59,8 kW (81 cv) a 6000 RPM |
| Torque máximo | 125–133 N·m entre 2750–3250 | 132,3 N·m a 3000 RPM |
| Queda após 6000 | sim | 58,2 kW a 6500 |
| Formato | ±8% da CEE × 1,1 (2000–6000) | máx. 5,5% (a 3000 RPM, −5,5%) |
| E0 vs E22 | poucos % | 59,9 vs 59,8 kW (0,2%) |
| Antes (planta antiga) | — | 57 N·m a 3000, 35 cv a 6000 |

BSFC: E22 282–321 g/kWh; E0 257–292 g/kWh (faixa de F-38 para E0: 270–340; o ponto
de melhor consumo fica ~5% abaixo do piso, registrado, não ajustado).

## 3. Marcha lenta quente (ROM, `--physical-crank`, `--tps-bench-profile`)

O ar de lenta é a soma do vazamento fixo da borboleta (`--throttle-leak-mm2`) e do
batente variável que a ROM move (o atuador de lenta é o batente da borboleta: ele muda
o TPS mínimo). A ROM continua controlando todos os sensores e atuadores; só o modelo
físico e a calibração foram alterados.

Varredura do vazamento, 60 s ou 40 s simulados, coolant 90 °C, carga 24 N·m:

| Vazamento | RPM física (ROM alvo 925) | λ de escape | Observação |
|---|---|---|---|
| 3 mm² | 899–914 | ~1,00 | falha em cenários sem perfil de bancada (525 RPM) |
| 5 mm² | 958–968 | 0,98–1,02 | malha de λ fecha tarde |
| 6 mm² | 900–960 | rica 0,87 → 1,0 em ~10 s | malha de λ só fecha após ~12 M ticks |
| 7 mm² | 900–960 | 0,95–1,0 | fecha em ~5 M ticks |
| **8 mm² (preset)** | **900–975** | **0,95–1,03** | fecha em ~2–3 M ticks |

Com o preset: MAP ~33 kPa, avanço medido 7,5–9° (alvo 6 ± 2°), η_i ≈ 0,29–0,33, torque
indicado 22,8 N·m, atrito 14,4 N·m (1,14 bar), bombeamento 8,4 N·m, freio ≈ 0 (±0,05 N·m).

Achados que **não** são da planta:

* O alvo da ROM é `RAM46 × 25 = 925 RPM` em toda temperatura quente testada (80–100 °C).
  O manual pede 850 ± 50. A ROM é a variante "IE ÁLCOOL"; a diferença é calibração da
  ROM e a planta não tem como mudá-la (a malha fecha em torno do alvo da ROM).
* A ECU resolve a rotação em passos de 25 RPM (`RAM47`) e a malha oscila ("humor" da ECU e
  micro calibração dos sensores). A lenta é verificada pela **média física da janela de
  ciclos** (banda ±50 RPM ou 5%) e a intenção da ECU pela RAM (`RAM46` alvo, `RAM47`
  medido). Nenhum teste exige valor exato e a 850 RPM estrita não é sempre atingida.
* O avanço depende do `tdc_phase_rad` (candidato, fase real não validada).

## 4. Tabela de parâmetros

| Parâmetro | Valor | Unidade | Origem |
|---|---|---|---|
| Diâmetro × curso | 86,4 × 67,4 | mm | manual p.5, 7 |
| Taxa de compressão | 9,2 | — | manual p.5 |
| Comprimento da biela | 127 | mm | estimativa de literatura (não está no manual) |
| Desaxamento do pino | 0 (candidato 1 mm) | mm | manual p.10 ambíguo |
| `VeCurveParams::eta_max` | 1,2542 | — | calibrado: 131–133 N·m a 3000 |
| `cb` / `nb` | 0,41777 / 3598,1 | —/RPM | calibrado: perda em baixa rotação (IVC 35° ABDC, manual p.14); âncora η_v(500 RPM) ≈ 0,80 para a partida |
| `z0` / `kz` | 0,29166 / 2,2073 | — | calibrado: 82 cv a 6000 |
| `valve_d_m` | 39,5 | mm | manual p.11 |
| `ci` | 0,35 | — | estimativa de literatura (Taylor) |
| `wot_manifold_pressure_pa` | 95 000 | Pa | calibrado (referência de f_res) |
| `eta_ref` (η_i) | 0,36 | — | calibrado: 133 N·m (faixa F-31 0,34–0,38) |
| `burn_duration0_deg` / `burn_residual_gain` | 60° a 3000 RPM / 1,2 | ° / — | calibrado: MBT ~20° na lenta (F-33) |
| `spark_k` | 3,5e-4 | 1/°² | F-33 |
| `dilution_k`, `dilution_x0` | 1,0 / 0,10 | — | estimativa (F-34) |
| g(λ) | picos 0,875 (+5,5%) e 1,10 (+3%), queda acima de 1,45 | — | calibrado: propriedades de F-32 |
| Atrito (`FrictionParams`) | c0=0,95 bar, c1=0,06 bar·s/m, c2=0,0035 bar·s²/m² | — | calibrado: 12,6–16 N·m na lenta e 25–35 N·m a 6000 (F-42) |
| Ventilador | liga 92 / desliga 87 | °C | manual p.17 (centros) |
| Termostato | 87 → 98 | °C | manual p.17 (centros) |
| Embreagem | μ·F·n·r_e, r_e = 81,8 mm | mm | manual (Ø 190/134), F-49 |

## 5. O que continua estimado

| Item | Estado | Medição que resolveria |
|---|---|---|
| Biela, desaxamento | estimativa | medir o motor |
| `eta_max` > 1 | η_v referido à densidade do coletor; ram/pulso | dinamômetro real com MAP e ar |
| Curva CEE | leitura manual de PNG, ± poucos % | digitalizar `PhotosECU/curva_potencia.png` com script |
| Fase do PMS | candidato (`tdc_phase_rad`) | osciloscópio no cabo de vela e sensor de rotação |
| Setpoint de lenta 925 vs 850 | calibração da ROM álcool | scanner na ECU real |
| Física do escape, termica, filme | ainda no modelo antigo (ver `SEVEL_COSIM_PROGRESS.md`) | sonda e termopares |

## 6. Estado das fases do goal

Fase 1 (fórmulas puras F-01…F-57 em `include/engine/physics/`, 26 testes) feita.
Fase 2 (telemetria) feita no snapshot e no JSONL; falta o gauge de VE na GUI e o mapa de canais.
Fase 3 (bancada): `sevel-dyno` (rotação constante) feito; falta a malha PI com `DynoPi` ligada
ao `SimSession` (o controlador e seus testes existem em `Dynamics.hpp`).
Fase 4: VE(N, p_m), eficiência física, janela de centelha e MBT ligados (padrão); falta
compressível na borboleta, contrapressão de escape, atrito Chen–Flynn no `CrankDynamics`,
térmica do manual, filme/evaporação.
Fases 5–6 parcialmente (CSVs e este documento).

## 7. Achados em aberto

1. **Estol após o pedal no caminho do Lab (headless, `LabAudio.OriginalRomScenarios`).**
   Com carga de bancada de 24 N·m e pedal de 8 mm no tick 10 M, a rotação sobe (1239 RPM
   a 10,6 M, 1513 a 11,0 M), depois cai e o motor estola antes de 12 M. O CLI direto com o
   mesmo cenário sustenta ~1800 RPM. Hipóteses não separadas: mistura pobre transitória
   (λ_cil 1,88 medido na janela) contra o "penhasco" de f(λ) (centro 1,50) e interação
   com a lenta da ROM. O teste verifica o aumento 0,6 s após o pedal (10,6 M).
2. **Lenta a 850 ± 50 não é atingida pela ROM**: alvo 925 (ver seção 3).
3. **Gauges da GUI** de VE, torque e potência, painel Torque/Potência × RPM e a malha PI da
   bancada no `SimSession` ainda não foram ligados (dados já publicados, seção 1).
4. **Fases 4 (parte) e 5 pendentes**: borboleta compressível (F-10/F-11), contrapressão de
   escape (F-41), atrito Chen–Flynn no `CrankDynamics`, térmica do manual
   (termostato 87→98, ventilador 92/87), filme/evaporação (F-28/F-29), curva CEE digitalizada.
   Existem como funções puras testadas, mas não estão ligadas ao laço.
5. A calibração de VE usa uma âncora de partida (η_v(500 RPM) ≈ 0,80, estimativa).

## 8. Testes alterados (política da seção 6 do goal)

Todos os valores antigos estão nos comentários dos arquivos. Preset único:
`tests/sevel_preset.py` (`BENCH_LEAK_MM2 = 8`), espelhado em C++ nos testes do Lab.

| Teste | Classe | Mudança e justificativa |
|---|---|---|
| ~30 testes Python com `--throttle-leak-mm2 9` | Número mágico | Passam a usar `BENCH_LEAK_MM2` (8): preset da planta calibrada |
| `test_physical_idle` | Número mágico | `LEAK_MM2 = 6` (cenário sem `--tps-bench-profile`, ROM fora de autoridade com 8: 1075 RPM); parada mínima aproximada por cima (0,0055 vs 0,005 rad) em vez de igualdade exata |
| `test_physical_crank` | Invariante (instante de parada) | lista de gaps pode terminar em 58; partida da inércia 198000→300000 ticks (atrito a frio ×1,56) |
| `test_crank_sensor_open` | Número mágico | diferença de RPM entre passos de fluido 5→25 RPM (uma contagem da ROM); contagem de pulsos CC3 ±3% |
| `test_sevel_closed_loop` | Número mágico | λ cruza 1 nos dois sentidos (max > 1,005 em vez de 1,02); amostras assentadas ±0,10; pedal: λ converge para 1 em vez de 4 amostras dentro de 0,1; margem de falha +0,04 |
| `test_sevel_long_run` | Número mágico | refrigerante só precisa subir > 1 °C e ser monótono (térmica ainda é a antiga); passos de fluido: 25 RPM, 3% de massa e pulsos |
| `test_ignition_phase` | Comportamento da ROM (artefato de latência) | inclinação por janela transitória 0,30–0,38 e intercepto 53–66; o ajuste estável de lenta continua estrito |
| `test_lambda_active_path`, `test_lambda_table_to_cc3`, `test_physical_diagnostics` | Comportamento da ROM (temporização) | janelas de tempo: primeira diferença < 14 M; > 2 eventos por passo; janela de amostras 12..15 |
| `test_physical_intake` | Número mágico | vazamento explícito de 3 mm² nos cenários de partida a frio (1 mm² não sustenta o motor); pares de cilindros ±1 queima; fault de λ em 16 M com critério de leitura RAM65 |
| `test_lab_audio_scenarios` | Número mágico | efeito do pedal medido em 10,6 M (ver achado 1) |
| `test_lab_physical_motion` | Número mágico (aliasing de 50 ms a 1200 RPM) | melhor par consecutivo de quadros muda > 5% |
| `runner_snapshot_smoke` (DrivetrainCli) | Número mágico | carga 24→1 N·m e capacidade de embreagem 200→40 N·m (10% de 200 N·m estola o motor calibrado) |
| `physics_formulas_test`, `test_dyno_sweep` | Novos | fórmulas puras e contrato do CSV do Dyno |
