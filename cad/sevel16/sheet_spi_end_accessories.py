"""Side-by-side evidence for the coil bracket and thermostat of the owner's SPI."""
from sheet_spi_cast_details import run

ROWS = [
    ("bobina", "suporte_bobina_bocal_oleo/*114251093*", "Suporte da bobina · ombro fundido e orelha superior"),
    ("flange", "*110758186*", "Termostática · ponte, elemento central e aberturas da flange"),
    ("mola", "*111038533*", "Termostática · mola, apoio e projeção da ponte na direção do cabeçote"),
    ("mangueiras", "*10-55-36*", "Carcaça instalada · abraçadeiras e saída das duas mangueiras"),
]


if __name__ == "__main__":
    run(ROWS, "v015", "v016")
