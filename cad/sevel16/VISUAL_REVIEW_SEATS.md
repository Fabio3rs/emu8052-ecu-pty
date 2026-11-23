# Apoios das molas — Head A3 v002

Modelo: `build/sevel-cad/models/SEVEL_Head_A3_v002.FCStd`.
SHA-256: `4434e43ac95b42500f9d060fc836b89b73e799f616a503f0cec027bdf2c9ddfb`.
192 sólidos válidos, salvos e reabertos; 184 peças preservadas integralmente.

A prancha 10107, PDF 36, mostra um prato inferior com ressalto central.
A tabela da página 38 identifica o item 12 como 4371517, quantidade oito.
No CAD anterior, o apoio externo terminava em Z=61 mm e o apoio interno
começava em Z=64 mm: havia uma lacuna de 3 mm. O ressalto agora começa
em Z=61 mm e continua até a altura anterior de apoio da mola, Z=66 mm.

Os nomes e IDs `OuterSpringSeat` e `InnerSpringSeat` foram preservados como
duas regiões CAD do mesmo prato inferior. A divisão não afirma que existam
duas peças OEM. Sua união resulta em um único sólido conectado. As dimensões
permanecem estimadas; catálogo e desenho não fornecem a altura do ressalto.

| Verificação | Evidência |
|---|---|
| Corpo do cabeçote → base do prato → ressalto central | Contatos com distância zero, sem interpenetração volumétrica |
| Folga do ressalto para a mola externa | 0,4 mm radiais; envelope anular válido durante todo o movimento |
| Oito regiões modificadas contra 184 peças e entre si | 1.500 pares aprovados por limites contínuos ou B-rep |
| Reconstrução | `valve_parts.build` reproduz as oito regiões; nenhum outro sólido alterado |
| Alturas das molas e movimento | Alturas preservadas, oito conjuntos e cinco mancais medidos; 21 testes Python aprovados |
| Controlador | 16 molas deformáveis, 0–720°, repetição sem desvio e retorno a zero |
| STEP | 192 sólidos reabertos; erro relativo de volume de 0,103 ppm |
| OBJ e visualizador | 192 instâncias, 79 geometrias; quatro poses aprovadas; erro máximo de caixa 0,039876 mm |

Capturas em `build/sevel-cad/evidence/`:
`SEVEL_Head_A3_v002_SeatSection-Right.png` e
`SEVEL_Head_A3_v002-exhaust-stack-Isometric.png`. Ambas foram examinadas;
o corte também foi inspecionado via `get_view`. Ele mostra a continuidade
do apoio antes interrompida, mantendo espaço livre em torno das molas.

A antiga lacuna é resolvida nesta versão. Permanecem os pequenos afastamentos
das pontas de mola não retificadas, documentados em `_valve_dimensions.json`.
As limitações das câmaras, galerias de água e contornos do cabeçote descritas
em `VISUAL_REVIEW_HEAD.md` continuam válidas. O GLB nativo falhou na calibração;
ver `GLB_CAPABILITY.md`. A entrega do objetivo integral ainda está em andamento.
