#include "ecu_hw/Ma17InjectorStage.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace ecu_hw {

Ma17InjectorStage::Ma17InjectorStage(InjectorStageParameters parameters)
    : parameters_(parameters) {
    if (!std::isfinite(parameters.rated_flow_m3_s) ||
        parameters.rated_flow_m3_s <= 0.0 ||
        !std::isfinite(parameters.rated_delta_pa) ||
        parameters.rated_delta_pa <= 0.0 ||
        !std::isfinite(parameters.fuel_density_kg_m3) ||
        parameters.fuel_density_kg_m3 <= 0.0 ||
        !std::isfinite(parameters.rail_absolute_pa) ||
        parameters.rail_absolute_pa <= parameters.outlet_absolute_pa ||
        !std::isfinite(parameters.outlet_absolute_pa) ||
        parameters.outlet_absolute_pa <= 0.0 ||
        !std::isfinite(parameters.dead_time_s) ||
        parameters.dead_time_s < 0.0 ||
        !std::isfinite(parameters.nominal_battery_v) ||
        parameters.nominal_battery_v <= 0.0 ||
        !std::isfinite(parameters.coil_resistance_ohm) ||
        parameters.coil_resistance_ohm <= 0.0 ||
        !std::isfinite(parameters.ballast_resistance_ohm) ||
        parameters.ballast_resistance_ohm < 0.0 ||
        !std::isfinite(parameters.coil_inductance_h) ||
        parameters.coil_inductance_h <= 0.0 ||
        !std::isfinite(parameters.pull_in_current_a) ||
        parameters.pull_in_current_a <= 0.0)
        throw std::invalid_argument("invalid injector stage parameters");
    const double delta_pa =
        parameters_.rail_absolute_pa - parameters_.outlet_absolute_pa;
    rated_mass_flow_kg_s_ =
        parameters_.rated_flow_m3_s * parameters_.fuel_density_kg_m3 *
        std::sqrt(delta_pa / parameters_.rated_delta_pa);
}

double Ma17InjectorStage::step(bool cc3_pin_high, double dt_s,
                               double battery_v) {
    if (!std::isfinite(dt_s) || dt_s <= 0.0 || !std::isfinite(battery_v) ||
        battery_v < 0.0)
        throw std::invalid_argument("invalid injector stage input");
    const bool commanded =
        parameters_.active_low ? !cc3_pin_high : cc3_pin_high;
    const bool active = commanded && connected_ && battery_v >= 6.0;
    if (!active) {
        energized_ = false;
        energized_time_s_ = 0.0;
        coil_current_a_ = 0.0;
        return 0.0;
    }
    if (!energized_) {
        energized_ = true;
        energized_time_s_ = 0.0;
        coil_current_a_ = 0.0;
        ++pulse_count_;
    }
    ++energized_ticks_;
    const double resistance_ohm = parameters_.coil_resistance_ohm +
                                  parameters_.ballast_resistance_ohm;
    if (std::abs(dt_s - cached_dt_s_) > 1e-15) {
        cached_dt_s_ = dt_s;
        current_rise_fraction_ =
            -std::expm1(-dt_s * resistance_ohm /
                        parameters_.coil_inductance_h);
    }
    coil_current_a_ +=
        (battery_v / resistance_ohm - coil_current_a_) *
        current_rise_fraction_;
    const double dead_time_s =
        parameters_.dead_time_s * parameters_.nominal_battery_v / battery_v;
    const double prior_flowing_s =
        std::max(0.0, energized_time_s_ - dead_time_s);
    energized_time_s_ += dt_s;
    const double hydraulic_flowing_s =
        std::max(0.0, energized_time_s_ - dead_time_s) - prior_flowing_s;
    // A short low-voltage pulse may pass dead time without opening the injector.
    // Um pulso curto em baixa tensão pode vencer o tempo morto sem abrir o bico.
    // Pull-in current is estimated; electrical state advances every CPU tick.
    const double flowing_s = coil_current_a_ >= parameters_.pull_in_current_a
                                 ? hydraulic_flowing_s : 0.0;
    const double delivered_kg = flowing_s * rated_mass_flow_kg_s_;
    delivered_total_kg_ += delivered_kg;
    return delivered_kg;
}

void Ma17InjectorStage::reset_electrical_state() {
    energized_ = false;
    energized_time_s_ = 0.0;
    coil_current_a_ = 0.0;
}

} // namespace ecu_hw
