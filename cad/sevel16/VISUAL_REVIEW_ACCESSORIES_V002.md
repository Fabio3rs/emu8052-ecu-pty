# Revisão — Accessories A5 v002

Modelo: `build/sevel-cad/models/SEVEL_Accessories_A5_v002.FCStd`.
SHA-256: `2d1b209f4d7e50ce68d80efebff5f6a057929e6ab9f2175439f4021d2ef33e64`.
Estado: `REVIEWED_WITH_DOCUMENTED_DIFFERENCES`.

As fontes e limitações de `VISUAL_REVIEW_ACCESSORIES.md` continuam aplicáveis:
catálogo local 160.362.1, PDF67–70/89–90, fotos do cabeçote/motor e anotação
`PhotosMotor/referencia_coletores_selos.png`. A geometria exterior é aproximada.

## Correções e nova inspeção

P0: retirados cortes redundantes nas entradas da admissão. A malha agora
fecha e o STEP isolado mantém volume com erro relativo de 1,41884e-8.
P0: escape refeito com cilindros e curvas esféricas, entradas espaçadas
36 mm (parâmetro provisório) e união iniciada pelo coletor comum. Isso evita
a alteração de superfícies no STEP e a perda de um ramo na união anterior.
Quatro sondas de percurso inteiro, com margem radial de verificação de
0,1 mm, ficaram contidas; as quatro portas de escape estão livres. Malha
fechada e erro relativo STEP de 1,72704e-9. Trial `accessories_v007` aprovado.

Foram examinadas as imagens v002 de coletores em Isometric/Back, escape
em Front, admissão em Bottom, montagem em Isometric/Back/Left e ambos os
cortes. O escape mostra quatro ramos separados ligados à saída inferior;
a admissão conserva as duas interfaces e o circuito separado de aquecimento.
Na lateral vê-se a polia da bomba fora do circuito da correia dentada.
Os cortes mantêm a conexão biela/pino/pistão e a ponta da vela na câmara.

`*_pixel_comparison.json` compara as 32 imagens com v001: 22 têm pixels RGB
idênticos às imagens já examinadas, apesar de novos metadados PNG. São as
dez poses do mecanismo, duas vistas da distribuição, cinco vistas isoladas
de tampa/cárter, duas da bomba, duas da vela e a vista explodida. As dez
imagens restantes foram inspecionadas novamente. O painel voltou a 0°.

## Diferenças documentadas

P1: o escape tem curvas segmentadas arredondadas e coletor mais largo; é
um volume visual simplificado, sem alegação de reprodução da fundição OEM.
P1: permanecem o plenum tubular, a carcaça simplificada da bomba e o alcance
interno provisório das velas. P2: fixadores finos, roscas e estampagens
continuam omitidos. A bomba é estática; sua relação de acionamento é desconhecida.

O respiro mantém inclinação provisória. As câmaras, galerias, nervuras e
planos externos conservam os limites registrados anteriormente. A verificação
de reconstrução informa separadamente qualquer comparação por amostragem;
essas verificações numéricas não constituem tolerâncias de fabricação.
