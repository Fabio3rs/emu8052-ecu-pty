"""Matched cameras for the accessory wall, flywheel foot and thermostat disc."""
from build_spi_skirt_review import DEST, DISC, SOURCE
from capture_spi_cast_details import capture
from capture_spi_end_accessories import THERMOSTAT
from sheet_spi_cast_details import run as sheet

VIEWS = (
    ("parede",("Block",),(140,-60,-105),(.06,-1,.25),360),
    ("pe",("Block",),(201,-76,-153),(.40,-1,.20),228),
    ("disco",(*THERMOSTAT,DISC),(350,0,34),(-.64,-.16,.77),135),
)


def run():
    capture(SOURCE,"antes-v018",VIEWS)
    capture(DEST,"v018",VIEWS)
    sheet([("parede","*_702072-*","Bloco · coluna larga do lado do filtro"),
           ("pe","*_722603-*","Saia · rebaixo protegido pela borda que desce ao pé do volante"),
           ("disco","*111038533*","Termostática · disco escuro em torno da cápsula acobreada")],"v017","v018")
