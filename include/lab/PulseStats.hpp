#pragma once

#include "ma17/EmulatorEvent.hpp"

#include <cstdio>
#include <span>
#include <string>
#include <vector>

namespace lab {

// D2/D3: width, period and duty of the latest complete pulse on one digital
// channel, from the recorded pin edges (990 000 ticks per second).
inline constexpr double kPulseTicksPerMs = 990.0;

struct PulseStat {
    bool valid = false;       // a complete pulse of the requested level exists
    double width_ms = 0.0;
    bool has_period = false;  // a previous pulse of the same level exists
    double period_ms = 0.0;
    double duty_percent = 0.0; // width / period, only when has_period
};

// `type` is InjectorPin or IgnitionPin (channel selects P5.x). `measure_high`
// picks the level whose width is measured: a pulse starts at an edge going to
// that level and ends at the opposite edge. Edges after `up_to_tick` are
// ignored.
inline PulseStat last_pulse_stat(std::span<const ma17::EmulatorEvent> events,
                                 ma17::EmulatorEventType type,
                                 unsigned channel, long long up_to_tick,
                                 bool measure_high) {
    struct Edge {
        long long tick;
        bool high;
    };
    std::vector<Edge> edges;
    for (const auto &event : events) {
        if (event.type != type || event.tick > up_to_tick)
            continue;
        if (type == ma17::EmulatorEventType::IgnitionPin &&
            event.channel != channel)
            continue;
        edges.push_back({event.tick, event.high});
    }
    PulseStat stat;
    for (std::size_t i = edges.size(); i-- > 1;) {
        if (edges[i].high == measure_high || edges[i - 1].high != measure_high)
            continue;
        stat.valid = true;
        stat.width_ms =
            static_cast<double>(edges[i].tick - edges[i - 1].tick) /
            kPulseTicksPerMs;
        for (std::size_t j = i - 1; j-- > 0;)
            if (edges[j].high == measure_high && edges[j + 1].high != measure_high) {
                stat.has_period = true;
                stat.period_ms =
                    static_cast<double>(edges[i - 1].tick - edges[j].tick) /
                    kPulseTicksPerMs;
                if (stat.period_ms > 0.0)
                    stat.duty_percent = 100.0 * stat.width_ms / stat.period_ms;
                else
                    stat.has_period = false;
                break;
            }
        break;
    }
    return stat;
}

// "TI 4.35 MS  DUTY 21.7%": injection time and duty; "TI --" without a pulse.
inline std::string injection_text(const PulseStat &stat) {
    if (!stat.valid)
        return "TI --";
    char text[48];
    if (stat.has_period)
        std::snprintf(text, sizeof(text), "TI %.2f MS  DUTY %.1f%%",
                      stat.width_ms, stat.duty_percent);
    else
        std::snprintf(text, sizeof(text), "TI %.2f MS", stat.width_ms);
    return text;
}

// The same reading in progressively shorter forms, longest first, for a cell
// that cannot hold the full text (the pixel face has a minimum glyph size).
inline std::vector<std::string> injection_text_variants(const PulseStat &stat) {
    if (!stat.valid)
        return {"TI --"};
    char full[48], compact[32], shortest[24];
    std::snprintf(full, sizeof(full), "TI %.2f MS  DUTY %.1f%%", stat.width_ms,
                  stat.duty_percent);
    std::snprintf(compact, sizeof(compact), "TI %.2fMS %.0f%%", stat.width_ms,
                  stat.duty_percent);
    std::snprintf(shortest, sizeof(shortest), "TI %.2fMS", stat.width_ms);
    if (!stat.has_period)
        return {shortest};
    return {full, compact, shortest};
}

// Coil line width, labelled as a candidate: the polarity of the P5 drive is
// not confirmed, so this is "LOW" time, never called dwell.
inline std::string coil_low_text(const PulseStat &stat) {
    if (!stat.valid)
        return "LOW --";
    char text[32];
    std::snprintf(text, sizeof(text), "LOW %.2fMS", stat.width_ms);
    return text;
}

} // namespace lab
