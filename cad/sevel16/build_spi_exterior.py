"""Rebuild the v014 SPI exterior from the reviewed v012, in the FreeCAD GUI."""
from pathlib import Path
from tempfile import TemporaryDirectory

import build_breather_profile
import build_core_plug_wall
import build_pan_side_press
import build_spark_buttresses
import build_spi_filler
from config import OUTPUT

SOURCE = OUTPUT / "models/SEVEL_Accessories_A5_v012_IntakeWall.FCStd"
DEST = OUTPUT / "models/SEVEL_Accessories_A5_v014_SPIExterior.FCStd"


def run(source=SOURCE, destination=DEST):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    with TemporaryDirectory(dir=destination.parent) as folder:
        previous = source
        for builder in (build_core_plug_wall, build_spark_buttresses,
                        build_spi_filler, build_pan_side_press):
            stage = Path(folder) / (builder.__name__ + ".FCStd")
            builder.run(previous, stage)
            previous = stage
        build_breather_profile.run(previous, destination)
    return destination
