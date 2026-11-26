"""Register the owner's 917 × 216 manifold gasket photo on the eight CAD ports."""
from bisect import bisect_right
import FreeCAD as App
import Part
from valvetrain_layout import valves

V = App.Vector
PORTS = [(128,97),(219,132),(328,131),(419,91),(529,88),(619,124),(726,120),(813,79)]
FIXINGS = [(77,66),(157,149),(362,83),(474,107),(586,79),(783,131),(861,45)]
OUTLINE = [(882,40),(879,32),(867,24),(849,24),(797,31),(770,47),(755,50),
           (578,54),(545,38),(521,36),(497,47),(478,70),(471,69),(463,58),
           (450,47),(425,39),(404,42),(370,59),(206,65),(175,63),(146,48),
           (75,45),(64,49),(58,55),(54,69),(79,123),(90,137),(170,179),
           (186,185),(351,183),(373,175),(380,167),(387,150),(394,145),
           (532,140),(558,142),(571,166),(586,175),(678,175),(809,169),
           (811,141),(842,123),(856,109),(881,53)]


def profile(params,frame):
    h = params['head_lower_casting_estimated']['value']
    rows = valves(params,frame)
    centers = [(r['axis_origin_mm'][0],h[r['kind']+'_port_z_mm']) for r in rows]
    # Register X by adjacent centers. The photo line of equal physical height
    # tilts upwards to the right. Correct this before measuring a Z offset.
    slope = (PORTS[-1][1]-PORTS[0][1])/(PORTS[-1][0]-PORTS[0][0])
    scale = (centers[1][1]-centers[0][1])/(PORTS[1][1]-PORTS[0][1]-slope*(PORTS[1][0]-PORTS[0][0]))
    def project(uv):
        u,v = uv
        i = max(0,min(len(PORTS)-2,bisect_right([p[0] for p in PORTS],u)-1))
        t = (u-PORTS[i][0])/(PORTS[i+1][0]-PORTS[i][0])
        x,z = [(1-t)*a+t*b for a,b in zip(centers[i],centers[i+1])]
        base_v = (1-t)*PORTS[i][1]+t*PORTS[i+1][1]
        return V(x,0,max(h['head_gasket_thickness_mm']+.25,z+(v-base_v)*scale))
    # Round the digitized outline between neighbouring sample midpoints.
    pts = [project(uv) for uv in OUTLINE]
    edges = []
    for i,p in enumerate(pts):
        prev,nxt = pts[i-1],pts[(i+1)%len(pts)]
        curve = Part.BezierCurve()
        curve.setPoles([(prev+p)*.5,p,(p+nxt)*.5])
        edges.append(curve.toShape())
    return Part.Face(Part.Wire(edges)),[project(uv) for uv in FIXINGS]
