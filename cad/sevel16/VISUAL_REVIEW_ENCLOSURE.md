# Envolvente do auxiliar — Casting A4 v001

Modelo: `build/sevel-cad/models/SEVEL_Casting_A4_v001.FCStd`.
SHA-256: `dde2e7fd7ddc363898757398ff1ee0f397a69195b77d45c7351a5c0b71ffe179`.
Seis PNGs examinados em `build/sevel-cad/evidence/`, prefixo
`SEVEL_Casting_A4_v001-enclosure-`, mais o corte `AuxiliarySection-Front`.
As vistas Isometric da montagem e Front do corte também foram examinadas
diretamente por `get_view` no FreeCAD.

Referências reabertas: fotos `702072-MLB118796798285` (lateral do respiro/filtro)
e `812345-MLB112262346988` (extremidade da distribuição), em `PhotosMotor/`.
São perspectivas não calibradas; as vistas CAD são ortográficas. Comparação
qualitativa de posição e contorno, sem medir raios ou ângulos nessas fotos.

| Referência e região | Observação no checkpoint | Resultado / prioridade |
|---|---|---|
| 702072, corpo do bloco ao redor do auxiliar | O eixo antes exposto foi coberto por uma envolvente contínua; as aberturas do filtro e do respiro permanecem visíveis | Lacuna de cobertura resolvida no domínio do modelo |
| 812345, alojamento dianteiro | A envolvente encontra a região dianteira sem deslocar eixo, bucha ou distribuição | Interface preservada; forma externa ainda aproximada |
| Corte de 2 mm em Y=-82 | Folga visível ao longo do eixo e apoios das duas buchas; cavidades do filtro/respiro permanecem abertas | Compatível com distância B-rep de aproximadamente 1 mm, sem medir folga por pixels |
| 702072, transições da fundição | A peça real distribui a saliência em uma parede mais larga e arredondada; o CAD ainda lembra um volume tubular unido à parede | P1: suavizar raízes e transições da parede/nervuras |
| 702072, nervuras e bosses | Persistem nervuras retas, regiões planas e detalhes de flange simplificados | P1/P2: reconciliar formas sem alterar interfaces e datum |
| Montagem externa | Cabeçote, gaiola e distribuição continuam legíveis; tampa e cárter completo ainda faltam | Trabalho visual pendente no objetivo integral |

O corte possui múltiplos sólidos onde o plano atravessa lados separados de
uma peça; isso não altera o requisito de um sólido por componente no FCStd
da montagem. O arquivo do corte foi salvo e reaberto com quatro objetos.

A integração reconstruiu o bloco e comprovou 191 peças inalteradas. A prova
incremental cobre 220 poses, 125 pares explícitos e 66 separações contínuas;
os 40 raios de inspeção lateral não certificam toda a espessura da fundição.
O perfil e o ângulo do respiro permanecem provisórios, conforme combinado.

O cálculo antigo da primeira tentativa terminou com folga zero, como previsto
pelo diagnóstico. Seu resultado não foi promovido. O checkpoint usa o
candidato corrigido `trials/enclosure_v003`, cuja folga B-rep é 0,999999942 mm.

Resultado: incremento mecânico e cobertura visual revisados, com diferenças
de fundição documentadas. Não é aprovação dimensional nem conclusão do motor.
