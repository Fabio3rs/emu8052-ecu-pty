#pragma once
// F-15..F-24 cylinder filling. SI units.
#include "engine/physics/Geometry.hpp"

#include <algorithm>

namespace engine::physics {
inline double cylinder_air_flow_kg_s(double eta_vm, double rho_m, double vd, double rpm) {
    return eta_vm * rho_m * vd * rpm / 120.0; // F-15
}
inline double ve_ambient(double m_cil_kg_s, double rho_ref_v, double vd, double rpm) {
    const double den = rho_ref_v * vd * rpm / 120.0; // F-16
    return den > 0.0 ? m_cil_kg_s / den : 0.0;
}
inline double ve_ambient_from_manifold(double eta_vm, double p_m, double p_ref, double t_m,
                                       double t_ref) {
    return eta_vm * (p_m / p_ref) * (t_ref / t_m); // F-17
}
inline double residual_correction(double p_e, double p_m, double r_c) { // F-18
    return 1.0 - (p_e / p_m - 1.0) / (gamma_air * (r_c - 1.0));
}
inline double residual_fraction(double p_e, double p_m, double r_c) { // F-19
    return (1.0 / r_c) * std::pow(p_e / p_m, 1.0 / gamma_air);
}
inline double mach_index(const EngineGeometry &g, double valve_d_m, double rpm, double ci,
                         double t_k) { // F-20
    const double b_dv = g.bore_m / valve_d_m;
    return b_dv * b_dv * mean_piston_speed(g, rpm) / (ci * sound_speed(t_k));
}
inline double f_z(double z, double z0, double kz) { // F-20
    return z <= z0 ? 1.0 : std::max(0.0, 1.0 - kz * (z - z0) * (z - z0));
}
inline double f_low(double rpm, double cb, double nb) { return 1.0 - cb * std::exp(-rpm / nb); } // F-21

struct VeCurveParams {
    // Manifold-referenced WOT curve, fitted by tools/fit_dyno_ve.py against the
    // sevel-dyno sweep (133 N.m @3000, 82 cv @6000, CEE x1.1 shape) with a
    // low-speed anchor eta_v(500 rpm) ~ 0.80 so the engine can start.
    // eta_max > 1 is ram/pulse tuning referred to manifold density.
    double eta_max = 1.2542;   // calibrado: alvo 131-133 N.m @3000
    double cb = 0.41777;       // calibrado: perda em baixa rotacao (IVC 35 deg ABDC, manual p.14)
    double nb = 3598.1;        // calibrado
    double valve_d_m = 0.0395; // manual B.500.837 p.11 (39,3-39,7)
    double ci = 0.35;          // estimativa de literatura (Taylor)
    double z0 = 0.29166;       // calibrado: queda de eta_v para 82 cv @6000
    double kz = 2.2073;        // calibrado
};
inline double eta_v_wot(const EngineGeometry &g, const VeCurveParams &v, double rpm,
                        double t_k) { // F-22
    const double z = mach_index(g, v.valve_d_m, rpm, v.ci, t_k);
    return v.eta_max * f_low(rpm, v.cb, v.nb) * f_z(z, v.z0, v.kz);
}
inline double curtain_area_m2(double valve_d_m, double lift_m) { return pi * valve_d_m * lift_m; } // F-23
inline double valve_mean_velocity(const EngineGeometry &g, double valve_d_m, double rpm) {
    const double r = g.bore_m / valve_d_m;
    return r * r * mean_piston_speed(g, rpm);
}
} // namespace engine::physics
