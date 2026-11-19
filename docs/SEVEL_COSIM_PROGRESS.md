# SEVEL 1.6 / Fiat MA1.7 — acompanhamento da cossimulação

## Estado e próxima tarefa

### Sonda de zircônia: oxigênio residual, AFR e λ

- A [experiência com sonda de zircônia aquecida publicada em *Sensors*
  (2013)](https://epub.uni-bayreuth.de/id/eprint/1934/1/Fischer%2C%20Sch%C3%B6nauer-Kamin%20et%20al.%202013%20-%20NO%20Detection%20by%20Pulsed%20Polarization.pdf)
  descreve a célula de Nernst: eletrodo externo no escape, interno em ar
  de referência; a tensão depende da razão das pressões parciais de O₂
  e da temperatura. O [estudo SAE 920289](https://saemobilus.sae.org/papers/operating-characteristics-zirconia-galvanic-cells-lambda-sensors-automotive-closed-loop-emission-control-systems-920289)
  relata uma queda forte de tensão entre λ=0,995 e λ=1,005. O [estudo
  SAE 760020](https://saemobilus.sae.org/papers/sensitivity-zirconia-oxygen-sensor-temperature-flow-rate-exhaust-gas-760020)
  também investiga a sensibilidade à temperatura e ao fluxo.
- Um [ensaio de 2010 com sonda automotiva aquecida de quatro fios](https://ojs.unifor.br/tec/article/download/5338/4511/0)
  descreve o mesmo princípio de dois eletrodos de platina e referência
  atmosférica. Nesse ensaio, o aquecimento levou cerca de 7 s, com
  constante de tempo de cerca de 2 s, em uma montagem para gases de
  combustão industrial; isso não calibra o aquecedor da peça do Tipo.
  A [NTK descreve os quatro fios](https://ngksparkplugs.com/wp-content/uploads/2020/10/NTKO2SensorQA.pdf)
  como sinal, terra do sinal e dois terminais do aquecedor em sua sonda
  de zircônia convencional. O mesmo guia também apresenta sensor AFR de
  quatro fios: contar fios, isoladamente, não prova que a peça é narrowband.
- A [revisão experimental de sensores YSZ (2009)](https://onlinelibrary.wiley.com/doi/full/10.1155/2009/258489)
  explica que CO e hidrocarbonetos reagem no eletrodo de platina e mudam
  o O₂ local. A [SAE 920289](https://saemobilus.sae.org/papers/operating-characteristics-zirconia-galvanic-cells-lambda-sensors-automotive-closed-loop-emission-control-systems-920289)
  observou resposta forte a H₂/CO. Portanto, a tensão não é uma leitura
  direta da concentração média de O₂ no escape; a regra rico/pobre é uma
  aproximação útil sob combustão normal e aquecimento adequado.
- Uma [tese com medições de motor a gás (1995)](https://wrap.warwick.ac.uk/id/eprint/109067/1/WRAP_Theses_Thomas_1995.pdf)
  relata atraso de transporte de cerca de 35–225 ms conforme rotação e
  escoamento e modela a resposta da sonda por primeira ordem de 100 ms.
  Essas ordens de grandeza apoiam separar transporte e inércia elétrica;
  não são medições do escape SEVEL nem da sonda instalada.
- Para cada combustível, `λ = AFR real / AFR estequiométrico daquele
  combustível`. E0 e E25 podem ter AFR absolutos distintos e ambos
  λ=1; manter AFR absoluto fixo produz λ diferentes. A sonda narrowband
  informa sobretudo em qual lado da estequiometria está o escape. A
  mistura que entrou no cilindro pode divergir da indicação de O₂
  residual em falha de combustão; por isso o modelo separa `charge_lambda`
  do `lambda` visto pela sonda.
- A curva sigmoide em `ExhaustLambda` é aproximação de engenharia em
  função de λ e aquecimento. A inclinação padrão continua em **25**;
  um parâmetro experimental de **600** produz queda de tensão maior que
  seis vezes entre λ=0,995 e 1,005, como no resumo do SAE 920289.
  A regressão isolada verifica essa janela. Porém, ao aplicar 600 como
  padrão, quatro de quinze testes dirigidos de malha fechada falharam:
  `PhysicalFuel.E25ClosedLoopResponse`, `PhysicalLambda.ConditionalClosedLoop`,
  `PhysicalLambda.TableThresholdAtFixedAdc` e
  `PhysicalLambda.TableCrossingToCc3`. Isso mostra sensibilidade da ROM
  e das hipóteses elétricas, não invalida o dado experimental da sonda.
  A inclinação da peça desta ECU ainda não foi medida. A curva **não**
  simula diretamente a pressão parcial de
  O₂, equilíbrio CO/H₂ ou célula de Nernst. Mesmo λ não garante a mesma
  tensão real entre combustíveis e temperaturas. A regressão E0/E25
  confirma apenas a invariância intencional do modelo e a troca de lado
  rico/pobre quando o AFR absoluto fica fixo. A identificação física da
  sonda de 3 ou 4 fios nesta unidade ainda depende de evidência da peça.
  `--lambda-switch-slope 600` expõe o contraste no executor físico;
  `25` é o padrão e o intervalo aceito é 1–1000. Em 10 M ticks,
  no cenário quente de 24 N·m abaixo com `--lambda-adc-gain 5`, ambos
  terminaram em λ físico 0,926. Com inclinação 25 a sonda deu
  0,7928 V (`RAM65h=203`); com 600, saturou em 0,9000 V
  (`RAM65h=230`). A massa injetada foi 0,002642326/0,002641801 kg;
  portanto esse trecho prova a sensibilidade do sinal elétrico, mas
  não uma grande alteração da dosagem em 10 s. O ganho ADC5 é candidato.
  Reproduzir com o comando E25 abaixo, substituindo `--stop-ticks`
  por `10000000`, `--ethanol-percent` por `0` e acrescentando
  `--lambda-switch-slope 600`; repetir com `25` como controle.

### Teor de etanol da ROM gasolina: cenário E22/E25

- A [Lei 8.723/1993, texto original](https://www2.camara.leg.br/legin/fed/lei/1993/lei-8723-28-outubro-1993-363267-publicacaooriginal-1-pl.html)
  fixou **22% em volume** de etanol anidro na gasolina brasileira.
  É uma pista de época para o manual Fiat VIII/93, não identificação da
  procedência ou do combustível esperado pela EPROM G. Os nomes das ROMs
  G/A distinguem arquivos de gasolina/álcool, mas não medem o teor da G.
  O E25 sugerido pelo proprietário é uma aproximação comparativa útil;
  nenhuma tabela da ROM foi convertida em porcentagem comprovada.
- O modelo aceita `--ethanol-percent N` (0–100, fração volumétrica).
  E0 permanece o caso explícito de regressão; usar `22` ou `25` para
  explorar combustível brasileiro sem mudar bytes da ROM. Densidades
  provisórias de gasolina/etanol: 740/789 kg/m³; AFR estequiométrico
  14,7/9,0; PCI 44/26,8 MJ/kg. O [manual de misturas do DOE](https://afdc.energy.gov/files/u/publication/ethanol_handbook.pdf)
  dá os valores de AFR e energia de referência; gasolina real varia.
  A mistura usa fração **de massa**, derivada da porcentagem em volume,
  ao calcular AFR e PCI. Resultam E22 ≈ 13,38:1 e E25 ≈ 13,21:1,
  com PCI E25 ≈ 39,49 MJ/kg. A densidade altera a massa do bico; o
  AFR altera a combustão e a sonda; o PCI altera torque e calor.
- Comparar largura CC3, massa injetada, lambda e estado de correção em
  janelas inicial/tardia. A ECU pode corrigir mistura depois de aquecer
  a sonda, então coincidência de lambda tardia isolada não identifica
  o combustível para o qual o mapa foi gravado. Pressão de 1 bar e
  deadtime do bico também afetam qualquer inferência da tabela.
- Ensaio com a ROM G original, 60 M ticks, 90 °C iniciais, 24 N·m e as
  ligações candidatas de ADC7/lenta/CC3/ADC5 do cenário sustentado:

  | Mistura | λ física nos 20 s finais, mínimo/mediana/máximo | Massa injetada | CC3 | RPM final |
  | --- | --- | ---: | ---: | ---: |
  | E22 | 0,978 / 1,0025 / 1,026 | 0,018985 kg | 1834 | 905,7 |
  | E25 | 0,939 / 0,9995 / 1,023 | 0,019314 kg | 1837 | 902,5 |

  Nos 20 s iniciais, E0 terminou em λ=0,954 com 0,006060 kg injetados;
  E22 em 0,921/0,006439 kg e E25 em 0,948/0,006505 kg. As três
  trajetórias diferem, mas E22 e E25 convergem perto de λ=1 no ensaio
  longo. Portanto, este contraste **não distingue** qual mistura a
  tabela original previa; confirma somente a sensibilidade do modelo
  e a compensação condicional da ROM. As aproximações de bico, ganho
  ADC5 e ligações elétricas limitam qualquer ajuste quantitativo.
  Reproduzir uma mistura por execução (substituir `25` por `22` para E22):

  ```sh
  ./build/emu8051-tty FiatTipo_MA17_dump_27c256.bin --physical-crank \
    --starter-ticks 495000 --stop-ticks 60000000 --adc7-mv 1232 \
    --idle-bridge-p15-p16 --idle-contact-p46 --coolant-c 90 \
    --idle-min-stop-mrad 5 --throttle-leak-mm2 9 \
    --load-step-tick 800000 --load-nm 24 --lambda-adc-gain 5 \
    --ethanol-percent 25
  ```

  ROM SHA-256: `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
  Build, quatro testes de mistura/injetor e 13 de combustão/escape
  passaram; `PhysicalIntake.ConditionalCc3Fuel` passou. O teste
  `PhysicalFuel.E25ClosedLoopResponse` compara E0/E25 com a ROM: em
  5 s, λ física E25 é maior, e até 20 s o tempo médio CC3 por pulso
  aumenta mais de 2%. Passou em 17,74 s. A comparação determinística
  de `PhysicalLambda.StallCooldown` agora usa somente eventos físicos:
  o caminho PTY muda de forma legítima sob CTest paralelo. A suíte
  completa após a opção de combustível passou **225/225** em 174,11 s;
  o novo teste E25, registrado depois, passou isoladamente (226 no total).

### T8: combustível e diagnóstico no toque de pedal

- Para distinguir a aceleração do cabo de um degrau impossível,
  `--pedal-rise-ticks N` interpola linearmente o puxão entre o comando
  e o alvo em tempo virtual. A atualização ocorre a cada passo de fluido,
  com o alvo aplicado exatamente no fim; `N=0` preserva o degrau antigo.
  Este é um perfil de motorista, não uma dinâmica medida do cabo.
- Com os mesmos 20 M ticks, E0, 8 mm de comando em 10 M e soltura em
  12 M, o degrau repetiu `F84E=0Ah` durante o pedal e `F85E=0Ah` depois.
  Uma subida em **200 mil ticks** (~0,202 s) chegou a 0,280 rad em
  10,2 M, abriu o contato, mas manteve `F84E=F85E=0` em todas as
  amostras; 500 mil ticks (~0,505 s) também terminou sem esses bits.
  Em 20 M, λ físico foi 0,949/0,940/0,972 para degrau/200 k/500 k.
  O teste `PhysicalTps.PedalRiseAvoidsTransientFault` confronta degrau
  e 200 k com a ROM original. Isso **isola a forma temporal do comando**
  como causa no modelo, sem provar a velocidade real do pedal ou os
  bindings P4.6/P1.5–6. Reproduzir acrescentando
  `--pedal-step-tick 10000000 --pedal-release-tick 12000000 --pedal-mm 8
  --pedal-rise-ticks 200000` ao comando de mistura acima, com
  `--ethanol-percent 0`; omitir a última opção
  para o controle instantâneo.
- Com `--fluid-step-ticks 495` no braço de 200 k, os mesmos 11 registros
  de diagnóstico de 9,9 a 19,8 M permaneceram zerados; a λ final mudou
  de 0,940 (passo 990) para 0,962. O resultado qualitativo do DTC é
  estável nesse refinamento, enquanto a λ exige tolerância numérica.
  Após o novo perfil, os testes direcionados de TPS, contato, bancos de
  falha e sustentação passaram **6/6**; a suíte completa com o novo teste
  passou **229/229** em 245,25 s antes de ampliar o ensaio forte abaixo.
- Com subida de 200 k, 8 mm e a ROM G, a λ física em 9,9/10,89/11,88 M
  foi 0,926/0,822/1,053 (E0) e 0,965/0,910/1,068 (E25). O byte
  `RAM65h` acompanhou o sinal da sonda: 203/228/79 e 170/215/58.
  A rota `1810h→186Dh` não teve bloqueio sustentado em 10–14 M:
  zero passagens E0 e uma isolada E25; ambos terminaram sem bits 1/3
  de diagnóstico e com 631/629 pulsos CC3. Isso descreve apenas o
  toque moderado no modelo, não prova que a ECU real permaneça em malha
  fechada numa acelerada rápida.
- Com os mesmos 200 k de subida e pedal de **40 mm** em E0, a ROM teve
  106 passagens por `1810h` sem seguir imediatamente a `186Dh`, da
  primeira em 12.685.372 à última em 19.177.299 ticks, já após soltar
  o cabo. `F84E/F85E` ficaram zero; a λ física chegou a 0,518 em
  12,87 M e 0,444 em 15,84 M, enquanto a soma final foi 674 pulsos
  CC3. O teste do pedal agora verifica também essa pausa forte.
  Chamar esse intervalo de modo *open loop* da ECU é interpretação:
  ainda há corte de combustível e estados internos compartilhados.
- Repetindo o braço de 40 mm/200 k com E25, houve 101 passagens
  bloqueadas entre 12.685.551 e 15.173.468 ticks, 672 pulsos CC3 e
  `F84E=F85E=0` no fim. A λ física em 12,87/14,85 M foi 0,604/0,433,
  contra 0,518/0,348 em E0. O último bloqueio observado ocorreu antes
  em E25 neste ensaio, mas RPM, filme e combustível mudam juntos;
  o contraste não identifica um temporizador próprio de E25.
- A suíte completa passou **229/229** antes da ampliação do teste forte;
  `PhysicalTps.PedalRiseAvoidsTransientFault` ampliado passou **1/1**
  em 35,91 s. A ROM permaneceu original.
- Com a ROM G, 20 M ticks, E0/E25 e pedal de 8 mm entre 10–12 M,
  ambos terminaram em `F84E=0, F85E=0Ah`; E25 com pedal de 12 mm
  terminou em `F84E=F85E=0`. A mistura mudou: em 20 s, λ física
  foi 0,949 (E0/8 mm), 1,018 (E25/8 mm) e 0,905 (E25/12 mm).
  Os pulsos CC3 foram 594/588/648, respectivamente. Portanto, o
  histórico `0Ah` neste contraste acompanha a condição do pedal,
  contato e lógica da ROM, sem depender de escolher E0 ou E25.
- No braço E25/8 mm, `2B42h` ligou `RAM27.1` no tick 10.997.308,
  `2B49h` ligou `.3` três ticks depois, e `41E5h` publicou
  `F84E=0Ah` em 11.113.490. Após soltar o pedal, `41E5h` zerou
  `F84E` em 12.034.348; `F85E=0Ah` continuou registrado. Os
  mesmos PCs e a ordem aparecem no ensaio E0 anterior. Os nomes
  `0402h/1A01h` vêm da tabela da ROM; sua causa física permanece
  condicional à ligação P4.6, à ponte P1.5/P1.6 e à velocidade da haste.
  Reproduzir com o comando E25 acima, acrescentando
  `--pedal-step-tick 10000000 --pedal-release-tick 12000000 --pedal-mm 8`.

### Resposta gradual da ECU e abertura do injetor

- A ROM original já acumula correções condicionadas à leitura da sonda:
  `RAM65h` influencia as flags e a correção `5Ch:5Dh`, que chega à
  duração `14h:15h` e ao pulso CC3. Portanto, a resposta ao mesmo
  estímulo pode mudar após segundos de funcionamento. Comparações de
  tensão, TPS ou λ devem registrar tanto o transiente quanto uma janela
  tardia, com o estado da correção e os DTCs; não pressupor pulso fixo.
- O estágio do bico agora exige corrente de bobina estimada de 0,75 A
  além do tempo morto hidráulico para entregar combustível. Isso separa
  um pulso elétrico curto sem abertura física de um pulso com vazão;
  0,75 A é hipótese de engenharia, sem medição desta peça. No teste de
  6 V, 1,8 ms não injeta e o mesmo pulso prolongado até 2,3 ms injeta;
  em 12,5 V, o pulso de 1,8 ms injeta. A correção lenta pertence à ROM,
  não a esse limiar elétrico fixo.

| Tarefa | Estado | Resultado observável / aceitação | Dependência |
| --- | --- | --- | --- |
| T0 Baseline e interfaces | validada no modelo | 229/229 após perfil gradual do pedal | nenhuma |
| T1 Partida e 60-2 | validada no modelo | torque acelera desde zero; captura real faz a ROM publicar RPM em 47h | T0 |
| T2 Cabo, TPS duplo, contato | validada no modelo | dois ADCs e GPIO respondem à mesma geometria; ROM os processa | T1 |
| T3 Alimentação e térmicos | validada no modelo | tensão/NTCs chegam aos canais Fiat e são lidos pela ROM | T0 |
| T4 Batente DC | validada sob binding candidato | P1.5/6→haste→TPS e P4.6 fecham o retorno | T2 |
| T5 Admissão e injetor | validada sob binding candidato | massa de ar e combustível evoluem com pulsos efetivos | T1, T2 |
| T6 Ignição e torque | validada sob binding candidato | quatro cargas por cilindro e bordas P5 sustentam rotação sem arranque | T5 |
| T7 Escape e lambda | validada sob binding candidato | transporte, aquecimento e falha de centelha chegam ao ADC5/65h | T6 |
| T8 Cenários e diagnósticos | validada no perfil condicional | partida e carga repetíveis; subida de 0,2 s evita DTC do degrau; ECT/TPS1 presente/histórico na K-Line | T1–T7 |

## Auditoria dos critérios de aceitação do modelo

| Critério | Evidência atual | Limite para encerrar |
| --- | --- | --- |
| 1. Núcleo C++ separado | `src/engine`, `src/ecu_hw`, executor `src/ma17/EmulatorLoop.cpp`; build aprovado | Organização suficiente para o modelo |
| 2. Relógio headless | `--physical-crank`, ticks inteiros a 990 kHz; repetição bit a bit no teste de 60 s | PTY em tempo real é opção separada |
| 3. Partida e 60-2 | `PhysicalCrank.FiatRomRpm`: torque desde zero, lacunas 58/59, escrita de `RAM47h` em `0EA5h` | P1.0 e fase física continuam hipóteses |
| 4. Sustentação | `PhysicalEngine.SustainedSixtySeconds`: quatro cilindros, sem arranque após 495 mil ticks, balanços e convergência | ADC7 e CC3→bico são bindings condicionais |
| 5. Cabo e lenta | `PhysicalTps.*`, `PhysicalIdle.*`: TPS duplo, contato e ponte candidata atuam na ROM; subida de 0,2 s evita DTC do degrau | Velocidade/pinagem real não medidas |
| 6. Sensores e combustível | `PhysicalThermal.*`, `PhysicalLambda.*`, `PhysicalIntake.*`: pressão interna, filme e ADC5 | Curvas, ganho ADC5 e origem ADC7 não calibrados na placa |
| 7. Pedal e carga | `PhysicalLambda.ConditionalClosedLoop` e cenário de carga documentam estado, RAM, pinos e DTCs | Respostas dependem das ligações candidatas |
| 8. Diagnósticos | O nominal de 60 s mantém oito bytes monitorados em zero; falhas negativas e K-Line têm testes; subida gradual não publica bits 1/3 no pedal | Causa física de `0402h/1A01h` depende das ligações e velocidade da haste |
| 9. Regressão/reprodução | 229/229 no build atual; inclinação padrão 25, contraste 600 opcional; ROM original manteve SHA-256 | Revalidar se mudar os bindings |

O objetivo do **modelo condicional** foi demonstrado nos nove critérios acima.
Em 16/11/2026, `ctest --test-dir build --output-on-failure -j 4` passou
229/229; a execução física sem `DISPLAY` produziu as mesmas 909 linhas
físicas com/sem `MA17_TRACE_PC=1` (SHA-256
`945ca55af20870405a9dc883ca87f7e5f3764dd18608bd0a5e0a27dcc9dd0555`).
Isso não valida a ligação elétrica da placa: P4.6, P1.5/P1.6, CC3, P5,
ganho ADC5 e origem de ADC7 continuam hipóteses declaradas. A ROM mostra
ADC7→`RAM67h` e seu uso na guarda `3B22h`; não revela a grandeza externa.
O canal lógico é suficiente para o ensaio solicitado, e 0/1,232 V abaixo
do limiar deram a mesma resposta, enquanto 1,260 V cedo bloqueou CC3.
Próxima investigação opcional da placa: medir a origem de ADC7 e confirmar
os drivers candidatos antes de alegar fidelidade elétrica da ECU real.

### Contraste ADC7 dentro da faixa que libera a guarda

- O parser físico aceita agora `--adc7-mv 0` e
  `--adc7-step-mv 0`. A ROM recebe essa tensão pelo periférico ADC;
  o valor zero não é escrito diretamente em RAM. O teste
  `PhysicalAdc7.StartupGateLatch` compara 0 com 1,232 V e também
  verifica um degrau tardio de 1,260 V para 0 V.
- Com a mesma ROM e o cenário quente de 20 milhões de ticks usado nos
  testes de malha, 0 e 1,232 V terminaram ambos em 867,227 RPM,
  620 pulsos CC3, 0,006059682 kg injetados e os mesmos bancos de falha.
  `RAM67h` foi 0 e 63, respectivamente; `F8DDh=AAh` e `2Bh.5=0`
  em ambos. Assim, 1,232 V não é uma calibração necessária à resposta
  observada nessa janela. O cenário continua condicional à ligação de
  ADC7, que pode ser outra grandeza ou um nó interno da ECU.

### Inversão das temperaturas e canais da CPU

O scanner local lê `62h` como ar e `63h` como água. Sua conversão assume
`1/(T+273,15)=A+B ln(R)+C ln(R)^3`, com `A=0,00130233960469996`,
`B=0,00025894836043228303` e `C=0,0000001691900955030085`.
Para obter a entrada a partir de uma temperatura, o circuito resolve essa
equação monotonamente para `R`, então calcula `Vadc=5R/(R+Rpu)`:
`Rpu=2661 Ω` no ar e `3004 Ω` na água. A aproximação do byte ideal do
scanner é `x=255R/(R+Rpu)`, antes da quantização ADC de 10 bits e do
tratamento da ROM. Esses coeficientes e pull-ups são ajustes do scanner,
não medições independentes da placa.

Exemplo a 20 °C: `R≈2516 Ω`, `Vadc2≈2,430 V`, `Vadc3≈2,279 V` e
`x≈124/116` para ar/água. No cenário Fiat frio de 2 milhões de ticks,
a ROM publicou `RAM62h=124` e `RAM63h=117`. A diferença de uma contagem
na água é compatível com quantização e processamento da amostra; não
igualar genericamente `RAM63h` ao byte ADC, pois ADC3 passa por `A8h` e
pela rotina `4756h`. A agenda original em `06E3h..06F1h`, o teste dos
opcodes em `0721h..0747h` e a execução térmica sustentam **ADC2→ar** e
**ADC3→água** como portas lógicas da CPU. Isso é suficiente para conectar
esses sensores ao simulador sem saber os terminais físicos do conector.

### Dados do motor nas páginas enviadas pelo proprietário

O manual Fiat Tipo `B.500.837`, VIII/93, páginas 5–6, 14, 17 e 18,
identifica a versão Monomotronic 1581. Registra quatro cilindros,
86,4 × 67,4 mm, 1581 cm³, compressão 9,2:1, ordem 1–3–4–2,
torque máximo de 13,3 daN·m a 3000 rpm e potência máxima ABNT de
60,4 kW a 6000 rpm. A curva CEE da página 6 usa outro método de medição;
não misturar sua escala com o pico ABNT. O modelo usa 1580 cm³ como
aproximação e não possui calibração de dinamômetro; os picos são alvos
de comparação, não uma curva de torque a impor ao virabrequim.

O mesmo manual informa pressão de regulagem do combustível de 1 bar,
avanço de ignição em lenta de 6° ± 2° a 850 ± 50 rpm e sensor de rotação
Bosch `0.261.210.102` com entreferro 0,5–1,5 mm. Não informa nesta página
o ângulo da roda 60-2 em relação ao PMS; a hipótese de 120° segue aberta.
Os diagramas de válvulas dão admissão de 7° antes do PMS a 35° após o PMI
e escape de 37° antes do PMI a 5° após o PMS. Servem para revisar a fase
física e a eficiência volumétrica quando esses efeitos forem modelados;
não são evidência do canal elétrico da ECU. O manual também descreve
injeção monoponto e ignição de distribuição estática, coerentes com os
dois pares de centelha desperdiçada do modelo.

Com `--tdc-reference-deg 120`, ROM Fiat original, 6 M ticks, motor quente,
`--throttle-leak-mm2 3` e carga aplicada em 800 mil ticks, a mediana das
bordas altas de P5 entre 3–6 M ticks e 800–900 rpm correspondeu a avanço
de 9,65° (`--load-nm 5`, RPM final 883,677; 51 bordas) ou 12,48°
(`--load-nm 6`, RPM final 824,955; 86 bordas). O cálculo foi
`(120°−ângulo_da_borda) mod 180°`; trata a borda alta como centelha
**candidata**. Ambos ficam acima dos 6° ± 2° especificados. O manual
mede o motor real em marcha lenta, enquanto o ensaio usa carga artificial,
fase de roda hipotética e estágio de potência sem atraso medido. Assim,
este contraste detecta uma lacuna de calibração; não fixa a referência
angular nem justifica ajustar a ROM. Reprodução: usar a configuração
física do ensaio de ignição abaixo, trocar `--stop-ticks` por `6000000`,
`--throttle-leak-mm2` por `3` e acrescentar `--load-step-tick 800000
--load-nm 5` ou `6`.

No cenário nominal quente de 20 M ticks (carga 24 N·m, fuga 9 mm²,
ADC7=1,232 V, ganho ADC5=5), a ROM terminou a 867,227 rpm com 620
pulsos CC3. Entre 15–20 M ticks, com bordas altas P5 em 800–900 rpm,
a referência de 120° deu avanço candidato mediano de 9,67° (23 bordas)
e λ amostrado de 0,932–0,988. Repetindo a **mesma ROM e entradas** com
`--tdc-reference-deg 118`, houve 882,746 rpm, 7,67° (18 bordas) e
λ=0,914–1,002; a 116°, 872,757 rpm, 6,36° (27 bordas) e
λ=0,967–1,012. `F84E/F85E` terminaram em zero nas três fases. O valor
116° aproxima o avanço especificado em lenta
sem impedir a malha modelada, mas permanece uma **fase candidata**:
o ajuste depende da interpretação de P5 como centelha, da carga e do
modelo de combustão. O padrão de 120° continua documentado para
comparação; não inferir uma montagem real de 116° destes resultados.
Reproduzir a varredura com `python3 tools/compare_idle_advance.py
./build/emu8051-tty FiatTipo_MA17_dump_27c256.bin`; o utilitário emite
JSON por fase com hash da ROM, RPM, avanço candidato, faixa de λ e
diagnósticos, sem alterar a ROM nem gravar arquivos.

### Pinout preliminar recebido, separado das portas lógicas

O pacote [pinout preliminar](../PhotosECU/pinout_preliminar.json) marca
**zero redes confirmadas por continuidade**. A foto conta 68 terminais no
Siemens B 58 371; o [datasheet oficial do SAB80C515A](https://www.infineon.com/assets/row/public/documents/10/57/infineon-d80515a-ds-v08-95-en.pdf)
mostra uma variante P-LCC-68 com ADC de oito canais, CC3, P5 e XRAM,
compatível em recursos relevantes, mas não identifica o B 58 371 nem
comprova a mesma pinagem no encapsulamento fotografado. No JSON, CPU 13
como AIN7, 18 como AIN2, 17 como AIN3, 33 como CC3 e 67/66 como P5.0/1
são apenas **candidatos físicos** dessa referência. A ROM confirma os
canais **lógicos** ADC7→`67h`, ADC2→`62h` e ADC3→`A8h`→`63h`; estes
independem da correspondência física dos pads. O possível B57574 como
latch da EPROM e as funções dos 35 pinos do conector também são pistas,
não novas ligações elétricas validadas para o emulador.
O manual do C515A lista também `IADC=0043h`, `IEX3=0053h` e
`IEX6=006Bh`, vetores que a ROM usa; isso reforça a compatibilidade
funcional do subconjunto emulado. A contagem de 68 terminais e esses
vetores ainda não identificam o silício Bosch/Siemens específico.

Na notação dos diagnósticos, `F84E/F85E=0Ah` significa a máscara
`00001010b`: bits 1/3, que a tabela da ROM associa às triplas
`0402h/1A01h` transmitidas pela K-Line. Não é o código `0A02h` do
sensor de temperatura da água listado no scanner. O scanner descreve
`1A01h` como falha do atuador de lenta, mas chama a peça de motor de
passo; essa descrição física conflita com o atuador DC informado pelo
proprietário e não define, por si só, a causa dos bits observados.

## Auditoria das entradas analógicas ainda sem ligação física

- O [manual Tecnomotor do Tipo 1.6 ie](https://pdfcoffee.com/tipo-16-ie-tecnomotor-pdf-free.html)
  enumera TPS duplo, temperaturas do ar e da água e sonda lambda, mas
  não lista sensor externo de pressão do coletor ou outra entrada analógica
  que explique diretamente ADC4 ou ADC7. Ausência na lista é apenas pista:
  pode haver condicionamento ou referência dentro da ECU, ou ligação
  omitida no manual. A pressão do coletor continua estado físico interno
  do modelo, sem atribuir a ela um pino da placa.
- A tabela da ROM em `06E3h..06F1h` agenda ADC4→`RAM64h` e
  ADC7→`RAM67h`. O uso de `RAM67h` na guarda de CC3 em `3B22h` é
  confirmado. A análise anterior da ROM Fiat também mostra `RAM64h`
  como divisor de `RAM61h` em `4044h`, afetando `RAM7Dh` e a duração
  modelada de P5; a função elétrica de ADC4 permanece desconhecida
  ([análise](MA17_FIRMWARE_VARIANTS_ANALYSIS.md)).
- Na desmontagem Fiat atual, a leitura **direta** de `RAM67h` pelo
  código aparece em `3B22h`: `CJNE R0,#41h` seguido de `CPL C` decide
  `2Bh.5` quando o estado `F8DDh` permite a comparação. Não foi
  identificado um lookup contínuo indexado por esse byte. A busca
  textual por operandos diretos não exclui acessos indiretos; por isso
  esta é uma pista de uso binário/condicional, não identificação do
  circuito que excita AIN7.
- Próxima verificação na placa: seguir as trilhas do microcontrolador até
  componentes internos ou terminais do conector e identificar a função
  elétrica de cada terminal medido. A numeração física abaixo vem da
  serigrafia; ela não identifica, por si só, ADC4 ou ADC7.
- As fotos recebidas em `PhotosECU/` mostram a placa `1 268 335 303-3`,
  conector de 35 vias numerado no lado das soldas e processador marcado
  `SIEMENS B 58 371 BB`, em QFP com 17 terminais por lado (68 ao todo).
  Em `IMG_20261116_120011999_HDR.jpg`, com o conector abaixo dos chips,
  a serigrafia marca 43 no canto superior esquerdo, 27/26 no superior
  direito, 10 no inferior direito e 61 no inferior esquerdo do Siemens.
  Assim, a sequência física é: lado superior 43→27 (esquerda→direita),
  direito 26→10 (cima→baixo), inferior 9→1→68→61 (direita→esquerda)
  e esquerdo 60→44 (baixo→cima). Confirmar cada ponta de prova no pad,
  pois essa orientação vale apenas para a vista e a placa fotografadas.
  O `ECUTIPOREPAIR.pdf` enviado também o descreve como processador de
  68 pinos. O material local `SAB80C517.PDF`/`Siemens.txt` descreve
  a família de periféricos, **não** traz pinagem verificada do B 58 371.
  Logo, os números 13/80 do C517A abaixo não servem para medir ADC7
  nesta placa. Ainda faltam identificação elétrica dos terminais do
  B 58 371 e continuidade real das trilhas até ADC4/ADC7.
- O [manual de reparo MA1.7 de Rafael Ferreira Pena](https://pt.scribd.com/document/690586461/Enciclopedia)
  identifica o Bosch `30276` de 52 terminais como driver secundário
  do injetor e das duas ignições; a marca `30276` aparece ao lado do
  Siemens na foto `IMG_20261116_120011999_HDR.jpg`. Para orientar
  continuidade, o manual atribui ao **30276**, não ao processador:
  terminal 13 à entrada de rotação, 10/12 a sinais digitais de rotação,
  2 à saída para o driver do injetor, 41/42 às saídas para os drivers
  das bobinas 2/3 e 1/4, e 40/44 às respectivas entradas de comando.
  A redação de algumas ligações internas no manual é ambígua; a foto
  confirma a identificação do componente, mas não essas funções.
  Medir com a placa desenergizada conector 21→30276, 35→driver do
  injetor e 1/19→drivers de ignição, depois 30276→Siemens. Registrar
  resistência e posição do pad; resistores e semicondutores podem
  impedir continuidade direta. Esse caminho pode testar P1.0, CC3 e
  P5 sem pressupor que a numeração do C517A vale para o B 58 371.
- A ROM original foi executada com `--adc4-mv 0/1760/4000` em três
  cenários de 990 mil ticks. `RAM64h=0/90/205`; com `RAM61h=166`,
  `RAM7Dh=255/255/207`, conforme a saturação e a razão calculadas pela
  ROM. A rotação final foi 1239,809/1239,809/1350,167 RPM no modelo.
  `PhysicalAdc4.ConditionalRomRatio` passou. O padrão de 1,760 V
  reproduz o antigo ADC=90, mas é somente estimativa elétrica do ensaio;
  nenhuma função de sensor foi atribuída ao canal 4.
- Continuidade sugerida com placa desenergizada: conector 8 (interruptor),
  11/12 (TPS), 13 (ar), 14 (água) e 10 (sonda) até a rede de
  resistores/capacitores e os terminais do B 58 371. Registrar ohms e
  posição física do terminal; ausência de bip não exclui resistor em
  série. A ordem ajuda a reconhecer o grupo de entradas antes de
  procurar ADC4/ADC7. Ainda não há correspondência de pinos comprovada.
- O PDF de reparo contém uma descrição abreviada de “1 coil” e chama
  o atuador de lenta de motor de passo. Conforme esclarecimento do
  proprietário, o corpo de três terminais contém **duas bobinas** em
  *wasted spark*; o conjunto de lenta é motor DC com interruptor no
  batente. Esses rótulos do PDF não foram usados para mudar a física.
  `ctest --test-dir build --output-on-failure -j 6` aprovou **222/222**
  em 223,05 s depois da parametrização de ADC4.

## Incremento T3/T5: bateria comum ao ADC e ao injetor

- O [manual Tecnomotor do Tipo 1.6 ie, edição 11/97](https://pdfcoffee.com/tipo-16-ie-tecnomotor-pdf-free.html)
  lista o injetor em 1,6 Ω ±15%, pré-resistor em 2,8–3,4 Ω e
  alimentação vinda do relé da bomba; o [ensaio de Jorge Alberto
  Garbero](https://sa8870b2467ffa3e5.jimcontent.com/download/version/1708537610/module/10743132970/name/SyM267.pdf)
  desenha a resistência em série e mede o pulso no terminal 35.
  O [catálogo Gauss](https://www.gauss.com.br/uploads/2024/09/26/NzZdp4yJHYiasNAqB772Exc3uCnaVjVEXgZqjrWP.pdf)
  associa o Tipo 1.6 SPI ao Bosch `0 280 150 698`, ainda não lido na
  peça desta unidade. A [tabela de injetores Bosch](https://floridainjection.com/documents/Bosch_Injector_data-short-form-2.pdf)
  lista 940 mL/min a 300 kPa para esse código; a [versão com colunas
  adicionais](https://www.scribd.com/document/490830919/Bosch-dados-bicos-injetores)
  também informa 380 g/min na pressão operacional de 100 kPa e
  21,77 mg por pulso de 2,5 ms a 300 kPa, com fluido de ensaio
  `Ch20v3` e spray indicado como 30°–80°. O [manual Bosch de
  injeção](https://www.acomee.com.mx/catalogos/catalogosb/BOSCH%20SISTEMAS%20DE%20INYECCION%20ELECTRONICA.pdf)
  dá 1,75 Ω ±10%. A tabela de vazão, porém, indica 1,3 Ω para o mesmo
  código; essa divergência impede tratar o conjunto como datasheet
  individual validado. São dados de catálogo, não medição do bico
  instalado. A razão 658,2 g/min ÷ 940 mL/min implica densidade de
  ensaio de ~0,700 g/mL. Com gasolina modelada em 0,740 g/mL, a
  vazão provisória de 900 mL/min a 3 bar equivale a ~384,5 g/min a
  1 bar pela lei √Δp, próxima dos 380 g/min da tabela. Aplicar 940
  mL/min diretamente com densidade de gasolina elevaria a massa para
  ~401,6 g/min a 1 bar e misturaria as bases de fluido. A resistência
  provisória do modelo passa a 1,75 Ω. O ponto dinâmico é um
  confronto independente: fluxo estático de 658,2 g/min e pulso de
  2,5 ms implicariam tempo efetivo de cerca de 0,52 ms para entregar
  21,77 mg, se abertura/fechamento fossem instantâneos. Sem tensão,
  driver e curva a 1 bar do ensaio, isso não determina o tempo morto
  do carro nem justifica substituir os 0,8 ms provisórios.
  `Ma17InjectorStage` agora calcula a corrente da bobina em série com
  1,75+3,1 Ω durante o comando CC3 candidato. `L=10 mH` é estimativa;
  o atraso empírico de 0,8 ms a 12,5 V continua sendo o limite nominal.
  Um limiar estimado de 0,75 A agora impede fluxo em pulsos curtos a
  6 V, sem alterar o início nominal de 10–14,5 V nos testes. O
  desligamento zera a corrente porque o caminho de recirculação do
  driver não foi identificado. Os testes dirigidos do estágio, admissão
  e bateria passaram **5/5**; o cenário sustentado de 60 s e a malha
  lambda passaram **2/2** após essa mudança.
- Conferência física do cenário quente sustentado com a ROM original:
  entre 20 e 60 s virtuais, lambda física variou de 0,976 a 1,037
  (mediana 1,006); a pressão final foi 42,7 kPa. As massas acumuladas
  de ar aos cilindros e combustível entregue foram 0,254022061 e
  0,017456779 kg, razão 14,55:1. `PhysicalEngine.SustainedSixtySeconds`
  agora limita pressão, mediana lambda e razão acumulada de massas.
  Essa verificação é do cenário com ADC7, CC3, ponte, contato e ganho
  ADC5 candidatos; não calibra o motor real. O teste dirigido passou
  **1/1** em 74,57 s; a suíte completa **220/220** foi executada antes
  desta asserção adicional.
- `--battery-mv` (6.000–16.000 mV, padrão 12.500) fornece uma condição
  elétrica única ao divisor de ADC1, tempo morto do injetor, ponte H
  candidata e aquecedor da sonda quando o relé candidato fecha. O
  arranque ainda usa torque prescrito, sem modelo de queda de tensão.
  Em ensaios com a ROM Fiat original, 10,0/14,5 V produziram
  `RAM61h=133/193`; sem combustão, a sonda atingiu 60,9/106,1 °C no
  tick 990.000. Em 4 M ticks com arranque, houve 150 comandos CC3 em
  ambos, mas 0,002146825/0,002445292 kg de combustível efetivamente
  injetado. São efeitos do modelo com divisor e tempo morto estimados,
  não calibração elétrica da placa. `PhysicalSupply.BatteryFeedsAdcInjectorAndHeater`
  e dois testes existentes de injetor/aquecedor passaram **3/3**.
  `ctest --test-dir build --output-on-failure -j 6` passou **220/220**
  em 216,75 s; ROM Fiat preservada.
- O estágio do injetor agora lê `Ma17SensorCircuit::supply_voltage()` no
  executor físico; o divisor do ADC de bateria usa o mesmo parâmetro
  `battery_v`. O valor padrão permanece 12,5 V e o tempo morto do bico
  continua uma aproximação dependente dessa tensão. No caminho de
  harness sem circuito físico, permanece o contorno de 12,5 V.
- Build aprovado; `Ma17SensorCircuit.*`, `Ma17InjectorStage.*` e
  `PhysicalIntake.ConditionalCc3Fuel` passaram **4/4** em 31,18 s.
  `ctest --test-dir build --output-on-failure -j 4` passou **219/219**
  em 258,18 s após a mudança; os dois testes de tabela lambda também
  passaram **2/2** em 67,84 s.
  As 3.942 linhas físicas/JSON do pedal de 12 mm e 15 M ticks foram
  idênticas às anteriores (SHA-256
  `fe6c837362e261d5c1ff593aa1339ba224b93e128dbb00086cf0af62f4fbb997`).
  Isso verifica ausência de mudança no cenário padrão; resposta a
  variação real de bateria e pré-resistor continua sem calibração.

## Incremento T6: seleção real de matriz durante o pedal

- Com a ROM Fiat original, carga candidata de 24 N·m, 15 M ticks e
  demais parâmetros do ensaio físico de ignição, `MA17_TRACE_MOVC=1`
  contou **200** leituras com `DPTR=7B46h` sem pedal e **1.114** com
  pedal de 12 mm entre 10 e 12 M ticks. Os PCs leitores foram
  `532Fh`, `5333h`, `534Bh` e `5350h`. Não houve seleção com
  `DPTR=7BBEh`, `7C36h`, `7CAEh`, `7D26h` ou `7D9Eh` nos dois braços.
- O catálogo da ROM já liga esse caminho de interpolação a valores
  que podem alcançar `RAM69h`; `PhysicalIgnition.P5PhaseVsRam69`
  verifica separadamente a relação de `RAM69h` com a fase das bordas
  P5. A nova asserção de seleção passou **1/1** em 56,82 s. A mudança
  de contagem acompanha RPM/carga/TPS, portanto não isola qual entrada
  escolhe a célula nem confirma que P5 acione as bobinas reais. As
  3.942 linhas físicas/JSON do braço com pedal foram idênticas com e
  sem `MA17_TRACE_MOVC` (SHA-256
  `fe6c837362e261d5c1ff593aa1339ba224b93e128dbb00086cf0af62f4fbb997`).
- A referência de 120° antes do PMS continua uma hipótese de montagem
  corroborada pelo manual e comparada no modelo. Nenhuma leitura
  identificou uma tabela separada de fixação do sensor. Próximo:
  correlacionar dente/lacuna, PMS e corrente das duas bobinas no
  veículo para fixar origem angular e polaridade sem usar o ótimo
  de torque assumido como prova.
- `--tdc-reference-deg` agora aceita 0–719° (antes 0–359°), mantendo
  120° como padrão. A diferença de 360° representa qual cilindro de
  cada par *wasted spark* está no tempo de compressão; não desloca a
  lacuna da roda em relação ao virabrequim. O teste
  `Combustion.FullCyclePhaseSwapsCompressionCylinderWithinCoilPair`
  verificou 1↔4 na mesma centelha, com a mesma massa queimada e torque.
  Na ROM Fiat, ensaios headless de 4 M ticks em 120° e 480° tiveram
  ambos 188 queimas, zero centelhas perdidas, 0,000712469 kg de
  combustível queimado e 1735,065 RPM na amostra de 3,96 M ticks.
  A simetria deste modelo não permite escolher a atribuição física
  de compressão pelo RPM. Build e nove testes dirigidos passaram;
  pinagem das bobinas e fase de 720° permanecem sem medição.
  Reprodução: `env -i PATH=/usr/bin:/bin ./build/emu8051-tty
  FiatTipo_MA17_dump_27c256.bin --physical-crank --starter-ticks 495000
  --stop-ticks 4000000 --adc7-mv 1232 --idle-bridge-p15-p16
  --idle-contact-p46 --coolant-c 90 --idle-min-stop-mrad 5
  --throttle-leak-mm2 9 --lambda-adc-gain 5 --tdc-reference-deg 120`;
  repetir com `--tdc-reference-deg 480`.

## Incremento T7: contador rápido versus alternância da correção

- No cenário quente de 20 M ticks com sonda livre, `F8E9h` e `F8EBh`
  mudaram 126 vezes cada após 7,5 M ticks (intervalo mediano 102.400
  ticks). Houve oito inversões em `1958h`. A distância da escrita
  `F8E9h` mais próxima foi 78–41.216 ticks; somente três ficaram a
  até 116 ticks. Logo, a inversão não ocorre em toda recarga do contador.
- Fixando eletricamente ADC5 em 4,000 V desde 2 M ticks, com o mesmo
  motor e ROM, ambos os contadores ainda mudaram 126 vezes cada após
  7,5 M ticks, com a mesma mediana de 102.400 ticks. Houve 1.222
  visitas a `1958h`, sempre com `PSW.5=0`, sem inversão. O controle
  separa a marcha dos contadores da alternância observada; não exclui
  que eles condicionem classificações ou prazos em outras entradas.
- `PhysicalLambda.TableThresholdAtFixedAdc` agora verifica esse
  contraste no trecho de 12 M ticks; passou **1/1** em 27,85 s.
  O estímulo ADC5 fixo é um ensaio elétrico contrafactual, não valida
  a sonda física.
- No braço livre, cada uma das oito inversões em `1958h` seguiu a
  última mudança da flag de classificação por 103–141 ticks. Nas três
  inversões próximas de `F8E9h`, essa escrita ocorreu 25 ticks após
  a flag mudar; as outras cinco inversões não exigiram essa escrita
  próxima. `PhysicalLambda.TableCrossingToCc3` verifica a ordem
  flag→inversão e ao menos uma inversão distante do contador; passou
  **1/1** em 42,06 s. Isso aponta a flag como antecedente imediato,
  sem provar que ela seja a única condição da decisão.
- Próximo: confrontar o comportamento da classificação com sinais
  ADC5 medidos e refinar o ganho elétrico antes de atribuir uma
  frequência de oscilação à sonda ou ao catalisador.

## Incremento T7/T8: acelerada forte e temporização da ROM

- Com a ROM Fiat original, pedal de 40 mm entre 10 e 12 M ticks,
  carga externa de 24 N·m, ADC7=1,232 V, ganho ADC5=5 e ligações
  candidatas P4.6/P1.5/P1.6, a rotação amostrada alcançou 3.342 rpm.
  A janela principal de passagens por `1810h` sem entrada em `186Dh`
  foi 12.685.355–13.740.134 ticks (105 passagens); o maior intervalo
  entre inícios CC3 foi 12.671.577–13.587.502 (915.925 ticks).
  A correção voltou após a janela e não apareceu `F84E/F85E=0Ah`.
- O pedal de 12 mm, nas mesmas condições, encerrou a janela principal
  perto de 13,157 M ticks. Assim, a resposta da ROM à acelerada forte
  prolonga o bloqueio após soltar o cabo, mas a pausa CC3 e o bloqueio
  da rota lambda têm durações diferentes. A regressão integrada verifica
  ambos sem alterar RAM, tabelas ou ROM.
- Sem os 24 N·m externos, o mesmo toque alcançou ~4.967 rpm amostrados;
  a rota ficou bloqueada até 18 M ticks. Uma revisão da janela CC3
  encontrou o corte que começa **depois** de soltar o pedal:
  12.665.404–19.414.083 ticks, sem início de pulso nesse intervalo.
  O filtro anterior descartava intervalos iniciados antes de 13 M ticks
  e ocultou a pausa. A sonda atingiu o limite pobre, enquanto o
  combustível queimado acumulado ficou praticamente constante entre
  13,86 e 18,81 M ticks; a 19,8 M voltou a indicar mistura rica.
  O motor terminou a 1.815 rpm em 20 M ticks. O intervalo prolongado
  coincide com corte de combustível em desaceleração no modelo, não
  demonstra um temporizador específico de retorno à malha fechada.
- `PhysicalLambda.ConditionalClosedLoop` passou **1/1** em 150,09 s
  após incluir a medição da pausa sem carga e as leituras de escape
  antes/depois da retomada CC3. Build sem mudanças pendentes;
  `ctest --test-dir build --output-on-failure -j 4` passou **219/219**
  em 267,31 s. Próximo: confrontar a duração do corte e o RPM de
  retomada com corrente real do bico e rotação no veículo; ambos
  dependem das hipóteses de pinagem e carga do ensaio.
- A ROM tem temporizações e calibrações reais (`7221h/3Dh` e
  `733Dh..7342h`), descritas abaixo. Estes contrastes não demonstram
  uma tabela que imponha ciclos rico/pobre por tempo fixo nem a função
  catalítica sugerida; a hipótese permanece aberta até correlacionar
  ADC5, CC3 e composição do escape medidos no veículo.
- `ctest --test-dir build --output-on-failure -R
  PhysicalLambda.ConditionalClosedLoop` passou **1/1** em 142,07 s;
  `git diff --check` passou e a ROM manteve SHA-256
  `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
  Próximo teste: medir ou simular uma sequência de degraus ADC5 com
  carga/RPM controlados para distinguir os contadores de limites da
  correção bidirecional sem confundir o corte de desaceleração.

## Incremento T5/T7: combustível residual durante o corte CC3

- No cenário físico de 12 mm, instantâneos em 12,8 e 13,0 M ticks
  conservaram `cc3_pulses=436`, `on_ticks=1.103.768` e massa total
  injetada `0,004909729 kg`: não houve nova alimentação no intervalo.
  Mesmo assim, a massa entregue aos cilindros subiu de `0,004860279`
  para `0,004886040 kg` (**25,761 mg**). A película caiu de 26,172
  para 14,070 mg e o vapor de 23,279 para 9,619 mg. A soma entregue
  + película + vapor permaneceu igual à massa injetada dentro de
  3×10⁻⁹ kg, limitada pelo arredondamento da telemetria.
- `PhysicalLambda.ConditionalClosedLoop` agora verifica esses dois
  instantâneos com a ROM original, além da pausa e retomada CC3;
  passou 1/1 em 128,56 s. Os três testes `IntakeFuel` e
  `PhysicalIntake.ConditionalCc3Fuel` passaram 4/4 em 31,27 s;
  `git diff --check` ficou limpo e a ROM Fiat preservou SHA-256
  `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
  Isso demonstra a reserva de combustível do
  modelo durante o corte candidato, mas não calibra a fração retida,
  evaporação ou a ligação elétrica CC3→bico. Próximo confronto físico:
  corrente no bico, pressão de combustível e sonda durante a soltura.

## Incremento T7/T8: estado de corte CC3 durante o retorno lambda

- No mesmo toque de 12 mm, `MA17_TRACE_LAMBDA_ROUTE=1` agora mostra o
  carry, `RAM29h`, `25h`, `26h`, `2Eh` e `B` em `1810h`. Com sonda livre,
  `RAM26h.7=1` ainda em 13,003 M ticks e zera perto de 13,013 M;
  com ADC5 fixo em 2,960 V, zera perto de 12,809 M. Enquanto vale 1,
  o carry de `1810h` mantém `RAM3Ch=0Fh`; depois a contagem desce.
- A ROM compara RPM em `1F81h..1F9Bh` com `ROM[7235h]=40h`, propaga o
  estado por `2052h` a `RAM26h.7`, usa essa flag na guarda lambda de
  `17F9h` e testa-a em `0591h` antes de agendar CC3. No intervalo
  12,8–13,0 M houve **zero** inícios de pulso CC3 com sonda livre e
  dez com ADC5 fixo; o braço livre voltou a pulsar após 13,0 M.
  `PhysicalLambda.ConditionalClosedLoop` exige essa diferença e passou
  1/1 em 117,93 s.
- O fluxo modelado entre 11,88 e 12,87 M ticks foi ~0,0071 kg/s;
  com a geometria e gás quente assumidos, o trânsito até a sonda é da
  ordem de 0,016 s. Logo, a diferença de ~0,207 s entre os braços
  corresponde principalmente ao estado/temporização da ROM no modelo.
  ADC5 também altera combustível, torque e RPM em malha fechada: o
  contraste não isola uma ação direta da sonda sobre `RAM26h.7`.
  A interpretação de `26h.7` como corte na desaceleração e CC3 como
  comando do bico continua dependente da pinagem física da ECU.
- Com `--fluid-step-ticks 495`, a janela 12,8–13,0 M teve um início
  CC3 com sonda livre e dez com ADC5 fixo; em 13,0–13,2 M os números
  foram dez e nove. O contraste persiste, mas a borda exata do corte
  muda com o passo físico. A saída integral do braço livre até 13,3 M
  coincidiu com/sem `MA17_TRACE_LAMBDA_ROUTE` (SHA-256
  `8ce4484ea95ae489d5ee824601cefd5ceabd1c218f27b9cbb87e741e91abfa9a`).

## Incremento T7/T8: retorno da rota lambda após o pedal

- Varredura com ROM Fiat original, ADC7=1,232 V, ganho ADC5=5,
  contato P4.6 e ponte P1.5/P1.6 candidatos, pedal de 10 a 12 M ticks
  e carga de 24 N·m: 4 mm produziu só uma passagem isolada por `1810h`
  sem `186Dh` durante o toque; 8 mm produziu 66 passagens bloqueadas
  entre 11,016 e 11,682 M; 12/16 mm mantiveram bloqueio após soltar
  o pedal, até 13,157/13,238 M ticks. Os braços 12/16 mm não
  publicaram `F84E/F85E=0Ah`, ao contrário de 4/8 mm neste cenário.
- Para 12 mm, a janela contínua após a soltura foi de 12.726.401 a
  13.156.595 ticks (43 passagens). Fixar ADC5 em 2,960 V desde 2 M
  manteve uma janela de 12.715.907 a 12.951.792 (24 passagens), com
  o restante do cenário igual. A diferença de término é 204.803 ticks
  (~0,207 s). Assim, a duração depende também da entrada da sonda
  neste modelo; o estímulo de pedal sozinho não a determina.
- `PhysicalLambda.ConditionalClosedLoop` agora verifica a janela de
  12 mm, o retorno após a soltura, a diferença com ADC5 fixo e a
  ausência do DTC candidato. Passou 1/1 em 117,02 s. A rota não
  demonstra um modo elétrico real de malha aberta, e ainda não reproduz
  os vários segundos de retorno observados pelo usuário no veículo.
  Próximo: confrontar duração de TPS, contato, ADC5 e pulsos CC3 no
  carro para distinguir transporte da sonda, estratégia da ROM e
  calibração elétrica assumida.

## Incremento T4/T8: bordas reais do interruptor de lenta

- O executor físico agora publica `idle_contact` quando a geometria
  muda o estado do interruptor, com tick, ângulo do cabo e do batente.
  A observação ocorre após os movimentos do pedal e da haste no tick;
  não escreve em pinos, RAM ou atuadores.
- No ensaio quente de 50 mm/s e pedal de 8 mm, o contato abriu no tick
  10.000.000, fechou em 10.638.049, reabriu em 10.728.008 e voltou a
  fechar na soltura do pedal. A recarga da ROM em `2A4Bh`, por volta
  de 10.648.810, ocorreu dentro da janela fechada. Em 40 mm/s, não
  houve fechamento durante o toque. O teste `PhysicalIdle.CandidateP15P16`
  exige a ordem contato fechado → recarga → contato aberto.
- A saída integral do ensaio de 50 mm/s até 11 M ticks coincidiu com
  `MA17_TRACE_PC` desligado e ligado (SHA-256
  `9da9d070df62baea8b000d1590c3e189b41984870a216bb9904a7dd4cae95768`).
  A duração do contato é resultado da velocidade e histerese estimadas;
  ainda precisa de confronto elétrico/mecânico no veículo.
- Build aprovado; testes dirigidos `PhysicalIdle.CandidateP15P16` e
  `PhysicalLambda.ConditionalClosedLoop` passaram 2/2. Após a asserção
  de ordem das bordas, a regressão completa passou **219/219** em
  250,49 s. `git diff --check` ficou limpo; ROM Fiat preservada com
  SHA-256 `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
  Próximo ensaio: comparar uma medição temporal do interruptor real com
  esta janela de 90 ms e verificar se o pino P4.6 acompanha o contato.

## Incremento T4/T8: velocidade da haste e contato transitório

- `--idle-motor-speed-mm-s N` permite ensaiar 1–100 mm/s no atuador
  físico candidato; exige `--idle-bridge-p15-p16`. O padrão continua
  8 mm/s, uma estimativa, sem medida da peça. Não há escrita forçada na
  RAM da ECU.
- No cenário quente com ADC7=1,232 V, contato candidato P4.6, pedal
  de 8 mm entre 10 e 12 M ticks e demais parâmetros do ensaio T7/T8,
  4–40 mm/s publicaram `F84E/F85E=0Ah`; 50–100 mm/s não publicaram
  esse código. Isso é sensibilidade do modelo, não velocidade calibrada.
- Em 50 mm/s, a ponte comandou avanço da haste durante o pedal; uma
  borda no tick 10.656.460 registrou `contact=true`, seguida de recuo
  e `contact=false` na borda de 10.748.615. A amostra de 10,89 M já
  mostrava contato aberto. Em 40 mm/s, nenhuma borda amostrada marcou
  contato fechado durante o mesmo toque. A amostragem tardia ocultava
  o pulso mecânico que separa os ensaios.
- O fluxo original `2D57h–2D5Ah` lê P4.6, inverte o nível e grava
  `RAM24h.4`. Em 50 mm/s, essa flag passa a um, `29BCh` deixa seguir
  por `29C2h`, e `2A45h–2A4Bh` recarrega `F839=0Fh` antes da falha.
  Em 40 mm/s, `29BCh` salta por `29F5h` enquanto o contato permanece
  aberto; o contador avança até `2B42h`. `T2CON.1=0` apenas permite
  a recarga após a entrada em `2A45h`; não explica qual ramo foi tomado.
  `PhysicalIdle.CandidateP15P16` compara os dois cenários com a ROM
  original e verifica a borda, a recarga e o diagnóstico. Pinagem P4.6,
  polaridade da ponte e velocidade real continuam hipóteses de hardware.
- Reprodução: `ctest --test-dir build --output-on-failure -R
  PhysicalIdle.CandidateP15P16`; o teste usa a ROM Fiat e varia apenas
  `--idle-motor-speed-mm-s 40`/`50` no cenário de pedal. Build aprovado,
  regressão completa **219/219** em 220,34 s, `git diff --check`
  limpo e ROM SHA-256
  `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
  Com `--fluid-step-ticks 495`, o contato de 50 mm/s ainda apareceu
  nas bordas 10.656.454 e 10.666.700 e voltou a abrir em 10.748.615;
  40 mm/s manteve `F85E=0Ah` e 50 mm/s terminou com `F85E=00h`.
  Próximo: confrontar velocidade, sentido da ponte e nível do contato
  no atuador/placa reais; em paralelo, medir ADC5 e largura do bico
  durante ciclos rico/pobre para testar a interpretação T7.

## Incremento T7: tabela temporizada da classificação lambda

- **Hipótese das lookup tables rica/pobre:** a ROM confirma parâmetros
  temporizados de classificação da sonda em `733Dh..7342h`, recarga
  condicional de `RAM3Dh` por `7221h` e uma correção bidirecional que
  alcança o compare CC3 do injetor. O cruzamento de um limite com ADC5
  fixo altera o acumulador e a largura do pulso; com a sonda livre,
  inversões seguem a flag medida. Logo, há suporte para regulação
  estreita realimentada, mas ainda não para um tick/tabela que imponha
  alternância rica/pobre em cada injeção ou um período fixo. A função
  de armazenamento de oxigênio do catalisador é interpretação funcional,
  não uma finalidade identificada no código.
- A hipótese de um temporizador associado à mistura encontrou uma
  estrutura concreta: `ROM[733Dh..7342h] = 1E 01 0A 1E 01 0F`.
  `0D5Eh..0D73h` inicializa dois contadores e limites em XRAM baixa;
  `1644h..1687h` compara a leitura ADC5 processada em `RAM65h` com
  esses limites; `16B5h..16EAh` recarrega ambos os contadores com
  `1Eh` e reduz os limites em passos de `01h`. A tabela e o fluxo são
  bytes da ROM original, já cobertos pelo catálogo de calibração.
- O confronto físico anterior mostrou cinco reduções de limite em
  20 M ticks com a sonda livre e também com ADC5 fixo. Só a sonda
  livre apresentou inversões repetidas da direção de correção; elas
  seguiram a mudança da flag da sonda por 103–141 ticks, enquanto a
  redução de limite mais próxima ficou a 204.884–1.331.297 ticks.
  A evidência sustenta limites temporizados que participam da
  classificação, mas não um sequenciador autônomo de pulsos rico/pobre.
  O efeito desejado sobre o catalisador e a escala elétrica de ADC5
  ainda são inferências a confrontar no veículo.

## Incremento T4/T8: sentido elétrico candidato da ponte H

- `--idle-bridge-reverse` troca apenas o sinal da tensão aplicada ao
  motor DC para os dois comandos opostos P1.5/P1.6; exige
  `--idle-bridge-p15-p16`. O latch da ROM, o contato físico e as
  entradas TPS continuam pelos mesmos caminhos. O sentido real dos
  transistores da placa não foi medido.
- Com ADC7=1,232 V, contato P4.6 baixo quando fechado e 4 M ticks,
  o sentido anterior publicou `F84E=00h`; o invertido chegou ao
  batente mínimo de 0,040 rad e publicou `F84E=08h`, mesmo sem pedal.
  No cenário quente de 13 M ticks, o sentido invertido terminou no
  limite superior de 0,314 rad e manteve `F84E=08h`, enquanto o
  sentido anterior ficou em 0,160 rad com `F84E=00h`. Com pedal de
  8 mm entre 10 e 12 M, o sentido invertido já tinha esse erro antes
  do pedal. Assim, inverter a ponte não corrige o erro do toque
  moderado neste conjunto de hipóteses.
- `PhysicalIdle.CandidateP15P16` cobre o controle de 4 M ticks e
  a validação da opção. Próximo confronto elétrico: medir o sentido
  da haste para cada par de níveis da ponte na placa/atuador real.
- Build e teste de lenta dirigidos passaram; a regressão completa
  passou **219/219** em 206,27 s. As linhas JSONL e `[PHYSICAL-*]`
  do braço invertido em 4 M ticks coincidiram com/sem
  `MA17_TRACE_PC=1` (SHA-256
  `78fa2abcab6d626b964e46eee7af3ab0d58e4465caf2a8113bf7238bb6af4af0`).

## Incremento T4/T8: comparação do contato em P4.3 e P4.6

- `--idle-contact-p43` liga o mesmo interruptor físico ao pino P4.3
  como ensaio alternativo, com nível baixo quando fechado. A opção
  exige a ponte candidata P1.5/P1.6 e é exclusiva dos vínculos P4.6.
  A ROM Fiat lê ambos os pinos em rotas de lenta; isso justifica o
  contraste, mas não identifica a trilha na placa.
- Com ADC7=1,232 V e quatro milhões de ticks, o contato físico ficou
  fechado nos dois braços. Em P4.3, `RAM27/F84E=06h` e o batente
  terminou em 3,627 mm; em P4.6, `RAM27/F84E=00h` e o batente em
  7,049 mm. No cenário quente com pedal de 8 mm entre 10 e 12 M,
  P4.3 já tinha `F84E=06h` antes do pedal e continuou assim;
  P4.6 partiu de zero e publicou `0Ah` durante o toque.
- Portanto P4.3 sozinho não resolve o diagnóstico inesperado neste
  modelo e é um candidato nominal mais fraco sob essas hipóteses.
  `PhysicalIdle.CandidateP15P16` verifica o resultado de repouso e
  a exclusividade das opções. Ainda faltam medidas do circuito da ECU
  e confrontos de polaridade/saídas para atribuir o contato real.
- Após a opção P4.3, build e os 10 testes dirigidos de porta/lenta
  passaram. A regressão completa passou **219/219** em 203,63 s.
  As linhas JSONL e `[PHYSICAL-*]` do ensaio P4.3 em repouso foram
  idênticas com/sem `MA17_TRACE_PC=1` (SHA-256
  `83b813f5426e6e377f3ee2b24cc924df18f600a68588b3af466dd0088c2984bc`).
  Reproduzir com `ctest --test-dir build --output-on-failure -R
  PhysicalIdle.CandidateP15P16`.

## Incremento T6/T7: falha de centelha em motor quente

- Relação ensaiada: interrupção elétrica da bobina candidata 0 entre
  10 e 11 milhões de ticks, com motor aquecido e carga de 24 N·m.
  A ROM Fiat e os pulsos dos dois comandos P5 permanecem originais;
  `Ma17IgnitionStage` retira a energia dessa bobina e o evento físico
  sem queima segue para `ExhaustLambda`. ADC7=1,232 V, P4.6 como
  contato e ganho ADC5=5 são hipóteses do cenário, não medições da placa.
- Até 9,9 milhões de ticks, controle e falha tiveram amostras físicas
  e de ROM iguais. Aos 10,89 milhões, o braço com falha tinha nove
  centelhas perdidas e 374,601 RPM, contra 824,091 RPM no controle.
  A mistura de carga estimada continuou rica (`λ=0,960`), mas o
  oxigênio equivalente no escape foi `1,788`: a sonda ainda válida
  caiu a 0,1017 V, o pino ADC5 a 0,5083 V e `RAM65h` a 26.
- Após a reconexão em 11 milhões, a rotação chegou a 967,817 RPM em
  11,88 milhões; a contagem de falhas de centelha parou de crescer,
  o oxigênio equivalente voltou a 0,926 e a sonda a 0,7751 V.
  `F84E/F84F` ficaram zero após a recuperação. O teste
  `PhysicalLambda.WarmCoilMisfireRecovery` compara os dois braços sem
  escrever RAM nem alterar a ROM; passou. Isso comprova o contraste
  no modelo, sem calibrar a química da sonda ou a ligação da bobina.
- Reproduzir com `ctest --test-dir build --output-on-failure -R
  PhysicalLambda.WarmCoilMisfireRecovery`. `cmake --build build -j 4`
  aprovou e a regressão completa passou **219/219** em 204,41 s.
  As linhas JSONL e `[PHYSICAL-*]` do braço com falha foram idênticas
  com/sem `MA17_TRACE_PC=1` (SHA-256
  `a26fa03ab22048987d60637908ac9ccefbc2b65be9fe87ec8dc5a54a8481c229`).
  Próximo: confrontar os dois comandos P5 e o sinal da sonda no veículo
  para validar polaridade, pares de cilindros e atraso de transporte.

## Incremento T1/T8: abertura elétrica do sensor da roda

- `--crank-sensor-open-tick` e `--crank-sensor-restore-tick` cortam
  somente as bordas entregues a P1.0/CC0 no modo físico. Virabrequim,
  dentes e lacunas continuam pelo balanço de torque. O fio aberto
  assenta o pino em nível baixo, sem inventar uma borda de captura; esse
  nível de repouso é uma hipótese elétrica, ainda sem medição da placa.
  A restauração usa o próximo dente real. Os ticks exigem ordem válida.
- Com arranque até 495 mil ticks, carga de 24 Nm e corte em 10 milhões,
  o controle chegou a 1.194,682 RPM, 483 inícios CC3 e `RAM47h=47`.
  No braço aberto, ainda ocorreram lacunas enquanto a roda girava,
  mas nenhum novo início CC3; o motor parou com `RAM47h=0`,
  `F84E=0` e `F850=02h` bruto. Este último valor também apareceu
  em parada induzida por carga; não foi atribuído a um DTC de sensor.
- Restaurar em 10,15 milhões de ticks retomou captura e injeção:
  488 inícios CC3, 1.273,490 RPM, `RAM47h=51` e os bancos
  `F84E/F84F/F850/F85E/F85F/F860=0` ao fim. Com passo de fluido
  495 em vez de 990 ticks, houve os mesmos 488 pulsos e
  1.273,216 RPM. O teste `PhysicalCrank.SensorOpenAndRestore` compara
  controle, abertura e recuperação com a ROM original; passou 1/1.
- Reproduzir com `ctest --test-dir build --output-on-failure -R
  PhysicalCrank.SensorOpenAndRestore`. No ensaio de 4 milhões de ticks
  com abertura em 2 milhões e restauração em 2,15 milhões, a saída
  padrão com/sem `MA17_TRACE_PC=1` teve SHA-256 idêntico
  `954f3d766b58d3e2251e5478662e688537d934829a67941a0b797e7f8f1d02bc`.
- Na primeira regressão paralela, o teste de 60 s comparou também o
  texto do PTY e falhou porque esse caminho pode variar entre processos.
  Ele agora compara todos os eventos JSONL e resumos `[PHYSICAL-*]`;
  qualquer diferença na física continua reprovando. Passou isolado
  e a nova suíte paralela aprovou **218/218** em 215,19 s.

## Incremento T2/T8: pista TPS2 elevada eletricamente

- `--tps2-high-tick` e `--tps2-restore-tick` aplicam 5 V apenas a
  ADC0 no intervalo indicado; cabo, contato, pista 1 e ângulo físico
  continuam independentes. `tps_ram` e `[PHYSICAL-TPS]` mostram a
  tensão efetiva no pino, não só a tensão geométrica.
- Num ensaio curto, a falha em 800 mil ticks levou `RAM60h` de 40 a
  255 e `RAM28/F84F=04h`, com `RAM66h=95` e ângulo inalterados.
  Restaurar aos 1,2 milhão trouxe ADC0 e `RAM60h` ao valor inicial,
  mas `RAM28/F84F=04h` persistiu até 2 milhões. O teste
  `PhysicalTps.FiatRomTracks` cobre ambos os braços e passou.
- No cenário quente, elevar ADC0 de 10 a 14 milhões de ticks publicou
  `RAM28/F84F=04h`; a entrada voltou à curva física após a restauração,
  porém o bit permaneceu até 30 milhões. Em consulta PTY/K-Line após
  a restauração aos 8 milhões, a ROM transmitiu `02 06 1E` em 9,9
  milhões, código `0602h` do grupo TPS na tabela local. A resposta
  ainda usa status `1Eh`; não equivale a uma tensão ainda defeituosa.
  `PhysicalDiagnostics.KlineFaultHistory` confere essa tripla.
- Os testes TPS/K-Line dirigidos passaram; a regressão completa após
  acrescentar o estímulo aprovou **218/218** em 230,62 s. Com/sem
  `MA17_TRACE_PC=1`, as 124 linhas físicas do ensaio curto foram
  idênticas (SHA-256
  `2a29d249b8f93b62eb16c5d0b1aa5baf62b1d875d3c92cf21df60dbbc349a146`).
- A retenção neste boot exige rastrear a guarda de limpeza da ROM e
  comparar com um novo ciclo de chave antes de classificar sua duração
  como propriedade geral da ECU. A pinagem ADC0→pista 2 permanece
  condicionada à interpretação do hardware Fiat.
- A rotina em `1049h..10AAh` carrega `RAM60h` (ADC0) e `RAM66h`
  (ADC6), arma `B.7` quando ADC0 chega a `F0h`, e só alcança a limpeza
  em `10A8h` quando ADC6 é pelo menos `DCh`, ADC0 pelo menos `12h`,
  `PSW.5` está limpo e `RAM6Dh.0` já foi consumido. Com TPS1 em
  repouso (`RAM66h=95`), o desvio em `1077h` impede essa limpeza;
  `113Eh..1146h` continua copiando `B.7` para `RAM28h.2`.
  Num contraste de 2 milhões de ticks, uma elevação elétrica breve
  da TPS1 depois da restauração da TPS2 limpou `RAM28h.2/F84Fh.2`.
  Esse estímulo cria também uma falha da TPS1 (`F85Fh=04h`), portanto
  não representa procedimento de reparo nem prova de limpeza espontânea.
  Com pedal físico de 20 mm após restaurar a TPS2, `RAM66h` saturou
  em `197`, abaixo do limiar digital `DCh=220`; `RAM28h/F84Fh=04h`
  persistiu. Isso limita a conclusão à curva TPS e ao intervalo
  simulados, sem supor um procedimento de recuperação no veículo.
  `PhysicalTps.FiatRomTracks` cobre os três resultados.

## Incremento T7: P3.4 como candidato ao relé da bomba

- A ROM limpa `P3.4` no boot (`0881h`), produz pulsos altos curtos em
  `0361h/0395h` e o coloca alto em `3C63h` após um contador. Na partida
  sem rotação, ficou baixo até cerca de 1,18 milhão de ticks; com motor
  funcionando, permaneceu baixo e subiu após a parada induzida. Isso é
  compatível com comando ativo em nível baixo do relé da bomba, mas a
  ligação do pino da CPU ao terminal 28 da ECU ainda não foi comprovada.
- `--pump-relay-p34` habilita somente no modo físico esse *binding*
  candidato. Uma retenção estimada de 9.900 ticks (~10 ms) filtra os
  pulsos altos curtos antes de aplicar 12,5 V ao aquecedor de 6 Ω. O
  padrão continua sem alimentação do aquecedor. A retenção e a
  resistência são hipóteses de engenharia, não medidas da placa/sonda.
- Sem partida, o candidato fechou no tick 781, abriu em 1.191.783 e a
  sonda aqueceu de 20 °C para cerca de 90 °C antes de esfriar, sem sinal
  lambda válido. No cenário quente, estava a 232,1 °C no primeiro
  segundo, contra 161,8 °C sem alimentação; ambos os braços atingiram
  validade e os bancos diagnósticos acompanhados permaneceram zero.
  Antes da validade, ADC5 e `RAM65h` eram iguais. Em 1,98 milhão de
  ticks, ADC5 foi 4,3132 V com aquecedor e 4,2207 V no controle;
  `RAM65h` foi 221/216. O efeito chega, portanto, à entrada elétrica
  e à leitura da ROM nesse cenário, condicionado à pinagem assumida.
  Nas bordas CC3, os dois braços foram idênticos até `RAM65h` divergir
  no tick 1.234.879; as flags lambda divergiram em 1.266.873 e
  `RAM14h:15h`/o início efetivo do pulso em cerca de 1.299.061.
  O teste verifica essa ordem sem exigir ticks ou valores exatos.
  Com parada induzida, abriu em 11.431.156 ticks e a sonda esfriou.
- Reduzir o passo de fluido de 990 para 495 ticks manteve idênticas,
  na precisão impressa, as três primeiras temperaturas da sonda
  aquecida; ADC5 diferiu menos de 0,01 V nas mesmas amostras. O teste
  integrado agora verifica esse contraste de convergência.
- Em 40 milhões de ticks com carga de 24 Nm, os últimos 20 pontos de
  1 s tiveram λ físico médio 1,0037 sem aquecedor e 1,0079 com o
  *binding* P3.4. Ambos cruzaram λ=1 quinze vezes e produziram 1.225
  pulsos CC3 na execução inteira; `F84E/F84F/F850/F85E/F85F/F860`
  terminaram zero. A sonda chegou a 650/850 °C (este último é o limite
  estimado do modelo). A amostragem de 1 s não determina o período
  exato da alternância nem demonstra uma finalidade catalítica.
- O modelo térmico agora usa o menor tempo de resposta entre gases
  quentes e aquecedor quando ambos atuam; antes, energizar o aquecedor
  atrasava artificialmente o aquecimento por gases. O teste integrado
  confronta partida sem rotação, marcha e parada com o controle sem
  *binding*; ainda falta identificar a trilha física do terminal 28.
- Validação: build e teste direcionado **7/7**, suíte completa **217/217**;
  `git diff --check` limpo. O trace opcional de latch preservou o hash
  SHA-256 da saída padrão (`d985f1ad28b68e2672ead6be466ba0307672b86f5a783b310573501ef9cf5cc1`)
  em 2 milhões de ticks sem partida. A ROM Fiat manteve SHA-256
  `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.

## Incremento T4/T8: circuito aberto no motor do batente

- `--idle-motor-disconnect-tick` e `--idle-motor-reconnect-tick`
  interrompem apenas a tensão aplicada ao motor DC durante o intervalo
  escolhido. P1.5/P1.6, ROM, TPS e contato físico permanecem ativos.
  As opções exigem o binding candidato da ponte H e ticks ordenados.
- No pedal de 8 mm entre 10 M e 12 M ticks, as duas bordas da ponte H
  foram idênticas com motor conectado e aberto. Em 11,88 M ticks, a
  haste mediu 7,999/4,086 mm, respectivamente; borboleta 0,280 rad,
  contato aberto e `RAM66h=9Dh` foram iguais. Os eventos que armaram
  `RAM27h=0Ah` em 10.997.615/618 e publicaram `F84Eh=0Ah` em
  11.113.596 também coincidiram. Depois da reconexão, a haste voltou
  a mover-se; ambos terminaram `F84E=0, F85E=0Ah`.
- `PhysicalIdle.MotorOpenDuringPedal` passou e a suíte completa passou
  **214/214**. O JSONL físico com/sem `MA17_TRACE_PC=1` foi idêntico
  (SHA-256 `bb5a717763a7eab56300d43f84d3ac8ed6d8cb694180901af68924fcb9f8667e`).
  Com passo de fluido 495 em vez de 990 ticks, a haste aberta ficou
  em 4,086 mm em 11,88 M e `F85E=0Ah` persistiu. Assim, nesse pedal,
  a falha publicada não depende do movimento real da haste enquanto
  o cabo a mantém afastada. A pinagem da ponte H e P4.6 permanece
  candidata; o contraste não identifica a causa elétrica no veículo.

## Incremento T4/T8: pedal mantido e retorno do batente

- Prolongar o pedal de 10 M a 16 M ticks, no mesmo cenário físico quente
  com ADC7/P4.6/P1.5–6 condicionais, separou duas respostas da ROM.
  Com 8 mm (0,280 rad), contato aberto e `RAM66h=9Dh`, a haste parou
  perto de 8,0 mm enquanto o pedal permaneceu aberto. `RAM27h=0Ah`
  foi armado perto de 10,998 M; `F84Eh=0Ah` apareceu em 11,114 M.
  Após a soltura, `F84Eh` limpou em ~16,030 M, mas `F85Eh=0Ah`
  permaneceu como histórico. Não houve reencontro mecânico durante os
  6 s de pedal.
- Com 10 mm (0,360 rad), o contato também ficou aberto e
  `RAM66h=B4h`, mas a haste ficou perto de 4,06 mm e `F84E/F85E`
  terminaram zero. Um bit 3 transitório após a soltura foi limpo antes
  da publicação. A distinção 8/10 mm persiste com passo físico de 990
  ou 495 ticks: no passo menor, haste 7,998/4,058 mm em 15,84 M,
  publicação 8 mm em 11.113.391 e nenhuma publicação 10 mm.
  Reproduzir com o cenário de `PhysicalLambda.ConditionalClosedLoop`,
  `--pedal-step-tick 10000000 --pedal-release-tick 16000000
  --pedal-mm 8` ou `10`, e opcionalmente `--fluid-step-ticks 495`.
  O contraste favorece a guarda TPS/contato já rastreada; não prova
  pinagem nem que o diagnóstico corresponda a defeito real do batente.

## Incremento T6/T7: centelha fraca e oxigênio residual

- O evento de combustão agora distingue combustível fornecido de massa
  efetivamente queimada quando a carga relativa da bobina é baixa. A
  fração queimada vai de zero sem centelha a um em 0,80; esse limiar é
  uma estimativa ajustável, não medida da bobina. O torque mantém a
  relação anterior com a carga relativa; seu trabalho útil não excede
  o permitido pela massa queimada. O escape interpola oxigênio residual
  e temperatura entre misfire completo e queima completa; a relação
  linear também é uma aproximação, não uma curva de sonda medida.
- No cenário Fiat quente de 20 M ticks, os 423 intervalos de carga
  observados após 7,5 M mediram 1.743–1.969 ticks (mediana 1.850),
  equivalentes a 0,88–0,99 da referência de 1.980 ticks. Desde a partida,
  o mínimo observado foi 1.617 ticks, ou 0,817 da referência. Tratar essa
  diferença como combustível não queimado manteve a leitura física
  sempre rica após 9,9 M e falhou no ensaio lambda. A saturação em
  0,80 conserva a queima completa no nominal e a relação de torque
  anterior. Uma primeira curva reduziu o trabalho na partida e falhou
  em dois cenários longos; foi substituída antes da regressão final.
- `cmake --build build -j 4` e `ctest --test-dir build
  --output-on-failure -j 4` passaram **213/213**, incluindo o novo
  teste de centelha fraca, 60 s de motor físico e propagação da
  correção lambda até CC3. A pinagem de ignição e a relação real entre
  carga da bobina e combustão continuam condicionais.

## Incremento T4/T8: contato elétrico fechado durante o pedal

- `--idle-contact-closed-tick` usa a mesma entrada candidata P4.6 e
  a mesma opção de restauração da falha aberta. As duas modalidades
  são mutuamente exclusivas; nenhuma altera a geometria, os TPS ou
  escreve diretamente na RAM/ROM. O ensaio parte do mesmo estado até
  o tick 10 M.
- Com pedal de 8 mm entre 10 e 12 M ticks, o contato físico abriu e
  a borboleta permaneceu em 0,280 rad nos dois braços. No controle,
  P4.6 subiu na leitura de 10.001.243, `2B42h/2B49h` armaram os bits
  1/3 de `RAM27h` perto de 10.997.539, e o histórico terminou
  `F85E=0Ah`. Com P4.6 mantido eletricamente baixo, essas duas
  rotas não armaram os bits; `2C0Ch` ainda armou transitoriamente o
  bit 3 e o histórico terminou `F85E=08h`.
- Em 11,88 M ticks, a haste mediu 14,22 mm no controle e zero com
  sinal forçado fechado. O resultado isola uma dependência do bit 1
  e do comando de haste em relação à entrada candidata, mas **não**
  demonstra que o código `1A01h` seja causado só por esse fio nem
  comprova que o terminal 8 da ECU alcance P4.6 da CPU.
- No braço forçado fechado, a primeira passagem `2C0Ch` em
  10.004.061 viu `F83Bh=32h` (50 decimal); `2C19h` limpou o bit oito
  ticks depois.
  A contagem chegou a zero e `2C0Ch` reteve `RAM27.3` em 10.515.759.
  `41E5h` publicou `F84E=08h` em 10.704.896, ainda durante o pedal.
  Depois da restauração, `41E5h` publicou zero em 12.136.902; só
  `F85E=08h` permaneceu como histórico. O teste confere essa ordem.
- O trace optativo `MA17_TRACE_IDLE_CONTACT_CHECK=1` com
  `MA17_TRACE_PC=1` mostrou a guarda interna em `2BC2h..2C19h`.
  No braço forçado fechado, `F83Ah` foi de `0Fh` a zero entre
  10.004.010 e 10.157.549 ticks; `F83Bh` foi de 50 a zero em
  10.515.706. Em `2C0Ah` no tick 10.515.758, a subrotina retornou
  `A=00h` com `F83Ah=F83Bh=0`; `2C0Ch` armou `RAM27.3` no tick seguinte.
  Antes disso, `2C19h` limpava o bit enquanto `F83Bh>0`. No braço
  nominal, só houve a entrada de `2BC2h` durante o pedal, pois a
  leitura do pino tomou outro ramo. `P4_LATCH6` no trace é o latch,
  não o nível físico lido por `JB P4.6`; o contraste de fluxo indica
  a diferença de entrada. `PhysicalIdle.ContactClosedDuringPedal`
  passou 1/1 após a instrumentação. O JSONL físico do braço forçado
  fechado foi idêntico com/sem trace (SHA-256 `5718117cac28ed81545be1403fe5a7279047f25df1bb5170cdc4395bddbaba1b`).
  Esses contadores explicam a latência do bit 3 nesta intervenção,
  sem validar a pinagem da placa ou resolver `F85E=0Ah` no pedal nominal.
- `PhysicalIdle.ContactClosedDuringPedal` e o teste da falha aberta
  passaram 2/2. A regressão completa após esta extensão passou
  **212/212** em 156,74 s; SHA-256 da ROM Fiat preservado.

### Ordem entre comando da haste e diagnóstico no toque nominal

- No perfil físico padrão, o comando candidato P1.5/P1.6=`1/0`
  começou em 10.175.180 e terminou em 10.697.416 ticks. A última
  redução `F839h=2Fh→2Eh` veio em 10.997.602; `2B42h/2B49h`
  armaram `RAM27.1/.3` 13/16 ticks depois. Com o perfil TPS de
  bancada, a mesma ordem ocorreu em 10.175.180, 10.697.416,
  10.997.488 e 10.997.539/542 ticks.
- Durante esse intervalo o cabo manteve a borboleta a 0,280 rad e
  o contato físico aberto: o movimento do batente não altera os TPS
  enquanto a alavanca está afastada. A ordem é compatível com uma
  verificação temporizada sem realimentação de posição nesse estado,
  mas não demonstra que essa seja a intenção da ROM ou que P1.5/P1.6
  e P4.6 estejam ligados às peças assumidas. A regressão lambda
  confere a ordem no perfil padrão sem fixar os ticks exatos.
- O trace ampliado de `2B2Dh..2B42h` mostrou no perfil padrão
  `R2=R3=90h` (`97h` no perfil TPS de bancada), `A=0Dh` após a
  subtração em `2B30h` e carry limpo. A ROM tomou o salto direto
  `2B31h→2B38h`, embora `F83Eh=33h` ainda fosse não nulo. Em
  `2B38h`, leu `F839h=2Eh`: bit 6 limpo e bit 5 ligado levam a
  `RAM27.1`; bit 7 limpo leva também a `RAM27.3`. Isso identifica
  a condição digital imediata de `F85E=0Ah` nesse toque.
  `PhysicalLambda.ConditionalClosedLoop` verifica a guarda e passou
  1/1 após a ampliação observacional; os JSONL físicos antes/depois
  dela foram idênticos.
- A origem do comparando foi seguida no mesmo cenário físico:
  `104Bh` lê `RAM66h` para `R4`; `11C4h..11D4h` produz
  `RAM6Fh=R4−0Dh` no ramo observado; `29A3h` leva esse byte a `R2`.
  Com 8 mm, ângulo 0,280 rad e ADC0/6=1,608/3,062 V,
  `RAM66h=9Dh→RAM6Fh=90h`; com 12 mm, 0,440 rad e
  2,023/3,857 V, `C5h→B8h`. A guarda de `2A9Eh` mantém a
  contagem para `R2≤A5h` e restaura `F839h` acima disso.
  Passos físicos intermediários delimitaram a mudança: 9 mm deu
  `RAM66h=A8h`, `R2=9Bh` e `F84E=0Ah`; 10 mm deu `B4h`,
  `R2=A7h` e `F84E=0`. Os JSONL de 9/10 mm foram idênticos
  com e sem trace; a regressão de 8/12 mm passou 1/1 após conferir
  o produtor `11CCh`. A fronteira `RAM66h≤B2h` vale só para
  esse ramo e estas hipóteses de TPS/contato. Não é calibração
  medida da peça; o motivo físico do diagnóstico ainda depende
  de verificar sinais e pinagem no veículo.
- Regressão após esta cadeia: `ctest --test-dir build
  --output-on-failure -j 4` aprovou **212/212** em 193,93 s;
  hash da ROM Fiat preservado.

## Incremento T4/T8: abertura elétrica isolada do contato de lenta

- `--idle-contact-open-tick` e `--idle-contact-restore-tick` simulam um
  fio aberto apenas no binding candidato P4.6, em ticks do relógio
  virtual. O contato mecânico, cabo, TPS e ROM continuam intactos; a
  opção exige o binding do contato e ordenação válida dos ticks.
- No cenário quente com perfil TPS de bancada e sem pedal, abrir o
  sinal entre 10 e 12 milhões de ticks fez P4.6 subir na primeira
  leitura em 10.001.243 e voltar a baixo em 12.000.503. O contato
  físico permaneceu fechado. Em 11,88 milhões, a haste estava a
  10,30 mm, contra 12,38 mm no controle; em 12,87 milhões, após
  restaurar o fio, avançou a 11,70 mm. Antes da falha, os estados
  físicos amostrados eram idênticos nos dois braços.
- `F84E/F85E` terminou zero em ambos até 14 milhões de ticks. Assim,
  contato aberto eletricamente por 2 s **sem pedal** altera o comando
  do atuador nesse binding, mas não reproduz o histórico `0Ah` do
  toque de pedal. A interpretação física continua dependente de
  comprovar o terminal 8 da ECU até P4.6 da CPU.
- `PhysicalIdle.ContactOpenElectricalFault` passou 1/1; regressão
  direcionada de porta, lenta, lambda e K-Line passou 10/10 em
  80,69 s. A suíte completa após os dois novos testes passou
  **211/211** em 152,80 s. O contraste seguinte de contato fechado
  durante o pedal está registrado acima.

## Incremento T4: curso angular do batente e toque de pedal

- O limite anterior de 12 mm de haste correspondia a apenas ~7,2° de
  batente no cenário quente com base de 5 mrad. O [manual MA1.7 da
  Alfatest](https://pt.scribd.com/document/656677219/Alfatest-Bosch-MA-1-7)
  descreve cerca de 18° de abertura no curso completo do atuador.
  `IdleActuator` agora limita o ângulo absoluto a ~18° e deriva o
  deslocamento máximo da relação haste/alavanca assumida. A abertura
  publicada é referência de serviço; a relação de 10 rad/m e o curso
  correspondente continuam estimativas sem medição da peça.
- Com pedal de 8 mm de 10 a 12 milhões de ticks e perfil TPS de
  bancada, a haste alcançou 14,22 mm durante o pedal, antes truncada
  em 12 mm. O contato ficou aberto; ao fim de 20 milhões de ticks,
  voltou a fechar e `F84E=0`, mas `F85E=0Ah` ainda persistiu.
  Portanto, a saturação em 12 mm **não era condição necessária** para
  esse histórico de falha. A causa elétrica ou lógica dos bits de
  diagnóstico exige um estímulo mais isolado do contato e dos dois TPS.
- A recuperação da perturbação de sonda no cenário de 20 milhões de
  ticks mudou ligeiramente: a diferença de λ físico entre os braços
  ficou ~0,065 no segundo 18 e ~0,022 no segundo 19. O teste compara
  a recuperação no fim da janela; o instante exato de convergência
  ainda depende da geometria e dos parâmetros estimados.
- `cmake --build build -j 4` e regressão completa
  `ctest --test-dir build --output-on-failure -j 4` passaram, 209/209
  em 149,07 s. A ROM Fiat permaneceu sem alterações. Depois dessa
  regressão, `IdleActuator.FullTravelStopsAtServiceAngleAndReturnsToBase`
  foi acrescentado para conferir avanço até ~18° e recuo ao batente
  base; build e `ctest --test-dir build --output-on-failure -R
  'IdleActuator\.'` passaram 2/2. A suíte completa ainda não foi
  repetida após adicionar esse teste.

## Incremento T5: janela de decisão do canal ADC7

- Contraste posterior à partida, no cenário físico quente com pedal de
  8 mm em 10–12 M ticks: subir ADC7 de 1,232 para 1,260 V em 9 M
  mudou `RAM67h=63→65`, mas conservou `F8DDh=AAh` e `2Bh.5=0`.
  `2B42h/2B49h/41E5h` armaram e publicaram `RAM27/F84E=0Ah` nos
  mesmos ticks 10.997.615/10.997.618/11.113.596 que no controle.
  O teste `PhysicalAdc7.StartupGateLatch` foi ampliado e passou 1/1
  em 21,50 s. Assim, a entrada ADC7 já ultrapassada depois do boot
  não explica essa falha do pedal no estado testado. Sua identidade
  elétrica e outras rotas de rearmamento continuam abertas.
- A ROM Fiat usa `RAM67h` em `3B22h`, mas a comparação com `41h`
  só ocorre quando o estado `XRAM[F8DDh]` passou abaixo de `1Ah`.
  O reset coloca `55h` em F8DDh; a rota `07B6h..07DFh` pode carregar
  `19h` após um timeout, e `3B2Fh..3B38h` leva a contagem a `AAh`
  ou `55h`. Portanto, o limiar 64/65 não é um corte contínuo e
  incondicional da injeção durante a marcha.
- `--adc7-step-mv` com `--adc7-step-tick` aplica um degrau elétrico
  somente ao pino ADC7 do cenário físico, sem escrever RAM ou ROM.
  O resumo `[PHYSICAL-ADC7]` mostra `RAM67h`, `F8DDh` e `2Bh.5`.
  Em 4 milhões de ticks, 1,232 V constantes deram 150 pulsos CC3,
  `RAM67=63`, `F8DD=AAh`, guarda limpa. Subir a 1,260 V no tick
  3.000.000 terminou com `RAM67=65`, mas preservou exatamente os
  150 pulsos, os ticks de condução e a rotação: `F8DD=AAh` e guarda
  limpa. Subir no tick 800.000 deixou 16 pulsos e terminou com
  `F8DD=55h`, guarda ligada. Começar em 1,260 V e baixar a 1,232 V
  no tick 3.000.000 terminou com `RAM67=63`, `F8DD=55h` e nenhum
  pulso. A memória da decisão foi observada **neste boot sem scanner**;
  outras rotas que rearmem F8DDh ainda precisam ser examinadas.
- `PhysicalAdc7.StartupGateLatch` e
  `PhysicalIntake.ConditionalCc3Fuel` passaram 2/2 em 33,29 s;
  reproduzir com `ctest --test-dir build --output-on-failure -R
  'PhysicalAdc7.StartupGateLatch|PhysicalIntake.ConditionalCc3Fuel'`.
  A última suíte completa anterior a este observador aprovou 208/208.
  A tensão de 1,232 V continua uma hipótese de ensaio: falta a
  ligação da entrada ADC7 na placa e sua grandeza física.
- Extensão do braço inverso no mesmo boot: com `--adc7-mv 1260
  --adc7-step-mv 1232 --adc7-step-tick 3000000 --stop-ticks 30000000`,
  a ROM terminou com `RAM67h=63`, `F8DDh=55h` e `2Bh.5=1`;
  não ocorreu nenhuma borda CC3 nem injeção e o motor parou.
  Assim, a baixa tensão posterior não liberou a guarda em 30 s
  virtuais nesse cenário. Ainda falta testar um novo ciclo de partida
  e identificar a função elétrica real de ADC7.

## Incremento T2: confronto da curva TPS com pontos de bancada

- O [manual MA1.7 da Alfatest](https://pt.scribd.com/document/656677219/Alfatest-Bosch-MA-1-7)
  descreve a pista 1 como útil de 0° a 24°, perto de 0 V fechada e
  perto de 5 V em 24°; a pista 2 entra em 18° e segue até ~90°.
  O [material de bancada de Flávio Xavier](https://pt.scribd.com/doc/89811032/Atuador-IAC-Bosch-Monomotronic-M1-7)
  informa 0,20–0,27 V fechada, ~1,00 V em lenta e 4,50–4,80 V
  de 24° até abertura total para a pista 1, e ~4,30–4,60 V em
  abertura total para a pista 2. São referências de sistema, não
  medições do nosso corpo de borboleta.
- O perfil integrado atual foi escolhido por um par de estímulos ADC
  aceito pela ROM (60h/66h = 40/95 no batente estimado de 4°).
  Ele produz ~3,86 V na pista 1 em 24°, abaixo da referência de
  bancada. `TpsCircuitParameters::bench_typical()` acrescenta uma
  curva **condicional**: 0,27/1,00/4,65 V na pista 1 em 0°/4°/24°;
  pista 2 de 0 V até 18° a ~4,5 V em 90°. A interpolação e o ângulo
  de lenta de 4° são inferências de engenharia, não dados publicados.
  `--tps-bench-profile` seleciona essa curva só no executor físico;
  o perfil integrado padrão permanece disponível para comparação.
- Build e testes `Ma17TpsCircuit|PhysicalTps` passaram 3/3;
  a regressão conjunta com `PhysicalLambda.ConditionalClosedLoop` e
  `PhysicalLambda.TableCrossingToCc3` passou 5/5 em 125,95 s.
  `git diff --check` limpo e SHA-256 da ROM Fiat preservado.
  No cenário quente condicional de 20 milhões de ticks, a curva de
  bancada deixou `RAM60/66=0/62` e `RAM6F=49`, contra `39/94` e `81`
  no perfil padrão. O contato ficou fechado nos dois; o batente DC
  moveu a haste a 8,549 mm, contra 6,074 mm. A ROM sustentou
  927,257/880,039 rpm e 625/600 pulsos CC3 com curva de bancada/padrão;
  `RAM27=F84E=F885=F84F=0` em ambos. Isto demonstra aceitação
  **nesse cenário**, não calibração elétrica da peça nem ausência de
  falha em toda a faixa de abertura. Um toque de 8 mm entre 10 e 12
  milhões de ticks com a curva de bancada voltou à lenta em 931,817 rpm;
  `F85E=0Ah` ao final é estado bruto a investigar, também observado
  anteriormente com o perfil padrão sob esse toque.
- `PhysicalTps.BenchProfileClosedLoop` compara dois perfis com a ROM
  original, incluindo RPM, RAM TPS, contato, movimento do batente,
  pulsos CC3 e bancos de falha. O teste passou 1/1 em 15,64 s.
  Reproduzir: `ctest --test-dir build --output-on-failure -R
  'PhysicalTps.BenchProfileClosedLoop'`.
- Regressão completa após o binding opcional: `ctest --test-dir build
  --output-on-failure` **208/208**, em 494,31 s.

### Sobreposição TPS e diagnóstico da ROM

- A [verificação de transição de Flávio Xavier](https://pt.scribd.com/doc/89811032/Atuador-IAC-Bosch-Monomotronic-M1-7)
  pede 0,45–0,70 V na pista 2 quando a pista 1 indica 4,40–4,60 V.
  A primeira interpolação da curva opcional dava apenas 0,307 V
  na pista 2 quando a pista 1 marcava 4,453 V. O [manual MA1.7 da
  Alfatest](https://pt.scribd.com/document/656677219/Alfatest-Bosch-MA-1-7)
  descreve verificação de sincronismo das pistas em 18°–24° e falha
  TPS quando os sinais são incompatíveis.
- A execução física confirmou a consequência: com a primeira curva,
  cabo de 10/11 mm (20,6°/22,9°) produziu `RAM28=F885=F84F=01h/06h`;
  o perfil padrão produziu zero nos mesmos ensaios. A alteração ficou
  limitada ao hardware TPS: a curva opcional agora tem trecho próprio
  de 18° a 24° e passa por ~0,55 V na pista 2 quando a pista 1
  alcança ~4,5 V. Após 24°, a inclinação volta a ser menor para chegar
  perto de 4,5 V em 90°. Essas inclinações intermediárias são
  inferências, não medições contínuas da peça.
- Com o cenário quente de 4 milhões de ticks e cabo de 9/10/11/12 mm
  (~18,3°/20,6°/22,9°/25,2°), a ROM publicou `RAM60=2/14/26/36`
  e `RAM66=185/206/228/238`; contato abriu e
  `RAM28=F885=F84F=0` nos quatro braços. O teste integrado percorre
  esses pontos e o ensaio de lenta; passou 3/3 junto aos testes
  unitários TPS em 23,02 s. A malha ainda depende de ADC7 e ligações
  de ponte H condicionais. Próximo: medir as duas pistas no veículo
  e verificar pontos adicionais da curva, sobretudo fora da transição.

## Hipótese T7: alternância rica/pobre próxima de λ=1

- Contraste adicional com entrada elétrica fixa: no cenário quente de
  20 milhões de ticks, `--lambda-stuck-tick 2000000
  --lambda-stuck-mv 2600 --lambda-adc-gain 5`, `RAM65h=85h` após
  estabilizar. `F8EA/F8E8` reduziram seus limites em cinco pares,
  aproximadamente nos ticks 4,759,426, 7,831,421, 10,903,438,
  13,975,658 e 17,047,448. A classificação mudou de `02h` para
  `08h` uma vez, no tick 7,841,889; não houve alternância sustentada
  apesar das três reduções posteriores. Nenhuma visita a `1958h` foi
  observada após 7,5 milhões de ticks nesse braço. O contraste
  delimita a função temporizada dos limites, sem atribuir a eles
  um período autônomo de mistura rica/pobre. Reproduzir com o cenário
  de `PhysicalLambda.TableThresholdAtFixedAdc`, `--stop-ticks
  20000000` e `MA17_TRACE_PC=1 MA17_TRACE_LAMBDA_BOUNDS=1
  MA17_TRACE_LAMBDA_DIRECTION=1`.
- No cenário físico quente atual de 20 milhões de ticks, com ganho ADC5
  assumido de 5 e `MA17_TRACE_PC=1 MA17_TRACE_LAMBDA_BOUNDS=1
  MA17_TRACE_LAMBDA_DIRECTION=1`, `F8EAh` e `F8E8h` reduziram seus
  limites em cinco pares nos ticks 4.759.420, 7.831.875, 10.903.431,
  13.975.445 e 17.047.435 (primeiro byte de cada par). Houve oito
  inversões da correção entre 11.784.127 e 17.661.900; a redução de
  limite mais próxima de cada uma ficou a 204.884–1.331.297 ticks.
  Já a última mudança de flag da sonda precedeu as inversões por
  103–141 ticks. Assim, a tabela temporiza os limites que podem
  afetar a classificação, mas essas reduções não foram o gatilho
  imediato das inversões observadas. O JSONL físico foi idêntico ao
  ensaio sem o trace de limites (SHA-256
  `1904bf90994eb44fd9aef4ebfd1ca66e7ce9a0ae397d99400bfc7157c75da364`).
  Próximo confronto: medir a tensão ADC5, os pulsos do bico e a sonda
  no veículo para separar atraso de gás, classificador e atuação.
- Sensibilidade do cenário físico atual ao ganho elétrico **assumido**
  de ADC5: com ganho 5, as oito inversões em `1958h` ocorreram entre
  11.784.127 e 17.661.900 ticks; com ganho 4, entre 11.425.975 e
  18.880.418. As primeiras diferiram 0,362 s e as últimas 1,231 s,
  mesmo com igual número de inversões. A última mudança de flag da
  sonda precedeu cada inversão em 78–141 ticks. `RAM3Dh` variou de
  `01h` a `4Bh` nesses pontos e nunca precisou chegar a zero.
  Reproduzir com o cenário de `PhysicalLambda.ConditionalClosedLoop`,
  `--lambda-adc-gain 4` ou `5`, e
  `MA17_TRACE_PC=1 MA17_TRACE_LAMBDA_DIRECTION=1`. Com ganho 4, o
  JSONL físico foi idêntico com e sem o trace (SHA-256
  `6e3e8c540e4da4281c80c51408fe05f9ad180fbdebc846bb23b9958a979297ab`).
  O deslocamento sustenta dependência da realimentação neste ensaio,
  sem identificar a ligação ou o ganho da placa real. Próximo teste:
  comparar estes instantes com tensão ADC5 e pulso CC3 medidos no carro.
- Há contagens na ROM, mas a atribuição precisa continua aberta:
  `733Dh..7342h` recarrega e reduz limites de classificação de ADC5;
  a rota de `7200h` controla uma correção bidirecional que alcança
  `5Ch:5Dh`, `14h:15h` e pulsos CC3. O ensaio de cruzamento documentado
  abaixo mostrou uma mudança de duração do pulso após a mudança do
  limite, mantendo a ROM original. No ensaio livre, dez inversões de
  correção acompanharam mudanças de flags da sonda. Isso é compatível
  com uma regulação estreita ao redor de λ=1, mas não identifica ainda
  um contador que imponha uma frequência fixa rica/pobre nem prova a
  finalidade catalítica. Separar o atraso do gás, a resposta da sonda
  e as guardas do firmware segue como próximo teste causal.
- Em novo contraste de 20 milhões de ticks, com o mesmo motor quente e
  `MA17_TRACE_PC=1 MA17_TRACE_LAMBDA_DIRECTION=1`, a sonda livre teve
  1.113 visitas a `1958h` depois de 7,5 milhões de ticks e oito
  inversões do bit `PSW.5` que escolhe soma/subtração. Prender ADC5
  em 4,000 V desde 2 milhões de ticks manteve 1.222 visitas à mesma
  rotina, todas na direção de subtração e **sem inversão**. Prender em
  2,500 V bloqueou a entrada nessa rotina na janela observada.
  Isso favorece realimentação e guardas em vez de um oscilador livre
  de período fixo nesse cenário. As contagens mudaram após o ajuste
  mecânico do batente e não devem ser comparadas diretamente com o
  ensaio anterior de dez inversões. Ainda não identifica qual tabela
  fixa os tempos da oscilação medida no veículo.
- No mesmo cenário livre, `ROM[7221h]=4Bh` recarrega `RAM3Dh` sob
  certas guardas e `187Fh` a decrementa. Entre 389 visitas a `187Fh`
  na janela rastreada, 275 pares consecutivos caíram exatamente uma
  unidade; a mediana entre eles foi 10.244 ticks de máquina
  (~10,35 ms a 990 kHz; uma contagem completa de 75 passos seria
  ~0,78 s se não houvesse recarga). Houve recargas para 75 ainda com
  valor anterior 44, 47, 39 e 45. Nas oito inversões em `1958h`,
  `RAM3Dh` valia 58, 42, 6, 60, 56, 56, 34 e 75: nenhuma exigiu
  que o contador tivesse chegado a zero. Portanto `7221h/3Dh` é uma
  temporização condicional demonstrada, mas não o período completo da
  oscilação rica/pobre. Reproduzir com o cenário quente de 20 milhões
  de ticks acima e `MA17_TRACE_PC=1 MA17_TRACE_LAMBDA_DIRECTION=1`.

## Incremento T7: contraste de saídas com o relé da bomba

- A ROM Fiat escreve `P5.4` em `3176h/317Ah`: `RAM2Dh.0=1` e
  `XRAM[F881h]=0` selecionam nível baixo; os demais casos, alto.
  `RAM2Dh.0` é armado em `0C25h` e pode ser rearmado em `419Ah` com
  `F881h=F5h`; o trecho não nomeia a carga externa do pino.
- O observador `p54_raw` registra apenas mudanças do latch, com PC,
  `RAM2Dh`, `F881h` e RPM da ROM. Com arranque de 0,5 s e parada
  induzida por carga aos 10 milhões de ticks, P5.4 subiu em 572.953
  (`PC=317Ah`, `RAM47h=26`) e caiu em 35.686.123
  (`PC=3176h`, `RAM47h=0`), cerca de 25 s após a RPM zerar.
  Com arranque de apenas 1 tick, o motor permaneceu parado e P5.4
  não mudou nos 30 milhões de ticks observados.
- Esse padrão não estabelece P5.4 como comando do relé da bomba no
  terminal 28 da ECU. O atraso após a parada e a ausência de transições
  no ensaio sem partida pedem confronto com a fiação e a polaridade do
  driver. Como P5.4 fica baixo sem partida, alto em marcha e baixo
  tardiamente após parar, o aviso de falha do terminal 31 da ECU é
  uma **hipótese alternativa**, sem ligação CPU→conector demonstrada.
- Com `MA17_TRACE_OUTPUT_CANDIDATES=1`, `P1.7` mudou 15 vezes em 50
  milhões de ticks. Em marcha, os pares baixo/alto ocorreram em
  3.130.042/4.358.842 e 5.997.242/7.226.042 ticks; após a carga
  extrema, alternou várias vezes entre 10.277.559 e 10.502.842.
  `RAM1Dh` era 55 ou 44 nas descidas e zero nas subidas. A ROM escreve
  esse pino em `06CAh` conforme `RAM1Dh` e `T2CON.1`; o padrão
  temporizado também não prova a ligação ao relé da bomba.
- O controle sem `--pump-relay-p34` mantém o aquecedor desligado; o
  *binding* condicional documentado acima permite testar P3.4.
- O rastro opcional não altera a saída física: duas execuções limpas
  de 2 milhões de ticks, com e sem `MA17_TRACE_OUTPUT_CANDIDATES=1`,
  tiveram `stdout` idêntico. Build aprovado e `git diff --check`
  limpo; testes direcionados de roda, circuito e sonda **6/6** e hash
  da ROM original preservado. Não se atribuiu função elétrica a
  P1.7/P5.4.
- Validação deste contraste: build aprovado, `PhysicalLambda.StallCooldown`
  1/1 em 37,39 s com as duas transições e RPM verificadas,
  `git diff --check` limpo; ROM Fiat intacta. A última suíte completa
  antes deste observador aprovou 206/206.

## Incremento T7: alimentação elétrica da sonda

- O [manual de reparos MA1.7 da Alfatest](https://pt.scribd.com/document/656677219/Alfatest-Bosch-MA-1-7)
  identifica o aquecedor como carga do terminal 87 do relé da bomba,
  protegida por fusível de 10 A. Informa 4–8 Ω para a resistência e
  terminal 28 da ECU para o comando do relé. O terminal da ECU ainda
  não foi relacionado com segurança a um pino da CPU emulada; a
  alimentação condicional por P3.4 é apenas uma hipótese testável.
- `Ma17LambdaHeater` representa a etapa elétrica separadamente, com
  6 Ω provisórios: a 12 V e relé fechado calcula 24 W; aberto, 0 W.
  `ExhaustLambda::step` aceita potência elétrica opcional e usa ganho
  estimado de 16 °C/W, resposta de 6 s e limite de 850 °C. Esses três
  parâmetros térmicos são palpites de engenharia, sem medição da peça.
  O teste isolado confirma aquecimento acima de 300 °C sem gás quente
  e resfriamento abaixo de 50 °C após desligar. O ensaio integrado de
  parada continua representando o ramo sem alimentação elétrica.
- O mesmo manual descreve a lacuna 60-2 como referência a 120° antes
  do PMS dos cilindros 1–4. Isso corrobora a ordem de grandeza da fase
  provisória, mas não identifica qual borda da lacuna corresponde ao
  dente zero do nosso gerador nem a polaridade elétrica do sensor.
- Para o batente, o manual situa o contato de lenta no terminal 8 da
  ECU e diz que ele o aterra quando fecha; o motor DC usa os terminais
  32/34. Isso confirma a topologia externa e a polaridade do contato
  no conector, mas ainda não prova que o terminal 8 corresponda a P4.6
  na CPU. O binding P4.6 permanece candidato no executor.
- Validação: `cmake --build build -j 4`, testes isolados de circuito e
  sonda 5/5, `ctest --test-dir build --output-on-failure -j 4` **206/206**
  em 139,68 s e `git diff --check` limpo. Próxima tarefa: identificar
  a saída da CPU ligada ao terminal 28 da ECU e observar seu comando
  pela ROM antes de energizar o aquecedor no executor.

## Incremento T7: resfriamento da sonda após cessar o escape

- O modelo térmico de `ExhaustLambda` mantinha indefinidamente o último
  alvo de gás quente após o motor parar. Agora, sem pacotes pendentes e
  após 495.000 ticks desde a última chegada, o alvo retorna ao ambiente
  provisório de 20 °C; a constante de resfriamento existente é 10 s.
  O limite de 0,5 s é uma escolha de engenharia, sem medição do tubo.
- O teste isolado agora aquece a sonda com pacotes repetidos de combustão,
  observa a resposta a um misfire e confirma que, 40 s após cessar o
  fluxo, ela fica inválida e a tensão volta a 0,45 V. Um pacote único
  que demora 5 s para chegar aumenta a temperatura, mas não mantém a
  sonda válida sozinho. O [catálogo NTK](https://www.ngkntk.com/fileadmin/middle_east/downloads/lambda_catalogue_2017-18.pdf)
  lista sondas de 3 fios para Tipo 1.6/159A3.048 e de 4 fios para
  835C1.000; a [nota técnica NTK](https://ngksparkplugs.com/wp-content/uploads/2020/10/NTKO2SensorQA.pdf)
  classifica ambas como aquecidas. O [manual de reparos MA1.7 da Alfatest](https://pt.scribd.com/document/656677219/Alfatest-Bosch-MA-1-7)
  descreve alimentação pelo terminal 87 do relé da bomba, via fusível de
  10 A, resistência de 4–8 Ω e comando do relé pelo terminal 28 da ECU.
  Isso sustenta a topologia elétrica da aplicação, mas ainda não liga o
  terminal 28 a um pino da CPU emulada. O ensaio de parada continua sem
  calor elétrico e sua curva é condicional a essa entrada desligada.
- Ensaio integrado com a ROM Fiat intacta: partida até 495.000 ticks,
  carga de 100 N·m a partir de 10 milhões e execução até 50 milhões,
  mantendo ADC7, P4.6, ponte H e ganho ADC5 condicionais. A RPM era
  1.664 em 9,9 milhões e zero em 10,89 milhões. A sonda ainda estava
  válida a 640,6 °C no instante da parada; em 19,8 milhões estava a
  272,3 °C, inválida, com 0,4500 V, pino ADC5 em 2,2499 V e
  `RAM65h=115`. Em 49,5 milhões, estava a 32,6 °C e `RAM65h=115`.
  O teste `PhysicalLambda.StallCooldown` repete o processo limpo,
  compara a saída inteira e confirma RPM física e `RAM47h` zeradas
  ao final: 1/1 aprovado em 37,44 s.
- A parada induzida terminou com `RAM27/F84E=00h/00h`, `F850=02h` e
  `F85E=08h`; esses bancos ficam em unidade bruta, pois a carga extrema
  e os bindings condicionais não definem uma especificação de DTC.
  O manual Alfatest descreve a falha de sonda aberta sob 0,45 V por
  mais de 40 s com motor acima de 2.000 RPM, água acima de 80 °C,
  contato aberto e borboleta acima de 15°; a parada a zero RPM não
  satisfaz esse conjunto de guardas.
  `cmake --build build -j 4` aprovou; `ExhaustLambda.*` 3/3 e
  `ctest --test-dir build --output-on-failure -j 4` **204/204**
  em 156,06 s. A ROM Fiat continua intacta. Próximo ensaio útil:
  comparar parada e nova partida, quando houver comando de arranque
  posterior e ligação do aquecedor fundamentada.

## Incremento T7: escala temporal dos pulsos rico/pobre

- `tools/analyze_sevel_lambda_pulses.py --from-tick 20000000` lê o JSONL
  do executor e resume as bordas efetivas CC3. Reproduzir passando a
  saída de `./build/emu8051-tty FiatTipo_MA17_dump_27c256.bin
  --physical-crank --starter-ticks 495000 --stop-ticks 60000000
  --adc7-mv 1232 --idle-bridge-p15-p16 --idle-contact-p46
  --coolant-c 90 --idle-min-stop-mrad 5 --throttle-leak-mm2 9
  --load-step-tick 800000 --load-nm 24 --lambda-adc-gain 5`
  pelo pipe; para o controle, acrescentar `--lambda-stuck-tick 2000000
  --lambda-stuck-mv 2960` antes do pipe.
- Entre 20 e 60 milhões de ticks, a sonda livre produziu 1.220 pulsos
  completos, larguras de 2.092 a 2.397 ticks (mediana 2.256): entre
  pulsos vizinhos, 259 larguras iguais, 478 aumentos e 482 reduções.
  Após subtrair a média local de 21 pulsos, a correlação entre resíduos
  vizinhos foi positiva, 0,7553. Com ADC5 fixo em 2,960 V, ocorreram
  1.016 pulsos, 2.064–2.177 ticks (mediana 2.156), correlação 0,4675
  e flag de classificação zero em todos os inícios tardios.
- Esses números não mostram uma alternância obrigatória de largura a
  cada pulso no modelo; são compatíveis com modulação mais lenta e com
  efeitos de RPM/carga. A diferença mediana entre larguras consecutivas
  que mudaram foi 4 ticks com sonda livre e 1 tick com ADC5 fixo;
  neste controle, 480 das 1.015 diferenças foram de exatamente 1 tick
  e apenas nove foram de pelo menos 10 ticks. Assim, a troca frequente
  de sinal nas pequenas diferenças do controle é compatível com
  quantização/temporização, sem provar alternância rica/pobre.
  Largura elétrica não equivale diretamente a
  mistura rica/pobre por combustão. A intenção de controlar o oxigênio
  armazenado no catalisador continua hipótese, sem medição do veículo.

## Incremento T7/T8: guarda da correção durante o pedal

- Relação testada: pedal de 8 mm de 10 a 12 milhões de ticks → TPS e
  contato físico → guarda `1810h` da ROM → entrada ou não em `186Dh`.
  O cenário mantém ADC7=1,232 V, ganho ADC5=5 e P4.6 ligado ao
  interruptor físico como hipóteses elétricas, sem escrever na RAM.
- Com sonda livre, ocorreram 196 passagens por `1810h` durante o pedal,
  das quais 66 não entraram em `186Dh`: primeira em 11.016.276 e
  última em 11.681.628 ticks. `RAM3Ch` foi recarregada com `0Fh` e
  decresceu até `01h`; a rota voltou antes de soltar o pedal em
  12 milhões. Portanto, neste ensaio, o bloqueio durou cerca de 0,67 s,
  não vários segundos após a soltura observados no veículo.
- Reduzindo a duração do mesmo pedal de 8 mm para 1 s (soltura no tick
  11.000.000), a contagem `RAM3Ch=0Fh→01h` apareceu **após** a soltura:
  de 11.026.493 a 11.180.119 ticks. A rota `186Dh` voltou antes de
  11,25 milhões. O teste integrado agora exige essa janela contínua;
  passagens isoladas por `1810h` mais tarde não foram tratadas como
  extensão do bloqueio. Esse ensaio demonstra memória breve da guarda,
  mas não explica os vários segundos relatados na medição do veículo.
- Com ADC5 fixo em 2,960 V desde 2 milhões de ticks, a mesma guarda
  bloqueou 66 vezes, entre 11.016.044 e 11.681.619 ticks. Isso mostra
  que a excursão da sonda não é necessária para esse bloqueio sob as
  condições ensaiadas; não identifica sozinho uma derivada de TPS.
- Sem o binding candidato P4.6, houve apenas duas passagens bloqueadas
  durante o pedal e o ensaio terminou com `RAM27/F84E=06h/06h`.
  O estado inicial e o controle da haste também mudam sem esse binding;
  o contraste não isola a ação direta do interruptor na guarda lambda.
- `PhysicalLambda.ConditionalClosedLoop` agora confere a janela e o
  contraste ADC5 fixo, e passou 1/1 em 79,10 s. Próximo confronto:
  medir no veículo a polaridade do switch, TPS e tempo entre pedal,
  sonda e retorno da correção; a simulação continua condicional.

## Incremento T7: chegada do gás e aquecimento da sonda

- O modelo de escape agora aplica a temperatura de cada pacote quando ele
  chega à posição da sonda. Antes, `admit()` mudava imediatamente o alvo
  térmico, embora λ aguardasse o transporte. Pacotes simultâneos são
  ponderados pela massa de ar, como já ocorria com λ. A distância de
  0,60 m e as temperaturas 650/120 °C continuam estimativas de engenharia.
- O ensaio de gás quente com transporte de 5 s confirmou que a sonda
  permanece a 20 °C e 0,45 V até 4 s e aquece após a chegada; após a
  correção acima, um pacote isolado não a torna válida. Os testes
  unitários de combustão e escape passaram 9/9.
- No cenário condicional com ADC5 preso em 2,960 V, os limites
  `F8EA=0Eh→0Dh` e `F8E8=09h→08h` passaram a mudar nos ticks
  7.831.457/7.831.476; a classificação mudou em 7.841.879.
  O teste físico segue a ordem limite → flag → acumulador → largura CC3
  e passou novamente. O deslocamento de cerca de 0,10 s vem da
  dinâmica simulada e não mede o atraso térmico da peça real.
- A hipótese de calibração fica delimitada: `733Dh..7342h` temporiza
  limites de classificação que podem alcançar CC3, e a rota
  `7200h`/`3Ch:3Dh` ajusta a correção em sentidos rico e pobre. Ainda
  não foi demonstrada uma tabela que imponha um período autônomo de
  alternância para o catalisador. Comparar `3Dh`, `5Ch:5Dh`, ADC5 e
  pulsos CC3 com um registro osciloscópico do veículo é o próximo teste.
  Portanto, os contadores e bytes de calibração são candidatos concretos
  para a alternância observada, mas o período e a finalidade química
  ainda são inferências, não funções comprovadas da tabela.
- Conferência direta da ROM Fiat: `733Dh..7342h = 1E 01 0A 1E 01 0F`.
  Cada grupo contém recarga `1Eh`, passo `01h` e limite inicial
  (`0Ah` ou `0Fh`). O `1Eh` é uma contagem interna; sem medir a cadência
  da rotina e suas guardas, não equivale a 30 ticks de CPU nem a um
  período fixo de mistura. SHA-256 da ROM:
  `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
- `cmake --build build -j 4` aprovou. A suíte completa inicialmente
  aprovou 202/203: a diferença entre passos de 990 e 495 ticks excedeu
  o antigo limite absoluto de 5 RPM no ensaio de 60 s. Valores medidos:
  914,207/908,362 RPM, 1820/1815 pulsos CC3 e
  0,017338409/0,017202832 kg injetados; diferenças relativas abaixo
  de 1%. O teste agora exige convergência de 1% nesses três valores e
  passou isoladamente (1/1, 72,97 s). Repetida em uma única execução,
  `ctest --test-dir build --output-on-failure -j 4` aprovou **203/203**
  em 123,38 s. `git diff --check` limpo; hash da ROM Fiat preservado.
- Contraste adicional da ROM original em 20 milhões de ticks, com
  `MA17_TRACE_PC=1 MA17_TRACE_LAMBDA_DIRECTION=1`: após 7,5 milhões,
  a sonda livre visitou `1958h` 1.095 vezes, com 293 seleções de soma,
  802 de subtração e dez inversões. Com ADC5 fixo desde 2 milhões em
  2,960 V (`RAM65h=98h`), houve 1.189 visitas, todas subtraindo, sem
  inversão; em 3,500 V (`RAM65h=B3h`), 1.223 visitas, também todas
  subtraindo. Em 2,500 V, a guarda impediu visitas a `1958h` após
  7,5 milhões, portanto esse braço não informa o sentido da correção.
  Isso reforça que as inversões do ensaio livre dependem da entrada ou
  de estados que ela afeta; não aparece um oscilador autônomo de período
  fixo nesses dois patamares. Ainda não prova finalidade de catalisador
  nem dispensa medição do sinal e da pinagem reais.

## Incremento selecionado: T2, cabo e duas pistas

- Relação: tração do cabo e posição do batente definem um ângulo comum;
  cada pista o converte em tensão própria. A ECU deve amostrar ADC0/6 e
  atualizar IRAM 60h/66h pela ROM, sem escrita externa de RAM.
- Evidência: `docs/MA17_SEMANTIC_INVENTORY.md` (agenda ADC 06E3h..0747h,
  teste da ROM original), scanner `SensorDecoders.cpp` e
  `KlineCollectionTables.h`. ADC0→60h é trilha 2; ADC6→66h é trilha 1.
  A conversão angular do scanner é ferramenta de depuração, sem medição
  elétrica independente; P4.3 e P4.6 seguem candidatos, não contato provado.
- Hipótese de ensaio: offset elétrico e inclinação por pista serão
  parâmetros provisórios, ancorados no par bruto válido 40/95 em ângulo
  mínimo. Esse par não prova ângulo nem tensão real. O contato físico
  será calculado por encontro alavanca/batente, ainda sem binding GPIO.
- Distinguir sucesso/erro: geometria respeita limites, pistas são
  contínuas e têm sensibilidades distintas, ADC segura amostra até a
  conversão seguinte, ROM modifica 60h/66h e seus derivados sem DTC TPS
  inesperado no cenário nominal; injeção de pista incoerente deve ser
  observada separadamente, sem forçar código de falha.
- Implementado: `ThrottleAssembly` mantém tração do cabo, batente, ângulo
  e contato separados. `Ma17TpsCircuit` gera duas tensões do mesmo ângulo;
  ADC0/6 as amostra dinamicamente em 10 bits, conservando o latch de
  conversão existente. Faixas úteis provisórias: pista 1 até 24°, pista 2
  com mudança de inclinação em 18°; coeficientes são hipóteses de ensaio,
  não calibração da peça. Referência constante de 5 V também provisória.
- Reproduzir: `env -i PATH=/usr/bin:/bin ./build/emu8051-tty
  FiatTipo_MA17_dump_27c256.bin --physical-crank --starter-ticks 495000
  --stop-ticks 2000000 --pedal-step-tick 800000 --pedal-mm 8`.
  O cabo moveu o ângulo de 0,069813 para 0,280000 rad e abriu o contato
  físico. A ROM escreveu 60h=82 no tick 803539 e 66h=157 no tick 805588,
  contra 40/95 sem pedal. 6Fh/70h passaram de 82/27 a 144/48.
- No cenário nominal, RAM 28h e XRAM F885h/F84Fh ficaram zero ao fim de
  2 milhões de ticks. Os valores brutos não comprovam ângulo real, pinagem
  da placa ou ausência de todos os diagnósticos.
- Falha elétrica controlada: `--tps1-high-tick 800000` leva ADC6 a 5 V e
  66h a 255 no tick 805589. `--tps1-restore-tick 1200000` devolve 66h a
  95 no tick 1204959, sem escrever RAM. Nenhum código TPS persistiu nos
  bytes observados até 2 milhões de ticks; condições/latência de DTC
  permanecem abertas. O GPIO do contato não foi ligado: P4.3/P4.6 ainda
  não têm identificação elétrica suficiente.
- Validação: `ctest --test-dir build --output-on-failure` 173/173; cenário
  nominal com tracing ligado/desligado produziu os mesmos estados físicos,
  RAM e contadores de roda. O modo físico ainda usa entradas fixas nos
  outros canais ADC até T3/T5/T7.

## Incremento selecionado: T3, térmicos e alimentação

- Relação: ar local, parede, líquido e elementos sensores terão temperaturas
  distintas; a resistência NTC e os divisores converterão essas temperaturas
  em tensão para ADC2 (ar) e ADC3 (água). Bateria será uma condição de
  contorno com divisor provisório para ADC1.
- Fontes: `SensorDecoders.cpp` usa ajuste Steinhart–Hart e pull-ups 2661 Ω
  (ar) / 3004 Ω (água), ambos sem validação elétrica da placa; agenda ADC
  original em `docs/MA17_SEMANTIC_INVENTORY.md` confirma 1→61h, 2→62h,
  3→A8h→63h. A ROM deve publicar 61h/62h/63h sem escrita externa.
- Ensaios: monotonicidade e limites do divisor, nós térmicos com respostas
  diferentes, condições iniciais fria/quente e comparação temporal entre
  sensor físico, ADC e RAM elaborada. Não inferir temperatura da RAM pela
  mesma fórmula usada para gerar a entrada.
- Implementado `ThermalState` com nós de ar local, parede e líquido,
  sensores de ar/água com constantes de tempo diferentes e trocas de calor
  conservativas entre nós. Sem combustão nem fluxo de ar em T3, calor externo
  permanece zero; isso será conectado em T5/T6. `Ma17SensorCircuit` inverte
  o ajuste NTC provisório do scanner, aplica os pull-ups e modela a bateria
  de 12,5 V com divisor estimado 0,26 para ADC1. Tensão de referência 5 V.
- Comando quente: `env -i PATH=/usr/bin:/bin ./build/emu8051-tty
  FiatTipo_MA17_dump_27c256.bin --physical-crank --starter-ticks 495000
  --stop-ticks 2000000 --coolant-c 90`. Frio: omitir `--coolant-c` (20 °C).
  Em 2 milhões de ticks, frio publicou 61h/62h/63h=`166/124/117`;
  quente `166/101/19`. No quente, ar local chegou a 30,911 °C e sensor
  IAT a 29,589 °C, distinto da parede a 89,743 °C e ECT a 89,992 °C.
- Falha controlada: `--ect-open-tick 800000 --ect-restore-tick 1200000`
  (com `--coolant-c 90`) levou ADC3 a 5 V e amostra superior A8h a 255
  no tick 990000, enquanto 63h elaborado era 17. Em 1980000, A8h e 63h
  voltaram a 19, sem escrita externa. Não atribuir DTC sem verificar suas
  guardas e latência na ROM.
- Testes unitários verificam conservação de energia dos nós sem troca
  externa e monotonicidade do NTC; teste de integração compara frio/quente,
  amostras temporais e falha/recuperação. Isso valida o acoplamento sob
  parâmetros assumidos, não a curva ou resistência real da placa.
- `ctest --test-dir build --output-on-failure`: 176/176 aprovados.
  O ensaio quente com tracing ligado manteve o mesmo estado físico e RAM.
  ROM Fiat SHA-256 ainda é
  `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.

## Próxima tarefa recomendada

- T4/T8: confrontar P4.6, TPS, `F835/F839` e comando/posição do batente
  com a peça real. A contagem até `F839=2Eh` já foi rastreada; falta
  validar qual condição elétrica deveria reiniciá-la antes de publicar
  `0402h/1A01h` durante um pedal sustentado. A faixa de pedal que arma
  essa contagem não é monotônica no ensaio condicional.
- T5: rastrear o nó elétrico que chega ao ADC7 na placa Fiat. A ROM
  confirma um limiar digital `RAM67h=65`, que suprime CC3; sem a origem
  do sinal, `--adc7-mv` permanece condição explícita de ensaio.
  Se o chip da placa seguir o mapa SAB80C517A, o alvo de medição é
  P7.7: pino 13 em PLCC-84 ou 80 em MQFP-100. Conferir primeiro a
  marcação e o encapsulamento do componente instalado.
- T8/T4: medir ou documentar a ligação real do interruptor no atuador
  e sua polaridade elétrica. O contraste digital com/sem P4.6 já
  mostrou que o grupo `1A01h` depende desse estado no modelo.
- T7: testar se algum cruzamento natural entre `RAM65h` e os limites
  `F8E8/F8EA` muda a correção antes de variar RPM e carga; os cinco
  passos observados no cenário nominal ocorreram longe do cruzamento
  elétrico de 2,960 V, embora o acumulador estivesse ativo.
- T7: confrontar o contador `3Dh` e a amplitude de `5Ch:5Dh` com o
  período de comutação da sonda medido no veículo; o ensaio livre já
  ligou dez inversões de correção às flags, sem medir a placa real.
- T4: medir o curso mínimo e a polaridade do conjunto de lenta, além dos
  terminais da ponte H e do interruptor na placa Fiat. O ensaio quente
  passa de `F84E=0` para `F84E=8` entre 5 e 10 mrad de limite; conferir
  se essa transição corresponde ao conjunto físico antes de calibrar.
- T6: medir polaridade dos drivers, pares de bobina e fase entre lacuna,
  dente zero e PMS na placa Fiat; a relação digital P5/`RAM69h` foi
  repetida em marcha sem carga, degrau de carga e pedal.
- T7: separar oxigênio residual de combustível não queimado na resposta
  aproximada da sonda.

## Incremento selecionado: T4, batente DC condicional

- Na ROM Fiat original, o serviço TF0 em `06FDh..070Fh` usa `RAM24h.7`
  para comandar `P1.5/P1.6` em sentidos opostos e usa `RAM1Fh` para a
  duração; em seguida limpa ambos os bits. Sem ligação física, o rastro
  com ADC7 condicional mostrou `1/0` de tick 621.258 a 1.143.494 e,
  após degrau do pedal, `0/1` de 1.460.938 a 2.425.543. Esses padrões
  sustentam a hipótese de ponte H, sem identificar seus transistores.
- `IdleActuator` integra velocidade e curso da haste com limite mecânico;
  o redutor sem-fim retém posição sem tensão. `Ma17IdleBridge` traduz
  provisoriamente `1/0` em avanço, `0/1` em recuo, `0/0` em frenagem e
  `1/1` em saída livre. Parâmetros estimados: 12,5 V, 8 mm/s no máximo,
  haste 0–12 mm, conversão de 10 rad/m para o batente. A posição não é
  oferecida à ECU como sensor adicional.
- `--idle-bridge-p15-p16` ativa apenas a ligação candidata entre latch
  P1.5/P1.6 e motor. Em 0,99 s, haste 5,641 mm, batente 0,096411 rad,
  ROM publicou TPS 45/103 contra 40/95 sem o motor. Com pedal de 8 mm,
  o recuo levou a haste a zero, mas o ângulo permaneceu em 0,28 rad e
  TPS 82/157: o cabo não foi vencido pelo batente.
- `--idle-contact-p46` liga condicionalmente o contato mecânico à leitura
  de P4.6 (baixo quando fechado). O inventário já mostra que P4.6 altera
  `RAM24h.4/2Fh.0` e rotas de diagnóstico; não há pinagem medida.
  Conforme a descrição do conjunto físico fornecida pelo usuário, o
  switch fica no próprio atuador: a borboleta o pressiona ao encostar no
  batente móvel. O modelo calcula esse contato pela folga entre cabo e
  batente, com histerese provisória de 0,1°/0,2°. Assim, mudar o batente
  pode mudar TPS e contato; puxar o cabo abre o contato mesmo com o
  atuador comandado. A associação elétrica desse switch a P4.6 segue
  hipótese, embora os ensaios indiquem efeito funcional na ROM.
  Com as duas opções, a ROM passou a alternar pulsos curtos em ambos os
  sentidos, o batente terminou em 0,110487 rad e `RAM27/F84E=0` em
  4 milhões de ticks. Com pedal mantido aberto, haste 11,324 mm,
  contato aberto e `F84E=0Ah` no mesmo instante. Ao soltar o pedal em
  2 milhões de ticks, contato fechou novamente e `F84E` voltou a zero
  sem limpar RAM nem XRAM externamente.
- A polaridade alternativa `--idle-contact-p46-high-closed` é ensaiável
  separadamente; com contato fechado durante os 4 s, ela reproduziu
  exatamente o comportamento sem binding de contato (`F84E=06h`,
  batente 0,076267 rad). O contraste funcional favorece a hipótese
  baixo-fechado **dentro deste modelo**, sem provar a fiação externa.
- Reproduzir acrescentando `--idle-bridge-p15-p16 --idle-contact-p46`
  ao ensaio condicional de T6. Para reencontro, acrescentar
  `--pedal-step-tick 800000 --pedal-mm 8 --pedal-release-tick 2000000`.
  A marcha lenta condicional ficou alta (~1.700 RPM sem pedal); curso,
  força, polaridade e entrada de contato precisam de medição independente.
- Teste isolado cobre avanço, recuo, limite, frenagem e cabo afastado;
  integração usa a ROM original, compara motor desligado/ligado e
  contato aberto/fechado/recuperado. `ctest --test-dir build
  --output-on-failure`: 186/186; round-trip da ROM Fiat sem diferença,
  SHA-256 original preservado; `git diff --check` limpo.
- Com contato candidato, duas execuções repetidas deram eventos e estado
  iguais. Reduzir o passo de fluidos 990→495 ticks mudou RPM final em
  0,434 e ângulo do batente em 0,000009 rad; `F84E` permaneceu zero.
  Com/sem `MA17_TRACE_PC=1` em 2 milhões de ticks, todos os resumos
  físicos, RAM e diagnósticos foram idênticos.
- Partida quente (`--coolant-c 90`) revelou limite da hipótese: a ROM
  manteve P1.5/P1.6 em `0/1` a partir do tick 180.938, recolheu a haste
  até 0 mm e publicou `F84E.3=1` (`1A01h` candidato) em 1.284.007.
  `RAM27.3` foi armado em `PC=2C0Ch` no tick 1.125.960 depois de
  `F83Bh` chegar a zero; nas passagens anteriores, `2C19h` limpava
  o bit. Na partida fria, o contador era recarregado e o bit final
  permaneceu zero. Permitir que TPS0/6 extrapolem abaixo do ponto de
  4° passou a mostrar a retração (`RAM60/66=34/86`), mas não eliminou
  o diagnóstico no limite anterior de 40 mrad. O parâmetro físico
  `--idle-min-stop-mrad` permite varrer o limite de 0 a 60 mrad,
  preservando o ângulo inicial. Em 4 milhões de ticks a 90 °C, 5 mrad
  deu ~816 RPM e `F84E=0`; 10 mrad deu ~823 RPM e `F84E=8`. Ambos
  terminaram com a haste em 0 mm. O resultado delimita uma sensibilidade
  do modelo, não calibra o batente real. Curso, ganho, polaridade,
  posição do contato e critério de diagnóstico da ROM exigem medição;
  a partida quente segue condicional, sem validação física.

## Incremento selecionado: T5, admissão e combustível

- Relação: ângulo físico altera fluxo pela borboleta; ar entra no volume do
  coletor e os cilindros o consomem em função de RPM e eficiência volumétrica.
  Pressão absoluta fica só na física. Pulsos efetivos de `cc3_output_pin`
  alimentam um único injetor candidato, com pressão diferencial, tempo morto
  e película de combustível conservativa.
- Evidências: `emu8051/core.c` distingue `cc3_output_pin` do shadow P1.3;
  `docs/MA17_SEMANTIC_INVENTORY.md` observa programação CC3 e resposta a
  TPS/RPM, mas não confirma terminal físico, polaridade nem driver. Vazão
  900 cm³/min a 3 bar e operação perto de 1 bar são provisórias do objetivo.
- Resultado esperado: a ROM continua publicando RPM e TPS; mudanças reais
  de CC3 produzem massa injetada distinta de zero e filme residual após
  desligar o comando. Sem CC3 ativo, não entra nova massa de combustível.
- Verificação: balanços independentes de ar e combustível, degrau de pedal,
  captura de bordas no tick correto, cenário de injetor desconectado e
  comparação com tracing ligado/desligado. As calibrações de fluxo e a
  associação elétrica permanecerão condicionais até medição externa.
- Implementado `IntakeFuel` com volume de 2 L, deslocamento de 1580 cm³,
  eficiência volumétrica 0,75, pressão absoluta interna, passagem pela
  borboleta e refluxo quando a pressão excede a atmosférica. Película de
  combustível retém 25% e evapora com constante dependente da parede;
  o balanço conserva massa. Áreas e eficiência são estimativas.
- `Ma17InjectorStage` amostra `cc3_output_pin` após cada tick da CPU.
  Binding **candidato** ativo em nível baixo; fluxo nominal provisório de
  900 cm³/min a 3 bar, densidade 740 kg/m³, rail absoluto 2 bar e descarga
  a 1 bar (diferencial 1 bar), tempo morto 0,8 ms a 12,5 V. A peça,
  polaridade, rail e pré-resistor não estão confirmados na placa.
- Sem `--adc7-mv`, o canal 7 interno padrão fica em 105; a ROM publica
  67h=105, mantém 2Bh.5 ligado, não produz bordas CC3 nem massa injetada.
  O sensor físico do ADC7 permanece desconhecido. Para um **ensaio
  condicional**, usar `--adc7-mv 1232` (63 contagens): 67h=63, 2Bh.5
  limpo, 27 pulsos CC3 e 177708 ticks de condução em 2 s virtuais.
  O coletor terminou em 22747,9 Pa absolutos; 1,011935 g entraram pelo
  injetor candidato, 0,719841 g chegaram aos cilindros, 0,133310 g ficaram
  na película e 0,158785 g no vapor. Esses números fecham o balanço, mas
  não validam o circuito físico nem sustentam combustão ainda.
- Limiar atual da ROM: `3B22h` carrega `RAM67h`, compara com `41h`
  e escreve `2Bh.5`; 64 deixa a guarda limpa e 65 a liga. No motor
  físico com carga de 24 Nm, 1,252 V deu `RAM67h=64`, 103 pulsos CC3,
  0,001076973 kg injetados e ~798 RPM após 4 milhões de ticks.
  Com 1,260 V, `RAM67h=65`, CC3 e massa injetada ficaram zero e o
  motor parou. O teste `PhysicalIntake.ConditionalCc3Fuel` cobre
  64/65 em 2 milhões de ticks. A antiga anotação de bloqueio com
  ADC7=64 era de uma captura anterior à correção do byte ADC.
- O [manual ECU-TEST, p. 13](https://mofler.com/uploads/attachments/monthly_2014_12/Manual_de-pinagem_ecu_test_2_evolution_nacional.pdf.3521774495bcf2303df240e9ebf3cd7c)
  lista no conector Fiat Tipo MA1.7 o injetor em 35, bobinas em 1/19,
  TPS em 11/12, sonda em 10, ar em 13 e água em 14. Isso reforça as
  funções externas desses terminais, mas não liga ADC7 a um deles nem
  identifica trilhas do microcontrolador na placa. O ADC7 continua
  desconhecido, e o valor 1,232 V é hipótese de operação do ensaio.
- O [datasheet Siemens/Infineon SAB80C517A](https://www.infineon.com/assets/row/public/documents/10/57/infineon-d80517a-ds-en.pdf)
  identifica P7.7 como entrada analógica 7 (pino 13 em PLCC-84,
  80 em MQFP-100). A ROM seleciona o canal 7 por `ADCON0` e publica
  o resultado em `RAM67h`; isso dá um ponto de partida concreto para
  seguir a trilha na placa. O encapsulamento e a conexão externa da
  placa Fiat não foram verificados neste checkout.
- Conferência do tipo de periférico: a ROM original contém
  `75 DC 00` em `3B91h` (`MOV DCh,#00h`) e, no serviço ADC em
  `0716h`, lê `DAh` antes de combinar seus bits com `D9h`.
  O [datasheet C517A](https://www.infineon.com/assets/row/public/documents/10/57/infineon-d80517a-ds-en.pdf)
  define `DCh=ADCON1`, `D9h=ADDATH`, `DAh=ADDATL`; o
  [datasheet C535](https://www.infineon.com/assets/row/public/documents/10/57/infineon-d80515-ds-v02-96-en.pdf)
  define `DCh` como reservado e `DAh=DAPR`, com ADC de 8 bits.
  Também há `XPAGE=91h` e `SYSCON=B1h` usados pela ROM, conforme
  `ROUNDTRIP_8051.md`. Assim, o perfil digital C517A é sustentado
  pelos opcodes; isso não prova a marcação exata do microcontrolador
  automotivo nem qual circuito alimenta ADC7. As fotos recebidas
  mostram justamente o B 58 371 de 68 pinos; portanto, a numeração
  13/80 do C517A não identifica um terminal a sondar nesta placa.
- Validação após o contraste ADC7 e o teste de fase da ignição:
  `ctest --test-dir build --output-on-failure` **200/200**;
  `git diff --check` limpo e SHA-256 da ROM Fiat preservado.
- Reproduzir: `env -i PATH=/usr/bin:/bin ./build/emu8051-tty
  FiatTipo_MA17_dump_27c256.bin --physical-crank --starter-ticks 495000
  --stop-ticks 2000000 --adc7-mv 1232`. Com
  `--pedal-step-tick 800000 --pedal-mm 8`, a pressão subiu a 89599,7 Pa
  e a massa injetada a 1,338372 g. O pedal ainda não altera o torque.
- Negativo: `--injector-disconnect-tick 800000` manteve comandos CC3,
  parou a entrada de combustível em 0,570047 g e conservou entrega residual
  do filme/vapor (0,343407→0,478711 g entre 0,99 e 1,98 s).
  `--injector-reconnect-tick 1400000` retomou a entrada até 0,752854 g.
  Nenhuma RAM ou memória de falha foi limpa para essa recuperação.
- Determinismo: duas execuções idênticas produziram mesmo resumo; tracing
  ligado/desligado deu as mesmas 53 bordas e massas. Passo de fluidos de
  990→495 ticks mudou a pressão final em 1,0 Pa e combustível entregue em
  0,000173 g, sem mudar pulsos CC3. `ctest --test-dir build
  --output-on-failure`: 181/181; round-trip Fiat 32768 bytes, zero
  diferenças, SHA-256 igual à ROM original.

## Incremento selecionado: T6, ignição e trabalho

- A ROM alterna pulsos baixos P5.0/P5.1. No ensaio físico, as subidas
  observadas ocorreram perto de `1,96 + nπ` rad da roda; a subida foi
  tomada como centelha candidata após pulso baixo. A fiação, polaridade
  e referência real do PMS permanecem sem medição.
- `Combustion` separa ar e combustível de `IntakeFuel` em quatro reservas
  segundo o ângulo da admissão. A ordem provisória é 1–3–4–2, com
  P5.0 nos cilindros 1/4 e P5.1 em 3/2; a compressão alterna a cada
  meia volta e o par oposto recebe centelha perdida. A atribuição das
  bobinas é configurável por `--swap-ignition-coils`. O modelo limita
  a carga queimada de cada evento a 0,6 g de ar e à razão
  estequiométrica 14,7, e converte combustível queimado em trabalho com
  energia de 44 MJ/kg e eficiência indicada provisória de 24%.
  O torque age por 2 rad após a borda; o virabrequim o integra no tick
  seguinte. Sem ar, combustível ou borda válida, não nasce pulso de torque.
- `Ma17IgnitionStage` separa carga de bobina candidata (P5 baixo) da
  interrupção de corrente (subida). Requer pelo menos 0,3 ms de carga e
  atinge força normalizada em 2,0 ms; polaridade e tempos são parâmetros
  provisórios, sem corrente primária ou tensão real modeladas.
- Com `--adc7-mv 1232`, arranque até 495.000 e parada em 4.000.000 ticks,
  ocorreram 146 queimas até 3.960.000 ticks, divididas em
  37/36/37/36 por cilindro, e RPM final de 1.265,7.
  Sem esse estímulo condicional, CC3 não pulsou, não houve queima e o
  motor caiu a 14,2 RPM no mesmo instante. Desconectar o injetor em
  800.000 ticks reduziu a RPM final; o filme residual ainda permitiu
  queimas, portanto esse cenário não equivale a corte instantâneo da chama.
- A massa queimada em 3,96 s foi 0,424 g contra 2,046 g entregues aos
  cilindros em 4 s: parte da diferença sai como combustível não queimado
  nos eventos que chegam ao escape; outra parte ainda espera combustão
  nas reservas individuais. Pressão de 7,75 kPa e rotação de
  ~1.266 RPM com borboleta fechada indicam que vazão/eficiência e fase
  precisam de calibração; não são previsão validada de marcha lenta.
- Testes unitários cobrem falta de carga, fase incorreta e tempo de carga
  antes da borda da bobina. Integração compara
  sustentação, ausência de combustível e corte do injetor com a ROM
  original. Repetição deu resumos físicos idênticos; reduzir o passo de
  fluidos de 990 a 495 ticks mudou RPM final em 0,071 e manteve 146
  eventos de queima. Testes de componente verificam a ordem 1–3–4–2,
  o par correto em compressão e a hipótese com canais trocados.
- Falha elétrica de ensaio: `--coil-channel 0 --coil-disconnect-tick 800000`
  deixa P5.0/P5.1 pulsando pela ROM, mas suprime a centelha no estágio
  candidato. Cada interrupção sem centelha consome a carga daquele evento
  como falha de queima; não a transfere para a outra bobina. Aos 3,96 s,
  queimas/falhas passaram de 146/0 para 68/57, e a RPM final de 1.265,7
  para 945,9. Cilindros 1/4 caíram de 37/36 para 3/3 queimas, enquanto
  2/3 tiveram 31/31. Com `--coil-reconnect-tick 2200000`, ocorreram
  106/27 queimas/falhas, 1/4 voltaram a 20/20 e a RPM final foi
  1.173,5. Inverter o binding dos dois canais desde o início produziu
  zero queimas e 14,2 RPM, ainda com combustível injetado. Os bytes
  de diagnóstico observados permaneceram iguais;
  não foi atribuído DTC de bobina sem rota correspondente demonstrada.
- A ROM usa matrizes em `7B46h/7BBEh/7C36h` e outras curvas para produzir
  `RAM69h`, que participa das recargas do Timer 1 e das bordas P5. O scanner
  interpreta `RAM69h` por `60 - 0,35 × bruto` graus; essa fórmula é
  hipótese do scanner, não uma calibração angular provada. Em 131 subidas
  P5 após 800.000 ticks, somar esse avanço ao ângulo da borda relativo ao
  dente zero deu 117,18–117,56°, mediana 117,18°. A informação não
  confirmada de sensor a 120° fica a ~2,8°, perto de meio passo da roda
  60-2. Montagem do sensor e fase entre lacuna, dente zero e PMS ainda
  precisam de medição. Não foi identificada tabela explícita de fixação.
- `--tdc-reference-deg` permite comparar a hipótese no modelo sem alterar
  a ROM. 120° e o valor anterior de 1,96 rad produziram 146
  eventos e 1.265,9/1.265,7 RPM neste ensaio, pois ambos estão na janela de
  queima simplificada; 60° produziu zero queimas e 14,2 RPM. Essa
  comparação verifica coerência de fase, mas não distingue 112° de 120°
  nem prova o posicionamento físico.
- Novo contraste de fase com a ROM original: as subidas P5 candidatas à
  centelha foram associadas, pelo mesmo tick, ao `RAM69h` do latch e ao
  ângulo físico relativo ao dente zero. Em 497 bordas após 800 mil ticks,
  nos cenários sem carga, carga 24 Nm e pedal 8 mm, o ajuste conjunto foi
  `fase módulo 180° ≈ 56,501° + 0,35443° × RAM69h`, resíduo RMS
  0,374°. Separadamente, as inclinações foram 0,3589°/0,3490°/0,3563°
  por unidade. A escala de 0,35° do scanner é numericamente próxima,
  mas a sua origem angular `60°` não está provada. Somar
  `60° - 0,35° × RAM69h` à fase medida deu medianas perto de 117°,
  a ~3° da hipótese de montagem a 120°. `PhysicalIgnition.P5PhaseVsRam69`
  protege a relação bruta sem exigir a hipótese de 120°; o teste passou.
  Com/sem `MA17_TRACE_PC=1`, 929 linhas físicas do caso com carga foram
  idênticas. Fase real da lacuna, polaridade elétrica e ordem dos pares
  ainda precisam de medição; não foi encontrada tabela explícita que
  codifique a fixação física do sensor.
- A janela tardia de 8 a 20 milhões de ticks com carga de 24 Nm
  acrescentou 409 subidas P5: ajuste `56,571° + 0,35385° × RAM69h`,
  resíduo RMS 0,254°. Somar a fórmula candidata do scanner
  `60° - 0,35° × RAM69h` deu mediana 117,18° desde o dente zero.
  `PhysicalIgnition.P5PhaseVsRam69` agora verifica também essa janela.
  A persistência do ajuste reforça a leitura digital do avanço, mas
  não mede a posição real do sensor nem fixa o PMS em 120°.
  A regressão completa após ampliar esse teste passou **217/217** em
  229,36 s; `git diff --check` ficou limpo e a ROM permaneceu intacta.
- A física agora atenua o torque continuamente conforme o erro entre a
  fase da centelha e um ótimo **provisório** de 0,20 rad antes do PMS:
  fator `exp(-0,5 × ((fase+0,20)/0,60)²)`. A massa de combustível
  queimada segue independente desse fator; apenas o trabalho útil muda.
  `Combustion.SparkTimingChangesUsefulWorkWithSameCharge` compara duas
  centelhas com carga idêntica. O parâmetro padrão de PMS passou de
  1,96 rad (~112,3°) para 120°, explicitamente como hipótese de ensaio
  sugerida pelo usuário, ainda sem confirmação do sensor na placa.
  `--tdc-reference-deg` continua permitindo confrontar outras fases.
- Com a nova curva e o mesmo cenário condicional de 60 s, 112,3°
  produziu uma amostra transitória `RAM27=08h` no tick 13.860.000,
  sem publicação em `F84E`; RPM final 917,222 e 1.819 pulsos CC3.
  A 120°, os oito bytes de diagnóstico amostrados ficaram zero,
  RPM final 907,365 e 1.818 pulsos. Reduzir o passo de fluidos para
  495 ticks a 120° deu 911,674 RPM, 1.815 pulsos e massa injetada
  0,017207169 kg contra 0,017301537 kg; ambos mantiveram queima nos
  quatro cilindros. Essa comparação mostra sensibilidade física à
  fase, não comprova que a montagem real seja de 120°.
- A suíte física completa encontrou duas expectativas antigas de
  trajetória: em `PhysicalIdle.CandidateP15P16`, o batente de 10 mrad
  agora tem `F84E=00h` e `RAM27=04h` apenas no primeiro registro,
  mascarado antes da publicação; no de 5 mrad também não publica falha.
  `PhysicalLambda.ActiveCorrectionToCc3` passou a conferir a última
  publicação de `14h:15h` antes de `058Eh`, pois a ROM pode atualizá-la
  de novo depois da primeira divergência entre os braços. Após esses
  ajustes, os dois testes específicos passaram. Build e regressão
  completa: `ctest --test-dir build --output-on-failure`, **202/202**
  aprovados em 420,01 s. A referência de 120° continua hipótese física;
  o teste não a valida contra o motor ou a placa reais.
- O corte de bobina também mostrou oxigênio residual sem empobrecer a
  carga: em 3,96 s, `physical` (λ ar/combustível) era 0,148, mas
  `oxygen_equivalent` era 2,571; a sonda aquecida apresentou 0,1000 V
  e a ROM publicou `RAM65h=5`. No controle, ambos eram 0,154, com
  0,9000 V e `RAM65h=46`. Depois da reconexão, os dois λ voltaram a
  ~0,149 e `RAM65h=46`. O escape usa mistura por massa dos pacotes que
  chegam no mesmo passo e resposta temporal de 80 ms, aproximações de
  engenharia ainda sem geometria ou sonda reais calibradas.
- Regressão após separar as quatro cargas: build aprovado,
  `ctest --test-dir build --output-on-failure` 194/194, incluindo
  partida, corte/reconexão de bobina, passo físico reduzido, pedal,
  atuador e lambda com a ROM Fiat original.

## Incremento selecionado: T7, escape e sonda

- A agenda ADC da ROM liga canal 5 a IRAM 65h; o scanner o interpreta
  como tensão de sonda por escala assumida de 3,9 mV/contagem. Esse
  caminho digital está confirmado; a pinagem externa permanece candidata.
- `ExhaustLambda` recebe ar, combustível e massa queimada por evento de
  ignição. Usa 0,60 m até a sonda, área de tubo provisória de 0,00049 m²,
  densidade ideal e vazão dos cilindros para atrasar a composição; a
  fila preserva ordem. Falha de combustão deixa oxigênio residual alto.
  A sonda aquece com constante de 2 s, só fica válida acima de 300 °C,
  e então responde em 0,1 s com curva narrowband de 0,1–0,9 V.
  Enquanto fria, a entrada elétrica fica em polarização provisória de
  0,45 V. Os parâmetros não são medição da peça.
- Na ROM Fiat com ADC7 condicional, a amostra em 0,99 s tinha λ físico
  0,185, sonda a 167 °C e 0,45 V, RAM65=23. Em 1,98 s tinha λ=0,151,
  357 °C, 0,8875 V e RAM65=46; em 3,96 s 0,90 V e RAM65=46.
  Sem combustível, λ reportado como teto 5, sonda permaneceu fria
  (103 °C) e RAM65=23 em 3,96 s. A mistura excessivamente rica desse
  ensaio inicial ainda não representava o cenário nominal posterior,
  com fuga de 9 mm² e carga de 24 N·m.
- Estudo anterior da ROM G identificou em `1644h..1687h` os limiares
  do classificador ADC5/65h e, em `17C2h..1810h`, guardas que incluem
  temperatura, TPS/carga e estado da sonda. Entradas em `186Dh` e a
  mudança de `F8:0Ch` acompanham a correção, mas esse byte armazenado
  não teve leitura de realimentação observada fora do autoteste da XRAM.
  Referência: `MA17_FIRMWARE_VARIANTS_ANALYSIS.md`, seção da rota lambda.
- Ensaio físico quente, ROM original, ADC7 condicional, contato de lenta
  candidato ligado a P4.6 e batente mínimo de 5 mrad: entre 3 e 10 s,
  ADC5/65h ficou em `2Eh` (46), sonda em 0,9000 V e λ de carga caiu
  de 0,115 a ~0,102. A rota `186Dh` executou 195 vezes entre 8 e 10 s,
  enquanto `F8:0Ch` subiu de `BAh` a `CBh`. Nesse ensaio inicial ainda
  não houve oscilação rica/pobre; o cenário nominal posterior a apresenta.
- Com pedal de 8 mm entre 3,0 e 4,5 s, a sonda marcou ~0,1 V em 5–6 s
  e voltou a ~0,9 V em 9–10 s. A rota `186Dh` teve 0 entradas entre
  4,5–6 s, 87 entre 6–8 s e 195 entre 8–10 s; o controle sem pedal
  teve 148, 195 e 195 nas mesmas janelas. Isso reproduz suspensão e
  retomada digital após o transitório, sem demonstrar que a duração,
  o motivo da mistura pobre ou a estratégia de malha fechada sejam reais.
- Para separar a geometria assumida da resposta do firmware, a área de
  passagem no fechamento pode ser variada apenas no modo físico com
  `--throttle-leak-mm2 N` (0–100; padrão anterior: 1 mm²). É área
  efetiva adicional à parcela angular, não medição do corpo de borboleta.
  Com o mesmo cenário quente acima até 4 milhões de ticks, 1/3/6 mm²
  deram pressão de 5,21/9,44/13,33 kPa, RPM 819/1336/1849 e λ de
  0,112/0,347/0,771. Com 8 mm², a sonda ficou pobre (λ≈5) e os
  pulsos CC3 contados caíram de 180 (6 mm²) para 134.
  Reproduzir: `env -i PATH=/usr/bin:/bin ./build/emu8051-tty
  FiatTipo_MA17_dump_27c256.bin --physical-crank --starter-ticks 495000
  --stop-ticks 4000000 --adc7-mv 1232 --idle-bridge-p15-p16
  --idle-contact-p46 --coolant-c 90 --idle-min-stop-mrad 5
  --throttle-leak-mm2 6`. Com 6/7/8 mm², `RAM26h.7` ligou pela primeira
  vez nos ticks 4.719.755/3.531.901/3.060.929, sempre ao passar
  `RAM47h=4Dh`; `1F9Bh→1FB4h→2052h` propagou `26h.5` até `26h.7`.
  O `JB 26h.7` em `0591h` suprime o agendamento CC3. Portanto a grande
  excursão pobre desse cenário inclui corte de pulsos ligado à rotação,
  e não prova uma temporização lambda intencional.
- A escala provisória do scanner (3,9 mV por contagem de `65h`) sugere
  que o caminho elétrico da sonda possa ter ganho: o modelo direto
  entregava 0,9 V ao ADC5 e a ROM via apenas `65h=46`, embora sua
  classificação digital use limiares próximos de `6Eh..9Ah`. Foi
  acrescentado `--lambda-adc-gain 1..8` no circuito da ECU; 1 preserva
  o padrão anterior e 5 é apenas um candidato de comparação, sem
  medição da placa. `--lambda-stuck-mv 0..5000` prende o pino ADC5
  para ensaio de falha, sem mudar a composição do escape.
- No ensaio quente com área 9 mm², carga 6 N·m desde 800.000 ticks e
  ganho 5, a sonda livre deu em 6 s `λ=1,028`, `65h=100`, massa injetada
  acumulada 0,0015154 kg. Com o pino ADC5 preso em 4,0 V, deu
  `λ=1,230`, `65h=205`, 0,0013647 kg. Entre 4–6 milhões de ticks,
  `F8:0Ch` foi de 177 a 208 no primeiro braço e de 74 a 60 no segundo;
  `186Dh` executou 196 contra 130 vezes. O contraste isola um efeito
  total do sinal elétrico sobre a injeção e a mistura nesse modelo/ROM.
  Aos 6 milhões de ticks, `RAM27/F84E=0/0` com sonda livre e `8/8`
  com pino preso; o bit 3 é associado ao atuador de lenta no inventário,
  e não constitui prova de um DTC específico da sonda.
  Reproduzir com o comando anterior, trocando a área para 9, o fim para
  6 milhões, e acrescentando `--load-step-tick 800000 --load-nm 6
  --lambda-adc-gain 5`; repetir com `--lambda-stuck-mv 4000`.
  Ainda não se identificou tabela que imponha período rico/pobre ou se
  comprovou que a oscilação real tenha a mesma causa. Próximo passo:
  seguir o estado interno até o agendamento CC3 e medir o circuito ADC5.
- A falha elétrica agora aceita `--lambda-stuck-tick` e
  `--lambda-restore-tick`, preservando a mesma partida até o estímulo.
  No cenário anterior, prender ADC5 em 4 V de 3,0 a 4,5 milhões de
  ticks manteve todos os pulsos CC3 anteriores a 3,0 milhões iguais ao
  controle. `65h` divergiu em 3.008.322 (`33h` livre, `CDh` preso);
  `2Fh` passou de `2Bh` a `29h` na guarda `1810h`. Em `1EA9h`, o
  candidato de pulso `R3:R2` foi `017Dh/0176h`; `1ED3h` o copia para
  `14h:15h`. A primeira entrada CC3 divergente em `058Eh`, tick
  3.011.441, mostrou exatamente `017Dh/0176h`, ainda com `26h=00h`
  nos dois braços. A borda de início foi comum no tick 3.011.469;
  a borda final veio em 3.012.982/3.012.954: 1.513/1.485 ticks.
  O código em `1C8Eh` lê `5Ch:5Dh` no caminho até esse cálculo e foi
  executado no trace; `F8:0Ch` continua tratado como observador.
- Aos 6 milhões de ticks, as massas injetadas acumuladas foram
  0,0015154 kg (livre), 0,0013683 kg (falha mantida) e 0,0014156 kg
  (falha retirada em 4,5 milhões); λ físico foi 1,028/1,375/1,113.
  `RAM27/F84E` permaneceu `0/0` nos três braços. `F847h=C0h/C4h/C0h`
  é apenas estado bruto ainda sem semântica de DTC confirmada.
  A regressão compara o histórico anterior à falha, o primeiro pulso
  e a recuperação sem escrever RAM nem alterar a ROM.
- No mesmo cenário até 6,5 milhões de ticks, o trace `MA17_TRACE_MOVC=1`
  leu `7221h` 515/449 vezes e `733Dh..7342h` 115/104 vezes com sonda
  livre/ADC5 preso em 4 V. `733Dh..7342h` são limites e recargas do
  classificador ADC5, não evidência isolada de um relógio de oscilação.
  Duas execuções de 6 milhões de ticks foram idênticas; tracing de PC
  e lambda preservou todas as amostras físicas. Reduzir o passo de
  fluidos de 990 para 495 ticks mudou a RPM final 1795,629→1794,940,
  λ 1,028→1,031 e combustível acumulado 0,001515385→0,001515120 kg.
- Validação deste incremento: build aprovado, testes de circuito e
  integração da sonda livre/pino preso aprovados, `ctest --test-dir build
  --output-on-failure` 190/190, `git diff --check` limpo e ROM Fiat com
  SHA-256 `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
- A janela provisória da centelha foi ampliada para ±0,60 rad após o
  degrau de pedal revelar avanço da ROM próximo de 0,36 rad e queimas
  artificialmente perdidas na janela anterior de ±0,35. Com pedal de
  8 mm desde 800.000 ticks, a ROM levou o motor a 3.501,6 RPM aos
  4 milhões de ticks, sem eventos perdidos; λ físico chegou a 0,663,
  distinto de 0,152 com borboleta no batente. Esse contraste valida a
  propagação do degrau no modelo, não a curva real de avanço.

## Ensaio condicional de regulação lambda por 20 s

- Cenário reproduzível: ROM Fiat original, `--physical-crank
  --starter-ticks 495000 --stop-ticks 20000000 --adc7-mv 1232
  --idle-bridge-p15-p16 --idle-contact-p46 --coolant-c 90
  --idle-min-stop-mrad 5 --throttle-leak-mm2 9 --load-step-tick 800000
  --load-nm 24 --lambda-adc-gain 5`. O ADC7, ganho do canal ADC5,
  vazamento, carga e condições térmicas são hipóteses de engenharia para
  isolar um estado plausível, não medições da placa ou do veículo.
- Após retirar o motor de partida em 495.000 ticks, o motor continua a
  873,7 rpm no tick 20.000.000. RAM47=34 (~850 rpm), 599 pulsos CC3 no
  total e 168 inícios de pulso nos últimos 5 milhões de ticks. O
  atuador fica a 5,848 mm de curso e `RAM27/F84E=0/0`; estes bytes
  não provam ausência de toda falha possível.
- Entre 9,9 e 19,8 milhões de ticks, λ físico ficou entre 0,933 e
  1,034 e a tensão da sonda entre aproximadamente 0,400 e 0,768 V.
  A amostragem de 0,99 s mostra cruzamentos de λ=1 e continuidade de
  pulsos injetores. Essa oscilação depende do modelo de mistura e do
  ganho ADC5 assumido; não é ainda prova de uma tabela de período
  rico/pobre programada na ROM.
- Com ganho ADC5=1 e os demais parâmetros iguais, λ final foi 0,680
  e a massa injetada acumulada subiu de 0,005743 para 0,007988 kg.
  Assim, nesta hipótese elétrica, a informação da sonda modifica o
  combustível comandado pela ROM ao longo de 20 s.
- Prender eletricamente ADC5 em 4,000 V entre 10 e 14 milhões de ticks
  preservou as primeiras dez amostras do controle. Durante a falha,
  λ chegou a 1,132, contra aproximadamente 0,996 no controle no mesmo
  instante; após soltar o pino, terminou em 1,004 contra 0,977. A
  massa injetada caiu para 0,005667 kg. O teste `PhysicalLambda.
  ConditionalClosedLoop` verifica estes contrastes sem modificar
  diretamente RAM, ROM, combustível ou estado físico da sonda.
- Toque de pedal separado, mantendo as hipóteses do cenário: puxar o
  cabo 8 mm em 10 milhões de ticks e soltar em 12 milhões abriu e
  fechou o contato de lenta. Em 10–12 milhões, `1810h` foi alcançado
  196 vezes, mas `186Dh` somente 130; `RAM3Ch` ficou não nula nas
  passagens bloqueadas. Em 12–14 milhões, as contagens voltaram a
  195/196. O λ físico chegou a 1,463 na amostra de 11,88 milhões e
  terminou em 0,927 após 20 milhões; `RAM27/F84E=0/0` ao final.
  `PhysicalLambda.ConditionalClosedLoop` verifica o bloqueio parcial
  e a recuperação da rota com a ROM intacta. Um toque menor de 4 mm
  também alterou a mistura, mas manteve `186Dh=196/196` durante
  10–12 milhões: excursão de λ não prova, sozinha, saída da rota de
  correção. O tempo de retorno observado no veículo ainda não está
  reproduzido nem atribuído a uma constante específica da ROM.
- Ao reduzir `--fluid-step-ticks` de 990 para 495 no toque de 8 mm,
  o pico de λ mudou de 1,463 para 1,476, a RPM final de 867,160
  para 872,960 e a massa injetada acumulada de 0,006157850 para
  0,006153811 kg; `F84Eh` terminou zero nos dois. O traço sustenta
  estabilidade aproximada do ensaio, sem calibrar a resposta real.
- Há uma tabela real de contagens em `733Dh..7342h`: dois bytes `1Eh`
  recarregam contadores internos, dois bytes `01h` definem decrementos
  e `0Ah/0Fh` inicializam limites associados à classificação de
  `RAM65` (detalhes e rastro em `MA17_FIRMWARE_VARIANTS_ANALYSIS.md`,
  seção `Sinal ADC5`). Isso sustenta temporização de limites da leitura
  da sonda, mas ainda não demonstra uma tabela que determine o período
  rico/pobre observado. A função temporal de `7221h` também segue
  inconclusiva para esse período.
- A busca por uma alternância rica/pobre encontrou também uma estrutura
  candidata em `ROM[7200h]`. Em `186Dh`, `ROM[7221h]=4Bh` pode ser
  carregado em `RAM3Dh`; `187Fh` a decrementa. `RAM3Ch` é recarregada
  em `1825h`, `18F9h` ou `1902h` e decrementada em `182Dh/1952h`.
  A rotina em `1889h..1958h` escolhe dois caminhos: `1958h` testa
  `PSW.5` e segue pela soma de `R5:R4` a `R7:R6` ou por `1971h/1983h`,
  que subtrai esse passo. `199Ah` grava o
  resultado em `5Ch:5Dh`, depois consumido no cálculo de injeção em
  `1C8Eh`. Os bytes `721Ah/721Bh` limitam os dois sentidos em
  `1958h..1994h`. Isso comprova uma correção digital bidirecional com
  contadores e calibrações na ROM, sob suas guardas. Não identifica
  `3Ch/3Dh` como contagem de ticks de parede, não demonstra alternância
  autônoma em frequência fixa nem estabelece uma estratégia específica
  de armazenamento de oxigênio no catalisador. A relação com a sonda
  é sustentada por `RAM65h→flags→5Ch:5Dh→14h:15h→CC3` nos ensaios
  condicionais; o ensaio abaixo verifica as inversões em execução livre.
- O novo rastro optativo `MA17_TRACE_PC=1
  MA17_TRACE_LAMBDA_DIRECTION=1` fez essa comparação na ROM Fiat
  original, em 20 milhões de ticks do cenário quente condicional.
  Nas 1.012 visitas a `1958h` após 7,5 milhões de ticks, `PSW.5`
  selecionou 296 somas e 716 subtrações; houve dez inversões de
  sentido. Cada inversão ocorreu 78–145 ticks depois da mudança mais
  recente das flags de classificação da sonda. `3Dh` variou de 0 a
  `4Bh`; `3Ch` ficou zero nas visitas registradas. Há 40 mudanças de
  flags no ensaio, logo nem toda mudança da sonda inverte a correção.
  A associação temporal favorece resposta ao classificador em vez de
  um oscilador autônomo de período fixo, mas ainda não calibra o tempo
  físico nem separa atraso de transporte da sonda e lógica da ECU.
  A saída física/JSON foi idêntica com o rastro ligado e desligado
  (SHA-256 `f752f435dac29d6dd60f181858abb8ba043bd77c3249188996486cba040e018b`).
- A observação física `lambda_class_raw` registra alterações de
  `RAM2Fh.1`/`RAM2Ch.3` com PC, `RAM65h` e limites `F8E8h/F8EAh`.
  No ensaio com ADC5 preso em 2,600 V desde 2 milhões de ticks,
  `RAM65h=133` ficou constante. A tabela reduziu `F8E8h` de 10 para 9
  em 4.657.084 e de 9 para 8 em 7.729.256; em 7.739.214,
  `1671h/1673h` trocou as flags de `02h` para `08h`, ainda com
  `RAM65h=133`. Com ADC5 em 2,500 V (`RAM65h=128`), essa troca não
  ocorreu até 12 milhões de ticks. O teste `PhysicalLambda.
  TableThresholdAtFixedAdc` conserva esse contraste. Portanto a
  tabela efetivamente temporiza uma fronteira de classificação da
  sonda; ainda falta demonstrar que ela temporize os pulsos rico/pobre
  observados no veículo ou a saída CC3.
- As bordas `cc3_pin` agora registram `RAM14h:15h`, flags lambda e
  `RAM65h` junto da largura efetiva. Entre os ensaios ADC5=2,500 e
  2,600 V, todos os pulsos desde 2 milhões de ticks até a troca da
  flag foram idênticos. Nos 21 primeiros pulsos após 7.739.215,
  `RAM14h:15h` também coincidiu, apesar das flags `02h/08h`; após
  10 milhões houve diferenças em 5 de 57 intervalos comparados.
  A mudança de limite não produz um degrau imediato de largura nesse
  cenário; a influência tardia ainda precisa ser separada da evolução
  física de RPM e mistura.
- O rastro opcional `MA17_TRACE_PC=1 MA17_TRACE_LAMBDA_PROPAGATION=1`
  observa `1687h`, `186Dh`, `199Ah/199Ch`, `1C8Eh`, `1ED5h/1ED7h` e
  `058Eh` sem alterar a RAM. No par 2,500/2,600 V, as flags já eram
  diferentes em `1687h` no tick 7.739.217, mas `5Ch:5Dh=0000h`
  nas mais de 440 passagens por `1C8Eh` em cada braço até 12 milhões
  de ticks. Com ADC5=4,000 V, o mesmo acumulador foi não nulo em
  todas as passagens observadas. Assim, a troca de flag próxima ao
  limiar não demonstra correção ativa pelo acumulador nesse estado.
  A primeira diferença observada de `RAM47h` no par ocorreu por volta
  de 10,647 milhões; `RAM14h:15h` divergiu por volta de 10,658 milhões.
  A ordem temporal é compatível com influência da rotação no intervalo,
  sem excluir efeitos anteriores de agenda ou atuadores.
- Com ADC5 preso em 2,600 V e 12 milhões de ticks, as 2.834 linhas
  observáveis do ensaio físico foram idênticas com o novo rastro ligado
  e desligado. Depois da instrumentação: build aprovado, 196/196
  testes CTest passaram, `git diff --check` limpo e hash da ROM intacto.
- No cenário quente de 16 milhões de ticks, a sonda livre e ADC5
  preso em 4,000 V entre 10 e 14 milhões começaram com amostras lambda
  e bordas CC3 idênticas. A primeira diferença de `5Ch:5Dh` no rastro
  `199Ch` veio em ~11,856 milhões de ticks, com `RAM47h` e
  `RAM14h:15h` ainda iguais. O novo valor chegou a `1C8Eh`, depois
  `1ED7h` publicou `026Ch` livre contra `0262h` preso. `058Eh` leu
  esses valores; a borda CC3 seguinte iniciou em 11.859.384/
  11.859.399 e durou 2.468/2.429 ticks. A diferença de 39 ticks
  excede a variação de 1 tick vista antes em algumas bordas. A ROM
  publicou RPM diferente apenas depois dessa cadeia observada.
  `PhysicalLambda.ActiveCorrectionToCc3` verifica a ordem e os
  valores efetivos, sem impor o resultado na RAM.
- Esse ensaio demonstra propagação de uma alteração elétrica ADC5 ao
  intervalo CC3 com o acumulador ativo. Não demonstra que a tabela
  `733Dh..7342h` fixa diretamente o período da oscilação rica/pobre;
  suas recargas continuam identificadas como temporização dos limites
  de classificação. Os ganhos e bindings físicos seguem condicionais.
- Validação deste ciclo: build aprovado, `ctest --test-dir build
  --output-on-failure` 197/197, `git diff --check` limpo e SHA-256 da
  ROM Fiat original preservado.
- Validação após esse ensaio: build aprovado, `ctest --test-dir build
  --output-on-failure` 196/196, `git diff --check` limpo e SHA-256 da
  ROM Fiat original preservado.
- Rastro somente observacional do mesmo ensaio com
  `MA17_TRACE_PC=1 MA17_TRACE_LAMBDA_BOUNDS=1`: `F8E9/F8EB` mudaram
  171 vezes cada após 3 milhões de ticks, com intervalo mediano de
  aproximadamente 102.400 ticks (0,103 s). `F8E8` caiu de `0Ah` para
  `05h`, e `F8EA` de `0Fh` para `0Ah`, em cinco pares de eventos entre
  4,657 e 16,945 milhões de ticks, separados por cerca de 3,072
  milhões de ticks. A falha ADC5 de 10 a 14 milhões mudou a trajetória
  de λ, mas preservou as cinco transições e seus valores; os instantes
  variaram no máximo algumas centenas de ticks. Portanto, estes
  contadores da ROM andam regularmente no cenário, mas a evidência
  atual não os identifica como relógio direto da alternância rica/pobre.
  A próxima investigação é seguir a guarda que usa esses limites e
  confrontar sua saída com `14h:15h` e cada pulso CC3.
- A instrumentação (`MA17_TRACE_PC` e `MA17_TRACE_LAMBDA_BOUNDS`) não
  alterou nenhuma amostra lambda, borda CC3 ou resumo físico do ensaio
  de 20 milhões de ticks. Reduzir `--fluid-step-ticks` de 990 para 495
  manteve 599 pulsos CC3 e `RAM27/F84E=0/0`; a RPM final mudou de
  873,658 para 871,206, λ de 0,977 para 0,973 e combustível injetado
  acumulado de 0,005742820 para 0,005744555 kg. A pequena diferença
  numérica é compatível com convergência do modelo neste cenário.
- A telemetria `idle_state_raw` observa `F847h` sem modificar a ECU.
  No mesmo ensaio de 20 s, `RAM27h` teve 336 mudanças observadas,
  incluindo 166 entradas transitórias em `08h`, mas `F84Eh` permaneceu
  zero em todos esses eventos. `F847h` começou em `80h` após `0C85h`,
  alternou entre valores como `80h/C0h/C4h/C6h` e terminou em `C0h`.
  Em cada escrita observada por `2D56h`, o bit 6 de `F847h` espelhou
  `RAM24h.7`; os bits 0/1 espelharam `RAM27h.1/.3`, como mostram os
  opcodes originais. Portanto `C0h` final, cujos bits baixos estão
  limpos, não deve ser rotulado como DTC ativo. Os bits internos que
  surgem transitoriamente ainda exigem a guarda de publicação e o
  caminho do pacote para uma classificação diagnóstica completa.
- O rastro opcional `MA17_TRACE_PC=1 MA17_TRACE_IDLE_PUBLISH=1` expõe
  `RAM27h`, a cópia `F884h`, `R7` e a saída `F84Eh` nos PCs `407Dh`,
  `41CDh` e `41E5h`. No ensaio nominal de 20 s, ocorreram 195
  publicações em `41E5h`, todas `R7=F84E=00h`: as entradas breves de
  `RAM27h.3` não produziram `R7` ativo nessa publicação. Em dois ensaios de 4 s
  com as mesmas condições quentes e contato ligado, 5 mrad deu 39
  publicações nulas; 10 mrad deu 14 publicações com `R7=F84E=08h`
  entre 39. Em todas as 78 publicações, os bytes coincidiram. O
  teste `PhysicalIdle.CandidateP15P16` protege esse contraste. Isto
  identifica uma falha publicada no cenário de 10 mrad, mas o estado
  K-Line presente/memorizado e a pinagem elétrica ainda carecem de
  confirmação própria.
- Validação: build aprovado, 191/191 testes CTest aprovados,
  `git diff --check` limpo e SHA-256 da ROM Fiat original preservado:
  `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.

## Incremento selecionado: T8, bancos brutos de diagnóstico

- No cenário quente condicional de 16 milhões de ticks, o controle teve
  `F84E/F84F/F850/F85E/F85F/F860=0` em todas as amostras de 1 s.
  Os mesmos bytes foram observados após estímulos elétricos entre 10 e
  14 milhões de ticks, sem escrita direta na RAM/ROM.
- Para o circuito aberto ECT, o ensaio físico publicou `F84Fh.3=1` e,
  após restauração, `F85Fh.3=1`. O teste dos opcodes da ROM original
  agora inicia a primeira varredura em `4414h` com `R3=0Ch` e o bit
  `F84Fh.3`: a própria ROM escolhe `R7=09h` e produz a tripla
  `02 0A 1E`. Na segunda varredura, iniciada em `4470h` com somente
  `F85Fh.3`, ela chega a `R3=23h`, `R6=0Ch`, `R7=09h` e produz
  `02 0A 9E`. Ambas têm código numérico `0A02h` em little-endian,
  descrito como temperatura do líquido pelo scanner. O scanner trata
  `1Eh` como presente e `9Eh` como não ativo; a ECU foi agora observada
  transmitindo ambas as triplas pela K-Line no cenário físico.
- Pista TPS1 presa em 5 V: `F84E.3=1` durante o estímulo e
  `F85E.3=1`, `F84E.3=0` após a restauração. `RAM28/F84F` não mudaram.
  Com somente esses bits ligados, a primeira varredura da ROM percorreu
  `R3=01h..04h`, manteve `R7=0` e produziu `01 1A 1B`; a segunda
  percorreu `R3=18h..1Bh`, `R6=04h`, e produziu `01 1A 9B`.
  O código numérico `1A01h` é descrito como atuador de lenta no
  scanner, não como TPS (`0602h`). A relação causal com a pista TPS1
  pode passar pelo controle do batente; a pinagem e o significado exato
  dos status `1Bh/9Bh` continuam abertos.
- ECT em circuito aberto: `RAM28.3=1` primeiro em `4656h`, quando a
  amostra bruta A8h excede o limiar `E8h`; `4200h` publicou
  `F84F.3=1`. Após restaurar, `4678h` limpou `RAM28.3`, `4200h`
  limpou `F84F.3`, e `F85F.3=1` apareceu no segundo banco.
  A tripla base de `4Fh.3` com `R7=0` é `0602h`; a execução do seletor
  da ROM descrita acima é necessária para chegar ao `0A02h` neste
  estado. A consulta K-Line confirmou `1Eh` com ECT aberto e `9Eh`
  após restauração. A interpretação presente/histórico vem do scanner;
  a política de apagamento da memória da ECU não foi ensaiada.
- ADC5 preso em 4 V no mesmo intervalo alterou λ físico em mais de
  0,1 contra o controle, mas os seis bytes de diagnóstico permaneceram
  zero. O ensaio de 4 s não estabelece se há diagnóstico de sonda,
  quais são suas condições, nem um relógio de alternância rica/pobre.
- `PhysicalDiagnostics.RawFaultBanks` verifica controle, transições,
  restauração e PCs originais para ECT. Ganho ADC5, carga, ADC7 e
  conexões elétricas seguem hipóteses explícitas do cenário.
- A extensão de `FirmwareFaultTripletReadersUseOriginalRom` cobre as
  triplas ECT e do grupo de lenta em ambos os bancos, com `R7`
  selecionado pela ROM nas varreduras de bits únicos. Build aprovado;
  `ctest --test-dir build --output-on-failure` 197/197, `git diff --check`
  limpo e SHA-256 da ROM Fiat preservado nessa etapa.
- Sessão K-Line física: `--physical-pty-realtime` mantém o relógio
  virtual acoplado ao tempo real quando o cliente PTY envia a inicialização
  de 5 baud; sem a opção, os ensaios headless continuam sem espera.
  `test_pty.py --faults-once` usa o handshake e o parser existentes e
  consulta somente o serviço `07h`. O modo `--diagnostics-once` compara
  leituras sequenciais com um snapshot `F4h` e reprovou essa comparação
  durante o motor vivo, embora recebesse corretamente o frame de falha.
- Reproduzir com `ctest --test-dir build -R
  PhysicalDiagnostics.KlineFaultHistory --output-on-failure`. O teste
  inicia emulador e cliente na mesma execução para compartilhar o PTY.
  ECT aberto em 2 milhões de ticks: `RAM28=F84F=08h` em 2,97 milhões;
  handshake e `07h` retornaram `FC:02 0A 1E`. Restaurado em 8 milhões:
  `RAM28=F84F=0`, `F85F=08h` em 8,91 milhões; consulta após 9,9
  milhões retornou `FC:02 0A 9E`. Ambos os clientes saíram com código
  zero, e o teste isolado passou em 20,38 s. ADC7, ganho da sonda,
  batente e ligação do ECT continuam hipóteses elétricas do ensaio.
- O mesmo cliente K-Line recebeu `FC:01 1A 1B` com TPS1 preso em
  5 V desde 10 milhões de ticks e `F84E.3=1` em 10,89 milhões.
  Em outro ensaio, TPS1 foi restaurado em 8 milhões de ticks:
  `F84E=0`, `F85E.3=1` em 8,91 milhões e a consulta após 9,9
  milhões retornou `FC:01 1A 9B`. Os quatro cenários ECT/TPS1
  presente/histórico integram `PhysicalDiagnostics.KlineFaultHistory`
  e passaram em 48,63 s. O código transmitido é evidência da seleção
  feita pela ROM, sem provar que o circuito físico do TPS1 está ligado
  ao DTC de atuador descrito pelo scanner.
- Controle do interruptor candidato: com `--idle-contact-p46`, os
  cenários nominais mantiveram `F84E=0`; TPS1 preso em 5 V a partir
  de 10 milhões de ticks deu `RAM27=F84E=08h` em 10,89 milhões.
  Sem esse binding, P4.6 ficou no estado padrão do emulador e o
  nominal já tinha `RAM27=F84E=06h`; o mesmo estímulo TPS1 não
  acrescentou o bit 3 até 16 milhões de ticks, mesmo após restaurar.
  `PhysicalDiagnostics.RawFaultBanks` protege os quatro braços.
  Na ROM, `2BABh..2C1Bh` testa `24h.4` antes do ramo que liga
  `27h.3`; o contato candidato é lido em `2D57h/2D60h` e chega a
  `24h.4/2Fh.0`. Isso confirma a dependência digital no perfil ensaiado,
  sem identificar a origem elétrica de P4.6 nem a peça do código `1A01h`.
- Após ampliar K-Line e o rastro da sonda, o build e a suíte completa
  passaram (`ctest --test-dir build --output-on-failure`: 199/199).
  Após acrescentar o controle com/sem P4.6, o teste específico
  `PhysicalDiagnostics.RawFaultBanks` passou em 36,00 s; a suíte
  completa não foi repetida após essa última alteração apenas no teste.
- Validação após a sessão física: `cmake -S . -B build -DENABLE_TESTS=ON`,
  `cmake --build build -j 4`, `ctest --test-dir build --output-on-failure`
  **198/198**; `git diff --check` limpo. A ROM Fiat preserva SHA-256
  `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.

## Incremento selecionado: T7, limite temporal até o pulso CC3

- Relação e critério: os seis bytes originais em `733Dh..7342h`
  recarregam `F8E9/F8EB` e diminuem `F8E8/F8EA`; procurar uma entrada
  ADC5 constante que cruze um desses limites enquanto `5Ch:5Dh` está
  ativo. Comparar classificação, acumulador, `14h:15h` e pulso efetivo
  com outro valor ADC5 que ainda não cruzou. As associações ADC7,
  ganho ADC5 e batente seguem condições elétricas de ensaio.
- Com o circuito da sonda fixado em 2,960 V desde 2 milhões de ticks,
  a ROM estabilizou `RAM65h=152`. `F8EA` caiu `0Eh→0Dh` no tick
  7.729.063 e `F8E8` caiu `09h→08h` no tick 7.729.082.
  Em 7.739.209, `PC=167Fh` mudou a flag de classificação de `08h`
  para `00h`, ainda com `RAM65h=152`. Na passagem por `1C8Eh` em
  7.739.642, `5Ch:5Dh` já era `FFF4h`, contra `0000h` antes.
- No braço de controle de 2,940 V, `RAM65h=151` e a mesma flag só
  mudou em 10.811.200 ticks. Todos os pulsos CC3 após fixar a entrada
  e antes da transição de 2,960 V coincidiram entre os dois braços.
  O primeiro pulso divergente começou em 7.748.700: `14h:15h` foi
  598/597 e a duração efetiva 2380/2376 ticks no controle/ensaio.
  O contraste alcança o injetor da cossimulação pela execução da ROM,
  sem escrita externa em RAM, tabelas ou saídas.
- `PhysicalLambda.TableCrossingToCc3` verifica a ordem e a identidade
  dos pulsos anteriores à transição. O rastro ligado/desligado deu
  1.892 eventos observáveis idênticos em 8,5 milhões de ticks. Reduzir
  `--fluid-step-ticks` de 990 para 495 antecipou o cruzamento em 10
  ticks; ambos os passos tiveram 21 inícios CC3 no intervalo posterior
  observado, embora a fase e o primeiro `14h:15h` mudassem.
  Isso demonstra influência do limite temporal sobre a correção e o
  pulso neste ponto fixo; não demonstra que a tabela determine sozinha
  o período rica/pobre com a sonda livre e o motor em transiente.
- Com a sonda livre no mesmo cenário de 20 milhões de ticks, ADC5
  variou de aproximadamente 1,945 a 3,929 V nas amostras tardias.
  Houve 34 transições observadas das flags de classificação após
  3 milhões de ticks, enquanto os limites `F8EA/F8E8` deram cinco
  passos entre 4,657 e 16,945 milhões. A alternância de flags é mais
  frequente que a recarga da tabela: ela acompanha também a evolução
  da leitura física. Ainda falta isolar se cada recarga muda a fase
  ou a amplitude da oscilação natural sob entrada variável.
- O rastro opcional de `F8E8/F8E9/F8EA/F8EB` agora inclui `RAM65h`,
  flags, `5Ch:5Dh` e `14h:15h` no tick da escrita. Com sonda livre,
  os cinco passos de `F8EA/F8E8` ocorreram com `RAM65h=DAh/C2h/C6h/
  8Eh/97h`, respectivamente; `5Ch:5Dh` estava não nulo nos cinco.
  Os três primeiros valores de sonda estão longe de `98h`, onde o
  ensaio fixo cruzou o limite temporal. Não apareceu uma troca da flag
  nesses ticks; a próxima transição observada após o quinto passo
  ocorreu 61.393 ticks depois, com `RAM65h=94h`. Isso não estabelece
  causalidade daquele passo sobre a alternância natural.
- O teste `PhysicalLambda.TableCrossingToCc3` agora também executa
  20 milhões de ticks com a sonda livre e exige múltiplas transições
  de classificação entre as cinco reduções de `F8EA`. Após ampliar
  o rastro, `PhysicalLambda.TableThresholdAtFixedAdc` e esse teste
  passaram; com/sem rastro, as 1.800 linhas de saída física de um
  cenário livre de 8 milhões de ticks foram idênticas.
- Validação deste incremento: `cmake -S . -B build -DENABLE_TESTS=ON`,
  `cmake --build build -j 4` e `ctest --test-dir build --output-on-failure`
  **199/199**; teste específico `PhysicalLambda.TableCrossingToCc3`
  aprovado. A comparação com/sem rastro foi idêntica; o cenário com
  passo físico menor preservou o cruzamento dos limites.
- Validação histórica anterior: build aprovado, `ctest --test-dir build
  --output-on-failure` 195/195, `git diff --check` limpo e SHA-256 da ROM
  Fiat preservado (`a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`).

## Incremento selecionado: T8, degrau de carga

- O cenário físico aceita `--load-step-tick 2000000 --load-nm 10`.
  O torque resistente entra na mesma equação do virabrequim após o tick
  escolhido, sem manipular RAM ou a agenda do firmware.
- Com ADC7 condicional e arranque até 495.000 ticks, a RPM foi igual ao
  controle antes do degrau (1.218,6 em 1.980.000); aos 4 milhões caiu
  para 609,0 contra 1.243,4 sem carga. A ROM publicou RAM47=24 contra
  49 no controle. O valor de 10 N·m é estímulo de ensaio, não carga
  medida do veículo.
- A integração testa o contraste antes/depois. Ainda faltam diagnóstico
  por subsistema, contato/ponte H de lenta e medições elétricas que
  sustentem um cenário nominal completo da placa Fiat.
- Observador bruto em 4 milhões de ticks: `RAM27=0Eh`, `F84E=0Eh`,
  `F847=C7h`, `F83D=07h`, `F83C=0Bh`, `F885=F84F=0` nos cenários
  sem combustível, condicional e com carga. O inventário associa bits
  de `F84E` a rotas `0402h`/`1A01h` do atuador de lenta, cuja ligação
  física ainda não está modelada; não atribuir esses bits a falhas
  novas de ignição, lambda ou carga sem seguir suas guardas na ROM.
- Vinte e cinco por cento da energia do combustível queimado chega ao nó
  de líquido como hipótese térmica. No ensaio condicional de 4 s, ele
  subiu de 20,000 a 20,086 °C; sem combustível permaneceu em 20,000 °C.
  O efeito ainda é pequeno demais para separar pela RAM63 quantizada.
- Regressão final deste ciclo: build aprovado, `ctest --test-dir build
  --output-on-failure` 184/184, `git diff --check` limpo e round-trip
  da ROM Fiat com 32768 bytes, zero diferenças e SHA-256 original igual.
- Teste unitário distingue transporte, aquecimento e resposta a misfire;
  integração confronta λ físico, tensão e RAM65. Ainda faltam geometria
  do escapamento, resposta da ECU em malha lambda e classificação de DTC.
  `ctest --test-dir build --output-on-failure`: 184/184 aprovados;
  `git diff --check` sem problemas.

## Incremento selecionado: T8, funcionamento sustentado por 60 s

- Critério: executar a ROM Fiat original após retirar o arranque, com
  combustão nos quatro cilindros, balanços de massa fechados, sensores e
  bancos de falha observados durante 60 milhões de ticks. Repetir o
  processo limpo e reduzir o passo de fluidos de 990 para 495 ticks.
- Reproduzir com `ctest --test-dir build -R
  PhysicalEngine.SustainedSixtySeconds --output-on-failure`. O cenário usa
  `--starter-ticks 495000 --stop-ticks 60000000 --adc7-mv 1232
  --idle-bridge-p15-p16 --idle-contact-p46 --coolant-c 90
  --idle-min-stop-mrad 5 --throttle-leak-mm2 9
  --load-step-tick 800000 --load-nm 24 --lambda-adc-gain 5`.
- Resultado: 60 amostras de combustão, lambda, térmicos e diagnósticos;
  1.797 queimas sem falhas até a última amostra, distribuídas 450/449/
  449/449 entre cilindros. Ao fim, RPM física 916,231, 1.817 pulsos
  CC3 e 1.818 lacunas da roda; o líquido chegou a 93,052 °C. Os oito
  bytes de diagnóstico acompanhados permaneceram zero nas 60 amostras.
  A lambda tardia permaneceu válida e passou pelos lados rico e pobre
  de 1; isso não identifica sozinho uma estratégia de catalisador.
- O processo repetido produziu as mesmas 12.471 linhas. Com passo de
  fluidos reduzido, RPM final 914,146 (diferença 2,085), 1.820 pulsos
  CC3 (diferença 3), massa injetada 0,017251084 kg contra 0,017198734 kg
  (diferença 0,3%) e nenhuma falha de combustão. O teste confere os
  balanços de ar e combustível e limites explícitos dessas diferenças.
- Evidência sobre a hipótese rica/pobre: a tabela `733Dh..7342h` já
  demonstrou deslocar o limiar de classificação e a duração CC3 sob
  ADC5 fixo. A alternância natural em 60 s é compatível com correção em
  malha, mas ainda não prova uma tabela que conte ticks para manter uma
  oscilação rica/pobre específica do catalisador. É preciso separar o
  atraso da sonda, os limiares temporais e a atuação do injetor.
- Contraste adicional no mesmo cenário de 60 s, com rastro observacional
  dos limites: entre 20 e 60 milhões de ticks, a sonda livre produziu
  29 cruzamentos de λ=1 nas 40 amostras de 1 s, λ médio 0,99635 e
  123 trocas das flags de classificação. Fixar apenas ADC5 em 2,960 V
  após 2 milhões de ticks levou a λ médio 1,37365, nenhum cruzamento
  e nenhuma troca dessas flags na mesma janela. Os dois braços tiveram
  15 decrementos de `F8EA` na execução inteira. Houve 1.217 contra
  1.015 inícios CC3 tardios, com `RAM14h:15h` médio 563,40 contra
  541,11; RPM e mistura também evoluíram, portanto essa diferença de
  comando não deve ser atribuída somente à tabela. A amostragem de 1 s
  não resolve a frequência exata da oscilação física.
- Validação: configuração e build aprovados; teste específico 1/1 em
  67,78 s após conferir também os diagnósticos no passo reduzido;
  última suíte completa antes deste registro 200/200.
  `git diff --check` limpo; SHA-256 da ROM Fiat preservado.
  ADC7, P4.6, ganho ADC5, ponte H, fase e geometria do batente seguem
  hipóteses de ligação/calibração, não medições da placa.

## Incremento selecionado: T8, diagnóstico durante toque de pedal

- Critério: aplicar pedal de 8 mm por 2 s após 10 milhões de ticks sob
  a carga condicional de 24 N·m e observar contato, TPS, λ, RPM, saída
  CC3 e bancos de falha antes, durante e depois. Comparar com um toque
  de 1 s sob a mesma configuração; não apagar a memória da ROM.
- Antes do pedal, os 10 primeiros segundos dos dois braços coincidem.
  No braço de 2 s, o cabo abre o contato e leva a borboleta a 0,280 rad;
  a RPM chega a 1.461 no período, λ posterior varia de 0,836 a 1,551,
  e o contato volta a fechar na soltura. A marcha retorna à faixa
  aproximada de 865–922 RPM entre 20 e 30 s.
- A comparação revelou uma limitação do binding candidato: no tick
  10.997.613, `PC=2B42h` liga `RAM27.1`; três ticks depois `2B49h`
  liga `.3`, ambos com `F839=2Eh`. `41E5h` publicou `F84E=0Ah`
  em 11.115.014. Após soltar o pedal em 12 milhões de ticks,
  `F84E` zerou em 12.034.484, mas `F85E=0Ah` persistiu até 30 s.
  Com o toque de 1 s, `RAM27=0Ah` ainda foi armado nos mesmos ticks,
  mas zerou em 11.017.905 após o contato fechar, antes de `F84E`
  publicar a falha; `F84E/F85E` ficaram zero. A publicação, portanto,
  depende da duração do estado e da agenda de diagnóstico.
  Os bits 1/3 apontam às triplas `0402h/1A01h` da ROM. Em duas sessões
  PTY/K-Line, a consulta `07h` recebeu `FC:02 04 1E` e `FC:01 1A 1B`
  com o pedal ainda aberto e `F84E=0Ah`; após a soltura recebeu
  `FC:02 04 9E` e `FC:01 1A 9B` com `F85E=0Ah`. Isso confirma o
  caminho dos dois bits até o protocolo no modelo,
  sem identificar a causa física nem a ligação real do interruptor.
- `MA17_TRACE_PC=1 MA17_TRACE_IDLE_FAULT=1` agora registra também
  `F839`, `RAM24`, `RAM70` e o latch de P4 na origem da falha; o latch
  não é uma medição do nível elétrico no pino. A regressão
  `PhysicalLambda.ConditionalClosedLoop` preserva os dois contrastes
  e passou 1/1 em 47,01 s após o ajuste observacional.
- O rastro `MA17_TRACE_PC=1 MA17_TRACE_IDLE_F839=1` localizou 35
  mudanças de `F839` entre a abertura e a soltura no braço baixo
  quando fechado: `0Fh→0Eh` em 10.014.010 (`555Bh`), passagem por
  `1Fh`, depois `2Fh→2Eh` em 10.997.600 (`555Bh`). Os bits de
  `RAM27` ligaram 13/16 ticks depois. Ao fechar o contato, `2A4Bh`
  restaurou `2Eh→0Fh` em 12.011.027. Os bytes `F835=90h` e
  `RAM6F=90h` acompanharam a contagem, sem semântica física validada.
  Na polaridade oposta, a abertura restaurou `AEh→0Fh` quase de
  imediato, mas o cenário já tinha `F84E=06h` antes do pedal e
  terminou com `F85E=02h`; inverter a polaridade não dá um nominal
  livre de falhas. Com/sem esse rastro, as 3.058 linhas de stdout
  do ensaio até 13 milhões de ticks foram idênticas.
- Varredura de amplitude no mesmo cenário até 13 milhões de ticks,
  pedal de 10 a 12 milhões: 2 mm não mudou `F839` nem publicou falha;
  o batente alcançou a alavanca (`contact=true` nas amostras de 10,89
  e 11,88 milhões). Com 4, 6 e 8 mm houve 35 escritas observadas de
  `F839` durante o pedal, terminando em `2Fh→2Eh`, e `F84E` alcançou
  `0Ah`; a haste ficou perto de 7,632 mm, afastada da borboleta.
  Com 12 mm não houve essas escritas nem `F84E` nesse intervalo, e a
  haste ficou perto de 3,692 mm. Os comandos candidatos da ponte H
  tiveram, respectivamente, 59/2/2/2/0 bordas nos cinco braços.
  Portanto, o diagnóstico neste binding depende da combinação de
  contato, TPS e ramo de comando, não apenas do tempo com pedal aberto.
  Os valores mecânicos e o vínculo P4.6 continuam hipóteses; as demais
  guardas `24h.4`, `2Eh.0` e `2B38h` ainda precisam de atribuição física.
- O rastro `MA17_TRACE_PC=1 MA17_TRACE_IDLE_PEDAL_GATE=1` isolou a
  primeira guarda que separa 4 e 12 mm após o transiente. Em ambos,
  `P4.6=1`, `24h=81h`, `2Eh=A0h`, e `2A93h` não salta. Em `2A9Eh`,
  os opcodes fazem `A6h−R2−1`, com carry de entrada ligado. Com 4 mm,
  `R2=61h` (lido de `RAM6Fh` sob `2Eh.6=0`): sem empréstimo, chega
  a `2AB3h` e a contagem continua. Com 12 mm, `R2=B8h`: há
  empréstimo, `2AA0h` salta a `2A45h`, que recarrega `F839=0Fh`.
  A fronteira digital desta guarda é `R2≤A5h`; ela não calibra
  milímetros de pedal nem prova o nó elétrico do interruptor.
  `PhysicalLambda.ConditionalClosedLoop` agora cobre os dois ramos e
  passou 1/1 em 61,80 s. Com/sem o novo rastro, as 3.058 linhas de
  saída do ensaio de 8 mm até 13 milhões de ticks foram idênticas
  (SHA-256 `f1b3f60e2158d3dde329ac607c30060528948d11948619f600b75f64c490c0da`).
- Este toque de 2 s não atende à ausência de DTCs inesperados. A
  hipótese prioritária é ligação/calibração do interruptor e do
  batente; é preciso rastrear `F839` e medir a placa antes de ajustar
  a física ou chamar o diagnóstico de comportamento nominal.
- Validação após o rastro `F839`: build aprovado e
  `PhysicalLambda.ConditionalClosedLoop` 1/1 em 47,50 s. A última
  suíte completa, anterior a esse rastro observacional, passou
  **201/201** em 367,27 s. A ROM Fiat preserva SHA-256
  `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
  Com os dois braços de pedal, `PhysicalDiagnostics.KlineFaultHistory`
  passou 1/1 em 81,05 s após conferir as quatro triplas; os quatro
  controles ECT/TPS1 continuam no teste.

## Inventário e baseline (2026-11-15)

- Checkout `51062957a10585408340104909ce906c48950d4b`; núcleo CPU
  `833a90aad2d6901b7255feb2a8765c92dd229ebd`.
- ROM de referência `FiatTipo_MA17_dump_27c256.bin`, 32768 bytes,
  SHA-256 `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
- `cmake --build build -j 4`: aprovado; `ctest --test-dir build
  --output-on-failure`: 165/165 aprovados. Nenhuma falha anterior observada.
- Muitos arquivos não rastreados preexistentes; não remover nem sobrescrever.
  `asm51` e `disasm51` estão com submódulos ausentes, sem impedir o build atual.
- Scanner em `../Monomotronic-MA1.7-Scanner/src/ECUSerial/`;
  `SensorDecoders.cpp` e `KlineCollectionTables.h` disponíveis para leitura.
- `docs/MA17_RPM_TRACE.md` documenta captura Timer 2 / IEX3 e escala
  observada `RAM[47h] × 25 RPM`; ligação física P1.0 ainda é hipótese do perfil.

## Incremento atual: T1, primeiro caminho vertical

- Relação: torque do arranque → inércia → ângulo → 60 posições, 58 dentes.
- Fonte: clock Fiat de 11,88 MHz (`990000` ciclos de máquina/s),
  `include/CrankshaftSimulator.hpp`, `src/ma17/CrankInput.cpp` e
  `docs/MA17_RPM_TRACE.md`.
- Hipótese inicial: inércia equivalente e perdas serão parâmetros estimados,
  sem impor RPM mínimo. Referência dente/PMS permanece configurável.
- Verificação: partida de zero, parada sem torque, bordas com lacuna, captura
  e `47h` pela ROM; comparar dois passos e duas execuções idênticas.
- Implementado `engine::CrankDynamics`: `J·dω/dt` com torque de arranque,
  perdas e carga, integração a 990000 ticks/s, ângulo contínuo e roda 60-2.
  Parâmetros iniciais **estimados**, em SI: `J=0,20 kg·m²`, arranque `30 Nm`,
  atrito de soltura `4 Nm`, atrito em movimento `3 Nm + 0,02 Nm·s/rad × ω`.
  A posição 0 tem offset ajustável; fase real em relação ao PMS não validada.
- `--physical-crank --starter-ticks 495000 --stop-ticks 1485000` seleciona
  o caminho físico; o modo legado mantém estímulo de RPM fixo. O modo físico
  rejeita variáveis `MA17_*` exceto tracing, não injeta `RAM[47h]` nem o
  marcador XRAM legado e não usa pacing de parede.
- Comando de reprodução:
  `env -i PATH=/usr/bin:/bin ./build/emu8051-tty FiatTipo_MA17_dump_27c256.bin --physical-crank --starter-ticks 495000 --stop-ticks 1485000`.
  Em `tick=467981`, `physical_rpm=595,215`, a ROM escreveu `47h=22`
  em `PC=0EA5h`; em `tick=1485000`, `rpm=432,587`, `47h=17` (425 RPM
  nominais), 665 bordas de subida, 665 de descida e 22 posições ausentes.
  Eventos `crank_gap` em JSONL mostram as posições 58/59, por exemplo
  `tick=298462/301037`. A ROM não foi alterada.
- Teste negativo: com `--starter-ticks 1`, após 1485000 ticks o estado
  permanece em 0 RPM, sem bordas e com `47h=0`. Tracing ligado/desligado
  produziu os mesmos eventos e estado final no ensaio nominal.
- Ao retirar o arranque em `tick=198000` e avançar até `3000000`, o
  virabrequim parou sem reversão e a ROM voltou a `47h=0` em `tick=1850210`.
  O último pulso ficou alto na posição de parada; a semântica do condicionador
  de entrada em repouso ainda precisa de validação elétrica.
- Validação: build aprovado; `ctest --test-dir build --output-on-failure`
  169/169 aprovados. O teste de integração executa duas vezes o cenário
  nominal, compara resultados e executa o negativo.
- Próximo passo: separar telemetria física do log legado, investigar DTCs e
  guardas da ROM na partida física, e iniciar T2 (cabo e TPS duplo) com
  associação ADC/RAM confirmada no scanner e no inventário semântico.

## Física da planta (GOAL_SEVEL_FISICA) — fases 1–4 parciais
Escrito com ajuda de LLM (Claude). Detalhes, tabelas e divergências em
`docs/SEVEL_PHYSICS_CALIBRATION.md`.

- Fase 1: fórmulas F-01…F-57 como funções puras em `include/engine/physics/*.hpp`;
  26 testes em `tests/physics_formulas_test.cpp` (valores de referência à mão).
- Fase 2: telemetria publicada (`EmulatorSnapshot`, JSONL `{"type":"plant"}`,
  `engine::PlantWindow` com janelas de 20 ciclos de 4π).
- Fase 3: `sevel-dyno` (varredura a rotação constante) gera CSV com curva esperada
  e erro; `DynoPi` (malha PI com anti-windup) testado. GOAL_DYNO_ROM: integração exata do
  pulso, telemetria de eixo com balanço de energia, e a bancada headless `--dyno-point` com a ROM
  controlando o motor (ainda não ligada ao `SimSession`). Os números "atendidos" de potência e
  torque anteriores usavam a integração por amostra e foram substituídos; ver `docs/SEVEL_DYNO_ROM.md`.
- Fase 4: `eta_v(N, p_m)` (F-18/F-22), eficiência indicada física (F-30..F-34, MBT por
  Wiebe) ligadas como padrão (`--legacy-plant` volta ao modelo antigo). Plena carga:
  59,8 kW (81 cv) a 6000 RPM, 131–132 N·m a 3000 RPM (antes 35 cv / 57 N·m) [valores da integração
  por amostra, substituídos: hoje 60,1 kW a 6000 e 128,6 N·m a 3000 RPM após o refit da VE, que é
  um ajuste e não uma validação; ver `docs/SEVEL_DYNO_ROM.md`].
  Lenta quente com `--throttle-leak-mm2 3`: ~900–915 RPM, MAP ~33 kPa, λ≈1,00,
  avanço ~8° (alvo da ROM 925 RPM; manual 850 ± 50).
- Preset único da bancada: `tests/sevel_preset.py` (`BENCH_LEAK_MM2 = 3`).
