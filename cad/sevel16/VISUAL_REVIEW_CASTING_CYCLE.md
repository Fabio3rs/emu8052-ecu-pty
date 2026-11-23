# Ciclo e cortes — Casting A4 v001

Modelo `build/sevel-cad/models/SEVEL_Casting_A4_v001.FCStd`, SHA-256
`dde2e7fd7ddc363898757398ff1ee0f397a69195b77d45c7351a5c0b71ffe179`.
As 13 capturas listadas em `reports/SEVEL_Casting_A4_v001_cycle_captures.json`
foram abertas e examinadas individualmente: 0, 90, 180, 270, 359, 360, 450,
540, 630 e 720 graus, duas vistas da distribuição e a montagem externa.

Observações:

- Em 0/180 graus, os pares de pistões alternam entre as posições extremas.
  Em 90/270 graus, a inclinação das bielas muda de sentido mantendo os pinos
  ligados aos moentes. As imagens apoiam a leitura; medidas vêm do teste CAD.
- Em 0/360 graus, os pistões retornam às mesmas posições, enquanto comando e
  válvulas mostram o outro semiciclo. Em 0/720 graus, o conjunto retoma a pose;
  o tensor tem período próprio, verificado separadamente no controlador.
- 359/360 graus mostram a proximidade do cruzamento sem salto visual.
  Válvulas de admissão/escape mantêm cores distintas; o perfil é sintético.
- As duas vistas da distribuição mostram três polias dentadas e tensor
  externo no dorso da correia. Comparação topológica com catálogo PDF 32;
  dentes, distâncias entre eixos e relação do auxiliar permanecem provisórios.
- A vista externa mostra a nova envolvente do auxiliar. A necessidade de
  suavizar as transições e completar tampa/cárter permanece registrada em
  `VISUAL_REVIEW_ENCLOSURE.md`; não confundir mecanismo isolado com motor completo.

Os cortes longitudinal (175 objetos) e transversal em C1 (22) foram salvos,
reabertos e suas imagens examinadas. Ambos incluem o cabeçote, a 90 graus.
O longitudinal também foi inspecionado por `get_view`. A biela inclinada,
canaletas e apoio do auxiliar são legíveis no transversal; esse plano não
passa pelos eixos deslocados das duas válvulas, portanto não mostra ambas
inteiras. Partes desconexas apenas no corte não provam peças soltas na montagem.

As 191 peças herdadas são B-reps idênticos ao Head v002, permitindo conservar
suas comparações anteriores com fotos de virabrequim, pistões/bielas e catálogo
do comando. A revisão atual acrescenta a nova fundição e suas interfaces.

Resultado: ciclo e cortes revisados com diferenças documentadas. Não é uma
prova visual de folga industrial, nem substitui interseções B-rep e medições.
