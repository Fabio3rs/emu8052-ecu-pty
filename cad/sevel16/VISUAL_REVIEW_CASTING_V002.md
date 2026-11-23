# Revisão de Casting A4 v002

Modelo salvo/reaberto: `models/SEVEL_Casting_A4_v002.FCStd`, 192 sólidos.
SHA-256: `0faa3b93b591dd1528a268bb953fa0fd294acc85be67741bd59bc0621b6bffbd`.
As referências abaixo são relativas a `build/sevel-cad/`.

Foram examinados individualmente os 13 PNGs de ciclo/distribuição/exterior,
os dois cortes da montagem e os seis PNGs de comparação da envolvente.
A montagem em Isometric também foi examinada diretamente por `get_view`.
As fotos 702072 e 812345 foram reabertas nesta revisão; a evolução dos
candidatos e as diferenças de perspectiva estão em `VISUAL_REVIEW_ROOT_BLEND.md`.

| Região / evidência | Observação |
|---|---|
| 0°, 180°, 360°, 540°, 720° | Alternância dos pares de pistões; 0° e 720° coincidem visualmente, enquanto 0° e 360° conservam pistões e mudam o comando |
| 90°, 270°, 450°, 630° | Bielas inclinadas e pinos conectados; as válvulas variam conforme o cilindro e fase |
| 359° | Quadro de cruzamento presente; contato e folgas são sustentados pelos relatórios numéricos, não pela imagem isolada |
| Distribuição Left/Isometric | Caminho contínuo passando por comando, virabrequim, auxiliar e tensor; correia lisa e dentes provisórios |
| Comparação Front/Isometric | Transição lateral mais ampla e término afunilado; face do respiro exposta, filtro aberto |
| Corte do auxiliar, Y=-82, espessura 2 mm | Eixo envolvido, apoios das duas buchas e separação do eixo legíveis; corte atravessa as aberturas do respiro/filtro |
| Longitudinal, 175 objetos, 90° | Cabeçote, comando, válvulas, pistões e apoios presentes |
| Transversal C1, 22 objetos, 90° | Perfil lateral ampliado e espaço para a biela visíveis; a seção não passa pelos eixos deslocados das válvulas, explicando os fragmentos superiores |

A forma aproxima melhor a parede larga da foto, mas conserva nervuras
retilíneas e uma linha de junção das superfícies. Tampa, cárter e acessórios
listados na auditoria continuam ausentes. A geometria das câmaras e das
galerias mantém as limitações do Head v002. O ângulo do respiro segue provisório.

As 191 peças herdadas são idênticas ao Head v002. O incremento do bloco
passou 220 poses e 3.730 testes B-rep, sem colisões inesperadas, com folga
contínua do auxiliar de 0,999999942 mm. As duas buchas mantêm contato com
os apoios. O controlador foi exercitado novamente com as 16 molas e timer,
retornando a 0°. Os cortes foram salvos e reabertos.

As seis vistas em `exports/SEVEL_Casting_A4_v002/meshes_v001/material_regions.png`
também foram examinadas. São plots dos OBJ locais, não capturas do FreeCAD;
mostram as interfaces conhecidas claras e as demais regiões em cinza.
O carregador/renderizador existente aprovou sete entradas e os bindings
de materiais das 192 peças. Não se trata de integração interativa no Lab.

Resultado: `REVIEWED_WITH_DOCUMENTED_DIFFERENCES`. Aprovado como checkpoint
intermediário; não representa conclusão do objetivo nem certificação dimensional.
