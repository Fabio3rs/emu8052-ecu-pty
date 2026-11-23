# Tampa, cárter e vista explodida — Closures A5 v001

Modelo: `build/sevel-cad/models/SEVEL_Closures_A5_v001.FCStd`.
SHA-256: `7890a81ad99484795718f41b1ca607659acf46be87175c3b6133771f11de0bc8`.
Prévia geométrica; dimensões externas e espessuras provisórias.

Foram examinadas as sete capturas de `capture_closures.py` e a vista
isométrica nativa pelo MCP. O PDF original de 426 páginas permanece intacto.
Numeração abaixo: páginas do PDF, incluindo a capa.

| Referência | Observação e alteração | Evidência visual |
|---|---|---|
| Catálogo pp.14–15 e foto `sevel_bloco_15.jpeg` | Tampa separada, corpo alongado, seis orelhas e bocal na extremidade do volante. A tampa preta é uma variante comparativa, não a reprodução da tampa desenhada no catálogo. | `*-cover-Isometric.png`, `*-cover-Bottom.png` |
| Catálogo pp.22–23; fotos do cárter 780830 e 845764 | Flange assimétrica com recuos curvos, cavidade e fundo profundo/raso ligados por transição curva. O contorno compartilha o parâmetro do bloco. | `*-pan-Isometric.png`, `*-pan-Top.png`, `*-pan-Bottom.png` |
| Catálogo p.23, item 03 | Bujão 14325311 listado M22×1,5; o CAD usa cilindro liso Ø22, sem modelar rosca ou especificar furo de fabricação. | `*-pan-Bottom.png` |
| Catálogo pp.14,16,22 | Separação de bloco, junta, cabeçote, junta inferior da gaiola, gaiola, junta superior, tampa e cárter. | `*_Exploded-Isometric.png` |
| Motor montado da foto comparativa | Tampa e cárter completam a silhueta externa; gaiola e nervuras conservam as simplificações anteriores. | `*-closures-Isometric.png` |

Correções P0: a primeira varredura encontrou contato indevido de bielas de
C3/C4 com a borda interna do cárter/junta. A cavidade agora continua o
envelope de passagem já reservado no bloco. O loft interno também foi
corrigido: interpolação curva entre estações desiguais ultrapassava a parede.
Paredes regradas mantêm os contornos curvos transversais sem essa extrapolação.

O candidato `closures_v004` passou nas 220 fases, com 1.167 pares novos,
4.456 testes B-rep, nenhuma colisão e seis contatos de montagem sem lacuna.
As seis peças foram reconstruídas e reabertas; 192 peças herdadas permaneceram
idênticas. A vista explodida contém 11 sólidos, cada um com ID de origem e
translação de apresentação; a transformação inversa restitui a geometria
original com diferença B-rep zero. Ela não prescreve desmontagem real.

Diferenças P2 documentadas: tampa sem nervuras/estampagens OEM; cárter sem
defletores internos, nervuras estampadas e furação detalhada da flange.
Profundidades, posição da transição, espessuras e bocal de óleo são hipóteses.
Não foi calculada capacidade útil de óleo nem verificada vedação física.
O respiro conserva o ângulo provisório; este catálogo não fornece essa cota.

Estado: `REVIEWED_WITH_DOCUMENTED_DIFFERENCES`. Os testes numéricos e a
revisão visual têm escopos separados; esta aprovação não certifica fabricação.

As 13 capturas do ciclo deste checkpoint também foram examinadas:
0°, 90°, 180°, 270°, 359°, 360°, 450°, 540°, 630°, 720°, duas da distribuição
e uma externa. Tampa/cárter são ocultados somente nas vistas do mecanismo.
Os pares de pistões mantêm alturas coincidentes; as bielas inclinam-se com
o moente; 0°/360° mostram o comando em fases diferentes e 0°/720° repetem a
configuração. A vista lateral mantém comando, tensor, auxiliar e virabrequim
no circuito registrado pela p.32 do catálogo. Correia lisa, contagens de
dentes e posição axial continuam hipóteses declaradas. A inspeção visual
complementa as medições de fase e contato; não as substitui.

Os cortes em fase 90° foram salvos, reabertos e examinados: longitudinal
com 181 objetos e transversal de C1 com 26. Mostram tampa oca, cárter oco,
fundo em dois níveis e espaço para a biela. O transversal passa entre os
eixos das válvulas; a ausência delas nesse corte fino não significa peça
ausente da montagem. As galerias de arrefecimento continuam simplificadas.
