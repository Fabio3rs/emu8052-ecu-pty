"""Static inspection of exported OBJ regions; not a replacement for the CAD viewport."""
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


def run(folder):
    folder = Path(folder)
    target = folder/'material_regions.png'
    version = 2
    while target.exists():
        target = folder/f'material_regions_v{version:03d}.png'
        version += 1
    manifest = json.loads((folder/'parts_manifest.json').read_text())
    fig = plt.figure(figsize=(16,10))
    light = np.array([-.4,-.5,1.])
    light /= np.linalg.norm(light)
    names = ('Block','HeadLower','CamCarrier')
    labels = ('Bloco','Cabeçote inferior','Gaiola do comando')
    for column,(name,label) in enumerate(zip(names,labels)):
        part = next(p for p in manifest['parts'] if p['source_object']==name)
        vertices,triangles,colors = [],[],[]
        batch = None
        for line in (folder/part['mesh_file']).read_text().splitlines():
            fields = line.split()
            if not fields:
                continue
            if fields[0]=='v':
                x,y,z = map(float,fields[1:])
                vertices.append((1000*x,-1000*z,1000*y))
            elif fields[0]=='o':
                batch = fields[1]
            elif fields[0]=='f':
                triangles.append([int(f.split('/')[0])-1 for f in fields[1:]])
                material = manifest['materials'][part['material_bindings'][batch]]
                colors.append(material['rgb'])
        points = np.asarray(vertices)
        facets = points[np.asarray(triangles)]
        normals = np.cross(facets[:,1]-facets[:,0],facets[:,2]-facets[:,0])
        normals /= np.linalg.norm(normals,axis=1)[:,None]
        lit = np.asarray(colors)*(.45+.55*np.maximum(0,normals@light))[:,None]
        lo,hi = points.min(axis=0),points.max(axis=0)
        for row,azimuth in enumerate((-60,60)):
            ax = fig.add_subplot(2,3,row*3+column+1,projection='3d')
            az,el = np.radians([azimuth,30])
            toward_camera = np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
            facing = normals@toward_camera>0
            ax.add_collection3d(Poly3DCollection(facets[facing],facecolors=lit[facing],
                                                edgecolors='none',antialiased=False))
            ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),zlim=(lo[2],hi[2]))
            ax.set_box_aspect(hi-lo)
            ax.view_init(elev=30,azim=azimuth)
            ax.set_axis_off()
            ax.set_title(label+' — '+('-Y' if row==0 else '+Y'))
    fig.suptitle('OBJ exportado: interfaces usinadas claras, demais superfícies da fundição em cinza',fontsize=14)
    fig.text(.5,.02,'Malhas locais isoladas; iluminação apenas para leitura. Geometria e regiões provisórias.',ha='center')
    fig.tight_layout(rect=(0,.04,1,.95))
    fig.savefig(target,dpi=125)
    plt.close(fig)
    print(target)
    return target


if __name__=='__main__':
    run(sys.argv[1])
