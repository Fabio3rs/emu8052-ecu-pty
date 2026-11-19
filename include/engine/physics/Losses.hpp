#pragma once
// F-40..F-45 pumping, back pressure, friction, accessories. SI units.
#include "engine/physics/Geometry.hpp"

#include <algorithm>

namespace engine::physics {
inline double pumping_torque_nm(double p_e, double p_m, double vd) { // F-40 (signed)
    return (p_e - p_m) * vd / (4.0 * pi);
}
inline double exhaust_back_pressure_pa(double p_amb, double k_e, double m_esc) { // F-41
    return p_amb + k_e * m_esc * m_esc;
}
struct FrictionParams {
    // calibrado: 12,6-16 N.m na lenta e 25-35 N.m a 6000 (F-42 faixas), Chen-Flynn simplificado
    double c0_pa = 0.95e5;
    double c1_pa_per_ms = 0.060e5;
    double c2_pa_per_ms2 = 0.0035e5;
};
inline double fmep_pa(const FrictionParams &f, double sp) {
    return f.c0_pa + f.c1_pa_per_ms * sp + f.c2_pa_per_ms2 * sp * sp; // F-42
}
inline double friction_torque_nm(const FrictionParams &f, double sp, double vd) {
    return fmep_pa(f, sp) * vd / (4.0 * pi);
}
inline double walther_visc_cst(double a, double b, double t_k) { // F-43
    return std::pow(10.0, std::pow(10.0, a - b * std::log10(t_k))) - 0.7;
}
// Oil temperature effect on friction (F-43). Walther fit of a 20W50 oil on
// nu40 = 160 cSt and nu100 = 19 cSt (estimativa de literatura, conferir ficha).
struct OilFrictionParams {
    double nu40_cst = 160.0;      // estimativa de literatura
    double nu100_cst = 19.0;      // estimativa de literatura
    double hydrodynamic_share = 0.30; // estimativa: parcela hidrodinamica do atrito
    double exponent = 0.35;       // F-43: n = 0.3-0.5
    double reference_c = 90.0;    // atrito calibrado a quente
};
inline double oil_friction_scale(const OilFrictionParams &p, double oil_c) {
    auto w = [](double nu) { return std::log10(std::log10(nu + 0.7)); };
    const double b = (w(p.nu40_cst) - w(p.nu100_cst)) /
                     (std::log10(373.15) - std::log10(313.15));
    const double a = w(p.nu40_cst) + b * std::log10(313.15);
    const auto nu = [&](double c) {
        return std::pow(10.0, std::pow(10.0, a - b * std::log10(c + 273.15))) - 0.7;
    };
    const double ratio = std::pow(nu(oil_c) / nu(p.reference_c), p.exponent);
    return 1.0 + p.hydrodynamic_share * (ratio - 1.0);
}
inline double hydrodynamic_scale(double nu, double nu_ref, double n = 0.4) {
    return std::pow(nu / nu_ref, n);
}
inline double valvetrain_spring_force_n(double h_mm, double k_n_per_mm, double preload_n) {
    return preload_n + k_n_per_mm * h_mm; // F-44 helper
}
inline double alternator_torque_nm(double p_el_w, double eta, double omega_alt) { // F-45
    return p_el_w / (eta * omega_alt);
}
} // namespace engine::physics
