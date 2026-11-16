#include "ecu_hw/Ma17IdleBridge.hpp"
#include "ecu_hw/Ma17TpsCircuit.hpp"
#include "engine/IdleActuator.hpp"
#include "engine/ThrottleAssembly.hpp"

#include <gtest/gtest.h>

#include <cmath>

namespace {
constexpr double radians(double degrees) {
    return degrees * 3.14159265358979323846 / 180.0;
}

TEST(ThrottleAssembly, CableAndStopMeetWithoutMovingEachOther) {
    engine::ThrottleAssembly throttle;
    EXPECT_NEAR(throttle.angle_rad(), radians(4), 1e-12);
    EXPECT_TRUE(throttle.contact_closed());

    throttle.set_cable_pull_m(0.001 + 0.025 * radians(12));
    EXPECT_NEAR(throttle.cable_angle_rad(), radians(12), 1e-12);
    EXPECT_NEAR(throttle.angle_rad(), radians(12), 1e-12);
    EXPECT_FALSE(throttle.contact_closed());

    throttle.set_stop_angle_rad(radians(8));
    EXPECT_NEAR(throttle.angle_rad(), radians(12), 1e-12);
    throttle.set_cable_pull_m(0.0);
    EXPECT_NEAR(throttle.angle_rad(), radians(8), 1e-12);
    EXPECT_TRUE(throttle.contact_closed());
}

TEST(IdleActuator, OppositeBridgeCommandsMoveStopWithoutFightingCable) {
    engine::IdleActuator actuator;
    engine::ThrottleAssembly throttle;
    ecu_hw::Ma17IdleBridge bridge;
    const double initial_stop = throttle.stop_angle_rad();
    const auto extend = bridge.drive(0x20);
    EXPECT_GT(extend.voltage_v, 0.0);
    for (int tick = 0; tick < 500; ++tick)
        actuator.step(extend.voltage_v, extend.brake, 0.001);
    throttle.set_stop_angle_rad(actuator.stop_angle_rad());
    EXPECT_GT(throttle.stop_angle_rad(), initial_stop);
    EXPECT_TRUE(throttle.contact_closed());

    throttle.set_cable_pull_m(0.001 + 0.025 * radians(12));
    EXPECT_FALSE(throttle.contact_closed());
    const double cable_angle = throttle.angle_rad();
    const auto retract = bridge.drive(0x40);
    EXPECT_LT(retract.voltage_v, 0.0);
    for (int tick = 0; tick < 1000; ++tick)
        actuator.step(retract.voltage_v, retract.brake, 0.001);
    throttle.set_stop_angle_rad(actuator.stop_angle_rad());
    EXPECT_LT(throttle.stop_angle_rad(), initial_stop);
    EXPECT_NEAR(throttle.angle_rad(), cable_angle, 1e-12);
    throttle.set_cable_pull_m(0.0);
    EXPECT_TRUE(throttle.contact_closed());
    EXPECT_NEAR(throttle.angle_rad(), actuator.stop_angle_rad(), 1e-12);

    const auto brake = bridge.drive(0x00);
    const double stopped_stem = actuator.stem_m();
    for (int tick = 0; tick < 1000; ++tick)
        actuator.step(brake.voltage_v, brake.brake, 0.001);
    EXPECT_NEAR(actuator.stem_m(), stopped_stem, 0.00001);
}

TEST(IdleActuator, FullTravelStopsAtServiceAngleAndReturnsToBase) {
    engine::IdleActuator actuator;
    ecu_hw::Ma17IdleBridge bridge;
    const auto extend = bridge.drive(0x20);
    for (int tick = 0; tick < 4000; ++tick)
        actuator.step(extend.voltage_v, extend.brake, 0.001);
    EXPECT_NEAR(actuator.stop_angle_rad(), radians(18), 1e-12);

    const auto retract = bridge.drive(0x40);
    for (int tick = 0; tick < 4000; ++tick)
        actuator.step(retract.voltage_v, retract.brake, 0.001);
    EXPECT_NEAR(actuator.stem_m(), 0.0, 1e-12);
    EXPECT_NEAR(actuator.stop_angle_rad(), 0.04, 1e-12);
}

TEST(Ma17TpsCircuit, TracksShareAngleWithDifferentUsefulRanges) {
    ecu_hw::Ma17TpsCircuit circuit;
    const auto adc8 = [](double voltage) {
        return static_cast<int>(std::lround(voltage / 5.0 * 1023.0)) >> 2;
    };
    EXPECT_EQ(adc8(circuit.track2_voltage(radians(4))), 40);
    EXPECT_EQ(adc8(circuit.track1_voltage(radians(4))), 95);
    EXPECT_LT(circuit.track2_voltage(radians(2)),
              circuit.track2_voltage(radians(4)));
    EXPECT_LT(circuit.track1_voltage(radians(2)),
              circuit.track1_voltage(radians(4)));
    EXPECT_LT(circuit.track1_voltage(radians(18)),
              circuit.track1_voltage(radians(24)));
    EXPECT_DOUBLE_EQ(circuit.track1_voltage(radians(24)),
                     circuit.track1_voltage(radians(90)));
    EXPECT_LT(circuit.track2_voltage(radians(24)),
              circuit.track2_voltage(radians(90)));
    EXPECT_NEAR(circuit.track2_voltage(radians(18) - 1e-8),
                circuit.track2_voltage(radians(18) + 1e-8), 1e-6);
}

TEST(Ma17TpsCircuit, BenchTypicalMatchesPublishedEndPoints) {
    ecu_hw::Ma17TpsCircuit circuit(ecu_hw::TpsCircuitParameters::bench_typical());
    EXPECT_NEAR(circuit.track1_voltage(radians(0)), 0.27, 0.02);
    EXPECT_NEAR(circuit.track1_voltage(radians(4)), 1.0, 0.01);
    EXPECT_NEAR(circuit.track1_voltage(radians(24)), 4.65, 0.02);
    EXPECT_DOUBLE_EQ(circuit.track1_voltage(radians(24)),
                     circuit.track1_voltage(radians(90)));
    EXPECT_DOUBLE_EQ(circuit.track2_voltage(radians(4)), 0.0);
    EXPECT_DOUBLE_EQ(circuit.track2_voltage(radians(18)), 0.0);
    EXPECT_NEAR(circuit.track1_voltage(radians(23.2)), 4.5, 0.05);
    EXPECT_GT(circuit.track2_voltage(radians(23.2)), 0.45);
    EXPECT_LT(circuit.track2_voltage(radians(23.2)), 0.70);
    EXPECT_NEAR(circuit.track2_voltage(radians(90)), 4.5, 0.02);
}

} // namespace
