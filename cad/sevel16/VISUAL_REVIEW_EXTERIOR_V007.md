# Polimento externo do SEVEL 1.6 SPI 8V · v007

A montagem publicada no Lab reúne duas alterações paramétricas. Na admissão, alargamos os ombros onde cada par de dutos se une ao corpo central. No fundo do cárter, deslocamos em conjunto o bujão, a passagem e o ressalto para o lado dos recuos da flange. Os 26 mm transversais do bujão e as seções dos ombros são estimativas fotográficas. [Montagem FreeCAD](../../build/sevel-cad/models/SEVEL_Accessories_A5_v007_DrainReview.FCStd) · [Motor montado](../../build/sevel-cad/polish/exterior-01/drain-assembly-after.png)

| Lote | Evidência e decisão |
|---|---|
| v006 · admissão | Fotos 713001 e 628178, duas vistas da peça. O primeiro perfil se autointersectava. O segundo passou no BOPCheck nativo, preservou as oito bocas e as duas cavidades de cada coletor. O Lab carregou 492 triângulos a menos na malha da admissão. [Antes e depois](../../build/sevel-cad/polish/exterior-01/reports/INT-01.jpg) · [Ficha](../../build/sevel-cad/polish/exterior-01/reports/INT-01.md) |
| v007 · bujão | Fotos 845764, 679775 e 780830. O bujão preserva a forma e o contato com o assento. A verificação isolada dos STEPs do bujão e do cárter passou. A contagem de triângulos das duas peças foi preservada. [Antes e depois](../../build/sevel-cad/polish/exterior-01/reports/PAN-04.jpg) · [Ficha](../../build/sevel-cad/polish/exterior-01/reports/PAN-04.md) |

O FCStd v007 tem SHA-256 `ec0fa4ed9557d42e7dcb99bf64c7f8f67866ffd9340a67efe7fb3f3d18f888c0`. Após a queda de energia, o original passou na verificação de CRC e reabriu. A segunda exportação reabriu o STEP com 224 sólidos válidos. Os arquivos de runtime contêm 224 instâncias e 105 malhas únicas. [STEP da montagem](../../build/sevel-cad/runtime_exports/SEVEL_Accessories_A5_v007_DrainReview/v002/geometry/assembly.step) · [OBJ e manifesto](../../build/sevel-cad/runtime-assets/d7ce0472d8b0a2a39404dc619baed68e1d53d541ef1a90ba9c7087f43b000545/parts_manifest.json)

## Movimento, exportação e recarga

A comparação v005 → v006 → v007 preservou o datum, o rig, os materiais, os IDs e as propriedades de instância. Mudaram três malhas ao longo dos dois lotes. Na v007, 13 peças herdadas também mudaram de hash B-rep. A comparação linha a linha dos arquivos internos encontrou apenas a troca do campo de flags `1100000` por `0100000`, sem alteração nas coordenadas ou nos OBJ correspondentes. [Diferenças por lote](../../build/sevel-cad/polish/exterior-01/reports/incremental-comparison.json)

O teste de poses do Lab comparou dez fases, incluindo 0°, 359°, 360° e 720°. A varredura da admissão cobriu 74 fases. A do cárter calculou 938 interseções candidatas em 50 fases. No Native Lab MCP, a mesma câmera, fase e ROM local produziram o mesmo estado de replay. Entre v006 e v007, 2035 pixels mudaram acima do limiar na vista isolada do dreno. F5 carregou a nova versão, rejeitou uma malha danificada e uma revisão ausente e voltou à anterior com a simulação em andamento. [Comparação no Lab](../../build/sevel-cad/polish/exterior-01/lab-drain/drain-comparison.png) · [Corte a 90°](../../build/sevel-cad/polish/exterior-01/lab-drain/reexport-section-gpu.png) · [Log de F5](../../build/sevel-cad/polish/exterior-01/lab-drain/reload-native.log)

O BOPCheck nativo ampliado do cárter aborta na v005 e na v007. No STEP da admissão, o verificador ampliado reporta 52 arestas com diagnóstico de curva sobre superfície na v005 e 58 na v006. O teste normal de sólido reaberto passa nas duas versões. Essa limitação importa para reutilizar a superfície importada em modelagem de precisão. [Geometria da admissão](../../build/sevel-cad/polish/exterior-01/reports/INT-01-geometry.json) · [Geometria do cárter](../../build/sevel-cad/polish/exterior-01/reports/PAN-04-geometry.json)

## Ensaio complementar de arredondamento no cárter

Na parede já oca, a primeira operação altera a geometria usada pela segunda. Em cópias da v007, selecionamos a aresta longitudinal no lado +Y do patamar profundo e testamos as duas ordens, selecionando novamente a aresta após o primeiro fillet. Para a parede nominal de 3 mm, usamos 8 mm na concavidade interna e 11 mm na convexidade externa. Cada etapa produziu um sólido válido nas duas ordens. O STEP reabriu nas duas, mas o BOPCheck ampliado apontou 23 arestas com diagnóstico de curva sobre superfície em cada caso. O ensaio ficou separado da montagem publicada. [Resultados por etapa](../../build/sevel-cad/polish/exterior-01/reports/PAN-01-sequential.json)

## Selecionar ou voltar a uma revisão

O Lab de desenvolvimento em `build-lab` e o registro em `build/sevel-cad/runtime-assets` apontam para a v007. Para abrir uma revisão somente naquela execução, passe o diretório dela em `--cad-assets`. Para trocar por F5, abra o Lab com `--cad-assets build/sevel-cad/runtime-assets`, selecione a revisão com o utilitário abaixo e pressione F5.

| Revisão | SHA-256 do manifesto |
|---|---|
| v005 · referência preservada | `294b11f14e15c5951e9a4fc5e0c16f32ee6e3af9c55d38ae5b4f40058e0ff2ac` |
| v006 · admissão | `6e7090cb28942a4c87d7d3acc20e8d786323f4bbd62c972b4dc1e9e0769f0736` |
| v007 · admissão e dreno | `d7ce0472d8b0a2a39404dc619baed68e1d53d541ef1a90ba9c7087f43b000545` |

Por exemplo, para voltar à v006 da admissão, execute na raiz do projeto:

```sh
python tools/sevel_cad_assets.py build/sevel-cad/runtime-assets --revision 6e7090cb28942a4c87d7d3acc20e8d786323f4bbd62c972b4dc1e9e0769f0736 --checker build-lab/sevel-cad-check
```

O arredondamento integral do cárter e os dois ensaios da saia do bloco ficaram nos arquivos de revisão. Ambos apresentaram regressões na verificação STEP. A furação da flange exige conciliar os apoios do conjunto. A divisória interna depende de conhecer a passagem do pescador. As tampas de outras variantes permaneceram como referências comparativas. [Auditoria e decisões](../../build/sevel-cad/polish/exterior-01/reports/issues.md) · [Fotos pendentes](FOTOS_PENDENTES.md)

Os geradores da [admissão](build_intake_shoulder_review.py) e do [dreno](build_drain_review.py) recebem a referência de entrada e um destino livre. Cada exportação conserva o próprio FCStd, os parâmetros e o datum usados. [Baseline](../../build/sevel-cad/polish/exterior-01/baseline/baseline.json) · [Parâmetros modificados](../../build/sevel-cad/polish/exterior-01/reports/parameters.patch) · [Diferenças nos geradores e testes](../../build/sevel-cad/polish/exterior-01/reports/generators.patch)
