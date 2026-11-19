#pragma once
// F-30..F-39 work, efficiency, MBT, mean pressures, power. SI units.
#include "engine/physics/Geometry.hpp"

#include <algorithm>

namespace engine::physics {
inline double burned_fuel_kg(double m_comb, double m_air, double afr_st, double eta_comb) {
    return std::min(m_comb, m_air / afr_st) * eta_comb; // F-30
}
// F-32 smooth lambda factor g(lambda) on indicated work per kg of burnable fuel.
// Rich bump (torque per kg AIR peaks near 0.875, +4%), lean bump (efficiency per
// kg FUEL peaks near 1.10), cliff above ~1.5 (misfire; center 1.50, width 0.05). Normalised g(1) = 1.
// calibrado: alvos F-32 (propriedades), amplitudes de literatura (Heywood cap. 3/9).
inline double f_lambda_raw(double lam) {
    const double r = (lam - 0.875) / 0.07, l = (lam - 1.10) / 0.10;
    const double cliff = 1.0 / (1.0 + std::exp((lam - 1.50) / 0.05));
    return (1.0 + 0.055 * std::exp(-r * r) + 0.030 * std::exp(-l * l)) * cliff;
}
inline double f_lambda_fuel(double lam) { return f_lambda_raw(lam) / f_lambda_raw(1.0); }
inline double wiebe_fraction(double theta, double theta_s, double dtheta_b, double a = 5.0,
                             double m = 2.0) { // F-33
    if (theta <= theta_s) return 0.0;
    return 1.0 - std::exp(-a * std::pow((theta - theta_s) / dtheta_b, m + 1.0));
}
inline double mbt_deg(double dtheta_b_deg) { return 0.5175 * dtheta_b_deg - 8.0; } // F-33, APMS
inline double burn_duration_deg(double d0, double rpm, double n0, double kr, double xr, double g) {
    return d0 * std::pow(rpm / n0, 0.3) * (1.0 + kr * xr) * g;
}
inline double f_advance(double delta_deg, double ks = 3.5e-4) {
    return std::max(0.0, 1.0 - ks * delta_deg * delta_deg);
}
inline double f_dilution(double xr, double kdil, double xr0) {
    return 1.0 - kdil * std::max(0.0, xr - xr0); // F-34
}
inline double imep_pa(double w_i_j, double vd1) { return w_i_j / vd1; } // F-36
inline double indicated_torque_nm(double w_i_j, int nc) { return nc * w_i_j / (4.0 * pi); }
inline double bmep_pa(double t_b, double vd) { return 4.0 * pi * t_b / vd; }
inline double power_kw(double t_nm, double rpm) { return t_nm * rpm / 9549.3; } // F-37
inline double kw_to_cv(double kw) { return kw / 0.7355; }
inline double bsfc_g_kwh(double fuel_kg_s, double p_kw) { return p_kw > 0 ? fuel_kg_s * 3.6e6 / p_kw : 0.0; } // F-38
inline double brake_efficiency(double p_w, double fuel_kg_s, double pci) { return p_w / (fuel_kg_s * pci); }
inline double exhaust_temp_k(double t_charge_k, double q_exh_w, double m_total_kg_s, double cp_exh = 1150.0) {
    return t_charge_k + q_exh_w / (m_total_kg_s * cp_exh); // F-39
}
} // namespace engine::physics
