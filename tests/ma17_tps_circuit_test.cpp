// UI-26: TPS tracks versus throttle angle. The scope compares both tracks by
// angle, so the electrical transfer must be monotonic and match the anchors
// documented in Ma17TpsCircuit.hpp.
#include "ecu_hw/Ma17TpsCircuit.hpp"

#include <gtest/gtest.h>

#include <cmath>

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double deg(double degrees) { return degrees * kPi / 180.0; }

} // namespace

TEST(Ma17TpsCircuit, BothTracksAreFiniteBoundedAndMonotonicOverTheFullTravel) {
    for (const bool bench : {false, true}) {
        const ecu_hw::Ma17TpsCircuit circuit(
            bench ? ecu_hw::TpsCircuitParameters::bench_typical()
                  : ecu_hw::TpsCircuitParameters{});
        double previous1 = -1.0, previous2 = -1.0;
        for (int tenth = 0; tenth <= 900; ++tenth) {
            const double angle = deg(tenth / 10.0);
            const double v1 = circuit.track1_voltage(angle);
            const double v2 = circuit.track2_voltage(angle);
            ASSERT_TRUE(std::isfinite(v1) && std::isfinite(v2)) << tenth / 10.0;
            EXPECT_GE(v1, 0.0);
            EXPECT_LE(v1, circuit.reference_voltage() + 1e-9);
            EXPECT_GE(v2, 0.0);
            EXPECT_LE(v2, circuit.reference_voltage() + 1e-9);
            EXPECT_GE(v1, previous1 - 1e-9) << "track 1 dropped at " << tenth / 10.0 << " deg";
            EXPECT_GE(v2, previous2 - 1e-9) << "track 2 dropped at " << tenth / 10.0 << " deg";
            previous1 = v1;
            previous2 = v2;
        }
    }
}

TEST(Ma17TpsCircuit, DefaultParametersAreAnchoredToTheObservedAdcPair) {
    const ecu_hw::Ma17TpsCircuit circuit;
    const double rest = ecu_hw::TpsCircuitParameters{}.rest_angle_rad;
    EXPECT_NEAR(rest, deg(4.0), 1e-3);
    EXPECT_NEAR(circuit.track1_voltage(rest), 95.0 * 4.0 / 1023.0 * 5.0, 1e-9); // ADC6 = 95
    EXPECT_NEAR(circuit.track2_voltage(rest), 40.0 * 4.0 / 1023.0 * 5.0, 1e-9); // ADC0 = 40
}

TEST(Ma17TpsCircuit, BenchTypicalFitReproducesThePublishedPoints) {
    const ecu_hw::Ma17TpsCircuit circuit(ecu_hw::TpsCircuitParameters::bench_typical());
    EXPECT_NEAR(circuit.track1_voltage(deg(4.0)), 1.0, 0.02);   // idle stop
    EXPECT_NEAR(circuit.track1_voltage(deg(24.0)), 4.65, 0.02); // end of track 1
    EXPECT_NEAR(circuit.track2_voltage(deg(90.0)), 4.5, 0.15);  // full throttle
    EXPECT_NEAR(circuit.track2_voltage(deg(10.0)), 0.0, 1e-9);  // track 2 starts near 18 deg
    // Overlap: track 2 is about 0.55 V when track 1 reaches 4.5 V.
    double angle_at_4v5 = -1.0;
    for (int tenth = 0; tenth <= 900 && angle_at_4v5 < 0.0; ++tenth)
        if (circuit.track1_voltage(deg(tenth / 10.0)) >= 4.5)
            angle_at_4v5 = deg(tenth / 10.0);
    ASSERT_GT(angle_at_4v5, 0.0);
    EXPECT_NEAR(circuit.track2_voltage(angle_at_4v5), 0.55, 0.15);
}
