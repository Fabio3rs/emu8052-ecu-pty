"""Locally visible high-tension cable ends in the owner's SPI installation."""
import FreeCAD as App
import Part

V = App.Vector
UP = V(0,0,1)
OUT = V(-1,0,0)


def boot_and_lead(spec,cable_length):
    mouth,radius = spec["mouth_radius"],spec["elbow_radius"]
    bend = spec["bend_axis_radius"]
    rise = spec["elbow_offset"]-bend
    foot = V(0,0,rise)
    end = V(-bend,0,rise+bend)
    middle = V(-bend+bend*2**-.5,0,rise+bend*2**-.5)
    path = Part.Wire([Part.Arc(foot,middle,end).toShape()])
    circle = Part.Wire([Part.makeCircle(radius,foot,UP)])
    elbow = path.makePipeShell([circle],True,False)
    sleeve = Part.makeCone(mouth,radius,rise)
    outlet = spec["outlet_offset"]
    tip = V(-outlet,0,end.z)
    lip = spec["end_ring_length"]
    arm = Part.makeCone(radius,spec["outlet_radius"],outlet-bend,end,OUT)
    bead = Part.makeCylinder(spec["end_ring_radius"],lip,tip-OUT*lip,OUT)
    body = sleeve.fuse([elbow,arm,bead]).removeSplitter()
    # The Bosch tower tapers from radius 9 to 7.7 over its exposed length.
    # Leave the black shoulder as the annular seating face and the metal socket clear.
    bore = Part.makeCone(9.15,7.8,19,V(0,0,-.1))
    bore = bore.fuse(Part.makeCylinder(7.8,1,V(0,0,18.8)))
    socket = Part.makeCylinder(spec["wire_radius"],5.1,tip-OUT*5,OUT)
    boot = body.cut([bore,socket]).removeSplitter()
    lead = Part.makeCylinder(spec["wire_radius"],cable_length+5,tip-OUT*5,OUT)
    for shape in (boot,lead):
        shape.check(True)
        assert shape.isValid() and len(shape.Solids)==1 and shape.Solids[0].isClosed()
    return boot,lead


def build(doc,params):
    spec = params["spi_coil_boots_estimated"]["value"]
    # On the installed top view, +X points out of the coil and the wires
    # turn toward -Y. The lower near elbow is visible below the two upper ones.
    sockets = (("UpperFar",25,22.5),("UpperNear",-25,22.5),("LowerNear",-25,-22.5))
    result = []
    for (station,y,z),length in zip(sockets,spec["visible_wire_lengths"],strict=True):
        boot,lead = boot_and_lead(spec,length)
        place = doc.IgnitionCoil.Placement.multiply(App.Placement(V(y,z,63),App.Rotation()))
        for shape,kind,color in ((boot,"Boot",(.40,.39,.36)),(lead,"Lead",(.13,.13,.13))):
            shape.Placement = place.multiply(shape.Placement)
            result.append(("Ignition"+kind+station,shape,color))
    return result
