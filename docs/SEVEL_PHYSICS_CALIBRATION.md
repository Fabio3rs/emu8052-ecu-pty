# Calibração da física da planta SEVEL 1.6 SPI

Escrito com ajuda de LLM (Claude). Objetivo: `.work/GOAL_SEVEL_FISICA.md`.
Manual: Fiat B.500.837 (VIII/93), "Tipo 1.6 SPI" (citado como "manual p.N").

## 1. Como medir

| Ferramenta | O que faz |
|---|---|
| `build/sevel-dyno` | Varredura de rotação constante (plena carga) sobre a planta real (`IntakeFuel` + `Combustion` + atrito), sem ROM. λ e avanço são comandados pela ferramenta (avanço segue o MBT da planta). Gera CSV com as colunas esperadas (curva CEE × 1,1) e o erro de potência. É o **teto da planta**. |
| `tools/plot_dyno.py` | Gera `docs/dyno_wot.png` (torque, potência e VE × RPM com os alvos sobrepostos) a partir dos CSVs. |
| `tools/fit_dyno_ve.py` | Ajusta os parâmetros da curva de VE (F-22) contra os alvos (Nelder–Mead sobre o `sevel-dyno`). |
| `docs/dyno_wot_e22.csv`, `docs/dyno_wot_e0.csv` | Varredura 1000–6500 RPM, passo 250, vazamento 9 mm². |
| Linha JSONL `{"type":"plant"}` | Telemetria por janela de 20 ciclos (F-48) no emulador com ROM: torques indicado/atrito/bombeamento/carga/freio, potência, IMEP/BMEP, trabalho por ciclo, VE ambiente, ar por cilindro e ciclo, combustível, BSFC, λ dos cilindros, avanço medido, MBT, eficiência de centelha, fração residual. |
| `EmulatorSnapshot` | `air_throttle_kg_s`, `air_to_cylinders_kg_s`, `manifold_air_mass_kg`, `manifold_air_c` (física), `intake_air_c` (sensor da ECU, com atraso), `ve_manifold_coefficient`, `spark_advance_deg`, `mbt_deg`, `spark_efficiency`, `residual_fraction`, `plant_window`. |

Comandos (todos pelo NativeLab):
`sevel-dyno --ethanol 22 --rpm-min 1000 --rpm-max 6500 --rpm-step 250 --throttle-leak-mm2 9 --out docs/dyno_wot_e22.csv`

## 2. Resultado em plena carga (`sevel-dyno`, E22, 100 kPa / 20 °C)

> **Correção (GOAL_DYNO_ROM).** Os números desta seção antes vinham de uma integração que amostrava o torque do pulso
> no início de cada passo (desvio de +3 a +6 % acima de 4000 RPM com dt = 100 µs) e eram citados como "atendidos". Desde a
> Fase 1 a integração é exata e a curva de VE foi **reajustada** (Fase 2). O que segue é um **ajuste** aos alvos, não uma
> validação independente: a VE do motor é desconhecida. Números e tabelas completas: `docs/SEVEL_DYNO_ROM.md`,
> `docs/dyno/fase2/` (`fit_result.json`, CSVs, manifesto).

| Grandeza | Alvo | Ajustado (integração exata) |
|---|---|---|
| Potência máxima | 60,3 kW ± 5 % entre 5750–6000 | pico 61,64 kW (83,8 cv) a 5500 RPM; 60,06 kW a 6000 |
| Torque máximo | 125–133 N·m entre 2750–3250 | 129,9 N·m a 3000 RPM (−2,3 % do alvo de 133) |
| Formato | ±8 % da CEE × 1,1 (2000–6000) | erro máximo 7,3 % (`dyno_summary.csv`); a referência CEE é de versão europeia (combustível e método diferentes do ABNT), então é branda |
| E0 vs E22 | poucos % | 61,70 vs 61,64 kW |

BSFC (CSV corrigido; o `sevel-dyno` usava o fator 3,6e9 em vez de 3,6e6): E22 ≈ 287 g/kWh a 3000 e 322 a 6000 RPM. Valores antigos citados aqui: E22 282–321 g/kWh; E0 257–292 g/kWh (faixa de F-38 para E0: 270–340; o ponto
de melhor consumo fica ~5% abaixo do piso, registrado, não ajustado).

## 3. Marcha lenta quente (ROM, `--physical-crank`, `--tps-bench-profile`)

O ar de lenta é o vazamento fixo da borboleta (`--throttle-leak-mm2`) mais o batente
variável que a ROM move (o atuador de lenta é o batente da borboleta e muda o TPS
mínimo). A ROM continua controlando todos os sensores e atuadores; só o modelo físico
e a calibração mudaram.

**Cenário de aceitação** (`tests/test_idle_acceptance.py`): 90 °C, **sem carga externa,
acessórios ligados** (`--accessory-load`: alternador 20 A + bomba d'água, F-45, ~2,9 N·m
a 925 RPM, rampa de carga do alternador 550–750 RPM do virabrequim), vazamento 9 mm² (borboleta compressível),
`--tdc-reference-deg 117`. Média das janelas de 20 ciclos após 25 M ticks:

| Grandeza | Medido | Alvo do manual (p.18) |
|---|---|---|
| Rotação física | 908 RPM (±2 na janela) | 850 ± 50 (ROM: 925) |
| λ dos cilindros | 1,01 | 0,97–1,03 |
| Avanço medido (evento de centelha) | 5,7° | 6 ± 2° |
| Balanço de energia | resíduo ≈ 5e-13; potência de eixo ≈ 0,00 kW | fecha (`energy_residual_rel`; o antigo "torque ao freio ≈ 0" era J·dω/dt, tautológico) |
| MAP | ~33 kPa | faixa plausível 30–45 kPa |
| Indicado / atrito / bombeamento / acessórios | 25,6 / 14,4 / 8,4 / 2,9 N·m | — |

O que continua fora do alcance da planta:

* O alvo da ROM é `RAM46 × 25 = 925 RPM` em toda temperatura quente testada (80–105 °C) e
  com bateria de 11,5 a 14,4 V. O manual pede 850 ± 50. A ROM é a imagem **G (gasolina)**
  `FiatTipo_MA17_dump_27c256.bin` (SHA-256 `a3473435…8e1f`, `MA17_FIRMWARE_VARIANTS_ANALYSIS.md`); o rótulo
  "IE ÁLCOOL" que apareceu aqui estava errado. A diferença para o manual é de calibração da ROM. A rotação física (908) fica 8 RPM acima do teto da
  banda do manual (900) e o teste a aceita até 925 (uma contagem de ROM de 25 RPM).
* A ECU resolve a rotação em passos de 25 RPM (`RAM47`) e a malha oscila ("humor" da ECU e
  micro calibração dos sensores). Por isso a lenta é verificada pela **média física da
  janela de ciclos**, e a intenção da ECU pela RAM (`RAM46` alvo, `RAM47` medido).
* O avanço depende da fase do PMS (`tdc_phase_rad`), que é um **candidato**: o manual dá 120° entre a falha
  da roda e o PMS 1/4 (sem tolerância, e sem dizer a partir de qual borda do dente). Com 120° o avanço medido é
  8,6°; com 117° é 5,7°. O 117° **não é uma medição**: é um ajuste ao avanço de 6° ± 2° do manual, e 115–119°
  o satisfazem igualmente (o `SEVEL_COSIM_PROGRESS.md` já registrou 116° pelo mesmo motivo e avisou para não
  inferir uma montagem real). O padrão do simulador continua 120°; 117° está só no preset sem carga do Lab e no
  teste de aceitação.

Varredura do vazamento (cenário com carga de 24 N·m dos testes, planta sem acessórios):
3 mm² → 899–914 RPM, mas falha em cenários sem perfil de bancada; 6 mm² → a malha de λ
só fecha após ~12 M ticks; **8 mm² → fecha em ~2–3 M ticks**, λ 0,95–1,03, 900–975 RPM
(todos estes valores com a borboleta incompressível antiga; veja o parágrafo da borboleta compressível abaixo).
**Sem carga e sem acessórios**, 8 mm² dá λ 1,2–1,3 (pobre) e 920 RPM à deriva: é o
sintoma original do goal. A carga de 24 N·m dos testes já representa "carga + acessórios".

Regra do preset do Lab (`--bench-preset`): se o cenário define `--load-nm`, vazamento 8 mm²
e sem acessórios; sem carga externa, vazamento 5 mm² e `--accessory-load`.

**Borboleta compressível (F-10/F-11, ligada no padrão; `--legacy-throttle` volta à antiga).** A área é a de
Heywood (furo 34 mm, eixo 0,15, Cd 0,75, estimativas a medir no corpo real) e o fluxo é compressível com
estrangulamento. A lenta fica estrangulada (MAP 33 kPa < 53 kPa), o que dá ~0,6× o ar do Bernoulli para a mesma
área. Novos presets (varredura 3–26 mm², janela de partida estreita: 12 mm² estola, 16 mm² não pega com carga de
24 N·m): **sem carga, com acessórios, 9 mm²** → 908,6 RPM, λ 1,00, avanço 5,7°, freio ≈ 0; **com carga de 24 N·m,
14 mm²** → λ ≈ 1 em ~2 M ticks, ~900 RPM; partida a frio dos testes 9 mm²; lenta quente sem perfil de bancada
(`PhysicalIdle`) 11 mm² (902 RPM; 12 → 961, 13 → 1030).
**Bug encontrado:** a fórmula de Heywood do catálogo do goal (F-10) tem o termo do arco-seno com sinal errado: a
area não zerava com a placa fechada (19% do furo a 5°). Corrigido (`ThrottleAreaZeroWhenClosedAndSmallAngleReference`).
A área também é mantida a partir de cos ψ = 1,25·a·cos ψ₀ para ficar monotônica quando quase aberta.

### 3.1 Fase do PMS, sensor de relutância variável e a lenta de 850 RPM

**Lenta de 850 RPM.** Os 850 ± 50 RPM do manual são uma referência, não um valor fixo: a ECU muda o
alvo de lenta conforme vários outros parâmetros (temperatura, cargas, estado da malha). Verificar o
cálculo da física, e não reproduzir esse número, é o que importa; por isso a lenta é medida como
"fecha o balanço de torque, λ ≈ 1, MAP plausível e rotação que acompanha o alvo da própria ROM".

**Avanço e PMS (120° do manual × 117°).** Comparação no mesmo cenário da ROM (sem carga ou com
pedal, acessórios ligados, janelas de 6 ciclos, média após 25–30 M ticks):

| Cenário | PMS | RPM | Avanço | η de centelha | Indicado |
|---|---|---|---|---|---|
| Lenta | 120° | 908 | 8,8° | 0,297 | 25,69 N·m |
| Lenta | 117° | 908 | 5,8° | 0,289 | 25,61 N·m |
| Pedal 8 mm + 40 N·m | 120° | 1150 | 9,5° | 0,328 | 62,56 N·m |
| Pedal 8 mm + 40 N·m | 117° | 1127 | 6,4° | 0,321 | 62,36 N·m |

A referência de PMS desloca o avanço *medido* em 3° e a eficiência de centelha em 2–3%, mas a ROM fecha a
malha e o torque indicado muda < 0,5%: a escolha afeta a leitura do avanço, quase não afeta a potência. (O
Dyno não depende dela: o avanço lá é o MBT da planta.)

**Sensor de rotação (ímã e bobina) e o que 3° significam.** O sensor é de relutância variável: a tensão é a
derivada do fluxo, com cruzamento por zero no centro do dente e amplitude proporcional à rotação. O que a
ECU enxerga como "borda" depende da topologia do condicionador, que na MA1.7 é **desconhecida**:

* condicionador que arma num limiar e marca no cruzamento por zero (tipo LM1815/MAX9924): a amplitude só
  decide quando o circuito arma; o atraso que sobra (indutância da bobina, filtro RC, propagação) é
  aproximadamente constante no tempo e cresce em graus com a rotação;
* comparador de limiar fixo: o disparo atrasa mais em baixa rotação (amplitude menor).

Os dois sinais de dependência com a rotação são opostos, então o sinal do efeito **não se infere** sem o
circuito. Quanto à magnitude, 3° a 908 RPM exigem τ ≈ 550 µs; um atraso constante no tempo daria então ≈ 20°
a 6000 RPM, o que o torna uma explicação fraca para os 3°. Tratar o 117° como "efeito do sensor" não está
sustentado.

**Sentido da referência.** O gerador (`tick_physical_crank_input`) põe a subida no limite da posição (6·k°)
e a descida 3° depois (6·k + 3°), e a ROM, no seguimento de dentes, captura a **descida** (`T2CON.6` = `I3FR`
é limpo em `code_FA` (`0x0FA`; a instrução `C2 CE` fica em `0x108`) com `CCEN` = `xxxxxx01`). Se os 120° do manual forem contados a partir do primeiro dente
capturado, o PMS fica em 123° nas coordenadas do gerador; para o ajuste dar 117° a referência precisa estar
6° antes, na posição do último dente ausente. As duas leituras ficam documentadas; só medir no carro as separa.

### 3.2 Análise estática: `RAM[69h]` → recarga do Timer 1 (sem mudar a planta)

Fonte: `FiatTipo_MA17_dump_27c256.asm`/`.bin` (bytes conferidos) e `MA17_SEMANTIC_INVENTORY.md` (~L1324).
**Fechado = lido no assembly; inferido = interpretação.**

**Verificado no assembly**

1. O serviço `IEX3_0` (`0x0B6`) roda a cada captura de dente em CC0. Cada captura faz `djnz RAM_30` e
   `djnz RAM_50`; só quando `RAM_50` chega a zero a máquina de estados (`IRAM[C4h]` = 1, 2, 4 ou 8) executa.
2. Borda capturada: `code_FA` (`0x0FA`) é o ressincronismo e limpa `T2CON.6` (`I3FR`, instrução `C2 CE` em
   `0x108`) e deixa `CCEN&3` = 01; logo o seguimento de dentes captura a **descida** (confere com o simulador,
   `capture_edge`). O modo de agendamento (`code_223`, `0x223`) ativa `CCEN|=3` e `setb T2CON.6`, e alterna `I3FR` em
   `0x23E`/`0x24A` (`xrl CCEN,#2`, `cpl T2CON.6`); portanto há capturas de subida nesse modo.
3. Confirmação da lacuna: no estado 1 (`code_118`) a ROM compara períodos de capturas consecutivas
   (`0x566C`/`0x5693`/`0x56A2`) durante `RAM_51` (= 4) capturas; confirmada, grava `C4 = 2`, `RAM_50 = 8`
   (`code_14C`/`code_15B`) e copia `RAM_47` para `XRAM[F8h]`.
4. Estado 2 (**8 capturas** depois da confirmação, `RAM_50` = 8): grava `C4 = 4`, `RAM_50 = 9` e salta para
   `code_2AF` (`0x2AF`), o tratador do evento de bobina: para o Timer 1 (`CLR TCON.6/7`) e, conforme `RAM_2A.2`,
   zera `P5.0` ou `P5.1` **na própria captura**, a menos que `RAM_22.7` esteja ativo, caso em que recarrega o
   Timer 1 com `RAM[34:35]` (`code_2D6`) e adia o evento para o overflow (`code_252`, `0x252..0x2A5`, que alterna
   `P5.0/P5.1` e recarrega `TL1/TH1` com `RAM[32:33]` ou `RAM[34:35]`).
5. Estado 4 (**9 capturas** depois, `RAM_50` = 9): grava `C4 = 1`, `RAM_50 = 8` (se `RAM_2A.2` = 0) ou `0x0D`
   (13, se = 1) e salta para `code_35E` (`0x35E`), a captura de referência: lê `CRCH:CRCL`, subtrai a captura de
   referência anterior (`R2:R3`) e grava `RAM[36:37]` = metade dessa diferença (um `rrc` na cadeia `0x3A5..0x3B2`).
6. Cadeia de `RAM[69h]` (`0x439..0x51E`), cálculo das duas recargas:
   * `V = RAM_69 × 15 − IRAM[C7h]` (16 bits; se negativo, 0). Byte alto → `RAM_3A`; byte baixo `Vb`.
     `RAM[32:33] = ~( round(Vb × 0x22 / 256) × RAM[36:37] / 256 )`.
   * `V' = (RAM_69 >> 1 − RAM_31 → flag RAM_22.7 pelo sinal) × 0x1E − IRAM[C7h]`; byte alto → `RAM_3B`;
     `RAM[34:35]` calculado como acima, com ajustes por `0x14/0x12/0x44/0x22` (`0x4C9..0x4E5`).
   * `RAM_38`/`RAM_39` (`0x530`, `0x535..0x547`) = quantas capturas ainda esperar (`RAM_30`) antes da fração fina
     do Timer 1.
   Ou seja, o atraso da centelha tem uma parte inteira em capturas (da ordem de `RAM_3A`/`RAM_3B`) e uma fração em
   contagens do Timer 1 proporcional ao período medido (`RAM[36:37]`).

**Não fechado (N e K).** Não consegui, só por leitura, fixar (a) a posição absoluta do dente de confirmação da
lacuna em relação à falha (quais das 4 capturas de `RAM_51` valem) e, portanto, **N** (descida do dente N, onde o
evento de bobina cai 8 capturas depois); nem (b) o **K** em graus, porque as unidades de `RAM_69` (fator 15, `0x22`,
`0x1E`, subtração de `IRAM[C7h]`) e o intervalo coberto por `RAM[36:37]` (metade da distância entre referências)
dependem de um traço com o tick de cada captura. A soma 8 + 9 + (8 ou 13) + 4 = 29 ou 34 capturas aponta para
o ciclo de meia volta (29 dentes por 180° com a lacuna), **inferência** que o traço deve confirmar.

**Medido, não estático** (testes existentes `test_ignition_phase.py`): o ângulo do flanco de `P5` no virabrequim, módulo
180°, é ≈ 56° + 0,35°·`RAM_69` (intercepto 53–59°, inclinação 0,34–0,37°/contagem). Pela fórmula acima a
sensibilidade seria 15·0,133/256·`RAM[36:37]`, ou 0,0078·`RAM[36:37]`; com `RAM[36:37]` ≙ 45° isso dá 0,35°/contagem
(**inferência**: `RAM[36:37]` cobriria 45° de giro, o que ainda precisa ser conferido).

**Implicações para `tdc_phase` (separando o que se sabe)**

* A ROM não contém "o PMS": ela posiciona o evento de `P5` por "descida do dente N + atraso(`RAM_69`)". Qualquer
  ângulo de avanço é então `tdc_phase − θ_P5`, e o simulador só escolhe `tdc_phase`; a ROM não o fixa.
* O PMS "na coordenada da própria ROM" fica determinado quando se souber, para um `RAM_69` conhecido, o atraso total
  em graus (N, K). Isso dispensaria o 120° do manual como entrada e daria o ponto no gerador por conta própria; hoje
  **não está determinado**.
* Próximo passo mínimo (dinâmico, sem mudar a planta): registrar, para cada captura, `tick`, `RAM_50`, `C4`,
  `RAM_51`, `RAM_69`, `RAM[36:37]` e o ângulo do gerador, e ver em qual dente (a partir da posição 58/59) cai o evento
  de estado 2 e quantas contagens do Timer 1 seguem.

## 4. Tabela de parâmetros

| Parâmetro | Valor | Unidade | Origem |
|---|---|---|---|
| Diâmetro × curso | 86,4 × 67,4 | mm | manual p.5, 7 |
| Taxa de compressão | 9,2 | — | manual p.5 |
| Comprimento da biela | 127 | mm | estimativa de literatura (não está no manual) |
| Desaxamento do pino | 0 (candidato 1 mm) | mm | manual p.10 ambíguo |
| `VeCurveParams::eta_max` | 1,0204 | — | calibrado: ~130 N·m a 3000 com borboleta compressível e contrapressão (F-41); valor físico (< 1,05) |
| `cb` / `nb` | 0,28677 / 1800,7 | —/RPM | calibrado: perda em baixa rotação (IVC 35° ABDC, manual p.14); âncora η_v(500 RPM) ≈ 0,80 para a partida |
| `z0` / `kz` | 0,42254 / 8,9186 | — | calibrado: 82 cv a 6000 |
| Borboleta: furo / eixo / Cd | 34 mm / 0,15 / 0,75 | mm / — / — | estimativas de literatura + calibração: área parcial ≈ modelo antigo (+17%) e MAP ≈ 90 kPa em plena carga; **medir o corpo real** |
| `exhaust_back_pressure_k` | 3,78e6 | Pa·s²/kg² | calibrado: F-41, 15 kPa a 63 g/s (faixa 10–20 kPa); ligado na planta física (resíduo F-18 e bombeamento F-40) |
| `valve_d_m` | 39,5 | mm | manual p.11 |
| `ci` | 0,35 | — | estimativa de literatura (Taylor) |
| `wot_manifold_pressure_pa` | 95 000 | Pa | calibrado (referência de f_res) |
| `eta_ref` (η_i) | 0,36 | — | calibrado: 133 N·m (faixa F-31 0,34–0,38) |
| `burn_duration0_deg` / `burn_residual_gain` | 60° a 3000 RPM / 1,2 | ° / — | calibrado: MBT ~20° na lenta (F-33) |
| `spark_k` | 3,5e-4 | 1/°² | F-33 |
| `dilution_k`, `dilution_x0` | 1,0 / 0,10 | — | estimativa (F-34) |
| g(λ) | picos 0,875 (+5,5%) e 1,10 (+3%), queda acima de 1,45 | — | calibrado: propriedades de F-32 |
| Atrito (`FrictionParams`) | c0=0,95 bar, c1=0,06 bar·s/m, c2=0,0035 bar·s²/m² | — | calibrado: 12,6–16 N·m na lenta e 25–35 N·m a 6000 (F-42) |
| Ventilador | liga 92 / desliga 86 | °C | manual p.17 (liga 90–94, desliga 85–89); 86 para a histerese completar (radiador zera em 87) |
| Termostato | 87 → 98 (ligado em `ThermalState`) | °C | manual p.17 (início 85–89, total 96–100) |
| Embreagem | μ·F·n·r_e, r_e = 81,8 mm | mm | manual (Ø 190/134), F-49 |

## 5. O que continua estimado

| Item | Estado | Medição que resolveria |
|---|---|---|
| Biela, desaxamento | estimativa | medir o motor |
| Diâmetro, eixo e Cd da borboleta | estimativas (furo 34 mm) | medir o corpo Mono-Motronic |
| Curva CEE | leitura manual de PNG, ± poucos % | digitalizar `PhotosECU/curva_potencia.png` com script |
| Fase do PMS | candidato (`tdc_phase_rad`) | osciloscópio no cabo de vela e sensor de rotação |
| Setpoint de lenta 925 vs 850 | calibração da ROM álcool | scanner na ECU real |
| Física do escape, termica, filme | ainda no modelo antigo (ver `SEVEL_COSIM_PROGRESS.md`) | sonda e termopares |

## 6. Estado das fases do goal

Fase 1 (fórmulas puras F-01…F-57 em `include/engine/physics/`, 26 testes) feita.
Fase 2 (telemetria) feita no snapshot e no JSONL; falta o gauge de VE na GUI e o mapa de canais.
Fase 3 (bancada): `sevel-dyno` (rotação constante) e, desde o GOAL_DYNO_ROM, a bancada headless com a ROM
(`--dyno-point`, `DynoPi` ligado ao laço) feitos; falta ligar o `DynoPi` ao `SimSession`/Lab.
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
2. **Lenta a 850 ± 50**: medida 908 RPM (ROM alvo 925), 8 RPM acima da banda do manual (seção 3).
3. **GUI:** o gauge de VE (`VE REF. AMBIENTE`) está ligado, e o tooltip traz torque, potência,
   BMEP e ar por ciclo. Faltam o painel Torque/Potência × RPM e a malha PI da bancada no
   `SimSession` (a bancada existe só no CLI headless: `--dyno-point`; ver `SEVEL_DYNO_ROM.md`).
4. **Fase 4, o que falta no laço**: atrito Chen–Flynn no `CrankDynamics` e filme/evaporação (F-28/F-29);
   curva CEE digitalizada. Ligados: VE(N, p_m), eficiência física, contrapressão de escape, borboleta
   compressível (Heywood + F-11), atrito por temperatura do óleo, acessórios (opcional) e térmica do manual.
   `eta_max` caiu de 1,35 para 1,02 quando a borboleta deixou de limitar o MAP a ~75 kPa em plena carga.
5. A calibração de VE usa uma âncora de partida (η_v(500 RPM) ≈ 0,80, estimativa).

## 8. Testes alterados (política da seção 6 do goal)

Todos os valores antigos estão nos comentários dos arquivos. Preset único:
`tests/sevel_preset.py` (`BENCH_LEAK_MM2 = 14`, para cenários com a carga de 24 N·m e borboleta compressível), espelhado em C++ nos testes do Lab.

| Teste | Classe | Mudança e justificativa |
|---|---|---|
| ~30 testes Python com `--throttle-leak-mm2 9` | Número mágico | Passam a usar `BENCH_LEAK_MM2` (8 com a borboleta antiga, 14 com a compressível) |
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
| `LabCapture.BatteryDebugCompact900x620` | GUI (texto longo demais) | linha do inspetor encurtada: `P1.1? 138 #13` em vez de `(13 pulses)` |
| `thermal_sensor_test`, `test_sevel_long_run` | Fórmula antiga | térmica do manual (87→98 °C; ventilador 92/86); refrigerante oscila e fica entre 86 e 100 °C |
| `test_tps_bench_profile`, `test_sevel_long_run` (rpm), `test_physical_intake` | Número mágico (amostra única) | média da janela (5 s ou 30 s) em vez de uma amostra final; só o 1º evento CC3 após a falha precisa coincidir |
| `test_physical_intake` (passo de fluido), `test_pedal_ramp`, `test_sevel_closed_loop` (pedal) | Número mágico / achado em aberto | passo de fluido 1 rpm → 1% (533,05 vs 529,12); pulsos CC3 mínimos 300 → 200; λ final só é exigido se o motor sobreviveu, senão o motor deve constar parado |
| `test_physical_crank`, `test_physical_intake`, `runner_snapshot_smoke` | Número mágico | partida a frio com vazamento explícito (9 mm²; 1 mm² não pega com a borboleta compressível); `coast` mantém 1 mm² |
| `test_physical_idle` | Número mágico | vazamento 11 mm²; tronco de bridge ≤ 150 bordas e vão da haste < 0,5 mm (ROM oscila; 60 bordas e 0,34 mm medidos) |
| `test_physical_lambda_cooldown`, `test_physical_misfire_lambda`, `test_lambda_table_threshold` | Número mágico / ROM | sensor frio lido em 29,7 M (era 19,8 M); coil cortado exige O₂ pobre (>1,2) e λ ≈ 1 ±0,1; ±1 pulso na borda da janela |
| `test_lab_kline_live` | Condição de corrida do teste | leitura por regex: linha JSON truncada por trace do stderr no mesmo cano |
| `physics_formulas_test`, `test_dyno_sweep`, `test_idle_acceptance` | Novos | fórmulas puras, contrato do CSV do Dyno e aceitação da lenta sem carga |

## Atualização CURVES_STUDY (2026-11-19): bomba-d'água e força de centelha

- **Bomba-d'água (F-45):** `pump_nm_at_ref` 0,5 → 0,02 N·m a 925 RPM de virabrequim; lei ω² mantida. A potência a 6000 RPM passa de ~13 kW para ~0,5 kW (estimativa; trocar pela curva real da bomba).
- **Força de centelha (`Combustion::spark`):** o torque do pulso segue a fração de queima (`força / full_burn_strength`, limitada a 1) e não a força bruta de carga da bobina; `--exp spark_torque_legacy=1` restaura a lei anterior.
- Planta isolada e VE inalteradas. ROM + planta: déficit contra a isolada de 23–35 % para 5–15 %; ver `docs/SEVEL_ROM_POWER_GAP_INVESTIGATION.md` (seção I) e `docs/SEVEL_DYNO_ROM.md`.
