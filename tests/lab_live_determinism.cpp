#include "lab/SimSession.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <string>
#include <thread>
#include <vector>

int main(int argc, char **argv) {
    if (argc != 2)
        return 2;
    std::vector<std::string> args{"lab_live_determinism",
                             argv[1],
                             "--physical-crank",
                             "--stop-ticks",
                             "10000000",
                             "--starter-ticks",
                             "495000",
                             "--adc7-mv",
                             "1232",
                             "--idle-bridge-p15-p16",
                             "--idle-contact-p46",
                             "--coolant-c",
                             "90",
                             "--idle-min-stop-mrad",
                             "5",
                             "--throttle-leak-mm2",
                             "8" /* BENCH_LEAK_MM2, see tests/sevel_preset.py */,
                             "--load-step-tick",
                             "800000",
                             "--load-nm",
                             "24",
                             "--lambda-adc-gain",
                             "5"};
    lab::SimSession session(args);
    session.set_speed(16.0);
    session.start();
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(120);
    while (!session.finished() && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    if (!session.finished()) {
        session.stop();
        return 1;
    }
    ma17::EmulatorSnapshot snapshot;
    if (!session.latest(snapshot) || session.result() != 0 ||
        snapshot.tick != 10000000 ||
        // Running-engine behaviour, not golden values. Exact reproducibility
        // is checked below by comparing independent runs sample by sample.
        // (Former goldens 513.626 rpm / RAM47 20 / 167 pulses described the
        // engine before friction, pumping and series-motor starter changes.)
        snapshot.rpm < 300.0 || snapshot.rpm > 1200.0 || snapshot.ram47 == 0 ||
        std::abs(static_cast<double>(snapshot.ram47) * 25.0 - snapshot.rpm) >
            75.0 ||
        snapshot.injector_pulses < 50 ||
        !snapshot.crank_available || !snapshot.throttle_available ||
        !snapshot.tps_available || !snapshot.thermal_available ||
        !snapshot.injector_available ||
        session.events().empty() || session.event_overflow() != 0)
        return 1;
    const auto history = session.snapshot_window(9000000);
    if (history.size() < 2 || history.front().tick < 9000000 ||
        history.back().tick != snapshot.tick ||
        !history.back().intake_available ||
        history.back().manifold_pressure_pa <= 0.0 ||
        history.back().injected_fuel_total_kg <= 0.0)
        return 1;
    for (std::size_t index = 1; index < history.size(); ++index) {
        if (history[index].tick <= history[index - 1].tick)
            return 1;
    }
    const auto full_history = session.snapshot_window(0);
    const auto retention = session.snapshot_retention();
    if (full_history.empty() || full_history.front().tick > 99000 ||
        full_history.back().tick != snapshot.tick ||
        full_history.size() <= history.size() ||
        retention.raw_evicted == 0 || retention.archive_evicted != 0)
        return 1;
    for (std::size_t index = 1; index < full_history.size(); ++index) {
        if (full_history[index].tick <= full_history[index - 1].tick)
            return 1;
    }
    args[4] = "1500000";
    lab::SimSession reference(args);
    reference.set_speed(16.0);
    reference.start();
    const auto reference_deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(20);
    while (!reference.finished() &&
           std::chrono::steady_clock::now() < reference_deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    if (!reference.finished() || reference.result() != 0) {
        reference.stop();
        return 1;
    }
    const auto raw = reference.snapshot_window(0);
    const auto reference_events = reference.events();
    for (const int poll_ms : {8, 32}) {
        lab::SimSession polled(args);
        polled.set_speed(16.0);
        polled.start();
        const auto poll_deadline =
            std::chrono::steady_clock::now() + std::chrono::seconds(20);
        while (!polled.finished() &&
               std::chrono::steady_clock::now() < poll_deadline) {
            ma17::EmulatorSnapshot observed;
            polled.latest(observed);
            std::this_thread::sleep_for(std::chrono::milliseconds(poll_ms));
        }
        if (!polled.finished() || polled.result() != 0)
            return 1;
        const auto observed = polled.snapshot_window(0);
        if (observed.size() != raw.size()) {
            std::fprintf(stderr,
                         "[SCOPE-CADENCE] poll=%d size=%zu expected=%zu\n",
                         poll_ms, observed.size(), raw.size());
            return 1;
        }
        for (std::size_t index = 0; index < raw.size(); ++index) {
            const auto &a = raw[index];
            const auto &b = observed[index];
            if (a.tick != b.tick || a.rpm != b.rpm ||
                a.lambda != b.lambda ||
                a.lambda_voltage_v != b.lambda_voltage_v ||
                a.tps_track1_v != b.tps_track1_v ||
                a.tps_track2_v != b.tps_track2_v ||
                a.throttle_angle_rad != b.throttle_angle_rad ||
                a.pedal_pull_m != b.pedal_pull_m ||
                a.coolant_c != b.coolant_c ||
                a.intake_air_c != b.intake_air_c ||
                a.thermostat_open_fraction != b.thermostat_open_fraction ||
                a.radiator_fan_on != b.radiator_fan_on ||
                a.manifold_pressure_pa != b.manifold_pressure_pa ||
                a.air_in_kg_s != b.air_in_kg_s ||
                a.applied_load_nm != b.applied_load_nm ||
                a.battery_supply_v != b.battery_supply_v ||
                a.injected_fuel_total_kg != b.injected_fuel_total_kg ||
                a.fuel_film_kg != b.fuel_film_kg ||
                a.fuel_vapor_kg != b.fuel_vapor_kg ||
                a.idle_stem_m != b.idle_stem_m ||
                a.idle_contact_closed != b.idle_contact_closed ||
                a.exhaust_sample_available != b.exhaust_sample_available ||
                a.crank_available != b.crank_available ||
                a.throttle_available != b.throttle_available ||
                a.tps_available != b.tps_available ||
                a.thermal_available != b.thermal_available ||
                a.intake_available != b.intake_available ||
                a.idle_bridge_candidate != b.idle_bridge_candidate ||
                a.battery_supply_available != b.battery_supply_available ||
                a.cc3_high != b.cc3_high || a.p50_high != b.p50_high ||
                a.p51_high != b.p51_high) {
                std::fprintf(stderr,
                             "[SCOPE-CADENCE] poll=%d mismatch=%zu tick=%lld/%lld\n",
                             poll_ms, index, a.tick, b.tick);
                return 1;
            }
            for (std::size_t channel = 0;
                 channel < a.adc_last_conversion.size(); ++channel) {
                const auto &adc_a = a.adc_last_conversion[channel];
                const auto &adc_b = b.adc_last_conversion[channel];
                if (adc_a.tick != adc_b.tick ||
                    adc_a.pin_voltage_v != adc_b.pin_voltage_v ||
                    adc_a.count != adc_b.count ||
                    adc_a.sampled != adc_b.sampled ||
                    adc_a.voltage_available != adc_b.voltage_available)
                    return 1;
            }
        }
        const auto observed_events = polled.events();
        if (observed_events.size() != reference_events.size())
            return 1;
        for (std::size_t index = 0; index < reference_events.size(); ++index) {
            const auto &a = reference_events[index];
            const auto &b = observed_events[index];
            if (a.tick != b.tick || a.type != b.type ||
                a.channel != b.channel || a.high != b.high ||
                a.rpm != b.rpm || a.crank_angle_rad != b.crank_angle_rad)
                return 1;
        }
        std::printf("[SCOPE-CADENCE] poll=%d samples=%zu events=%zu\n",
                    poll_ms, observed.size(), observed_events.size());
    }
    struct Field {
        double ma17::EmulatorSnapshot::*value;
        bool ma17::EmulatorSnapshot::*available;
        bool requires_exhaust_sample = false;
    };
    constexpr std::array<Field, 7> fields{{
        {&ma17::EmulatorSnapshot::rpm, &ma17::EmulatorSnapshot::crank_available},
        {&ma17::EmulatorSnapshot::lambda,
         &ma17::EmulatorSnapshot::crank_available, true},
        {&ma17::EmulatorSnapshot::tps_track1_v, &ma17::EmulatorSnapshot::tps_available},
        {&ma17::EmulatorSnapshot::coolant_c, &ma17::EmulatorSnapshot::thermal_available},
        {&ma17::EmulatorSnapshot::manifold_pressure_pa,
         &ma17::EmulatorSnapshot::intake_available},
        {&ma17::EmulatorSnapshot::fuel_film_kg,
         &ma17::EmulatorSnapshot::intake_available},
        {&ma17::EmulatorSnapshot::idle_stem_m,
         &ma17::EmulatorSnapshot::idle_bridge_candidate}}};
    for (const auto field : fields) {
        const ma17::EmulatorSnapshot *minimum = nullptr;
        const ma17::EmulatorSnapshot *maximum = nullptr;
        for (const auto &sample : raw) {
            if (sample.tick >= 990000)
                break;
            const double value = sample.*field.value;
            if (!(sample.*field.available) ||
                (field.requires_exhaust_sample && !sample.exhaust_sample_available) ||
                !std::isfinite(value))
                continue;
            if (!minimum || value < minimum->*field.value)
                minimum = &sample;
            if (!maximum || value > maximum->*field.value)
                maximum = &sample;
        }
        if (!minimum || !maximum) {
            std::fprintf(stderr, "[ARCHIVE] field has no valid early sample\n");
            return 1;
        }
        // The archive keeps the extrema of each 100 ms bucket, and a bucket
        // may straddle the 990000-tick cut used above, so the exact sample of
        // the first-second peak can be replaced by a bucket neighbour that is
        // at least as extreme. Require that: an archived sample within one
        // bucket (+0.5 ms sampling) that is >= the maximum / <= the minimum.
        constexpr long long bucket_ticks = 99000 + 1000;
        for (const bool is_max : {true, false}) {
            const auto *peak = is_max ? maximum : minimum;
            const bool retained = std::any_of(
                full_history.begin(), full_history.end(),
                [&](const auto &sample) {
                    if (sample.tick < peak->tick - bucket_ticks ||
                        sample.tick > peak->tick + bucket_ticks ||
                        !(sample.*field.available) ||
                        (field.requires_exhaust_sample &&
                         !sample.exhaust_sample_available) ||
                        !std::isfinite(sample.*field.value))
                        return false;
                    return is_max ? sample.*field.value >=
                                        peak->*field.value
                                  : sample.*field.value <=
                                        peak->*field.value;
                });
            if (!retained) {
                std::fprintf(stderr,
                             "[ARCHIVE] %s at tick %lld value=%.9g lost\n",
                             is_max ? "maximum" : "minimum", peak->tick,
                             peak->*field.value);
                return 1;
            }
        }
    }
    constexpr std::array<std::size_t, 6> adc_channels{0, 1, 2, 3, 5, 6};
    for (const std::size_t channel : adc_channels) {
        const ma17::EmulatorSnapshot *minimum = nullptr;
        const ma17::EmulatorSnapshot *maximum = nullptr;
        for (const auto &sample : raw) {
            if (sample.tick >= 990000)
                break;
            const auto &adc = sample.adc_last_conversion[channel];
            if (!adc.sampled || !adc.voltage_available ||
                adc.tick > static_cast<std::uint64_t>(sample.tick) ||
                static_cast<std::uint64_t>(sample.tick) - adc.tick > 99000 ||
                !std::isfinite(adc.pin_voltage_v))
                continue;
            if (!minimum || adc.pin_voltage_v <
                                minimum->adc_last_conversion[channel].pin_voltage_v)
                minimum = &sample;
            if (!maximum || adc.pin_voltage_v >
                                maximum->adc_last_conversion[channel].pin_voltage_v)
                maximum = &sample;
        }
        if (!minimum || !maximum) {
            std::fprintf(stderr, "[ADC-ARCHIVE] channel=%zu no valid early sample\n",
                         channel);
            return 1;
        }
        for (const auto *peak : {minimum, maximum}) {
            const auto &expected = peak->adc_last_conversion[channel];
            const bool retained = std::any_of(
                full_history.begin(), full_history.end(),
                [&](const auto &sample) {
                    const auto &adc = sample.adc_last_conversion[channel];
                    return sample.tick < 990000 && adc.sampled &&
                           adc.voltage_available &&
                           adc.tick == expected.tick &&
                           adc.pin_voltage_v == expected.pin_voltage_v;
                });
            if (!retained) {
                std::fprintf(stderr,
                             "[ADC-ARCHIVE] channel=%zu missing conversion=%llu voltage=%.6f\n",
                             channel, static_cast<unsigned long long>(expected.tick),
                             expected.pin_voltage_v);
                return 1;
            }
        }
    }
    std::printf("[LAB-DETERMINISM] tick=%lld rpm=%.3f ram47=%u "
                "cc3=%llu events=%zu\n",
                snapshot.tick, snapshot.rpm,
                static_cast<unsigned>(snapshot.ram47), snapshot.injector_pulses,
                session.events().size());
    return 0;
}
