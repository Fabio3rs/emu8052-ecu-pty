"""Ignition coil and cast mount. Local XY is the YZ end face, +Z points out."""
import FreeCAD as App
import Part
from cam_carrier import rounded_prism
from config import layout
from head_carrier_exterior import MOUNT_HOLES

V = App.Vector
UP = V(0,0,1)
COIL_FEET = [(y,z) for y in (-45,45) for z in (-26,26)]


def rectangle(width,height,z,thickness,radius):
    return rounded_prism(-width/2,-height/2,z,width,height,thickness,radius)


def cone_at(y,z,depth,bottom,top,length):
    return Part.makeCone(bottom,top,length,V(y,z,depth))


def build(params,frame, *, mount_profile=None):
    p = params['valvetrain_layout_estimated']['value']
    hi = layout(params,frame)['supports'][-1]+p['cam_journal_width_mm']/2
    place = App.Placement(V(hi+4,0,p['cam_axis_z_mm']),App.Rotation(V(1,1,1),120))
    # Photo 114059059: estimated 43 mm from visible joint to coil seat.
    seat = 43
    base = rectangle(74,72,0,6,14)
    base = base.cut(Part.makeCylinder(27.6,8,V(0,0,-1)))
    plate = rectangle(110,68,seat-7,7,9).cut(rectangle(81,46,seat-8,9,7))
    ribs = []
    for side in (-1,1):
        for bottom, width, drift in ((-26,10,-1),(13,11,4)):
            wires = []
            for yy, vv, depth, wy, wv in ((side*27,bottom,4,10,width),
                    (side*37,bottom+drift,23,8,width-2),(side*46,bottom,seat-5,10,width+1)):
                pts = [V(yy+a*wy/2,vv+b*wv/2,depth) for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))]
                wires.append(Part.makePolygon(pts+[pts[0]]))
            ribs.append(Part.makeLoft(wires,True,False))
    # Upper cast ear and central stiffening rib seen in 114251093.
    ear = Part.makeCylinder(8,15,V(4,23,seat-8.3),V(0,1,0))
    strut = Part.Face(Part.makePolygon([V(1,28,3),V(1,31,seat-4),
                 V(1,21,seat-4),V(1,22,4),V(1,28,3)])).extrude(V(5,0,0))
    castings = ribs+[plate,ear,strut]
    if mount_profile is not None:
        # The wide shoulder crosses the top of the cast support and tapers
        # into the eye. All coordinates are in the existing end-face frame.
        contours = []
        for depth, half, center, height in mount_profile:
            section = rounded_prism(-half, center-height/2, depth, 2*half, height, 1, 2)
            face = next(f for f in section.Faces if abs(f.BoundBox.ZMax - depth) < 1e-6)
            contours.append(face.OuterWire)
        apron = Part.makeLoft(contours, True, False)
        castings.append(apron.cut(Part.makeCylinder(27.6, 7.5, V(0,0,-.5))))
    mount = base.fuse(castings)
    holes = [Part.makeCylinder(3.5,9,V(y,z,-1)) for y,z in MOUNT_HOLES]
    holes += [Part.makeCylinder(2.5,11,V(y,z,seat-10)) for y,z in COIL_FEET]
    holes.append(Part.makeCylinder(3,10,V(4,39,seat-8.3),V(0,-1,0)))
    mount = mount.cut(holes).removeSplitter()

    # Bosch drawing, p.3: width 107, hole pitch 90 x 52, tower pitch 50 x 45.
    coil = rectangle(82,57,seat,20,8)
    rear = rectangle(60.5,40.5,seat-17,18,4)
    feet, bores = [], []
    for y,z in COIL_FEET:
        feet.append(rounded_prism((y-8.5) if y<0 else y-12, z-6.5,seat,20.5,13,6,5.8))
        bores.append(Part.makeCylinder(3.05,7,V(y,z,seat-.5)))
    towers = []
    for y in (-25,25):
        for z in (-22.5,22.5):
            towers.append(Part.makeCylinder(12.5,20,V(y,z,seat)))
            towers.append(cone_at(y,z,seat+19.8,9,7.7,18.8))
            bores.append(Part.makeCylinder(4.9,15,V(y,z,seat+25)))
    connector = rounded_prism(-10,-46,seat+3,20,21,13,2)
    socket = Part.makeBox(15,9,8,V(-7.5,-46.5,seat+5.5))
    coil = coil.fuse([rear,connector,*feet,*towers]).cut(bores+[socket]).removeSplitter()
    for shape in (mount,coil):
        shape.Placement = place.multiply(shape.Placement)
    return {'IgnitionCoilMount':mount,'IgnitionCoil':coil}
