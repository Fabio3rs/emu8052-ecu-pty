# SEVEL 1.6 · Furação junto às velas

A v009 corrige os quatro furos pequenos na prateleira inferior da face das velas. A referência é a face de assentamento do cabeçote sobre o bloco. Sua normal coincide com o eixo Z do CAD. A câmera muda a projeção das bocas circulares e a forma aparente das elipses. [Fotos e CAD na mesma vista](../../build/sevel-cad/reviews/head-v009/comparacao-furos.jpg)

| Eixo medido na geometria | Ângulo com a normal na v008 | Ângulo com a normal na v009 | Ângulo com o plano na v009 |
|---|---:|---:|---:|
| Quatro furos pequenos junto às velas | 60,61° | 0° | 90° |
| Dez passagens principais de fixação do cabeçote | 0° | 0° | 90° |
| Quatro alojamentos das velas | 71,22° | 71,22° | 18,78° |

Na v009, cada pequeno ressalto termina em uma face paralela à junta, com furo na direção indicada pelo proprietário. Os quatro furos pequenos continuam cegos no modelo. Sua profundidade, eventual continuidade até o bloco e função de fixação específica ainda precisam de confirmação na peça. Os ângulos das velas são os do modelo. [Eixos do arquivo reaberto](../../build/sevel-cad/reviews/head-v009/bore-axes.json) · [Verificação de assentos e interferências](../../build/sevel-cad/reviews/head-v009/validation.json) · [FreeCAD v009](../../build/sevel-cad/models/SEVEL_Accessories_A5_v009_HeadBores.FCStd)

## Exportação e ensaio no simulador

O STEP completo retornou ao OpenCascade com 231 sólidos válidos e diferença relativa de volume de 7,36 × 10⁻⁸. A integração adaptativa por intervalos das B-splines resolveu a diferença numérica na comparação de volumes. A malha da junta da termostática ficou a 0,0352% do volume calculado por esse método. Os limites originais de aceitação do STEP e dos OBJ foram aplicados. Para recompilar o verificador no Linux, execute `sh cad/sevel16/build_volume_checker.sh`. [STEP](../../build/sevel-cad/runtime_exports/SEVEL_Accessories_A5_v009_HeadBores/v001/geometry/assembly.step) · [Verificação do STEP](../../build/sevel-cad/runtime_exports/SEVEL_Accessories_A5_v009_HeadBores/v001/geometry/export_checks.json)

O Native Lab MCP executou o binário gráfico com a ROM local, replay de controles e SDL offscreen. O carregador leu 231 peças, 112 malhas e 1.101.244 triângulos da revisão `47fffabef5a92ca8b5ce1801fc2c4a702b54aa41db94749ebb6305354135ae61`. A captura do cabeçote usou Vulkan com o ICD Lavapipe. No tick 1.200.000 as duas vistas da v009 e o controle v007 chegaram a 871,17 rpm, com os mesmos hashes de estado e eventos da ECU. Os três logs registraram cinco diagnósticos IRET do emulador. [Cena completa](../../build/sevel-cad/reviews/head-v009/lab-v009-gpu.png) · [Cabeçote isolado](../../build/sevel-cad/reviews/head-v009/lab-v009-cabecote-gpu.png) · [Log da cena](../../build/sevel-cad/reviews/head-v009/lab-v009.log) · [Log Vulkan](../../build/sevel-cad/reviews/head-v009/lab-v009-cabecote.log)

Para abrir a v009 em janela a partir da raiz do repositório, use o pacote da revisão explicitamente.

```sh
./build-lab/sevel-ma17-lab FiatTipo_MA17_dump_27c256.bin --live \
  --cad-assets build/sevel-cad/reviews/head-v009/lab-assets \
  --cad-preset build/sevel-cad/reviews/head-v008/lab-exterior.json
```
