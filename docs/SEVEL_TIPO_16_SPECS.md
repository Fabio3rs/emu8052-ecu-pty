# Especificações Técnicas do Carro Real: Fiat Tipo 1.6 SPI SOHC (Bosch Mono-Motronic MA 1.7)

Este documento registra os parâmetros físicos, mecânicos, elétricos e de instrumentação do veículo real (**Fiat Tipo 1.6 i.e. SPI SOHC**, motor Sevel 1581 cm³) para calibração e correspondência fidedigna da interface gráfica e do modelo de simulação do `sevel-ma17-lab`.

---

## 1. Painel de Instrumentos Real (Veglia Borletti Electronic)

Fotografias do conjunto de mostradores com iluminação verde original acesa e motor em funcionamento registraram as seguintes graduações:

### 1.1 Tacômetro (`ENGINE SPEED` / Conta-giros)
- **Fabricante / Modelo:** Veglia Borletti *ELECTRONIC x100*.
- **Fundo de escala:** **$8000\text{ RPM}$** (marcas numéricas: `0, 10, 20, 30, 40, 50, 60, 70, 80`).
- **Passo da escala:**
  - Marcas principais a cada $1000\text{ RPM}$ ($10\times 100$).
  - Marcas secundárias a cada $100\text{ RPM}$ ($1\times 100$).
- **Faixa de Marcha Lenta (Idle Zone):** $850\text{ a }900\text{ RPM}$ (ponteiro estabilizado logo abaixo do número 10).
- **Faixa Amarela (*Yellow Line*):** Início em **$5600\text{ RPM}$** até **$6000\text{ RPM}$** (`#F5CD1E`).
- **Faixa Vermelha (*Redline*):** Início em **$6000\text{ RPM}$** até **$8000\text{ RPM}$** (`#EE4445`).

### 1.2 Velocímetro (`VEHICLE SPEED`)
- **Fundo de escala:** **$200\text{ km/h}$**.
- **Graduação:** Marcas numéricas em passos de $20\text{ km/h}$ (`0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200`), com traços intermediários a cada $10\text{ km/h}$.
- **Hodômetro:** Total mecânico e parcial com botão de zeramento.

### 1.3 Termômetro do Líquido de Arrefecimento (`COOLANT`)
- **Escala de temperatura:** **$50^\circ\text{C} - 90^\circ\text{C} - 130^\circ\text{C}$**.
- **Temperatura nominal de operação:** **$90^\circ\text{C}$** (ponteiro na horizontal ou ligeiramente inclinado para cima).
- **Faixa crítica de superaquecimento:** Acima de $120^\circ\text{C}$, atingindo a marcação vermelha em $130^\circ\text{C}$.
- **Válvula termostática:** Abertura mecânica em $87^\circ\text{C}$.
- **Eletroventilador:** Acionamento em dois estágios / histerese em torno de $92^\circ\text{C} - 97^\circ\text{C}$.

### 1.4 Indicador de Combustível
- **Escala:** $0\text{ (Reserva) } - 1/2\text{ (Meio tanque) } - 1\text{ (Cheio)}$.
- **Luz de reserva:** LED integrado ativado abaixo de ~7 litros.

---

## 2. Motor Fiat Sevel 1.6 SPI SOHC

### 2.1 Dados Geométricos & Termodinâmicos
- **Cilindrada:** $1581\text{ cm}^3$ ($1.581\text{ L} \approx 96.5\text{ CI}$).
- **Número de cilindros / Disposição:** 4 cilindros em linha, montagem transversal, inclinado para a frente.
- **Diâmetro dos cilindros (Bore):** $86.400\text{ a }86.450\text{ mm}$ (Classes de pistão: A: 86.360–86.370, C: 86.380–86.390, E: 86.400–86.410 mm).
- **Curso dos pistões (Stroke):** $67.400\text{ mm}$.
- **Taxa de compressão:** $9.2 : 1$ (gasolina).
- **Folga entre pistão e camisa:** $0.030\text{ a }0.050\text{ mm}$.
- **Ordem de ignição e combustão:** **$1 - 3 - 4 - 2$**.
- **Diâmetro dos mancais principais:** $\varnothing\ 54.507\text{ a }54.520\text{ mm}$ (5 mancais de apoio).
- **Diâmetro dos moentes do virabrequim:** Buchas do eixo auxiliar $\varnothing_1 = 38.700\text{ a }38.730\text{ mm}$, $\varnothing_2 = 35.036\text{ a }35.066\text{ mm}$.

### 2.2 Desempenho & Curvas Características (CEE DIN)
- **Potência máxima ABNT:** **$82\text{ CV}$** ($60.4\text{ kW}$) a **$6000\text{ RPM}$**.
- **Torque máximo ABNT:** **$13.3\text{ daN}\cdot\text{m}$** ($133\text{ N}\cdot\text{m}$; $13.0\text{ kgf}\cdot\text{m}$) a **$3000\text{ RPM}$**.
- **Curva CEE:** a página 6 mostra curvas medidas pelo método CEE; seus picos não devem ser rotulados como os valores ABNT acima.
- **Regime de rotação máxima recomendada:** $6000\text{ RPM}$ contínua / corte por ECU em ~6300–6500 RPM.

As páginas digitalizadas em `PhotosECU/curso_numeros.png`,
`PhotosECU/desenhos_pistoes.png` e `PhotosECU/curva_potencia.png` são as
referências diretas para os números e para a forma das curvas. O desenho do
pistão mostra topo plano, três anéis próximos ao topo e saia curva na base;
`PhotosECU/desenhos_motor.png` mostra a biela e o virabrequim. Os recortes
do manual servem como referências visuais, não como texturas do motor animado.

### 2.3 Transmissão e ignição documentadas

- **Caixa:** C.513.5.13, cinco marchas; relações 3.909, 2.238, 1.541,
  1.156 e 0.891; ré 3.909 (`PhotosECU/manual_cambio.png`).
- **Diferencial:** 63/16 = 3.9375, apresentado como 3.938 no manual;
  a página de relações totais nas rodas imprime 15.393, 8.813, 5.784,
  4.107 e 3.343 (`PhotosECU/manual_cambio_2.png`). Para 3ª–5ª, esses
  números divergem dos produtos 1.541, 1.156 e 0.891 × 3.9375, que dão
  6.068, 4.552 e 3.508. Para apresentação e futura dinâmica aproximada,
  adotar as cinco relações da página de câmbio multiplicadas por 3.9375;
  identificar as relações totais impressas como uma tabela divergente,
  sem afirmar precisão de calibração. O velocímetro atual mostra uma
  entrada de cenário.
- **Embreagem:** monodisco a seco com comando mecânico
  (`PhotosECU/manual_embreagem.png`).
- **Ignição:** distribuição estática SPI, ordem 1–3–4–2; avanço de
  6° ± 2° em 850 ± 50 RPM (`PhotosECU/manual_ignicao_ecu.png`).

---

## 3. Sistema de Gerenciamento Bosch Mono-Motronic MA 1.7

### 3.1 Corpo de Borboleta (TBI) & Atuador de Marcha Lenta
Diferente de sistemas com válvula de desvio de ar (IACV / atuador *stepper* em duto paralelo), o sistema MA1.7 controla a marcha lenta movendo mecanicamente a própria borboleta de aceleração através de um motor elétrico DC:
- **Motor DC Atuador:** Avança ou retrai uma haste rosqueada móvel contra a alavanca da borboleta de aceleração.
- **Comprimento de avanço da haste:** Regulagem física nominal em torno de $5\text{ mm}$ de curso útil.
- **Interruptor de Mínimo (Microswitch de Lenta):** Localizado na ponta de contato da haste móvel com a alavanca da borboleta.
  - **Acelerador solto (pedal em repouso):** O batente da alavanca encosta no atuador, fechando o microswitch (`IDLE SW: CLOSED`, pino ligado ao terra). A ECU sabe que o motor está em regime de marcha lenta e assume o controle de malha fechada via PID de RPM pelo motor DC.
  - **Acelerador pressionado:** A alavanca se afasta do atuador, abrindo o microswitch (`IDLE SW: OPEN`). A ECU sai imediatamente da malha fechada de marcha lenta e passa para o mapa principal de aceleração.
- **Potenciômetro de Borboleta (TPS):** Dupla pista resistiva coaxial para garantir alta resolução na fase crítica inicial:
  - **Pista 1:** Leitura angular fina de $0^\circ\text{ a }24^\circ$.
  - **Pista 2:** Leitura angular complementar de $18^\circ\text{ a }90^\circ$.

### 3.2 Injeção & Ignição Estática
- **Injetor Monoponto (SPI):** Bico injetor central eletromagnético posicionado sobre o venturi da TBI, disparado em sincronismo ou semi-sincronismo com as voltas do virabrequim (canal `CC3`).
- **Sistema de Ignição 2x2 (*Wasted Spark*):** Bobina de faísca perdida sem distribuidor mecânico, com dois canais de potência acionados pelo microcontrolador 80C517:
  - **Canal A (`P5.0`):** Cilindros 1 e 4 (faísca simultânea; um em combustão, outro em escape).
  - **Canal B (`P5.1`):** Cilindros 2 e 3 (faísca simultânea).
- **Roda Fônica:** Disco dentado $60-2$ acoplado ao virabrequim com sensor de relutância variável indutivo ligado à porta `P1.0`.

---

## 4. Mapeamento de Calibração na Interface do Simulador (`sevel-ma17-lab`)

| Parâmetro Real | Configuração no Código | Arquivo Fonte |
| :--- | :--- | :--- |
| Escala do Tacômetro | $0\text{ a }8000\text{ RPM}$ | [src/lab/LabInstruments.cpp](file:///mnt/projects/Projects/emu8051-tty/src/lab/LabInstruments.cpp), [apps/sevel-ma17-lab/SdlDisplay.cpp](file:///mnt/projects/Projects/emu8051-tty/apps/sevel-ma17-lab/SdlDisplay.cpp) |
| Início da Faixa Amarela | $5600\text{ RPM}$ (`#F5CD1E`) | [src/lab/LabInstruments.cpp](file:///mnt/projects/Projects/emu8051-tty/src/lab/LabInstruments.cpp) |
| Início da Faixa Vermelha | $6000\text{ RPM}$ (`#EE4445`) | [src/lab/LabInstruments.cpp](file:///mnt/projects/Projects/emu8051-tty/src/lab/LabInstruments.cpp) |
| Escala do Termômetro | $50 - 90 - 130^\circ\text{C}$ | [apps/sevel-ma17-lab/SdlDisplay.cpp](file:///mnt/projects/Projects/emu8051-tty/apps/sevel-ma17-lab/SdlDisplay.cpp) |
| Haste do Motor DC | `STEM: X.XX mm` ($0\text{ a }5\text{ mm}$) | [src/lab/LabInstruments.cpp](file:///mnt/projects/Projects/emu8051-tty/src/lab/LabInstruments.cpp) |
| Microswitch de Batente | `IDLE SW: CLOSED / OPEN` | [src/lab/LabInstruments.cpp](file:///mnt/projects/Projects/emu8051-tty/src/lab/LabInstruments.cpp) |
| Cilindrada & Vazão de Ar | $1.581\text{ L}$ ($0.0279 \times \text{RPM} \times \eta_v$) | [src/lab/LabInstruments.cpp](file:///mnt/projects/Projects/emu8051-tty/src/lab/LabInstruments.cpp) |
