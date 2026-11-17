#include "engine/CrankDynamics.hpp"

#include <gtest/gtest.h>

#include <cmath>

namespace {

TEST(CrankDynamics, StarterAcceleratesFromRestByTorqueBalance) {
    engine::CrankParameters parameters;
    parameters.inertia_kg_m2 = 0.20;
    parameters.starter_torque_nm = 30.0;
    parameters.breakaway_torque_nm = 0.0;
    parameters.running_friction_nm = 0.0;
    parameters.viscous_friction_nm_per_rad_s = 0.0;
    engine::CrankDynamics crank(parameters);

    constexpr int ticks = 495000; // 0.5 s
    for (int tick = 0; tick < ticks; ++tick)
        crank.step(true);

    EXPECT_NEAR(crank.speed_rad_s(), 75.0, 1e-8);
    EXPECT_NEAR(crank.angle_rad(), 18.75, 1e-8);
    EXPECT_NEAR(crank.rpm(), 75.0 * 30.0 / std::acos(-1.0), 1e-7);
}

TEST(CrankDynamics, WheelHasTwoMissingPositionsAndStopsWithoutDrive) {
    engine::CrankDynamics crank;
    int counts[engine::CrankDynamics::wheel_positions]{};
    for (int tick = 0; tick < 2475000; ++tick) {
        if (crank.step(tick < 198000))
            ++counts[crank.wheel_position()];
    }
    for (int position = 0; position < 60; ++position)
        EXPECT_GT(counts[position], 0) << position;
    EXPECT_DOUBLE_EQ(crank.speed_rad_s(), 0.0);
    const double stopped_angle = crank.angle_rad();
    for (int tick = 0; tick < 99000; ++tick)
        EXPECT_FALSE(crank.step(false));
    EXPECT_DOUBLE_EQ(crank.angle_rad(), stopped_angle);
}

TEST(CrankDynamics, FrictionMatchesMotoredIdleOrderOfMagnitude) {
    engine::CrankDynamics crank;
    for (int tick = 0; tick < 400000; ++tick)
        crank.step(true);
    const double fmep_pa = crank.friction_torque_nm() *
                           4.0 * std::acos(-1.0) / 0.001580;
    EXPECT_GT(fmep_pa, 100000.0);
    EXPECT_LT(fmep_pa, 150000.0);
}

TEST(CrankDynamics, RejectsInvalidParametersAndTorque) {
    engine::CrankParameters parameters;
    parameters.inertia_kg_m2 = 0.0;
    EXPECT_THROW(engine::CrankDynamics crank(parameters),
                 std::invalid_argument);
    engine::CrankDynamics crank;
    EXPECT_THROW(crank.step(false, 0.0, -1.0), std::invalid_argument);
}

} // namespace
