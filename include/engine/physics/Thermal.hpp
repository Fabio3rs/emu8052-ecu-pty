#pragma once
// F-51..F-57 intake heating, cooling, exhaust sensor, battery. SI units.
#include "engine/physics/Gas.hpp"

#include <algorithm>

namespace engine::physics {
inline double intake_heat_effectiveness(double ha_w_k, double m_air) { // F-51
    return 1.0 - std::exp(-ha_w_k / (m_air * cp_air));
}
inline double manifold_air_temp_c(double t_amb, double eps, double t_wall, double dt_evap) {
    return t_amb + eps * (t_wall - t_amb) - dt_evap;
}
// F-52 manual B.500.837 p.17 (centros das faixas).
inline double thermostat_opening(double t_c, double t_start = 87.0, double t_full = 98.0) {
    return std::clamp((t_c - t_start) / (t_full - t_start), 0.0, 1.0);
}
inline bool fan_state(bool on, double t_c, double t_on = 92.0, double t_off = 87.0) {
    if (t_c >= t_on) return true;
    if (t_c <= t_off) return false;
    return on;
}
inline double exhaust_transport_delay_s(double v_pipe, double m_esc, double r, double t_esc,
                                        double p_e, double tau_sensor) { // F-54
    return v_pipe / (m_esc * r * t_esc / p_e) + tau_sensor;
}
inline double narrow_o2_volts(double lam, double v_lo = 0.08, double v_hi = 0.85,
                              double k = 80.0) { // F-55
    return v_lo + (v_hi - v_lo) / (1.0 + std::exp(k * (lam - 1.0)));
}
inline double battery_voltage(double e_oc, double i, double r_int = 0.021) { // F-56
    return e_oc - i * r_int;
}
inline double injector_current_derivative(double v, double i, double r, double l) {
    return (v - i * r) / l; // F-57
}
} // namespace engine::physics
