# Contrato do gabarito mestre do SEVEL (obrigatório antes da fundição)

## Objetivo

Todo volume modelado no FreeCAD deve depender de um **referencial mestre único** validado, cuja geometria não seja alterada por operações de estilização ou por vetorização da fotografia. O resultado inicial é uma prévia visual confiável para diâmetro e curso e **provisória para entrecentros**, até confirmar a variante 82 cv.

## Ordem de execução e bloqueio

1. Verificar a variante-alvo dos manuais/fotos (Tipo SPI 82 cv, 1993–1995) e registrar variantes diferentes separadamente.
2. Revisar `assets/reference_parameters.example.json` como *semente* e produzir `build/sevel-cad/parameters.json` com **os valores, sua unidade, evidência, fonte e variante**. Não apagar a ressalva dos 93/96/93 mm ao copiá-los.
3. Executar `scripts/build_reference_frame.py --params build/sevel-cad/parameters.json --output build/sevel-cad/datums`. Conferir os JSON e o SVG de prova.
4. Executar `scripts/freecad_reference_from_json.py` por `execute_code` do MCP com `FRAME_MANIFEST_PATH` e `FRAME_OUTPUT` explícitos. Gerar o FCStd de **referência**, separado do bloco, e capturar `Top`, `Isometric`, `Front` com `get_view`.
5. Comprovar numericamente quatro círculos com Ø do bloco, centros colineares no plano Z=0, espaçamentos positivos e ordenados, sem unidade ambígua. A geometria do motor deve reutilizar os centros desse manifesto, sem duplicar valores hardcoded.
6. Registrar `PASS_PROVISIONAL_FOR_VISUAL_ONLY` ou `PASS_CONFIRMED`. Apenas então M2 pode começar. `FAIL` ou ausência de relatório impedem M2; não completar o modelo por intuição.
7. Validar o portão novamente sempre que uma fonte alterar o entrecentro, diâmetro ou o referencial. Guardar resultados antes/depois e registrar as peças afetadas pela mudança.

## Sistema de coordenadas canônico

- Unidade: milímetros no CAD.
- O = (0,0,0), interseção do eixo do **cilindro 1** com o **plano superior do bloco** (deck).
- +X = direção longitudinal do cilindro 1 ao 4. +Y = direção transversal arbitrada, mas mantida em todo o projeto. +Z = ao longo dos cilindros, do bloco rumo ao cabeçote.
- Plano do deck: Z=0.
- Eixos dos cilindros: linhas paralelas a Z passando por (X_i,0,0). Os centros na vista Top são (X_i,0).
- Para entrecentros de referência [93,96,93] mm: X_i = [0,93,189,282] mm. Distância entre extremos 1→4 = 282 mm.
- Diâmetro do **furo de cada cilindro**: Ø86,4 mm, raio 43,2 mm. Distâncias **planas entre as bordas dos furos**: [6,6;9,6;6,6] mm. Isso NÃO afirma a espessura real da parede fundida, nem contempla galerias.
- Curso: 67,4 mm; raio de manivela derivado 33,7 mm. Eixo do virabrequim é paralelo a X, mas não fixar seu Z sem medida ou estimativa explicitamente rotulada. Não inserir uma dimensão provisória no datum definitivo.

## Fontes e precedência

- `MANUAL_TARGET`: cota explícita de manual identificável da variante-alvo. Valor nominal, não inferência.
- `MEASURED_TARGET`: medição física identificada da peça-alvo, com instrumento e incerteza.
- `OTHER_VARIANT_REFERENCE`: fonte técnica de variante diferente, com possível aplicação a ser verificada. **Espaçamento 93–96–93 mm está aqui.** Fonte: https://www.clubedounobrasil.com.br/forum/viewtopic.php?t=73, postagem 2013-03-02, motor injetado **92 cv**.
- `PHOTO_ESTIMATE`: medida derivada de foto calibrada/deformada, com possível erro de perspectiva, reprojeção e escala não uniforme.
- `ASSUMPTION`: estimativa explícita do modelador.
- `UNKNOWN`: não preencher por analogia sem registrar uma escolha provisória.

A prioridade em conflitos não deve ser resolvida apenas por ordem fixa: documentar as versões e confirmar o que corresponde à mesma peça/variante. Um resultado numérico bonito não demonstra procedência.

## Política das juntas digitalizadas

A junta SVG é uma prova de contorno e de posição aproximada de furos: sua **abertura de cilindro** não tem necessariamente Ø86,4 mm. Usar a dimensão do cilindro como *escala inicial do raster* é uma aproximação do processador de imagens, não uma especificação dimensional da junta.

- Nunca ajustar os centros do bloco para fazer o contorno raster se encaixar melhor.
- Registrar transformação de imagem→CAD (translação, rotação, escala X/Y e, se necessário, homografia), conjunto de pontos de controle, resíduos e eventuais buracos não casados.
- Preferir corrigir círculos como curvas analíticas; manter contornos irregulares suavizados, mas identificados como `PHOTO_ESTIMATE`.
- Aberturas da junta, galerias de água/óleo e parafusos são **classes separadas**, a serem interpretadas com o catálogo e fotos reais. Uma região transparente da máscara não é automaticamente uma cavidade do bloco.
- Se a foto de outra junta mostrar os mesmos eixos mas em escala diferente, recadastrar o ajuste e a incerteza, não alterar o datum do motor.

## Critérios do portão

`PASS_CONFIRMED`: Ø, curso e todos os entrecentros são provenientes de fontes aplicáveis à variante-alvo, sem contradições relevantes; todos os testes passam. Não afirma precisão metrológica integral do bloco.

`PASS_PROVISIONAL_FOR_VISUAL_ONLY`: testes geométricos passam e todas as cotas não confirmadas na variante-alvo estão explicitamente marcadas (caso atual dos 93/96/93 mm). Permite projeto do simulador visual e captura, mantendo ressalvas nos resultados.

`FAIL`: insumos sem procedência, campos físicos inválidos, centros invertidos, superposição das aberturas de cilindro, ou falha de teste/geração. Não avançar à fundição.

**Teste obrigatório:** reexecutar a geração com o mesmo manifesto e obter os mesmos JSON/SVG (arquivos determinísticos); reconstruir as peças após alterar um entrecentro, verificar que suas coordenadas derivadas acompanham a mudança e que a evidência fotográfica é comparada no novo referencial.
