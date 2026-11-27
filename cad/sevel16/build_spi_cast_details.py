"""Rebuild the exposed SPI castings and removable intake fittings in FreeCAD."""
from pathlib import Path
import tempfile

import FreeCAD as App

from assembly import add_part
from breather_cast_shoulder import fitting
from build_core_plug_wall import run as build_wall
from build_manifold_review import verify
from build_spi_exterior import SOURCE as WALL_BASE, DEST as EXTERIOR_BASE
from config import OUTPUT, load
from core_plug_panels import cast_skin
from intake_external_fittings import fittings
from manifold_castings import exhaust
from manifold_intake_casting import intake

DEST = OUTPUT / "models/SEVEL_Accessories_A5_v015_SPICastDetails.FCStd"


def verify_mounts(doc, support, others=()):
    parts = [o for o in doc.Objects if hasattr(o, "Shape")]
    for name in (*support, *others):
        obj = doc.getObject(name)
        solid = obj.Shape
        assert solid.isValid() and len(solid.Solids) == 1 and solid.Solids[0].isClosed()
        if name in support:
            assert solid.distToShape(doc.getObject(support[name]).Shape)[0] < 1e-6, name
        for other in parts:
            if obj != other and solid.BoundBox.intersect(other.Shape.BoundBox):
                assert abs(solid.common(other.Shape).Volume) < 1e-5, (name, other.Name)


def run(source=EXTERIOR_BASE, destination=DEST):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    params, frame = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        original_count = sum(hasattr(o, "Shape") for o in doc.Objects)
        # The new panels replace the first wall study. All other items inherit
        # the v014 assembly, including the v014 cover, plug bays and pan.
        with tempfile.TemporaryDirectory(dir=destination.parent) as folder:
            stage = Path(folder) / "SEVEL_CorePanels.FCStd"
            build_wall(WALL_BASE, stage, cast_skin(params["core_plug_panels_estimated"]["value"]))
            block_doc = App.openDocument(str(stage))
            try:
                doc.Block.Shape = block_doc.Block.Shape.copy()
            finally:
                App.closeDocument(block_doc.Name)
        doc.PCVBreatherOutlet.Shape = fitting(params, frame)
        doc.IntakeManifold.Shape = intake(
            params, frame, front_sections=params["intake_front_casting_estimated"]["value"])[0]
        # The four separate M8 studs already exist in this assembly.
        doc.ExhaustManifold.Shape = exhaust(params, frame, cast_flanks=True)[0]
        additions = fittings(params, frame)
        for name, shape, color in additions:
            if doc.getObject(name) is not None:
                raise ValueError("Fitting already present: " + name)
            add_part(doc, name, shape, color=color)
        doc.Label = destination.stem
        doc.recompute()
        mounts = {"PCVBreatherOutlet": "Block", "IntakeManifoldHoseTail": "IntakeManifold",
                  "IntakeManifoldPlugBase": "IntakeManifold", "IntakeManifoldSocket": "IntakeManifoldPlugBase"}
        verify_mounts(doc, mounts)
        verify(doc, params, frame, expected_parts=original_count + len(additions))
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
    return destination
