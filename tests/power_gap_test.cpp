// Invariants behind the power-gap investigation (CURVES_STUDY). LLM-written (Claude).
#include "engine/Combustion.hpp"
#include "engine/physics/Losses.hpp"

#include <gtest/gtest.h>

#include <cmath>

namespace {
using engine::physics::AccessoryParams;
using engine::physics::accessory_torque_nm;
constexpr double kPi = 3.14159265358979323846;
double omega_of(double rpm) { return rpm * 2.0 * kPi / 60.0; }
} // namespace

TEST(PowerGap, ExperimentScalesDefaultToTheOriginalModel) {
    AccessoryParams a;
    EXPECT_EQ(a.alternator_scale, 1.0);
    EXPECT_EQ(a.pump_scale, 1.0);
}

TEST(PowerGap, WaterPumpTorqueIsQuadraticAndItsPowerCubicInSpeed) {
    AccessoryParams a;
    a.alternator_scale = 0.0;
    const double t3 = accessory_torque_nm(a, 14.0, omega_of(3000.0));
    const double t6 = accessory_torque_nm(a, 14.0, omega_of(6000.0));
    EXPECT_NEAR(t6 / t3, 4.0, 1e-9);
    // Documented finding: the current pump constants absorb > 10 kW at 6000 rpm.
    EXPECT_GT(t6 * omega_of(6000.0), 10e3);
}

TEST(PowerGap, AccessoryScalesAreIndependent) {
    AccessoryParams both, alt_off, pump_off;
    alt_off.alternator_scale = 0.0;
    pump_off.pump_scale = 0.0;
    const double w = omega_of(4000.0);
    EXPECT_NEAR(accessory_torque_nm(both, 14.0, w),
                accessory_torque_nm(alt_off, 14.0, w) + accessory_torque_nm(pump_off, 14.0, w), 1e-12);
}

namespace {
double fire_torque(const engine::CombustionParameters &p, double strength) {
    engine::Combustion c(p);
    c.set_operating_point(3000.0, 95000.0, 101000.0);
    engine::IntakeStep charge;
    charge.air_to_cylinders_kg = 0.0004;
    charge.fuel_to_cylinders_kg = 0.0004 / 14.7;
    const double tdc = c.tdc_phase_rad();
    c.admit(charge, tdc + 3.5 * kPi); // same pairing as combustion_pulse_test, slot 1
    c.spark(tdc + kPi - 0.2, 1, strength);
    return c.pulse_torque_nm();
}
} // namespace

TEST(PowerGap, TorqueSaturationRemovesTheCoilStrengthScalingAboveTheBurnThreshold) {
    engine::CombustionParameters orig;
    orig.physical_efficiency = true;
    engine::CombustionParameters sat = orig;
    sat.exp_torque_saturate = true;
    const double full = fire_torque(orig, 1.0);
    ASSERT_GT(full, 0.0);
    EXPECT_NEAR(fire_torque(orig, 0.9) / full, 0.9, 1e-9);        // original: proportional
    EXPECT_NEAR(fire_torque(sat, 0.9) / fire_torque(sat, 1.0), 1.0, 1e-9); // experiment: saturated
    EXPECT_NEAR(fire_torque(sat, 0.4) / fire_torque(sat, 1.0), 0.5, 1e-9); // below 0.8: partial
}
