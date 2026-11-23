# Cabeçote inferior — revisão provisória v001

Checkpoint `build/sevel-cad/models/SEVEL_Head_A3_v001.FCStd`, 192 sólidos.
SHA-256: `072975ec2bfb3f598973054c52e4f893e1c65d478ad821ac5ed1165dbeddf9c9`.
O alvo continua sendo o Tipo 1.6 i.e. **82 cv**. Nenhum datum foi movido.

## Referências e comparação

O catálogo local `Tipo 1.6 - Tipo 1.6 4P 1.6 SPI 8V Gasolina 1993-1995.pdf`
tem 426 páginas e código 160.362.1. As páginas PDF 12–15 distinguem o corpo
inferior, a gaiola e suas juntas. A prancha 14 foi novamente examinada.
São referências de identidade e montagem, sem escala dimensional certificada.

| Referência | Observação e aplicação | Captura em `build/sevel-cad/evidence/` | Pendência |
|---|---|---|---|
| Foto 957036, cavidade superior sem gaiola | Cavidade contínua e borda com reentrâncias; junta acompanha a interface inclinada | `SEVEL_Head_A3_v001-head-Top.png` | P1: piso ainda uniforme; faltam relevos em torno das guias e fixações |
| Foto 621331 e `referencia_coletores_selos.png` | Oito bocas no mesmo lado, sequência E–I–I–E–E–I–I–E e duas bocas de água entre pares de admissão | `SEVEL_Head_A3_v001-head-Back.png` | P1: formas dos dutos e espaçamentos transversais não medidos |
| Foto 901284, extremidade | Flange com duas fixações e abertura arredondada de três arcos | `SEVEL_Head_A3_v001-head-Right.png` | P1: profundidade e orientação na extremidade são provisórias |
| Foto 882668 e catálogo PDF 12 | Quatro câmaras com duas sedes; junta independente do diâmetro dos cilindros | `SEVEL_Head_A3_v001-head-Bottom.png` | P1: contorno das câmaras e passagens da junta ainda simplificados |
| Fotos laterais e catálogo PDF 14 | Colunas arredondadas e faces inclinadas ligam o deck à gaiola | `SEVEL_Head_A3_v001-head-Isometric.png` | P1: nervuras e transições de fundição ainda pouco detalhadas |
| Montagem em suporte e manual | Corpo inferior agora ocupa o espaço entre bloco e gaiola | `SEVEL_Head_A3_v001-external-Isometric.png` | Tampa e curvas inferiores do bloco continuam pendentes |

As oito capturas foram examinadas em disco, além das vistas Isometric do
cabeçote e da montagem pelo `get_view` real. A imagem do RecordingRenderer
na fase 90° também foi examinada; sua projeção não resolve ocultação por
profundidade, portanto não substitui as capturas CAD para revisar a fundição.
O corte `SEVEL_Head_A3_v001_ExhaustSection-Right.png` passa em X=-19,5 mm,
pelo eixo provisório da válvula de escape de C1; largura de 2 mm, fase zero.
Mostra a junta inclinada, o alojamento da guia, a sede e o duto até +Y.

## Verificações e limites

- Três adições: `HeadLower`, `HeadGasket`, `CarrierGasket`. Os 189 sólidos
  anteriores têm diferença simétrica B-rep zero após salvar e reabrir.
- Os 570 pares novos passaram por limites contínuos ou interseções B-rep.
  Isso não converte as amostras dos pares herdados em uma prova contínua.
- Sedes, guias, apoios externos de mola e quatro interfaces de junta têm
  distância zero sem sobreposição volumétrica acima de 1e-5 mm³.
- Os apoios internos das molas preservam a lacuna anterior: 5 mm até o
  cabeçote e 3 mm até o apoio externo. A montagem de apoio está incompleta.
- Recessos de água do deck inicialmente com 12 mm alcançavam quatro dutos
  de escape. A profundidade provisória foi reduzida para 4 mm; os 88 pares
  entre oito dutos e onze recessos de água agora têm volume comum zero.
  Não existe galeria de arrefecimento conectando essas aberturas.
- Cada ferramenta de câmara mede 19,224686 cm³, excluindo recessos da sede
  e da vela. O manual, PDF 13 / página impressa 11, informa 33,7 cm³.
  O CAD ainda não reproduz esse volume; não inferir taxa de compressão dele.
- A junta usa abertura estimada Ø88,4 mm, distinta do cilindro documentado
  Ø86,4 mm. Espessuras, ângulos e contornos permanecem hipóteses explícitas.
- STEP reaberto com 192 sólidos e diferença relativa de volume de 0,103 ppm.
  Malhas: 192 instâncias, 79 OBJ; carregamento em quatro poses aprovado,
  erro máximo de caixa de 0,039876 mm. Os 21 testes Python passaram.
- Reconstrução independente das três adições a partir dos parâmetros:
  diferença B-rep zero. Controlador do novo documento exercitado de 0° a
  720°, 16 molas deformáveis, periodicidade de posicionamento sem desvio
  e retorno a 0°. O tensor mantém seu período angular próprio.

Relatórios: `SEVEL_Head_A3_v001_head_validation.json`, `_head_captures.json`,
`_head_rebuild.json`, `_controller.json`
e exportações em `exports/SEVEL_Head_A3_v001/`. Na entrega inicial desta
revisão, `kinematics_validation.json` estava vinculada ao Carrier v001;
o relatório incremental referencia seu hash e identifica as adições.
A consolidação atual aponta para Head v002 e preserva a anterior em
`kinematics_validation.carrier.da8db84a9817.json`.
O objetivo integral permanece em andamento.
