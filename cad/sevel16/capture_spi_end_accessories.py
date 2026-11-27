"""Views of the loose thermostat, installed hose bands and coil-support shoulder."""
from build_spi_end_accessories import DEST, SOURCE
from capture_spi_cast_details import capture

THERMOSTAT = ("ThermostatHousing", "ThermostatBridge", "ThermostatElement",
              "ThermostatSeat", "ThermostatReturnSpring")
INSTALLED = (*THERMOSTAT, "ThermostatMainHose", "ThermostatBranchHose",
             "ThermostatMainClamp", "ThermostatBranchClamp")
VIEWS = (
    ("flange", THERMOSTAT, (350,0,34), (-1,-.05,.07), 137),
    ("mola", THERMOSTAT, (350,0,34), (-.54,-.12,.85), 134),
    ("mangueiras", INSTALLED, (367,0,30), (.78,-.28,.72), 204),
    ("bobina", ("IgnitionCoilMount",), (363,0,132), (.4,-.03,1), 138),
    ("bocal-bobina", ("IgnitionCoilMount", "IgnitionCoil", "ValveCover", "OilFillerCap"),
     (337,-2,162), (.3,-1,.64), 186),
)


def run():
    capture(SOURCE, "antes-v016", VIEWS)
    capture(DEST, "v016", VIEWS)
