"""FreeCAD phase controls; rigid CAD motion plus constant-wire spring previews."""
import time
import FreeCAD as App
import FreeCADGui as Gui
import Mesh
from PySide import QtCore, QtGui
from assembly import apply_pose
from config import load
from valve_springs import mesh


class PhaseController(QtGui.QDialog):
    def __init__(self, doc):
        super().__init__(Gui.getMainWindow())
        self.doc = doc
        self.params,self.frame = load()
        self.initial_theta = doc.Phase.ThetaDeg
        self.springs = [o for o in doc.Objects if getattr(o,'MotionType','')=='spring']
        self.previews = []
        self.visibility = [o.Visibility for o in self.springs]
        self.setWindowTitle('SEVEL — ciclo de 720° (geometria provisória)')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(QtGui.QLabel('0° = PMS de compressão C1 · ordem 1–3–4–2'))
        self.angle = QtGui.QDoubleSpinBox()
        self.angle.setRange(0,720)
        self.angle.setDecimals(3)
        self.angle.setSuffix(' °')
        self.angle.setValue(self.initial_theta)
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0,7200)
        self.slider.setValue(round(self.initial_theta*10))
        self.play = QtGui.QPushButton('Reproduzir')
        self.play.setCheckable(True)
        self.status = QtGui.QLabel()
        for widget in (self.angle,self.slider,self.play,self.status):
            layout.addWidget(widget)
        for spring in self.springs:
            preview = doc.addObject('Mesh::Feature',spring.Name+'_AnimationPreview')
            preview.ViewObject.ShapeColor = spring.ViewObject.ShapeColor
            preview.Placement = App.Placement(spring.RestBase,App.Rotation())
            self.previews.append(preview)
            spring.Visibility = False
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)
        self.play.toggled.connect(self.toggle)
        self.angle.valueChanged.connect(self.set_phase)
        self.slider.valueChanged.connect(lambda value:self.set_phase(value/10))
        self.set_phase(self.initial_theta)

    def set_phase(self, theta):
        state = apply_pose(self.doc,theta,self.params,self.frame,update_springs=False)
        shapes = {}
        for spring,preview,visible in zip(self.springs,self.previews,self.visibility):
            lift = state['cylinders'][spring.CylinderId-1]['valve_lifts_mm'][spring.ValveKind]
            key = (spring.SpringKind,lift)
            if key not in shapes:
                vertices,triangles = mesh(self.params,*key)
                shapes[key] = Mesh.Mesh([[vertices[i] for i in face] for face in triangles])
            preview.Mesh = shapes[key]
            preview.Visibility = visible
        for widget,value in ((self.angle,theta),(self.slider,round(theta*10))):
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self.status.setText(' · '.join(f'C{c["cylinder"]}: {c["stroke_label"]}' for c in state['cylinders']))
        return state

    def toggle(self, playing):
        self.play.setText('Pausar' if playing else 'Reproduzir')
        self.last_tick = time.monotonic()
        self.timer.start() if playing else self.timer.stop()

    def tick(self):
        now = time.monotonic()
        theta = (self.doc.Phase.ThetaDeg+30*(now-self.last_tick))%720
        self.last_tick = now
        self.set_phase(theta)

    def closeEvent(self, event):
        self.timer.stop()
        for preview in self.previews:
            self.doc.removeObject(preview.Name)
        for spring,visible in zip(self.springs,self.visibility):
            spring.Visibility = visible
        apply_pose(self.doc,self.initial_theta,self.params,self.frame)
        super().closeEvent(event)


def show(doc):
    controller = PhaseController(doc)
    controller.show()
    return controller  # Keep this reference alive in the FreeCAD console.
