# Cabeçote SEVEL e NGK BCPR5ES

Revisão da montagem `SEVEL_Accessories_A5_v002.FCStd` pelo FreeCAD MCP.
O modelo revisado está em `build/sevel-cad/models/SEVEL_Accessories_A5_v003_SparkReview.FCStd`.
O datum conserva a classificação `PASS_PROVISIONAL_FOR_VISUAL_ONLY`.

| Referência em PhotosMotor | Comparação com o CAD |
|---|---|
| 870987, 723789, 885508, 939231 e 714275 | A face recua entre as cinco nervuras e avança na borda inferior. O poço tem boca circular e assento plano. A fundição real tem raios diferentes em cada vão e pequenos ressaltos com furos junto às velas. O CAD ainda simplifica esses detalhes. |
| BCPR5ES61UgZsbZz6L.jpg, BCPR5ESD, 787543 e 958845 | Terminal com cintura, cinco nervuras arredondadas no isolador, sextavado, arruela, rosca externa helicoidal e eletrodo de massa dobrado. Os contornos do terminal, da cerâmica e dos eletrodos são estimativas visuais. |
| 704878 e 844000 | A extremidade de ignição aparece na borda da câmara, entre as válvulas. O contorno da câmara na foto 704878 é mais assimétrico que no modelo. |

| Cota axial ou transversal | Valor no CAD | Origem |
|---|---:|---|
| Rosca externa, alcance e sextavado entre faces | M14 × 1,25 / 19 / 16 mm | Especificação BCPR5ES fornecida para esta revisão |
| Folga entre as faces dos eletrodos | 0,8 mm | Aplicação Tipo informada pelo usuário, conferida nos quatro sólidos montados |
| Assento até o terminal | 53 mm | Estimativa externa fornecida |
| Boca do rebaixo até a arruela | 5 mm | Estimativa do usuário a partir das fotos |
| Arruela até a primeira interseção do eixo com a câmara | 19,5 mm | Hipótese de montagem aplicada à câmara existente |
| Inclinação para dentro da câmara | 18,8° abaixo do plano do deck | Eixo herdado da montagem v002 |
| Avanço do eletrodo central a partir da parede | 3,3 mm | Resultado axial no CAD. A extremidade da rosca fica 0,5 mm antes da parede no eixo. |

O modelo representa a rosca fêmea pelo diâmetro nominal. Na posição de 0°,
os quatro assentos apoiam toda a faixa verificada da arruela. As peças das
velas têm volume de interseção abaixo de 0,00001 mm³ com o cabeçote, a junta,
os pistões e as válvulas. A menor distância entre o corte do poço e a cavidade
de água simplificada é 0,98 mm. A espessura real nessa região continua desconhecida.

O FCStd reaberto contém 218 peças com B-rep válido e um sólido por peça.
Para reproduzir a partir da v002, executar `build_spark_review.run()` com
`cad/sevel16` no caminho Python do FreeCAD e o destino livre. As capturas
`SparkReview_comparacao.png` e `SparkReview_section.png` ficam em
`build/sevel-cad/reports/`. A primeira vela foi ocultada apenas na vista
comparativa da face externa, para expor o alojamento como na foto 870987.
