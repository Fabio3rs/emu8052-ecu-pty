#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace lab {

enum class ValveKind { Intake, Exhaust };

// Firing TDC offsets for the documented 1-3-4-2 sequence, indexed 1-2-3-4.
constexpr std::array<double, 4> firing_tdc_degrees{0.0, 540.0, 180.0, 360.0};

inline double valve_lift_fraction(double crank_angle_rad,
                                  std::size_t cylinder_index, ValveKind kind,
                                  double tdc_phase_rad = 0.0) {
    if (!std::isfinite(crank_angle_rad) || !std::isfinite(tdc_phase_rad) ||
        cylinder_index >= firing_tdc_degrees.size())
        throw std::invalid_argument("invalid SEVEL valve phase");
    constexpr double degrees_per_radian = 180.0 / 3.14159265358979323846;
    double phase =
        std::fmod((crank_angle_rad - tdc_phase_rad) * degrees_per_radian -
                      firing_tdc_degrees[cylinder_index],
                  720.0);
    if (phase < 0.0)
        phase += 720.0;
    // Manual: intake 7° BTDC to 35° ABDC; exhaust 37° BBDC to 5° ATDC.
    const double opening = kind == ValveKind::Intake ? 353.0 : 143.0;
    const double closing = kind == ValveKind::Intake ? 575.0 : 365.0;
    if (phase <= opening || phase >= closing)
        return 0.0;
    return std::sin(3.14159265358979323846 * (phase - opening) /
                    (closing - opening));
}

// Camshaft lobe angle for the valve, measured from "nose straight at the
// tappet" (0) and turning at HALF the crankshaft speed (SOHC, 2:1). The nose
// points at the tappet exactly at the middle of the lift, so the lobe a viewer
// sees agrees with valve_lift_fraction().
inline double valve_cam_angle_rad(double crank_angle_rad,
                                  std::size_t cylinder_index, ValveKind kind,
                                  double tdc_phase_rad = 0.0) {
    if (!std::isfinite(crank_angle_rad) || !std::isfinite(tdc_phase_rad) ||
        cylinder_index >= firing_tdc_degrees.size())
        throw std::invalid_argument("invalid SEVEL valve phase");
    constexpr double degrees_per_radian = 180.0 / 3.14159265358979323846;
    double phase =
        std::fmod((crank_angle_rad - tdc_phase_rad) * degrees_per_radian -
                      firing_tdc_degrees[cylinder_index],
                  720.0);
    if (phase < 0.0)
        phase += 720.0;
    const double middle = kind == ValveKind::Intake ? 464.0 : 254.0;
    double cam_degrees = std::fmod((phase - middle) * 0.5, 360.0);
    if (cam_degrees < 0.0)
        cam_degrees += 360.0;
    return cam_degrees / degrees_per_radian;
}

} // namespace lab
