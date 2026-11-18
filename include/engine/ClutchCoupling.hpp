#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace engine {

struct ClutchTransfer {
    // Apply these equal/opposite angular impulses once to the free shaft
    // velocities (after external forces); do not apply them again as torque.
    double crank_impulse_nm_s = 0.0;
    double vehicle_impulse_nm_s = 0.0;
    double dissipated_energy_j = 0.0;
};

// Scalar adaptation of OES ClutchConstraint's (-1,+1) angular Jacobian
// and Transmission::update's +/- maxTorque * pressure bounds. Solves the
// isolated two-inertia constraint analytically instead of importing its
// general rigid-body solver. Vehicle quantities are reflected to the clutch.
inline ClutchTransfer solve_clutch_transfer(
    double crank_speed_rad_s, double vehicle_speed_rad_s,
    double crank_inertia_kg_m2, double vehicle_inertia_kg_m2,
    double max_torque_nm, double pressure, double dt_s) {
    if (!std::isfinite(crank_speed_rad_s) ||
        !std::isfinite(vehicle_speed_rad_s) ||
        !std::isfinite(crank_inertia_kg_m2) || crank_inertia_kg_m2 <= 0.0 ||
        !std::isfinite(vehicle_inertia_kg_m2) || vehicle_inertia_kg_m2 <= 0.0 ||
        !std::isfinite(max_torque_nm) || max_torque_nm < 0.0 ||
        !std::isfinite(pressure) || pressure < 0.0 || pressure > 1.0 ||
        !std::isfinite(dt_s) || dt_s <= 0.0)
        throw std::invalid_argument("invalid clutch state");
    if (pressure == 0.0 || max_torque_nm == 0.0)
        return {};
    const double inverse_inertia =
        1.0 / crank_inertia_kg_m2 + 1.0 / vehicle_inertia_kg_m2;
    const double slip = crank_speed_rad_s - vehicle_speed_rad_s;
    const double limit = max_torque_nm * pressure * dt_s;
    if (!std::isfinite(inverse_inertia) || inverse_inertia <= 0.0 ||
        !std::isfinite(slip) || !std::isfinite(limit))
        throw std::invalid_argument("clutch state exceeds numeric range");
    const double impulse = std::clamp(slip / inverse_inertia, -limit, limit);
    const double heat = impulse * (slip - 0.5 * impulse * inverse_inertia);
    if (!std::isfinite(heat))
        throw std::invalid_argument("clutch energy exceeds numeric range");
    return {-impulse, impulse, std::max(0.0, heat)};
}

} // namespace engine
