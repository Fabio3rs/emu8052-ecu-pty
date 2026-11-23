# Motor montado e bocal da PCV

Montagem `SEVEL_Accessories_A5_v004_BlockReview.FCStd`, derivada da revisão
v003 das velas. Datum `PASS_PROVISIONAL_FOR_VISUAL_ONLY`. O arquivo abre com
as 220 peças visíveis. Nas imagens de comparação, velas e coletores foram
ocultados para aproximar a configuração das fotografias.

| Fotos em PhotosMotor | Observação e decisão |
|---|---|
| 946397, 600896 e 699233 | As duas vistas de viés e a vista frontal mostram uma parede saliente desde o suporte da distribuição até a base da PCV e a face do filtro. A fundição da v004 cobre essa área acima e abaixo do eixo auxiliar. |
| 702072 e 812345 | O bloco nu permite distinguir o anel do filtro, os pontos de fixação e a abertura do respiro. A transição para a parte traseira e os ressaltos de fixação continuam simplificados. |
| 946397, 699233, F9Lhc e KpWw | O bocal prateado identificado pelo usuário pertence à ventilação positiva do cárter. A tampa tem tubo aberto, deslocado do centro, com uma pequena inclinação. No CAD ela é uma peça removível. |
| 745438, 795677 e 959724 | Na face oposta reconhecem-se os três selos e a posição do volante. As nervuras dessa face têm contorno mais regular no CAD. As fotos mostram a capa da distribuição, ausente nesta montagem. As duas cópias de 795677 têm o mesmo SHA-256. |

O eixo do tubo da PCV forma **15° com a vertical**. A normal à face de apoio
forma **18° com a vertical**. Ambos apontam para fora, no sentido −Y. O
alojamento anterior usava 45°. Os dois novos ângulos, os contornos da fundição
e as dimensões do espigão são hipóteses visuais (`ASSUMPTION`). A perspectiva
e a falta de uma vista ortogonal calibrada limitam sua determinação. O espigão
do filtro tem representação lisa. A passagem verificada conecta o tubo à boca
existente do bloco; o circuito de ventilação interno está fora desta revisão.

| Ponto no bloco, X e Z em mm | Face anterior Y, v003 | Face anterior Y, v004 | Avanço para fora |
|---|---:|---:|---:|
| 20, −70 | −65,0 | −98,6 | 33,6 mm |
| 20, −154 | −96,4 | −106,0 | 9,6 mm |
| 82, −190 | −76,6 | −91,1 | 14,5 mm |

Os valores são interseções de retas paralelas a Y com os sólidos CAD.
No FCStd reaberto, cada peça tem um sólido B-rep válido. A faixa anular
verificada da PCV está apoiada; a passagem e o tubo estão livres. A tampa
e o espigão encostam no bloco e o teste estático a 0° encontrou volume
comum inferior a 0,00001 mm³ com as peças próximas. O eixo auxiliar gira
na simulação herdada; nesta revisão foram verificados o eixo e as duas
buchas na pose salva.

Gerador da montagem em `build_block_pcv_review.run()`, a partir da v003 e
com o destino livre. Prancha em `build/sevel-cad/reports/BlockReview_comparacao.jpg`.
