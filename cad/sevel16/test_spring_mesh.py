"""Runtime spring mesh: closed oriented surface and constant wire section."""
import math
import unittest
from collections import Counter
from config import load
from valve_springs import dimensions, mesh


class SpringMeshTests(unittest.TestCase):
    def test_compression_preserves_wire_and_closed_surface(self):
        params,_ = load()
        for kind in ('inner','outer'):
            for lift in (0,0.4,4.2,8.3,8.4):
                with self.subTest(kind=kind,lift=lift):
                    seat,height,radius,wire,turns = dimensions(params,kind,lift)
                    vertices,triangles = mesh(params,kind,lift)
                    count,sides = math.ceil(turns*48),12
                    for i in range(count+1):
                        a = 2*math.pi*turns*i/count
                        center = (radius*math.cos(a),radius*math.sin(a),
                                  seat+wire+(height-2*wire)*i/count)
                        for vertex in vertices[i*sides:(i+1)*sides]:
                            self.assertAlmostEqual(math.dist(vertex,center),wire,places=10)
                    edges = Counter()
                    volume = 0
                    for ids in triangles:
                        a,b,c = [vertices[i] for i in ids]
                        cross = (b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0])
                        volume += sum(a[k]*cross[k] for k in range(3))/6
                        for j in range(3):
                            edges[(ids[j],ids[(j+1)%3])] += 1
                    self.assertTrue(all(n==1 and edges[(b,a)]==1 for (a,b),n in edges.items()))
                    self.assertEqual(len(vertices)-len(edges)//2+len(triangles),2)
                    length = math.hypot(2*math.pi*turns*radius,height-2*wire)
                    self.assertGreater(volume,0)
                    self.assertLess(abs(volume/(math.pi*wire*wire*length)-1),0.06)
                    self.assertGreaterEqual(min(v[2] for v in vertices),seat-1e-9)
                    self.assertLessEqual(max(v[2] for v in vertices),seat+height+1e-9)


if __name__=='__main__':
    unittest.main()
