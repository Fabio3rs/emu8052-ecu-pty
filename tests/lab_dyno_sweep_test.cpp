#include "lab/DynoSweep.hpp"

#include <gtest/gtest.h>

#include <thread>

TEST(DynoSweep, PlanFromSpecAndBadSpecs) {
    EXPECT_EQ(lab::parse_sweep_spec("1500:6000:500").size(), 10u);
    EXPECT_EQ(lab::parse_sweep_spec("3000:3000:500"), (std::vector<double>{3000.0}));
    EXPECT_TRUE(lab::parse_sweep_spec("garbage").empty());
    EXPECT_TRUE(lab::parse_sweep_spec("6000:1500:500").empty());
    EXPECT_TRUE(lab::parse_sweep_spec("1500:6000:0").empty());
    EXPECT_TRUE(lab::parse_sweep_spec("1:2:3:4").empty());
}

TEST(DynoSweep, ParsesAMeasurementLineAndIgnoresOthers) {
    const std::string line =
        "{\"type\":\"dyno_point\",\"state\":\"ACCEPTED\",\"reason\":\"none\","
        "\"target_rpm\":3000.0,\"mean_rpm\":2999.68,\"shaft_torque_nm\":117.9,"
        "\"shaft_power_kw\":37.0,\"adv_mean_deg\":18.6,\"mbt_mean_deg\":27.4,"
        "\"lambda\":1.0,\"spark_abs_deg_cyl\":[1.0,2.0]}";
    const auto row = lab::parse_dyno_point_line(line);
    ASSERT_TRUE(row);
    EXPECT_EQ(row->state, "ACCEPTED");
    EXPECT_NEAR(row->point.torque_nm, 117.9, 1e-9);
    EXPECT_NEAR(row->target_rpm, 3000.0, 1e-9);
    EXPECT_FALSE(lab::parse_dyno_point_line("[P53-GATE] tick=1"));
    EXPECT_FALSE(lab::parse_dyno_point_line("{\"type\":\"dyno_point\",broken"));
    EXPECT_FALSE(lab::parse_dyno_point_line("{\"type\":\"other\"}"));
}

// Only ACCEPTED points are curve points; the rest are INVALID with a reason.
TEST(DynoSweep, OnlyAcceptedPointsReachTheCurveAndStatesAreShown) {
    lab::DynoSweepState sweep;
    lab::DynoProvenance provenance;
    provenance.code_sha = "abc1234";
    provenance.rom_sha256 = std::string(64, 'f');
    sweep.start({3000.0, 3500.0, 4000.0}, provenance);
    ASSERT_TRUE(sweep.running);
    EXPECT_EQ(sweep.lines().front(), "3000 STAB");
    lab::DynoSweepRow accepted;
    accepted.target_rpm = 3000.0;
    accepted.state = "ACCEPTED";
    accepted.point = {3001.0, 118.0, 37.1};
    sweep.on_row(accepted);
    lab::DynoSweepRow invalid;
    invalid.target_rpm = 3500.0;
    invalid.state = "INVALID";
    invalid.reason = "not_steady";
    sweep.on_row(invalid);
    EXPECT_EQ(sweep.curve.points.size(), 1u);
    EXPECT_TRUE(sweep.running);              // 4000 still to run
    sweep.on_failure();                      // child died: INVALID: no result
    EXPECT_FALSE(sweep.running);
    const auto lines = sweep.lines();
    EXPECT_EQ(lines[0], "4000 INVALID: no result");
    EXPECT_EQ(lines[1], "3500 INVALID: not_steady");
    EXPECT_EQ(lines[2], "3000 ACC 118.0 N.M");
    ASSERT_TRUE(sweep.curve.provenance);
    EXPECT_EQ(sweep.curve.provenance->code_sha, "abc1234");
}

TEST(DynoSweep, CancelStopsTheSweepAndSaysSo) {
    lab::DynoSweepState sweep;
    sweep.start({3000.0, 3500.0}, {});
    sweep.cancel();
    EXPECT_FALSE(sweep.running);
    EXPECT_EQ(sweep.lines().front(), "CANCELLED");
}

// The runner reads a child's stdout without blocking and sees it exit.
TEST(ChildProcess, ReadsLinesWithoutBlockingAndDetectsExit) {
    lab::ChildProcess child;
    ASSERT_TRUE(child.start({"/bin/sh", "-c", "echo one; echo two; sleep 0.2; echo three"}));
    std::vector<std::string> lines;
    for (int i = 0; i < 200 && !(child.exited() && lines.size() >= 3); ++i) {
        for (auto &l : child.poll_lines())
            lines.push_back(l);
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    EXPECT_EQ(lines, (std::vector<std::string>{"one", "two", "three"}));
    EXPECT_TRUE(child.exited());
    // A missing binary exits with 127 and prints nothing.
    ASSERT_TRUE(child.start({"/nonexistent/binary"}));
    for (int i = 0; i < 100 && !child.exited(); ++i)
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    EXPECT_TRUE(child.exited());
    EXPECT_TRUE(child.poll_lines().empty());
}

// Review finding: an ACCEPTED row without a finite rpm/torque is not a point.
TEST(DynoSweep, AcceptedRowWithNanIsInvalidNotACurvePoint) {
    lab::DynoSweepState sweep;
    sweep.start({3000.0, 3500.0}, {});
    lab::DynoSweepRow bad;
    bad.target_rpm = 3000.0;
    bad.state = "ACCEPTED";
    bad.point.rpm = std::nan("");
    bad.point.torque_nm = 100.0;
    sweep.on_row(bad);
    EXPECT_TRUE(sweep.curve.points.empty());
    EXPECT_EQ(sweep.lines()[1], "3000 INVALID: bad result");
    EXPECT_TRUE(sweep.running); // 3500 still to run
}
