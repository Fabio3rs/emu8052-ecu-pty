# Auditoria da entrega — conjunto móvel e distribuição

Este arquivo conserva o histórico dos marcos. A auditoria da entrega atual
está em `FINAL_DELIVERY_AUDIT.md`; a conclusão depende do registro verificável
`build/sevel-cad/reports/final_delivery.json`. O checkpoint Accessories v002
contém 218 sólidos, incluindo os acessórios antes pendentes. Suas correções
de exportação e revisão estão em `VISUAL_REVIEW_ACCESSORIES_V002.md`.

Alvo: `GOAL_SEVEL_CONJUNTO_MOVEL_CINEMATICA.md`, com os contratos pertinentes
de `SEVEL_16_FREECAD_CODEX_SPEC.md` §§4, 6, 8, 9, 11 e 14. O datum da skill
prevalece sobre a origem alternativa da especificação. Objetivo em andamento.

Baseline histórico: `build/sevel-cad/models/SEVEL_Carrier_A3_v001.FCStd`.
SHA-256: `66e07706301ff57acc8d46303715d4a4b62a97e169426a550119193edea1da0f`.
As referências abaixo são relativas a `build/sevel-cad/`, salvo indicação.

Primeiro incremento do cabeçote: `models/SEVEL_Head_A3_v001.FCStd`, SHA-256
`072975ec2bfb3f598973054c52e4f893e1c65d478ad821ac5ed1165dbeddf9c9`.
Adiciona corpo inferior e duas juntas, preservando 189 peças. O relatório
`*_head_validation.json` cobre 570 pares novos, contatos e separação dos
recessos de água dos dutos. `*_head_rebuild.json` reconstrói três peças com
diferença B-rep zero. STEP e 192 instâncias/79 OBJ passaram; oito capturas
e um corte pelo eixo de escape de C1 foram salvos/reabertos e examinados.
O relatório único agora incorpora essa etapa e a correção dos apoios abaixo.
O baseline histórico foi preservado integralmente em
`reports/kinematics_validation.carrier.da8db84a9817.json`.

Checkpoint anterior: `models/SEVEL_Head_A3_v002.FCStd`, SHA-256
`4434e43ac95b42500f9d060fc836b89b73e799f616a503f0cec027bdf2c9ddfb`.
Corrige oito regiões de apoio interno de mola, com 184 sólidos idênticos.
`*_seat_validation.json` comprova 1.500 pares e contato entre as regiões do
prato inferior; `*_valve_dimensions.json`, `_controller.json` e as exportações
verificam dimensões, controlador 720° e as 192 peças no STEP/OBJ.

Checkpoint anterior: `models/SEVEL_Casting_A4_v001.FCStd`, SHA-256
`dde2e7fd7ddc363898757398ff1ee0f397a69195b77d45c7351a5c0b71ffe179`.
Envolve o eixo auxiliar, preserva 191 peças e acrescenta 191 pares cobertos
à cadeia de colisões. `ENCLOSURE_STATUS.md` descreve o incremento, suas
exportações e as diferenças visuais restantes. As verificações de dimensões,
reconstrução, controlador, cortes e 13 capturas foram repetidas neste modelo.

Checkpoint anterior: `models/SEVEL_Casting_A4_v002.FCStd`, SHA-256
`0faa3b93b591dd1528a268bb953fa0fd294acc85be67741bd59bc0621b6bffbd`.
Amplia as transições do auxiliar e afunila o término na parede. 191 peças
preservadas do Head v002; 220 poses/3.730 testes B-rep sem colisões no
incremento, folga de 1 mm. As verificações e exportações abaixo foram
repetidas no v002. Ver `VISUAL_REVIEW_CASTING_V002.md`.

Checkpoint novo: `models/SEVEL_Closures_A5_v001.FCStd`, SHA-256
`7890a81ad99484795718f41b1ca607659acf46be87175c3b6133771f11de0bc8`.
Adiciona tampa, junta da tampa, tampão de óleo, cárter, junta do cárter e
bujão; 198 sólidos válidos, 192 peças herdadas idênticas. O incremento
passou em 220 fases/1.167 pares/4.456 testes B-rep, sem colisões. Dimensões,
reconstrução, controlador, 13 capturas do ciclo e sete capturas externas
foram verificados novamente. STEP reaberto: 198 sólidos, erro de volume
0,06792 ppm. Cortes atuais: 181 objetos longitudinal e 26 transversal C1.
`VISUAL_REVIEW_CLOSURES.md` documenta fontes e simplificações. A tabela
histórica abaixo conserva as provas de Casting v002. Closures v001 também
passou na exportação de 198 instâncias/85 OBJ compartilhados, quatro poses
e calibração no renderer existente; erro máximo de caixa 0,039876 mm.
O relatório único agora aponta para Closures v001, com 12 relatórios diretos
e 11 estágios da cadeia de colisões, incluindo 1.167 novos pares. Quatro
provas malformadas em memória foram rejeitadas: par ausente, amostra repetida,
contagem negativa e hash herdado incorreto. Os 24 testes analíticos passaram.
Reconstrução posterior à publicação também passou: seis diferenças B-rep
zero, predecessor recuperado da prova arquivada com hash conferido.
O pacote portável histórico ainda é de Casting v001; não representa as seis
peças novas. Bomba d'água, velas e coletores permanecem pendentes abaixo.

| Requisito | Evidência atual / resultado | Estado |
|---|---|---|
| Fontes, variante 82 cv e incertezas | `parameters.json`, `reports/moving_sources.json`; catálogo local agora indexado | Conferido; geometria não certificada |
| Datum único, cilindros Ø86,4 e curso 67,4 | `datums/reference_frame.json`; recálculo obrigatório em `config.load()` | Provisório apenas nos entrecentros e demais hipóteses declaradas |
| A1: cinco munhões e quatro moentes | Modelo atual válido; reconstrução do virabrequim com diferença B-rep zero | Comprovado |
| A2: pistões, pinos, anéis, bielas bipartidas e apoios | `*_dimensions.json`, `*_rebuild.json`; 13 protótipos reconstruídos idênticos | Comprovado no modelo |
| A3: oito cames, cinco apoios, oito conjuntos e molas duplas | `*_valve_dimensions.json`, `*_cam_contact.json`, controlador | Comprovado; perfil sintético |
| A3: contato real came/tucho | 1.760 medidas em 220 fases, margem de contato positiva, erro máximo 0,001610 mm | Comprovado no checkpoint atual |
| A3: cabeçote e interfaces | Head v002 mantém fundição/juntas e fecha a lacuna dos apoios internos de mola; revisões HEAD e SEATS | Câmaras abaixo do volume manual e água sem galeria conectada; fundição provisória |
| A4: volante, roda fônica, auxiliar, tensor e correia | Cadeia de sete relatórios auditada em `proof_chain.py`; hashes dos modelos e links conferem | Comprovado para a geometria construída |
| A4: relações e sensor | Comando 1:2; auxiliar 1:1 provisório; tensor com período próprio; entreferro 1 mm | Valores documentados e hipóteses separados |
| B: poses absolutas, curso, conexões e ordem 1–3–4–2 | `kinematics_analytic.json`; reconstrução atual verifica 145 poses e quatro cursos de 67,4 mm | Comprovado |
| B: fases, folgas e limites de válvula | Testes do perfil, contato real, picos líquidos 8,4/8,3 mm; conferência a 0,80 mm | Comprovado para o perfil sintético |
| B: colisões | Varredura inferior do Carrier herdada por identidade das peças: 220 poses, 2.278 pares, 12.351 testes B-rep, zero colisões inesperadas e quatro encaixes prensados limitados | Comprovado no escopo amostrado; demais pares cobertos pela cadeia incremental |
| B: relatório único | `kinematics_validation.json`: Casting v002, dez relatórios diretos, dez estágios; 570 + 1.500 + 191 pares incrementais | `PASS_CURRENT_KINEMATICS_VISUAL_WORK_PENDING`; objetivo integral ainda aberto |
| C: oito poses e cruzamento | `evidence/SEVEL_Casting_A4_v002-pose*.png`, incluindo 359° e 720°; 13 capturas examinadas | Comprovado por capturas atuais |
| C: cortes atuais | `SEVEL_Casting_A4_v002_sections.json`: longitudinal 175 objetos, transversal C1 22, fase 90°, cabeçote incluído | Salvos/reabertos; imagens examinadas; corte adicional no eixo auxiliar |
| C: STEP e identidade das peças | Casting v002: 192 sólidos e erro de volume 0,0711 ppm; IDs únicos | Comprovado |
| C: malhas, pivôs e visualizador existente | Casting v002: 192 peças/79 OBJ, calibração deslocada, quatro poses no RecordingRenderer | Comprovado; não é integração interativa no Lab |
| C: contrato completo dos metadados | IDs, TRS, pivôs, gerador, grupos e materiais por primitive conferidos no v002; pacote portável ainda do v001 | Atualizar pacote após componentes externos; superfícies não classificadas conservam material padrão |
| C: GLB quando disponível | Três calibrações nativas falharam sem criar arquivo; `GLB_CAPABILITY.md` e relatórios v001..003 | STEP/OBJ utilizáveis; falta gravador/conversor GLB funcional para validar esse formato |
| C: mudança de curso/cosmética em cópias | Novo `*_rebuild.json`: curso 70 mm e contrapesos 48°, preset preservado | Comprovado no checkpoint atual |
| C: demonstração contínua | Controlador FreeCAD novamente exercitado com 16 molas, timer e fase 0–720° | Comprovado; novo relatório inclui hashes do modelo e dos parâmetros |
| Revisões visuais solicitadas | Gaiola inclinada, cabeçote inferior e envolvente com transições ampliadas; término abrupto e borda do respiro encoberta foram corrigidos no v002 | Nervuras e cabeçote ainda simplificados; completar tampa/cárter/acessórios |

Os relatórios antigos continuam válidos apenas no escopo indicado por cada
um. A cadeia incremental verifica as identidades dos modelos e as peças
preservadas; não transforma uma amostragem de 220 poses numa prova contínua
de todos os pares. Os quatro encaixes prensados biela/bucha têm limites de
volume próprios e não autorizam outras interpenetrações.

Para encerrar, faltam as revisões de fundição solicitadas pelo usuário e a
conferência final de todos os requisitos. O pacote atual foi verificado;
alterações posteriores de geometria exigirão nova versão da entrega.
As medidas desconhecidas permanecem explícitas; não é necessário atribuir
ângulos exatos a fotografias em perspectiva para produzir a prévia.

A consolidação atual também foi ensaiada com quatro falhas injetadas apenas
em memória: par duplicado/ausente, separação negativa, elo de hash rompido e
curso herdado alterado para 70 mm. Todas foram rejeitadas, sem alterar os
arquivos publicados. A compilação dos módulos Python e `git diff --check`
passaram. A prova analítica atual registra os 24 testes executados.

Empacotamento comprovado: `deliveries/SEVEL_Casting_A4_v001_v002/delivery.json`
enumera 542 arquivos. `reports/SEVEL_Casting_A4_v001_portable_delivery.json`
liga a prova de relocação em `/tmp` (caminho com espaços, 24 testes, compilação
C++, sete entradas no renderer e dez estágios auditados) à reconstrução CAD
independente a partir do diretório do pacote no projeto (13
protótipos idênticos, 145 poses, curso 67,4 mm). Os 192 sólidos foram abertos
e validados a partir do pacote. PDFs/fotos permanecem externos; seu índice
de procedência acompanha a entrega. Não houve nova varredura completa de
colisões nessa prova. Instruções em `PORTABLE_DELIVERY.md`.

## Pendências concretas da especificação

A árvore real de Casting v001 foi consultada novamente via MCP. Seus
objetos fixos incluem bloco, mancais, tampões, cabeçote, gaiola, juntas,
guias, assentos e suportes; não incluem os componentes abaixo. A conferência
de 192 sólidos não comprova a presença de peças ainda ausentes.

| Requisito | Evidência ausente e próximo critério de aceite |
|---|---|
| §8.1, tampa superior | Closures v001: peça separada, flange/bosses, volume oco e espaço para comando/molas verificados; variante preta comparativa |
| §8.7, cárter | Closures v001: reservatório em dois níveis, flange curva, bujão e ausência de colisões nos novos pares; defletores/furação detalhada ainda simplificados |
| §8.7, bomba d'água | Carcaça e polia exteriores; circuito de acessórios separado da distribuição |
| §8.7, velas | Quatro conjuntos simplificados alinhados às câmaras; interfaces verificadas |
| §8.7, coletores | Admissão e escape no mesmo lado, ligados às portas correspondentes; curvas provisórias documentadas |
| §14.6, vista explodida | Closures v001: 11 sólidos com ID de origem e translação reversível, salvos/reabertos e imagem examinada |

As exportações, contagens e verificações incrementais deverão acompanhar
essas adições. TBI detalhada, galerias completas, calibração OEM da roda
fônica e perfis de came medidos continuam no backlog indicado pela própria
especificação; não são requisitos para certificar esta prévia geométrica.
