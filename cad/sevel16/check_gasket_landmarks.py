"""Register a deck photograph with the cylinder openings and asymmetric windows."""
import argparse
import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from config import OUTPUT, ROOT
from head_fixing_alignment import LANDMARKS


def run(new_photo):
    rows = LANDMARKS['666447']
    controls = np.float64(rows['cylinders']+rows['water_windows']+rows['opposite_end_slot'])
    # Original 1200×750 photo and a 2× crop (+60,+135) of the 500×500 photo.
    examples = [
        (next((ROOT/'PhotosMotor').glob('*666661*')),[(254,435),(503,439),(749,445),(989,445),
         (390,276),(863,292),(998,584)],[(298,275),(482,281),(779,288),(952,290)]),
        (new_photo,[(134,119),(264,127),(413,136),(578,145),(223,48),(499,53),(580,228)],
         [(179,46),(269,48),(442,50),(558,54)])]
    folder = OUTPUT/'reviews/head-v010'
    folder.mkdir(exist_ok=True,parents=True)
    fig,axes = plt.subplots(2,1,figsize=(10,7.6),layout='constrained')
    result = []
    for i,(path,xy,small) in enumerate(examples):
        xy,small = np.float64(xy),np.float64(small)
        if i==1:
            xy,small = xy/2+[60,135],small/2+[60,135]
        transform,_ = cv2.findHomography(controls,xy,method=0)
        def project(points):
            return cv2.perspectiveTransform(np.float64(points)[None,:,:],transform)[0]
        predicted = project(rows['small'])
        errors = np.linalg.norm(predicted-small,axis=1)
        result.append(dict(source=path.name,control_px=xy.tolist(),homography=transform.tolist(),
                           control_rms_px=float(np.mean((np.linalg.norm(project(controls)-xy,axis=1))**2)**.5),
                           observed_secondary_px=small.tolist(),secondary_residual_px=errors.tolist()))
        ax = axes[i]
        ax.imshow(Image.open(path))
        ax.scatter(*xy[:4].T,marker='+',s=90,c='white',label='Centros dos cilindros')
        ax.scatter(*xy[4:].T,marker='s',s=125,facecolors='none',edgecolors='#ffb534',
                   linewidths=2,label='Duas janelas e rasgo oposto')
        ax.scatter(*small.T,s=125,facecolors='none',edgecolors='#3aebf2',linewidths=2,
                   label='Furos pequenos observados')
        ax.scatter(*predicted.T,marker='+',s=100,c='#ff5292',label='Projeção da junta')
        ax.set(xlim=(65,1140) if i==0 else (65,418),ylim=(641,206) if i==0 else (267,140))
        ax.axis('off')
    axes[1].legend(loc='upper center',bbox_to_anchor=(.5,-.02),ncol=2)
    fig.savefig(folder/'junta-sobre-blocos.png',dpi=135,bbox_inches='tight')
    plt.close(fig)
    (folder/'registro-blocos.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_photo',type=Path)
    run(parser.parse_args().new_photo)
