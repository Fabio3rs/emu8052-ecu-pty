"""Surface membership and lossless material batching at known mechanical interfaces."""
import math
from pathlib import Path
import tempfile
import unittest
from config import load
from material_regions import classify
from mesh_obj import encode, decode


class MaterialRegionsTests(unittest.TestCase):
    def test_planes_and_bore_are_distinct_from_casting(self):
        params,frame = load()
        radius = params['dimensions']['cylinder_bore_diameter_mm']['value']/2
        x = frame['bore_circle_centers_mm'][0]['x']
        cases = [([(0,50,0),(10,50,0),(0,60,0)],'machined_surface'),
                 ([(x+radius,0,-20),(x+radius*math.cos(.1),radius*math.sin(.1),-20),
                   (x+radius,0,-30)],'machined_surface'),
                 ([(0,73,-20),(10,73,-20),(0,73,-30)],'cast_surface'),
                 ([(0,50,-.001),(10,50,-.001),(0,60,-.001)],'cast_surface')]
        for vertices,expected in cases:
            self.assertEqual(classify('Block',vertices,[(0,1,2)],params,frame),[expected])

    def test_sloped_carrier_interface_uses_parameter_plane(self):
        params,frame = load()
        base = params['valvetrain_layout_estimated']['value']['carrier_base_z_mm']
        slope = math.tan(math.radians(params['carrier_section_estimated']['value']['base_slope_y_deg']))
        vertices = [(x,y,base+y*slope) for x,y in ((0,-20),(10,-20),(0,20))]
        self.assertEqual(classify('CamCarrier',vertices,[(0,1,2)],params,frame),['machined_surface'])
        displaced = [(x,y,z+.01) for x,y,z in vertices]
        self.assertEqual(classify('CamCarrier',displaced,[(0,1,2)],params,frame),['cast_surface'])

    def test_material_partition_preserves_vertices_triangles_and_normals(self):
        vertices = [(0,0,0),(10,0,0),(0,10,0),(10,10,0)]
        triangles = [(0,1,2),(1,3,2)]
        plain,_,_ = encode(vertices,triangles)
        colored,_,batches = encode(vertices,triangles,['machined_surface','cast_surface'])
        self.assertEqual(len(batches),2)
        with tempfile.TemporaryDirectory() as folder:
            a,b = Path(folder)/'plain.obj',Path(folder)/'colored.obj'
            a.write_bytes(plain); b.write_bytes(colored)
            ap,at,_ = decode(a)
            bp,bt,sizes = decode(b)
        self.assertEqual(ap,bp)
        self.assertEqual(sorted(at),sorted(bt))
        self.assertEqual(set(sizes),set(batches))
        with self.assertRaises(ValueError):
            encode(vertices,triangles,['machined_surface'])


if __name__=='__main__':
    unittest.main()
