# Protocolo de revisão visual: foto → modelo → screenshot → correção

## Materiais por peça

- Separar `PhotosMotor/` em vistas do bloco, cabeçote (superior/inferior/lateral), cárter, pistões, bielas, juntas e elementos da distribuição. Não somar fotos de variantes sem confirmar compatibilidade.
- Registrar em `build/sevel-cad/references.json`: `photo_path`, `part`, `side`, `orientation`, `source_product`, `variant`, `notes`, `camera_assumptions`.
- Alinhar orientation do viewport a uma foto apenas aproximadamente quando a lente/perspectiva não for conhecida. Para comparações mais fortes, usar silhuetas e pontos característicos sob a mesma projeção.

## Ciclo por marco

1. Antes: `get_rpc_status`, confirmar FreeCAD acessível e documento ativo.
2. Renderizar quatro vistas (a mais informativa primeiro) usando `get_view`.
3. Comparar visualmente **somente a geometria visível** e registrar `feature / esperado / observado / correção / evidência`.
4. Verificar dimensões, eixos, colisões e validade em Python.
5. Corrigir a fonte parametrizada, reexecutar e obter novas capturas.
6. Salvar prints com prefixo de marco + componente + vista + timestamp, sem sobrescrever evidências anteriores.

## Prancha de imagens para o agente

```bash
python .agents/skills/sevel-freecad-vision/scripts/make_review_sheet.py \
  --photos PhotosMotor --captures build/sevel-cad/evidence \
  --part bloco --output build/sevel-cad/reports/block_review_sheet.png
```

O script pareia por linha/ordem do nome, sem pose tracking. Rever manualmente o ângulo das fotos e das capturas antes de concluir diferenças; o agente deve analisar tanto a imagem original como a montagem produzida.

## Critérios de inspeção

| Checagem | Pergunta operacional |
| --- | --- |
| Silhueta | Faces/cantos superiores, profundidade e base correspondem à foto aproximada? |
| Nervuras | Quantidade, orientação e localização das maiores nervuras parecem corretas? |
| Fixações | Posições de suportes, bosses e flanges estão no lado esperado? |
| Tampões | Pontos de inspeção e tampões se alinham com catálogo/fotos? |
| Juntas | Bordas, perfurações e superfícies estão no mesmo referencial CAD? |
| Cabeçote | Plano inferior, inclinação aparente e volume externo correspondem? |
| Conjunto móvel | Biela, pistão e comando cabem dentro do bloco em todas as fases? |
| Câmera | A referência é visão ortográfica, fotografia perspectiva ou desenho isométrico? Comparação pixel-a-pixel é significativa? |
| Escala | Há no mínimo uma cota física independente ou o dado é fotografia não calibrada? |

## Escore qualitativo, nunca pseudometrológico

`PASS`: atende referências fornecidas; `REVIEW`: parecido mas há diferenças; `BLOCKED`: fonte ou dimensão indispensável ausente. Para cada item registrar evidências com o mínimo de duas vistas quando o detalhe puder ficar oculto.

Não usar SSIM, IoU pixelwise ou CLIP similarity como prova de fidelidade geométrica quando a câmera, perspectiva e iluminação não coincidem. Esses indicadores podem ajudar em triagem de revisões, porém não substituem dimensões e avaliação de formas.

## Exemplo de entrega de marco

```text
build/sevel-cad/
  parameters.json
  generator/
  models/sevel_block.fcstd
  exports/block.step
  exports/block.glb
  evidence/M2_block-Isometric-20261122T...png
  evidence/M2_block-Right-20261122T...png
  reports/M2_geometry_checks.json
  reports/M2_visual_review.md
```

Para preservar visão do agente, `get_view` retorna imagem diretamente. Para preservar no disco, o helper `freecad_capture_views.py` usa `view.saveImage` no FreeCAD; verificar API da versão em uso.
