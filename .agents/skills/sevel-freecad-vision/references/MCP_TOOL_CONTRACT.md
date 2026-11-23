# FreeCAD MCP — contrato operacional inspecionado

Fonte: https://github.com/neka-nat/freecad-mcp/blob/main/docs/tools.md e https://github.com/neka-nat/freecad-mcp/blob/main/docs/execution.md (consultados em 2026-11-22). Verificar contratos do ambiente instalado, pois evoluem.

## Servidor e processos

- Codex -> `freecad-mcp` por MCP stdio; processo servidor -> addon dentro do FreeCAD por XML-RPC HTTP/TCP `127.0.0.1:9875` por padrão.
- `FreeCADMCP` precisa estar instalado no diretório de addons do FreeCAD e `Start RPC Server` ativo.
- O servidor externo usa Python >=3.12; o Python interno do FreeCAD é separado.
- RPC remoto exposto requer autenticação e, preferencialmente, túnel SSH: `execute_code` pode executar Python arbitrário como o usuário do FreeCAD.

## Ferramentas e uso recomendado

| MCP | Quando usar | Cuidados |
| --- | --- | --- |
| `get_rpc_status`, `list_documents` | Pré-verificação e recuperação | Estado do GUI dispatcher e versões |
| `create_document` | Criar arquivo de trabalho novo | Evitar alterar documento preexistente não solicitado |
| `create_object`, `edit_object`, `delete_object` | Primitivas simples, mudanças pontuais | `include_screenshot=false` nas alterações intermediárias |
| `get_objects`, `get_object` | Inspecionar propriedades e árvore | Pedir imagem só quando necessário |
| `execute_code` | Operações Part/PartDesign, scripts, salvar/capturar | GUI thread; orçamento usual 90s, configurable; evitar computação pesada bloqueante |
| `execute_code_async` | Booleans e outras computações OCCT demoradas fora da GUI | Nunca mutar documentos diretamente; usar `commit()` na GUI e acompanhar `get_async_status` |
| `execute_code_headless` | Operações perigosas/travamentos/lofts/sweeps | Processo isolado `freecadcmd`; salvar em disco e `reload_document` na GUI |
| `get_view` | Captura visual explícita | `view_name`, `width`, `height`, `focus_object`; retorno `image/png`, mesmo com `--only-text-feedback` |
| `get_task_status` | Timeout de operação GUI | Verificar `task_id` antes de repetir |
| `get_async_status` | Resultado de worker | `job_id` e traceback quando falhou |
| `insert_part_from_library` | Peças genéricas presentes em biblioteca FreeCAD | Verificar licença, dimensões, compatibilidade geométrica |
| `run_fem_analysis` | Somente se usuário pedir FEM ou isso trouxer benefício | Requer material/cargas/malha/solver corretos |

## Política de screenshots

No `get_view`, as vistas documentadas são Isometric, Front, Top, Right, Back, Left, Bottom, Dimetric e Trimetric. Sem tamanho explícito a maior aresta é de até 1024 px. A imagem é obtida do viewport do FreeCAD (renderer) e retornada como conteúdo de imagem MCP. Um cliente multimodal *pode* consumi-la, desde que o cliente encaminhe a imagem ao modelo.

Para evidências reproduzíveis em disco, executar `scripts/freecad_capture_views.py` na thread GUI; esse script foi escrito para a API convencional `view.saveImage` e requer verificação no FreeCAD instalado.

## Timeout, falhas e idempotência

- Erro de timeout não significa que a operação foi revertida; obter `task_id`, `mutation_outcome` e consultar o estado.
- `execute_code` / `execute_code_async` compartilham namespace Python persistente: nomes podem sobreviver entre chamadas, mas não ao restart do processo FreeCAD.
- O addon aplica exclusão de scripts (`SCRIPT_BUSY`). Não abrir dois scripts mutantes concorrentes.
- Falhas de `execute_code` podem deixar alterações parciais, diferentemente de certas operações de objeto que tentam rollback.
- Reutilizar scripts versionados e usar gravação em arquivos do projeto após cada marco. Não depender de estado de memória do addon para a entrega.
