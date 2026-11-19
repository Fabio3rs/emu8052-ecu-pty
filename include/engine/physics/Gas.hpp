#pragma once
// F-01..F-03 gas constants and references. SI units. LLM-written (Claude).
#include <cmath>

namespace engine::physics {
inline constexpr double pi = 3.14159265358979323846;
inline constexpr double kelvin_offset = 273.15;
inline constexpr double gas_r = 287.05;   // J/(kg K), dry air, literatura
inline constexpr double gamma_air = 1.4;  // literatura
inline constexpr double cp_air = 1005.0;  // J/(kg K), literatura

inline double density(double p_pa, double t_k) { return p_pa / (gas_r * t_k); } // F-01
inline double sound_speed(double t_k) { return std::sqrt(gamma_air * gas_r * t_k); } // F-02
inline double rho_ref(double p_ref_pa, double t_ref_k) { return density(p_ref_pa, t_ref_k); } // F-03
} // namespace engine::physics
