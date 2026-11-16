#include "ecu_hw/Ma17SensorCircuit.hpp"
#include "engine/ThermalState.hpp"

#include <gtest/gtest.h>

#include <cmath>

namespace {

TEST(ThermalState, ConservesEnergyAcrossInternalNodes) {
    engine::ThermalParameters parameters;
    parameters.air_ambient_w_per_k = 0.0;
    parameters.coolant_ambient_w_per_k = 0.0;
    engine::ThermalState state(20.0, 90.0, parameters);
    const double initial_energy = 20.0 * parameters.air_capacity_j_per_k +
                                  90.0 * parameters.wall_capacity_j_per_k +
                                  90.0 * parameters.coolant_capacity_j_per_k;
    state.advance_ticks(9900000);
    const double final_energy =
        state.air_c() * parameters.air_capacity_j_per_k +
        state.wall_c() * parameters.wall_capacity_j_per_k +
        state.coolant_c() * parameters.coolant_capacity_j_per_k;
    EXPECT_NEAR(final_energy, initial_energy, 1e-5);
    EXPECT_GT(state.air_c(), 20.0);
    EXPECT_GT(state.air_c(), state.air_sensor_c());
    EXPECT_LT(state.coolant_c(), 90.0);
}

TEST(Ma17SensorCircuit, HotNtcLowersDividerVoltage) {
    ecu_hw::Ma17SensorCircuit circuit;
    EXPECT_GT(ecu_hw::Ma17SensorCircuit::ntc_resistance_ohm(20.0),
              ecu_hw::Ma17SensorCircuit::ntc_resistance_ohm(90.0));
    EXPECT_GT(circuit.air_voltage(20.0), circuit.air_voltage(90.0));
    EXPECT_GT(circuit.coolant_voltage(20.0), circuit.coolant_voltage(90.0));
    EXPECT_DOUBLE_EQ(circuit.battery_voltage(), 3.25);
    EXPECT_THROW(circuit.air_voltage(-60.0), std::invalid_argument);
}

TEST(Ma17SensorCircuit, LambdaGainConditionsAdcPin) {
    ecu_hw::SensorCircuitParameters parameters;
    parameters.lambda_adc_gain = 5.0;
    ecu_hw::Ma17SensorCircuit circuit(parameters);
    EXPECT_DOUBLE_EQ(circuit.lambda_adc_voltage(0.1), 0.5);
    EXPECT_DOUBLE_EQ(circuit.lambda_adc_voltage(0.9), 4.5);
    EXPECT_DOUBLE_EQ(circuit.lambda_adc_voltage(1.2), 5.0);
    EXPECT_THROW(circuit.lambda_adc_voltage(-0.1), std::invalid_argument);
}

} // namespace
