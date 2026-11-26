# Avaliação do piloto visual

A avaliação usou dez originais com revisão anterior, selecionados pelo comando
`infer --limit 10`, e uma prancha independente de quatro fotos de cabeçote.
O prompt individual usou identificadores neutros. O DeepSeek recebeu
instruções em inglês e produziu descrições em português. As dez respostas
individuais passaram pela validação local de JSON, IDs e regiões.

| SHA-256 abreviado | Referência anterior | Comparação com a sugestão do DeepSeek |
|---|---|---|
| 4d312cda7254 | Biela | Reconheceu a biela e descreveu o fixador. |
| 1fcd6517027d | Bloco | Reconheceu a categoria; aplicação permaneceu hipotética. |
| 35e1a4f885e3 | Bloco montado | Reconheceu o bloco; o estado de montagem requer a referência anterior. |
| 28e99c22a9a1 | Cabeçote | Reconheceu o cabeçote e descreveu a face com cavidades. |
| 9732650b713c | Bloco de variante 16V | Reconheceu o bloco, mas sugeriu aplicação 8V. Manter a referência comparativa 16V. |
| 42c84c413317 | Cabeçote montado | Sugeriu cabeçote com alojamento superior. |
| 1995cf42bfbb | Cárter | Reconheceu a categoria e qualificou a compatibilidade como incerta. |
| 4cdef42747e6 | Gaiola do comando | A sugestão de cabeçote perde a distinção do componente. |
| 345a574d453b | Conjunto | Identificou peças individuais; conferir a composição no original. |
| 1ba69a2bb60a | Virabrequim | Reconheceu a categoria; a marcação visível não confirma a aplicação. |

A prancha `107c27e0f7b78d67180ceb6e866c437fcf9a4374ab83d91f08c0ae44b7196494`
expôs um erro diferente. Qwen e Gemma atribuíram à quarta foto detalhes da
face das câmaras visível na primeira. O DeepSeek descreveu a tampa à direita
do quadro na quarta vista. Ao revisar um detalhe, abra cada original indicado
em `seen_in` e confira sua presença naquele quadro. A escolha do modelo e o
resultado deste piloto não constituem confirmação de geometria ou variante.
