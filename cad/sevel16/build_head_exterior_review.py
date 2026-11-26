"""Build the photo-reviewed assembled motor from the saved A5 v007 checkpoint."""
import hashlib
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
from assembly import add_part
from config import OUTPUT, load
import block_oil_filter
import head_carrier_exterior
import head_flanks
import head_ignition
import head_thermostat
import head_water_end
import valve_cover

SOURCE = OUTPUT/'models/SEVEL_Accessories_A5_v007_DrainReview.FCStd'
SOURCE_HASH = 'ec0fa4ed9557d42e7dcb99bf64c7f8f67866ffd9340a67efe7fb3f3d18f888c0'
DEST = OUTPUT/'models/SEVEL_Accessories_A5_v008_HeadExterior.FCStd'
COLORS = {
    'IgnitionCoilMount': (.64,.65,.63), 'IgnitionCoil': (.17,.18,.19),
    'ThermostatHousing': (.62,.64,.63), 'ThermostatGasket': (.24,.32,.29),
    'ThermostatMainHose': (.16,.17,.17), 'ThermostatBranchHose': (.16,.17,.17),
    'OilFilterCartridge': (.86,.84,.77),
}


def run(destination=DEST):
    destination = Path(destination)
    if destination.exists() or destination.stem in App.listDocuments():
        raise FileExistsError(destination)
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_HASH:
        raise ValueError('Expected the reviewed v007 checkpoint')
    params, frame = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(SOURCE))
        head = head_flanks.spark_face(doc,params,frame)
        head = head_flanks.manifold_face(head,params,frame)
        changed = {'HeadLower':head_water_end.revised(head,params,frame),
                   'CamCarrier':head_carrier_exterior.revised(doc,params,frame)}
        cover = valve_cover.build(params,frame,photo_review=True)
        changed.update({key:cover[key] for key in ('ValveCover','OilFillerCap')})
        new = head_ignition.build(params,frame)
        new.update(head_thermostat.build(params,frame))
        new['OilFilterCartridge'] = block_oil_filter.build(doc,params)
        for name, shape in {**changed, **new}.items():
            if not shape.isValid() or len(shape.Solids)!=1 or not shape.Solids[0].isClosed():
                raise ValueError(('Invalid exterior part',name))
            if name in new:
                obj = add_part(doc,name,shape,color=COLORS[name])
            else:
                obj = doc.getObject(name)
                obj.Shape = shape
            obj.ViewObject.Deviation = .07
            obj.ViewObject.DisplayMode = 'Flat Lines'
        doc.ValveCover.ViewObject.ShapeColor = (.64,.65,.63)
        doc.OilFillerCap.ViewObject.ShapeColor = (.13,.14,.15)
        for obj in doc.Objects:
            if hasattr(obj,'Shape'):
                obj.Visibility = True
        doc.Label = destination.stem
        doc.recompute()
        view = Gui.activeDocument().activeView()
        view.setCameraOrientation(App.Rotation(App.Vector(),App.Vector(0,0,1),
                                               App.Vector(.72,-1,.58),'ZYX').Q)
        view.fitAll()
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
    return App.openDocument(str(destination))
