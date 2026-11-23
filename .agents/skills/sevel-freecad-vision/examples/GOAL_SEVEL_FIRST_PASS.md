# /goal — SEVEL 1.6, primeira execução verificável (revisado)

/goal

Use obrigatoriamente a skill `$sevel-freecad-vision` (v3). Se estiver presente,
leia `SEVEL_16_FREECAD_CODEX_SPEC.md` como especificação ampla de longo prazo;
a ausência desse documento não deve impedir o trabalho com os manuais locais e a skill.
O objetivo imediato é CONCLUIR O BLOCO antes de distribuir esforço pelo motor inteiro.

**Ordem de prioridade dos contratos**:
1. Modelo e arquivo de medidas `build/sevel-cad/parameters.json` com procedência.
2. Referencial mestre criado por M1: `build/sevel-cad/datums/reference_frame.json`.
3. Processo de execução e verificação descrito pela skill v3.
4. Especificação extensa como referência dimensional/visual/cinemática.

Quando a spec antiga usar origem no virabrequim e X centrado, converta isso
explicitamente em transformações de cena; NUNCA misture coordenadas com o gabarito
cuja origem é no centro do cilindro 1, no plano superior do bloco (deck).

**Autonomia e segurança**:
- Inspecione o repositório, `PhotosMotor/`, PDFs, macros e modelo já existente antes de gerar peças.
- Preserve fotografias, PDFs e documentos do usuário, e não sobrescreva FCStd existentes.
- Pode criar/editar scripts e arquivos do projeto e fazer commits locais após validar.
- NÃO faça `git push`, não remova alterações alheias e não tente redesenhar o motor inteiro em um único script monolítico.
- Se o MCP não estiver conectado ou não houver FreeCAD aberto, faça todo o trabalho offline possível (parâmetros, testes, gabaritos, geradores) e relate o bloqueio específico.

**Etapas e portões**:
M0 — inventário: grupo de fotos por peça, variante e orientação; registre também as fontes do manual e catálogo. Primeiro tente localizar modelos CAD reaproveitáveis no repositório.
M1 — gere `parameters.json`, `reference_frame.json`, `reference_gate.json` e FCStd de datums. Verifique Ø86,4 mm, curso 67,4 mm, quatro eixos e entrecentros. Os 93/96/93 mm são provisórios de outra variante; permitir PASS_PROVISIONAL_FOR_VISUAL_ONLY para esta etapa visual, registrando a ressalva.
M2a — construa o bloco estrutural: deck, quatro bores, cárter do virabrequim, mancais/apoios, flange inferior e aberturas essenciais. Construa via scripts Python reproduzíveis executados pelo MCP, com validação B-rep e teste de reconstrução.
M2b — refine a identidade SEVEL com saliências laterais, tampões, nervuras, orelhas, flanges e extremidades assimétricas visíveis nas fotos. Priorize o que altera a silhueta e a leitura em corte; não gaste o primeiro marco com roscas, parafusos e galerias sem evidência.

**Feedback multimodal obrigatório**:
- Depois de cada subetapa relevante, chame `get_view` nas vistas apropriadas e INSPECIONE de fato as imagens retornadas.
- Compare com pelo menos duas referências fotográficas ou desenhos de vistas correspondentes, identificando os arquivos usados. Não use uma foto em perspectiva como prova métrica.
- Salve imagens e `reports/M2_visual_review.md` com defeitos observáveis, prioridade, correções tentadas e novas evidências.
- Use `Shape.isNull`, `Shape.isValid`, número de sólidos, dimensões, posições e interferências para conferir também numericamente.
- Em timeout/SCRIPT_BUSY consulte status e estado do documento antes de repetir qualquer mutação.

**Saída esperada**:
- Um bloco SEVEL visualmente reconhecível, paramétrico por gerador, reabrível em FreeCAD e com interfaces mecânicas consistentes.
- `parameters.json`, scripts, FCStd, STEP (quando funcional), galeria de capturas, `reference_gate.json`, relatórios geométrico/visual e lacunas de evidência.
- Teste mínimo de exportação com dimensões, orientação e pivô verificados.
- Reporte separadamente COMPROVADO, ESTIMADO e AINDA AUSENTE; não declare fidelidade dimensional completa.

**Continuação**: só avance a M3 (cabeçote), M4 (cinemática) e M5 (apresentação/exportação completa) quando M2 estiver salvo e verificado. Se alguma parte falhar, entregue o último marco verificável com diagnóstico e próximos passos concretos, sem reiniciar cegamente toda a modelagem.
