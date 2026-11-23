"""Versioned external timing assembly, without overwriting its flywheel baseline."""
import hashlib
import json
import FreeCAD as App
import FreeCADGui as Gui
from config import OUTPUT, load
from assembly import add_part, apply_pose
import timing_parts


def run():
    params,frame = load()
    source = OUTPUT/'models/SEVEL_Flywheel_A4_v001.FCStd'
    old = next((d for d in App.listDocuments().values() if d.FileName==str(source)),None)
    old = old or App.openDocument(str(source))
    assert old.Phase.ThetaDeg==0
    previous = json.loads((OUTPUT/f'reports/{old.Name}.parameters.json').read_text())
    assert {k:v for k,v in params.items() if k not in ('timing_visual_estimated','auxiliary_nominal')}==previous
    index = 1
    while (OUTPUT/f'models/SEVEL_Timing_A4_v{index:03d}.FCStd').exists():
        index += 1
    parts = timing_parts.build(params,frame)
    doc = App.newDocument(f'SEVEL_Timing_A4_v{index:03d}')
    phase = doc.addObject('App::FeaturePython','Phase')
    phase.addProperty('App::PropertyFloat','ThetaDeg','Kinematics')
    phase.addProperty('App::PropertyString','EvidenceStatus','Provenance')
    phase.EvidenceStatus = frame['status']
    for original in old.Objects:
        if not hasattr(original,'Shape'):
            continue
        obj = add_part(doc,original.Name,original.Shape.copy(),original.MotionType,
                       original.CylinderId,original.ViewObject.ShapeColor)
        obj.Placement = original.Placement
        for prop,kind in [('ValveKind','String'),('SpringKind','String'),('RestBase','Vector')]:
            if hasattr(original,prop):
                obj.addProperty('App::Property'+kind,prop,'Assembly')
                setattr(obj,prop,getattr(original,prop))
        obj.ViewObject.Visibility = obj.Name not in ('Block','CamCarrier')
    for name,(shape,motion) in parts.items():
        color = (0.22,0.24,0.27) if name=='TimingBelt' else (0.52,0.54,0.56)
        obj = add_part(doc,name,shape,'fixed' if motion.endswith('_fixed') else motion,color=color)
        if motion=='aux_fixed':
            p = params['casting_visual_estimated']['value']
            obj.Placement.Base = App.Vector(0,p['aux_y'],p['aux_z'])
            obj.ViewObject.ShapeColor = (0.71,0.61,0.37)
        elif motion=='tensioner_fixed':
            p = params['timing_visual_estimated']['value']
            obj.Placement.Base = App.Vector(0,p['tensioner_y_mm'],p['tensioner_z_mm'])
    apply_pose(doc,0,params,frame,update_springs=False)
    solids = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(solids)==182 and len({o.PartId for o in solids})==182
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in solids)
    App.setActiveDocument(doc.Name)
    Gui.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewIsometric()
    Gui.activeDocument().activeView().fitAll()
    path = OUTPUT/f'models/{doc.Name}.FCStd'
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    assert all(o.Shape.isValid() for o in doc.Objects if hasattr(o,'Shape'))
    report = {'status':'BUILT_EXTERNAL_TIMING_CHECKS_PENDING','document':doc.Name,'solids':182,
              'source_baseline':str(source),'source_baseline_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'added_parts':list(parts),
              'limits':['20/40/20 teeth and axial positions are provisional',
                        'smooth stationary belt envelope; no tooth meshing or belt material animation',
                        'auxiliary front journal only; rear journal, internal shaft and oil-pump drive pending',
                        'trigger wheel, sensor and external accessory pulley pending',
                        'inherits provisional A3 valve and cage inclinations']}
    (OUTPUT/f'reports/{doc.Name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{doc.Name}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return doc


if __name__=='__main__':
    run()
