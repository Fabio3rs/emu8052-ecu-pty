#pragma once

#include <algorithm>

#include "ma17/EmulatorEvent.hpp"
#include "ma17/EmulatorSnapshot.hpp"

#include <cmath>
#include <optional>
#include <span>

namespace lab {

enum class TriggerSlope { Rising, Falling };
enum class TriggerOccurrence { First, Latest };

// Where a trigger may fire for a view of `span` ticks showing the event at
// `pre_fraction` of the span (10 %, 25 % or 50 % in the GUI). `armed_tick` is
// the moment the trigger was (re)armed: nothing earlier is eligible.
struct TriggerSearchWindow {
    long long pre_ticks = 0;  // ticks shown before the event
    long long post_ticks = 0; // ticks shown after it
    long long first_candidate = 0;
    long long last_candidate = 0;
    bool empty() const { return first_candidate > last_candidate; }
};

inline TriggerSearchWindow trigger_search_window(long long span,
                                                 double pre_fraction,
                                                 long long history_front_tick,
                                                 long long displayed_tick,
                                                 long long armed_tick) {
    TriggerSearchWindow window;
    const double fraction =
        pre_fraction >= 0.0 && pre_fraction <= 1.0 ? pre_fraction : 0.25;
    window.pre_ticks = static_cast<long long>(
        std::llround(static_cast<double>(span) * fraction));
    window.post_ticks = span - window.pre_ticks;
    window.first_candidate =
        std::max({history_front_tick + window.pre_ticks,
                  displayed_tick - 2LL * span + window.pre_ticks, armed_tick});
    window.last_candidate = displayed_tick - window.post_ticks;
    return window;
}
enum class EventTriggerSource {
    Ignition0,
    Ignition1,
    Injector,
    Spark14,
    Spark23,
};

inline std::optional<long long>
find_event_trigger(std::span<const ma17::EmulatorEvent> events,
                   EventTriggerSource source, TriggerSlope slope,
                   long long first_tick, long long last_tick,
                   TriggerOccurrence occurrence = TriggerOccurrence::Latest) {
    if (first_tick > last_tick)
        return std::nullopt;
    std::optional<long long> latest;
    for (const auto &event : events) {
        if (event.tick < first_tick)
            continue;
        if (event.tick > last_tick)
            break;
        const bool pin_edge = event.high == (slope == TriggerSlope::Rising);
        const bool matched =
            (source == EventTriggerSource::Ignition0 &&
             event.type == ma17::EmulatorEventType::IgnitionPin &&
             event.channel == 0 && pin_edge) ||
            (source == EventTriggerSource::Ignition1 &&
             event.type == ma17::EmulatorEventType::IgnitionPin &&
             event.channel == 1 && pin_edge) ||
            (source == EventTriggerSource::Injector &&
             event.type == ma17::EmulatorEventType::InjectorPin && pin_edge) ||
            (source == EventTriggerSource::Spark14 &&
             event.type == ma17::EmulatorEventType::Spark &&
             event.pair_index == 0) ||
            (source == EventTriggerSource::Spark23 &&
             event.type == ma17::EmulatorEventType::Spark &&
             event.pair_index == 1);
        if (matched) {
            latest = event.tick;
            if (occurrence == TriggerOccurrence::First)
                return latest;
        }
    }
    return latest;
}

// Crossings are timestamped at the first source sample on the new side of
// the level. Missing values, nonmonotonic ticks and long gaps break a trace.
template <class ValueOf>
std::optional<long long>
find_analog_trigger(std::span<const ma17::EmulatorSnapshot> history,
                    ValueOf value_of, double level, TriggerSlope slope,
                    long long first_tick, long long last_tick,
                    long long max_gap_ticks = 247500,
                    TriggerOccurrence occurrence = TriggerOccurrence::Latest) {
    if (!std::isfinite(level) || first_tick > last_tick || max_gap_ticks <= 0)
        return std::nullopt;
    std::optional<long long> previous_tick;
    std::optional<double> previous_value;
    std::optional<long long> latest;
    for (const auto &sample : history) {
        if (sample.tick > last_tick)
            break;
        const auto value = value_of(sample);
        if (!value || !std::isfinite(*value) ||
            (previous_tick && sample.tick <= *previous_tick)) {
            previous_tick.reset();
            previous_value.reset();
            continue;
        }
        if (previous_tick && previous_value &&
            sample.tick - *previous_tick <= max_gap_ticks &&
            sample.tick >= first_tick &&
            (slope == TriggerSlope::Rising
                 ? *previous_value < level && *value >= level
                 : *previous_value > level && *value <= level)) {
            latest = sample.tick;
            if (occurrence == TriggerOccurrence::First)
                return latest;
        }
        previous_tick = sample.tick;
        previous_value = *value;
    }
    return latest;
}

inline std::optional<long long>
latest_event_trigger(std::span<const ma17::EmulatorEvent> events,
                     EventTriggerSource source, TriggerSlope slope,
                     long long first_tick, long long last_tick) {
    return find_event_trigger(events, source, slope, first_tick, last_tick);
}

template <class ValueOf>
std::optional<long long>
latest_analog_trigger(std::span<const ma17::EmulatorSnapshot> history,
                      ValueOf value_of, double level, TriggerSlope slope,
                      long long first_tick, long long last_tick,
                      long long max_gap_ticks = 247500) {
    return find_analog_trigger(history, value_of, level, slope, first_tick,
                               last_tick, max_gap_ticks);
}

} // namespace lab
