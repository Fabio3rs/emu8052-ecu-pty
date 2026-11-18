#include "engine/CrankDynamics.hpp"
#include "engine/ClutchCoupling.hpp"
#include "engine/Drivetrain.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <limits>

namespace {

TEST(ClutchCoupling, LocksShaftsWithConservedMomentumAndDissipatedEnergy) {
    for (const double crank_speed : {0.0, 100.0}) {
        const double vehicle_speed = 100.0 - crank_speed;
        const auto transfer = engine::solve_clutch_transfer(
            crank_speed, vehicle_speed, 0.2, 2.0, 1000.0, 1.0, 1.0);
        const double crank_after = crank_speed + transfer.crank_impulse_nm_s / 0.2;
        const double vehicle_after = vehicle_speed + transfer.vehicle_impulse_nm_s / 2.0;
        EXPECT_NEAR(crank_after, vehicle_after, 1e-12);
        EXPECT_DOUBLE_EQ(transfer.crank_impulse_nm_s, -transfer.vehicle_impulse_nm_s);
        EXPECT_NEAR(0.2 * crank_after + 2.0 * vehicle_after,
                    0.2 * crank_speed + 2.0 * vehicle_speed, 1e-12);
        const double before = 0.1 * crank_speed * crank_speed +
                              vehicle_speed * vehicle_speed;
        const double after = 0.1 * crank_after * crank_after +
                             vehicle_after * vehicle_after;
        EXPECT_NEAR(before - after, transfer.dissipated_energy_j, 1e-10);
        EXPECT_GT(transfer.dissipated_energy_j, 0.0);
    }
}

TEST(ClutchCoupling, PressureLimitsSlipTorqueAndOpenClutchTransfersNothing) {
    const auto open = engine::solve_clutch_transfer(100, 0, 0.2, 2, 100, 0, 0.01);
    EXPECT_DOUBLE_EQ(open.crank_impulse_nm_s, 0.0);
    EXPECT_DOUBLE_EQ(open.dissipated_energy_j, 0.0);
    const auto slip = engine::solve_clutch_transfer(100, 0, 0.2, 2, 100, 0.5, 0.01);
    EXPECT_DOUBLE_EQ(slip.vehicle_impulse_nm_s, 0.5);
    EXPECT_NEAR(slip.dissipated_energy_j, 49.3125, 1e-12);
    EXPECT_THROW(engine::solve_clutch_transfer(100, 0, 0, 2, 100, 1, 0.01),
                 std::invalid_argument);
    EXPECT_THROW(engine::solve_clutch_transfer(100, 0, 0.2, 2, 100, 2, 0.01),
                 std::invalid_argument);
    EXPECT_THROW(engine::solve_clutch_transfer(100, 0, 0.2, 2, 100, 1, 0),
                 std::invalid_argument);
}

TEST(Drivetrain, CouplesCrankAndVehicleWithEnergyAccountedAsHeat) {
    engine::CrankParameters parameters;
    parameters.breakaway_torque_nm = 0.0;
    parameters.running_friction_nm = 0.0;
    parameters.viscous_friction_nm_per_rad_s = 0.0;
    engine::CrankDynamics crank(parameters);
    crank.step(false, 100.0 * 0.2 * crank.ticks_per_second);
    engine::Drivetrain car(1000.0, 0.29, 200.0);
    car.set_gear(1);
    car.set_clutch_pressure(1.0);
    for (int tick = 0; tick < 198000; ++tick)
        crank.step(false, 0.0, 0.0, 0.0, &car);
    EXPECT_GT(car.speed_m_s(), 0.0);
    EXPECT_NEAR(crank.speed_rad_s(), car.speed_m_s() *
                engine::transmission::overall_ratio(1) / 0.29, 1e-9);
    const double final_energy = 0.1 * crank.speed_rad_s() * crank.speed_rad_s() +
                               500.0 * car.speed_m_s() * car.speed_m_s();
    EXPECT_NEAR(final_energy + car.clutch_heat_j(), 1000.0, 1e-6);
    const double road_speed = car.speed_m_s();
    car.set_clutch_pressure(0.0);
    car.set_gear(2);
    EXPECT_DOUBLE_EQ(car.speed_m_s(), road_speed);
    crank.step(false, 0.0, 0.0, 0.0, &car);
    EXPECT_DOUBLE_EQ(car.speed_m_s(), road_speed);
    car.set_gear(0);
    car.set_clutch_pressure(1.0);
    crank.step(false, 20.0, 0.0, 0.0, &car);
    EXPECT_DOUBLE_EQ(car.speed_m_s(), road_speed);
    EXPECT_DOUBLE_EQ(car.crank_torque_nm(), 0.0);
}

TEST(Drivetrain, ReverseLaunchAndVehicleBackdriveKeepCorrectDirections) {
    engine::CrankParameters parameters;
    parameters.breakaway_torque_nm = 0.0;
    parameters.running_friction_nm = 0.0;
    parameters.viscous_friction_nm_per_rad_s = 0.0;
    engine::CrankDynamics crank(parameters);
    engine::Drivetrain reverse(1000.0, 0.29, 200.0);
    reverse.set_gear(-1);
    reverse.set_clutch_pressure(1.0);
    for (int tick = 0; tick < 99000; ++tick)
        crank.step(false, 20.0, 0.0, 0.0, &reverse);
    EXPECT_LT(reverse.speed_m_s(), 0.0);
    EXPECT_GT(crank.speed_rad_s(), 0.0);
    engine::CrankDynamics stopped(parameters);
    engine::Drivetrain rolling(1000.0, 0.29, 200.0, 10.0);
    rolling.set_gear(3);
    rolling.set_clutch_pressure(1.0);
    stopped.step(false, 0.0, 0.0, 0.0, &rolling);
    EXPECT_GT(stopped.speed_rad_s(), 0.0);
    EXPECT_LT(rolling.speed_m_s(), 10.0);
    EXPECT_GT(rolling.crank_torque_nm(), 0.0);
}

TEST(Drivetrain, RoadResistanceOpposesBothDirectionsAndStopsAtRest) {
    for (const double speed : {-20.0, 20.0}) {
        engine::Drivetrain car(1000.0, 0.29, 200.0, speed);
        // Fixture: 100 N rolling + 0.5 * 1.2 * 0.3 * 2 * 20² = 244 N.
        car.set_road_resistance(100.0, 1.2, 0.3, 2.0);
        EXPECT_DOUBLE_EQ(car.couple(100.0, 0.2, 0.1), 100.0);
        EXPECT_NEAR(car.speed_m_s(), std::copysign(19.9756, speed), 1e-12);
        EXPECT_DOUBLE_EQ(car.clutch_heat_j(), 0.0);
        // Even with a long timestep the resistance must never reverse speed.
        car.couple(100.0, 0.2, 1000.0);
        EXPECT_DOUBLE_EQ(car.speed_m_s(), 0.0);
        car.couple(100.0, 0.2, 1.0);
        EXPECT_DOUBLE_EQ(car.speed_m_s(), 0.0);
    }
    engine::Drivetrain car(1000.0, 0.29, 200.0);
    EXPECT_THROW(car.set_road_resistance(-1.0, 1.2, 0.3, 2.0),
                 std::invalid_argument);
    EXPECT_THROW(car.set_road_resistance(100.0,
        std::numeric_limits<double>::quiet_NaN(), 0.3, 2.0), std::invalid_argument);
}

TEST(Drivetrain, RollingResistanceHoldsWeakDriveAndAllowsLaunch) {
    for (const int gear : {-1, 1}) {
        engine::Drivetrain car(1000.0, 0.29, 4.0);
        car.set_gear(gear);
        car.set_road_resistance(100.0, 0.0, 0.0, 0.0);
        car.set_clutch_pressure(0.25); // 1 Nm gives about 53 N at the tire.
        for (int step = 0; step < 100; ++step) {
            const double crank = car.couple(100.0, 0.2, 0.001);
            EXPECT_DOUBLE_EQ(car.speed_m_s(), 0.0);
            EXPECT_LT(crank, 100.0); // Clutch still loads the engine at rest.
        }
        car.set_clutch_pressure(1.0);
        const double crank = car.couple(100.0, 0.2, 0.001);
        const double tire_force =
            4.0 * engine::transmission::overall_ratio(gear) / 0.29;
        const double expected_speed =
            std::copysign((std::abs(tire_force) - 100.0) * 0.001 / 1000.0,
                          tire_force);
        EXPECT_NEAR(car.speed_m_s(), expected_speed, 1e-12);
        EXPECT_LT(crank, 100.0);
    }
}

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

TEST(CrankDynamics, TransmissionCanMotorAndBrakeCrankWithoutCombustion) {
    engine::CrankParameters parameters;
    parameters.breakaway_torque_nm = 0.0;
    parameters.running_friction_nm = 0.0;
    parameters.viscous_friction_nm_per_rad_s = 0.0;
    engine::CrankDynamics crank(parameters);
    EXPECT_DOUBLE_EQ(crank.inertia_kg_m2(), 0.20);
    for (int tick = 0; tick < 99000; ++tick)
        crank.step(false, 0.0, 0.0, 20.0);
    EXPECT_NEAR(crank.speed_rad_s(), 10.0, 1e-9);
    EXPECT_NEAR(crank.angle_rad(), 0.5, 1e-9);
    const double energy = 0.5 * crank.inertia_kg_m2() *
                          crank.speed_rad_s() * crank.speed_rad_s();
    EXPECT_NEAR(energy, 20.0 * crank.angle_rad(), 1e-8);
    for (int tick = 0; tick < 100000; ++tick)
        crank.step(false, 0.0, 0.0, -20.0);
    EXPECT_DOUBLE_EQ(crank.speed_rad_s(), 0.0);
    EXPECT_NEAR(crank.angle_rad(), 1.0, 1e-8);
    const double stopped = crank.angle_rad();
    EXPECT_FALSE(crank.step(false, 0.0, 0.0, -20.0));
    EXPECT_DOUBLE_EQ(crank.angle_rad(), stopped);
}

TEST(CrankDynamics, RejectsInvalidParametersAndTorque) {
    engine::CrankParameters parameters;
    parameters.inertia_kg_m2 = 0.0;
    EXPECT_THROW(engine::CrankDynamics crank(parameters),
                 std::invalid_argument);
    engine::CrankDynamics crank;
    EXPECT_THROW(crank.step(false, 0.0, -1.0), std::invalid_argument);
    for (const double torque : {std::numeric_limits<double>::quiet_NaN(),
             std::numeric_limits<double>::infinity(),
             -std::numeric_limits<double>::infinity()})
        EXPECT_THROW(crank.step(false, 0.0, 0.0, torque), std::invalid_argument);
    EXPECT_DOUBLE_EQ(crank.speed_rad_s(), 0.0);
}

} // namespace
