#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <vector>

namespace lab {

template <typename Sample, typename Value>
std::vector<std::size_t> decimate_scope_samples(
    const std::vector<Sample> &samples, long long first_tick,
    long long last_tick, int columns, long long max_gap_ticks,
    Value value_of) {
    std::vector<std::size_t> selected;
    if (columns <= 0 || last_tick < first_tick)
        return selected;
    int bucket = -1;
    std::size_t first = 0;
    std::size_t last = 0;
    std::size_t minimum = 0;
    std::size_t maximum = 0;
    double low = 0.0;
    double high = 0.0;
    bool previous_valid = false;
    long long previous_tick = 0;
    const auto flush = [&](std::vector<std::size_t> &output) {
        if (bucket < 0)
            return;
        std::array<std::size_t, 4> picks{first, minimum, maximum, last};
        std::sort(picks.begin(), picks.end());
        output.insert(output.end(), picks.begin(),
                      std::unique(picks.begin(), picks.end()));
        bucket = -1;
    };
    const double span = static_cast<double>(
        std::max(1LL, last_tick - first_tick));
    for (std::size_t index = 0; index < samples.size(); ++index) {
        const auto &sample = samples[index];
        if (sample.tick < first_tick || sample.tick > last_tick)
            continue;
        const auto value = value_of(sample);
        if (!value || !std::isfinite(*value)) {
            flush(selected);
            if (previous_valid)
                selected.push_back(index);
            previous_valid = false;
            continue;
        }
        if (previous_valid &&
            (sample.tick <= previous_tick ||
             sample.tick - previous_tick > max_gap_ticks))
            flush(selected);
        const auto position = static_cast<int>(
            static_cast<double>(sample.tick - first_tick) *
            static_cast<double>(columns) / span);
        const int column = std::clamp(position, 0, columns - 1);
        if (bucket != column) {
            flush(selected);
            bucket = column;
            first = minimum = maximum = index;
            low = high = *value;
        }
        last = index;
        if (*value < low) {
            low = *value;
            minimum = index;
        }
        if (*value > high) {
            high = *value;
            maximum = index;
        }
        previous_tick = sample.tick;
        previous_valid = true;
    }
    flush(selected);
    return selected;
}

} // namespace lab
