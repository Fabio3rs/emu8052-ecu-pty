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
// F-45 accessory load of the running engine: alternator + water pump.
struct AccessoryParams {
    double electrical_current_a = 20.0; // estimativa F-45 (ECU + bomba + injetor + bobina, 15-20 A)
    double alternator_efficiency = 0.55; // F-45 (0,5-0,6)
    double alternator_ratio = 2.0;       // estimativa: relacao de polias desconhecida
    double pump_nm_at_ref = 0.5;         // estimativa: bomba d'agua a rotacao de referencia
    double pump_ref_rad_s = 96.9;        // 925 rpm
    // Alternator starts charging at 1050-1150 alternator rpm (manual p.18); below
    // that the battery feeds the loads and the crank sees no electrical torque.
    // Ramp over crank 550..750 rpm (alternator_ratio 2.0 => ~1100..1500 rpm).
    double charge_start_rpm = 550.0;
    double charge_full_rpm = 750.0;
};
inline double accessory_torque_nm(const AccessoryParams &a, double v_sys, double omega) {
    if (omega <= 0.0) return 0.0;
    const double rpm = omega * 60.0 / (2.0 * pi);
    const double ramp = std::clamp(
        (rpm - a.charge_start_rpm) / (a.charge_full_rpm - a.charge_start_rpm), 0.0, 1.0);
    const double alt = ramp * v_sys * a.electrical_current_a /
                       (a.alternator_efficiency * a.alternator_ratio * omega);
    const double r = omega / a.pump_ref_rad_s;
    return alt + a.pump_nm_at_ref * r * r;
}
inline double alternator_torque_nm(double p_el_w, double eta, double omega_alt) { // F-45
    return p_el_w / (eta * omega_alt);
}
} // namespace engine::physics
