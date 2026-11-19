// Bench controller without the ROM (GOAL_DYNO_ROM 5.5): constant engine torque, 180-degree
// sample-and-hold speed feedback, default DynoPi gains. LLM-written (Claude).
#include "engine/CrankDynamics.hpp"
#include "ma17/DynoBench.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>

namespace {
struct Outcome {
    double min_rpm_late = 1e9, max_rpm_late = 0.0, peak_brake = 0.0, saturated_s = 0.0;
};

Outcome run_constant_torque(double engine_nm, double target_rpm, double seconds) {
    engine::CrankDynamics crank;
    ma17::DynoBrake brake(target_rpm * 2.0 * engine::physics::pi / 60.0);
    brake.engage(0.0);
    Outcome o;
    const auto ticks = static_cast<long long>(seconds * 990000.0);
    double angle_prev = crank.angle_rad();
    for (long long t = 1; t <= ticks; ++t) {
        const double nm = brake.step(crank.angle_rad() - angle_prev, ma17::bench_tick_s);
        angle_prev = crank.angle_rad();
        crank.step(false, engine_nm, nm);
        o.peak_brake = std::max(o.peak_brake, nm);
        if (nm >= 0.999 * brake.t_max()) o.saturated_s += ma17::bench_tick_s;
        if (t > ticks / 2) {
            o.min_rpm_late = std::min(o.min_rpm_late, crank.rpm());
            o.max_rpm_late = std::max(o.max_rpm_late, crank.rpm());
        }
    }
    return o;
}
} // namespace

TEST(DynoBench, ConstantTorqueStabilizesWithinOnePercentWithoutSaturating) {
    const Outcome o = run_constant_torque(130.0, 3000.0, 14.0);
    EXPECT_GT(o.min_rpm_late, 3000.0 * 0.99);
    EXPECT_LT(o.max_rpm_late, 3000.0 * 1.01);
    EXPECT_EQ(o.saturated_s, 0.0);
    EXPECT_LT(o.peak_brake, 400.0);
}

TEST(DynoBench, BrakeNeverPushesTheEngine) {
    ma17::DynoBrake brake(300.0);
    brake.engage(500.0);
    for (int i = 0; i < 100000; ++i) EXPECT_GE(brake.step(0.0005, ma17::bench_tick_s), 0.0);
}

TEST(DynoBench, StateMachineStallsWhenTheEngineNeverRuns) {
    ma17::DynoBenchConfig cfg;
    cfg.settle_end_tick = 1000;
    ma17::DynoBench bench(cfg);
    for (long long t = 1; t <= 1200; ++t)
        bench.brake_for_tick(t, 0.0, 0.0, 0.0, false);
    EXPECT_EQ(bench.state(), ma17::DynoState::Invalid);
    EXPECT_EQ(bench.reason(), ma17::DynoInvalid::Stall);
}
