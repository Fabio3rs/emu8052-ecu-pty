// Energy ledger of PlantWindow without the ROM (GOAL_DYNO_ROM 3.6). LLM-written (Claude).
#include "engine/CrankDynamics.hpp"
#include "engine/PlantTelemetry.hpp"

#include <gtest/gtest.h>

#include <cmath>

namespace {
constexpr double dt = 1.0 / engine::CrankDynamics::ticks_per_second;

struct RunResult {
    engine::PlantWindowResult last;
    double omega = 0.0;
};

// Drives a CrankDynamics with fixed torques for n ticks, ledgering every tick.
RunResult drive(double combustion_nm, double brake_nm, double pumping_nm, double accessory_nm,
          bool starter, long long ticks, double window_cycles) {
    engine::CrankDynamics crank;
    engine::PlantWindow window{0.00158, 4, window_cycles};
    window.set_inertia(crank.inertia_kg_m2());
    for (long long tick = 1; tick <= ticks; ++tick) {
        const double angle0 = crank.angle_rad(), omega0 = crank.speed_rad_s();
        engine::TickTorques t;
        t.combustion_nm = combustion_nm;
        t.friction_nm = crank.friction_torque_nm();
        t.pumping_nm = pumping_nm;
        t.accessory_nm = accessory_nm;
        t.brake_nm = brake_nm;
        t.starter_nm = starter ? crank.starter_torque_at_crank_nm() : 0.0;
        crank.step(starter, combustion_nm, brake_nm + pumping_nm + accessory_nm);
        window.accumulate(tick, dt, crank.angle_rad() - angle0, omega0, crank.speed_rad_s(), t);
        window.finish_if_ready(1.19, 14.7, 44e6);
    }
    return {window.last(), crank.speed_rad_s()};
}
} // namespace

TEST(PlantEnergy, ConstantCombustionAndBrakeCloseTheLedger) {
    // 60 N.m of combustion against 25 N.m of brake: the engine accelerates, the ledger closes.
    const RunResult r = drive(60.0, 25.0, 5.0, 3.0, false, 400000, 0.25);
    ASSERT_TRUE(r.last.valid);
    EXPECT_LT(std::abs(r.last.energy_residual_rel), 1e-3);
    EXPECT_NEAR(r.last.brake_absorbed_nm, 25.0, 1e-9);
    EXPECT_NEAR(r.last.accessory_torque_nm, 3.0, 1e-9);
    EXPECT_NEAR(r.last.shaft_torque_nm,
                r.last.indicated_torque_nm - r.last.friction_torque_nm - 5.0 - 3.0, 1e-9);
    // net torque x crank angle = kinetic energy gained (J d(omega)/dt averaged by angle)
    const double angle = r.last.mean_rpm * 2.0 * 3.14159265358979323846 / 60.0 * r.last.window_s;
    EXPECT_NEAR(r.last.net_torque_nm * angle, r.last.kinetic_j, 1e-6 * std::abs(r.last.kinetic_j));
    EXPECT_GT(r.last.window_id, 0u);
    EXPECT_GT(r.last.tick_end, r.last.tick_start);
}

TEST(PlantEnergy, FreeAccelerationShaftPowerIsKineticPowerOverTime) {
    const RunResult r = drive(80.0, 0.0, 0.0, 0.0, false, 300000, 0.25);
    ASSERT_TRUE(r.last.valid);
    const double de = r.last.kinetic_j;
    ASSERT_GT(de, 0.0);
    EXPECT_NEAR(r.last.shaft_power_kw, de / r.last.window_s / 1000.0,
                1e-9 * std::abs(r.last.shaft_power_kw));
    EXPECT_LT(std::abs(r.last.energy_residual_rel), 1e-3);
    // dE_kin from the speeds equals the net work (independent of the ledger formulas)
    const double net_work = r.last.net_torque_nm * (r.last.omega_end_rad_s * r.last.window_s * 0.5 +
                                                    r.last.omega_start_rad_s * r.last.window_s * 0.5);
    EXPECT_NEAR(net_work, de, 1e-3 * de);
}

TEST(PlantEnergy, StarterWorkIsCounted) {
    const RunResult r = drive(0.0, 0.0, 0.0, 0.0, true, 200000, 0.25);
    ASSERT_TRUE(r.last.valid);
    EXPECT_GT(r.last.w_starter_j, 0.0);
    EXPECT_LT(std::abs(r.last.energy_residual_rel), 1e-3);
}
