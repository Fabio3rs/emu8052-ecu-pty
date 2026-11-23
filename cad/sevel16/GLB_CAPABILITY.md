# Exportação GLB na instalação disponível

Teste feito no FreeCAD 1.1.4, addon MCP 0.1.32, em GUI. A consulta
`App.getExportType('glb')` retorna `ImportGui`, mas o registro do formato
não comprovou a capacidade de gravar um arquivo nesta instalação.

`probe_glb.py` cria duas caixas assimétricas de 86,4 × 33,7 × 67,4 mm,
com cores diferentes, pivô deslocado e rotações compostas. Os resultados
estão em `build/sevel-cad/exports/glb_calibration_v001` a `v003`:

| Tentativa | Condição | Resultado |
|---|---|---|
| v001 | Exportação direta de dois objetos visíveis | `OSError: Cannot save to file: `; nenhum GLB criado |
| v002 | Tesselação explícita a 0,08 mm e atualização da GUI | Mesmo erro; nenhum GLB criado |
| v003 | Tesselação; `legacy=True`, `exportHidden=True`, `keepPlacement=True` | Mesmo erro; nenhum GLB criado |

As opções da terceira tentativa foram conferidas no
[código do exportador FreeCAD 1.1.0](https://raw.githubusercontent.com/FreeCAD/FreeCAD/1.1.0/src/Mod/Import/Gui/AppImportGuiPy.cpp).
O [gravador GLTF dessa versão](https://raw.githubusercontent.com/FreeCAD/FreeCAD/1.1.0/src/Mod/Import/App/WriterGltf.cpp)
emite a exceção quando a operação nativa falha; esse caminho não fornece,
sozinho, a causa interna da falha observada em 1.1.4. Não foi atribuída uma
causa de compilação, permissão ou geometria sem evidência adicional.

As duas últimas pastas preservam `expected.json` e `capability.json`.
Sem GLB produzido, escala, orientação, materiais e hierarquia desse formato
continuam **não verificados**. O validador Khronos não está instalado como
comando nem como módulo Node disponível; Blender, trimesh e pygltflib também
não foram encontrados na cadeia local inspecionada.

A entrega utilizável continua em STEP e OBJ por componente com manifest,
calibração de pivô, materiais e poses verificadas no carregador existente.
Para produzir GLB falta corrigir a gravação nativa ou disponibilizar um
conversor funcional e então repetir a calibração, a reabertura e a validação.
Essa limitação de formato não interrompe o restante da modelagem.
