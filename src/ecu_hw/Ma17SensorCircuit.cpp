#include "ecu_hw/Ma17SensorCircuit.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace ecu_hw {
namespace {
// From scanner SensorDecoders.cpp; fit is not an independent measurement.
constexpr double sh_a = 0.00130233960469996;
constexpr double sh_b = 0.00025894836043228303;
constexpr double sh_c = 0.0000001691900955030085;
constexpr double kelvin_offset = 273.15;
} // namespace

Ma17SensorCircuit::Ma17SensorCircuit(SensorCircuitParameters parameters)
    : parameters_(parameters) {
    if (!std::isfinite(parameters.reference_v) ||
        parameters.reference_v <= 0.0 ||
        !std::isfinite(parameters.air_pullup_ohm) ||
        parameters.air_pullup_ohm <= 0.0 ||
        !std::isfinite(parameters.coolant_pullup_ohm) ||
        parameters.coolant_pullup_ohm <= 0.0 ||
        !std::isfinite(parameters.battery_v) || parameters.battery_v < 0.0 ||
        !std::isfinite(parameters.battery_divider_ratio) ||
        parameters.battery_divider_ratio < 0.0 ||
        parameters.battery_divider_ratio > 1.0 ||
        !std::isfinite(parameters.lambda_adc_gain) ||
        parameters.lambda_adc_gain <= 0.0)
        throw std::invalid_argument("invalid sensor circuit parameters");
}

double Ma17SensorCircuit::ntc_resistance_ohm(double temperature_c) {
    if (!std::isfinite(temperature_c) || temperature_c < -50.0 ||
        temperature_c > 150.0)
        throw std::invalid_argument("invalid NTC temperature");
    const double inverse_kelvin = 1.0 / (temperature_c + kelvin_offset);
    double low = std::log(1.0);
    double high = std::log(1e7);
    for (int iteration = 0; iteration < 64; ++iteration) {
        const double middle = (low + high) / 2.0;
        const double estimated =
            sh_a + sh_b * middle + sh_c * middle * middle * middle;
        if (estimated < inverse_kelvin)
            low = middle;
        else
            high = middle;
    }
    return std::exp((low + high) / 2.0);
}

double Ma17SensorCircuit::divider_voltage(double resistance_ohm,
                                          double pullup_ohm) const {
    return parameters_.reference_v * resistance_ohm /
           (resistance_ohm + pullup_ohm);
}

double Ma17SensorCircuit::air_voltage(double temperature_c) const {
    return divider_voltage(ntc_resistance_ohm(temperature_c),
                           parameters_.air_pullup_ohm);
}

double Ma17SensorCircuit::coolant_voltage(double temperature_c) const {
    return divider_voltage(ntc_resistance_ohm(temperature_c),
                           parameters_.coolant_pullup_ohm);
}

double Ma17SensorCircuit::battery_voltage() const {
    return std::clamp(parameters_.battery_v * parameters_.battery_divider_ratio,
                      0.0, parameters_.reference_v);
}

double Ma17SensorCircuit::lambda_adc_voltage(double sensor_v) const {
    if (!std::isfinite(sensor_v) || sensor_v < 0.0)
        throw std::invalid_argument("invalid lambda sensor voltage");
    return std::clamp(sensor_v * parameters_.lambda_adc_gain,
                      0.0, parameters_.reference_v);
}

} // namespace ecu_hw
