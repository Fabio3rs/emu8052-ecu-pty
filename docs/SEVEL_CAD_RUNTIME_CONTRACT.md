# Contrato espacial e temporal do CAD no Lab

O motor é uma montagem visual do SEVEL 1.6 SPI. O catálogo local identifica
as peças em desenhos explodidos. A revisão da aparência usa fotografias de
`PhotosMotor/`. O datum atual tem status `PASS_PROVISIONAL_FOR_VISUAL_ONLY`.
Os entrecentros 93/96/93 mm são provisórios para a variante 82 cv.

## Origem, unidades e identidade

O CAD coloca a origem no eixo de C1 no deck. +X aponta para C4 e +Z para
o cabeçote. O exportador aplica uma rotação própria de −90° sobre X e muda
mm para m. Uma posição CAD (x,y,z) vira (x,z,−y)/1000. A normal passa pela
mesma rotação, com módulo unitário. O determinante da rotação é +1 e a ordem
dos índices permanece. A orientação de cada instância passa por conjugação
com essa rotação. O leitor usa os vértices, pivôs e poses já convertidos.

Cada `PartId` identifica uma instância ao longo das revisões. O `mesh_id`
identifica o conteúdo local compartilhado e deriva do SHA-256 do OBJ. Nomes
dos batches ligam índices de 16 bits aos materiais de cada instância. Cada
desenho usa um deslocamento de vértices e índices na arena GPU. A troca de
pacote verifica os dados antes de instalar novos buffers. O renderizador
passa a tocar apenas os uniforms enquanto essa geometria permanece instalada.

## Fase

`CrankDynamics::step` integra um ângulo contínuo. `EmulatorLoop` copia esse
ângulo e a referência de PMS de `Combustion` para o snapshot. A fase CAD
em graus é `(crank_angle_rad - tdc_phase_rad) * 180 / pi`. O primeiro PMS
de compressão corresponde a C1, com os seguintes em C3, C4 e C2. Conservar
o ângulo contínuo é necessário para o tensor, que tem período próprio.

O conjunto CAD usa curso 67,4 mm e raio 33,7 mm. O mecanismo 2D existente
tem sua própria parametrização de exibição em `SevelGeometry.hpp`. Para
o 3D, o FCStd determina o comprimento da biela, os pivôs e o perfil de came.
O snapshot determina a fase. As poses são absolutas no referencial do motor.
A transformação de uma biela já contém a posição do moente.

## Auditoria inicial

Linha de base local em `main`, commit `50b8fae`, com alterações locais
preexistentes. FreeCAD 1.1.4, addon MCP 0.1.32, protocolo 3. O build do Lab
usa SDL 3.2.8 e shaders offline SPIR-V, DXIL e MSL. O modo tradicional
`--gpu-preview` e o renderer dos instrumentos têm caminhos próprios.

| Evidência | Resultado |
|---|---|
| v002, `meshes_v001` | 218 instâncias, 97 malhas, 704452 triângulos únicos, 497289 vértices GPU após deduplicação por batch |
| Validador histórico e prova assimétrica | Duas instâncias de cores distintas, rotação composta e pivô deslocado. Desvio máximo das caixas da montagem de 0,040 mm nas poses de ensaio |
| Pacote portátil v002 | 873 arquivos verificados, verificador C++ recompilado e poses e materiais reproduzidos |
| FCStd v005 | 224 sólidos. Roundtrip STEP com erro relativo de volume de 4,75 × 10⁻⁷. O bloco exige tesselação mais fina na junção do bocal da PCV |
| Captura de integração v002 | A primeira imagem revelou falha de oclusão. A ativação explícita do depth target do pipeline CAD restaurou a face externa do bloco e do cabeçote |

As cores são materiais visuais. A fase de montagem do sensor e a relação da
bomba d'água seguem sem confirmação. O PDF do catálogo e as fotos não
fornecem cotas independentes para esses parâmetros.
