# SEVEL 1.6 · As cinco fixações do lado das velas

Na v011, as cinco colunas M10 avançam em direção aos cilindros. Os quatro assentos pequenos ficam na borda da fundição. A fotografia da junta mostra os dois M10 das extremidades mais próximos dessa borda que os três intermediários. A montagem compara as duas versões do cabeçote na mesma vista superior. [Comparação v010, v011 e junta](../../build/sevel-cad/reviews/head-v011/comparacao-fileiras.png) · [Vista lateral da peça e do CAD](../../build/sevel-cad/reviews/head-v011/comparacao-lateral.png)

| Posição a partir da distribuição | X no CAD (mm) | Y no CAD (mm) | Deslocamento transversal para dentro desde a v010 (mm) |
|---|---:|---:|---:|
| Extremidade da distribuição | −41 | −45 | 16 |
| Entre C1 e C2 | 45 | −38 | 23 |
| Entre C2 e C3 | 140 | −39 | 22 |
| Entre C3 e C4 | 235 | −39 | 22 |
| Extremidade da termostática | 322 | −46 | 15 |

O gerador calcula a média das duas juntas registradas sobre o datum dos cilindros e arredonda os centros ao milímetro. A origem fica no centro de C1 sobre o bloco, com X crescendo até C4. As posições são estimativas para o modelo visual. O plano dos cinco assentos segue em Z = 62 mm e a profundidade representada no bloco é de 24 mm, ambas herdadas do modelo anterior. A confirmação dimensional depende de uma medida transversal entre centros na peça. [Gerador](build_head_main_row.py) · [Registro fotográfico](head_fixing_alignment.py)

Fechei os furos antigos e reposicionei os cinco eixos nas três peças. Remodelei as colunas e abri espaço acima dos assentos. No arquivo reaberto, os testes verificaram a passagem de cada eixo, a parede em toda a profundidade, o apoio anular até um raio de 9,5 mm e as quatro fixações pequenas. A verificação do conjunto comparou 253 pares candidatos a interferência na posição salva. [FreeCAD v011](../../build/sevel-cad/models/SEVEL_Accessories_A5_v011_HeadMainRow.FCStd) · [Eixos por peça](../../build/sevel-cad/reviews/head-v011/furo-principal.json) · [Verificações do conjunto](../../build/sevel-cad/reviews/head-v011/validation.json)

## Identificação da passagem de óleo

Na junta com cordão vermelho, o pequeno furo na borda entre C2 e C3 tem um aro metálico próprio e é circundado pelo cordão. O proprietário o identifica como alimentação de óleo pressurizado e informa 4 bar. A mesma foto mostra os aros de esmagamento dos quatro cilindros. A sobreposição indica separadamente os cinco eixos principais e os quatro pequenos. A identificação do retorno e o trajeto interno do óleo continuam pendentes. [Detalhe da alimentação e do aro do cilindro](../../build/sevel-cad/reviews/head-v011/alimentacao-oleo.jpg) · [Nove fixações sobre a junta](../../build/sevel-cad/reviews/head-v011/junta-vedacao.png)

O manual do Tipo 1.6 SPI, página impressa 16 (página 18 do PDF), especifica a pressão de funcionamento do circuito de lubrificação a 100 °C. A tabela traz mais de 1,5 bar em regime mínimo e 4,6 bar a 4.000 rpm. A pressão local na passagem da junta ainda carece de medição. [Manual do Tipo 1.6 SPI](../../PhotosECU/OCR_03-1.Tipo%201.6%20SPI.pdf)

## Ensaio da v011

O STEP reimportado no OpenCascade contém 231 sólidos válidos. No Native Lab MCP, o simulador gráfico carregou 231 peças e 112 malhas, e capturou o cabeçote isolado e o motor montado em Vulkan offscreen. As duas execuções chegaram ao tick 1.200.000 com os mesmos hashes de estado e eventos e os mesmos cinco diagnósticos IRET do ensaio v010. [STEP da montagem](../../build/sevel-cad/runtime_exports/SEVEL_Accessories_A5_v011_HeadMainRow/v001/geometry/assembly.step) · [Cabeçote no simulador](../../build/sevel-cad/reviews/head-v011/lab-v011-cabecote-gpu.png) · [Montagem no simulador](../../build/sevel-cad/reviews/head-v011/lab-v011-conjunto-gpu.png) · [Log](../../build/sevel-cad/reviews/head-v011/lab-v011-cabecote.log)
