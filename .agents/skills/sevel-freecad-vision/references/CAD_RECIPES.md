# Receitas CAD adaptadas aos tutoriais relevantes

## Tutoriais selecionados

1. **FreeCAD Engine Block Tutorial (antigo, 0.14)** — https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Engine_Block_Tutorial.md
   - Extração: primitiva para envelope, corte de cilindros, alojamento de virabrequim, cárter, gabarito da junta do cabeçote e furos; operações `Part::Cut` e `Part::Fuse`.
   - Adaptação: quatro cilindros, diâmetro nominal 86,4 mm, parâmetros de motores reais, cinco mancais e blocos externos em grupos. NÃO copiar dimensões fictícias do exemplo de dois cilindros.
   - A interface Draft antiga mudou; preferir APIs Python `Part`, `Sketcher`, `PartDesign`, `Draft` atuais.
2. **FreeCAD PartDesign tutorial** — https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Basic_Part_Design_Tutorial.md
   - Extração: sketch mestre + operações `Pad`, `Pocket`, `Revolution`, espelhamento, parâmetros e histórico.
   - Adaptação: um sketch mestre do deck e outro do eixo do virabrequim, features localizadas por sólidos de referência e offsets rastreáveis.
3. **FreeCAD image-to-geometry com Inkscape** — https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Import_text_and_geometry_from_Inkscape.md
   - Extração: importar **SVG as geometry**, revisar dimensões e, se necessário, Draft -> Sketch.
   - Adaptação: importar separadamente a silhueta irregular e círculos analíticos, verificar escala no FreeCAD com distância conhecida, não confiar apenas no DPI.
4. **FreeCAD Draft SVG** — https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Draft_SVG.md
   - Importa `path`, `line`, `rect`, `circle`, `ellipse`, `polygon`, `polyline`; `width`/`height` e `viewBox` governam escala física na importação.
5. **FreeCAD tutorial 4 cilindros (2026)** — https://www.youtube.com/watch?v=70-kATkOnEc
   - Contém pistão, anéis, virabrequim, biela, pino, assemblies e simulação; adaptar cinemática e estruturas, não assumir motor igual ao SEVEL.
6. **FreeCAD 1.1: montagem e animação de pistão (MangoJelly)** — https://www.youtube.com/watch?v=wxxDahY1U6E
   - Útil para master sketch, SubShapeBinder e juntas revolute/slider. Separar modelo paramétrico de demonstração de dados dimensionais do SEVEL.
7. **FreeCAD Part Face from Wires / Python API** — https://robertmassaioli.github.io/freecad-docs/part/tools/face-from-wires/
   - Face planar com fios internos; usar para gabaritos de juntas e extrusões, verificando orientação e interseções.

## Receitas por etapa

### M1: Envelope, bores e deck

1. Definir sistemas de referência: X ao longo dos cilindros, Z ao longo dos eixos dos cilindros, Y transversal; origem obrigatória no eixo do cilindro 1, no plano superior do bloco (referencial `reference_frame.json`). Centralização de renderização ocorre somente por transformação separada.
2. Carregar `reference_frame.json` criado pelo portão M1. Parâmetros `bore = 86.4`, `stroke = 67.4`, `crank_radius = 33.7` em milímetros são confirmados; `centers_x = [0, 93, 189, 282]` é gabarito **provisório baseado na tabela 92 cv**, salvo confirmação independente para Tipo SPI 82 cv. Nunca extrair centros do SVG sem comparar ao gabarito.
3. Construir quatro `Part.makeCylinder(radius=43.2, height=block_deck_depth, ...)` alinhados aos eixos nominais; usá-los para `cut` do envelope do bloco.
4. Criar planos face a face sem inventar medidas de galeria de óleo/água. Separar a parede externa de referência da geometria funcional.
5. Sobrepor `head_gasket_analytic.svg` de referência, registrar escala/calibração com ressalva; **não aplicar automaticamente seus 39 furos ao bloco como canais reais**.

### M2: Fundição complexa

1. Montar massas principais por `Part::Feature`/booleans, ou sketches parametrizados e `Pad`/`Pocket` quando o histórico for útil.
2. Gerar nervuras e bosses com operações específicas, possivelmente sólidos auxiliares. Agregar adições/cortes em lotes apropriados para reduzir tempo de booleans.
3. Na fusão, evitar operações com milhares de faces originadas de raster; converter contorno em B-spline suave apenas após testar desvios e manter detalhe visual necessário.
4. Preservar alojamentos, tampões e planos de fixação como objetos identificáveis; não saturar o modelo com roscas reais no primeiro marco.
5. Se um boolean pesado travar, migrar cálculo puro para worker async e `commit()` ou execução headless, seguindo contrato MCP.

### M3: Cabeçote

1. Começar pela silhueta externa e plano de junta, volumes de admissão/escape e fixações mais visíveis; separar parte inferior, porta-comando e tampa.
2. Usar medidas de guias/valvulas e alojamentos do manual, com fontes/páginas; uma câmara geométrica aproximada deve ser rotulada como tal.
3. As cotas e inclinações não disponíveis são variáveis, não fatos deduzidos por desenho em perspectiva.
4. Conferir aspecto com fotos de cabeçote e desenho do catálogo em mais de uma vista.

### M4: Cinemática

1. Virabrequim com raio da manivela de 33,7 mm; fase de moentes 1+4 versus 2+3.
2. Curso de 67,4 mm validado por amostra angular do ciclo, de 0° a 720°.
3. Comprimento de biela **a medir**. `z = r*cos(theta) + sqrt(L² - r²*sin²(theta))` somente no caso de pino centrado, em um referencial adequado.
4. Comando gira metade da velocidade do virabrequim, ordem de ignição 1-3-4-2. Levantamento de válvula sintetizado até existirem perfis reais dos cames.
5. Registrar pivôs e transforms por peça; a visualização não deve ocultar colisões indevidas.

## Regras de modelagem de desenho para sólido

- Um contorno SVG importado em FreeCAD é referência 2D; `Draft to Sketch` pode converter contornos planares, mas revisar círculos e arcos como entidades analíticas.
- O histórico de um sólido gerado por `Part.Shape` com script pode ser regenerável sem ser uma árvore `PartDesign` nativa. O aceite inicial pode usar script reproduzível; melhorar a parametricidade nativa em etapas.
- `Part.Face([outer, *inner])` requer fios fechados, planares e sem auto-interseção, com orientação apropriada. Validar `isValid()`; em falha, identificar contorno inválido e ajustar antes de continuar.
- Importar SVG por `viewBox`/dimensões físicas apenas após confirmar que o arquivo usa mm; o SVG simples do Inkscape do usuário está em unidades de `viewBox` e não tem escala em mm verificada.
