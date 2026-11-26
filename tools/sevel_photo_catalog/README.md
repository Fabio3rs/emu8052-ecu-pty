# Catálogo de referências SEVEL

Na raiz do repositório, use Python 3.11 ou superior com Pillow e requests.
O SQLite da biblioteca padrão mantém o catálogo em
`build/sevel-photo-catalog/catalog.sqlite3`. Use disco local para WAL.
FTS5 é opcional. A busca usa LIKE quando o SQLite foi compilado sem FTS5.

```sh
python -m tools.sevel_photo_catalog scan
python -m tools.sevel_photo_catalog group
python -m tools.sevel_photo_catalog sheets
python -m tools.sevel_photo_catalog review --port 8765
python -m tools.sevel_photo_catalog infer --limit 10 --dry-run
python -m tools.sevel_photo_catalog infer --limit 10
python -m tools.sevel_photo_catalog infer --limit 10 --workers 2
python -m tools.sevel_photo_catalog export-md
python -m tools.sevel_photo_catalog stats
python -m tools.sevel_photo_catalog validate
python -m tools.sevel_photo_catalog backup
```

A revisão abre em http://127.0.0.1:8765. Busque por peça ou vista, abra um grupo
ou uma imagem e registre uma decisão. As coordenadas da ROI vão de 0 a 1,
da esquerda para a direita e de cima para baixo. O formulário aceita o nome
de objeto do FreeCAD ou PartId. Cada envio acrescenta um registro ao histórico.

O scan associa caminhos ao SHA-256 do conteúdo. As notas dos inventários
anteriores são importadas pelo hash. O agrupamento distingue duplicatas por
bytes, pares candidatos por dHash de 64 bits com distância de Hamming até 4,
títulos comerciais semelhantes e categoria. Confirmar a identidade física
exige revisão visual. As pranchas usam entre dois e quatro originais com
rótulos exteriores. A página de cada imagem dá acesso ao original ampliável.

Para enviar uma prancha específica, use o nome do PNG sem extensão como ID:

```sh
python -m tools.sevel_photo_catalog infer --sheet 107c27e0f7b78d67180ceb6e866c437fcf9a4374ab83d91f08c0ae44b7196494
```

O arquivo `config.toml` configura modelo, URL, limites e timeouts. A primeira
passagem distribui fotos entre processos independentes (dois por padrão).
Cada processo abre sua conexão SQLite em WAL e sua sessão HTTP. O limite
`max_calls` vale para o lote inteiro, incluindo retentativas. Uma chave de
cache em processamento é protegida por um bloqueio de arquivo local.
Use `--workers 1` para processamento sequencial. A primeira passagem usa IDs neutros. A passagem comparativa
envia também uma lista separada com nomes de arquivo e hashes. O cache inclui
imagem, prompt, modelo, endpoint e parâmetros do corpo. Respostas inválidas
podem ser revalidadas localmente. Um timeout fica registrado como incerto.
Cada tentativa HTTP consome uma unidade de `max_calls`.

O padrão usa `deepseek-v4.1-flash:1017-cloud` pelo proxy Ollama local autenticado.
O processamento visual desse modelo ocorre na nuvem. Use `--model qwen3-vl:8b`
para inferência local com o modelo instalado.
O prompt padrão em inglês pede uma descrição em português para quem ainda
não viu a peça, com silhueta, faces, contornos, detalhes e oclusões.
Use `--prompt-language pt` para repetir o protocolo anterior. Para a nuvem,
use por exemplo `--model gemma4:cloud`. Acesso direto com
`--base-url https://ollama.com/v1` requer a variável `OLLAMA_API_KEY`.
O login do proxy é independente dessa chave. Revise os resultados do piloto
contra as notas anteriores antes de ampliar o lote.

O índice gerado fica em `build/sevel-photo-catalog/exports/SEVEL_PHOTO_CATALOG.md`.
Para exportar as vistas revisadas do lado das velas do cabeçote:

```sh
python -m tools.sevel_photo_catalog export-md --component head --view spark-plug --status prior-review
```

O recorte fica em uma subpasta própria e também aceita `--group` e `--utility`.
Os rótulos diferentes entre a revisão anterior e uma sugestão automática ficam
assinalados para conciliação, inclusive quando a diferença pode ser de idioma.
Para registrar uma hipótese de mesmo exemplar físico, use
`group --specimen ID1 ID2 --evidence "detalhes visuais compartilhados"`.
O diagnóstico dos PDFs usa os comandos opcionais `pdfinfo` e `pdfimages` do Poppler.
O banco registra páginas com imagens e indica falhas de inspeção para nova tentativa.

Use o comando backup para obter uma cópia consistente, inclusive durante a
revisão. O SQLite utiliza seu autocheckpoint WAL padrão de 1000 páginas.
