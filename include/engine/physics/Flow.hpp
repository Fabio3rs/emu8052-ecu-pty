#pragma once
// F-10..F-14 throttle area, compressible orifice flow, filter, manifold.
#include "engine/physics/Gas.hpp"

#include <algorithm>

namespace engine::physics {
// F-10 Heywood throttle plate area. psi, psi0 [rad]; a_s = shaft/bore ratio.
inline double throttle_area_m2(double bore_d_m, double shaft_ratio, double psi,
                               double psi0) {
    const double a = shaft_ratio, c0 = std::cos(psi0);
    const double c = std::max(std::cos(psi), a * c0); // fully open: hold boundary value
    const double full = pi * bore_d_m * bore_d_m / 4.0;
    if (psi <= psi0) return 0.0;
    const double rad = std::max(0.0, c * c - a * a * c0 * c0);
    const double frac = (1.0 - c / c0) +
        (2.0 / pi) * (a / c * std::sqrt(rad) + c / c0 * std::asin(std::min(1.0, a * c0 / c)) -
                      a * std::sqrt(1.0 - a * a) + std::asin(a));
    return full * std::clamp(frac, 0.0, 1.0);
}

inline constexpr double pr_critical() { // F-11
    return 0.52828; // (2/(g+1))^(g/(g-1)) for g=1.4
}
inline double psi_flow(double pr) { // F-11 Psi(pr), pr = p_low/p_high
    constexpr double g = gamma_air;
    pr = std::clamp(pr, 0.0, 1.0);
    if (pr <= pr_critical())
        return std::sqrt(g) * std::pow(2.0 / (g + 1.0), (g + 1.0) / (2.0 * (g - 1.0)));
    return std::pow(pr, 1.0 / g) *
           std::sqrt(2.0 * g / (g - 1.0) * (1.0 - std::pow(pr, (g - 1.0) / g)));
}
// Regularisation threshold near pr -> 1 (dPsi/dpr -> infinity). Documented eps.
inline constexpr double flow_epsilon = 1e-3;
// Signed mass flow, positive from p_up to p_down.
inline double orifice_flow_kg_s(double a_eff_m2, double p_a, double t_a_k, double p_b,
                                double t_b_k) {
    const bool forward = p_a >= p_b;
    const double ph = forward ? p_a : p_b, pl = forward ? p_b : p_a;
    const double th = forward ? t_a_k : t_b_k;
    const double pr = pl / ph;
    double m;
    if (1.0 - pr < flow_epsilon) {
        // Linear branch, continuous at 1 - pr = eps: m = Psi(1-eps) A ph/sqrt(R T) * (1-pr)/eps.
        const double m_eps = psi_flow(1.0 - flow_epsilon) * a_eff_m2 * ph / std::sqrt(gas_r * th);
        m = m_eps * (1.0 - pr) / flow_epsilon;
    } else {
        m = a_eff_m2 * ph / std::sqrt(gas_r * th) * psi_flow(pr);
    }
    return forward ? m : -m;
}
inline double filter_pressure_drop_pa(double k_f, double m_dot, double rho_amb) { // F-12
    return k_f * m_dot * m_dot / rho_amb;
}
inline double manifold_pressure_pa(double mass_kg, double t_k, double volume_m3) { // F-13
    return mass_kg * gas_r * t_k / volume_m3;
}
inline double manifold_time_constant_s(double volume_m3, double eta_v, double vd_m3,
                                       double rpm) { // F-14
    return volume_m3 / (eta_v * vd_m3 * rpm / 120.0);
}
} // namespace engine::physics
