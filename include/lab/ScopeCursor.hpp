#pragma once

#include "ma17/EmulatorSnapshot.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <iterator>
#include <optional>
#include <span>
#include <string>

namespace lab {

inline std::optional<std::size_t> nearest_scope_sample(
    std::span<const ma17::EmulatorSnapshot> history, long long target,
    long long first_tick, long long last_tick) {
    if (target < first_tick || target > last_tick)
        return std::nullopt;
    const auto first = std::lower_bound(
        history.begin(), history.end(), first_tick,
        [](const ma17::EmulatorSnapshot &sample, long long tick) {
            return sample.tick < tick;
        });
    const auto last = std::upper_bound(
        first, history.end(), last_tick,
        [](long long tick, const ma17::EmulatorSnapshot &sample) {
            return tick < sample.tick;
        });
    if (first == last)
        return std::nullopt;
    auto next = std::lower_bound(
        first, last, target,
        [](const ma17::EmulatorSnapshot &sample, long long tick) {
            return sample.tick < tick;
        });
    if (next == last)
        --next;
    else if (next != first) {
        const auto previous = std::prev(next);
        if (target - previous->tick <= next->tick - target)
            next = previous;
    }
    if ((next->tick >= target ? next->tick - target : target - next->tick) >
        247500LL)
        return std::nullopt;
    return static_cast<std::size_t>(next - history.begin());
}

inline std::string format_scope_cursor_row(
    char label, std::optional<long long> tick, std::span<const double> values,
    std::span<const char *const> units) {
    std::string row(1, label);
    char part[48];
    if (!tick)
        row += " NO SAMPLE";
    else {
        std::snprintf(part, sizeof(part), " %.3f s",
                      static_cast<double>(*tick) / 990000.0);
        row += part;
        for (std::size_t signal = 0;
             signal < std::min(values.size(), units.size()); ++signal) {
            row += signal == 0 ? "  " : " / ";
            if (!std::isfinite(values[signal])) {
                row += "--";
                continue;
            }
            std::snprintf(part, sizeof(part), "%.2f", values[signal]);
            row += part;
            row += units[signal];
        }
    }
    return row;
}

inline std::string format_scope_cursor_delta(
    long long first_tick, long long last_tick,
    std::span<const double> first, std::span<const double> last,
    std::span<const char *const> units) {
    char part[48];
    std::snprintf(part, sizeof(part), "DT %.2f ms",
                  static_cast<double>(last_tick - first_tick) / 990.0);
    std::string row = part;
    for (std::size_t signal = 0;
         signal < std::min({first.size(), last.size(), units.size()}); ++signal) {
        if (std::isfinite(first[signal]) && std::isfinite(last[signal])) {
            std::snprintf(part, sizeof(part), "  D%zu %+.2f", signal + 1,
                          last[signal] - first[signal]);
            row += part;
            row += units[signal];
        } else {
            std::snprintf(part, sizeof(part), "  D%zu --", signal + 1);
            row += part;
        }
    }
    return row;
}

} // namespace lab
