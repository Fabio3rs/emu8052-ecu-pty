"""Portable, local-space OBJ with bounded 16-bit renderer batches."""
import hashlib
import math


def runtime_point(p):
    return (p[0]*0.001, p[2]*0.001, -p[1]*0.001)


def triangle_normal(a, b, c):
    u = tuple(b[i]-a[i] for i in range(3))
    v = tuple(c[i]-a[i] for i in range(3))
    n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    length = math.sqrt(sum(x*x for x in n))
    if length <= 1e-20:
        raise ValueError('Degenerate export triangle')
    return tuple(x/length for x in n)


def encode(vertices_mm, triangles, regions=None):
    """Convert once; shared geometry can be instanced with different poses/colors."""
    vertices = [runtime_point(p) for p in vertices_mm]
    lines = ['# SEVEL local vertices in meters; instance transforms in manifest\n']
    lines += ['v %.10g %.10g %.10g\n' % p for p in vertices]
    face_normals = [triangle_normal(*(vertices[i] for i in tri)) for tri in triangles]
    adjacent = [[] for _ in vertices]
    for face, tri in enumerate(triangles):
        for vertex in tri:
            adjacent[vertex].append(face)
    normals, corner_normals, normal_ids = [], [], {}
    # Smooth tessellated curved surfaces; preserve edges sharper than 30 degrees.
    for face, tri in enumerate(triangles):
        ids = []
        for vertex in tri:
            neighbors = [face_normals[j] for j in adjacent[vertex]
                         if sum(a*b for a,b in zip(face_normals[face],face_normals[j]))
                         > math.cos(math.pi/6)]
            vector = tuple(sum(n[k] for n in neighbors) for k in range(3))
            length = math.sqrt(sum(x*x for x in vector))
            normal = tuple(round(x/length,10) for x in vector)
            if normal not in normal_ids:
                normal_ids[normal] = len(normals)
                normals.append(normal)
            ids.append(normal_ids[normal])
        corner_normals.append(ids)
    lines += ['vn %.10g %.10g %.10g\n' % n for n in normals]
    if regions is not None:
        if len(regions)!=len(triangles) or any(r not in
                ('cast_surface','machined_surface','body_surface','section_surface') for r in regions):
            raise ValueError('One recognized material region is required per triangle')
        groups = {r:[] for r in sorted(set(regions))}
        for index,region in enumerate(regions):
            groups[region].append(index)
    else:
        groups = {'':list(range(len(triangles)))}
    batches = []
    # Flat normals can split every triangle corner into a distinct GPU vertex.
    for region,indices in groups.items():
        for offset in range(0,len(indices),20000):
            name = (region+'_' if region else '')+'batch_%03d' % len(batches)
            batches.append(name)
            lines.append('o '+name+'\n')
            for j in indices[offset:offset+20000]:
                lines.append('f '+' '.join(f'{i+1}//{n+1}' for i,n in
                                           zip(triangles[j],corner_normals[j]))+'\n')
    data = ''.join(lines).encode('ascii')
    return data, hashlib.sha256(data).hexdigest(), batches


def decode(path):
    """Independent file round trip used by export checks; only this OBJ subset."""
    points, normals, triangles = [], [], []
    batches = {}
    current = None
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields or fields[0].startswith('#'):
            continue
        kind, values = fields[0], fields[1:]
        if kind in ('v', 'vn'):
            target = points if kind=='v' else normals
            target.append(tuple(map(float, values)))
        elif kind=='o':
            current = values[0]
            batches[current] = set()
        elif kind=='f':
            assert current and len(values)==3
            pairs = [tuple(int(i)-1 for i in token.split('//')) for token in values]
            assert all(0<=p<len(points) and 0<=n<len(normals) for p,n in pairs)
            batches[current].update(pairs)
            tri = tuple(points[p] for p,n in pairs)
            expected = triangle_normal(*tri)
            assert all(sum(expected[i]*normals[n][i] for i in range(3))>math.cos(math.pi/6)-1e-6
                       for p,n in pairs)
            assert all(abs(sum(x*x for x in normals[n])-1)<1e-8 for p,n in pairs)
            triangles.append(tri)
    assert triangles and all(0<len(v)<=65536 for v in batches.values())
    assert all(math.isfinite(x) for p in points+normals for x in p)
    return points, triangles, {k:len(v) for k,v in batches.items()}
