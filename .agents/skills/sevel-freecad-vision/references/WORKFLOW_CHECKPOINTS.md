# Checkpoints executáveis — SEVEL FreeCAD Vision v3

## Entrada: antes de modelar

- `PhotosMotor` e os manuais foram **abertos e inspecionados**, e o agente registrou arquivos existentes? Nomes de marketplace não bastam.
- `get_rpc_status` e `list_documents` verificaram GUI, addon e versão? O diretório do agente é visível pelo FreeCAD?
- `parameters.json` foi gerado de uma fonte apenas, com classes de evidência reconhecidas?
- `build_reference_frame.py` foi executado e `reference_gate.json` tem PASS admissível?
- Qual transformação separa a origem do deck da origem do simulador? Há teste simples?

## M2a — funcional

- Existe um gerador idempotente que reabre um FCStd limpo e recupera os quatro furos? Sem duas peças coincidentes na exportação.
- Quatro círculos de Ø86,4 mm, centros de um mesmo manifesto, deck Z=0, bores alinhados com Z?
- Cinco posições de mancal foram definidas ou assinaladas como provisórias, sem mascarar ausência de cotas?
- O volume interno permite mecanismo móvel plausível? Existem cavidades e flange inferior?
- Relatórios `Shape.isValid`, volume e dimensões do resultado foram salvos?

## M2b — identidade visual

- Vista superior, lateral principal e extremidade comparadas com referências nomeadas? 
- Tampões grandes, nervuras, flanges, orelhas e porta/eixo auxiliar foram tratados conforme as vistas realmente disponíveis?
- Fotos de outros motores/variantes estão marcadas como hipótese? Relevos não documentados estão rotulados e são editáveis?
- `reports/M2_visual_review.md` tem falhas priorizadas e capturas antes/depois? 

## Encerramento do marco

- Scripts geradores, parâmetros, FCStd, STEP quando viável, evidências, relatório e arquivo de dúvidas pendentes existem?
- Arquivo reabre e reconstrução em sessão limpa refaz o modelo?
- Foram preservados arquivos originais e o estado Git do usuário?
- Falhas e tarefas parcialmente executadas foram verificadas por `get_task_status`, evitando repetir uma mutação?
