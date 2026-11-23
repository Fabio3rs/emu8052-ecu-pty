# Transição da envolvente para a parede — candidatos isolados

Referências examinadas: fotografias `702072-MLB118796798285` e
`812345-MLB112262346988` em `PhotosMotor/`. A primeira mostra uma parede
larga ao redor do respiro; a segunda permite conferir a raiz dianteira.
São perspectivas não calibradas, sem raios de concordância cotados.

## Candidato enclosure_v004

Documento comparativo: `models/SEVEL_Root_Review_enclosure_v004.FCStd`.
Capturas `evidence/SEVEL_Root_Review_enclosure_v004-*` confrontam o bloco
Casting v001 com o candidato em Front e Isometric. Três PNGs foram abertos
e a vista Isometric posterior foi examinada diretamente por `get_view`.

As curvas cúbicas ampliaram a transição vertical e reduziram a aparência de
tubo separado. A revisão revelou dois defeitos: término traseiro em uma
face abrupta e material novo cobrindo parcialmente a face anular do respiro.
O candidato não foi promovido. Sua prova numérica passou: 220 poses,
4.061 testes B-rep, nenhuma colisão e folga auxiliar de 0,999999942 mm.

Correção em avaliação no candidato seguinte: redução progressiva da seção
até desaparecer na parede existente e alívio do material acrescentado à
frente da face anular. Eixos, diâmetros dos apoios e ângulo provisório do
respiro permanecem inalterados. O perfil continua sendo uma estimativa;
a avaliação numérica não substitui a revisão das novas capturas.

## Candidato enclosure_v005

As vistas Front e Isometric do novo documento comparativo foram examinadas
diretamente por `get_view`. O término passou a afunilar até entrar na parede,
e a face anular do respiro voltou a ficar inteiramente visível. A silhueta
vertical está mais ampla que a do Casting v001, compatível qualitativamente
com a transição larga da foto 702072. Ainda há nervuras retilíneas e uma
linha de junção entre as duas superfícies; não se alega uma réplica da fundição.

O candidato passou 220 poses e 3.730 testes B-rep, sem colisões inesperadas.
A folga contínua do auxiliar permanece em 0,999999942 mm, com contato das
duas buchas; mínimo nos 40 raios laterais: 7,035709 mm. Acrescenta
371.941,541723 mm³ ao baseline Head v002, sem remover material deste.
O novo material fica afastado 13,228571 mm do limite Y dos cilindros e
31,257652 mm do plano inferior de vedação. Os raios amostrados não provam
toda a espessura da parede. Aprovado para integração como incremento visual.

Integrado em `models/SEVEL_Casting_A4_v002.FCStd`, salvo e reaberto com 192
sólidos válidos e 191 peças inalteradas. A revisão da montagem, ciclo e
cortes está em `VISUAL_REVIEW_CASTING_V002.md`. O candidato v004 permanece
preservado como tentativa rejeitada visualmente; v005 é a fonte promovida.
