# Fundição do auxiliar — Casting A4 v002

Atual: `models/SEVEL_Casting_A4_v002.FCStd`, derivado de `trials/enclosure_v005`.
Transições cúbicas mais amplas e término afunilado substituem o perfil tubular;
o alívio frontal preserva a face anular do respiro. 192 sólidos válidos,
191 peças herdadas idênticas, 220 poses e 3.730 testes B-rep sem colisões.
Folga auxiliar: 0,999999942 mm; mínimo nos 40 raios: 7,035709 mm.
Dimensões, reconstrução, controlador, STEP, OBJ e renderer aprovados.
O agregado atual aponta para v002. Revisões detalhadas e capturas:
`VISUAL_REVIEW_ROOT_BLEND.md` e `VISUAL_REVIEW_CASTING_V002.md`.

## Histórico preservado — Casting A4 v001

Baseline preservado: `models/SEVEL_Head_A3_v002.FCStd`, 192 sólidos.
Novo modelo: `models/SEVEL_Casting_A4_v001.FCStd`, 192 sólidos, 191 inalterados.
SHA-256: `dde2e7fd7ddc363898757398ff1ee0f397a69195b77d45c7351a5c0b71ffe179`.
Artefatos novos em `build/sevel-cad/trials/enclosure_v003/`:
`block.brep`, `added.brep`, `parameters.json`, `validation.json`, `block.step`,
`block.obj` e `export_checks.json`.

O loft lateral acrescenta 249.567,146837 mm³, sem remover material original.
Os cilindros ficam fora do domínio da alteração por 14,8 mm em Y; a face
de vedação do cárter fica afastada 51 mm em Z. Filtro e respiro permanecem
abertos. O contorno exterior e a transição axial são hipóteses de fundição.

A primeira tentativa atingiu `C1_Rod` (565,693021 mm³ a 65°) e
`C1_RodBolt1` (134,523610 mm³). A correção reaplica ao material novo o espaço
cilíndrico já reservado às bielas/parafusos, com raio 73,170768 mm nas baias.
Também foi necessário alívio axial no fim do colo dianteiro: sem ele,
duas faces tocavam em X=-43 mm, embora o volume de interseção fosse zero.

Resultado do candidato corrigido:

- 220 poses, 125 pares explícitos e 66 separações contínuas superiores;
- 951 interseções B-rep, nenhuma colisão inesperada;
- envelope de rotação do auxiliar afastado 0,999999942 mm do bloco;
- duas buchas em contato com seus apoios, sem interpenetração;
- 40 raios de inspeção lateral atravessam material; mínimo 7,454942 mm;
- STEP reaberto válido, um sólido, erro de volume 0,271 ppm;
- OBJ fechado, 31.842 triângulos, erro de volume 0,07093%.

Esses raios não certificam toda a espessura da parede. A análise não inclui
engrenamento de bomba de óleo. O perfil foi examinado no modelo completo e
no corte, inclusive por `get_view`. `VISUAL_REVIEW_ENCLOSURE.md` registra a
cobertura resolvida e raízes ainda excessivamente tubulares.

## Retomada

O job GUI antigo `job-b02641fc80064017ace4a7ef46d08885` terminou: `failed`,
`AssertionError: 0.0`, após 220 poses. Corresponde à folga zero da primeira
tentativa, já diagnosticada. O RPC confirmou execução livre antes da integração.

O headless corrigido terminou normalmente em 85,56 s. Seus arquivos e hashes
são independentes do job antigo. Um ensaio adicional mostrou que salvar
FCStd apenas pelo kernel headless perde `GuiDocument.xml`; por isso a
integração definitiva deve passar pela GUI, preservando as cores/propriedades.

`build_enclosure_checkpoint.from_trial(enclosure_v003)` foi executado e
reconstruiu/salvou/reabriu o novo modelo. Dimensões, oito válvulas, cinco apoios,
13 protótipos, 145 poses e controlador 720° passaram. Os cortes longitudinal e
transversal e as 13 capturas do ciclo foram examinados; ver
`VISUAL_REVIEW_CASTING_CYCLE.md`. STEP: 192 sólidos, erro de volume 0,089 ppm.
OBJ: 192 peças, 79 malhas, materiais por primitive e quatro poses no renderer
aprovados, com erro máximo de caixa 0,039876 mm. O relatório principal foi
consolidado para Casting v001: dez provas diretas e dez estágios, mantendo
`goal_complete=false` pelas revisões visuais e componentes ainda pendentes.

O campo `auxiliary_casting_enclosure_estimated` pertence ao Casting v001.
Os relatórios históricos do Head permanecem separados e não validam esse campo.
