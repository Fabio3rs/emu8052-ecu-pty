#include "lab/AnalogTrigger.hpp"
#include "lab/DigitalPulseMeasurements.hpp"
#include "lab/DigitalScopeExport.hpp"
#include "lab/DrivetrainExport.hpp"
#include "lab/ScopeCursor.hpp"
#include "lab/SevelGeometry.hpp"
#include "lab/SevelTransmission.hpp"
#include "lab/SevelValves.hpp"

#include "lab/CylinderLabels.hpp"
#include "lab/SpeedReading.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <sstream>

namespace {

constexpr double pi = 3.14159265358979323846;

TEST(DrivetrainExport,
     PreservesReverseAndSignedTorqueWithExplicitAvailability) {
    ma17::EmulatorSnapshot sample;
    sample.drivetrain_available = true;
    sample.vehicle_speed_available = true;
    sample.vehicle_speed_kmh = -12.5;
    sample.transmission_gear = -1;
    sample.clutch_pressure = 0.25;
    sample.clutch_crank_torque_nm = -45.5;
    sample.clutch_heat_j = 123.75;
    std::ostringstream row;
    lab::write_drivetrain_csv_row(row, sample);
    EXPECT_EQ(row.str(), ",1,-12.5,-1,0.25,-45.5,123.75");
    std::ostringstream header;
    lab::write_drivetrain_csv_header(header);
    EXPECT_NE(header.str().find("physical_vehicle_speed_kmh"),
              std::string::npos);
    EXPECT_NE(header.str().find("clutch_heat_J"), std::string::npos);
}

TEST(DrivetrainExport, MissingOrInvalidValuesRemainEmpty) {
    ma17::EmulatorSnapshot sample;
    sample.vehicle_speed_kmh =
        100.0; // Scenario input is not physical evidence.
    std::ostringstream missing;
    lab::write_drivetrain_csv_row(missing, sample);
    EXPECT_EQ(missing.str(), ",0,,,,,");
    sample.drivetrain_available = true;
    sample.transmission_gear = 6;
    sample.clutch_pressure = 2.0;
    sample.clutch_crank_torque_nm = std::numeric_limits<double>::quiet_NaN();
    sample.clutch_heat_j = -1.0;
    std::ostringstream invalid;
    lab::write_drivetrain_csv_row(invalid, sample);
    EXPECT_EQ(invalid.str(), ",1,,,,,");
}

TEST(SevelTransmission, RecomputesOverallRatiosFromGearAndFinalDrive) {
    constexpr std::array<double, 5> expected{15.3916875, 8.812125, 6.0676875,
                                             4.55175, 3.5083125};
    EXPECT_DOUBLE_EQ(lab::transmission::final_drive_ratio, 3.9375);
    EXPECT_DOUBLE_EQ(lab::transmission::overall_ratio(0), 0.0);
    EXPECT_DOUBLE_EQ(lab::transmission::overall_ratio(6), 0.0);
    for (int gear = 1; gear <= 5; ++gear)
        EXPECT_NEAR(lab::transmission::overall_ratio(gear),
                    expected[static_cast<std::size_t>(gear - 1)], 1e-9);
}

TEST(SevelTransmission, ReverseSpeedShowsMagnitudeWithRMarker) {
    const auto reverse = lab::speed_reading(-12.4, "KM/H");
    EXPECT_TRUE(reverse.reversing);
    EXPECT_DOUBLE_EQ(reverse.dial_value, 12.4); // never a negative needle value
    EXPECT_EQ(reverse.text, "R 12 KM/H");
    const auto forward = lab::speed_reading(37.6, "KM/H");
    EXPECT_FALSE(forward.reversing);
    EXPECT_EQ(forward.text, "38 KM/H");
    // Standing still and a nonfinite value are not "reverse".
    EXPECT_FALSE(lab::speed_reading(0.0, "KM/H").reversing);
    EXPECT_FALSE(lab::speed_reading(-0.0, "KM/H").reversing);
    EXPECT_FALSE(lab::speed_reading(std::nan(""), "KM/H").reversing);
}

TEST(SevelTransmission, ManualPagesDisagreeForGears3To5) {
    // Fiat Tipo manual B.500.837 p. 21 ("Relacao nas rodas"), transcribed from
    // PhotosECU/manual_cambio_2.png; see docs/SEVEL_LAB_CHANNEL_MAP.md.
    constexpr std::array<double, 5> manual_wheel_ratio{15.393, 8.813, 5.784,
                                                       4.107, 3.343};
    for (int gear : {1, 2})
        EXPECT_NEAR(lab::transmission::overall_ratio(gear),
                    manual_wheel_ratio[static_cast<std::size_t>(gear - 1)],
                    0.005)
            << "gear " << gear;
    EXPECT_NEAR(-lab::transmission::overall_ratio(-1), 15.393, 0.005);
    // Gears 3-5: the code follows p. 20 (1.541/1.156/0.891) but p. 21 implies
    // 1.469/1.043/0.849. The gap is intentional until the owner chooses; when
    // the ratios are changed this test must be updated together with a new
    // physical baseline.
    for (int gear : {3, 4, 5}) {
        const double gap =
            lab::transmission::overall_ratio(gear) -
            manual_wheel_ratio[static_cast<std::size_t>(gear - 1)];
        // 0.28 / 0.45 / 0.17: far above the manual's 3-decimal rounding.
        EXPECT_GT(gap, 0.1) << "gear " << gear;
    }
}

TEST(SevelTransmission, CalculatesIdealWheelRpmWithoutRoadSpeedClaim) {
    EXPECT_DOUBLE_EQ(*lab::transmission::wheel_rpm(0.0, 1), 0.0);
    EXPECT_FALSE(lab::transmission::wheel_rpm(1000.0, 0).has_value());
    EXPECT_FALSE(lab::transmission::wheel_rpm(1000.0, 6).has_value());
    EXPECT_FALSE(lab::transmission::wheel_rpm(-100.0, 1).has_value());
    EXPECT_FALSE(lab::transmission::wheel_rpm(
                     std::numeric_limits<double>::quiet_NaN(), 1)
                     .has_value());
    EXPECT_FALSE(
        lab::transmission::wheel_rpm(std::numeric_limits<double>::infinity(), 1)
            .has_value());
    EXPECT_NEAR(*lab::transmission::wheel_rpm(1000.0, 1), 1000.0 / 15.3916875,
                1e-9);
    EXPECT_NEAR(*lab::transmission::wheel_rpm(1000.0, 5), 1000.0 / 3.5083125,
                1e-9);
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
    EXPECT_FALSE(lab::transmission::ideal_speed_kmh(
        1000.0, 1, std::numeric_limits<double>::quiet_NaN()));
}

TEST(SevelTransmission, ReflectedInertiaPreservesVehicleEnergyAcrossGears) {
    // Fixture mass, not a claimed Fiat curb weight. Preserve road speed
    // during shifts by changing shaft speed along with reflected inertia.
    constexpr double mass = 1000.0, radius = 0.29, speed = 20.0;
    for (const int gear : {-1, 1, 2, 3, 4, 5}) {
        const auto inertia =
            engine::transmission::reflected_inertia_kg_m2(mass, gear, radius);
        ASSERT_TRUE(inertia);
        const double omega =
            speed * engine::transmission::overall_ratio(gear) / radius;
        EXPECT_NEAR(0.5 * *inertia * omega * omega, 0.5 * mass * speed * speed,
                    1e-8);
        for (const double force : {-1000.0, 0.0, 1000.0}) {
            const auto torque =
                engine::transmission::reflected_torque_nm(force, gear, radius);
            ASSERT_TRUE(torque);
            EXPECT_NEAR(*torque * omega, force * speed, 1e-9);
        }
    }
}

TEST(SevelTransmission, ReflectedLoadsRejectDisconnectedAndInvalidInputs) {
    using engine::transmission::reflected_inertia_kg_m2;
    using engine::transmission::reflected_torque_nm;
    for (const int gear : {0, -2, 6}) {
        EXPECT_FALSE(reflected_inertia_kg_m2(1000.0, gear, 0.29));
        EXPECT_FALSE(reflected_torque_nm(1000.0, gear, 0.29));
    }
    for (const double invalid :
         {0.0, -1.0, std::numeric_limits<double>::quiet_NaN(),
          std::numeric_limits<double>::infinity()}) {
        EXPECT_FALSE(reflected_inertia_kg_m2(invalid, 1, 0.29));
        EXPECT_FALSE(reflected_inertia_kg_m2(1000.0, 1, invalid));
        EXPECT_FALSE(reflected_torque_nm(1000.0, 1, invalid));
    }
    EXPECT_FALSE(
        reflected_torque_nm(std::numeric_limits<double>::quiet_NaN(), 1, 0.29));
    EXPECT_FALSE(
        reflected_torque_nm(std::numeric_limits<double>::infinity(), 1, 0.29));
}

TEST(SevelTransmission, ReverseChangesDirectionWithoutNegativeInertia) {
    using namespace engine::transmission;
    EXPECT_DOUBLE_EQ(overall_ratio(-1), -15.3916875);
    const auto forward = ideal_speed_kmh(1000.0, 1, 0.29);
    const auto reverse = ideal_speed_kmh(1000.0, -1, 0.29);
    ASSERT_TRUE(forward);
    ASSERT_TRUE(reverse);
    EXPECT_DOUBLE_EQ(*reverse, -*forward);
    EXPECT_LT(*wheel_rpm(1000.0, -1), 0.0);
    EXPECT_GT(*reflected_inertia_kg_m2(1000.0, -1, 0.29), 0.0);
    // A positive road force brakes a reversing vehicle and opposes the
    // positive engine shaft rotation through the negative ratio.
    EXPECT_LT(*reflected_torque_nm(1000.0, -1, 0.29), 0.0);
    EXPECT_FALSE(ideal_speed_kmh(std::numeric_limits<double>::max(), -1,
                                 std::numeric_limits<double>::max()));
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
    EXPECT_EQ(lab::nearest_scope_sample(samples, 900000, 0, 900000), 3U);
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
    EXPECT_EQ(
        lab::format_scope_cursor_delta(990000LL, 1485000LL, first, last, units),
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
    EXPECT_EQ(lab::nearest_digital_edge(events, 1, 101, 0, 200, 10)->tick, 102);
}

TEST(DigitalPulseMeasurements, IdleCursorUsesFirstValidChangedSample) {
    std::array<ma17::EmulatorSnapshot, 8> history{};
    constexpr std::array<long long, 8> ticks{10, 20,     30,     40,
                                             50, 300000, 300010, 300020};
    constexpr std::array<bool, 8> closed{false, false, true, false,
                                         true,  false, true, false};
    for (std::size_t i = 0; i < history.size(); ++i) {
        history[i].tick = ticks[i];
        history[i].throttle_available = true;
        history[i].idle_contact_closed = closed[i];
    }
    history[3].throttle_available = false;
    const auto closed_edge =
        lab::nearest_idle_sample_transition(history, 29, 0, 50, 10);
    ASSERT_TRUE(closed_edge.has_value());
    EXPECT_EQ(closed_edge->tick, 30);
    EXPECT_TRUE(closed_edge->high);
    EXPECT_FALSE(
        lab::nearest_idle_sample_transition(history, 50, 0, 50, 0).has_value());
    EXPECT_FALSE(
        lab::nearest_idle_sample_transition(history, 300000, 0, 300000, 0)
            .has_value());
    const auto reopened =
        lab::nearest_idle_sample_transition(history, 300020, 300015, 300020, 0);
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
    const auto rows = lab::selected_digital_records(events, history, 100, 180);
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
    constexpr std::array<long long, 8> ticks{10, 20,     30,     40,
                                             50, 400000, 400010, 400020};
    for (std::size_t i = 0; i < samples.size(); ++i) {
        samples[i].tick = ticks[i];
        samples[i].tps_track1_v = values[i];
        samples[i].tps_available = true;
    }
    const auto value_of =
        [](const ma17::EmulatorSnapshot &sample) -> std::optional<double> {
        if (!sample.tps_available)
            return std::nullopt;
        return sample.tps_track1_v;
    };
    using lab::TriggerSlope;
    EXPECT_EQ(lab::latest_analog_trigger(samples, value_of, 1.0,
                                         TriggerSlope::Rising, 0, 50),
              40);
    EXPECT_EQ(lab::latest_analog_trigger(samples, value_of, 1.0,
                                         TriggerSlope::Falling, 0, 50),
              50);
    EXPECT_EQ(lab::latest_analog_trigger(samples, value_of, 1.0,
                                         TriggerSlope::Rising, 41, 400010),
              std::nullopt);
    samples[2].tps_available = false;
    EXPECT_EQ(lab::latest_analog_trigger(samples, value_of, 1.0,
                                         TriggerSlope::Rising, 21, 40),
              std::nullopt);
    EXPECT_EQ(lab::latest_analog_trigger(
                  samples, value_of, std::numeric_limits<double>::quiet_NaN(),
                  TriggerSlope::Rising, 0, 50),
              std::nullopt);
}

TEST(AnalogTrigger, SingleSelectsFirstEligibleCrossingAcrossFrameBatches) {
    std::array<ma17::EmulatorSnapshot, 8> samples{};
    std::array<ma17::EmulatorEvent, 4> events{};
    for (std::size_t i = 0; i < samples.size(); ++i) {
        samples[i].tick = static_cast<long long>(i + 1) * 10;
        samples[i].tps_track1_v = i % 2 == 0 ? 0.0 : 2.0;
    }
    for (std::size_t i = 0; i < events.size(); ++i)
        events[i] = {static_cast<long long>(i + 1) * 20,
                     ma17::EmulatorEventType::IgnitionPin, 0, true};
    const auto value =
        [](const ma17::EmulatorSnapshot &sample) -> std::optional<double> {
        return sample.tps_track1_v;
    };
    for (const long long frame_end : {40LL, 60LL, 80LL}) {
        // Armed after tick 20: first eligible edge is 40 even if a slow
        // renderer receives several crossings together in a later frame.
        EXPECT_EQ(lab::find_analog_trigger(
                      samples, value, 1.0, lab::TriggerSlope::Rising, 21,
                      frame_end, 247500, lab::TriggerOccurrence::First),
                  40);
        EXPECT_EQ(
            lab::find_event_trigger(events, lab::EventTriggerSource::Ignition0,
                                    lab::TriggerSlope::Rising, 21, frame_end,
                                    lab::TriggerOccurrence::First),
            40);
        EXPECT_EQ(lab::latest_analog_trigger(samples, value, 1.0,
                                             lab::TriggerSlope::Rising, 21,
                                             frame_end),
                  frame_end);
        EXPECT_EQ(lab::latest_event_trigger(
                      events, lab::EventTriggerSource::Ignition0,
                      lab::TriggerSlope::Rising, 21, frame_end),
                  frame_end);
    }
    samples[3].tps_track1_v = std::numeric_limits<double>::quiet_NaN();
    EXPECT_EQ(lab::find_analog_trigger(samples, value, 1.0,
                                       lab::TriggerSlope::Rising, 21, 80,
                                       247500, lab::TriggerOccurrence::First),
              60);
    EXPECT_EQ(lab::find_analog_trigger(samples, value, 1.0,
                                       lab::TriggerSlope::Falling, 21, 80,
                                       247500, lab::TriggerOccurrence::First),
              30);
}

TEST(AnalogTrigger, PreTriggerPlacesTheEventAtTheConfiguredFractionOfTheView) {
    constexpr long long span = 990000; // 1 s view
    for (const double pre_fraction : {0.10, 0.25, 0.50}) {
        const auto w =
            lab::trigger_search_window(span, pre_fraction, 0, 10 * span, 0);
        EXPECT_EQ(w.pre_ticks + w.post_ticks, span) << pre_fraction;
        // An event at tick T is shown with T - pre_ticks as the first tick of
        // the view, i.e. at pre_fraction of the span from its left edge.
        const long long event = 5 * span;
        const long long view_end = event + w.post_ticks;
        const long long view_first = view_end - span;
        EXPECT_NEAR(static_cast<double>(event - view_first) / span,
                    pre_fraction, 1e-6);
        // The latest eligible event leaves exactly `post_ticks` of data.
        EXPECT_EQ(w.last_candidate, 10 * span - w.post_ticks);
    }
    // Invalid fractions fall back to the 25 % default instead of escaping the
    // view.
    const auto bad =
        lab::trigger_search_window(span, std::nan(""), 0, 10 * span, 0);
    EXPECT_EQ(bad.pre_ticks, span / 4);
    EXPECT_EQ(lab::trigger_search_window(span, 1.5, 0, 10 * span, 0).pre_ticks,
              span / 4);
}

TEST(AnalogTrigger,
     RearmingWhilePausedLeavesNoEligibleCrossingUntilNewDataArrives) {
    constexpr long long span = 990000;
    constexpr long long paused_tick = 8 * span;
    const auto before =
        lab::trigger_search_window(span, 0.25, 0, paused_tick, 0);
    EXPECT_FALSE(before.empty());
    // Re-arm at the paused tick: nothing already recorded is eligible, and a
    // paused clock cannot make anything eligible.
    for (int repeat = 0; repeat < 3; ++repeat) {
        const auto armed =
            lab::trigger_search_window(span, 0.25, 0, paused_tick, paused_tick);
        EXPECT_TRUE(armed.empty());
        EXPECT_EQ(armed.first_candidate, paused_tick);
    }
    // Only after `post_ticks` of new data does the window open again.
    const auto later = lab::trigger_search_window(
        span, 0.25, 0, paused_tick + before.post_ticks + 1, paused_tick);
    EXPECT_FALSE(later.empty());
    // A history that starts late limits the first candidate (acquisition
    // limit).
    const auto limited =
        lab::trigger_search_window(span, 0.25, 7 * span, paused_tick, 0);
    EXPECT_GE(limited.first_candidate, 7 * span + limited.pre_ticks);
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
                                        TriggerSlope::Rising, 0, 70),
              10);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Ignition0,
                                        TriggerSlope::Falling, 0, 70),
              20);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Ignition1,
                                        TriggerSlope::Rising, 0, 70),
              30);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Injector,
                                        TriggerSlope::Falling, 0, 70),
              50);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Spark14,
                                        TriggerSlope::Falling, 0, 70),
              60);
    EXPECT_EQ(lab::latest_event_trigger(events, EventTriggerSource::Spark23,
                                        TriggerSlope::Rising, 0, 70),
              70);
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
    EXPECT_THROW(
        lab::cylinder_pose(std::numeric_limits<double>::quiet_NaN(), 1),
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
    EXPECT_THROW(
        lab::valve_lift_fraction(0.0, 0, lab::ValveKind::Intake,
                                 std::numeric_limits<double>::quiet_NaN()),
        std::invalid_argument);
}

} // namespace

TEST(CylinderLabels, FocusLabelNamesTheSelectedCylinderOnly) {
    for (int cylinder = 1; cylinder <= 4; ++cylinder) {
        EXPECT_EQ(lab::cylinder_focus_label(cylinder),
                  "CYL " + std::to_string(cylinder) + " VIEW");
        EXPECT_EQ(lab::cylinder_focus_label(cylinder, true),
                  "CYL " + std::to_string(cylinder) + " VIEW | ");
    }
    for (const int none : {0, -1, 5, 99})
        EXPECT_TRUE(lab::cylinder_focus_label(none).empty()) << none;
}

TEST(CylinderLabels, IgnitionPairsFollowTheFiringOrder1342) {
    EXPECT_EQ(lab::firing_order, (std::array<int, 4>{1, 3, 4, 2}));
    EXPECT_EQ(lab::ignition_pair_of_cylinder(1), 0);
    EXPECT_EQ(lab::ignition_pair_of_cylinder(4), 0);
    EXPECT_EQ(lab::ignition_pair_of_cylinder(2), 1);
    EXPECT_EQ(lab::ignition_pair_of_cylinder(3), 1);
    EXPECT_EQ(lab::ignition_pair_of_cylinder(0), -1);
    EXPECT_STREQ(lab::ignition_pair_label(0), "1/4");
    EXPECT_STREQ(lab::ignition_pair_label(1), "2/3");
    // Wasted spark: consecutive cylinders in the firing order alternate coils.
    for (std::size_t i = 0; i < lab::firing_order.size(); ++i)
        EXPECT_NE(lab::ignition_pair_of_cylinder(lab::firing_order[i]),
                  lab::ignition_pair_of_cylinder(
                      lab::firing_order[(i + 1) % lab::firing_order.size()]));
}
