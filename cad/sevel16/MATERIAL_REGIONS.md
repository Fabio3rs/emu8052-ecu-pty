# Materiais por região nas malhas

`material_regions.py` identifica interfaces do CAD por coordenadas e parâmetros,
sem depender de números de faces. O particionamento conserva os vértices,
triângulos, normais, pivô e movimento da peça. O OBJ recebe objetos/batches
nomeados pela região; o manifest associa cada batch a um material visual.

Interfaces classificadas como `machined_surface`:

- bloco: deck, plano inferior da flange e paredes dos quatro cilindros;
- cabeçote inferior: face da junta do bloco, face dos coletores e plano
  inclinado de contato com a junta da gaiola;
- gaiola: planos inclinados inferior e superior.

O restante dessas três peças conserva `cast_surface`. Isso não afirma que
todos os demais furos, sedes e superfícies sejam brutos de fundição: a
classificação cobre apenas as interfaces identificadas acima. As demais peças
usam `body_surface` com o material visual já existente. Cores não comprovam
liga metálica, tratamento ou acabamento industrial.

O teste de pertencimento usa 0,00001 mm como tolerância numérica de coordenadas,
não como tolerância de fabricação. A parede de cilindro exige vértices no raio
nominal e extensão vertical; triângulos de uma tampa circular não são tratados
como parede apenas porque seus vértices estão na circunferência.

No manifest de malha, `material_bindings[id][batch]` e o campo homônimo de cada
peça contêm a mesma associação por primitive. `default_material_bindings`
preserva o material padrão por peça. `prepare_mesh_probe.py` usa os bindings
em cada draw call; as malhas deformadas das molas mantêm seu material padrão.
`check_mesh_package.py` confere completude, IDs de material e cores nas quatro
poses, além da carga real no renderizador C++ e seus limites geométricos.

`render_material_regions.py <pasta_meshes>` produz seis vistas estáticas das
três fundições. É uma inspeção dos OBJ, com iluminação e remoção de faces
voltadas para trás; não substitui `get_view` nem valida a semelhança da fundição
com a peça original. As primeiras pranchas revelaram artefatos do desenho
por triângulos; a remoção de faces traseiras e a desativação do antialiasing
por polígono eliminaram as linhas internas espúrias na prévia examinada.

As exportações anteriores permanecem intactas. A alteração de materiais não
transforma um checkpoint anterior em prova de uma geometria posterior.
