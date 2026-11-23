# Trem de válvulas — revisão do checkpoint A3 v002

Modelo: `build/sevel-cad/models/SEVEL_ValveTrain_A3_v002.FCStd`.
Estado: 171 sólidos salvos/reabertos; ciclo de colisões A3 aprovado em 220 fases.
O motor completo e a distribuição ainda não estão entregues.

| Referência e observação | Implementação / limite | Evidência |
|---|---|---|
| Foto 843166: oito conjuntos alinhados, molas e pratos | Oito válvulas com duas molas, guia, prato e duas travas cada; dimensões espaciais estimadas | `SEVEL_ValveTrain_A3_v002-valves-Isometric.png` |
| Foto 833139: pratos de admissão maiores e sequência E-I-I-E-E-I-I-E | Diâmetros escolhidos nas faixas do manual; sequência preservada | Relatório `*_valve_dimensions.json` |
| Manual, página impressa 12: cinco colos de diâmetros diferentes e levantamento 8,8 mm | Eixo contínuo com oito cames sintéticos; perfis medidos no B-rep final | Relatório `*_cam_contact.json`: 1.760 medições em 220 fases |
| Manual, páginas 11–13: tucho copo, calço, guia e molas duplas | Corte evidencia haste dentro da guia, copo sobre a haste, travas no sulco e molas concêntricas | `SEVEL_ValveTrain_A3_v002_ValveSection-Isometric.png` e FCStd correspondente |
| Verificação da v001: molas perderam o deslocamento Z ao receber placement da montagem | Deslocamento preservado na geometria interna; v002 substitui a v001 para revisão | Checagem estática v002: 352 interseções B-rep, nenhuma colisão |
| Verificação da v001: assentos vizinhos se sobrepunham | Parede radial estimada reduzida de 3 para 1,5 mm, mantendo os pratos documentados | Checagem estática v002 |

As vistas do trem isolado e do corte foram efetivamente examinadas por
`get_view`. A captura de 359° foi examinada a partir do PNG salvo. A sequência
inclui 0/90/180/270/359/360/450/540/630/720°, com metadados por imagem.

O erro máximo do suporte do came foi 0,001610 mm. Quando a válvula está
aberta, o afastamento máximo medido entre came e calço foi 0,000459 mm;
a margem mínima até a borda do calço foi 2,364 mm. São limites numéricos
do perfil poligonal adotado, não tolerâncias industriais.

A varredura terminou com `PASS_A3_COLLISIONS`: 21.112 interseções B-rep e
55.952 reutilizações de pares invariantes, sem sobreposições acima de
1e-5 mm³. A lista completa de 220 fases e o hash do FCStd foram auditados;
o worker encerrou normalmente. Esse resultado cobre os pares envolvendo
o trem A3, inclusive contra A2, e não valida geometria ainda não construída.

Limitações: molas sem extremidades retificadas, com pequenos afastamentos
axiais inferiores a 0,02 mm na pose medida; porta-comando simplificado,
sem fundição inferior do cabeçote; ausência de canais, câmaras e dutos.
Os eixos de válvula paralelos a Z são uma hipótese de montagem. A inclinação
real deve ser reconciliada com fotos/medidas antes de afirmar fidelidade do
cabeçote. O controlador usa malhas de arame circular durante a reprodução
e restaura as molas CAD ao fechar; não executa sweeps a cada quadro.

## Orientação dos colos: evidência adicional

O [manual de reparação do Tipo 1991, capítulo 1, página 26](https://manualzz.com/doc/65244504/fiat-tipo-1991-workshop-manual)
identifica o colo menor no extremo da distribuição e o maior junto ao volante.
Isso corrobora a ordem D1→D5 adotada em +X. Trata-se de referência de outra
aplicação/edição, não comprovação dimensional específica do Tipo SPI 82 cv.
Os diâmetros continuam provenientes do manual local do alvo; não se alterou
o datum nem se promoveu a orientação a medição confirmada. A mesma obra
descreve válvulas inclinadas, reforçando o limite da hipótese de eixos paralelos.

O STEP reabriu com 171 sólidos, erro relativo de volume de 0,195 ppm e
calibração com pivô deslocado aprovada. Manifest de IDs, pivôs, eixo do comando
e tipos de válvula/mola acompanha a exportação. Malhas para o visualizador
do repositório continuam pendentes.

## Novas referências fornecidas durante a varredura

Os 14 originais indicados pelo usuário foram examinados diretamente, sem
alterar fotografias ou o checkpoint que está em cálculo. `inventory.py`
registra caminhos, hashes e observações em `reports/moving_sources.json`.
As duplicatas `(1)` de 939442 e 795677 têm bytes idênticos às respectivas
cópias sem sufixo; não contam como vistas independentes.

| Fotos | Diferença observada / ação posterior |
|---|---|
| 726745, 954033 | P1: substituir o porta-comando prismático com cinco capas separadas por gaiola contínua, quatro janelas e pontes integradas. O modelo atual apenas verifica interfaces |
| 621331, 885508 | Modelar a separação entre cabeçote, gaiola e tampa; lado dos dutos tem aberturas em alturas alternadas e nervuras arredondadas |
| 939442, 957036 | Reproduzir cavidades superiores recortadas, bosses das guias e fixações; conferir a inclinação das válvulas com geometria independente |
| 781290, 882668 | Câmaras não são simples cilindros; há paredes curvas, duas sedes e abertura da vela. Usar o comando solto como comparação de silhueta |
| 723789 | Reforça o uso de transições amplas na fundição, sem converter cada relevo em prisma de quinas vivas |
| 745438, 959724, 600896, 946397, 795677 | Conferir proporções da montagem, extremidades, volante e curvas inferiores; o suporte de madeira oculta parte do conjunto |

Os anúncios incluem aplicações Palio/Uno/Elba e uma tampa diferente. São
referências visuais comparativas; não comprovam sozinhos cotas, variante exata,
ângulo do respiro, número de dentes ou fase da roda fônica do Tipo i.e. 82 cv.
A comparação da gaiola exige revisão geométrica após o término da varredura;
o eventual PASS desta versão não provará fidelidade dessa fundição.

## Face comum dos coletores

Na anotação do usuário `codex-clipboard-W4uxtk.png`, sobre a vista do motor
montado correspondente à série 745438, azul identifica os três selos do bloco,
vermelho as quatro saídas de escape e amarelo as quatro entradas de admissão.
A disposição observada é E–A–A–E–E–A–A–E; as entradas de admissão aparecem
mais altas que as saídas de escape. Os dois coletores pertencem à **mesma face**,
acima dos selos: lado +Y na convenção já adotada em `parameters.json`.
Não distribuir admissão e escape em lados opostos ao construir os dutos e
coletores. Essa evidência estabelece disposição e identidade, sem determinar
raios, coordenadas dos centros ou trajetórias internas dos dutos.

Na anotação seguinte, `codex-clipboard-G7YEAg.png`, o usuário identifica em
verde duas passagens de líquido de arrefecimento, uma entre cada par de
entradas de admissão. Segundo sua informação, a versão i.e. possui coletor
de admissão aquecido pela água do motor. Registrar essas interfaces como
passagens de arrefecimento separadas dos quatro dutos de admissão e dos
furos de fixação; preservar sua posição relativa na face comum dos coletores.
A função foi informada pelo usuário; a foto mostra a localização externa,
mas não estabelece diâmetros, profundidades, percurso interno ou sentido
de circulação. Esses dados permanecem desconhecidos até outra evidência.

O usuário preservou a anotação completa no repositório:
[`PhotosMotor/referencia_coletores_selos.png`](../../PhotosMotor/referencia_coletores_selos.png).
Essa é a referência persistente para as quatro cores descritas acima;
`reports/moving_sources.json` registra seu hash e a origem da identificação.

## Malhas e prova no renderizador existente

Pacote: `exports/SEVEL_ValveTrain_A3_v002/meshes_v002/`. São 171 instâncias
e 55 malhas compartilhadas, em metros e com pivôs locais preservados.
As normais suavizam superfícies curvas até 30° e conservam arestas maiores.
`mesh_checks.json` verifica releitura, orientação, fechamento, volumes e
transformações; a diferença máxima de volume aproximado é 1,181%.

O carregador existente `AuthoredMeshLibrary` ganhou `loadAll` para nomes CAD;
o modo original continua exigindo as peças antigas. Os cinco testes
`LabMeshAsset.*` passam, incluindo carga dos assets antigos.
`check_mesh_renderer.cpp` usa esse carregador e `lab::RecordingRenderer`,
mede as 171 peças em 0/90/359/720° e gera SVG. O desvio máximo de caixa
envolvente frente ao CAD é 0,174213 mm (limite de malha: 0,25 mm).
Duas instâncias de calibração com pivô deslocado, rotações compostas e
cores diferentes passaram; poses e SVG de 0/720° são idênticos.

A captura `evidence/SEVEL_ValveTrain_A3_v002-renderer-090.png` foi examinada:
o mecanismo aparece completo em projeção frontal; pares de pistões estão
na mesma altura nessa fase e válvulas abertas/fechadas são distinguíveis.
Foi necessário excluir faces voltadas para trás no adaptador da prévia,
pois suas projeções cancelavam o preenchimento das faces dianteiras no SVG.
O renderizador de registro não resolve profundidade; esta prova não equivale
a integração interativa no painel do Lab. Molas OBJ são poses estáticas;
a reprodução contínua com deformação permanece no controlador FreeCAD.
As novas referências exigem revisão da gaiola e da fundição antes de uma
exportação final; `meshes_v001` é a versão anterior com normais planas.

## Checkpoint v003 e revisão das inclinações

`SEVEL_ValveTrain_A3_v003.FCStd` contém 166 sólidos: uma gaiola contínua
substitui o corpo e as cinco capas anteriores. Quatro janelas e seis orelhas
de fixação estão presentes; os 165 outros componentes foram preservados.
`*_carrier_change.json` registra `PASS_CARRIER_CHANGE_CONTINUOUS_ENVELOPES`:
comparação geométrica com v002 e envelopes contínuos conservadores comprovam
que o material fixo acrescentado não invade o movimento já validado.
Não foi executada outra varredura de 220 fases para v003. O relatório
`*_valve_dimensions.json` passou; nenhum desses resultados aprova a fundição.

As fotos enviadas pelo usuário foram confrontadas com os originais locais:
649747 corresponde à extremidade com flange de água; 833777, à extremidade
com retentor/cubo; 885508, à lateral com tampa; `cabeçote_cima.webp`, à gaiola
aberta com comando. A vista oblíqua enviada como `codex-clipboard-gO7MZa.png`
complementa essas referências. Não há escala angular calibrada nessas fotos.

| Evidência | Diferença observada | Ação / prioridade |
|---|---|---|
| Extremidades 649747 e 833777 | Juntas superior e inferior da gaiola aparecem com inclinações distintas relativamente ao deck; a seção não é retangular | P1: reconstruir separadamente os planos de interface e a seção transversal; não girar toda a montagem como um bloco |
| 885508 e `cabeçote_cima.webp` | Nervuras, paredes e bosses variam de seção; há transições largas e arredondadas | P1: substituir a extrusão uniforme da gaiola por fundição com seções reconciliadas |
| Junta 806433 | Contorno superior arredondado e seis fixações | Gabarito qualitativo do perímetro da interface, sem definir sua orientação no motor |
| Junta 737590 | Reentrâncias curvas em uma borda longitudinal | P1: reconciliar flange inferior; identidade e escala ainda comparativas |
| Junta 980809 | Recuos curvos no contorno do cárter | Preservar a interface de vedação ao revisar a transição tridimensional do bloco |

Capturas reais v003: `evidence/SEVEL_ValveTrain_A3_v003-cage-review-`
`{Right,Top,Isometric}-20261122T234734-0300.png`. As vistas Right e Top foram
também examinadas via `get_view`. A extremidade CAD continua retangular,
com topo/base horizontais: **a correção angular continua pendente**.
As juntas ajudam a determinar curvas no próprio plano de vedação; as fotos
de extremidade ajudam a orientá-lo e a reconstruir a fundição ao redor.
Nenhum ângulo da tampa foi transferido automaticamente aos eixos das válvulas.

## Conferência das páginas 00.10 reenviadas pelo usuário

Os valores nominais existentes foram confrontados com as duas imagens.
O desenho identifica 18 como cabeçote superior/gaiola, 19 como tucho copo,
20 como calço e 14 como válvula. Embora algumas legendas da tabela usem
“válvulas”, os diâmetros próximos de 37 mm nesta página se referem ao
acoplamento tucho/alojamento, não aos pratos das válvulas.

| Grandeza | Manual reenviado | Modelo / interpretação |
|---|---|---|
| Alojamento do tucho | Ø37,000–37,025 mm | Ø37,0125 mm |
| Tucho | Ø36,975–36,995 mm | Ø36,985 mm |
| Folga tucho/alojamento | 0,005–0,050 mm | 0,0275 mm diametral |
| Folga nos mancais do comando | 0,030–0,070 mm | 0,0495–0,0500 mm diametral |
| Calço | 3,25–4,70 mm, passos de 0,05 mm | 3,50 mm escolhido para a prévia |
| Folga para controle do diagrama | 0,80 mm, ambos | `checking_lash_mm=0.8` |
| Folga de funcionamento | Admissão 0,40±0,05; escape 0,50±0,05 mm | Nominais 0,40 e 0,50 mm |
| Admissão A/B | Abre 7° antes do PMS; fecha 35° após o PMI | Fases locais 353°/575° |
| Escape C/D | Abre 37° antes do PMI; fecha 5° após o PMS | Fases locais 143°/365° |

Os eventos usam graus do virabrequim, PMS de compressão do cilindro em 0°,
e folga de controle. Duração de cada evento: 222°; cruzamento de controle:
12°. O levantamento em funcionamento usa a folga própria de cada válvula,
portanto seus pontos de abertura/fechamento diferem dos eventos de controle.
Sete testes de `test_cam_profile.py` passaram na reconferência. As páginas
não fornecem a inclinação física da gaiola, tampa ou eixos de válvula, nem
o perfil completo do came; este continua sintético e identificado como tal.

## Seção inclinada — SEVEL_Carrier_A3_v001

Checkpoint derivado de `SEVEL_Auxiliary_A4_v002`, com 189 sólidos. Apenas
`CamCarrier` mudou; 188 peças preservadas por comparação B-rep. O relatório
`reports/SEVEL_Carrier_A3_v001_carrier_validation.json` aprova a mudança
contra 98 envelopes contínuos e 90 separações espaciais. Cinco superfícies
de apoio do comando e oito alojamentos de tucho foram conferidos no sólido.
O prolongamento da polia do comando tem envelope próprio, pois alcança a
interface da gaiola. Não houve nova varredura completa de pares herdados.

| Referência → observação | Mudança e captura | Limite / prioridade restante |
|---|---|---|
| Fotos 649747/833777: juntas em planos diferentes | Seção trapezoidal, topo +22° e base −12° em função de +Y; `*-carrier-Right.png` | P1: ângulos escolhidos para prévia, não medidos; eixos mecânicos preservados |
| Junta 737590 e catálogo 10101, PDF 14–15: interface inferior recortada | Três reentrâncias curvas na faixa inferior; `*-carrier-Bottom.png` | P1: recortes ainda simplificados; lado −Y e raios provisórios, sem ajuste métrico ao contorno completo |
| Fotos 726745/954033: quatro janelas, paredes contínuas e seis fixações | Janelas e fixações mantidas sobre seção inclinada; `*-carrier-Isometric.png` | P1: paredes ainda uniformes longitudinalmente; bosses e nervuras reais não reconciliados |
| Catálogo 10107, PDF 36–38: comando e oito conjuntos de válvulas | `*-valvetrain-Isometric.png`, com interfaces preservadas | Inclinação das válvulas independente dos planos externos e ainda desconhecida |

Prefixo das quatro capturas: `evidence/SEVEL_Carrier_A3_v001`.
A vista isométrica foi examinada via `get_view`; arquivos Right, Bottom e
valvetrain também foram abertos e examinados. Há 13 capturas adicionais
de poses/distribuição/exterior. O teste real do controlador aprovou 16
molas, periodicidade compatível de 720° com erro zero e período próprio
do tensor; atualização máxima observada 0,158 s. Vinte e um testes Python
passaram. Isso valida a geometria construída e seu movimento, não a
fidelidade dimensional da fundição. Cabeçote inferior e transição curva
do bloco permanecem pendentes.

Exportação em `exports/SEVEL_Carrier_A3_v001/`: STEP reaberto com 189
sólidos e erro de volume de 0,161 ppm; `meshes_v001` contém 76 geometrias
OBJ compartilhadas por 189 peças. O RecordingRenderer existente aprovou
0°, 90°, 359° e 720°, com desvio máximo de caixa de 0,039876 mm.
O tensor tem seu período próprio verificado separadamente. As poses/SVG
dos demais componentes compatíveis coincidem em 0°/720°; essa prova não
substitui reprodução interativa no Lab. Os hashes apontam para o FCStd
salvo, SHA-256 `66e07706301ff57acc8d46303715d4a4b62a97e169426a550119193edea1da0f`.
