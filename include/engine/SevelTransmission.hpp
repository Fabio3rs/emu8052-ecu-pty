#pragma once

#include <array>
#include <limits>
#include <optional>

namespace engine::transmission {

// Fiat Tipo manual B.500.837, pages 20-21. Index zero is neutral.
inline constexpr std::array<double, 6> gear_ratios{0.0,   3.909, 2.238,
                                                   1.541, 1.156, 0.891};
inline constexpr double reverse_ratio = 3.909;
inline constexpr double final_drive_ratio = 63.0 / 16.0;
// Approximate rolling radius; the available Fiat manual does not specify a
// tire.
inline constexpr double reference_tire_radius_m = 0.29;

constexpr double overall_ratio(int gear) {
    // SEVEL convention: -1 reverse, 0 neutral, 1..5 forward.
    if (gear == -1)
        return -reverse_ratio * final_drive_ratio;
    return gear >= 1 && gear <= 5
               ? gear_ratios[static_cast<std::size_t>(gear)] * final_drive_ratio
               : 0.0;
}

// Ideal kinematic reference only (no slip). The coupled vehicle state lives in
// Drivetrain/ClutchCoupling; this helper is the engaged-clutch limit.
constexpr std::optional<double> wheel_rpm(double engine_rpm, int gear) {
    const double ratio = overall_ratio(gear);
    if (ratio == 0.0 || !(engine_rpm >= 0.0 &&
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
    return speed >= -std::numeric_limits<double>::max() &&
                   speed <= std::numeric_limits<double>::max()
               ? std::optional<double>{speed}
               : std::nullopt;
}

// OES Transmission::changeGear: f = tire_radius / (diff_ratio * gear_ratio),
// new_I = m_car * f * f. No connected vehicle inertia exists in neutral.
constexpr std::optional<double>
reflected_inertia_kg_m2(double mass_kg, int gear, double tire_radius_m) {
    const double ratio = overall_ratio(gear);
    constexpr double max = std::numeric_limits<double>::max();
    if (ratio == 0.0 || !(mass_kg > 0.0 && mass_kg <= max) ||
        !(tire_radius_m > 0.0 && tire_radius_m <= max))
        return std::nullopt;
    const double f = tire_radius_m / ratio;
    const double inertia = mass_kg * f * f;
    return inertia > 0.0 && inertia <= max ? std::optional<double>{inertia}
                                           : std::nullopt;
}

// OES Vehicle::linearForceToVirtualTorque uses sqrt(I / mass) * force.
// For forward gears, substitution gives (radius / ratio) * force.
// Unlike the donor's unsigned sqrt, retain ratio direction for reverse.
// Signed force is retained: braking/back-driving must not become propulsion.
constexpr std::optional<double> reflected_torque_nm(double force_n, int gear,
                                                    double tire_radius_m) {
    const double ratio = overall_ratio(gear);
    constexpr double max = std::numeric_limits<double>::max();
    if (ratio == 0.0 || !(force_n >= -max && force_n <= max) ||
        !(tire_radius_m > 0.0 && tire_radius_m <= max))
        return std::nullopt;
    const double torque = (tire_radius_m / ratio) * force_n;
    return torque >= -max && torque <= max ? std::optional<double>{torque}
                                           : std::nullopt;
}

} // namespace engine::transmission
