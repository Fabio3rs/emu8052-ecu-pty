# SEVEL 1.6 8V · Revisão externa A5 v008

O arquivo reúne o motor em fase 0°, com quatro peças revistas e sete acrescentadas à v007. O cartucho branco é o filtro de óleo identificado pelo proprietário nas duas vistas do bloco. Ele aparece na árvore do FreeCAD como `OilFilterCartridge`, separado do espigão e do respiro. [Modelo FreeCAD](../../build/sevel-cad/models/SEVEL_Accessories_A5_v008_HeadExterior.FCStd) · [Motor montado](../../build/sevel-cad/reviews/head-v008/assembled-v008.png)

## Cartucho do filtro de óleo

Na foto F9Lhc, a extremidade fechada se projeta diante da face da distribuição. Na KpWw4, o corpo encurta em perspectiva e aparece abaixo e ao lado do respiro. O apoio circular e o espigão da v007 localizam o eixo no CAD. O cartucho novo tem corpo cilíndrico, borda enrolada junto ao apoio e extremidade fechada com raio de transição. A montagem fica em contato com o bloco. A largura da borda, o diâmetro máximo de 70 mm e a projeção de 129,5 mm são escolhas de modelagem feitas sem escala. Para confirmar as duas últimas cotas, basta identificar o código do filtro ou medir diâmetro e comprimento da peça avulsa. [Vista de três quartos](../../build/sevel-cad/reviews/head-v008/filter-v008.jpg) · [Vista lateral](../../build/sevel-cad/reviews/head-v008/filter-side-v008.jpg)

## Cabeçote e acessórios

Cada prancha mostra duas fotos e, abaixo, a v007 e a v008 com a mesma câmera e a mesma seleção de peças.

| Região | Alteração e leitura da comparação |
|---|---|
| Face das velas | Quatro recuos de perfis diferentes, cinco pés alargados e quatro pequenos ressaltos perfurados. As colunas da peça fotografada ainda se destacam mais junto à base. Os quatro assentos anulares das velas mantêm apoio integral no CAD. [Comparação](../../build/sevel-cad/reviews/head-v008/plugs-v008.jpg) |
| Face dos coletores | As nervuras da gaiola recuam e mudam de largura em direção à flange. A vista com os coletores ocultos mostra que a parede entre nervuras continua mais plana que a fundição real. As oito bocas de gases e as duas de água mantêm o perfil local da v007 no plano usinado. [Comparação](../../build/sevel-cad/reviews/head-v008/ports-v008.jpg) |
| Flange da termostática | O contorno segue a foto 649747, com teto arredondado, entalhe inferior, lobo direito mais profundo e orelhas em alturas diferentes. A linha que une os centros desce 6,31° na imagem. O modelo conserva o entrecentros provisório de 62 mm e os eixos dos furos perpendiculares à flange. [Comparação](../../build/sevel-cad/reviews/head-v008/end-v008.jpg) |
| Extremidades do comando | A ponta sobre a termostática ganhou face usinada, três furos e abertura oblonga sob o fechamento circular. A ponta da distribuição ganhou um anel escalonado menor e uma transição própria para a gaiola. [Lado da termostática](../../build/sevel-cad/reviews/head-v008/end-v008.jpg) · [Lado da distribuição](../../build/sevel-cad/reviews/head-v008/timing-v008.jpg) |
| Tampa e abastecimento de óleo | As extremidades têm relevo e abas vazadas. O pescoço parte de uma base larga e a boca avança para a ponta. Duas nervuras chegam sob o lábio. O diâmetro aparente de 68 mm orientou a tampa preta estriada. A profundidade da passagem e o ângulo físico continuam estimados. [Perfil](../../build/sevel-cad/reviews/head-v008/cover-v008.jpg) · [Bocal aberto](../../build/sevel-cad/reviews/head-v008/throat-v008.jpg) |
| Bobina, suporte e termostática | O suporte apoia a bobina de quatro torres acima da carcaça. A vista de ponta mostra ambas as saídas de mangueira e o acesso lateral à tampa de óleo. A furação da bobina segue os 90 × 52 mm do desenho Bosch. Os trechos de mangueira terminam depois da primeira curva. [Montagem em perspectiva](../../build/sevel-cad/reviews/head-v008/installed-v008.jpg) · [Vista de ponta](../../build/sevel-cad/reviews/head-v008/installed-end-v008.jpg) |
| Gaiola aberta | As três travessas entre as quatro janelas ganharam rebaixos e furos cegos. A flange segue as seis posições existentes dos prisioneiros. A profundidade dos rebaixos ainda depende de medida direta. [Comparação](../../build/sevel-cad/reviews/head-v008/carrier-v008.jpg) |

## Verificação do arquivo reaberto

- O FreeCAD reabriu a montagem com 231 sólidos fechados e válidos. Na fase de 0°, foram testados 174 pares com possibilidade de contato envolvendo ao menos uma das onze peças novas ou revistas. A revisão passou sem aumento de interferência acima de 0,00001 mm³.
- Os quatro assentos anulares das velas passaram na verificação de apoio. As oito bocas de gases e as duas de água conservaram o contorno da entrada. As seis fixações da tampa passaram depois de reposicionar uma aba e liberar a nervura vizinha na gaiola. O cartucho tem contato nominal com a face de apoio e 0,15 mm de folga radial no espigão no modelo. [Resultados de montagem](../../build/sevel-cad/reviews/head-v008/validation.json)
- A gaiola passou em 74 verificações com os volumes ocupados pelo comando, pela distribuição e pelos componentes do trem de válvulas. Cada uma das onze peças novas ou revistas voltou do STEP como um sólido fechado e válido. [Resultados de movimento e STEP](../../build/sevel-cad/reviews/head-v008/exchange-motion.json)

## Medidas e referências pendentes

- **Prioridade para o encaixe da termostática.** Medir diretamente o entrecentros das roscas no cabeçote quando ele estiver acessível. A folga nos furos da carcaça e o ponto de apoio dos mordentes afetam a estimativa de cerca de 78 mm na peça solta. Uma foto perpendicular com escala no plano da flange também ajuda a recuperar o ângulo físico.
- **Bobina original.** O código gravado e a distância entre centros dos furos identificam a correspondência com a Bosch 0 221 503 407 caso apareça divergência de montagem. O suporte e o afastamento da bobina foram aproximados pelas fotos do proprietário.
- **Fundição.** Vistas rasantes dos pés das colunas e das nervuras dos coletores ajudariam a acertar o relevo residual. A escala do filtro pode ser obtida com um cartucho fora do motor. As imagens atuais bastam para localizá-lo, mesmo sem bloco desmontado.

A pasta `PhotosMotor/` reúne as imagens originais e catálogos usados como referência visual. O índice e as listas por peça ficam em `build/sevel-photo-catalog/exports/`. As cotas usadas nesta revisão têm origem e confiança registradas. [Catálogo de fotos](../../build/sevel-photo-catalog/exports/SEVEL_PHOTO_CATALOG.md) · [Cotas da v008](head_exterior_evidence.json) · [Comparação anterior](COMPARACAO_V007_FOTOS.md) · [Lista de fotos pendentes](FOTOS_PENDENTES.md)
