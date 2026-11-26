"""Hollow thermostat casting, seal and the visible starts of both hoses (mm)."""
import FreeCAD as App
import Part
from head_water_end import AXIS, LEFT, RIGHT, MOUTH, OUTLINE, datum, profile

V = App.Vector


def ring(center,normal,radius):
    return Part.Wire([Part.makeCircle(radius,center,normal)])


def along_x(face, distance, thickness):
    face = face.copy()
    face.translate(AXIS*distance)
    return face.extrude(AXIS*thickness)


def hose(tip, direction, radius, bend):
    start = tip-direction*10
    mid = tip+direction*18
    finish = mid+direction*29+bend
    last = (direction*29+bend*2).normalize()
    path = [(start,direction),(tip,direction),(mid,direction),(finish,last)]
    exterior = [ring(p,n,radius+3) for p,n in path]
    interior = [ring(start-direction,n,radius+.35) if i==0 else
                ring(p+(last if i==3 else V()),n,radius+(.35 if i==1 else -.8))
                for i,(p,n) in enumerate(path)]
    return Part.makeLoft(exterior,True,False).cut(Part.makeLoft(interior,True,False)).removeSplitter()


def build(params,frame):
    h,project = datum(params,frame)
    depth = h['water_end_flange_depth_mm']
    mouth = profile(MOUTH,project)
    base = project((427,915))+AXIS*depth
    # The mating axes follow the provisional head. Only the loose flange width
    # (~96) and spigot ODs (~37/16.5) use the caliper photographs.
    def wide(pixel):
        p = project(pixel)
        return V(p.x,1.27*p.y,p.z)
    flange = profile(OUTLINE,wide)
    gasket = along_x(flange,depth,1)
    casting = along_x(flange,depth+1,7)
    def dome(rows):
        return Part.makeLoft([ring(base+V(x,y,z),AXIS,r) for x,y,z,r in rows],True,False)
    crown = dome([(7,0,0,24),(14,0,1,24.5),(25,-2,2,23),(36,-3,2,17),(40,-4,2,4)])
    # A cylindrical inlet feeds a rounded chamber shared by both outlets.
    inside = Part.makeCylinder(18,17,base+AXIS*3,AXIS).fuse(Part.makeSphere(18,base+AXIS*18))
    additions,cutters,hoses = [crown],[along_x(mouth,depth-1,14),inside],{}
    for tag,offset,slope,length,radius,bend in (
            ('Main',V(23,-10,0),V(.31,-.945,-.1),49,18.5,V(2,0,-16)),
            ('Branch',V(22,10,3),V(.11,.91,.4),40,8.25,V(-3,5,8))):
        normal = slope.normalize()
        root = base+offset
        tip = root+normal*length
        additions.extend([Part.makeCylinder(radius,length,root,normal),
                          Part.makeCone(radius,radius+1,2,tip-normal*5,normal),
                          Part.makeCone(radius+1,radius,3,tip-normal*3,normal)])
        cutters.append(Part.makeCylinder(radius-2.3,length+6,root-normal*4,normal))
        # Sleeve inner diameter clears the small retaining bead.
        hoses['Thermostat'+tag+'Hose'] = hose(tip,normal,radius+1.15,bend)
    holes = [Part.makeCylinder(4.5,10,project(px)+AXIS*(depth-.5),AXIS) for px in (LEFT,RIGHT)]
    void = cutters[0].fuse(cutters[1:]).removeSplitter()
    shell = casting.fuse(additions).cut(void).cut(holes).removeSplitter()
    return {'ThermostatHousing':shell,'ThermostatGasket':gasket.cut(holes+[cutters[0]]).removeSplitter(),
            **hoses}
