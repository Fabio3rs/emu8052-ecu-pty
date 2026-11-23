# SEVEL 1.6 i.e. 82 cv — conjunto móvel

Checkpoint atual: `build/sevel-cad/models/SEVEL_Accessories_A5_v002.FCStd`,
218 sólidos, incluindo velas, coletores e carcaça/polia da bomba d'água.
Consulte `DELIVERY_AUDIT.md` e `build/sevel-cad/reports/final_delivery.json`
para a auditoria e a verificação da entrega, quando publicada.

Para entregar um checkpoint com fontes, parâmetros e caminhos independentes
da instalação original, consulte `PORTABLE_DELIVERY.md`. O teste de relocação
recompila o verificador C++ e confere poses e materiais contra os originais.

Fontes únicas: `build/sevel-cad/parameters.json` e
`build/sevel-cad/datums/reference_frame.json`. O carregador verifica o datum
por recálculo e rejeita divergências. Não altera o gabarito.

O catálogo local `PhotosMotor/Tipo 1.6 - Tipo 1.6 4P 1.6 SPI 8V Gasolina
1993-1995.pdf` tem 426 páginas, código 160.362.1. Índice de referências e
ressalvas em `catalog_source.py` e `reports/moving_sources.json`:

| Páginas do PDF | Componentes |
|---|---|
| 10–17 | Bloco, cabeçote, gaiola e juntas |
| 22–23 | Cárter, flange, junta e bujão M22×1,5 |
| 32–38 | Correia, polias, proteções e trem de válvulas |
| 67–70 | Coletores de admissão e escape |
| 83–84 | Respiro, mangueira e retorno de óleo |
| 89–90 | Bomba d'água e acionamento separado por acessórios |

Os esquemas identificam peças e montagem; não são desenhos cotados para
medir inclinações ou raios. O respiro permanece com ângulo provisório.

Para reproduzir os acessórios sobre Closures v001, com os parâmetros atuais:

```python
import build_accessories_checkpoint
from config import OUTPUT
doc, report = build_accessories_checkpoint.run(OUTPUT/'trials/accessories_v007')
```

O gerador cria outra versão sem sobrescrever o modelo. Para verificar os
20 componentes em um processo FreeCAD independente, execute
`check_accessories_rebuild.run('SEVEL_Accessories_A5_v002')`.
O coletor de admissão tem comparação amostrada de superfícies/bordas após
falha da subtração OCCT; o relatório distingue isso da identidade B-rep.
Para animar o checkpoint atual, abra seu FCStd e use `phase_controller.show(doc)`.
Mantenha a referência ao painel e feche-o antes de salvar ou exportar.

Para reproduzir tampa/cárter do checkpoint Closures v001 no console FreeCAD,
com `cad/sevel16` no `sys.path` e os parâmetros correspondentes carregados:

```python
import build_closures_checkpoint
from config import OUTPUT
doc, report = build_closures_checkpoint.run(
    OUTPUT / 'trials/closures_v004')
```

Isso cria uma nova versão, usando o predecessor preservado e sua prova
arquivada. Para conferir somente a reconstrução das seis peças num processo
FreeCAD headless: `import check_closure_rebuild; check_closure_rebuild.run()`.

Testes sem FreeCAD, na raiz do repositório:

```bash
python -m unittest discover -s cad/sevel16 -p 'test_*.py' -v
python cad/sevel16/validate_analytic.py
```

Construção no console Python do FreeCAD ou via `execute_code` do MCP:

```python
from pathlib import Path
import sys
root = Path('/mnt/projects/Projects/emu8051-tty')
sys.path.insert(0, str(root / 'cad/sevel16'))
p = root / 'cad/sevel16/build_moving.py'
exec(compile(p.read_text(), str(p), 'exec'), {'__file__':str(p), '__name__':'__main__'})
```

O gerador cria a próxima versão livre `SEVEL_Moving_A2_vNNN.FCStd`, salva,
fecha e reabre. O bloco v008 original não é alterado. Todos os corpos móveis
têm origem local mecânica e recebem pose absoluta no referencial mestre.

Selecionar uma fase, usando o documento criado pelo gerador:

```python
import FreeCAD as App
from config import load
from assembly import apply_pose
params, frame = load()
doc = App.getDocument('SEVEL_Moving_A2_v003')
apply_pose(doc, 90, params, frame)
```

`Phase.ThetaDeg` registra a última pose aplicada; editar essa propriedade
isoladamente não aciona a montagem. Não há integração acumulativa.

Para construir o trem de válvulas sobre o checkpoint A2:

```python
import build_valvetrain
doc = build_valvetrain.run()
```

O gerador salva a próxima versão livre `SEVEL_ValveTrain_A3_vNNN.FCStd`.
No documento A3, abrir o controlador de fase:

```python
import phase_controller
panel = phase_controller.show(doc)
```

O painel oferece fase contínua 0–720° e reprodução a 30 graus de virabrequim
por segundo. As molas usam malhas de seção circular constante durante a
prévia. Feche o painel antes de salvar/exportar: ele remove essas malhas e
restaura a pose inicial e as molas CAD. Mantenha a variável `panel` viva.

Verificadores A3: `check_cam_contacts.run(doc)` mede o came final;
`check_valve_dimensions.run(doc)` mede interfaces; `check_controller.run(panel)`
exercita e fecha o painel. `check_valvetrain.run_cycle(doc)` deve executar
em FreeCAD **headless**, pois aplica poses e recalcula molas na cópia aberta
nesse processo. Não o execute numa thread de background com documento da GUI.
O relatório incremental só passa a aprovado após todas as fases terminarem.

`check_moving.snapshot(doc)` deve rodar na thread da GUI. A função
`check_moving.scan(parts, params, frame, angles, report_name)` usa apenas
cópias de shapes e pode rodar por `execute_code_async`. Aguarde o job terminar
antes de alterar documentos ou recarregar módulos. O relatório não sobrescreve
arquivos de mesmo nome.

As alturas do deck e de compressão, comprimento da biela, formas externas e
perfil dos cames são provisórios. O perfil sintético usa a envolvente de
contato de um tucho plano, com pico e eventos de conferência do manual;
não representa uma medição do comando original.

Exportar as malhas de um checkpoint que já possui STEP e `parts_manifest.json`,
com o painel fechado e fase zero (console FreeCAD):

```python
import export_meshes, prepare_mesh_probe
folder = export_meshes.run(doc)
prepare_mesh_probe.run(doc, folder)
```

Cada execução cria `exports/<documento>/meshes_vNNN/`. Os OBJ têm vértices
locais em metros, normais suavizadas com limite de 30° e batches compatíveis
com índices de 16 bits. O manifest associa geometria compartilhada, materiais
por instância e poses absolutas; não aplicar a conversão CAD→runtime novamente.
As molas exportadas são poses estáticas; a prévia contínua ainda usa o
controlador FreeCAD e sua malha deformável de seção circular.

Prova de carga e pose no carregador e renderizador de registro existentes:

```bash
c++ -std=c++20 -O2 -Wall -Wextra -Werror -Iinclude \
  -Ithird_party/open-engine-sim/include cad/sevel16/check_mesh_renderer.cpp \
  third_party/open-engine-sim/src/authored_mesh_library.cpp \
  -o build/sevel-cad/check_mesh_renderer
python cad/sevel16/check_mesh_package.py <pasta>
```

O verificador mede as caixas de todas as peças carregadas e transformadas contra
o CAD, verifica normais e gera SVG com `lab::RecordingRenderer`. É uma prova
do caminho de carga/renderização, não integração do painel interativo do Lab.
O teste de calibração usa duas instâncias, cores diferentes, pivô deslocado
e rotações compostas. Os SVG são projeções sem ocultação por profundidade.
O adaptador exclui faces voltadas para trás para evitar cancelamento do
preenchimento SVG de superfícies fechadas. `renderer_checks.json` preserva
hashes, medidas, diferença 0/90° e igualdade exata das poses/SVG de 0/720°
para componentes com período compatível. Componentes de período próprio,
como o tensor, permanecem nas quatro poses completas e têm sua transformação
final verificada separadamente pela relação angular declarada no manifest.

Regressão do carregador, numa árvore configurada com Lab/GUI/testes ativos:
`cmake --build .work/lab-build --target lab_mesh_asset_test -j2` e
`ctest --test-dir .work/lab-build -R '^LabMeshAsset\.' --output-on-failure`.

Checkpoint do volante (console FreeCAD, painel de animação fechado):

```python
import build_flywheel_checkpoint, check_flywheel, export_step, parts_manifest
doc = build_flywheel_checkpoint.run()
baseline = App.getDocument('SEVEL_ValveTrain_A3_v003')
check_flywheel.run(doc, baseline)
export_step.run(doc)
parts_manifest.run(doc)
```

O gerador cria a próxima versão `SEVEL_Flywheel_A4_vNNN`, preserva A3 v003
e exige que os parâmetros herdados coincidam com seu snapshot. As oito
peças novas usam `MotionType=crank`, portanto o mesmo controlador de fase.
`check_flywheel` compara os B-reps herdados, verifica contatos e exclusão
contínua por limites axiais, além das 145 poses. Ele não aprova componentes
da distribuição ainda não construídos. Conferir `VISUAL_REVIEW_A4.md`.

Distribuição externa, incluindo a ponta dianteira do auxiliar (console FreeCAD):

```python
import build_timing_checkpoint, check_timing, capture_timing
doc = build_timing_checkpoint.run()
baseline = App.getDocument('SEVEL_Flywheel_A4_v001')
check_timing.run(doc, baseline)
capture_timing.run(doc)
export_step.run(doc)
parts_manifest.run(doc)
```

O gerador usa o volante A4 v001 como origem e cria `SEVEL_Timing_A4_vNNN`.
Execute na thread GUI. Em uma sessão já aberta após editar os módulos,
recarregue `kinematics`, `assembly` e `phase_controller` nessa ordem antes de
abrir o controlador, para atualizar os imports. O tensor possui período
angular próprio; `check_controller` distingue isso da periodicidade 720°
do comando/válvulas. A roda fônica e a porção interna do auxiliar ainda não
estão incluídas neste checkpoint. Referências e limites em `VISUAL_REVIEW_A4.md`.

Polia de acessórios, roda fônica e sensor (console FreeCAD):

```python
import build_trigger_checkpoint, check_trigger, capture_trigger
doc = build_trigger_checkpoint.run()
baseline = App.getDocument('SEVEL_Timing_A4_v002')
check_trigger.run(doc, baseline)
capture_trigger.run(doc)
export_step.run(doc)
parts_manifest.run(doc)
folder = export_meshes.run(doc)
prepare_mesh_probe.run(doc, folder)
```

O gerador parte de Timing A4 v002 e permite apenas a extensão declarada
da ponta do virabrequim entre os parâmetros herdados: 35 → 52 mm. Os demais
181 B-reps permanecem iguais. A extensão de 17 mm é uma hipótese de montagem;
roscas e aperto não são simulados. O padrão 60−2 e sua fase são provisórios;
o entreferro de 1 mm foi escolhido dentro da faixa manual de 0,5–1,5 mm.
O ângulo do sensor e a fase da roda são parâmetros independentes; a fase
de sincronismo com PMS continua desconhecida. Não inferir sinal de ECU
dos eventos geométricos de passagem dos centros dos dentes.

Para reproduzir checkpoints históricos, usar seus snapshots de parâmetros.
Os geradores antigos rejeitam corretamente a ponta de 52 mm quando a origem
validada contém 35 mm; não remover essa proteção para reutilizar a geometria.

Eixo auxiliar completo, segundo mancal e passagem interna (thread GUI):

```python
import json
from config import load, OUTPUT
import build_auxiliary_checkpoint, check_auxiliary, auxiliary_cycle, auxiliary_pose_checks
doc = build_auxiliary_checkpoint.run()
baseline = App.getDocument('SEVEL_Trigger_A4_v001')
params, frame = load()
report, targets = check_auxiliary.prepare(doc, baseline)
report['pose_checks'] = auxiliary_pose_checks.run(doc, params, frame)
moving, fixed, excluded = auxiliary_cycle.inputs(doc, baseline, params, frame, targets)
name = doc.Name
angles = sorted(set(range(0,721,5)) | set(json.loads(
    (OUTPUT/'reports/SEVEL_ValveTrain_A3_v002_valvetrain_cycle.json').read_text())['target_angles']))
```

Executar a seguir apenas o cálculo sobre cópias de shapes via
`execute_code_async`, aguardando `get_async_status` terminar:

```python
result = auxiliary_cycle.run(name, report, targets, moving, fixed, excluded, params, frame, angles)
```

Depois do PASS, voltar à thread GUI para `capture_auxiliary.run(doc)`,
`export_step.run(doc)` e `parts_manifest.run(doc)`. Exportar/conferir malhas
com o procedimento anterior. A v001 do auxiliar falhou por extrapolação
radial do loft suave; a v002 usa dentes regrados e preserva esse raio.
O eixo conserva seu ID anterior, embora agora contenha ambos os mancais.
O perfil dos dentes e as medidas axiais são estimativas; não há engrenamento
com uma bomba de óleo modelada. A modificação do bloco é restrita à passagem
e ao apoio traseiro, sem alterar os datums nem as superfícies dos cilindros.

Revisão da seção inclinada da gaiola, mantendo o conjunto Auxiliary A4 v002
(thread GUI, com os parâmetros correntes e sem animação em execução):

```python
import build_carrier_checkpoint, check_inclined_carrier, capture_carrier
doc = build_carrier_checkpoint.run()
baseline = App.getDocument('SEVEL_Auxiliary_A4_v002')
check_inclined_carrier.run(doc, baseline)
capture_carrier.run(doc)
export_step.run(doc)
parts_manifest.run(doc)
```

O gerador cria `SEVEL_Carrier_A3_vNNN` e substitui apenas a gaiola fixa.
A verificação compara as 188 peças herdadas e testa a nova fundição contra
envelopes de movimento contínuo e separações espaciais. Os ângulos de
fundição são estimativas independentes dos eixos do comando e das válvulas.
O catálogo local de 426 páginas corrobora as interfaces e identidades;
não calibra raios, ângulos ou entrecentros. `python cad/sevel16/inventory.py`
regenera sua procedência e as ambiguidades das tabelas sem editar o PDF.

Auditoria do checkpoint atual Head v002:

```bash
python cad/sevel16/consolidate_head_validation.py
```

O comando confere hashes do CAD, parâmetros, relatórios, malhas, capturas e
prova do renderizador antes de escrever `reports/kinematics_validation.json`.
Inclui nove estágios de colisões e dez relatórios diretos do Head v002.
A consolidação histórica do Carrier foi preservada integralmente em
`reports/kinematics_validation.carrier.da8db84a9817.json`; os incrementos
continuam ligados a esse hash. `head_proof_chain.py` também exige cobertura
completa dos pares novos, sem duplicatas ou alterações de parâmetros herdados.

`consolidate_validation.py` permanece específico do Carrier e recusa os
parâmetros atuais. Não executar `validate_analytic.py` sobre o relatório
analítico histórico usado por essa cadeia. Para a versão atual, usar
`validate_analytic.run('SEVEL_Head_A3_v002_analytic.json')` em Python comum,
com `cad/sevel16` no `sys.path`. As pendências estão em `DELIVERY_AUDIT.md`.

As provas atuais incluem `check_dimensions.run(doc)`,
`check_valve_dimensions.run(doc)`, `check_cam_contacts.run(doc)`,
`check_rebuild.run(doc)` e `check_controller.run(phase_controller.show(doc))`
na thread GUI. A varredura inferior usa as 68 peças identificadas no
relatório de reutilização A2, copiadas do documento atual, e as 220 fases
de `check_cam_contacts.angles(params)`. Passar `source_sha256` à função
`check_moving.scan` e executar somente sobre cópias fora da GUI. Preservar
o relatório existente ao repetir: escolher outro nome e auditar a substituição.

`capture_current_sections.run(doc)` produz documentos derivados longitudinal
e transversal C1 em 90°, salva/reabre cada um e restaura a fase original.
Ele recusa sobrescrever cortes existentes. São cortes estáticos; o controle
de fase deve ser aplicado ao documento de montagem, não aos derivados.

## Cabeçote inferior: checkpoint Head A3 v001

O modelo atual tem 192 sólidos: as 189 peças do Carrier v001 e três adições
fixas. Ver `VISUAL_REVIEW_HEAD.md` e `reports/SEVEL_Head_A3_v001_head_validation.json`.
Os relatórios consolidados do Carrier continuam associados aos parâmetros
originais daquele checkpoint. Não substituí-los por resultados dos parâmetros
atuais: `consolidate_validation.py` recusa essa mistura de hashes.

Para reconstruir o incremento, preparar na thread GUI, com baseline a 0°:

```python
import build_head_checkpoint, head_envelopes, check_head_increment, check_head_interfaces
params, frame = config.load()
baseline = App.getDocument('SEVEL_Carrier_A3_v001')
envelopes = head_envelopes.prepare(baseline, params, frame)
old_shapes = {o.Name:o.Shape.copy() for o in baseline.Objects if hasattr(o, 'Shape')}
```

Calcular apenas shapes independentes em `execute_code_async` e aguardar o job:

```python
shapes, metrics = build_head_checkpoint.generate(params, frame)
interfaces = check_head_interfaces.run(shapes, old_shapes, params, frame)
verification = check_head_increment.scan(shapes, envelopes)
```

Depois, na thread GUI, criar a próxima versão sem sobrescrever arquivos:

```python
doc, report = build_head_checkpoint.run(baseline, shapes, metrics, verification, interfaces, params)
export_step.run(doc)
parts_manifest.run(doc)
capture_head.run(doc)
```

`check_head_rebuild.run(saved_shapes, params, frame, Path(doc.FileName))`
reconstrói as três adições e mede a diferença B-rep; fornecer cópias dos
shapes, permitindo execução assíncrona. Para malhas, seguir o fluxo
`export_meshes` → `prepare_mesh_probe` → `check_mesh_package.py` descrito acima.
O corte `*_ExhaustSection` é estático. O controlador de fase opera na montagem.

As câmaras, galerias de água, contornos de fundição e apoios internos de
mola ainda têm lacunas documentadas. Passar nas verificações de interferência
não significa que esses detalhes já correspondem ao motor real.

## Apoios inferiores das molas: Head A3 v002

Nesta revisão, a lacuna dos apoios internos foi eliminada mantendo as alturas
das molas e todos os movimentos. Os dois sólidos de apoio são regiões de um
único prato inferior com ressalto, não duas peças de catálogo. A v001 mantém
sua geometria e seus relatórios anteriores.

Na thread GUI, preparar cópias e envelopes do baseline a 0°:

```python
import build_seat_checkpoint, check_spring_seats, head_envelopes
params, frame = config.load()
baseline = App.getDocument('SEVEL_Head_A3_v001')
replacements = build_seat_checkpoint.generate(params, frame)
old_shapes = {o.Name:o.Shape.copy() for o in baseline.Objects if hasattr(o, 'Shape')}
envelopes = head_envelopes.prepare(baseline, params, frame)
```

`check_spring_seats.run(replacements, old_shapes, envelopes, params, frame)`
pode ser executado em background. Após obter seu relatório `verification`,
na thread GUI:

```python
doc, report = build_seat_checkpoint.run(baseline, replacements, verification, params)
export_step.run(doc)
parts_manifest.run(doc, 'cad/sevel16/build_seat_checkpoint.py')
capture_spring_seats.run(doc)
```

Seguir a exportação OBJ e verificação de poses já descritas. O modo novo de
`valve_parts.build` depende de `spring_seat_support_estimated`; snapshots
anteriores sem esse campo continuam reproduzindo os apoios antigos.
Ver `VISUAL_REVIEW_SEATS.md` para validação e `GLB_CAPABILITY.md` para as
tentativas de exportação nativa que falharam nesta instalação.
