#include "ecu_hw/Ma17Tachometer.hpp"

#include <gtest/gtest.h>

#include <cmath>

namespace {

constexpr long long kTimeout = 495000; // 500 ms at the Fiat clock (990 kHz)

// One P1.1 pulse: rising edge at `rise`, falling edge 1000 ticks later.
void pulse(ecu_hw::Ma17Tachometer &tach, long long rise) {
    tach.observe(true, rise);
    tach.observe(false, rise + 1000);
}

double expected_rpm(long long period) {
    return 30.0 * 990000.0 / static_cast<double>(period); // 2 pulses/rev
}

} // namespace

TEST(Ma17Tachometer, NeedsTwoRisingEdgesAndIsUnavailableBeforeAnyObservation) {
    ecu_hw::Ma17Tachometer tach;
    EXPECT_FALSE(tach.available());
    EXPECT_EQ(tach.rpm(0), 0.0);
    tach.observe(false, 10); // first sample only initializes the level
    EXPECT_TRUE(tach.available());
    pulse(tach, 100000);
    EXPECT_EQ(tach.rpm(100500), 0.0) << "one edge has no period yet";
    pulse(tach, 300000);
    EXPECT_NEAR(tach.rpm(300500), expected_rpm(200000), 1e-9);
    EXPECT_EQ(tach.pulses(), 2U);
}

TEST(Ma17Tachometer, TimesOutAfterExactly500Milliseconds) {
    ecu_hw::Ma17Tachometer tach;
    tach.observe(false, 0);
    pulse(tach, 100000);
    pulse(tach, 300000);
    EXPECT_GT(tach.rpm(300000 + kTimeout - 1), 0.0);
    EXPECT_EQ(tach.rpm(300000 + kTimeout), 0.0);
    EXPECT_EQ(tach.rpm(300000 + 10 * kTimeout), 0.0);
}

TEST(Ma17Tachometer, RecoversAfterStopOnlyAfterTwoNewEdges) {
    ecu_hw::Ma17Tachometer tach;
    tach.observe(false, 0);
    pulse(tach, 100000);
    pulse(tach, 300000);
    // Engine stalls: a gap longer than the timeout between rising edges.
    const long long resume = 300000 + 3 * kTimeout;
    pulse(tach, resume);
    EXPECT_EQ(tach.rpm(resume + 500), 0.0)
        << "the first edge after a stop has no valid period";
    pulse(tach, resume + 150000);
    EXPECT_NEAR(tach.rpm(resume + 150500), expected_rpm(150000), 1e-9);
    EXPECT_EQ(tach.pulses(), 4U) << "pulses keep counting through the stop";
}

TEST(Ma17Tachometer, FollowsTransientsWithoutFilteringOrOvershoot) {
    ecu_hw::Ma17Tachometer tach;
    tach.observe(false, 0);
    long long rise = 50000;
    pulse(tach, rise);
    double previous = 0.0;
    // Accelerating: the period shrinks 300k -> 60k ticks; rpm must be the
    // instantaneous 1/period value each time, strictly increasing.
    for (long long period : {300000, 240000, 180000, 120000, 90000, 60000}) {
        rise += period;
        pulse(tach, rise);
        const double rpm = tach.rpm(rise + 500);
        EXPECT_NEAR(rpm, expected_rpm(period), 1e-9);
        EXPECT_GT(rpm, previous);
        previous = rpm;
    }
    // Decelerating again follows the latest period too.
    rise += 400000;
    pulse(tach, rise);
    EXPECT_NEAR(tach.rpm(rise + 500), expected_rpm(400000), 1e-9);
    EXPECT_LT(tach.rpm(rise + 500), previous);
}

TEST(Ma17Tachometer,
     IgnoresFallingEdgesAndRepeatedHighSamplesAndReplayRewinds) {
    ecu_hw::Ma17Tachometer tach;
    tach.observe(true, 10); // high at start is a level, not an edge
    tach.observe(true, 20);
    EXPECT_EQ(tach.pulses(), 0U);
    tach.observe(false, 30);
    tach.observe(true, 100000);
    tach.observe(true, 100100); // still high: no second edge
    tach.observe(false, 101000);
    tach.observe(true, 250000);
    EXPECT_EQ(tach.pulses(), 2U);
    EXPECT_NEAR(tach.rpm(250500), expected_rpm(150000), 1e-9);
    // A query earlier than the last edge (replay rewind) is not a reading.
    EXPECT_EQ(tach.rpm(1000), 0.0);
}
