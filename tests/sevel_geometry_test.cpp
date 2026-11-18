#include "lab/AnalogTrigger.hpp"
#include "lab/DigitalPulseMeasurements.hpp"
#include "lab/DigitalScopeExport.hpp"
#include "lab/ScopeCursor.hpp"
#include "lab/SevelGeometry.hpp"
#include "lab/SevelTransmission.hpp"
#include "lab/SevelValves.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <limits>

namespace {

constexpr double pi = 3.14159265358979323846;

TEST(SevelTransmission, RecomputesOverallRatiosFromGearAndFinalDrive) {
    constexpr std::array<double, 5> expected{
        15.3916875, 8.812125, 6.0676875, 4.55175, 3.5083125};
    EXPECT_DOUBLE_EQ(lab::transmission::final_drive_ratio, 3.9375);
    EXPECT_DOUBLE_EQ(lab::transmission::overall_ratio(0), 0.0);
    EXPECT_DOUBLE_EQ(lab::transmission::overall_ratio(6), 0.0);
    for (int gear = 1; gear <= 5; ++gear)
        EXPECT_NEAR(lab::transmission::overall_ratio(gear),
                    expected[static_cast<std::size_t>(gear - 1)], 1e-9);
}

TEST(SevelTransmission, CalculatesIdealWheelRpmWithoutRoadSpeedClaim) {
    EXPECT_DOUBLE_EQ(*lab::transmission::wheel_rpm(0.0, 1), 0.0);
    EXPECT_FALSE(lab::transmission::wheel_rpm(1000.0, 0).has_value());
    EXPECT_FALSE(lab::transmission::wheel_rpm(1000.0, 6).has_value());
    EXPECT_FALSE(lab::transmission::wheel_rpm(-100.0, 1).has_value());
    EXPECT_FALSE(lab::transmission::wheel_rpm(
        std::numeric_limits<double>::quiet_NaN(), 1).has_value());
    EXPECT_FALSE(lab::transmission::wheel_rpm(
        std::numeric_limits<double>::infinity(), 1).has_value());
    EXPECT_NEAR(*lab::transmission::wheel_rpm(1000.0, 1),
                1000.0 / 15.3916875, 1e-9);
    EXPECT_NEAR(*lab::transmission::wheel_rpm(1000.0, 5),
                1000.0 / 3.5083125, 1e-9);
}

TEST(SevelTransmission, CalculatesEngagedClutchSpeedReference) {
    constexpr double radius = lab::transmission::reference_tire_radius_m;
    const double wheel = *lab::transmission::wheel_rpm(1000.0, 1);
    EXPECT_NEAR(*lab::transmission::ideal_speed_kmh(1000.0, 1, radius),
                wheel * 2.0 * pi * radius * 60.0 / 1000.0, 1e-12);
    EXPECT_FALSE(lab::transmission::ideal_speed_kmh(1000.0, 0, radius));
    EXPECT_FALSE(lab::transmission::ideal_speed_kmh(1000.0, 1, 0.0));
    EXPECT_FALSE(lab::transmission::ideal_speed_kmh(
        std::numeric_limits<double>::infinity(), 1, radius));
    EXPECT_FALSE(lab::transmission::ideal_speed_kmh(1000.0, 1,
        std::numeric_limits<double>::quiet_NaN()));
}

TEST(ScopeCursor, SelectsRecordedSampleInsideVisibleWindow) {
    std::array<ma17::EmulatorSnapshot, 4> samples{};
    constexpr std::array<long long, 4> ticks{100, 200, 300, 900000};
    constexpr std::array<double, 4> voltages{1.0, 2.0, 3.0, 4.0};
    for (std::size_t i = 0; i < samples.size(); ++i) {
        samples[i].tick = ticks[i];
        samples[i].tps_track1_v = voltages[i];
    }
    const auto a = lab::nearest_scope_sample(samples, 251, 200, 300);
    const auto b = lab::nearest_scope_sample(samples, 249, 200, 300);
    ASSERT_TRUE(a.has_value());
    ASSERT_TRUE(b.has_value());
    EXPECT_EQ(samples[*a].tick, 300);
    EXPECT_EQ(samples[*b].tick, 200);
    EXPECT_DOUBLE_EQ(samples[*a].tps_track1_v - samples[*b].tps_track1_v, 1.0);
    EXPECT_EQ(lab::nearest_scope_sample(samples, 199, 200, 300), std::nullopt);
    EXPECT_EQ(lab::nearest_scope_sample(samples, 250, 250, 300), 2U);
    EXPECT_EQ(lab::nearest_scope_sample(samples, 500000, 0, 900000),
              std::nullopt);
    EXPECT_EQ(lab::nearest_scope_sample(samples, 900000, 0, 900000),
              3U);
}

TEST(ScopeCursor, FormatsRecordedValuesUnitsAndMissingChannels) {
    const std::array<double, 3> first{
        1.2, std::numeric_limits<double>::quiet_NaN(), 5.0};
    const std::array<double, 3> last{1.5, 2.0, 4.5};
    constexpr std::array<const char *, 3> units{"V", "V", "deg"};
    EXPECT_EQ(lab::format_scope_cursor_row('A', 990000LL, first, units),
              "A 1.000 s  1.20V / -- / 5.00deg");
    EXPECT_EQ(lab::format_scope_cursor_row('B', 1485000LL, last, units),
              "B 1.500 s  1.50V / 2.00V / 4.50deg");
    EXPECT_EQ(lab::format_scope_cursor_row('B', std::nullopt, last, units),
              "B NO SAMPLE");
    EXPECT_EQ(lab::format_scope_cursor_delta(990000LL, 1485000LL,
                                             first, last, units),
              "DT 500.00 ms  D1 +0.30V  D2 --  D3 -0.50deg");
}

TEST(DigitalPulseMeasurements, UsesRecordedEdgesRatherThanVisualPulseWidth) {
    using ma17::EmulatorEvent;
    using ma17::EmulatorEventType;
    const std::array<EmulatorEvent, 7> events{{
        {10, EmulatorEventType::InjectorPin, 0, true},
        {11, EmulatorEventType::InjectorPin, 0, false},
        {15, EmulatorEventType::IgnitionPin, 0, true},
        {20, EmulatorEventType::InjectorPin, 0, true},
        {21, EmulatorEventType::InjectorPin, 0, false},
        {30, EmulatorEventType::InjectorPin, 0, true},
        {38, EmulatorEventType::InjectorPin, 0, false},
    }};
    const auto measured = lab::measure_digital_pulses(events, 0, 10, 38);
    ASSERT_TRUE(measured.high_ticks.has_value());
    ASSERT_TRUE(measured.cycle_high_ticks.has_value());
    ASSERT_TRUE(measured.low_ticks.has_value());
    ASSERT_TRUE(measured.period_ticks.has_value());
    ASSERT_TRUE(measured.duty_percent.has_value());
    EXPECT_EQ(*measured.high_ticks, 8);
    EXPECT_EQ(*measured.cycle_high_ticks, 1);
    EXPECT_EQ(*measured.low_ticks, 9);
    EXPECT_EQ(*measured.period_ticks, 10);
    EXPECT_DOUBLE_EQ(*measured.duty_percent, 10.0);
    const auto incomplete = lab::measure_digital_pulses(events, 0, 19, 25);
    EXPECT_EQ(incomplete.high_ticks, 1);
    EXPECT_FALSE(incomplete.low_ticks.has_value());
    EXPECT_FALSE(incomplete.period_ticks.has_value());
    EXPECT_FALSE(lab::measure_digital_pulses(events, 1, 10, 30)
                     .period_ticks.has_value());
}

TEST(DigitalPulseMeasurements, CursorSnapsToOriginalPinEdge) {
    using ma17::EmulatorEvent;
    using ma17::EmulatorEventType;
    const std::array<EmulatorEvent, 4> events{{
        {100, EmulatorEventType::InjectorPin, 0, true},
        {101, EmulatorEventType::InjectorPin, 0, false},
        {102, EmulatorEventType::IgnitionPin, 0, true},
        {200, EmulatorEventType::InjectorPin, 0, true},
    }};
    const auto a = lab::nearest_digital_edge(events, 0, 100, 0, 200, 10);
    const auto b = lab::nearest_digital_edge(events, 0, 101, 0, 200, 10);
    ASSERT_TRUE(a.has_value());
    ASSERT_TRUE(b.has_value());
    EXPECT_EQ(b->tick - a->tick, 1);
    EXPECT_TRUE(a->high);
    EXPECT_FALSE(b->high);
    EXPECT_EQ(lab::nearest_digital_edge(events, 0, 150, 0, 200, 10),
              std::nullopt);
    EXPECT_EQ(lab::nearest_digital_edge(events, 1, 101, 0, 200, 10)->tick,
              102);
}

TEST(DigitalPulseMeasurements, IdleCursorUsesFirstValidChangedSample) {
    std::array<ma17::EmulatorSnapshot, 8> history{};
    constexpr std::array<long long, 8> ticks{
        10, 20, 30, 40, 50, 300000, 300010, 300020};
    constexpr std::array<bool, 8> closed{
        false, false, true, false, true, false, true, false};
    for (std::size_t i = 0; i < history.size(); ++i) {
        history[i].tick = ticks[i];
        history[i].throttle_available = true;
        history[i].idle_contact_closed = closed[i];
    }
    history[3].throttle_available = false;
    const auto closed_edge = lab::nearest_idle_sample_transition(
        history, 29, 0, 50, 10);
    ASSERT_TRUE(closed_edge.has_value());
    EXPECT_EQ(closed_edge->tick, 30);
    EXPECT_TRUE(closed_edge->high);
    EXPECT_FALSE(lab::nearest_idle_sample_transition(
        history, 50, 0, 50, 0).has_value());
    EXPECT_FALSE(lab::nearest_idle_sample_transition(
        history, 300000, 0, 300000, 0).has_value());
    const auto reopened = lab::nearest_idle_sample_transition(
        history, 300020, 300015, 300020, 0);
    ASSERT_TRUE(reopened.has_value());
    EXPECT_EQ(reopened->tick, 300020);
    EXPECT_FALSE(reopened->high);
}

TEST(DigitalScopeExport, SelectsOriginalEventsAndObservedContactChanges) {
    using ma17::EmulatorEvent;
    using ma17::EmulatorEventType;
    const std::array<EmulatorEvent, 4> events{{
        {110, EmulatorEventType::InjectorPin, 0, true},
        {130, EmulatorEventType::Spark, 0, false},
        {140, EmulatorEventType::LampCandidate, 0, true},
        {190, EmulatorEventType::IgnitionPin, 1, false},
    }};
    std::array<ma17::EmulatorSnapshot, 5> history{};
    constexpr std::array<long long, 5> ticks{90, 120, 150, 160, 180};
    constexpr std::array<bool, 5> closed{false, true, false, true, false};
    for (std::size_t i = 0; i < history.size(); ++i) {
        history[i].tick = ticks[i];
        history[i].idle_contact_closed = closed[i];
        history[i].throttle_available = true;
    }
    history[2].throttle_available = false;
    const auto rows = lab::selected_digital_records(events, history,
                                                     100, 180);
    ASSERT_EQ(rows.size(), 4U);
    EXPECT_EQ(rows[0].tick, 110);
    EXPECT_EQ(rows[0].event->type, EmulatorEventType::InjectorPin);
    EXPECT_EQ(rows[1].tick, 120);
    EXPECT_FALSE(rows[1].event.has_value());
    EXPECT_TRUE(rows[1].contact_closed);
    EXPECT_EQ(rows[2].tick, 130);
    EXPECT_EQ(rows[2].event->type, EmulatorEventType::Spark);
    EXPECT_EQ(rows[3].tick, 180);
    EXPECT_FALSE(rows[3].event.has_value());
    EXPECT_FALSE(rows[3].contact_closed);
}

TEST(AnalogTrigger, UsesSourceTicksAndRequiresValidAdjacentSamples) {
    std::array<ma17::EmulatorSnapshot, 8> samples{};
    constexpr std::array<double, 8> values{0.2, 1.2, 0.2, 1.3,
                                            0.1, 1.4, 0.1, 1.5};
    constexpr std::array<long long, 8> ticks{10, 20, 30, 40,
                                             50, 400000, 400010, 400020};
    for (std::size_t i = 0; i < samples.size(); ++i) {
        samples[i].tick = ticks[i];
        samples[i].tps_track1_v = values[i];
        samples[i].tps_available = true;
    }
    const auto value_of = [](const ma17::EmulatorSnapshot &sample)
        -> std::optional<double> {
        if (!sample.tps_available)
            return std::nullopt;
        return sample.tps_track1_v;
    };
    using lab::TriggerSlope;
    EXPECT_EQ(lab::latest_analog_trigger(samples, value_of, 1.0,
                                         TriggerSlope::Rising, 0, 50), 40);
    EXPECT_EQ(lab::latest_analog_trigger(samples, value_of, 1.0,
                                         TriggerSlope::Falling, 0, 50), 50);
    EXPECT_EQ(lab::latest_analog_trigger(samples, value_of, 1.0,
                                         TriggerSlope::Rising, 41, 400010),
              std::nullopt);
    samples[2].tps_available = false;
    EXPECT_EQ(lab::latest_analog_trigger(samples, value_of, 1.0,
                                         TriggerSlope::Rising, 21, 40),
              std::nullopt);
    EXPECT_EQ(lab::latest_analog_trigger(samples, value_of,
                                         std::numeric_limits<double>::quiet_NaN(),
                                         TriggerSlope::Rising, 0, 50),
              std::nullopt);
}

TEST(AnalogTrigger, SelectsRecordedElectricalEdgesAndSparkPairs) {
    using ma17::EmulatorEvent;
    using ma17::EmulatorEventType;
    const std::array<EmulatorEvent, 7> events{{
        {10, EmulatorEventType::IgnitionPin, 0, true},
        {20, EmulatorEventType::IgnitionPin, 0, false},
        {30, EmulatorEventType::IgnitionPin, 1, true},
        {40, EmulatorEventType::InjectorPin, 0, true},
        {50, EmulatorEventType::InjectorPin, 0, false},
        {60, EmulatorEventType::Spark, 0, false, 0.0, 0.0, 0.0, 0, 0},
        {70, EmulatorEventType::Spark, 1, false, 0.0, 0.0, 0.0, 0, 1},
    }};
    using lab::EventTriggerSource;
    using lab::TriggerSlope;
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Ignition0,
                                        TriggerSlope::Rising, 0, 70), 10);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Ignition0,
                                        TriggerSlope::Falling, 0, 70), 20);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Ignition1,
                                        TriggerSlope::Rising, 0, 70), 30);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Injector,
                                        TriggerSlope::Falling, 0, 70), 50);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Spark14,
                                        TriggerSlope::Falling, 0, 70), 60);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Spark23,
                                        TriggerSlope::Rising, 0, 70), 70);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Spark14,
                                        TriggerSlope::Rising, 61, 70),
              std::nullopt);
}

TEST(SevelGeometry, TopBottomAndOpposedCrankPins) {
    constexpr double radius = lab::SevelVisualGeometry::crank_radius_m;
    constexpr double rod = 0.14;
    const auto top = lab::sevel_cylinder_poses(0.0);
    EXPECT_NEAR(top[0].piston_pin_y_m, rod + radius, 1e-12);
    EXPECT_NEAR(top[3].piston_pin_y_m, rod + radius, 1e-12);
    EXPECT_NEAR(top[1].piston_pin_y_m, rod - radius, 1e-12);
    EXPECT_NEAR(top[2].piston_pin_y_m, rod - radius, 1e-12);

    const auto half_turn = lab::sevel_cylinder_poses(pi);
    EXPECT_NEAR(half_turn[0].piston_pin_y_m, rod - radius, 1e-12);
    EXPECT_NEAR(half_turn[1].piston_pin_y_m, rod + radius, 1e-12);

    const auto quarter_turn = lab::sevel_cylinder_poses(pi / 2.0);
    EXPECT_NEAR(quarter_turn[0].crank_pin_x_m, radius, 1e-12);
    EXPECT_NEAR(quarter_turn[1].crank_pin_x_m, -radius, 1e-12);
    EXPECT_NEAR(quarter_turn[0].piston_pin_y_m,
                std::sqrt(rod * rod - radius * radius), 1e-12);
}

TEST(SevelGeometry, RepeatsAcrossFullFourStrokeCycle) {
    for (double angle : {0.0, pi / 2.0, pi, 2.0 * pi - 0.001}) {
        const auto first = lab::sevel_cylinder_poses(angle);
        const auto next = lab::sevel_cylinder_poses(angle + 4.0 * pi);
        for (std::size_t i = 0; i < first.size(); ++i) {
            EXPECT_NEAR(first[i].crank_pin_x_m, next[i].crank_pin_x_m, 1e-12);
            EXPECT_NEAR(first[i].piston_pin_y_m, next[i].piston_pin_y_m, 1e-12);
            EXPECT_NEAR(first[i].rod_angle_rad, next[i].rod_angle_rad, 1e-12);
        }
    }
}

TEST(SevelGeometry, RodEndpointsAndPairPhasesRemainCoherentAcross720Degrees) {
    constexpr double rod = 0.14;
    constexpr double tolerance = 1e-12;
    for (int degree = 0; degree <= 720; ++degree) {
        const double angle = static_cast<double>(degree) * pi / 180.0;
        const auto poses = lab::sevel_cylinder_poses(angle);
        for (const auto &pose : poses) {
            const double end_x =
                pose.crank_pin_x_m + rod * std::sin(pose.rod_angle_rad);
            const double end_y =
                pose.crank_pin_y_m + rod * std::cos(pose.rod_angle_rad);
            EXPECT_NEAR(end_x, 0.0, tolerance) << degree;
            EXPECT_NEAR(end_y, pose.piston_pin_y_m, tolerance) << degree;
            EXPECT_NEAR(std::hypot(-pose.crank_pin_x_m,
                                   pose.piston_pin_y_m - pose.crank_pin_y_m),
                        rod, tolerance)
                << degree;
        }
        EXPECT_NEAR(poses[0].crank_pin_x_m, poses[3].crank_pin_x_m, tolerance);
        EXPECT_NEAR(poses[0].piston_pin_y_m, poses[3].piston_pin_y_m,
                    tolerance);
        EXPECT_NEAR(poses[1].crank_pin_x_m, poses[2].crank_pin_x_m, tolerance);
        EXPECT_NEAR(poses[1].piston_pin_y_m, poses[2].piston_pin_y_m,
                    tolerance);
    }
    const auto seam_start = lab::sevel_cylinder_poses(0.0);
    const auto seam_end = lab::sevel_cylinder_poses(4.0 * pi);
    for (std::size_t index = 0; index < seam_start.size(); ++index) {
        EXPECT_NEAR(seam_start[index].piston_pin_y_m,
                    seam_end[index].piston_pin_y_m, tolerance);
        EXPECT_NEAR(seam_start[index].rod_angle_rad,
                    seam_end[index].rod_angle_rad, tolerance);
    }
}

TEST(SevelGeometry, RejectsImpossibleDimensions) {
    lab::SevelVisualGeometry geometry;
    geometry.visual_estimate_rod_length_m = 0.02;
    EXPECT_THROW(lab::cylinder_pose(0.0, 1, geometry), std::invalid_argument);
    EXPECT_THROW(lab::cylinder_pose(std::numeric_limits<double>::quiet_NaN(), 1),
                 std::invalid_argument);
    EXPECT_THROW(lab::cylinder_pose(0.0, 5), std::invalid_argument);
}

TEST(SevelValves, FiringOrderAndManualWindows) {
    EXPECT_EQ(lab::firing_tdc_degrees[0], 0.0);
    EXPECT_EQ(lab::firing_tdc_degrees[2], 180.0);
    EXPECT_EQ(lab::firing_tdc_degrees[3], 360.0);
    EXPECT_EQ(lab::firing_tdc_degrees[1], 540.0);
    for (std::size_t cylinder = 0; cylinder < 4; ++cylinder) {
        const double tdc = lab::firing_tdc_degrees[cylinder];
        const auto lift = [cylinder](double degrees, lab::ValveKind kind) {
            return lab::valve_lift_fraction(degrees * pi / 180.0, cylinder,
                                            kind);
        };
        EXPECT_GT(lift(tdc + 250.0, lab::ValveKind::Exhaust), 0.0);
        EXPECT_EQ(lift(tdc + 250.0, lab::ValveKind::Intake), 0.0);
        EXPECT_GT(lift(tdc + 450.0, lab::ValveKind::Intake), 0.0);
        EXPECT_EQ(lift(tdc + 450.0, lab::ValveKind::Exhaust), 0.0);
        EXPECT_NEAR(lift(tdc + 450.0, lab::ValveKind::Intake),
                    lift(tdc + 1170.0, lab::ValveKind::Intake), 1e-12);
    }
}

TEST(SevelValves, FollowsConfiguredPhysicalTdcReference) {
    const double reference = 120.0 * pi / 180.0;
    const double open_angle = 570.0 * pi / 180.0;
    EXPECT_NEAR(
        lab::valve_lift_fraction(open_angle, 0, lab::ValveKind::Intake,
                                 reference),
        lab::valve_lift_fraction(450.0 * pi / 180.0, 0, lab::ValveKind::Intake),
        1e-12);
    EXPECT_EQ(lab::valve_lift_fraction(450.0 * pi / 180.0, 0,
                                       lab::ValveKind::Intake, reference),
              0.0);
    EXPECT_THROW(lab::valve_lift_fraction(
                     0.0, 0, lab::ValveKind::Intake,
                     std::numeric_limits<double>::quiet_NaN()),
                 std::invalid_argument);
}

} // namespace
