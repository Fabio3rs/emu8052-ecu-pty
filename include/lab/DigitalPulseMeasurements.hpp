#pragma once

#include "ma17/EmulatorEvent.hpp"
#include "ma17/EmulatorSnapshot.hpp"

#include <optional>
#include <span>

namespace lab {

struct DigitalPulseMeasurements {
    std::optional<long long> high_ticks;
    std::optional<long long> cycle_high_ticks;
    std::optional<long long> low_ticks;
    std::optional<long long> period_ticks;
    std::optional<double> duty_percent;
};

struct DigitalScopeEdge {
    long long tick = 0;
    bool high = false;
};

struct DigitalScopeCursor {
    unsigned channel = 0;
    DigitalScopeEdge edge;
};

inline std::optional<DigitalScopeEdge> nearest_digital_edge(
    std::span<const ma17::EmulatorEvent> events, unsigned channel,
    long long target, long long first_tick, long long last_tick,
    long long max_distance_ticks) {
    if (channel > 2 || target < first_tick || target > last_tick ||
        max_distance_ticks < 0)
        return std::nullopt;
    std::optional<DigitalScopeEdge> nearest;
    long long best_distance = max_distance_ticks;
    for (const auto &event : events) {
        const bool matches = channel == 0
            ? event.type == ma17::EmulatorEventType::InjectorPin
            : event.type == ma17::EmulatorEventType::IgnitionPin &&
                  event.channel == channel - 1;
        if (!matches || event.tick < first_tick || event.tick > last_tick)
            continue;
        const long long distance = event.tick >= target
            ? event.tick - target : target - event.tick;
        if (distance <= best_distance &&
            (!nearest || distance < best_distance ||
             event.tick < nearest->tick)) {
            nearest = DigitalScopeEdge{event.tick, event.high};
            best_distance = distance;
        }
    }
    return nearest;
}

// The contact is sampled: a transition belongs to the first valid snapshot
// observing the new state, not to an inferred electrical edge.
inline std::optional<DigitalScopeEdge> nearest_idle_sample_transition(
    std::span<const ma17::EmulatorSnapshot> history, long long target,
    long long first_tick, long long last_tick, long long max_distance_ticks) {
    constexpr long long max_gap_ticks = 247500;
    if (target < first_tick || target > last_tick || max_distance_ticks < 0)
        return std::nullopt;
    std::optional<DigitalScopeEdge> nearest;
    std::optional<DigitalScopeEdge> previous;
    long long best_distance = max_distance_ticks;
    for (const auto &sample : history) {
        if (sample.tick > last_tick)
            break;
        if (sample.tick < first_tick - max_gap_ticks)
            continue;
        if (!sample.throttle_available) {
            previous.reset();
            continue;
        }
        if (previous && sample.tick > previous->tick &&
            sample.tick - previous->tick <= max_gap_ticks &&
            sample.idle_contact_closed != previous->high &&
            sample.tick >= first_tick) {
            const long long distance = sample.tick >= target
                ? sample.tick - target : target - sample.tick;
            if (distance <= best_distance &&
                (!nearest || distance < best_distance ||
                 sample.tick < nearest->tick)) {
                nearest = DigitalScopeEdge{sample.tick,
                                           sample.idle_contact_closed};
                best_distance = distance;
            }
        }
        previous = DigitalScopeEdge{sample.tick, sample.idle_contact_closed};
    }
    return nearest;
}

inline DigitalPulseMeasurements measure_digital_pulses(
    std::span<const ma17::EmulatorEvent> events, unsigned channel,
    long long first_tick, long long last_tick) {
    DigitalPulseMeasurements result;
    std::optional<long long> rise;
    std::optional<long long> fall;
    std::optional<long long> previous_edge;
    if (last_tick < first_tick || channel > 2)
        return result;
    for (const auto &event : events) {
        const bool matches = channel == 0
            ? event.type == ma17::EmulatorEventType::InjectorPin
            : event.type == ma17::EmulatorEventType::IgnitionPin &&
                  event.channel == channel - 1;
        if (!matches || event.tick < first_tick || event.tick > last_tick)
            continue;
        if (previous_edge && event.tick <= *previous_edge) {
            result = {};
            rise.reset();
            fall.reset();
        }
        previous_edge = event.tick;
        if (event.high) {
            if (fall) {
                result.low_ticks = event.tick - *fall;
                if (rise && *rise < *fall) {
                    result.period_ticks = event.tick - *rise;
                    result.cycle_high_ticks = *fall - *rise;
                    result.duty_percent = 100.0 *
                        static_cast<double>(*result.cycle_high_ticks) /
                        static_cast<double>(*result.period_ticks);
                }
            }
            rise = event.tick;
            fall.reset();
        } else if (!fall) {
            if (rise)
                result.high_ticks = event.tick - *rise;
            fall = event.tick;
        }
    }
    return result;
}

} // namespace lab
