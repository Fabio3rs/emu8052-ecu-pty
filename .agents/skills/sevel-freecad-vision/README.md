# sevel-freecad-vision v3

Skill local do Codex para modelagem de bloco/cabeçote SEVEL 1.6 com FreeCAD MCP, referências fotográficas, calibração das juntas e revisão multimodal do viewport.

## Alterações da v3

- Resolve conflito de origens e eixos entre a spec original (§6.3) e o gabarito v2: `reference_frame.json` é canônico.
- Padroniza classes `evidence` em todas as referências, evitando manifesto inválido.
- Introduz M2a estrutural / M2b de fidelidade visual, com checkpoint obrigatório e referência fotográfica identificada.
- Exige revisão visual com lista de defeitos e smoke test de exportação cedo; respeita limites do MCP.
- Inclui `references/WORKFLOW_CHECKPOINTS.md` e prompt `/goal` recomendado em `examples/GOAL_SEVEL_FIRST_PASS.md` (também fornecido separado).

## Instalar no projeto

Este pacote ZIP contém a pasta `sevel-freecad-vision/`, que deve ser extraída sob `.agents/skills/` na raiz do repositório:

```bash
cd /mnt/projects/Projects/emu8051-tty
mkdir -p .agents/skills
unzip /caminho/para/sevel-freecad-vision.zip -d .agents/skills
```

O Codex carrega skills locais em `.agents/skills` e pode ser solicitado com `$sevel-freecad-vision`.

## Etapa obrigatória: gabarito CAD validado **antes da fundição**

A partir desta versão, M1 tem um portão explícito: nenhum componente da fundição deve ser construído antes do gabarito mestre passar na validação geométrica e na auditoria das fontes.

Os valores **Ø86,4 mm** e **curso 67,4 mm** pertencem diretamente ao manual do Tipo 1.6 SPI 82 cv. Os entrecentros **93 / 96 / 93 mm** aparecem numa tabela externa do SEVEL injetado **92 cv**; são uma hipótese útil para prévia, **pendente de confirmação para a variante de 82 cv**. Os centros derivados X são `0, 93, 189, 282 mm`. Não igualar o diâmetro do furo do cilindro ao diâmetro real da abertura da junta.

```bash
cd /mnt/projects/Projects/emu8051-tty
mkdir -p build/sevel-cad/datums
cp .agents/skills/sevel-freecad-vision/assets/reference_parameters.example.json \
  build/sevel-cad/parameters.json

python3 .agents/skills/sevel-freecad-vision/scripts/build_reference_frame.py \
  --params build/sevel-cad/parameters.json \
  --output build/sevel-cad/datums
```

Resultados: `reference_frame.json`, `reference_frame.svg`, `reference_gate.json`. O status inicial é `PASS_PROVISIONAL_FOR_VISUAL_ONLY`, pois o entrecentros pertence à fonte de outra variante. A opção `--require-confirmed` gera o relatório mas retorna código 2 para impedir progresso enquanto essa hipótese não for substituída por uma fonte confiável da variante-alvo.

Para ver os círculos no FreeCAD, peça ao Codex uma chamada MCP `execute_code` com o seguinte conteúdo Python (ajustando o diretório do projeto):

```python
from pathlib import Path
root = Path('/mnt/projects/Projects/emu8051-tty')
FRAME_MANIFEST_PATH = str(root / 'build/sevel-cad/datums/reference_frame.json')
FRAME_OUTPUT = str(root / 'build/sevel-cad/models/master_datum.FCStd')
script = root / '.agents/skills/sevel-freecad-vision/scripts/freecad_reference_from_json.py'
exec(compile(script.read_text(), str(script), 'exec'))
```

Depois, o agente deve chamar `get_view` no plano `Top`, validar os quatro círculos geometricamente e salvar uma captura antes de construir os volumes do bloco. A construção usa **sempre** os centros do mesmo manifesto, sem repetir valores como constantes dispersas nos scripts.

O script FreeCAD precisa ser exercitado na instância GUI real; sua API foi escrita para `FreeCAD`, `Part` e o contrato MCP, mas somente a parte Python padrão foi testada neste ambiente.

## Smoke test local da imagem de juntas

O PNG e SVG fornecidos estão incluídos para comparação, com autorização implícita apenas para uso nesta entrega. O PNG original continua sem modificações.

```bash
python3 -m venv .venv-gasket
.venv-gasket/bin/pip install numpy opencv-python-headless Pillow
.venv-gasket/bin/python .agents/skills/sevel-freecad-vision/scripts/gasket_extract.py \
  .agents/skills/sevel-freecad-vision/assets/source_head_gasket.png \
  --output build/sevel-cad/gasket --nominal-bore-mm 86.4
.venv-gasket/bin/python -m unittest discover -s .agents/skills/sevel-freecad-vision/tests -v
```

O script escreve quatro arquivos: um SVG com contornos separados, um JSON geométrico, um PNG de comparação e um relatório. A escala é **aproximada** porque a dimensão física real da abertura da junta não foi medida; o diâmetro 86,4 mm é o furo nominal do cilindro.

Para configurar com diâmetro da **abertura da junta realmente medido**:

```bash
python3 .agents/skills/sevel-freecad-vision/scripts/gasket_extract.py \
  PhotosMotor/D_NQ_NP_2X_666447-MLB115951529104_092026-F-juntas-do-cabecote-fibra-fiat-tipo-16-8v-sevel_bk.png \
  --output build/sevel-cad/gasket --actual-opening-mm 87.5
```

O valor `87.5` é **apenas um exemplo da sintaxe**. Não utilize esse número como diâmetro real sem medição.

## Montar prancha de revisão visual

Após salvar capturas do FreeCAD em `build/sevel-cad/evidence`, gere uma prancha de fotos contra capturas:

```bash
.venv-gasket/bin/python .agents/skills/sevel-freecad-vision/scripts/make_review_sheet.py \
  --photos PhotosMotor --captures build/sevel-cad/evidence \
  --part bloco --output build/sevel-cad/reports/block_review_sheet.png
```

A comparação é lado a lado, sem normalização de perspectiva ou métricas enganadoras de similaridade. O agente deverá reconhecer poses e correspondências.

## Rodar no FreeCAD por MCP

O servidor `neka-nat/freecad-mcp` deve estar conectado ao Codex, com o addon FreeCAD aberto e RPC ativo. O gerador da junta só executa dentro do ambiente Python do FreeCAD, não dentro do venv do processador de imagens.

Exemplo de código a enviar a `execute_code`:

```python
from pathlib import Path
root = Path('/mnt/projects/Projects/emu8051-tty')
script = root / '.agents/skills/sevel-freecad-vision/scripts/freecad_gasket_from_json.py'
MANIFEST_PATH = str(root / 'build/sevel-cad/gasket/head_gasket_geometry.json')
GASKET_OUTPUT = str(root / 'build/sevel-cad/models/gasket_reference.fcstd')
exec(compile(script.read_text(), str(script), 'exec'))
```

Peça ao agente **capturas `get_view` e revisão visual** em vez de só confirmar que um script retornou sucesso.

## Exemplo de prompt para Codex

```text
$sevel-freecad-vision

Trabalhe no SEVEL 1.6 SPI 82 cv usando as imagens locais em PhotosMotor,
os manuais e o FreeCAD MCP conectado.

Comece por M0 e M1: inventário de referências e gabarito dos cilindros.
Primeiro analise e calibra a junta do cabeçote com o script incluso.
Não adote os entrecentros de imagem como medida confirmada.

Crie geometria por parâmetros, valide B-rep, faça screenshots via get_view,
compare com os desenhos e fotografias correspondentes e corrija diferenças.
Salve scripts, FCStd, relatório de dimensões e screenshots em build/sevel-cad.
```

## Limitações desta entrega

- Os scripts de extração raster, SVG e JSON foram executados e conferidos com o PNG fornecido.
- Os scripts `freecad_*.py` foram escritos a partir da API pública, porém **não foram executados em uma instância FreeCAD neste ambiente**. O agente deve validá-los e ajustar a versão instalada.
- As fotos listadas em `PhotosMotor/` não foram recebidas, apenas os nomes; deverão ser inspecionadas pelo agente no computador do usuário.
- O SVG vetorial é um gabarito visual aproximado, impróprio para fabricação ou certificação dimensional sem medições adicionais.
