#pragma once

#include "lab/FontRenderer.hpp"

#include <algorithm>
#include <string>
#include <vector>

namespace lab {

// Fits a header title into `max_width` logical units at `px`: the full text if
// it fits, else `short_text`, else `short_text` (or the full text when no short
// form is given) cut with an ellipsis. Never returns something wider than
// `max_width` unless even "..." does not fit.
inline std::string fit_header_title(const FontRenderer &font,
                                    const std::string &full_text,
                                    const std::string &short_text, float px,
                                    float max_width) {
    if (font.measure_px(full_text, px) <= max_width)
        return full_text;
    const std::string &fallback = short_text.empty() ? full_text : short_text;
    return font.ellipsize(fallback, px, max_width);
}

// L1: one status line made of chips in display order. When the line is too
// wide, the chip with the numerically highest `priority` (the least important)
// is dropped first and a "+N" chip counts what was dropped; the font scale
// never changes. `measure` returns the width of a string.
struct StatusChip {
    std::string text;
    int priority; // 0 = most important
};

template <typename Measure>
std::string fit_status_chips(std::vector<StatusChip> chips, Measure &&measure,
                             float max_width,
                             const std::string &separator = " | ") {
    const auto join = [&](const std::vector<StatusChip> &list,
                          int dropped) -> std::string {
        std::string line;
        for (const auto &chip : list) {
            if (!line.empty())
                line += separator;
            line += chip.text;
        }
        if (dropped > 0) {
            if (!line.empty())
                line += separator;
            line += "+" + std::to_string(dropped);
        }
        return line;
    };
    int dropped = 0;
    std::string line = join(chips, dropped);
    while (measure(line) > max_width && chips.size() > 1) {
        const auto victim = std::max_element(
            chips.begin(), chips.end(),
            [](const StatusChip &a, const StatusChip &b) {
                return a.priority < b.priority;
            });
        chips.erase(victim);
        ++dropped;
        line = join(chips, dropped);
    }
    return line;
}

} // namespace lab
