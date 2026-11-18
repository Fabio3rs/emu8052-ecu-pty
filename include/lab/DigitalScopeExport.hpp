#pragma once

#include "ma17/EmulatorEvent.hpp"
#include "ma17/EmulatorSnapshot.hpp"

#include <algorithm>
#include <optional>
#include <span>
#include <vector>

namespace lab {

struct DigitalScopeRecord {
    long long tick = 0;
    std::optional<ma17::EmulatorEvent> event;
    bool contact_closed = false;
};

inline std::vector<DigitalScopeRecord> selected_digital_records(
    std::span<const ma17::EmulatorEvent> events,
    std::span<const ma17::EmulatorSnapshot> history,
    long long first_tick, long long last_tick) {
    std::vector<DigitalScopeRecord> rows;
    if (last_tick < first_tick)
        return rows;
    for (const auto &event : events) {
        if (event.tick < first_tick || event.tick > last_tick ||
            event.type == ma17::EmulatorEventType::LampCandidate ||
            (event.type == ma17::EmulatorEventType::IgnitionPin &&
             event.channel >= 2) ||
            (event.type == ma17::EmulatorEventType::Spark &&
             event.pair_index >= 2) ||
            ((event.type == ma17::EmulatorEventType::Combustion ||
              event.type == ma17::EmulatorEventType::Misfire) &&
             event.cylinder_index >= 4))
            continue;
        rows.push_back({event.tick, event, false});
    }
    constexpr long long max_gap_ticks = 247500;
    std::optional<DigitalScopeRecord> previous;
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
            sample.idle_contact_closed != previous->contact_closed &&
            sample.tick >= first_tick)
            rows.push_back({sample.tick, std::nullopt,
                            sample.idle_contact_closed});
        previous = DigitalScopeRecord{sample.tick, std::nullopt,
                                      sample.idle_contact_closed};
    }
    std::stable_sort(rows.begin(), rows.end(),
                     [](const auto &a, const auto &b) {
                         return a.tick < b.tick;
                     });
    return rows;
}

} // namespace lab
