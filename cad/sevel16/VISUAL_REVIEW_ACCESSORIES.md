# Revisão — SEVEL Accessories A5 v001

Modelo: `build/sevel-cad/models/SEVEL_Accessories_A5_v001.FCStd`.
SHA-256: `999d32a3f1dedcb6f7965b67b2f77b3a6d28930ebc9aa58d35807efae879acbc`.
Estado visual: `REVIEWED_WITH_DOCUMENTED_DIFFERENCES`; prévia geométrica.
As dimensões externas dos novos componentes são `ASSUMPTION` no manifesto.

## Referências e observações

Catálogo local do Tipo 1.6 SPI 1993–1995, código 160.362.1, páginas PDF
67–70 e 89–90: coletores, duas juntas comuns e bomba com polia de acessórios.
Comparação complementar com `PhotosMotor/referencia_coletores_selos.png` e
as fotos do motor completo e cabeçote indicadas no índice de referências.
Essas perspectivas não permitem recuperar cotas nem inclinações exatas.

| Referência → observação | Prioridade e ação | Evidência nova |
|---|---|---|
| Coletores no mesmo lado; ordem E–I–I–E–E–I–I–E | P0: quatro caminhos de cada tipo ligados às portas corretas; duas juntas comuns | `*-manifolds-Isometric.png`, `*-manifolds-Back.png` |
| Passagens de água junto à admissão, anotadas pelo usuário | P0: circuito de aquecimento separado do ar; distância mínima 5,70836 mm | `*-intake-Bottom.png` e métricas de interfaces |
| Quatro ramos convergem no escape | P0: corrigida a união de pontas coincidentes que gerava sólido inválido | `*-exhaust-Front.png` |
| Bomba assentada na interface retangular lateral | P0: o primeiro loft perdeu parte da carcaça; lacuna de 23,77 mm rejeitada. Carcaça refeita e contato conferido | `*-pump-Isometric.png`, `*-pump-Right.png`; trial `accessories_v002` |
| Polia da bomba separada da distribuição | P0: plano alinhado à polia de acessórios; não participa da correia dentada | `*-external-accessories-Left.png` |
| Velas entram pela face oposta aos coletores | P0: quatro conjuntos com cerâmica, sextavado e eletrodo; pontas dentro das câmaras | `*-spark-Isometric.png`, `*_TransverseC1-Right.png` |

Todos os nomes abreviados acima começam com `SEVEL_Accessories_A5_v001` e
estão em `build/sevel-cad/evidence/`. Foram examinadas as dez imagens do
relatório `*_accessory_captures.json`, as sete de `*_closure_captures.json`,
as treze de `*_cycle_captures.json` e os dois cortes atuais.

O conjunto mantém quatro pistões, bielas articuladas, oito válvulas,
comando e auxiliar legíveis nas dez poses de 0° a 720°, incluindo 359°.
0° e 720° coincidem visualmente; 180° e 540° preservam pistões mas mudam
as válvulas conforme o ciclo. As vistas de distribuição isolam o circuito.
Tampa/cárter mostram cavidades, bosses, flange assimétrica e fundo em dois
níveis. A explosão separa 11 peças com translações reversíveis. Os cortes
longitudinal (189 objetos) e transversal C1 (34) foram salvos e reabertos.

## Diferenças mantidas nesta prévia

- P1: plenum tubular, curvas de coletores e carcaça da bomba ainda têm
  aparência simplificada; não reproduzem toda a fundição das fotos.
- P1: trecho interno das velas acompanha o canal provisório do cabeçote;
  seu comprimento não representa alcance de rosca de uma vela comercial.
- P1: a bomba é estática, com relação de acionamento desconhecida; sem
  rotor ou correia de acessórios. A polia não foi ligada ao comando.
- P2: roscas, fixadores de coletores, defletores e estampagens omitidos;
  reflexos triangulares em curvas são da tesselação de exibição.
- Mantidos os limites anteriores: câmaras simplificadas, nervuras externas
  aproximadas, entrecentros de outra variante e ângulo do respiro provisório.

A subtração B-rep do coletor de admissão reconstruído contra sua cópia
salva falhou no OCCT. A verificação independente registra esse limite e
compara topologia, tipos de superfícies, orientação, domínios, áreas,
volume, vértices e 14.544 amostras de superfícies/bordas. Isso é equivalência
numérica amostrada, não identidade exata nem prova de fabricação.
