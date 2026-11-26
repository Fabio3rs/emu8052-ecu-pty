# SEVEL 1.6 · Alinhamento entre cabeçote, junta e bloco

A [revisão v011](VISUAL_REVIEW_HEAD_MAIN_ROW_V011.md) corrige a fileira principal do lado das velas e registra a identificação fotográfica da alimentação de óleo.

## Orientação pelas galerias

Nas duas fotos do bloco, as duas janelas alongadas entre pares de cilindros identificam uma borda longitudinal da junta. O rasgo isolado na borda oposta identifica a extremidade da roda dentada (−X no CAD). Assim é possível comparar a vista superior do bloco à vista inferior do cabeçote levando em conta a inversão entre as faces. A identificação individual da alimentação de óleo e do retorno continua pendente. [Sobreposição da junta nas duas fotos](../../build/sevel-cad/reviews/head-v010/junta-sobre-blocos.png)

A projeção em cada foto usa sete referências marcadas à mão, os centros dos quatro cilindros e das três aberturas assimétricas. Os quatro furos pequenos servem de verificação independente. A distância entre cada centro previsto pela junta e o centro observado ficou entre 0,9 e 3,2 pixels na foto de 1200 × 750 e entre 0,3 e 1,9 pixels na de 500 × 500. Para passar ao CAD, a escala vem dos 282 mm provisórios entre os cilindros extremos do modelo. Na primeira junta o centro de um cilindro intermediário diverge em até 2,4 mm. [Pontos e resíduos por foto](../../build/sevel-cad/reviews/head-v010/registro-blocos.json) · [Duas juntas comparadas ao CAD](../../build/sevel-cad/reviews/head-v010/registro-juntas.png)

## Furações e ressaltos

| Elemento | Resultado da revisão |
|---|---|
| Quatro fixações pequenas junto às velas | Os centros acompanham as juntas e alternam de lado. Em X, os deslocamentos em relação aos centros C1–C4 são +10, −12, +10 e −12 mm. Em Y, ficam a −61, −61, −62 e −62 mm da linha dos cilindros. São estimativas fotográficas arredondadas. |
| Altura e continuidade | O plano de apoio dos quatro ressaltos passou de Z = 19 para Z = 10 mm em relação ao topo do bloco. A altura foi estimada pela vista lateral. No CAD, os furos são normais à face, atravessam cabeçote e junta e encontram um piloto de 5 mm no bloco. Diâmetros, profundidade e rosca reais aguardam medição. |
| Dez fixações principais M10 | Seus eixos coincidem nas três peças do CAD. Na junta, os três centros intermediários do lado das velas projetam-se 21–23 mm mais perto da linha dos cilindros. No plano atual dos assentos (Z = 62 mm), uma coroa de ensaio com raios 5,6 e 9,5 mm tem 0% de apoio nessas três posições. A correção requer remodelar as colunas e conferir a distância transversal entre fileiras. |
| Quatro velas | Cada ponta no CAD chega à respectiva câmara. Os 18,78° com o plano da junta descrevem o modelo. A foto das câmaras indica o lado da entrada, mas a inclinação e a profundidade reais ainda precisam de medida. |

O catálogo do Tipo 1.6, pp. 12–13, lista cinco M10 × 99, cinco M10 × 84 e, separadamente, quatro fixadores 7771474 com quatro arruelas D8 × 15. A dimensão da arruela, sozinha, não estabelece a rosca do fixador. [Catálogo](../../PhotosMotor/Tipo%201.6%20-%20Tipo%201.6%204P%201.6%20SPI%208V%20Gasolina%201993-1995.pdf) · [Conferência dos eixos e das velas](../../build/sevel-cad/reviews/head-v010/alignment-checks.json) · [Apoio nas posições candidatas](../../build/sevel-cad/reviews/head-v010/major-lands.json)

## Comparações visuais

- [Cinco fixações principais e quatro pequenas na mesma lateral](../../build/sevel-cad/reviews/head-v010/cinco-quatro.png). Na captura superior da v010 os cinco eixos principais desta lateral estão em Y = −61 mm. Dois pequenos estão nessa mesma linha e dois a apenas 1 mm dela. Na foto da junta anotada, os quatro pequenos ficam junto à borda, ladeando as duas janelas largas. Os cinco principais ficam mais para dentro. Os dois das pontas ficam mais perto da borda que os três intermediários. A foto do cabeçote mostra ainda a diferença de altura entre os respectivos assentos. Para a correção, usar as coordenadas individuais no plano da junta e verificar separadamente a altura das cinco colunas.
- [Face das velas, foto e FreeCAD](../../build/sevel-cad/reviews/head-v010/lateral-cabecote-lado-a-lado.jpg) e [comparação dos ressaltos na v009 e na v010](../../build/sevel-cad/reviews/head-v010/comparacao-velas.jpg).
- [Face superior do bloco, foto e FreeCAD](../../build/sevel-cad/reviews/head-v010/bloco-face-lado-a-lado.jpg) e [junta em planta, foto e FreeCAD](../../build/sevel-cad/reviews/head-v010/junta-planta-lado-a-lado.jpg).
- [Extremidade da termostática e bocal de óleo, foto e FreeCAD](../../build/sevel-cad/reviews/head-v010/flange-extremidade-lado-a-lado.jpg).

Na lateral, o CAD tem quatro rebaixos largos e arredondados em volta das velas. A foto 885508 mostra superfícies menores e mais planas ao redor das bocas, entre colunas de fundição que se alargam em direção à base. Ao revisar as colunas M10, convém reproduzir também essas transições e a borda inferior ondulada. Na extremidade 649747, o bocal tem uma borda mais saliente e nervuras mais visíveis sob a boca. Na planta, a junta do CAD ainda apresenta rasgos retangulares repetidos onde a foto mostra janelas assimétricas. Esses contornos permanecem pendentes.

Quando houver acesso à peça, as medidas mais úteis serão a distância centro a centro de dois M10 opostos na estação central e a altura de um ressalto pequeno em relação ao plano de junta. Uma foto perpendicular com a régua apoiada no mesmo plano ajudará a conferir a escala. [Modelo FreeCAD v010](../../build/sevel-cad/models/SEVEL_Accessories_A5_v010_HeadAlignment.FCStd)

## Exportação e simulador

O STEP reimportado contém 231 sólidos válidos. O simulador gráfico executado pelo Native Lab MCP carregou 231 peças e 112 malhas. As vistas do cabeçote e do conjunto chegaram ao tick 1.200.000 a 871,17 rpm, com os mesmos identificadores de estado e eventos e os mesmos cinco diagnósticos IRET do ensaio v009. A captura do cabeçote usou SDL offscreen e Vulkan com o ICD Lavapipe. [Teste do STEP](../../build/sevel-cad/runtime_exports/SEVEL_Accessories_A5_v010_HeadAlignment/v001/geometry/export_checks.json) · [Cabeçote no simulador](../../build/sevel-cad/reviews/head-v010/lab-v010-cabecote-gpu.png) · [Motor no simulador](../../build/sevel-cad/reviews/head-v010/lab-v010-conjunto-gpu.png) · [Log do ensaio](../../build/sevel-cad/reviews/head-v010/lab-v010-cabecote.log)
