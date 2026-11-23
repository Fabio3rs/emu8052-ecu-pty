# Revisão visual — conjunto inferior

Escopo: `SEVEL_Moving_A2_v003`, com geometria provisória onde faltam cotas.
Não constitui revisão do motor completo: cabeçote, válvulas, molas,
distribuição, volante e roda fônica ainda não estão nesta montagem.

| Referência → observação | Prioridade / ação | Evidência CAD |
|---|---|---|
| 707064 / 683381: cinco colos, quatro moentes alternados e contrapesos predominantes nas extremidades e junto ao centro | A1 implementado; comprimentos axiais e contorno dos contrapesos estimados. Não há balanceamento físico | `A1_v002-crank-Isometric.png`, `A1_v002-crank-Front.png` |
| 994280: três canaletas, saia aberta, bosses do pino, coroa rebaixada com duas cavidades | A2 implementado. As cavidades são circulares simplificadas; a foto tem contorno mais próximo de segmentos. P1: refinar essa forma após definir interfaces das válvulas | `SEVEL_Moving_A2_v003-piston-rod-Isometric.png` |
| 760527: haste rebaixada, cabeça bipartida, bucha no pé e dois fixadores | A2 implementado com peças separadas. P1: arredondar bosses e transições da haste; a prévia conserva cantos mais retos que a foto | `SEVEL_Moving_A2_v003-piston-rod-Right.png` |
| Anéis em posições angulares distintas | Reconstrução revelou perda da rotação local na v002; corrigida na v003 por uma raiz geométrica de placement identidade | Relatório `SEVEL_Moving_A2_v003_rebuild.json`: diferença simétrica zero para todos os protótipos |
| Foto do bloco/junta: contorno de vedação com dois recuos curvos | Face planar conservada e conferida no B-rep; a nova parede acima dela é mais larga para permitir o giro das bielas | `SEVEL_Moving_A2_v003_dimensions.json` |
| Correção do usuário: a parede do bloco ao longo da marca verde na colagem também é bastante curva, com poucas quinas de 90° | P1 pendente: reconstruir a transição volumétrica arredondada da lateral até a flange; o contorno curvo da junta, sozinho, não comprova essa forma | Colagem `codex-clipboard-eCRTsy.png`; observação visual qualitativa, sem raio medido |
| Fundição inferior existente era estreita para as cabeças das bielas | Revisão estimada da montagem; **a nova largura externa não foi confirmada por fotografia calibrada**. P1: medir bloco/biela e revisar o abaulamento | `SEVEL_Moving_A2_v003-external-Isometric.png`, `SEVEL_Moving_A2_v003-external-Bottom.png` |
| Conexão mecânica e folgas em corte | Pino dentro da bucha; biela inclinada sem deslocar o eixo do pistão; casquilhos distinguíveis; cavidade livre na pose de 90° | Cortes longitudinal e transversal C1, ambos em 90° |

As fotografias têm perspectiva e escala desconhecidas. Não foi aplicada uma
métrica de semelhança de pixels como prova dimensional.

Critério para a região verde: comparar a lateral e uma vista oblíqua, verificando
o abaulamento e a continuidade visual entre as superfícies. Não reduzir a
correção a um chanfro ou a um pequeno filete sobre uma parede prismática.
Preservar o plano de vedação e seu contorno; raios e extensão da transição
continuam provisórios até haver medidas. Esta anotação não altera a geometria.

As vistas da v002 foram examinadas via `get_view` em Isometric, Front e Right,
incluindo ambos os cortes. As capturas da v003 documentam a correção dos anéis;
os JSONs registram documento, câmera e ângulo para impedir confusão entre abas.
A montagem v003 também foi examinada por `get_view(Isometric)` após a correção;
o FCStd foi reaberto com 68 sólidos válidos e pose inicial zero.

O teste anterior de flange baseado em uma fatia de 0,1 mm não se aplica à
nova parede, que se alarga acima do plano de vedação. A validação atual usa
as faces planas reais em Z=-218 mm: área fora do contorno e distância dos
segmentos da borda, com limiar numérico de 1e-6. Não é tolerância industrial.

Lacunas visuais conservadas: furos de óleo e filetes do virabrequim, drenos
do pistão, travas do pino, conjunto de óleo multiparte, fixadores das capas
principais e correspondência fotográfica do novo abaulamento da fundição.
