#pragma once

#include "lab/SevelValves.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <vector>

namespace lab {

// 4.5: the 0-720 degree cycle ruler under the two views. The cycle angle is the
// crank angle relative to the TDC reference, over two revolutions.
struct CycleSpan {
    double start_deg = 0.0;
    double end_deg = 0.0;
};

inline double cycle_angle_deg(double crank_angle_rad, double tdc_phase_rad) {
    double degrees = std::fmod((crank_angle_rad - tdc_phase_rad) *
                                   (180.0 / 3.14159265358979323846),
                               720.0);
    return degrees < 0.0 ? degrees + 720.0 : degrees;
}

// Where `kind`'s valve of cylinder `cylinder_index` is open in the 0..720 cycle:
// the same window valve_lift_fraction() uses, moved by the cylinder's firing
// offset and split in two when it wraps past 720.
inline std::vector<CycleSpan> valve_open_spans(std::size_t cylinder_index,
                                               ValveKind kind) {
    const double opening = kind == ValveKind::Intake ? 353.0 : 143.0;
    const double closing = kind == ValveKind::Intake ? 575.0 : 365.0;
    const double offset = firing_tdc_degrees.at(cylinder_index);
    double start = std::fmod(opening + offset, 720.0);
    const double length = closing - opening;
    if (start + length <= 720.0)
        return {{start, start + length}};
    return {{start, 720.0}, {0.0, start + length - 720.0}};
}

// Firing TDC of the cylinder on the ruler (where its spark belongs).
inline double firing_mark_deg(std::size_t cylinder_index) {
    return std::fmod(firing_tdc_degrees.at(cylinder_index), 720.0);
}

// Where the spark of cylinder `cylinder_index` falls on the ruler: its firing
// TDC minus the advance (degrees BTDC), wrapped into 0..720. Negative advance
// (retard) lands after the TDC. A non-finite advance has no position.
inline double spark_mark_deg(std::size_t cylinder_index, double advance_deg) {
    if (!std::isfinite(advance_deg))
        return std::nan("");
    double mark = std::fmod(firing_mark_deg(cylinder_index) - advance_deg, 720.0);
    return mark < 0.0 ? mark + 720.0 : mark;
}

} // namespace lab
