# Pacote independente do caminho original

`portable_delivery.py` cria `build/sevel-cad/deliveries/<documento>_vNNN/`.
Cada pacote contém o FCStd selecionado, STEP, OBJ por peça, poses, parâmetros,
datum, fontes Python/C++, geradores anteriores, modelos de origem e relatórios.
`delivery.json` lista os arquivos e seus hashes. O pacote é um checkpoint;
não representa conclusão automática do objetivo nem certificação dimensional.

Criar na raiz do projeto, após exportação e consolidação do checkpoint:

```bash
python cad/sevel16/portable_delivery.py SEVEL_Accessories_A5_v002
```

Copie a pasta gerada para o destino desejado. Dentro dessa pasta, execute:

```bash
python cad/sevel16/check_portable_delivery.py
```

O verificador exige Python 3 e compilador C++20. Confere todos os hashes,
executa os testes analíticos, recompila o carregador/renderizador existente
e carrega a calibração e as poses exportadas. As provas novas ficam em
`verification/`; os relatórios históricos permanecem intactos. A renderização
é a prova do RecordingRenderer, não uma nova interface interativa do Lab.

O manifest operacional usa caminhos relativos à raiz do pacote. Os arquivos
de pose seguem a mesma regra; execute o renderizador com essa raiz como CWD.
Vértices estão em metros no espaço local da peça, com conversão `(x,z,-y)`
aplicada uma vez. Não recentralize os objetos nem reaplique essa conversão.
Materiais, IDs, pivôs e números das poses são comparados aos originais.

No console Python do FreeCAD, em uma sessão sem módulos de outra cópia:

```python
from pathlib import Path
import json, sys
root = Path('/caminho/para/o/pacote')
sys.path.insert(0, str(root / 'cad/sevel16'))
import FreeCAD as App
import config, phase_controller
index = json.loads((root / 'delivery.json').read_text())
doc = App.openDocument(str(root / 'build/sevel-cad/models' / (index['document'] + '.FCStd')))
params, frame = config.load()
panel = phase_controller.show(doc)
```

O painel controla 0–720°. Ao fechar, restaura a fase e remove as prévias de
molas. Para repetir reconstrução e 145 poses sem sobrescrever prova histórica,
feche o painel e use `check_rebuild.run(doc, root/'verification/rebuild.json')`.
O arquivo de destino deve ser novo. Essa verificação inclui os protótipos
inferiores e alterações de curso/cosmética em cópias; não substitui a cadeia
completa de colisões nem a revisão visual.

Para a montagem Accessories, a verificação CAD independente completa deve
rodar em um processo FreeCAD novo, com `cad/sevel16` do pacote no `sys.path`:
`import check_portable_cad; check_portable_cad.run()`.
Ela confere os hashes antes/depois, abre os 218 sólidos, audita a cadeia
herdada, reconstrói 20 acessórios e 13 protótipos móveis e mede 145 poses.
Os resultados ficam em `verification/`, sem sobrescrever provas empacotadas.
O coletor de admissão mantém a ressalva de comparação numérica amostrada.

Os parâmetros vêm do snapshot aprovado do checkpoint selecionado. A comparação
é de conteúdo JSON; a formatação do antigo arquivo pode ter outro hash.
O manifest registra ambos os contextos sem atribuir ao modelo dados posteriores.
PDFs e fotos originais não são duplicados; caminhos e hashes de referência
estão em `build/sevel-cad/reports/moving_sources.json`. São necessários para
reexaminar as fontes, mas não para reproduzir poses ou carregar os modelos.
Os caminhos absolutos em relatórios históricos descrevem o ambiente de origem.
