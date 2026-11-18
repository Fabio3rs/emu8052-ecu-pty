#pragma once

#include "ma17/EmulatorSnapshot.hpp"

#include <cmath>
#include <ostream>

namespace lab {

inline void write_drivetrain_csv_header(std::ostream &out) {
    out << ",drivetrain_available,physical_vehicle_speed_kmh,transmission_gear"
           ",clutch_pressure_fraction,clutch_crank_torque_Nm,clutch_heat_J";
}

inline void write_drivetrain_csv_row(std::ostream &out,
                                     const ma17::EmulatorSnapshot &sample) {
    out << ',' << (sample.drivetrain_available ? 1 : 0);
    if (!sample.drivetrain_available) {
        out << ",,,,,";
        return;
    }
    out << ',';
    if (sample.vehicle_speed_available && std::isfinite(sample.vehicle_speed_kmh))
        out << sample.vehicle_speed_kmh;
    out << ',';
    if (sample.transmission_gear >= -1 && sample.transmission_gear <= 5)
        out << sample.transmission_gear;
    out << ',';
    if (std::isfinite(sample.clutch_pressure) &&
        sample.clutch_pressure >= 0.0 && sample.clutch_pressure <= 1.0)
        out << sample.clutch_pressure;
    out << ',';
    if (std::isfinite(sample.clutch_crank_torque_nm))
        out << sample.clutch_crank_torque_nm;
    out << ',';
    if (std::isfinite(sample.clutch_heat_j) && sample.clutch_heat_j >= 0.0)
        out << sample.clutch_heat_j;
}

} // namespace lab
