"""Extend the verified A2 checkpoint with a separately identifiable SOHC stack."""
import json
import FreeCAD as App
from config import OUTPUT, load
from assembly import add_part, apply_pose
from capture_checkpoint import prepare_view
from valvetrain_layout import valves
import camshaft
import cam_carrier
import valve_parts
import valve_springs


def run():
    params,frame = load()
    source = OUTPUT/'models/SEVEL_Moving_A2_v003.FCStd'
    old = next((d for d in App.listDocuments().values() if d.FileName==str(source)),None)
    old = old or App.openDocument(str(source))
    index = 1
    while (OUTPUT/f'models/SEVEL_ValveTrain_A3_v{index:03d}.FCStd').exists():
        index += 1
    name = f'SEVEL_ValveTrain_A3_v{index:03d}'
    doc = App.newDocument(name)
    phase = doc.addObject('App::FeaturePython','Phase')
    phase.addProperty('App::PropertyFloat','ThetaDeg','Kinematics')
    phase.addProperty('App::PropertyString','EvidenceStatus','Provenance')
    phase.EvidenceStatus = frame['status']
    for original in old.Objects:
        if not hasattr(original,'Shape'):
            continue
        obj = add_part(doc,original.Name,original.Shape.copy(),original.MotionType,
                       original.CylinderId,original.ViewObject.ShapeColor)
        obj.ViewObject.Visibility = original.ViewObject.Visibility
    shape,_ = camshaft.build(params,frame)
    add_part(doc,'Camshaft',shape,'cam',color=(0.48,0.50,0.54))
    for label,shape in cam_carrier.build(params,frame).items():
        obj = add_part(doc,label,shape,color=(0.68,0.70,0.73))
        obj.ViewObject.Visibility = False
    rows = valves(params,frame)
    for row in rows:
        x,y,_ = row['axis_origin_mm']
        pieces = valve_parts.build(params,row)
        for kind in ('inner','outer'):
            pieces[kind.title()+'Spring'] = (valve_springs.build(params,kind),'spring')
        for label,(shape,motion) in pieces.items():
            color = (0.65,0.67,0.70)
            if label=='Valve':
                color = (0.75,0.46,0.28) if row['kind']=='exhaust' else (0.40,0.59,0.78)
            if 'Spring' in label and 'Seat' not in label:
                color = (0.25,0.28,0.31)
            if label=='Guide':
                color = (0.71,0.61,0.37)
            obj = add_part(doc,row['id']+'_'+label,shape,motion,row['cylinder'],color)
            obj.addProperty('App::PropertyString','ValveKind','Assembly')
            obj.ValveKind = row['kind']
            obj.addProperty('App::PropertyVector','RestBase','Assembly')
            obj.RestBase = App.Vector(x,y,0)
            obj.Placement.Base = obj.RestBase
            if motion=='spring':
                obj.addProperty('App::PropertyString','SpringKind','Assembly')
                obj.SpringKind = label.removesuffix('Spring').lower()
    apply_pose(doc,0,params,frame)
    parts = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(parts)==166
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in parts)
    App.setActiveDocument(doc.Name)
    prepare_view('Isometric')
    path = OUTPUT/f'models/{name}.FCStd'
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    assert all(o.Shape.isValid() for o in doc.Objects if hasattr(o,'Shape'))
    (OUTPUT/f'reports/{name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    report = {'status':'GEOMETRY_BUILT_CONTACT_CHECKS_PENDING','document':name,'solids':len(parts),
              'source_bottom_end':str(source),'valves':rows,
              'limits':['continuous four-window carrier; lower scalloped flange provisional; no lower-head casting',
                        'cam bearing end mapping corroborated by other application, not confirmed on target',
                        'spring ends unground; CAD pipe used only at checkpoints']}
    (OUTPUT/f'reports/{name}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(name,len(parts),'solids saved and reopened')
    return doc


if __name__=='__main__':
    run()
