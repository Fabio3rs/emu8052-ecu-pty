# Motor SEVEL em 3D no MA1.7 Lab

O modo **3D CAD** abre a montagem FreeCAD em perspectiva dentro do painel Mechanics. A ECU, os instrumentos, o áudio e o osciloscópio usam a sessão do Lab. O renderizador recebe a fase do snapshot que a interface está apresentando. O aplicativo lê OBJ e JSON em C++.

## Compilar e abrir

Com SDL 3.4 ou superior, FreeType, zlib e libpng disponíveis, execute na raiz do projeto:

```sh
cmake -S . -B build-lab -DENABLE_SEVEL_MA17_LAB=ON -DENABLE_TESTS=ON
cmake --build build-lab --target sevel-ma17-lab sevel-cad-check -j8
cmake --build build-lab --target sevel-cad-assets
build-lab/sevel-ma17-lab "$ROM"
```

O alvo de assets instala a revisão ativa de `build/sevel-cad/runtime-assets` junto ao executável. Configure `SEVEL_CAD_ASSET_DIR` para usar outro registro. Ao abrir a ROM, o Lab inicia em **Live**, com o preset de bancada e **3D CAD** em Mechanics. Se o pacote estiver ausente, incompleto ou inválido, a simulação abre na vista mecânica clássica. Use `--no-cad` para escolhê-la diretamente ou `--no-bench-preset` para iniciar com o cenário físico bruto. Para abrir o CAD em uma segunda janela sincronizada, use `--cad-assets bundled`. O argumento também aceita o registro, a pasta de uma revisão ou o próprio `parts_manifest.json`. Um manifest histórico sem o rig numérico abre em pose estática.

Para medir a taxa do laboratório completo durante o uso, execute
`SEVEL_LAB_FPS=1 build-lab/sevel-ma17-lab "$ROM"`. Para incluir rastreamento da ECU, use `--verbose`.
A linha `[LAB-VIDEO]` identifica a GPU e `[LAB-FPS]` mostra a taxa de apresentação do último segundo e a média acumulada.
Ao medir com `--window-frames`, acrescente `--frame-delay-ms 0` para retirar a pausa das capturas automatizadas.
`SEVEL_CAD_PROFILE=1` acrescenta uma espera pela GPU a cada quadro para cronometrar o desenho do CAD.

```sh
cmake --install build-lab --prefix "$PWD/build-lab/ma17-distribution"
build-lab/ma17-distribution/bin/sevel-ma17-lab "$ROM"
```

A instalação leva os shaders, fontes, créditos e a revisão CAD ativa. Forneça a ROM separadamente. O pacote CAD usa caminhos relativos. A execução requer um driver SDL_GPU compatível. Se a inicialização gráfica do CAD falhar, o Lab registra o motivo e oferece as vistas mecânicas anteriores.

## Inspeção

Clique na área 3D para dar foco aos atalhos do CAD. **Esc** devolve o foco ao painel. Os botões e os dois controles deslizantes ficam acima da cena.

| Ação | Controle |
|---|---|
| Orbitar, transladar, aproximar | Arrastar com botão esquerdo, botão direito, roda |
| Ajustar montagem, alternar projeção | Home, O |
| Frente, traseira, lateral, topo | F1 a F4. Shift+F3 e Shift+F4 mostram a face oposta |
| Selecionar e consultar peça, enquadrar, isolar | Clique, Enter, J |
| Escolher grupo, ocultar, transparência, explodir | Tab, H, G, E |
| Ligar corte, inverter, mover | C, F, colchetes ou Shift+roda. O controle PLANE mostra milímetros |
| Longitudinal, transversal em C1 a C4, horizontal | Teclas 1 a 6 |
| Inclinar o plano livre | X, Y, Z. Shift inverte o sentido |
| Imobilizar um plano e mover o segundo | B fixa o primeiro semiespaço. B novamente o remove |
| Cortar peças móveis, isentar o grupo, preencher a seção | M, U, K |
| Alternar LIVE e INSPECT | I ou o botão de modo. Arrastar PHASE entra em INSPECT |
| Reproduzir, avançar, velocidade de inspeção | Espaço, setas esquerda/direita, −/=. Shift+seta avança 90° |
| Salvar e restaurar câmera, corte e visibilidade | F6, F7. O arquivo fica na pasta de preferências do Lab |
| Recarregar assets | RELOAD ou F5 na cena |

A superfície laranja é a interseção de um sólido fechado com o plano. Um tubo mantém o furo, inclusive com duas seções ativas. A indicação **CLIP ONLY** aparece quando o preenchimento está desligado ou o dispositivo carece de stencil compatível. Grupos em ghost têm transparência e corte aberto. O clique considera a profundidade, os planos e as superfícies de seção visíveis. A projeção da normal do corte aparece junto ao controle PLANE.

## Captura e reprodução

```sh
build-lab/sevel-ma17-lab "$ROM" --live --cad-panel \
  --cad-preset tests/cad_longitudinal.json --replay-controls tests/data/lab_control_replay.txt \
  --capture-tick 1200000 --stop-ticks 1200000 --window-frames 180 \
  --screenshot build-lab/corte.png
```

O Lab grava o painel, a cena limpa em `corte-gpu.png` e o preset efetivo em `corte-gpu.json`. O log registra tick, fase apresentada em graus, SHA-256 do manifest e do preset, e hash das poses. Em LIVE a fase pode superar 720° durante várias voltas. Em INSPECT o slider escolhe uma pose visual e a ROM continua recebendo os mesmos controles. A correia usa deslocamento periódico com passo e dentes do rig. O levantamento das válvulas segue o perfil CAD provisório. As indicações de injeção e combustão vêm da sessão da ECU.

## Reexportar uma revisão

1. Salve um novo FCStd na fase zero. Compare a forma com as fotos em `PhotosMotor`. Os wireframes do catálogo ajudam a identificar peças e interfaces. Preserve os `PartId`, o datum, os pivôs e os tipos de movimento.
2. Pelo FreeCAD MCP, execute no console Python o trecho abaixo, indicando o checkpoint e o gerador correspondentes. O exportador abre uma cópia de auditoria e cria uma nova pasta em `build/sevel-cad/runtime_exports/<checkpoint>/vNNN`.

```python
import sys
from pathlib import Path
repo = Path("/mnt/projects/Projects/emu8051-tty")
sys.path.insert(0, str(repo / "cad/sevel16"))
from export_lab_assets import export
meshes = export(repo / "build/sevel-cad/models/SEVEL_Accessories_A5_v005_ManifoldReview.FCStd",
                "cad/sevel16/build_manifold_review.py")
print(meshes)
```

3. No terminal, defina `AUDIT` como essa pasta `vNNN` e `MESHES` como a pasta impressa. Execute a verificação das poses exportadas e a publicação. O relatório de auditoria conserva o STEP, a volta de leitura, os hashes e as tolerâncias de malha.

```sh
REGISTRY=build/sevel-cad/runtime-assets
python3 cad/sevel16/check_mesh_package.py "$MESHES"
python3 cad/sevel16/runtime_package.py "$MESHES" "$REGISTRY" \
  --parameters "$AUDIT/parameters.json" --datum "$AUDIT/reference_frame.json" \
  --checker build-lab/sevel-cad-check
```

4. Abra o Lab apontando para `$REGISTRY` ou pressione F5 se ele já estiver aberto com esse caminho. Para a cópia instalada junto ao build, repita o alvo `sevel-cad-assets` e recarregue. A troca compara o rig e o datum, valida os arquivos numa tarefa de fundo e instala os buffers no thread gráfico. A câmera, os cortes e a sessão permanecem ativos.
5. Para voltar a uma revisão publicada, use o SHA-256 completo da pasta desejada.

```sh
python3 tools/sevel_cad_assets.py "$REGISTRY" --revision "$REVISAO_ANTERIOR" \
  --checker build-lab/sevel-cad-check
```

O registro mantém cada versão em uma pasta imutável. A troca de `current.json` é atômica. Uma forma B-rep equivalente reutiliza a malha auditada quando os parâmetros, o datum, os batches e a versão do exportador permitem. Uma alteração no eixo, na escala ou no rig requer migração explícita. Para distribuir os assets, repita a instalação em um novo prefixo.

Consulte também o [contrato de coordenadas e fase](SEVEL_CAD_RUNTIME_CONTRACT.md) e o [relatório de aceite](SEVEL_LAB_3D_ACCEPTANCE.md).
