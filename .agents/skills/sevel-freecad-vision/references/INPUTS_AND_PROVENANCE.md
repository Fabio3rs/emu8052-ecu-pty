# Inputs, medidas e rastreabilidade

## Estrutura local esperada

- Diretório do projeto: `/mnt/projects/Projects/emu8051-tty` no computador do usuário, salvo se a execução tiver outro CWD.
- Referências: `PhotosMotor/` contendo `*.webp`, `*.png`, `*.svg` e possivelmente JPGs.
- Manual técnico: `OCR_03-1.Tipo 1.6 SPI.pdf` (páginas impressas 5, 7–16, 18 para dados do motor).
- Catálogo: `Tipo 1.6 - Tipo 1.6 4P 1.6 SPI 8V Gasolina 1993-1995.pdf`, capítulos 10101, 10102, 10103, 10105, 10106, 10107, 10115, 10254, 10301 etc.
- Fotos pelo nome do arquivo somente não podem ser inspecionadas daqui; o agente local deve abri-las e agrupar por face/peça/ângulo.

## Inventário por prefixo de nome (não significa foto validada)

| Grupo | Filtros de nomes |
| --- | --- |
| Bloco externo | `*bloco-motor-fiat-16-8v-sevel*` |
| Cabeçote | `*cabecote*` |
| Bielas | `*biela*` e `*bielas-c-pitoes*` |
| Pistões | `*pistao*`, `*pitoes*` |
| Cárter | `*carter-de-oleo*` |
| Juntas | `*juntas-do-cabecote*`, `*jogo-de-juntas*` |
| Válvulas | `*valvula*` |

Imagens de marketplace podem ser de variantes 82/92cv, motor argentino ou componentes retificados. Registrar o texto do anúncio e só usar como identidade dimensional se a peça estiver comprovada como correspondente ao Tipo SPI original. Nunca assumir mesma escala e inclinação entre fotos distintas sem um objeto de referência.

## Medidas presentes na referência do usuário

| Dado | Valor | Fonte | Confiança |
| --- | --- | --- | --- |
| Nº de cilindros | 4 em linha | Manual impresso p. 5 | Confirmado para variante |
| Diâmetro nominal | 86,4 mm | Manual p. 5 e p. 7 | Confirmado nominal |
| Curso | 67,4 mm | Manual p. 5 | Confirmado nominal |
| Cilindrada | 1581 cm³ (arredondado) | Manual p. 5 | Confirmado |
| Compressão | 9,2:1 nominal | Manual p. 5 | Confirmado nominal |
| Mancais principais | 5 (diagrama) | Manual p. 7 | Confirmado por diagrama |
| Diâmetro de munhão | 50,780–50,800 mm por classe | Manual p. 9 | Confirmado por classe |
| Diâmetro de moente | 45,503–45,523 mm por classe | Manual p. 9 | Confirmado por classe |
| Válvula admissão cabeça | 39,300–39,700 mm | Manual p. 11 | Confirmado |
| Válvula escape cabeça | 30,850–31,150 mm | Manual p. 11 | Confirmado |
| Altura de came declarada | 8,8 mm | Manual p. 12 | Confirmado como tabela, interpretar alcance |
| Ignition order | 1-3-4-2 | Manual p. 18 | Confirmado |
| Camshaft | SOHC 8V | Manual e catálogo | Confirmado |
| Entrecentros 93/96/93 | Tabela técnica SEVEL injetado **92 cv**, Clube do Uno Brasil (2013) | Fonte externa para outra variante; NÃO confirmado nos PDFs do Tipo SPI 82 cv | `OTHER_VARIANT_REFERENCE` |
| Comprimento de biela | Desconhecido | Medição externa requerida | Pendente |
| Altura de deck | Desconhecida | Medição externa requerida | Pendente |
| Posição de válvulas/furos | Parcialmente visível | Fotografias e catálogo | Aproximação |

**Atenção à geometria da junta**: o diâmetro de abertura da junta pode ser maior que 86,4 mm. O script usa esse valor como aproximação inicial, explicitamente anotada. Para uma medição rigorosa, obter o diâmetro verdadeiro da abertura, usar scanner/medida de régua e corrigir perspectiva com múltiplos pontos de controle.

## Protocolo de prioridade das referências

Usar `REFERENCE_FRAME_PROTOCOL.md` e o manifesto em `assets/reference_parameters.example.json`. Para o bloco SPI 82 cv, Ø86,4 mm e curso 67,4 mm são cotas nominais diretas do manual. O entrecentros 93–96–93 mm está documentado publicamente para a variante 92 cv, mas deve permanecer **provisório** para a variante alvo. Os quatro centros derivados seriam X=0, 93, 189 e 282 mm. As folgas geométricas nominais entre círculos de Ø86,4 mm são 6,6, 9,6 e 6,6 mm; são diferenças de geometria 2D, **não** espessuras de parede fundida medidas.

Fonte externa identificada: https://www.clubedounobrasil.com.br/forum/viewtopic.php?t=73 (postagem 02/03/2013, variante 92 cv).

## SVG fornecido e diagnóstico reproduzível

- PNG RGBA 858×814 px, com alfa que facilita a segmentação.
- SVG Inkscape com `viewBox="0 0 1144 1085.3333"` e apenas um `<path>` preenchido.
- A análise feita pelo script detectou 7 componentes maiores que 1000 pixels; a junta do cabeçote é a maior.
- 4 aberturas grandes detectadas; 39 outras aberturas na mesma junta.
- Ajustes de elipse das quatro aberturas em pixels: (136,0×140,0), (138,3×142,0), (137,3×139,4), (130,6×136,6).
- Calibração **provisória** por diâmetro nominal de 86,4 mm produz `~0,6252 mm/pixel`; entrecentros estimados na imagem `~90,93 / 95,10 / 88,44 mm` — demonstram que não se deve tratá-la como desenho dimensional de exatidão.
- Para outros componentes da colagem, calibrar separadamente.

## Níveis de confiança a persistir (mesmo vocabulário do validador)

- `MANUAL_TARGET`: dimensão expressa em manual aplicável à variante-alvo.
- `MEASURED_TARGET`: medição física do alvo, com instrumento e incerteza.
- `OTHER_VARIANT_REFERENCE`: valor documentado apenas em outra variante.
- `PHOTO_ESTIMATE`: medida inferida de foto calibrada, com método e erro estimado.
- `ASSUMPTION`: parâmetro provisório de visualização.
- `UNKNOWN`: ainda não medido; usar `value: null` quando não houver aproximação justificável.

Os rótulos `CATALOG` e `SYNTHETIC` podem ser usados **em metadados de referência visual ou visualização**, mas não no campo `evidence` aceito por `build_reference_frame.py`.

## Exemplo do manifesto compatível

Usar `assets/reference_parameters.example.json` como estrutura canônica e validar com `scripts/build_reference_frame.py`. O formato antigo com `"parameters": {"bore_mm": ...}` é apenas uma ilustração conceitual e **não** deve ser passado ao gerador. O manifesto operacional usa `schema="sevel.reference-parameters.v1"`, `dimensions.cylinder_bore_diameter_mm`, `dimensions.stroke_mm` e `dimensions.center_spacings_mm`, cada qual com `value`, `evidence` e `source`.
