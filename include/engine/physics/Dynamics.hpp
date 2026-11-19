#pragma once
// F-46..F-50 dynamics, dyno, clutch, vehicle. SI units.
#include "engine/physics/Geometry.hpp"

#include <algorithm>

namespace engine::physics {
inline double domega_dt(double j, double tau_comb, double tau_start, double t_f, double t_p,
                        double t_ac, double t_load, double t_clutch) { // F-46
    return (tau_comb + tau_start - t_f - t_p - t_ac - t_load - t_clutch) / j;
}
struct DynoPi {
    double kp = 2.0, ki = 8.0, t_max = 400.0; // t_max >= 160 N.m (F-47)
    double integral = 0.0;
};
// Conditional-integration anti-windup. e in rad/s.
inline double dyno_brake_nm(DynoPi &c, double omega_ref, double omega, double dt) {
    const double e = omega_ref - omega;
    // brake opposes the engine, so positive speed error (engine too fast) raises brake
    const double raw = -(c.kp * e + c.ki * (c.integral));
    const double out = std::clamp(raw, 0.0, c.t_max);
    const bool saturated_hi = raw > c.t_max && e < 0.0;
    const bool saturated_lo = raw < 0.0 && e > 0.0;
    if (!saturated_hi && !saturated_lo) c.integral += e * dt;
    return out;
}
inline double dyno_shaft_torque(double t_brake, double j, double domega_dt_v) {
    return t_brake + j * domega_dt_v;
}
inline double clutch_mean_radius_m(double ro, double ri) {
    return (2.0 / 3.0) * (ro * ro * ro - ri * ri * ri) / (ro * ro - ri * ri); // F-49
}
inline double clutch_torque_nm(double mu, double fn, int faces, double r_e) {
    return mu * fn * faces * r_e;
}
inline double vehicle_force_n(double m, double crr, double rho, double cda, double v,
                              double slope_rad, double g = 9.80665) { // F-50
    return m * g * crr + 0.5 * rho * cda * v * v + m * g * std::sin(slope_rad);
}
inline double vehicle_speed_ms(double omega_e, double r_dyn, double ig, double i_f) {
    return omega_e * r_dyn / (ig * i_f);
}
} // namespace engine::physics
