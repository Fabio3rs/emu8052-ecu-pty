"""Standalone evidence plot; not a CAD or collision proof."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from config import load, OUTPUT
from kinematics import pose


def run():
    params,frame = load()
    angles = list(range(721))
    states = [pose(theta,params,frame) for theta in angles]
    fig,axes = plt.subplots(3,1,figsize=(10,8),sharex=True,constrained_layout=True)
    for i,label in [(0,'Pistões 1 e 4'),(1,'Pistões 2 e 3')]:
        axes[0].plot(angles,[s['cylinders'][i]['crown_z_mm'] for s in states],label=label)
    axes[0].set_ylabel('Coroa: Z (mm)')
    axes[0].legend()
    for kind,label in [('intake','Admissão'),('exhaust','Escape')]:
        axes[1].plot(angles,[s['cylinders'][0]['valve_lifts_mm'][kind] for s in states],label=label)
    for angle in [143,353,365,575]:
        axes[1].axvline(angle,color='gray',alpha=0.35,linestyle=':')
    axes[1].set_ylabel('Válvulas C1 (mm)')
    axes[1].legend()
    axes[2].plot(angles,[a/2 for a in angles],color='#6b4ca0')
    axes[2].set_ylabel('Comando (graus)')
    axes[2].set_xlabel('Virabrequim (graus); 0° = PMS de compressão C1')
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.set_xticks(range(0,721,90))
    fig.suptitle('SEVEL 1.6 i.e. 82 cv — cinemática analítica de 720°\n'
                 'Curso 67,4 mm; biela estimada 127 mm; levantamento de came sintético',fontsize=12)
    path = OUTPUT/'evidence/analytic_cycle_720.png'
    fig.savefig(path,dpi=160)
    plt.close(fig)
    print(path)


if __name__=='__main__':
    run()
