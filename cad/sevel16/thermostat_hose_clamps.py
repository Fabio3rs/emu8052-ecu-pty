"""Two visible worm-drive clamps, seated on the outer rubber sleeves."""
import FreeCAD as App
import Part

from head_thermostat import spigots
from head_water_end import AXIS, datum

V = App.Vector


def build(doc, params, frame):
    h, project = datum(params, frame)
    base = project((427,915)) + AXIS*h["water_end_flange_depth_mm"]
    dims = params["thermostat_clamps_estimated"]["value"]
    clamps, hoses = [], {}
    for tag, start, axis, length, radius, _ in spigots(base):
        width, thickness, sign = dims[tag]
        center = start+axis*(length-3)
        hose_name = "Thermostat"+tag+"Hose"
        rubber = doc.getObject(hose_name).Shape
        outer = radius+4.15  # The uncompressed sleeve around the spigot bead.
        band_base = center-axis*(width/2)
        seated = outer-dims["compression"]
        # The clamp compresses a narrow cylindrical seat into the rubber.
        # Keep the hose lumen and neighboring retaining bead intact.
        stock = Part.makeCylinder(outer+4, width, band_base, axis)
        seat_tool = stock.cut(Part.makeCylinder(seated, width+2, band_base-axis, axis))
        hoses[hose_name] = rubber.cut(seat_tool).removeSplitter()
        band = Part.makeCylinder(seated+thickness, width, band_base, axis)
        band = band.cut(Part.makeCylinder(seated, width+2, band_base-axis, axis))
        up = V(0,0,1)
        radial = (up-axis*up.dot(axis)).normalize()*sign
        tangent = radial.cross(axis).normalize()
        # The rolled band carries a pressed saddle. The screw barrel sits
        # above it, clear of the hose, as in the mounted end view 10-53-44.
        place = App.Placement(center,App.Rotation(tangent,radial,axis,"ZXY"))
        cradle = Part.makeBox(9,2.3,4.8,V(-4.5,seated+.12,-2.4))
        screw = V(-5,seated+4.1,0)
        barrel = Part.makeCylinder(3,11,screw,V(1,0,0))
        head = Part.makeCylinder(3.6,2.4,screw+V(10.7,0,0),V(1,0,0))
        fastener = cradle.fuse([barrel,head]).removeSplitter()
        fastener.Placement = place.multiply(fastener.Placement)
        band = band.fuse(fastener).removeSplitter()
        assert band.isValid() and len(band.Solids) == 1
        assert band.distToShape(hoses[hose_name])[0] < 1e-6
        lining = Part.makeCylinder(seated, width-.1, band_base+axis*.05, axis).cut(
            Part.makeCylinder(seated-.05, width+1, band_base-axis*.5, axis))
        assert abs(lining.cut(hoses[hose_name]).Volume) < 1e-5, hose_name
        clamps.append(("Thermostat"+tag+"Clamp",band,(.54,.53,.48)))
    return hoses, clamps
