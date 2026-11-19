#include "engine/IntakeFuel.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace engine {
namespace {
constexpr double gas_constant_j_per_kg_k = 287.0;
constexpr double kelvin_offset = 273.15;
constexpr double pi = 3.14159265358979323846;
} // namespace

IntakeFuel::IntakeFuel(IntakeFuelParameters parameters)
    : parameters_(parameters),
      air_temperature_c_(parameters.ambient_temperature_c),
      initial_air_mass_kg_(
          parameters.ambient_pressure_pa * parameters.manifold_volume_m3 /
          (gas_constant_j_per_kg_k *
           (parameters.ambient_temperature_c + kelvin_offset))),
      air_mass_kg_(initial_air_mass_kg_),
      exhaust_pressure_pa_(parameters.exhaust_pressure_pa) {
    if (!(parameters.displacement_m3 > 0.0) ||
        !(parameters.manifold_volume_m3 > 0.0) ||
        !(parameters.ambient_pressure_pa > 0.0) ||
        !std::isfinite(parameters.ambient_temperature_c) ||
        parameters.ambient_temperature_c <= -kelvin_offset ||
        !(parameters.volumetric_efficiency > 0.0) ||
        parameters.volumetric_efficiency > 1.0 ||
        !(parameters.throttle_max_area_m2 > 0.0) ||
        !(parameters.throttle_leak_area_m2 >= 0.0) ||
        !(parameters.film_fraction >= 0.0) || parameters.film_fraction > 1.0)
        throw std::invalid_argument("invalid intake parameters");
}

double IntakeFuel::pressure_pa() const {
    return air_mass_kg_ * gas_constant_j_per_kg_k *
           (air_temperature_c_ + kelvin_offset) /
           parameters_.manifold_volume_m3;
}

double IntakeFuel::pumping_torque_nm() const {
    // F-40: PMEP = p_e - p_m (p_e = p_amb in the legacy plant).
    const double intake_pressure_drop_pa = std::max(
        0.0, (parameters_.exhaust_back_pressure_k > 0.0 ? exhaust_pressure_pa_
                                                        : parameters_.ambient_pressure_pa) -
                 pressure_pa());
    return intake_pressure_drop_pa * parameters_.displacement_m3 / (4.0 * pi);
}

IntakeStep IntakeFuel::step(double dt_s, double rpm, double angle_rad,
                            double air_temperature_c, double wall_temperature_c,
                            double injected_fuel_kg) {
    if (!std::isfinite(dt_s) || dt_s <= 0.0 || !std::isfinite(rpm) ||
        rpm < 0.0 || !std::isfinite(angle_rad) || angle_rad < 0.0 ||
        angle_rad > 1.5707963267948966 || !std::isfinite(air_temperature_c) ||
        air_temperature_c <= -kelvin_offset ||
        !std::isfinite(wall_temperature_c) ||
        !std::isfinite(injected_fuel_kg) || injected_fuel_kg < 0.0)
        throw std::invalid_argument("invalid intake input");

    const double old_air_mass_kg = air_mass_kg_;
    air_temperature_c_ = air_temperature_c;
    const double density_ambient =
        parameters_.ambient_pressure_pa /
        (gas_constant_j_per_kg_k *
         (parameters_.ambient_temperature_c + kelvin_offset));
    const double manifold_t_k = air_temperature_c + kelvin_offset;
    double throttle_flow_kg_s;
    const double manifold_density =
        old_air_mass_kg / parameters_.manifold_volume_m3;
    const double pressure_difference_pa =
        parameters_.ambient_pressure_pa - pressure_pa();
    if (parameters_.compressible_throttle) {
        const double plate_m2 = physics::throttle_area_m2(
            parameters_.throttle_bore_m, parameters_.throttle_shaft_ratio, angle_rad,
            0.0);
        const double area_eff_m2 =
            parameters_.throttle_leak_area_m2 +
            parameters_.throttle_discharge_cd * plate_m2;
        throttle_flow_kg_s = physics::orifice_flow_kg_s(
            area_eff_m2, parameters_.ambient_pressure_pa,
            parameters_.ambient_temperature_c + kelvin_offset, pressure_pa(),
            manifold_t_k);
    } else {
        const double area_m2 =
            parameters_.throttle_leak_area_m2 +
            parameters_.throttle_max_area_m2 * std::pow(std::sin(angle_rad), 2.0);
        const double source_density =
            pressure_difference_pa >= 0.0 ? density_ambient : manifold_density;
        throttle_flow_kg_s =
            std::copysign(area_m2 * std::sqrt(2.0 * source_density *
                                              std::abs(pressure_difference_pa)),
                          pressure_difference_pa);
    }
    double eta_vm = parameters_.volumetric_efficiency;
    if (parameters_.ve_map) {
        const double t_k = air_temperature_c + kelvin_offset;
        const double p_m = std::max(1000.0, pressure_pa());
        const double r_c = parameters_.geometry.compression_ratio;
        eta_vm = physics::eta_v_wot(parameters_.geometry, parameters_.ve_curve, rpm, t_k) *
                 physics::residual_correction(exhaust_pressure_pa_, p_m, r_c) /
                 physics::residual_correction(parameters_.exhaust_pressure_pa,
                                              parameters_.wot_manifold_pressure_pa, r_c);
        eta_vm = std::clamp(eta_vm, 0.0, 1.2);
    }
    const double air_out_kg_s = manifold_density * parameters_.displacement_m3 *
                                rpm / 120.0 * eta_vm;
    last_ve_manifold_ = eta_vm;
    last_ve_ambient_ =
        density_ambient > 0.0 && rpm > 0.0
            ? air_out_kg_s / (density_ambient * parameters_.displacement_m3 * rpm / 120.0)
            : 0.0;
    IntakeStep result;
    result.air_in_kg = std::max(-old_air_mass_kg, throttle_flow_kg_s * dt_s);
    result.air_to_cylinders_kg = std::min(old_air_mass_kg, air_out_kg_s * dt_s);
    if (result.air_in_kg < 0.0)
        result.air_in_kg = std::max(
            result.air_in_kg, result.air_to_cylinders_kg - old_air_mass_kg);
    air_mass_kg_ =
        old_air_mass_kg + result.air_in_kg - result.air_to_cylinders_kg;
    last_air_in_kg_s_ = result.air_in_kg / dt_s;
    last_air_cyl_kg_s_ = result.air_to_cylinders_kg / dt_s;
    if (parameters_.exhaust_back_pressure_k > 0.0) {
        const double m_exh = last_air_cyl_kg_s_ + result.fuel_to_cylinders_kg / dt_s;
        exhaust_pressure_pa_ = parameters_.exhaust_pressure_pa +
                               parameters_.exhaust_back_pressure_k * m_exh * m_exh;
    }
    air_in_total_kg_ += result.air_in_kg;
    air_delivered_total_kg_ += result.air_to_cylinders_kg;

    const double retained_kg = parameters_.film_fraction * injected_fuel_kg;
    fuel_film_kg_ += retained_kg;
    const double evaporation_tau_s =
        0.3 + 0.02 * std::max(0.0, 90.0 - wall_temperature_c);
    const double evaporated_kg =
        fuel_film_kg_ * (1.0 - std::exp(-dt_s / evaporation_tau_s));
    fuel_film_kg_ -= evaporated_kg;
    fuel_vapor_kg_ += injected_fuel_kg - retained_kg + evaporated_kg;
    const double consumed_fraction =
        old_air_mass_kg > 0.0 ? result.air_to_cylinders_kg / old_air_mass_kg
                              : 0.0;
    result.fuel_to_cylinders_kg = fuel_vapor_kg_ * consumed_fraction;
    fuel_vapor_kg_ -= result.fuel_to_cylinders_kg;
    injected_total_kg_ += injected_fuel_kg;
    fuel_delivered_total_kg_ += result.fuel_to_cylinders_kg;
    return result;
}

} // namespace engine
