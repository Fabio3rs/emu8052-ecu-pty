# Fiat Tipo 1.6 SPI · Coletores de admissão e escape

A revisão v005 parte da montagem v004 do bloco e da PCV. A prancha reúne a peça fotografada e as duas versões CAD. As colunas CAD usam a mesma câmera para cada peça. A orientação das fotografias é aproximada. [Comparação](../../build/sevel-cad/reports/ManifoldReview_comparacao.jpg) · [Motor montado](../../build/sevel-cad/reports/ManifoldReview_montagem.png)

| Peça | Referências visuais | Alteração verificada |
| --- | --- | --- |
| Admissão 7745124 | Fotos 713001 e 628178, vistas superiores. Fotos 807385 e 909298, bocas no cabeçote. Foto 927431, face inferior. | Quatro dutos chegam à câmara central por dois lados. A fundição forma o U frontal, com braços largos, mesa recortada para o corpo de borboleta, nervuras inferiores e ressaltos para conexões. |
| Escape 7691880 | Fotos 859499 e 881888, disposição dos ramos. Fotos 626156 e 670103, fundição dos ramos centrais. Fotos 998081 e 812541, face da saída. | Os ramos externos convergem para uma boca e os internos para a outra. A faixa fundida une o par central. A flange inferior alongada tem duas passagens e quatro prisioneiros independentes. |

O grupo 10254 identifica os dois coletores, as juntas e os quatro prisioneiros M8×12×25 na saída do escape. A disposição das bocas na flange foi reconstruída pelas fotos da própria peça. [Catálogo, páginas 67–70](<../../PhotosMotor/Tipo 1.6 - Tipo 1.6 4P 1.6 SPI 8V Gasolina 1993-1995.pdf>)

## Verificação no FreeCAD

- A montagem salva reabriu com 224 sólidos válidos. Os coletores passaram pela verificação de geometria com BOPCheck. As duas fundições e os quatro prisioneiros passaram na verificação de interferência com as peças vizinhas.
- Foram verificadas as oito bocas do cabeçote, os anéis de apoio, as duas entradas de água, a abertura superior de admissão e a divisória do escape. Ao tampar provisoriamente as bocas, cada coletor apresentou duas cavidades fechadas. Na admissão correspondem ao ar e à água. No escape correspondem aos dois pares de cilindros.
- A distância mínima calculada entre as superfícies dos coletores montados é de 0,65 mm. Os contornos e alturas das fundições, as galerias internas e essa folga são estimativas do modelo. O gabarito mestre mantém a classificação `PASS_PROVISIONAL_FOR_VISUAL_ONLY`.
- A principal diferença visual restante está na admissão. A peça fotografada tem uma transição mais contínua entre os braços e o corpo central. Os ressaltos das conexões foram representados na fundição. Os sensores e os terminais de mangueira visíveis na foto 713001 são acessórios separados.

O gerador usa a v004 como entrada e lê as cotas estimadas em `manifold_photo_review_estimated`. [Gerador e validação](build_manifold_review.py) · [Parâmetros](../../build/sevel-cad/parameters.json) · [Montagem v005](../../build/sevel-cad/models/SEVEL_Accessories_A5_v005_ManifoldReview.FCStd)
