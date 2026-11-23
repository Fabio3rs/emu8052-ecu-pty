"""Read-only source audit; names alone never establish photo orientation."""
import hashlib
import json
from config import ROOT, OUTPUT
from catalog_source import record as catalog_record

REVIEWED = {
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
    '649747':('head','cam end and water flange, cover installed',
              'Upper and lower cage seams have different apparent slopes relative to deck; no calibrated angle'),
    '833777':('head','opposite cam end with seal and hub, cover installed',
              'Nonrectangular cage end section and inclined seams; perspective precludes exact tilt measurement'),
    'cabeçote_cima':('cam_carrier','oblique upper windows and spark-plug side',
              'Four bays, integral bridges and six cover studs; sculpted walls instead of uniform extrusion'),
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


def run():
    rows = []
    for path in sorted((ROOT/'PhotosMotor').iterdir()):
        if not path.is_file() or not any(k in path.name for k in
                ('virabrequim','pistao','biela','valvula','wireframe',*REVIEWED)):
            continue
        reviewed = next((v for k,v in REVIEWED.items() if k in path.name),None)
        rows.append({'path':str(path.relative_to(ROOT)),
                     'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'reviewed':bool(reviewed),'part':reviewed[0] if reviewed else 'unclassified',
                     'view':reviewed[1] if reviewed else 'not visually inspected',
                     'observation':reviewed[2] if reviewed else None,
                     'scale':'uncalibrated',
                     'variant':('user-annotated comparative reference; dimensions unconfirmed'
                                if path.name=='referencia_coletores_selos.png'
                                else 'listing claim, not independently verified')})
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
