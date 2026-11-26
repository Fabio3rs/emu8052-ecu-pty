"""Pixel landmarks on the two gasket images, in a common viewing orientation."""
# Left to right with the two long coolant windows above the cylinder centerline.
# Pixel midpoints on the alpha mask of 666447 and on the white holes of image 4.
# The latter coordinates are after a 180-degree rotation of its 1495 x 521 crop.
LANDMARKS = {
    '666447': {
        'cylinders': [(139,166),(284,166),(437,166),(578,163)],
        'small': [(158,70),(268,68),(454,68),(562,68)],
        'water_windows': [(212,70),(508,70)],
        'opposite_end_slot': [(584,250)],
        'plug_side': [(77,94),(212,105),(361,103),(508,104),(638,92)],
        'opposite': [(66,252),(214,254),(361,254),(508,251),(648,248)]},
    'image4_rot180': {
        'cylinders': [(201,279),(497,275),(803,269),(1101,263)],
        'small': [(232,79),(459,78),(839,74),(1068,71)],
        'water_windows': [(345,84),(953,76)],
        'opposite_end_slot': [(1116,438)],
        'plug_side': [(68,133),(346,149),(649,147),(952,142),(1238,116)],
        'opposite': [(53,463),(352,457),(652,450),(952,442),(1256,438)]},
}


def register(rows, cylinder_x):
    """Scale and rotate from the two outside centers; keep inner residuals visible."""
    x0,y0 = rows['cylinders'][0]
    x3,y3 = rows['cylinders'][-1]
    dx,dy = x3-x0,y3-y0
    factor = (cylinder_x[-1]-cylinder_x[0])/(dx*dx+dy*dy)
    def project(pixel):
        x,y = pixel[0]-x0,pixel[1]-y0
        return (cylinder_x[0]+factor*(x*dx+y*dy),factor*(y*dx-x*dy))
    # The isolated opposite-edge slot lies near the toothed wheel in the block
    # photo. That end is -X in the assembly. Looking at the face from below
    # reverses its handedness compared with a top view of the block.
    result = {}
    for name,pixels in rows.items():
        result[name] = sorted((cylinder_x[0]+cylinder_x[-1]-x,y)
                              for x,y in map(project,pixels))
    return result


def lower_centers(cylinder_x):
    # Average the local offsets, then round to mm to reflect the photo precision.
    sets = [register(rows,cylinder_x) for rows in LANDMARKS.values()]
    centers = []
    for i,x in enumerate(cylinder_x):
        dx = sum(s['small'][i][0]-s['cylinders'][i][0] for s in sets)/len(sets)
        y = sum(s['small'][i][1] for s in sets)/len(sets)
        centers.append((x+round(dx),round(y)))
    return centers


def plot_review():
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from config import OUTPUT,layout,load

    p,f = load()
    stations = layout(p,f)
    xs = stations['centers']
    output = OUTPUT/'reviews/head-v010'
    output.mkdir(parents=True,exist_ok=True)
    fig,ax = plt.subplots(figsize=(12,5.4))
    for i,x in enumerate(xs,1):
        ax.add_patch(Circle((x,0),43.2,facecolor='0.96',edgecolor='0.75'))
        ax.text(x,0,f'C{i}',ha='center',va='center',color='0.35')
    for key,marker,color in [('666447','o','#096a77'),('image4_rot180','+','#bc5a02')]:
        rows = register(LANDMARKS[key],xs)
        points = rows['small']+rows['plug_side']+rows['opposite']
        ax.plot(*zip(*points),linestyle='',marker=marker,color=color,fillstyle='none',ms=10,
                label='Junta 666447' if key=='666447' else 'Junta com borda vermelha')
        landmarks = rows['water_windows']+rows['opposite_end_slot']
        ax.plot(*zip(*landmarks),linestyle='',marker='_',color=color,ms=21,mew=2)
    majors = [(x,y) for x in stations['supports'] for y in (-61,61)]
    ax.plot(*zip(*majors),'x',color='0.35',ms=8,label='10 eixos principais do CAD')
    old = [(x+dx,-69) for x,dx in zip(xs,(-22,22,-21,22))]
    new = lower_centers(xs)
    ax.plot(*zip(*old),'s',color='#952459',fillstyle='none',label='4 pequenos · v009')
    ax.plot(*zip(*new),'d',color='#263ada',ms=5,label='4 pequenos · v010')
    for a,b in zip(old,new):
        ax.annotate('',b,a,arrowprops={'arrowstyle':'->','color':'0.48','lw':.85})
    ax.set(aspect='equal',xlim=(-60,345),ylim=(-82,76),xlabel='X longitudinal do CAD (mm)',
           ylabel='Y transversal (mm)',title='Registro das juntas · traços horizontais indicam os centros das janelas de referência')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.21),ncol=3,frameon=False)
    fig.savefig(output/'registro-juntas.png',bbox_inches='tight',dpi=145)
    plt.close(fig)


if __name__=='__main__':
    plot_review()
