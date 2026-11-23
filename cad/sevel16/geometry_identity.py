"""Exact canonical serialization before a Boolean symmetric-difference fallback."""
import Part
from check_auxiliary import difference as boolean_difference


def difference(a,b):
    assert not a.isNull() and not b.isNull()
    assert a.isValid() and b.isValid()
    # Identical B-reps need no Boolean operation. OCC may fail cutting a
    # complex swept body by its own serialized copy despite valid operands.
    def canonical(shape):
        # One import normalizes OCC's stored topology flags (e.g. Checked).
        # Geometry, locations and topology remain in the full comparison.
        restored = Part.Shape()
        restored.importBrepFromString(shape.exportBrepToString())
        return restored.exportBrepToString()
    if canonical(a)==canonical(b):
        return 0.0
    return boolean_difference(a,b)


def sampled_equivalence(a,b):
    """Measured reconstruction check when OCC cannot subtract valid copies.

    This is finite surface/trim sampling, not exact Boolean identity.
    Topology order, surface types, orientation and parameter domains must agree.
    """
    assert a.isValid() and b.isValid() and not a.isNull() and not b.isNull()
    counts = {}
    for key in ('Solids','Shells','Faces','Wires','Edges','Vertexes'):
        counts[key] = len(getattr(a,key))
        assert counts[key]==len(getattr(b,key)),key
    surface,edges,ranges,areas = [],[],[],[]
    for f,g in zip(a.Faces,b.Faces):
        assert type(f.Surface)==type(g.Surface) and f.Orientation==g.Orientation
        assert len(f.Wires)==len(g.Wires) and len(f.Edges)==len(g.Edges)
        ranges.extend(abs(x-y) for x,y in zip(f.ParameterRange,g.ParameterRange))
        areas.append(abs(f.Area-g.Area))
        u0,u1,v0,v1 = f.ParameterRange
        for i in range(9):
            for j in range(9):
                u,v = u0+(u1-u0)*i/8,v0+(v1-v0)*j/8
                surface.append((f.valueAt(u,v)-g.valueAt(u,v)).Length)
    zero_length = 0
    for e,f in zip(a.Edges,b.Edges):
        assert e.Orientation==f.Orientation and len(e.Vertexes)==len(f.Vertexes)
        assert abs(e.Length-f.Length)<1e-7
        if e.Length<1e-12:
            assert f.Length<1e-12
            edges.extend((v.Point-w.Point).Length for v,w in zip(e.Vertexes,f.Vertexes))
            zero_length += 1
            continue
        assert type(e.Curve)==type(f.Curve)
        assert max(abs(e.FirstParameter-f.FirstParameter),abs(e.LastParameter-f.LastParameter))<1e-7
        for j in range(33):
            t = e.FirstParameter+(e.LastParameter-e.FirstParameter)*j/32
            edges.append((e.valueAt(t)-f.valueAt(t)).Length)
    vertices = max((v.Point-w.Point).Length for v,w in zip(a.Vertexes,b.Vertexes))
    result = {'method':'Ordered surface and trim sampling; not exact B-rep identity',
        'counts':counts,'surface_samples':len(surface),'edge_samples':len(edges),
        'zero_length_edges_checked':zero_length,'maximum_surface_error_mm':max(surface),
        'maximum_edge_error_mm':max(edges),'maximum_vertex_error_mm':vertices,
        'maximum_parameter_range_error':max(ranges),'maximum_face_area_error_mm2':max(areas),
        'volume_error_mm3':abs(a.Volume-b.Volume),'linear_tolerance_mm':1e-7}
    assert max(max(surface),max(edges),vertices,max(ranges))<1e-7,result
    assert max(areas)<1e-6 and result['volume_error_mm3']<1e-5,result
    return result
