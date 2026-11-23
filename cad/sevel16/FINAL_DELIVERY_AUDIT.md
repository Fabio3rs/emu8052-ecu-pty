# Auditoria da entrega visual e cinemática

Esta auditoria aplica-se ao documento identificado em
`build/sevel-cad/reports/final_delivery.json`. Sem esse registro com status
`PASS_VISUAL_KINEMATIC_DELIVERY`, o pacote ainda está em verificação.
O registro liga o modelo, os parâmetros, a consolidação, o pacote e seus
testes por SHA-256. Não certifica uma peça fabricável.

Escopo: `GOAL_SEVEL_CONJUNTO_MOVEL_CINEMATICA.md` e requisitos pertinentes
de `SEVEL_16_FREECAD_CODEX_SPEC.md` §§4, 6, 8, 9, 11 e 14. Alvo: 1.6 i.e.
82 cv. O datum da skill prevalece: origem em C1 no deck, +X até C4,
+Z até o cabeçote e +Y no lado dos coletores/selos.

## Requisitos e evidências

Os nomes `*_...json` abaixo usam o documento indicado no registro final.
Os relatórios ficam em `build/sevel-cad/reports/`; exportações em
`build/sevel-cad/exports/<documento>/`.

| Requisito | Resultado e prova exigida para publicar a entrega |
|---|---|
| A1: virabrequim | Cinco munhões, quatro moentes, excentricidade 33,7 mm; dimensões CAD e cadeia de colisões |
| A2: pistões/bielas | Quatro conjuntos com pinos, anéis, capas, buchas e fixadores; 13 protótipos reconstruídos e 145 poses medidas em `*_rebuild.json` |
| A3: distribuição superior | Comando com oito lóbulos/cinco apoios, oito válvulas/tuchos/calços e 16 molas; `*_valve_dimensions.json`, contatos do came herdados e controlador atual |
| A4: acionamentos | Volante/roda fônica solidários ao virabrequim; comando 1:2, auxiliar com relação própria provisória, tensor com período próprio; bomba de acessórios separada |
| B: ciclo completo | 24 testes Python, curso de 67,4 mm, ordem 1–3–4–2, repetição inferior 360° e superior 720°, eventos de conferência com 0,80 mm |
| B: interfaces e colisões | Cadeia de 12 estágios, identidade das peças herdadas, 220 poses nos incrementos pertinentes; novos acessórios cobrem 4.150 pares e 22 contatos |
| §8: exterior e juntas | Bloco, cabeçote, gaiola inclinada, tampa e cárter separados; flange curva e reservatório em dois níveis; juntas adequadas à vista explodida |
| §8: acessórios | Quatro velas, dois coletores e juntas no lado comum, aquecimento da admissão separado do ar, carcaça e polia da bomba; 218 sólidos na montagem |
| C: capturas | Treze imagens de ciclo/distribuição/exterior, sete de tampa/cárter/explosão e dez de acessórios, com revisão visual identificada |
| C: cortes/explosão | Cortes longitudinal/transversal C1 salvos e reabertos; explosão de 11 componentes com translações reversíveis |
| C: STEP | Montagem reaberta, 218 sólidos válidos e erro relativo de volume abaixo de 1e-6; calibração assimétrica com pivô deslocado |
| C: malhas | OBJ por geometria, IDs/pivôs/TRS/materiais por instância; malhas fechadas, normais e unidades verificadas |
| C: visualizador | RecordingRenderer existente recebe calibração e quatro poses completas, além do par 0°/720° compatível; tensor verificado separadamente |
| C: variações paramétricas | Curso de 70 mm e contrapesos de 48° somente em cópias; preset de entrega preservado |
| Reprodução | Pacote relocado executa testes, recompila C++ e recarrega poses; processo FreeCAD novo abre 218 sólidos e reconstrói os protótipos/acessórios |

O relatório cinemático consolidado contém 13 provas diretas e a cadeia
incremental. Seu `goal_complete=false` registra o estado anterior ao teste
do pacote; a conclusão posterior está exclusivamente em `final_delivery.json`.
Não é preciso modificar os arquivos imutáveis do pacote para registrar isso.

## Fontes, limites e medições futuras

O manual fundamenta Ø86,4 mm, curso 67,4 mm, classes de diâmetros mecânicos,
dimensões de válvulas/tuchos/apoios e eventos de distribuição. As escolhas
nominais e respectivas faixas estão em `parameters.json`. O catálogo local
de 426 páginas identifica peças e montagem; não fornece escala automática
para as perspectivas. Fotos/PDFs originais foram preservados e ficam externos
ao pacote, identificados por caminho e hash no índice de referências.

Permanecem provisórios: entrecentros 93/96/93 mm, comprimento da biela,
altura do deck/compressão, posições e inclinações externas, forma dos dutos,
perfil sintético dos cames, dentes/fase da roda fônica e relação do auxiliar.
O respiro não recebeu um ângulo medido. A geometria das câmaras mantém seu
volume próprio separado do valor documental. A bomba não gira na prévia;
sua relação, rotor e correia de acessórios não foram deduzidos da distribuição.

O escape usa tubos com curvas arredondadas analíticas para preservar a
geometria no STEP. A forma é simplificada. As velas usam comprimento interno
compatível com o canal provisório, sem alegar alcance comercial de rosca.
Quando uma comparação booleana falha, o relatório de reconstrução identifica
explicitamente a comparação numérica amostrada usada; não a chama de identidade
B-rep. Os limites numéricos são critérios de software, não tolerâncias OEM.

A colisão é verificada por amostragem/envelopes indicados em cada prova;
não equivale a demonstração contínua exaustiva de todos os pares. Os quatro
encaixes prensados permitidos têm limites próprios. Nenhuma exceção genérica
autoriza interpenetrações novas.

GLB não foi entregue: as calibrações nativas disponíveis falharam, conforme
`GLB_CAPABILITY.md`. STEP e OBJ com manifest são as alternativas verificadas.
A animação contínua demonstrada é o controlador FreeCAD; o teste do renderer
não representa integração interativa no Lab nem simulação de combustão.

As medições que mais melhorariam a fidelidade são os entrecentros, comprimento
da biela, altura do deck/compressão e posições/inclinações do comando e válvulas.
Contornos ortogonais com escala ajudariam na fundição e nos coletores.
TBI detalhada, galerias completas, mangueiras, roscas e calibrações OEM permanecem
no backlog opcional da especificação. Instruções em `README.md` e
`PORTABLE_DELIVERY.md`; nenhuma publicação remota faz parte desta entrega.
