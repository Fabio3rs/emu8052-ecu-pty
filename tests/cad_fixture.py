"""Small closed solids in runtime metres. The exporter supplies ordinary v1 OBJ batches."""
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cad/sevel16'))
from mesh_obj import encode


def extrude(points, faces, loops):
    n = len(points)
    vertices = [(x,y,z) for z in (-.045,.045) for x,y in points]
    triangles = [tuple(reversed(f)) for f in faces]+[tuple(i+n for i in f) for f in faces]
    for loop in loops:
        for i,j in zip(loop,loop[1:]+loop[:1]):
            triangles.extend(((i,j,j+n),(i,j+n,i+n)))
    return vertices,triangles


def solids():
    square = [(-.05,-.05),(.05,-.05),(.05,.05),(-.05,.05)]
    cube = extrude(square,[(0,1,2),(0,2,3)],[[0,1,2,3]])
    ring = [(.055*math.cos(i*math.tau/48),.055*math.sin(i*math.tau/48)) for i in range(48)]
    circle = list(range(48))
    cyl = extrude(ring,[(0,i,i+1) for i in range(1,47)],[circle])
    points = ring+[(.46*x,.46*y) for x,y in ring]
    faces = []
    for i in circle:
        j = (i+1)%48
        faces.extend(((i,j,j+48),(i,j+48,i+48)))
    tube = extrude(points,faces,[circle,list(range(95,47,-1))])
    ell = [(-.05,-.05),(.05,-.05),(.05,-.015),(-.015,-.015),(-.015,.05),(-.05,.05)]
    concave = extrude(ell,[(0,1,2),(0,2,3),(0,3,4),(0,4,5)],[[0,1,2,3,4,5]])
    return cube,cyl,tube,concave


def package(folder):
    folder.mkdir(parents=True,exist_ok=True)
    material = {'rgb':[.3,.66,.8],'opacity':1,'physical_material_verified':False}
    manifest = dict(schema='sevel.parts.v1',theta_zero='C1 compression TDC',theta_deg=0,
                    units={'length':'m','angle':'rad','time':'s'},parts=[],meshes={},
                    compression_tdc_deg=[0,540,180,360],conversion_owner='cad/sevel16/export_meshes.py',
                    reference_status='PASS_PROVISIONAL_FOR_VISUAL_ONLY',
                    root={'id':'engine_root','parent_id':None,'translation_m':[0,0,0],'rotation_xyzw':[0,0,0,1]},
                    generator={'datum_sha256':'a'*64},materials={'fixture':material})
    cube,cyl,tube,concave = solids()
    for name,(vertices,triangles),pos in [('cube',cube,[-.14,.075,0]),('cylinder',cyl,[0,.075,0]),
                                        ('tube',tube,[.14,.075,0]),('concave',concave,[-.14,-.075,0]),
                                        ('left',cube,[0,-.075,0]),('right',cube,[.1,-.075,0])]:
        data,sha,batches = encode([(1000*x,-1000*z,1000*y) for x,y,z in vertices],triangles)
        key = 'mesh_'+sha[:20]
        filename = key+'.obj'
        (folder/filename).write_bytes(data)
        manifest['meshes'][key] = dict(file=filename,sha256=sha,batches=batches,
                                       vertices=len(vertices),triangles=len(triangles))
        manifest['parts'].append(dict(id=name,source_object=name,display_label=name,parent_id='engine_root',
            mesh_id=key,mesh_file=filename,mesh_batches=batches,pivot_local_m=[0,0,0],
            rest_translation_m=pos,rest_rotation_xyzw=[0,0,0,1],rest_scale=[1,1,1],scene_group='fixture',
            cylinder_id=None,motion_type='fixed',angular_ratio_to_crank=None,valve_kind=None,spring_kind=None,
            material_bindings={b:'fixture' for b in batches},evidence_refs=['synthetic geometry']))
    (folder/'parts_manifest.json').write_text(json.dumps(manifest))
    return manifest


def moving_cube(folder):
    manifest = package(folder)
    cube = manifest['parts'][0]
    cube.update(motion_type='piston',cylinder_id=1)
    springs = dict(retainer_bottom_z_mm=50)
    for kind in ['inner','outer']:
        springs.update({kind+'_spring_seat_z_mm':0,kind+'_spring_wire_radius_mm':1,
                        kind+'_spring_turns':5})
    valves = dict(cam_height_mm=5,checking_lash_mm=.2,intake_events_deg=[300,550],
                  exhaust_events_deg=[100,360],intake_lash_mm=.4,exhaust_lash_mm=.5)
    manifest['runtime'] = dict(schema_version=1,rig=dict(radius_m=.05,rod_m=.15,
        compression_tdc_deg=manifest['compression_tdc_deg'],cam_phase_deg=0,valves=valves,
        springs=springs,pitch_mm=9,crank_teeth=20,
        belt_segments=[dict(kind='line',points=[[i,0],[i+1,0]]) for i in range(8)]))
    (folder/'parts_manifest.json').write_text(json.dumps(manifest))
