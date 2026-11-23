# Distribuição — primeiro checkpoint: volante

Modelo: `build/sevel-cad/models/SEVEL_Flywheel_A4_v001.FCStd`.
174 sólidos válidos, salvos e reabertos. O incremento contém volante,
cremalheira de partida e seis parafusos; os 166 componentes A3 permanecem
geometricamente idênticos. A distribuição completa ainda está pendente.

## Comparação visual

Referências examinadas: foto 795677 do motor montado e manual
`PhotosECU/04-1.Motor 1580spi Monomotronic.pdf`, página impressa 12,
figura PX005G505. Capturas em `build/sevel-cad/evidence/`:

- `SEVEL_Flywheel_A4_v001-flywheel-Right.png`;
- `SEVEL_Flywheel_A4_v001-flywheel-Isometric.png`;
- `SEVEL_Flywheel_A4_v001-external-Isometric.png`;
- `SEVEL_Flywheel_A4_v001-pose090-Isometric.png`.

As vistas isométricas do volante isolado e do mecanismo foram examinadas
também com `get_view`. O disco, rebaixo central, seis fixações e cremalheira
separada reproduzem a organização visível. As posições axiais derivam da
face traseira do virabrequim, em X=362,5 mm, sem deslocar o datum mestre.
O conjunto gira solidariamente em torno de X, com centro Y=0, Z=-190 mm.

Diâmetro do corpo 250 mm, espessura 24 mm, 128 dentes trapezoidais e demais
cotas são hipóteses visuais, registradas em `flywheel_visual_estimated`.
Não há confirmação da contagem de dentes. A cremalheira é de partida;
não substitui a roda fônica. Faltam pinos periféricos e detalhes de usinagem
vistos na fotografia; os seis furos periféricos são uma simplificação.
Não foi modelada a embreagem nem validado o engrenamento com o motor de partida.

## Verificações realizadas

`reports/SEVEL_Flywheel_A4_v001_flywheel_validation.json`:

- Diferença simétrica B-rep dos 166 componentes herdados abaixo de 1e-5 mm³.
- 36 pares entre virabrequim e oito peças novas sem sobreposição acima de
  1e-5 mm³. Distância zero nos contatos previstos: flange/volante,
  volante/cremalheira e cabeças dos seis parafusos/volante.
- Separação axial mínima de 11,3 mm frente aos demais componentes. O limite
  vale continuamente porque as rotações em X e os deslocamentos existentes
  preservam essas faixas axiais; molas usam limites de raio e seção do arame.
- 145 poses entre 0° e 720°, passo de 5°, sem movimento relativo ao
  virabrequim; erro máximo de vértice de 1,82e-13 mm.

A prova retém os relatórios A3 por hash e verifica apenas o incremento.
Não equivale a outra varredura B-rep de todos os pares do motor nem valida
as partes A4 ainda ausentes. Os limites de cálculo não são tolerâncias fabris.

A caixa padrão do FreeCAD usou a triangulação de exibição e indicou
249,146 mm numa direção para o cilindro de Ø250 mm. O verificador foi
corrigido para `optimalBoundingBox(False)`, medindo diretamente a geometria,
sem relaxar o critério dimensional ou alterar a peça.

O STEP reabriu com 174 sólidos e erro relativo de volume de 0,194 ppm;
a calibração com pivô deslocado passou. Manifest de IDs/pivôs/materiais
em `exports/SEVEL_Flywheel_A4_v001/parts_manifest.json`. As malhas comprovadas
no renderizador ainda são as de A3 v002; este incremento aguarda exportação
de malhas. Os 12 testes Python existentes passaram com os parâmetros atuais.

Pendentes: polias, roda fônica/sensor, eixo auxiliar, tensor e correia;
revisão angular da gaiola e do trem; transição curva da fundição; validação
e exportação da montagem final, incluindo vistas da distribuição.

## Distribuição externa — A4 v002

`models/SEVEL_Timing_A4_v002.FCStd`: 182 sólidos salvos/reabertos. Foram
acrescentadas as polias do comando, virabrequim e auxiliar; ponta dianteira
e bucha do auxiliar; tensor e suporte; correia. A v001 tinha um afastamento
de 8 mm entre suporte do tensor e bloco; a v002 corrige seu comprimento.
Não sobrescrever o checkpoint anterior nem tratar a v001 como aprovada.

Comparação com `wireframe_com_polias.png` e manual, páginas impressas 10–12:
comando no topo, auxiliar deslocado lateralmente, virabrequim inferior e
tensor atuando no dorso da correia. A polia do comando tem cinco janelas.
A vista Left da distribuição e a isométrica do mecanismo foram examinadas;
13 capturas `evidence/SEVEL_Timing_A4_v002-*` cobrem distribuição, exterior
e poses 0/90/180/270/359/360/450/540/630/720°, com molas CAD correspondentes.

Os 20/40/20 dentes são escolhas visuais, mantendo comando 1:2 e auxiliar
independentemente parametrizado em 1:1. A correia é um sólido liso estático,
formado por tangentes e arcos exatos, com folga visual de 0,2 mm dos envelopes
rotacionais. Não há simulação do engrenamento dos dentes, tensão, comprimento
comercial ou deslocamento do material da correia. A bomba d'água não foi
incluída nesse circuito. Posições e larguras das polias continuam estimadas.

O manual local, páginas impressas 7 e 15 (PDF 9 e 17), documenta dois
diâmetros de colos e buchas do auxiliar. O mancal dianteiro usa Ø35,6055 mm
no eixo e Ø35,674 mm na bucha: folga radial medida de 0,03425 mm. A bucha
tem Ø38,715 mm externo, compatível com a sede representada no bloco. O
modelo usa contato geométrico, sem inventar magnitude de interferência.
Mancal traseiro, comprimento interno do eixo e acionamento da bomba de óleo
continuam pendentes; a ponta dianteira não constitui o eixo auxiliar completo.

`*_timing_validation.json`: 174 B-reps herdados com diferença simétrica zero;
64 pares de envelopes/peças sem sobreposição. Foram incluídos o curso completo
do primeiro pistão e o envelope rotacional do trecho pertinente do virabrequim.
As 145 poses verificaram as relações angulares. O controlador real passou:
16 molas animadas, repetição de fase sem deriva e remoção das prévias ao fechar.
O tensor mantém seu período angular próprio, portanto sua orientação não
é incluída na igualdade de placements 0/720° dos órgãos de período compatível.

STEP reaberto: 182 sólidos, erro de volume 0,182 ppm e calibração aprovada.
Manifest com eixos e pivôs de auxiliar/tensor em
`exports/SEVEL_Timing_A4_v002/parts_manifest.json`. Os 16 testes Python passam,
incluindo mudança independente de relação/fase do auxiliar e continuidade
do trajeto. Malhas atualizadas, roda fônica/sensor/polia de acessórios e
correções de fundição/inclinação continuam pendentes.

## Polia de acessórios, roda fônica e sensor — A4 v001

`models/SEVEL_Trigger_A4_v001.FCStd`: 188 sólidos válidos, salvos/reabertos.
Seis peças adicionadas: polia, roda fônica, arruela, porca, sensor e suporte.
Os 181 componentes herdados sem alteração foram comparados por diferença
simétrica B-rep. O virabrequim recebeu somente uma extensão cilíndrica
de raio 15 mm e comprimento 17 mm; o comprimento da ponta passou de 35 a
52 mm para fechar a pilha axial. Roscas e aperto continuam simplificados.

Referências: manual de desmontagem, PX003G509/510, e
`wireframe_com_polias.png` para a separação entre polia dentada e externa.
O manual `OCR_03-1.Tipo 1.6 SPI.pdf`, página impressa 18/PDF 20, foi
examinado e fornece entreferro de 0,5–1,5 mm; adotou-se 1 mm.
Diâmetros, suporte e posições são hipóteses geométricas. O padrão 60−2
e a montagem angular não foram confirmados pelo manual: permanecem
parametrizados separadamente do ângulo do sensor. A fase com PMS é UNKNOWN.

As vistas isoladas da polia/roda/sensor foram examinadas no `get_view`;
a captura `SEVEL_Trigger_A4_v001-missing-gap-Right.png` mostra o sensor
diante da região sem dois dentes. A organização das peças é legível,
mas o suporte ainda é uma hipótese de ligação à carcaça existente.
Há 16 capturas `evidence/SEVEL_Trigger_A4_v001-*`, incluindo as dez poses,
distribuição, exterior e detalhes da roda/sensor.

`reports/SEVEL_Trigger_A4_v001_trigger_validation.json` registra:

- 36 pares de envelopes/peças sem sobreposição; contatos previstos com
  polia dentada, arruela, porca, bloco e virabrequim verificados.
- Extensão do virabrequim igual ao cilindro declarado, sem volume removido;
  separação axial mínima de 5,5 mm frente às demais peças herdadas.
- 58 dentes medidos nas faces CAD, espaçamento nominal de 6°; 18° entre
  centros ao atravessar a lacuna e arco de raiz de 15°.
- 145 poses rígidas, 58 passagens de centros de dentes com entreferro
  de 1 mm e distância de 5 mm no centro da lacuna, em theta=99°.
- Envelope contínuo de rotação com folga mínima sensor/roda de 1 mm.

STEP reaberto com 188 sólidos, erro de volume de 0,174 ppm e calibração
de pivô aprovada. O controlador passou com 16 molas deformáveis, fases
repetíveis e restauração da pose zero. Os 21 testes Python passaram.

Malhas: `exports/SEVEL_Trigger_A4_v001/meshes_v001/`, 188 instâncias e
75 geometrias OBJ compartilhadas. `renderer_checks.json` comprova carga
das quatro poses completas no `RecordingRenderer`, desvio máximo de caixa
de 0,039876 mm contra o CAD e igualdade 0/720 para os 187 componentes
de período compatível. A matriz do tensor é verificada separadamente
pela sua relação angular. A regressão do pacote A3 também passou.
`evidence/SEVEL_Trigger_A4_v001-renderer-090.png` foi examinada: mecanismo
e distribuição aparecem na projeção lateral, sem ocultação por profundidade.
Esta é uma prova de carga/pose, não integração do painel interativo do Lab.

Permanecem pendentes o auxiliar interno/traseiro, a revisão das inclinações
da gaiola/cabeçote e da transição curva do bloco, além da consolidação dos
relatórios e exportações da montagem final. A bomba d'água não foi acoplada
à distribuição; seu acionamento de acessórios ainda não está representado.

## Eixo auxiliar interno e segundo mancal — A4 v002

`models/SEVEL_Auxiliary_A4_v002.FCStd`: 189 sólidos válidos, salvos/reabertos.
O eixo anterior foi prolongado, conservando seu PartId. Agora contém dois
colos, corpo, excêntrico e dentes torcidos simplificados. A bucha traseira
é uma peça separada. O bloco recebeu passagem interna e apoio traseiro;
186 componentes anteriores foram comparados por diferença simétrica B-rep
e permanecem iguais. O modelo Trigger A4 v001 está preservado.

Referência: manual de desmontagem, página impressa 12, PX005G506, cotejada
com o diagrama e as cotas do manual técnico, página impressa 15/PDF 17.
A vista isométrica no `get_view` mostra polia, bucha maior dianteira,
excêntrico, corpo longo e conjunto engrenagem/mancal traseiro. A organização
corresponde à referência; a foto não fornece os comprimentos axiais.
Esses comprimentos, o deslocamento do excêntrico e os 14 dentes/torção de
18° são ASSUMPTION. O perfil é facetado, sem evolvente ou prova de contato;
não há árvore conjugada da bomba de óleo. O flange/retentor frontal da foto
ainda não foi reproduzido como peça separada.

A primeira versão falhou: o loft suave extrapolava o cilindro dos dentes
em 21,7118 mm³. O relatório da v001 registra FAIL e ela foi preservada.
A v002 usa seções regradas, contidas no raio declarado. Não houve mudança
do raio nem relaxamento da tolerância. A refinação do bloco também produziu
uma falha booleana na comparação, apesar de `isValid`; mantiveram-se as
subdivisões do resultado booleano original, cuja comparação passou.

`reports/SEVEL_Auxiliary_A4_v002_auxiliary_validation.json`:

- 186 peças herdadas idênticas; colo traseiro medido em Ø31,950 mm.
- Folgas radiais dianteira/traseira de 0,03425/0,030 mm; bucha traseira
  assentada sem sobreposição. Interferência de montagem não foi inventada.
- Envelope de rotação completo do auxiliar contido na passagem, com
  distância mínima de 1 mm do bloco. Adição/remoção de material restritas
  às ferramentas declaradas e afastadas 20,8 mm do limite Y dos cilindros.
- 220 fases, 58 interseções B-rep após filtro espacial, nenhuma colisão
  acima de 1e-5 mm³ nos pares do incremento. O trem superior fica separado
  por um limite contínuo em Z; o conjunto inferior é conferido nas fases
  declaradas. Esta não é uma nova varredura de todos os pares herdados.
- 145 poses reais: eixo e polia com o mesmo placement, buchas fixas,
  erro máximo de vetor de rotação/pivô de 1,25e-15.

Controlador FreeCAD aprovado: 16 molas deformáveis, repetição 0/720 sem
erro nos componentes de período compatível, tensor tratado separadamente,
timer funcional e retorno a zero. STEP reaberto com 189 sólidos, erro
relativo de volume de 0,173 ppm e calibração de pivô aprovada.

Foram salvas 16 capturas, incluindo duas do auxiliar e um corte longitudinal
em `models/SEVEL_Auxiliary_A4_v002_AuxiliarySection.FCStd`. A seção e a
isométrica foram examinadas: a passagem liga o alojamento dianteiro ao
segundo apoio e revela o posicionamento das buchas. O desenho do apoio e
as superfícies internas são hipóteses de fechamento mecânico, sem metrologia
da fundição. As inclinações da gaiola/cabeçote, o contorno amplo do bloco e
a consolidação das entregas finais continuam pendentes.

As malhas deste checkpoint também foram verificadas:
`exports/SEVEL_Auxiliary_A4_v002/meshes_v001/`, 189 instâncias em 76 OBJ
compartilhados. As quatro poses completas passaram no carregador e no
`RecordingRenderer`, com erro máximo de caixa de 0,039876 mm frente ao CAD.
Os 188 componentes de período compatível repetem exatamente em 0/720°;
a matriz do tensor é validada pelo período próprio. A calibração de escala,
pivô e orientação passou. A imagem `SEVEL_Auxiliary_A4_v002-renderer-090.png`
foi examinada; ela comprova carga/pose e mantém a limitação de projeção sem
ocultação por profundidade, sem integração no painel interativo do Lab.
