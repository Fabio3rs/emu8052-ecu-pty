#pragma once

#include <array>
#include <limits>
#include <optional>

namespace lab::transmission {

// Fiat Tipo manual B.500.837, pages 20-21. Index zero is neutral.
inline constexpr std::array<double, 6> gear_ratios{
    0.0, 3.909, 2.238, 1.541, 1.156, 0.891};
inline constexpr double reverse_ratio = 3.909;
inline constexpr double final_drive_ratio = 63.0 / 16.0;
// Approximate rolling radius; the available Fiat manual does not specify a tire.
inline constexpr double reference_tire_radius_m = 0.29;

constexpr double overall_ratio(int gear) {
    return gear >= 1 && gear <= 5
               ? gear_ratios[static_cast<std::size_t>(gear)] * final_drive_ratio
               : 0.0;
}

// Ideal kinematic reference only; the simulation has no clutch coupling yet.
constexpr std::optional<double> wheel_rpm(double engine_rpm, int gear) {
    const double ratio = overall_ratio(gear);
    if (ratio <= 0.0 || !(engine_rpm >= 0.0 &&
                          engine_rpm <= std::numeric_limits<double>::max()))
        return std::nullopt;
    return engine_rpm / ratio;
}

// OES drivetrain kinematics: wheel angular speed times rolling circumference.
// This is an engaged-clutch reference, not a coupled vehicle state.
constexpr std::optional<double> ideal_speed_kmh(double engine_rpm, int gear,
                                                double tire_radius_m) {
    const auto rotation = wheel_rpm(engine_rpm, gear);
    if (!rotation || !(tire_radius_m > 0.0 &&
                       tire_radius_m <= std::numeric_limits<double>::max()))
        return std::nullopt;
    constexpr double pi = 3.14159265358979323846;
    const double speed = *rotation * (2.0 * pi * tire_radius_m) * 60.0 / 1000.0;
    return speed <= std::numeric_limits<double>::max()
               ? std::optional<double>{speed} : std::nullopt;
}

} // namespace lab::transmission
