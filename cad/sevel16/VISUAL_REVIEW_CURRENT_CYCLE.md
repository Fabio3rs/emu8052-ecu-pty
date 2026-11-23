# Revisão do ciclo — Head A3 v002

Modelo: `build/sevel-cad/models/SEVEL_Head_A3_v002.FCStd`, 192 sólidos.
As 13 capturas de `*_cycle_captures.json` e os dois cortes de
`*_sections.json` foram examinados. O corte longitudinal também foi
inspecionado pelo `get_view` do FreeCAD. Datum e modelo salvo permanecem iguais.

| Evidência | Observação | Consequência |
|---|---|---|
| Poses 0°, 90°, 180°, 270° | Pistões extremos em fase, centrais em oposição; bielas inclinam sem girar os pistões | Compatível com as medições CAD de 145 poses |
| Poses 359°, 360°, 450°, 540°, 630°, 720° | Parte inferior repete após 360°; comando e válvulas distinguem os dois giros e retornam em 720° | Perfil sintético; a prova numérica permanece separada |
| Distribuição Left/Isometric; catálogo PDF32 | Comando, virabrequim, auxiliar e tensor aparecem separados; duas buchas do auxiliar visíveis | Correia lisa e engrenagem auxiliar sem peça conjugada continuam simplificações |
| Longitudinal 90° | Cabeçote, câmaras, válvulas e pistões aparecem no mesmo corte; 175 objetos derivados | Complementa o corte anterior, que não incluía o cabeçote |
| Transversal C1 90° | Pino, biela inclinada e moente são legíveis; 22 objetos derivados | Plano X=0 passa entre as válvulas; não usar para avaliar suas hastes |
| Vista externa; foto do bloco 702072 | Parede lateral e nervura inferior ainda são muito facetadas; eixo auxiliar aparece exposto ao longo da lateral | P1: reconciliar a fundição envolvente com as fotos e preservar a passagem do eixo |
| Vista Bottom do bloco; junta 980809 | Dois recuos tangentes e extremidades arredondadas já existem no contorno inferior | Não interpretar a perspectiva da foto como desnível da face de vedação |

Referências em `PhotosMotor/`: junta `D_NQ_NP_2X_980809-…webp`, bloco
`D_NQ_NP_2X_702072-…webp`, catálogo Tipo SPI 1993–1995, páginas PDF14 e 32.
Os nomes completos constam em `parameters.json`/inventário das fontes.

A vista externa ainda não demonstra um motor completo: faltam tampa superior,
cárter e acessórios previstos na especificação. O ensaio de colisões demonstra
folgas no modelo construído; não prova que a fundição envolve corretamente
todos os mecanismos. A revisão dessas superfícies continua pendente.

Os novos cortes e capturas são evidência visual de geometria provisória.
Ângulos, entrecentros de outra variante e dimensões estimadas conservam suas
classes de evidência; nenhuma cota foi promovida por esta inspeção.
