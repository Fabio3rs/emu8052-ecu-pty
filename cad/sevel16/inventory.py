"""Read-only source audit; names alone never establish photo orientation."""
import hashlib
import json
from config import ROOT, OUTPUT
from catalog_source import record as catalog_record

REVIEWED = {
    '2X_640123-':('respiro_oleo','oblique, outlet end',
              'Bocal de respiro avulso com boca tubular aberta e ressalto perfurado ao lado.'),
    '2X_925239-':('respiro_oleo','underside',
              'A vista inferior mostra uma espiga tubular aberta sob o corpo mais largo.'),
    '2X_949850-':('respiro_oleo','side profile',
              'O tubo superior inclina-se em relação à espiga inferior; o ressalto vizinho tem topo aberto.'),
    '2X_764099-':('carcaca_termostatica','mounting face',
              'Face de apoio, elemento termostático visível e junta avulsa ao lado.'),
    '2X_808610-':('carcaca_termostatica','exterior, flange and branches',
              'Vista externa do bocal principal, derivação oblíqua e espigão menor; junta ao lado.'),
    '2X_856527-':('carcaca_termostatica','opposite exterior',
              'Perfil dos bocais e ressaltos da flange vistos pelo lado oposto.'),
    '2X_921528-':('junta_termostatica','gasket alone',
              'Junta avulsa da carcaça com janela central assimétrica e dois furos de fixação.'),
    '2X_993519-':('carcaca_termostatica','looking into the large outlet',
              'Vista pela boca circular do duto maior, com parte do mecanismo ao fundo.'),
    '2X_700243-':('juntas','isolated long gasket',
              'Uma junta alongada com uma sequência de aberturas de tamanhos diferentes; anúncio cita Elba.'),
    '2X_920276-':('juntas','kit overview',
              'Conjunto completo em uma imagem; inclui contornos de cabeçote, cárter e várias juntas menores.'),
    'sevel_bloco_15':('engine','oblique spark-plug/breather side on wooden support',
              'Black elongated cover with filler near flywheel end; user identifies cover as a comparative variant'),
    '780830':('oil_pan','oblique interior with flange and baffles',
              'Curved asymmetric flange and stepped floor; no calibrated capacity or wall thickness'),
    '845764':('oil_pan','exterior of stepped reservoir',
              'Deep and shallow regions with bottom drain; perspective does not establish depths'),
    'referencia_coletores_selos':('engine','annotated manifold/core-plug side, timing right',
              'User annotation: blue three block core plugs, red four exhaust ports, yellow four intake ports; green two coolant interfaces for water-heated i.e. intake manifold'),
    '707064':('crank','oblique side; flywheel left, distribution right',
              'Five mains, four alternating throws, four dominant counterweights'),
    '683381':('crank','opposite oblique side; flywheel left, distribution right',
              'Complementary view of the same listing; not independent metrology'),
    '994280':('piston','collage: sides, crown, underside',
              'Three ring positions, hollow skirt, pin bosses, dish and two crown recesses'),
    '760527':('rod','perspective from cap and big end',
              'Split cap, two bolts, bushed small end and recessed beam'),
    'wireframe_com_polias':('timing','exploded perspective',
              'Cam, crank, auxiliary and tensioner belt; water pump shown separately'),
    '833139':('head','underside in perspective',
              'Head diameters support E-I-I-E-E-I-I-E longitudinal valve sequence'),
    '843166':('head','spark-plug side, springs exposed',
              'Eight spring assemblies in a longitudinal row; no calibrated valve inclination'),
    '726745':('cam_carrier','oblique top and spark-plug side, cover removed',
              'Four open bays with transverse integral bridges; current separate CAD caps are not a faithful casting'),
    '954033':('cam_carrier','opposite oblique top and end',
              'Confirms continuous cage walls, four bays and rounded end housings'),
    '621331':('head','manifold side with upper cage installed',
              'Eight ports at staggered heights, lower cage seam and curved vertical ribs'),
    'D_NQ_NP_2X_885508':('head','spark-plug side with valve cover installed',
              'Distinct lower head, upper cage and cover; this cover differs from the assembled black-cover variant'),
    'Lateral_cabeçote_com_guias_gimp_Captura de tela_2026-11-26_12-27-23.png':(
              'head','captura da vista 649747 com guias','Registro visual das guias do usuário na flange da válvula termostática.'),
    'guias_D_NQ_NP_2X_649747-':('head','projeto GIMP da vista 649747',
              'Guias dos centros na tela original em (210, 891) e (644, 939) px, origem no canto superior esquerdo.'),
    '649747':('head','cam end and water flange, cover installed',
              'Upper and lower cage seams have different apparent slopes relative to deck; no calibrated angle'),
    '833777':('head','opposite cam end with seal and hub, cover installed',
              'Nonrectangular cage end section and inclined seams; perspective precludes exact tilt measurement'),
    'cabeçote_cima':('cam_carrier','oblique upper windows and spark-plug side',
              'Four bays, integral bridges and six cover studs; sculpted walls instead of uniform extrusion'),
    'troca_junta_tampa_valvulas_carroCaptura de tela_2026-11-22_22-56-16.png':(
              'cam_carrier','gaiola instalada com tampa removida',
              'Quatro janelas e comando exposto, com o conjunto da bobina na extremidade junto à bateria.'),
    'troca_junta_tampa_valvulas_2_Captura de tela_2026-11-22_22-58-05.png':(
              'cam_carrier','detalhe da face de junta e das travessas',
              'Prisioneiros na borda, rebaixos e aberturas nas travessas entre as janelas.'),
    'cabeçote_D_NQ_NP_885508-':('head','tampa montada, lado das velas',
              'Vista geral da boca de óleo aberta, abas da tampa e linha de união com a gaiola.'),
    '2X_610418-':('head','superior oblíqua pelo lado dos coletores, com tampa',
              'O bocal com tampa preta avança para a ponta esquerda da foto. A linha de junta e os prisioneiros dos coletores orientam a vista.'),
    'cabeçote_lateral_perspectiva_D_NQ_NP_728942-':('head','extremidade do bocal de óleo',
              'Boca com rosca interna e reforços externos, fechamento do comando e flange de água abaixo.'),
    '901284':('head','water flange end, upper cage removed',
              'Scalloped mating outline, raised guide bosses and curved water opening; uncalibrated perspective'),
    '806433':('gasket','isolated elongated cover-interface outline',
              'Rounded perimeter and six fixing ears; no evidence of installed plane orientation'),
    '737590':('gasket','isolated scalloped upper-head-interface reference',
              'Curved recesses along one long edge; component assignment and metric scale remain comparative'),
    '980809':('gasket','isolated sump-interface outline',
              'Asymmetric rounded perimeter with curved setbacks; does not establish out-of-plane casting radii'),
    '939442':('head','oblique top without upper cage',
              'Eight exposed springs, scalloped upper cavity, guide bosses and retainer details'),
    '745438':('engine','manifold/core-plug side; flywheel left, timing right',
              'Complete assembly proportions, three core plugs and curved lower casting'),
    '959724':('engine','oblique timing end on wooden support',
              'Timing cover silhouette; wooden support obscures lower pulley region'),
    '600896':('engine','high oblique spark-plug/breather side',
              'Breather fitting, filter interface and black cover; perspective is not an angle measurement'),
    '946397':('engine','spark-plug/breather side; timing left, flywheel right',
              'Shared block/head outline, curved lower wall and exposed flywheel rim'),
    '795677':('engine','oblique flywheel and manifold side',
              'Flywheel face, six central bolts, ring gear and separated outer holes; no tooth count inferred'),
    '781290':('head_and_cam','head underside, loose valves and camshaft',
              'Combustion chamber shape, valve proportions and nonuniform camshaft end diameters'),
    '957036':('head','oblique top, valves and cage removed',
              'Eight guide bores, scalloped cavity walls and raised fixing bosses'),
    '882668':('head','underside in perspective',
              'Four noncircular chambers with two valve seats and spark-plug opening each'),
    '723789':('head','spark-plug side without cage',
              'Broad rounded ribs and bosses; useful for casting silhouette, not metric radii'),
}


# Only the named frames have been visually reviewed.
THERMOSTAT_FRAMES = {}
for times, view, detail in (
    ('10-50-54 10-51-40 10-52-25 10-52-39', 'montagem no motor',
     'Sequência da extremidade do cabeçote com bobina, suporte e mangueiras.'),
    ('10-52-53 10-53-15 10-53-44 10-55-36', 'bocais instalados',
     'Corpo sob o suporte da bobina e primeiros trechos das mangueiras com abraçadeiras.'),
    ('10-54-20 10-54-29 10-54-40', 'face do motor exposta',
     'Com a carcaça retirada aparecem a janela, a junta verde e os dois furos em diagonal.'),
    ('10-55-22', 'bocal aberto na montagem',
     'Boca maior livre junto à base do suporte, antes de conectar a mangueira.'),
):
    for timestamp in times.split():
        name = f'VALVULATERMOSTATICACaptura de tela_2026-11-26_{timestamp}.png'
        THERMOSTAT_FRAMES[name] = ('carcaca_termostatica', view, detail)

THERMOSTAT_BENCH = {}
for stems, view, detail in (
    ('110751155 110758186_HDR 110812454_HDR', 'largura da flange',
     'Mordentes nas bordas externas das duas orelhas de fixação.'),
    ('110931620_HDR', 'diâmetro externo do bocal maior', 'Mordentes junto ao ressalto terminal.'),
    ('110954058_HDR', 'diâmetro externo do bocal menor', 'Mordentes junto ao ressalto terminal.'),
    ('111020197_HDR 111038533_HDR 111244401_HDR', 'furos de fixação',
     'Mordentes apoiados nas bordas dos furos. O entrecentros exige uma estimativa indireta.'),
    ('111109357_HDR 111113565_HDR 111118793_HDR 111134655_HDR 111140628 111207165_HDR',
     'cavidade e elemento termostático', 'Escala em várias direções na face de montagem.'),
    ('111219261_HDR', 'perfil da carcaça', 'Vista oblíqua do corpo e dos bocais com paquímetro.'),
    ('111231457_HDR 111233956_HDR', 'espessura local da flange',
     'Uma ponta toca a face de apoio e a outra o ressalto traseiro de fixação.'),
    ('111258165_HDR', 'perfil dos bocais', 'Vista do corpo arredondado e dos dois bocais.'),
):
    for stem in stems.split():
        THERMOSTAT_BENCH[f'IMG_20261126_{stem}.jpg'] = ('carcaca_termostatica', view, detail)


# Installed components on the owner's engine, with a printed caliper scale.
COIL_AND_FILLER = {}
for stems, part, view, detail in (
    ('114053141_HDR 114059059', 'suporte_bobina', 'perfil junto à união com o motor',
     'Do ressalto junto à linha de união até a borda externa da fundição junto à bobina, cerca de 43 mm.'),
    ('114205137_HDR 114205881_HDR', 'suporte_bobina', 'conjunto instalado',
     'A tampa preta do óleo aparece ao lado da bobina. Os mordentes abrangem um trecho do suporte.'),
    ('114246354_HDR 114251093_HDR 114255366', 'suporte_bobina', 'largura transversal',
     'Suporte e bobina em vista transversal, com os mordentes nas extremidades do conjunto.'),
    ('114400449_HDR 114409541_HDR', 'suporte_bobina', 'rebaixo junto à bobina',
     'Haste do paquímetro na região entre o ressalto do suporte e o corpo preto da bobina.'),
    ('114427762_HDR 114434966_HDR 114509286_HDR', 'suporte_bobina', 'fixação em perfil',
     'Comparação entre faces externas na região de fixação da bobina.'),
    ('114709950_HDR 114723688_HDR 114756839_HDR', 'suporte_bobina', 'detalhes laterais',
     'Vistas da borda e dos ressaltos do suporte no conjunto montado.'),
    ('114130725_HDR 114133128_HDR', 'bocal_oleo', 'pescoço abaixo da tampa',
     'Mordentes abrangem a seção externa do pescoço do bocal.'),
    ('114226165_HDR', 'bocal_oleo', 'tampa de frente',
     'Mordentes nas bordas opostas da tampa preta, abertura próxima de 68 mm.'),
    ('114605545_HDR 114608513_HDR', 'bocal_oleo', 'perfil da tampa e do pescoço',
     'Vista da inclinação do bocal, da união na base e da borda estriada da tampa.'),
    ('114644023_HDR 114646170_HDR 114647917_HDR', 'bocal_oleo', 'ressalto roscado vizinho',
     'Mordentes sobre o exterior do ressalto cilíndrico ao lado do bocal.'),
    ('114701626_HDR 114816002_HDR', 'bocal_oleo', 'fixações próximas',
     'Detalhes das fixações ao redor do bocal no conjunto instalado.'),
    ('114830230_HDR 114832665_HDR', 'bocal_oleo', 'junção entre pescoço e tampa',
     'Mordentes próximos da junção com a tampa preta, vista de lado e em viés.'),
):
    for stem in stems.split():
        COIL_AND_FILLER[f'IMG_20261126_{stem}.jpg'] = (part, view, detail)


LOOSE_VALVE_COVER = {
    '201617543000572.png': ('perfil longitudinal', 'A boca se projeta além da extremidade da tampa.'),
    '215616663404314.png': ('superior oblíqua', 'Contorno inteiro, orelhas de fixação e abas laterais.'),
    '216654184908095.png': ('extremidade oposta ao bocal', 'Ombro abaulado, degrau transversal e ressaltos perfurados.'),
    '218632427668720.png': ('oblíqua a partir do bocal', 'O pescoço domina a extremidade e se une à lateral da fundição.'),
    '219683186606960.png': ('detalhe do bocal', 'Base alargada junto a duas orelhas e borda estriada da tampa preta.'),
    '223649425194962.png': ('face interna', 'Seis furos principais na flange, nervura longitudinal e travessas na cavidade.'),
}


def run():
    rows = []
    photos = ROOT/'PhotosMotor'
    installed_dir = photos/'suporte_bobina_bocal_oleo'
    cover_dir = photos/'TAMPA_VALVULAS'
    originals = list(photos.iterdir()) + [installed_dir/name for name in COIL_AND_FILLER]
    originals.extend(cover_dir/name for name in LOOSE_VALVE_COVER)
    for path in sorted(originals):
        installed = path.parent == installed_dir
        loose_cover = path.parent == cover_dir
        bench = path.name in THERMOSTAT_BENCH
        frame = path.name in THERMOSTAT_FRAMES
        if not path.is_file() or not (loose_cover or installed or bench or frame or any(k in path.name for k in
                ('virabrequim','pistao','biela','valvula','wireframe',*REVIEWED))):
            continue
        reviewed = THERMOSTAT_BENCH.get(path.name) or THERMOSTAT_FRAMES.get(path.name)
        if loose_cover:
            reviewed = ('tampa_valvulas', *LOOSE_VALVE_COVER[path.name])
        elif installed:
            reviewed = COIL_AND_FILLER[path.name]
        elif reviewed is None:
            reviewed = next((v for k,v in REVIEWED.items() if k in path.name),None)
        variant = 'listing claim, not independently verified'
        if loose_cover:
            variant = 'loose valve cover, application unconfirmed'
        elif installed:
            variant = 'installed coil support and oil filler, user photos'
        elif bench:
            variant = 'user bench photos, housing marked VALCLEI 3325.87'
        elif frame:
            variant = 'installation reference supplied by user'
        elif path.name.startswith('troca_junta_tampa_valvulas'):
            variant = 'service screenshot, installation reference'
        elif path.name == 'referencia_coletores_selos.png' or path.name.startswith(
                ('guias_D_NQ_NP_2X_649747-', 'Lateral_cabeçote_com_guias_gimp_')):
            variant = 'user-annotated comparative reference; dimensions unconfirmed'
        rows.append({'path':str(path.relative_to(ROOT)),
                     'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'reviewed':bool(reviewed),'part':reviewed[0] if reviewed else 'unclassified',
                     'view':reviewed[1] if reviewed else 'not visually inspected',
                     'observation':reviewed[2] if reviewed else None,
                     'scale':'printed caliper scale, approximate' if bench or installed else 'uncalibrated',
                     'variant':variant})
    manual = ROOT/'PhotosECU/OCR_03-1.Tipo 1.6 SPI.pdf'
    engine_manual = ROOT/'PhotosECU/04-1.Motor 1580spi Monomotronic.pdf'
    report = {'photos':rows,'manual':{'path':str(manual.relative_to(ROOT)),
              'sha256':hashlib.sha256(manual.read_bytes()).hexdigest(),
              'pages_visually_reviewed_this_stage':[9,10,11,12,13,14,15,16,17,20]},
              'catalog_pdf':catalog_record(),
              'reuse_audit':'See cad/sevel16/PROGRESS.md; existing mesh interfaces incompatible with master datum'}
    report['engine_disassembly_manual'] = {
        'path':str(engine_manual.relative_to(ROOT)),
        'sha256':hashlib.sha256(engine_manual.read_bytes()).hexdigest(),
        'pdf_pages_visually_reviewed':[12,13,14],
        'printed_pages':[10,11,12],
        'section':'10. Motor — Desmontagem na bancada',
        'evidence':'MANUAL_TARGET',
        'scope':'Component identity, assembly relationships and qualitative outlines; no calibrated dimensions',
        'observations':[
            'PX003G502: valve cover and separate six-fixing gasket',
            'PX003G504: cam sprocket with five large lightening openings',
            'PX003G509/510: toothed crank sprocket and external pulley are separate components',
            'PX004G504: water pump assembly with smooth pulley, distinct from toothed timing drive',
            'PX005G501: four-window upper cage visible on removed head',
            'PX005G505: flywheel face and starter ring gear',
            'PX005G506: auxiliary shaft, flange and separate gasket',
            'PX005G507: asymmetric sump and matching gasket'],
        'unknown':['tooth counts','pulley diameters and axial offsets',
                   'trigger-wheel identity and phase','cage and valve inclination angles']}
    (OUTPUT/'reports/moving_sources.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'{len(rows)} sources catalogued; {sum(r["reviewed"] for r in rows)} visually reviewed')


if __name__=='__main__':
    run()
