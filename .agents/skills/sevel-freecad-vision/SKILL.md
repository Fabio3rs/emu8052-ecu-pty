---
name: sevel-freecad-vision
description: Modelagem CAD de motores, especialmente SEVEL 1.6 SOHC 8V do Fiat Tipo, com FreeCAD MCP, referências de fotos/manuais, gabaritos de juntas PNG/SVG, geometria paramétrica, capturas de viewport e revisão visual iterativa. Use quando o usuário pedir reconstrução de bloco/cabeçote, importação de juntas, animação ou verificação de modelos no FreeCAD. Não use para validar peças fabricáveis ou para inventar tolerâncias não documentadas.
---

# SEVEL CAD: modelar, medir, capturar, comparar e corrigir

Esta skill organiza a execução do agente. O FreeCAD MCP executa as ações; as ferramentas CAD, os scripts locais e a avaliação de imagens são complementares. Objetivo inicial: construir **um modelo visual convincente, geométrica e cinematicamente coerente** do motor Fiat Tipo 1.6 SPI SOHC 8V, sem pretensão de engenharia reversa metrológica completa.

## Início obrigatório

1. Localizar o projeto, `PhotosMotor/`, manual técnico, catálogo de peças, geometria existente e geradores. Não presumir que arquivos presentes em outro computador estão disponíveis; verificar existência em disco. Tratar originais como somente leitura.
2. Examinar `references/INPUTS_AND_PROVENANCE.md`, `references/CAD_RECIPES.md`, `references/MCP_TOOL_CONTRACT.md` e `references/VISION_REVIEW.md` conforme a tarefa. As fotos e dimensões do usuário prevalecem sobre silhuetas genéricas.
3. Usar `get_rpc_status` e `list_documents` para diagnosticar a instância FreeCAD. Verificar se o addon e servidor MCP são compatíveis antes de começar. Não alterar documentos não pertencentes ao projeto.
4. Construir o `build/sevel-cad/parameters.json` (ou outro manifesto estruturado) para separar fatos comprovados, medições indiretas e escolhas provisórias. O manifesto deve incluir **fonte + página/foto + confiança + unidade** para cada dimensão.
5. **Antes de M2**, cumprir o portão obrigatório de referências M1: construir o datum mestre com os quatro eixos e centros, verificar suas distâncias e diâmetros, registrar a classe de evidência de cada dimensão e obter `PASS_CONFIRMED` ou `PASS_PROVISIONAL_FOR_VISUAL_ONLY`. Nunca modelar a fundição sobre um SVG rasterizado sem antes fixar o sistema de coordenadas. Seguir `references/REFERENCE_FRAME_PROTOCOL.md`.
6. Manter parâmetros em uma única fonte e scripts reexecutáveis; não deixar a montagem final dependente apenas de estado transitório do console FreeCAD.

## Contrato de autoridade e compatibilidade com o `/goal` antigo

**Uma única origem de verdade espacial:** `build/sevel-cad/datums/reference_frame.json`, calculado a partir de `parameters.json`, governa os quatro eixos, o plano do deck e a direção dos eixos. Ele prevalece sobre qualquer convenção alternativa no documento `SEVEL_16_FREECAD_CODEX_SPEC.md` (especialmente §6.3, que usa origem centrada no eixo do virabrequim). Não misturar essas coordenadas.

- **Referencial mestre:** O=(centro de C1 no deck), X=C1→C4, Z=deck→cabeçote e Y completa o sistema destro. O eixo do virabrequim é paralelo a X e tem Z negativo, desconhecido até medição ou estimativa separada.
- **Referencial de apresentação/exportação:** origem centrada ou no virabrequim somente por uma transformação `T_model_to_render` explícita, guardada em arquivo e testada. Não editar/mover os datums para centralizar a cena.
- **Fontes de medidas:** usar exclusivamente as classes `MANUAL_TARGET`, `MEASURED_TARGET`, `OTHER_VARIANT_REFERENCE`, `PHOTO_ESTIMATE`, `ASSUMPTION` e `UNKNOWN` no manifesto dimensional. `CATALOG` identifica componentes e vistas; `SYNTHETIC` descreve visualização e cinemática assumida, sem virar um fato metrológico.
- **Correções por evidência:** nenhuma foto, vetor ou anotação de outra variante deve sobrescrever automaticamente uma cota `MANUAL_TARGET`; conflitos vão para `reports/evidence_conflicts.md`.
- Os esquemas do catálogo e fotos são referências de identidade e posicionamento, **não** desenhos ortográficos dimensionados por padrão.

## Entrega em fatias verificáveis (evitar dispersão)

O `/goal` original pede M0–M5 numa única execução. Para otimizar o tempo do agente, executar **M0 → M1 → M2a (bloco estrutural) → M2b (fundição externa)** antes de detalhar M3–M5. Ao fim de cada fatia, salvar `FCStd`, gerador, parâmetros, métricas e capturas. Não marcar M2 como concluído só porque quatro cilindros foram perfurados num paralelepípedo.

- **M2a:** deck, quatro bores, envelope, região do virabrequim, mancais, flange inferior e interfaces principais; CAD válido e regenerável.
- **M2b:** assimetria das extremidades, tampões, bosses, pelo menos as nervuras principais e flanges características do bloco conforme fotos; duas vistas externas comparadas com fontes identificadas.
- Se a construção avançar rapidamente, seguir M3 (cabeçote), M4 (cinemática) e M5 (visualização/exportação) pelo plano, sem sacrificar a avaliação de M2.
- Um problema numérico sem fonte confiável pode limitar a **fidelidade dimensional** daquela feature sem interromper a prévia visual, desde que apareça como provisório e não comprometa interfaces críticas.

## Regras de geometria

- Dimensões confirmadas da variante 82 cv: diâmetro nominal cilindro `86.4 mm`, curso `67.4 mm`, raio manivela `33.7 mm`, 4 cilindros, 5 mancais principais e comando SOHC 8V; ver páginas impressas 5, 7–15 do manual. Outras dimensões precisam ser checadas antes de virar parâmetro definitivo.
- **Entrecentros `93/96/93 mm` têm uma fonte externa identificada**: tabela técnica para SEVEL injetado de **92 cv**, publicada em 2013 no Clube do Uno Brasil (https://www.clubedounobrasil.com.br/forum/viewtopic.php?t=73). Essa fonte não comprova automaticamente o bloco SPI **82 cv** do Tipo; classificar como `OTHER_VARIANT_REFERENCE` até confrontar com fonte da variante, uma medição física ou um gabarito independente confiável. Para prévia, centros X = `0, 93, 189, 282 mm` podem ser adotados com ressalva.
- Contornos da fundição, nervuras e flanges devem ser reconciliados com vistas fotográficas. Dar prioridade à silhueta, aos planos de interface, à localização dos eixos e a colisões. Parafusos e texturas vêm depois.
- O SVG derivado de fotos é um **gabarito 2D de referência**. Evitar transformar milhares de vértices rasterizados em um único sólido de precisão. Separar curvas/contornos de referência dos círculos/planos/volumes definidos analiticamente.
- Manter `block`, `head_lower`, `cam_carrier`, `valve_cover`, `oil_pan`, `crank`, `connecting_rods`, `pistons`, `camshaft`, `tappets`, `valves`, `timing` como componentes e transforms separados na medida do necessário.
- Quando usar dados desconhecidos, adotar nomes `_estimated` e documentar a fonte da estimativa. Nunca apresentar o objeto como réplica dimensionalmente certificada.

## Portão obrigatório: gabarito mecânico antes de qualquer fundição

1. Executar `scripts/build_reference_frame.py` a partir do manifesto de parâmetros (`assets/reference_parameters.example.json` é uma **semente**, não prova de engenharia). O script produz `reference_frame.json`, `reference_frame.svg` e `reference_gate.json` com posições nominais e status de confiança. Nunca substituir uma medida confirmada pelo resultado da segmentação da foto.
2. Definir sistema **único e estável**: origem O em eixo do cilindro 1 ∩ plano do deck; +X ao longo dos centros 1→4; Y transversal; +Z paralelo aos eixos dos cilindros, para o cabeçote. O deck é Z=0; a posição Z do virabrequim continua desconhecida até documentação ou parâmetro provisório separado.
3. Confirmar Ø86,4 mm para os furos do **bloco**, raio de manivela 33,7 mm, curso 67,4 mm. Manter o diâmetro das aberturas da **junta do cabeçote** como campo distinto e desconhecido até medição.
4. Conferir centros ordenados, espaçamentos, círculo/raio, distância mínima entre círculos, unidades e rastreabilidade de cada valor. Adicionar captura ortográfica do gabarito no FreeCAD e relatório de validação numérica.
5. `PASS_PROVISIONAL_FOR_VISUAL_ONLY` permite avançar ao bloco *visual*, desde que os entrecentros de outra variante estejam assinalados em todo artefato e que nenhuma peça seja apresentada como dimensionalmente certificada. `PASS_CONFIRMED` exige comprovação na variante-alvo. Em caso de `FAIL`, não avançar.
6. O desenho raster, a vetorização SVG e as fotos devem ser **registrados/alinhados** sobre o datum mestre, nunca governá-lo quando contradizem cotas de maior confiança. Diferenças exigem diagnóstico de escala anisotrópica, perspectiva, diâmetro da junta versus furo e variante antes de alterar parâmetros.
7. Ler `references/REFERENCE_FRAME_PROTOCOL.md` para a hierarquia de fontes, as verificações e a maneira de importar essas referências pelo MCP.

## Processar juntas PNG/SVG antes da modelagem do deck

Se existir `PhotosMotor/*-juntas-*_bk.png`, analisar a máscara alfa, identificar componentes e propor uma reconstrução de contorno. O script incluído produz um primeiro gabarito vetorial **sem modificar o original**:

```bash
python -m pip install numpy opencv-python-headless Pillow
python .agents/skills/sevel-freecad-vision/scripts/gasket_extract.py \
  PhotosMotor/D_NQ_NP_2X_666447-MLB115951529104_092026-F-juntas-do-cabecote-fibra-fiat-tipo-16-8v-sevel_bk.png \
  --output build/sevel-cad/gasket --nominal-bore-mm 86.4
```

**Aviso**: na imagem disponível, a diferença entre eixos e o próprio diâmetro da abertura da junta são estimativas rasterizadas. A calibração padrão **assume** que a abertura da junta tem 86,4 mm porque falta uma medição real dessa abertura. Se houver a medida da junta, passar `--actual-opening-mm <VALOR>`. Não tratar o resultado padrão como medida industrial.

Ler `head_gasket_report.json` e verificar `head_gasket_overlay.png`. Confirmar quatro aberturas, contorno, posição de furos e artefatos. O `head_gasket_analytic.svg` contém elementos editáveis separados e a versão `head_gasket_geometry.json` pode alimentar o gerador do FreeCAD. Corrigir dados em parâmetros e reconstruir; nunca editar o SVG base às cegas com perda das fontes.

Não assumir que as outras seis juntas na mesma colagem seguem a mesma escala em pixels. Selecioná-las e calibrá-las separadamente, quando houver cotas físicas independentes.

## Ciclo de execução MCP

1. **Planejar marco** (nome e critérios), escrever/atualizar script de geração. Escolher um subconjunto pequeno e testável (por exemplo, apenas deck/bores).
2. **Executar** com `execute_code` na GUI e `include_screenshot=false` para mutações intermediárias; usar `create_document`/`create_object` se bastarem, ou executar scripts Python via `execute_code` se a operação necessitar geometria OCCT.
3. **Validar numericamente**: `Shape.isValid()`, `BoundBox`, `Volume`, `Solids`, posição dos eixos, tolerâncias e colisões relevantes. Há roteiro em `scripts/freecad_validate.py`.
4. **Capturar** com `get_view(view_name='Isometric'/'Top'/'Front'/'Right')` e, para evidências em disco, `scripts/freecad_capture_views.py` via `execute_code`. O retorno MCP da ferramenta `get_view` é imagem e deve ser efetivamente examinado pelo agente multimodal.
5. **Comparar** a vista renderizada com a foto/desenho de referência **da mesma região e orientação aproximada**. Produzir observações verificáveis: contorno, proporções, nervuras, plano do cabeçote, tampões, alojamentos, flanges, postura da peça, posição dos furos.
6. **Corrigir** por parâmetros e regenerar. Repetir o ciclo apenas até cumprir os critérios de aceite do marco; não polir detalhes cosméticos antes de resolver geometria principal.
7. **Persistir** gerador, manifesto, FCStd, capturas, relatório de medidas, e exportações por componente para `build/sevel-cad/` (ou local do projeto). Entregar links/caminhos e lista de dúvidas dimensionais ainda abertas.

Uma captura isolada não comprova dimensões ou validade B-rep. Uma verificação B-rep não comprova semelhança visual. Usar ambas.

## Contrato de avaliação visual por marcos

1. Fazer um inventário `reports/photo_manifest.json`: caminho relativo, hash, peça, variante alegada, lado/ângulo, tipo (`foto`, `desenho`, `junta`), confiabilidade e cotas independentes disponíveis. **Não inferir a vista apenas do nome do arquivo**; inspecionar a imagem real.
2. Para cada vista a comparar, registrar a orientação/projeção da referência. Desenho em perspectiva, vista ortográfica e foto de marketplace não podem ser comparados pixel a pixel sem calibração. Nas fotos, diferenças de perspectiva e lente devem ser identificadas antes de remodelar a fundição.
3. Capturar por `get_view` quando se requer inspeção multimodal **durante** a execução. Persistir cópias com `freecad_capture_views.py`, identificando documento, componente, vista, câmera e marco; conferir arquivo não vazio e viewport correto.
4. Para cada marco, gerar `reports/Mx_visual_review.md` incluindo **referência → observação → prioridade P0/P1/P2 → parâmetro/feature corrigida → novo screenshot**. Pelo menos duas vistas relevantes para bloco e cabeçote. `PASS` é possível com lacunas cosméticas documentadas.
5. Limitar tentativas cegas: se duas reconstruções consecutivas não resolverem o mesmo problema, isolar a geometria mínima, inspecionar o erro CAD e revisar a hipótese. Evitar repetir booleans indefinidamente.
6. Validar também os números: `isNull()`, `isValid()`, número de sólidos esperado, posições/raios, volumes, `BoundBox`, folgas e interferências relevantes; validar o **resultado final**, não somente os operantes intermediários. Verificar abertura/reconstrução do FCStd salvo.
7. Fazer um *smoke test* de exportação cedo com objeto de medida conhecida, pivot deslocado e transformação não trivial; testar escala, orientação, IDs e materiais no formato de destino. GLB somente se a cadeia real de exportação estiver disponível. A especificação grande §11 contém requisitos adicionais.

## Política de execução concorrente / timeout

- `execute_code`: opera na GUI; nunca tentar executar outra mutação antes de concluir a primeira.
- `execute_code_async`: apenas computação geométrica independente; documentos, `recompute()`, `ViewObject`, `Gui` e `save()` **somente via `commit(fn)` na thread GUI**. Consultar `get_async_status`.
- `execute_code_headless`: reservar para geometrias pesadas que podem travar o OCCT. Abrir/salvar FCStd no processo isolado e chamar `reload_document` na GUI após salvar.
- `SCRIPT_BUSY`: esperar tarefa existente; `still_running` ou timeout: consultar `get_task_status` / `get_rpc_status` antes de repetir. Uma operação pode ter sido efetivada apesar de a resposta falhar.
- Capturas que falham: verificar documento ativo/viewport 3D e `get_rpc_status`; tentar `get_view` antes de capturas específicas do SO. **Não desligar capturas globalmente** se a tarefa precisa de feedback visual.

## Marcos sugeridos

- **M0 — Ambiente e evidências**: localizar assets, confirmar RPC/versões, gerar catálogo de fotos (bloco/cabeçote/biela/pistão/juntas), criar parâmetros e PNGs calibrados quando possíveis.
- **M1 — Gabarito (PORTÃO OBRIGATÓRIO)**: quatro eixos de cilindro, origem/referenciais, deck, virabrequim, parâmetros e quatro furos cilíndricos geometricamente exatos; ver `head_gasket_analytic.svg` apenas como sobreposição de referência.
- **M2 — Bloco**: executar M2a e M2b acima; envelope e cárter com paredes e cavidades essenciais; planos, tampões, nervuras, flanges, suporte externo. Comparar fotos do bloco pelo menos em duas orientações e registrar a revisão.
- **M3 — Cabeçote**: planos de junta, geometria externa, alojamentos, comando e tampa. Usar catálogo 10101 e 10107 para identidade mecânica.
- **M4 — Órgãos móveis**: virabrequim, 4 pistões/bielas, 8 válvulas, comando, correia, eixo auxiliar; cinemática 720° com comando 1:2 e ordem 1-3-4-2.
- **M5 — Apresentação**: recortes, visibilidade seletiva, vista explodida, cores coerentes, exportações STEP e GLB por peça, pivôs e metadados; gerar a galeria de validação.

## Condições de aceite

- O relatório do datum mestre existe e declara explicitamente `PASS_CONFIRMED` ou `PASS_PROVISIONAL_FOR_VISUAL_ONLY`; o status provisório acompanha todas as exportações e relatórios.
- O modelo se parece com o SEVEL nas referências que cobrem o mesmo lado, sem copiar detalhes de outra variante sem identificar.
- Boreshapes realmente circulares e coincidentes com os eixos, e curso de 67,4 mm reproduzido.
- Os parâmetros conhecidos têm citações de arquivo/página, e os desconhecidos são explicitamente rastreados.
- Geometria B-rep válida e sólidos independentes quando necessário; arquivos resultantes reabrem após reconstrução limpa.
- Há capturas de ao menos três vistas relevantes e um relatório com diferenças observadas e resolvidas.
- Nenhuma alteração destrutiva em PDFs, fotografias e bancos de dados originais.

## Recursos complementares

- `references/MCP_TOOL_CONTRACT.md`: mapa de ferramentas FreeCAD MCP e cuidados de runtime.
- `references/CAD_RECIPES.md`: tutoriais adaptados, arquitetura de sólidos e práticas de construção.
- `references/INPUTS_AND_PROVENANCE.md`: fontes, escala, cotas confirmadas/pendentes e limitações de juntas.
- `references/REFERENCE_FRAME_PROTOCOL.md`: referencial mestre, hierarquia de evidências, gabarito e portão de aprovação dimensional.
- `references/VISION_REVIEW.md`: protocolo de comparação foto → viewport e checklist.
- `scripts/gasket_extract.py`: separação e vetorização de gabarito a partir do alfa do PNG.
- `scripts/build_reference_frame.py`: cria e testa o datum 2D do motor e seu relatório de aprovação antes de iniciar a fundição.
- `scripts/freecad_gasket_from_json.py`: teste de extrusão CAD da junta (precisa rodar no FreeCAD real).
- `scripts/freecad_capture_views.py`, `scripts/freecad_validate.py`: evidências e validação.
- `scripts/make_review_sheet.py`: prancha comparativa de fotos reais e capturas do FreeCAD.
- `assets/demo/`: exemplo gerado a partir do PNG do usuário, apenas referência **provisória**.
