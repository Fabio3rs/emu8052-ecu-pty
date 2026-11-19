#pragma once
// F-25..F-29 fuel properties, injector, film, evaporation. SI units.
#include "engine/physics/Gas.hpp"

#include <algorithm>

namespace engine::physics {
struct FuelProps { double w_e, afr_st, pci_j_kg, hfg_j_kg; };
inline FuelProps fuel_props(double phi) { // F-25; densities 740/789: estimativa de literatura
    const double rg = 740.0, re = 789.0;
    const double we = phi * re / (phi * re + (1.0 - phi) * rg);
    return {we, (1.0 - we) * 14.7 + we * 9.0, ((1.0 - we) * 44.0 + we * 26.8) * 1e6,
            ((1.0 - we) * 350e3 + we * 900e3)};
}
inline double lambda_of(double m_air, double m_fuel, double afr_st) { // F-26
    return m_air / (m_fuel * afr_st);
}
inline double injector_flow_kg_s(double rho_f, double q_ref_m3_s, double dp, double dp_ref) {
    return rho_f * q_ref_m3_s * std::sqrt(dp / dp_ref); // F-27
}
inline double injector_dead_time_s(double t0, double kd, double v_nom, double v) {
    return t0 + kd * (v_nom - v);
}
inline double injector_mass_kg(double flow, double pulse_s, double dead_s) {
    return flow * std::max(0.0, pulse_s - dead_s);
}
struct FilmStep { double film_kg, to_cyl_kg_s; };
// F-28: X fraction of injected flow goes to the film, film empties with tau.
inline FilmStep film_derivative(double x, double inj_kg_s, double film_kg, double tau) {
    return {x * inj_kg_s - film_kg / tau, (1.0 - x) * inj_kg_s + film_kg / tau};
}
inline double evap_cooling_k(double chi, double m_evap, double hfg, double m_air) { // F-29
    return chi * m_evap * hfg / (m_air * cp_air);
}
} // namespace engine::physics
