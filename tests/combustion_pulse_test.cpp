// Exact pulse integration (GOAL_DYNO_ROM phase 1). LLM-written (Claude).
#include "engine/Combustion.hpp"
#include "engine/IntakeFuel.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <random>

namespace {
constexpr double pi = 3.14159265358979323846;

// Builds a Combustion with exactly one scheduled pulse; returns the spark angle.
double fire_one_pulse(engine::Combustion &c, unsigned slot, double advance_rad) {
    engine::IntakeStep charge;
    charge.air_to_cylinders_kg = 0.0004;
    charge.fuel_to_cylinders_kg = 0.0004 / 14.7;
    const double tdc = c.tdc_phase_rad();
    // Admit on the cylinder that will be on compression for `slot` (see slot_at()).
    c.admit(charge, tdc + (static_cast<double>(slot) + 2.5) * pi);
    const double angle = tdc + static_cast<double>(slot) * pi - advance_rad;
    c.spark(angle, slot % 2, 1.0);
    return angle;
}
} // namespace

TEST(CombustionPulse, TorqueIsZeroBeforeSparkAndAfterEnd) {
    engine::Combustion c;
    const double s = fire_one_pulse(c, 1, 0.2);
    ASSERT_GT(c.pulse_torque_nm(), 0.0);
    EXPECT_DOUBLE_EQ(c.pulse_start_rad(), s);
    EXPECT_DOUBLE_EQ(c.torque_nm(s - 1e-9), 0.0);
    EXPECT_DOUBLE_EQ(c.torque_nm(s - 1.0), 0.0);
    EXPECT_DOUBLE_EQ(c.torque_nm(s), c.pulse_torque_nm());
    EXPECT_DOUBLE_EQ(c.torque_nm(s + 1.999), c.pulse_torque_nm());
    EXPECT_DOUBLE_EQ(c.torque_nm(s + 2.0), 0.0); // end is exclusive
    EXPECT_DOUBLE_EQ(c.torque_nm(s + 3.0), 0.0);
    EXPECT_DOUBLE_EQ(c.work_j(s - 3.0, s), 0.0);
    EXPECT_DOUBLE_EQ(c.work_j(s + 2.0, s + 9.0), 0.0);
}

TEST(CombustionPulse, ConstantStepIntegrationOfOnePulseIsExact) {
    // 1000 random spark phases against the step grid, steps from 0.01 to 5 degrees.
    std::mt19937 rng(12345);
    std::uniform_real_distribution<double> phase(0.0, 1.0), step_deg(0.01, 5.0),
        advance(0.0, 0.55); // inside the 0.60 rad spark window
    for (int trial = 0; trial < 1000; ++trial) {
        engine::Combustion c;
        const unsigned slot = static_cast<unsigned>(trial % 4);
        const double s = fire_one_pulse(c, slot, advance(rng));
        const double expected = c.pulse_torque_nm() * 2.0;
        ASSERT_GT(expected, 0.0);
        const double step = step_deg(rng) * pi / 180.0;
        // grid anchored so the spark lands at a random fraction of a step
        double a = s - 4.0 - phase(rng) * step, w = 0.0;
        while (a < s + 6.0) {
            w += c.work_j(a, a + step);
            a += step;
        }
        EXPECT_NEAR(w, expected, 1e-9 * expected) << "trial " << trial;
    }
}

TEST(CombustionPulse, ScheduledEnergyAccumulatesTwoRadianPerPulse) {
    engine::Combustion c;
    fire_one_pulse(c, 0, 0.2);
    const double first = c.energy_scheduled_j();
    EXPECT_NEAR(first, c.pulse_torque_nm() * 2.0, 1e-12);
    fire_one_pulse(c, 1, 0.2);
    EXPECT_GT(c.energy_scheduled_j(), first);
}
