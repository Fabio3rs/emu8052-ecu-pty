# Conjunto móvel — checkpoint em andamento

Objetivo integral: `GOAL_SEVEL_CONJUNTO_MOVEL_CINEMATICA.md`. O conjunto completo
de 720° ainda não está entregue. Este registro distingue CAD construído,
verificação analítica e requisitos ainda pendentes.

Checkpoint atual consolidado: `models/SEVEL_Casting_A4_v002.FCStd`.
Amplia e afunila as transições da envolvente do auxiliar; a face do respiro
permanece visível. 192 sólidos válidos e 191 peças idênticas ao Head v002;
220 poses/3.730 interseções do incremento sem colisões, folga auxiliar de 1 mm.
Dimensões, 13 protótipos reconstruídos, 145 poses CAD e controlador passaram.
STEP reaberto: 192 sólidos, erro de volume 0,0711 ppm. OBJ: 192 peças/79
malhas; sete entradas de pose/calibração aprovadas no renderer, erro máximo
de caixa de 0,039876 mm. As 13 capturas de ciclo, seis da envolvente e três
cortes foram examinados. O relatório único incorpora dez provas diretas e
dez estágios; o agregado anterior foi arquivado antes da substituição.
Revisões: `VISUAL_REVIEW_ROOT_BLEND.md` e `VISUAL_REVIEW_CASTING_V002.md`.
O pacote portável abaixo permanece referente ao v001. Próximas adições:
tampa, cárter, acessórios simplificados e vista explodida, conforme auditoria.

Checkpoint anterior: `models/SEVEL_Casting_A4_v001.FCStd`, 192 sólidos válidos.
Integra a envolvente do auxiliar, preservando 191 peças do Head v002.
220 poses e 951 interseções B-rep do incremento sem colisões, folga de 1 mm;
13 protótipos reconstruídos, 145 poses CAD, controlador 720°, 24 testes Python,
STEP e OBJ aprovados. O relatório único agora aponta para Casting v001,
com dez provas diretas e dez estágios. Treze capturas do ciclo e os cortes
foram examinados. Ver `ENCLOSURE_STATUS.md` e `VISUAL_REVIEW_CASTING_CYCLE.md`.
O cálculo antigo terminou; nenhuma execução GUI ficou pendente.

Pacote anterior verificado: `deliveries/SEVEL_Casting_A4_v001_v002/`, 542 arquivos.
A cópia em outro caminho passou 24 testes, recompilação C++, sete entradas
no renderizador e auditoria dos dez estágios da cadeia de provas. O FreeCAD
independente abriu os 192 sólidos do pacote, reconstruiu 13 protótipos sem
diferença B-rep e verificou 145 poses. Inclui calibração STEP, parâmetros
validados e B-reps do incremento; fotos/PDFs permanecem externos e indexados.
Prova: `reports/SEVEL_Casting_A4_v001_portable_delivery.json`.

Fechada a lacuna de 3 mm sob os apoios internos das oito molas. As duas
regiões CAD representam um prato inferior com ressalto, conforme item 12
do catálogo, sem alegar duas peças OEM. Alturas das molas, eixos e movimentos
preservados; 184 sólidos idênticos, 1.500 pares aprovados e contatos contínuos
até o cabeçote. `VISUAL_REVIEW_SEATS.md` registra a correção e as capturas.
STEP e OBJ de v002 aprovados, 21 testes Python e controlador de 720° passando.
O manifest agora identifica o gerador, materiais e grupos dos pratos inferiores.
Pacote portável do Head v002: `deliveries/SEVEL_Head_A3_v002_v002/`, com
454 arquivos conferidos, fontes e parâmetros do checkpoint. A cópia em outro
caminho passou os 21 testes e recompilou/carregou o renderizador C++ nas sete
entradas de pose/calibração. O FreeCAD independente abriu os 192 sólidos,
reconstruiu 13 protótipos com diferença B-rep zero e verificou 145 poses,
incluindo curso/cosmética em cópias. Relatório `*_portable_delivery.json`.
Materiais por região implementados e conferidos em `exports/SEVEL_Head_A3_v002/meshes_v003/`:
192 peças, 79 malhas e bindings por primitive nas quatro poses e calibração.
Bloco, cabeçote e gaiola separam fundição das interfaces usinadas conhecidas;
vértices, pivôs e movimentos preservados. As seis vistas estáticas foram
examinadas. Relatório `*_material_regions_v003.json`, descrição em
`MATERIAL_REGIONS.md`; 24 testes Python aprovados. O pacote portável anterior
continua preservado; o pacote Casting acima já inclui os materiais por região.

Teste GLB: formato registrado, mas três calibrações nativas falharam antes
de criar arquivo, inclusive com tesselação e modo alternativo. Evidências em
`exports/glb_calibration_v001..003/` e `GLB_CAPABILITY.md`; STEP/OBJ mantidos.

Checkpoint anterior: `models/SEVEL_Head_A3_v001.FCStd`, 192 sólidos válidos.
Corpo inferior do cabeçote e duas juntas adicionados ao Carrier v001;
189 peças herdadas idênticas, datum preservado e 570 pares novos aprovados.
O catálogo de 426 páginas fornecido pelo usuário está registrado nas fontes.
`VISUAL_REVIEW_HEAD.md` registra fotos/pranchas, capturas e limitações.

STEP reaberto (erro de volume 0,103 ppm), oito capturas e corte pelo eixo
de escape de C1 disponíveis. Malhas: 192 peças/79 OBJ, quatro poses aprovadas
no renderizador existente, erro máximo de caixa 0,039876 mm. Os 21 testes
Python passaram. Câmaras de 19,224686 cm³ ainda não reproduzem os 33,7 cm³
documentados. Faltam galerias de água completas e relevos internos. A lacuna
dos assentos internos de mola observada em v001 foi corrigida em v002.
O checkpoint é uma prévia geométrica, não uma montagem mecânica concluída.

Consolidação histórica do Head v002: dez relatórios diretos e nove estágios.
O relatório atual `reports/kinematics_validation.json` aponta para Casting v001.
O Carrier foi preservado em `kinematics_validation.carrier.da8db84a9817.json`.
`head_proof_chain.py` verifica os links, as identidades B-rep preservadas e
a cobertura exata dos 570 + 1.500 pares dos incrementos do cabeçote/apoios.
O status continua `PASS_CURRENT_KINEMATICS_VISUAL_WORK_PENDING`.

No Head v002, novas medições aprovaram 192 sólidos, reconstrução idêntica de
13 protótipos, alterações de curso/cosmética em cópias e 145 poses CAD.
Os quatro cursos medidos são 67,4 mm; erro máximo biela/pino 7,994e-14 mm.
A prova analítica atual é `SEVEL_Head_A3_v002_analytic.json`, com 21 testes.
Foram examinadas 13 capturas do ciclo/distribuição/exterior e dois cortes
com cabeçote: longitudinal com 175 objetos, transversal C1 com 22, ambos 90°.
`VISUAL_REVIEW_CURRENT_CYCLE.md` registra as observações e limitações.

A flange inferior já tem os dois recuos curvos da junta. A envolvente do
auxiliar foi adicionada no Casting v001; suas raízes, a parede lateral e as
nervuras ainda precisam de refinamento, além dos componentes visuais ausentes.

Varredura inferior herdada do Carrier, com peças inalteradas: 68 peças, 220 fases,
2.278 pares e 12.351 testes B-rep; nenhuma colisão inesperada, quatro encaixes
prensados biela/bucha dentro dos limites explícitos. Sete estágios da cadeia
de colisões tiveram modelos, links entre relatórios e peças preservadas
conferidos. Isso combina amostras discretas e exclusões contínuas específicas.
Não constitui uma certificação contínua de todos os pares.

No checkpoint Carrier, repetiram-se 1.760 contatos came/tucho, medições de
interfaces, reconstrução de 13 protótipos, duas variantes em cópias e 145
poses CAD: curso 67,4 mm nos quatro pistões, erro máximo biela/pino
7,994e-14 mm. O controlador foi exercitado novamente e identificado por hash.
Os cortes `SEVEL_Carrier_A3_v001_Longitudinal` e `..._TransverseC1`, ambos a
90°, foram salvos/reabertos e examinados. O transversal passa entre os eixos
das duas válvulas de C1; portanto não mostra suas hastes completas.
Esses cortes do baseline precedem a adição da fundição inferior do cabeçote.

## Inventário e reutilização

- FreeCAD 1.1.4, addon MCP 0.1.32, protocolo 3; RPC saudável e sem tarefa prévia.
- Fonte preservada: `build/sevel-cad/models/SEVEL_Block_M2b_v008.FCStd`.
- Gabarito existente conferido por recálculo, sem alteração. Entrecentros
  93/96/93 continuam `OTHER_VARIANT_REFERENCE`; alvo Tipo i.e. **82 cv**.
- Não há FCStd/STEP prévio dos órgãos móveis. Há malhas e gerador em
  `tools/gen_sevel_meshes.py` e `.work/gui-review/v2/sevel_meshes.obj`.
  O virabrequim dessa malha usa passo uniforme de 95 mm e superfícies abertas;
  a biela contém discos fechados sem furos e primitivas sobrepostas; o pistão
  não tem alojamento funcional do pino. Não servem como sólidos de montagem.
- Foram reaproveitados os raios estimados da cabeça/pé da biela desse gerador
  e o comprimento provisório de 127 mm de `include/lab/SevelGeometry.hpp`.
- Visualizador existente: `src/lab/DonorScene.cpp`, `AuthoredMeshLibrary`, OBJ.
  Suas convenções e dimensões ainda precisam de um adaptador e prova de carga.
- Catálogo completo agora disponível em `PhotosMotor/Tipo 1.6 - Tipo 1.6 4P
  1.6 SPI 8V Gasolina 1993-1995.pdf`: 426 páginas, código 160.362.1.
  Pranchas PDF 2, 12, 14, 16, 32, 34 e 36 inspecionadas e confrontadas
  com suas tabelas. Fonte, hash e ressalvas em `catalog_source.py` e no
  relatório gerado `reports/moving_sources.json`. Numeração inclui a capa.
  O desenho local `PhotosMotor/wireframe_com_polias.png` também foi
  inspecionado; números de dentes continuam sem confirmação documental.

## Evidências já examinadas

- Catálogo 10101, PDF 14–15: gaiola catalogada como cabeçote 7648903,
  junta superior 7797034 e junta inferior recortada 7784728. A perspectiva
  corrobora as interfaces separadas; não estabelece ângulos ou raios.
- Catálogo 10106, PDF 32–35: polias do comando/auxiliar/virabrequim,
  tensor, espaçador e proteções separados; ref. 9 é espaçador, não outro tensor.
- Catálogo 10107, PDF 36–38: oito tuchos, dezesseis semicones de retenção
  (dois por válvula), oito molas de cada tipo e oito retentores.
  O desenho repete o número 14 junto a um retentor; a tabela atribui
  retentores à ref. 10 e válvulas de admissão à ref. 14.
- Calços de reposição listados até 4,90 mm no catálogo não substituem a
  faixa 3,25–4,70 mm do manual. A tabela também repete 3,80 mm para dois
  códigos consecutivos; a ambiguidade foi registrada sem corrigir a fonte.
- Revisão da gaiola `SEVEL_Carrier_A3_v001`: 189 sólidos, 188 peças herdadas
  idênticas; `*_carrier_validation.json` passou com 98 envelopes contínuos
  e 90 separações espaciais. Cinco apoios e oito alojamentos conferidos.
  Planos +22°/−12° e reentrâncias inferiores continuam provisórios.
  Dezessete capturas e revisão em `VISUAL_REVIEW_A3.md`; controlador de
  720° aprovado, 16 molas deformáveis e erro de periodicidade zero.
  STEP reaberto com erro de volume de 0,161 ppm. Pacote
  `exports/SEVEL_Carrier_A3_v001/meshes_v001`: 189 peças, 76 OBJ,
  quatro poses aprovadas pelo RecordingRenderer; desvio máximo 0,039876 mm.
  O timeout da exportação foi apenas de observação: a mesma tarefa terminou
  com sucesso e restaurou theta=0. RPC novamente saudável, sem trabalho pendente.
  Vinte e um testes Python passaram. Cabeçote inferior, transição curva do
  bloco e consolidação final dos relatórios do objetivo permanecem pendentes.
- Manual `PhotosECU/OCR_03-1.Tipo 1.6 SPI.pdf`, imagens PDF 9–12, 14 e 16:
  classes de pistão/pino, sedes, casquilhos, colos, eventos e altura do came.
- Fotografias 707064 e 683381: duas vistas do virabrequim, colos, braços e
  quatro contrapesos predominantes. Contorno simplificado, sem balanceamento.
- Fotografia 994280: pistão por fora, coroa, pino e cavidade inferior.
- Fotografia 760527: biela bipartida, haste com seção I e parafusos.
- Fotografias originais não modificadas; variantes de anúncios não confirmadas.

Referência adicional enviada pelo usuário: `PhotosECU/04-1.Motor 1580spi
Monomotronic.pdf`, seção 10, páginas impressas 10–12 (PDF 12–14), examinadas
diretamente. Fonte e hash registrados por `inventory.py`.

| Figura | Evidência para a próxima montagem |
|---|---|
| PX003G502 | Tampa e junta separadas, com seis regiões de fixação |
| PX003G504 | Polia do comando com cinco grandes aberturas de alívio; contagem dos dentes ainda desconhecida |
| PX003G509/510 | Pinhão dentado do virabrequim e polia externa são peças distintas, com posições axiais a reconciliar |
| PX004G501/502 | Chapa posterior da distribuição tem contorno e recortes próprios, não é uma junta do bloco |
| PX004G504 | Bomba d'água com polia lisa como conjunto separado; não inseri-la automaticamente no circuito dentado |
| PX005G501 | Cabeçote removido com gaiola de quatro janelas: corroboração pelo manual do alvo |
| PX005G505/506 | Volante com cremalheira e eixo auxiliar com flange/junta separados |
| PX005G507 | Cárter assimétrico e sua junta, úteis para o perímetro da interface inferior |

Essas fotografias estabelecem identidade e organização dos componentes.
Não fornecem cotas, números seguros de dentes, fase da roda fônica ou ângulos
da gaiola/válvulas. As relações acima não alteram os parâmetros dimensionais
nem validam peças A4 ainda ausentes.

## Estado dos requisitos

| Requisito | Evidência / estado |
|---|---|
| A1: cinco munhões, quatro moentes, eixo contínuo | `SEVEL_Crank_A1_v002.FCStd`; sólido válido, salvo/reaberto |
| A1: giro dentro do bloco | Relatório A1 v002: 438 pares/poses, PASS; cobre apenas virabrequim/bloco/capas |
| A2: pistões, pinos, anéis, bielas, capas, buchas, parafusos | `SEVEL_Moving_A2_v003.FCStd`, 68 sólidos, reconstrução idêntica; orientação das aberturas dos anéis corrigida |
| A2: varredura de 720° e revisão final | v003 PASS em 150 fases, 8.191 interseções B-rep, nenhuma colisão não prevista; revisão em `VISUAL_REVIEW_A2.md` |
| A3: comando/8 lóbulos/5 apoios/8 conjuntos/molas duplas | `SEVEL_ValveTrain_A3_v002.FCStd`, 171 sólidos; dimensões e contato de cames aprovados, ver `VISUAL_REVIEW_A3.md` |
| A4: volante, roda fônica, correia, auxiliar, tensor | Auxiliary A4 v002 inclui eixo auxiliar com dois mancais, excêntrico/engrenagem visual; geometria axial provisória e acionamento conjugado não modelado |
| B: poses absolutas, conexão biela/pino, fases e curso | 21 testes Python passam; 145 poses FreeCAD verificadas; relatório analítico ainda parcial |
| B: contato real came/tucho e colisões de todos os sistemas | 1.760 contatos em 220 fases PASS; A3: 21.112 interseções B-rep; incrementos A4 validados por B-rep/envelopes, consolidação final pendente |
| C: poses, cortes, captura externa/distribuição/cruzamento | Capturas A2/A3 e 16 vistas Trigger A4, incluindo distribuição e cruzamento; revisão final pendente |
| C: STEP/malhas, IDs, pivôs, materiais, visualizador | STEP Auxiliary A4 v002 reaberto com 189 sólidos; 76 OBJ compartilhados, 189 instâncias; quatro poses no RecordingRenderer aprovadas |
| C: mudança de curso e cosmética com reconstrução CAD | PASS em cópias: curso 70 mm e meia-abertura de contrapeso 48°; baseline inalterado |

A cópia do bloco da montagem possui uma região inferior revista para alojar
as bielas. É uma hipótese de fechamento cinemático, ainda sem calibração
fotográfica; o contorno da face de vedação foi conferido no B-rep. A aparência
do novo abaulamento ainda precisa de confrontação com medidas/referências melhores.

Checkpoint atual: `build/sevel-cad/models/SEVEL_Moving_A2_v003.FCStd`.
STEP e manifest: `build/sevel-cad/exports/SEVEL_Moving_A2_v003/`.
Após salvar a câmera, os 68 B-reps foram comparados geometricamente à cópia
exata usada no STEP: diferença simétrica zero; poses preservadas. O FCStd
foi reaberto novamente e a câmera salva foi conferida.

Checkpoint A3 adicional: `build/sevel-cad/models/SEVEL_ValveTrain_A3_v002.FCStd`,
com STEP/manifest em `exports/SEVEL_ValveTrain_A3_v002/`. Há 13 capturas novas
e um corte de válvulas em FCStd. O controlador `phase_controller.show(doc)`
foi exercitado: 16 malhas sólidas de mola, poses repetíveis, periodicidade
0/720 sem erro de placement e timer funcional. Doze testes Python passam.

Varredura A3 encerrada: o monitor do host (sessão 56981) confirmou saída do
worker PID 63367 e resultado `PASS_A3_COLLISIONS`. O timeout inicial do MCP
foi apenas de observação; não houve reinício do cálculo. A auditoria no
FreeCAD confirmou igualdade entre as 220 fases concluídas e o alvo recalculado,
21.112 interseções B-rep, 55.952 reaproveitamentos de pares invariantes e zero
colisões acima de 1e-5 mm³. Relatório:
`reports/SEVEL_ValveTrain_A3_v002_valvetrain_cycle.json`.
Seu SHA-256 de origem confere com o FCStd salvo:
`534b40410be51a4cce74396d46540a5f6017eb6991add0928cdd0dee6b3c5766`.
O escopo cobre pares envolvendo A3 e seus contatos com A2; pares somente do
conjunto inferior são cobertos pelo relatório A2. Não há validação de peças
ainda ausentes. GUI saudável, sem tarefa ativa e fase restaurada a zero.

As malhas em `exports/SEVEL_ValveTrain_A3_v002/meshes_v002/` passaram na
releitura, transformação e calibração; `renderer_checks.json` registra a carga
pelo `AuthoredMeshLibrary` e quatro poses no `lab::RecordingRenderer`.
Desvio máximo de caixa frente ao CAD: 0,174213 mm; poses e SVG 0/720 idênticos.
A captura `evidence/SEVEL_ValveTrain_A3_v002-renderer-090.png` foi examinada.
Cinco testes `LabMeshAsset.*` passaram; o pacote original continua carregando.
Essa prova usa o renderizador de registro, não o painel interativo do Lab.
Reprodução contínua e molas deformáveis continuam no controlador FreeCAD.

Checkpoint de topologia A3 v003: 166 sólidos, gaiola contínua com quatro
janelas e seis fixações; 165 componentes preservados. Dimensões aprovadas;
comparação B-rep e envelopes contínuos validam a alteração do corpo fixo
contra o movimento da v002. Não houve nova varredura completa de 220 fases.
Capturas Right/Top/Isometric salvas em `evidence/*v003-cage-review*`.
As fotos de extremidade 649747/833777 evidenciam que a seção retangular e
os planos horizontais atuais ainda não representam a fundição corretamente.
As páginas 00.10 reenviadas conferem com os diâmetros, folgas e eventos
adotados; sete testes do perfil passaram. Detalhes em `VISUAL_REVIEW_A3.md`.

Próximos itens: inclinações e seção transversal da gaiola/cabeçote,
flange recortada inferior, transição curva do bloco, distribuição/volante/roda fônica e pacote final
com suas validações e exportações. A orientação D1..D5
foi corroborada por outro manual, com ressalva em `VISUAL_REVIEW_A3.md`.
Inclinação real das válvulas e transição curva da fundição continuam pendentes.

Checkpoint A4: `models/SEVEL_Flywheel_A4_v001.FCStd`, 174 sólidos válidos,
salvos/reabertos; STEP e manifest em `exports/SEVEL_Flywheel_A4_v001/`.
As oito peças novas giram com o virabrequim. Os 166 componentes herdados
foram comparados por diferença simétrica B-rep. Verificação incremental:
36 pares sem colisão, oito contatos previstos, separação axial contínua
mínima de 11,3 mm e 145 poses corretas. Relatório
`reports/SEVEL_Flywheel_A4_v001_flywheel_validation.json`.
STEP reaberto com 174 sólidos e erro de volume de 0,194 ppm; calibração
de pivô aprovada. Quatro capturas e revisão em `VISUAL_REVIEW_A4.md`.
Doze testes Python passaram. Dimensões e dentição do volante são estimadas;
nenhuma roda fônica foi inferida da cremalheira de partida. Malhas A4 e
distribuição completa continuam pendentes, assim como as correções visuais
da gaiola e do bloco. O objetivo integral permanece em andamento.

Checkpoint atual da distribuição: `models/SEVEL_Timing_A4_v002.FCStd`,
182 sólidos. A v001 tinha suporte do tensor sem contato com o bloco;
v002 corrigida, salva/reaberta e validada. Os 174 componentes anteriores
permanecem idênticos. `*_timing_validation.json` registra 64 pares sem
colisão por envelopes contínuos/posições relativas invariantes e 145 poses
com relações angulares corretas. A correia mantém folga visual de 0,2 mm;
os dentes não são engrenados na geometria lisa da correia.
Controlador FreeCAD aprovado com 16 molas deformáveis, repetição de fases
e período próprio do tensor. Dezesseis testes Python passam.
STEP/manifest em `exports/SEVEL_Timing_A4_v002/`; 182 sólidos reabertos,
erro de volume de 0,182 ppm. Treze novas capturas, incluindo a distribuição.
Detalhes e comparação visual em `VISUAL_REVIEW_A4.md`.
Próximos componentes A4: trecho interno/mancal traseiro do auxiliar,
polia de acessórios, roda fônica e sensor. Permanecem as correções de
inclinação/fundição e as malhas e validações finais da montagem completa.

Checkpoint atual: `models/SEVEL_Trigger_A4_v001.FCStd`, 188 sólidos.
Polia de acessórios, roda fônica, arruela/porca, sensor e suporte adicionados.
Ponta do virabrequim estendida em 17 mm como hipótese de montagem; demais
181 peças herdadas idênticas. Incremento aprovado por 36 pares sem colisão,
145 poses, contatos e folgas contínuas; 58 dentes medidos no CAD. Padrão
60−2 e fase permanecem provisórios; entreferro de 1 mm usa a faixa manual.
STEP e malhas em `exports/SEVEL_Trigger_A4_v001/`; 75 OBJ compartilhados.
As 188 peças passaram no carregador/renderizador, com erro máximo de caixa
de 0,039876 mm. Periodicidade 0/720 aprovada para 187 peças e tensor
conferido pelo período próprio. Regressão A3 e 21 testes Python passaram.
O controlador FreeCAD, as 16 capturas CAD e a imagem do renderizador foram
verificados. Detalhes, fontes e limites em `VISUAL_REVIEW_A4.md`.
O objetivo completo continua ativo: auxiliar interno/traseiro, correções
de fundição/inclinação e consolidação da validação final ainda faltam.

Checkpoint atual: `models/SEVEL_Auxiliary_A4_v002.FCStd`, 189 sólidos.
Eixo auxiliar interno, segundo colo/bucha e passagem no bloco construídos.
186 peças herdadas idênticas; alterações restritas ao eixo e bloco, sem
modificar o datum ou atingir as superfícies dos cilindros. A v001 falhou
por extrapolação radial do loft dos dentes; a v002 corrigida passou.
`*_auxiliary_validation.json`: 220 fases, 58 interseções B-rep, nenhuma
colisão nos pares novos; 145 poses solidárias à polia. Folgas nas buchas
de 0,03425 e 0,030 mm; envelope de rotação a pelo menos 1 mm do bloco.
STEP reaberto com 189 sólidos e erro de volume de 0,173 ppm; controlador
com molas deformáveis e retorno a zero aprovado. Dezesseis capturas e
corte longitudinal salvos/examinados. Os 21 testes Python passam.
Permanecem as correções de inclinação/fundição, os detalhes de interface
explicitamente simplificados e a consolidação das validações finais.

Malhas do auxiliar v002 aprovadas em
`exports/SEVEL_Auxiliary_A4_v002/meshes_v001/`: 189 instâncias, 76 geometrias,
quatro poses no renderizador existente, erro máximo de caixa de 0,039876 mm.
Repetição 0/720 dos 188 componentes compatíveis e transformação independente
do tensor verificadas; PNG da pose 90° examinado. GUI saudável, sem tarefa
pendente, montagem restaurada a 0°. O objetivo integral permanece ativo.

Checkpoint atual: `models/SEVEL_Closures_A5_v001.FCStd`, 198 sólidos.
SHA-256: `7890a81ad99484795718f41b1ca607659acf46be87175c3b6133771f11de0bc8`.
Sobre Casting v002, adiciona tampa oca, junta superior, tampão de óleo,
cárter com flange curva/fundo em dois níveis, junta inferior e bujão.
O catálogo local, código 160.362.1, confirma a identidade do bujão M22×1,5;
as demais dimensões externas permanecem estimativas. 192 peças preservadas.

`closures_v004` aprovado: 220 fases, 1.167 pares, 4.456 testes B-rep,
nenhuma colisão e seis contatos sem lacuna. Corrigidas interferências das
bielas C3/C4 na borda interna e extrapolação do loft da cavidade do cárter.
As seis peças foram reconstruídas, salvas e reabertas. Dimensões, 13
protótipos, 145 poses CAD, curso de 67,4 mm, controlador e 24 testes passaram.

STEP: 198 sólidos, erro relativo de volume 6,79193e-8. OBJ: 198 instâncias,
85 geometrias compartilhadas, calibração e quatro poses aprovadas no
RecordingRenderer; erro máximo de caixa 0,039876 mm. Foram examinadas 13
capturas do ciclo, sete de tampa/cárter/explosão e dois cortes atuais.
Vista explodida: 11 sólidos com translações reversíveis e identidade B-rep
verificada. Ver `VISUAL_REVIEW_CLOSURES.md` e `DELIVERY_AUDIT.md`.

`kinematics_validation.json` consolidado neste checkpoint: 12 relatórios
diretos e 11 estágios auditados; `goal_complete=false`. Pacote portável ainda
histórico; bomba d'água, velas e coletores permanecem como próximos componentes.
Não houve push nem alteração dos originais de fotos/PDFs.
Reconstrução após publicação conferida em processo nativo independente:
seis peças idênticas, usando a prova imutável arquivada do predecessor.

Incremento em validação: `SEVEL_Accessories_A5_v001.FCStd`, 218 sólidos,
SHA `999d32a3f1dedcb6f7965b67b2f77b3a6d28930ebc9aa58d35807efae879acbc`.
Adiciona quatro velas em três regiões cada, duas juntas comuns, coletores
de admissão/escape e quatro peças da bomba d'água. Os 198 sólidos herdados
foram preservados. `accessories_v002` passou 4.150 pares/220 fases e 22
contatos; controlador, dimensões, reconstrução inferior e 24 testes passaram.
Trinta capturas e dois cortes foram examinados; explosão com 11 peças.

Esse incremento ainda NÃO substitui a entrega consolidada Closures v001:
o STEP excedeu o limite de diferença de volume e a exportação OBJ detectou
malhas abertas nos coletores. O ensaio isolado da admissão identificou
cortes cilíndricos redundantes sobre o início dos dutos curvos. Retirá-los
fechou a malha e produziu STEP com erro relativo de volume 1,41884e-8.
A mesma correção localizada foi aplicada ao escape. `run_accessories_trial`
agora exige malha fechada nas 20 peças e round-trip STEP nos dois coletores
antes da varredura de colisões. Trial corretivo `accessories_v004` em execução.

A comparação booleana do coletor contra sua cópia serializada também falhou
no OCCT. `geometry_identity.sampled_equivalence` registra uma alternativa
explícita por topologia, superfícies, bordas, áreas e volume; não declara
identidade B-rep exata. O ensaio rejeitou deslocamento de 0,0001 mm.
O pacote atual permanece histórico; `check_portable_cad.py` foi preparado
para conferir a futura entrega Accessories sem reescrever suas provas.

Correção aprovada em `accessories_v007`: 20 malhas fechadas; erros relativos
do STEP isolado de 1,41884e-8 (admissão) e 1,72704e-9 (escape). O escape
usa tubos analíticos com curvas arredondadas e entradas espaçadas 36 mm,
valor provisório centralizado no manifesto. A união começa pelo coletor
comum; quatro sondas volumétricas de percurso inteiro, recuadas 0,1 mm das
paredes para evitar faces coincidentes, ficaram completamente contidas.
As oito portas ficaram desobstruídas. Novamente 4.150 pares/220 posições,
22 contatos, nenhuma falha. `SEVEL_Accessories_A5_v002` está sendo integrado;
v001 permanece como diagnóstico de uma exportação rejeitada.

Checkpoint validado: `models/SEVEL_Accessories_A5_v002.FCStd`, 218 sólidos.
SHA `2d1b209f4d7e50ce68d80efebff5f6a057929e6ab9f2175439f4021d2ef33e64`.
Parâmetros SHA `4aa58e8e7b79fecc0e9474704ac662ac42ce089d7119a0f54df49c44a6ebe506`.
Reconstrução independente: 198 peças herdadas preservadas; 19 acessórios
por identidade/subtração e admissão por 12.186 amostras de superfície/borda,
erro máximo de 2,93e-13 mm. Treze protótipos móveis, 145 poses, dimensões,
controlador com 16 molas e 24 testes Python aprovados.

STEP completo reaberto: 218 sólidos, erro relativo de volume 6,17834e-8.
Malhas: 218 instâncias/97 geometrias; sete entradas aprovadas no renderer,
incluindo calibração e periodicidade; erro máximo de caixa 0,039876 mm.
Trinta capturas e dois cortes atuais revisados: 22 imagens têm pixels RGB
idênticos às anteriores e dez foram examinadas novamente. Ver
`VISUAL_REVIEW_ACCESSORIES_V002.md` e `*_pixel_comparison.json`.

`kinematics_validation.json`: `PASS_CURRENT_VISUAL_KINEMATICS`, 13 provas
diretas e 12 estágios auditados. A conclusão geral é registrada separadamente
em `reports/final_delivery.json` após os testes do pacote, conforme
`FINAL_DELIVERY_AUDIT.md`. Esse registro posterior prevalece sobre pendências
de empacotamento dos checkpoints históricos.
