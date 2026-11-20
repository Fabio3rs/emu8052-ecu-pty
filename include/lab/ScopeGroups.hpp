#pragma once

#include <algorithm>
#include <array>
#include <cstddef>

namespace lab {

// The one place that names the analog scope groups (L6). The window title and
// headings use `title`; tabs and the narrow-heading fallback use `short_name`
// at every window size, so a group never changes name when the window resizes.
struct ScopeGroupSpec {
    const char *title;
    const char *short_name;
};

inline constexpr std::size_t kScopeGroupCount = 11;

inline constexpr std::array<ScopeGroupSpec, kScopeGroupCount> kScopeGroups{{
    {"LAMBDA", "LAM"},
    {"TPS", "TPS"},
    {"THERMAL", "TEMP"},
    {"INTAKE", "AIR"},
    {"ENGINE", "RPM"},
    {"FUEL", "FUEL"},
    {"ADC TPS", "A TPS"},
    {"ADC BAT/LAMBDA", "A B/L"},
    {"ADC IAT/ECT", "A T/E"},
    {"BATTERY", "BAT"},
    {"IDLE", "IDLE"},
}};

inline const ScopeGroupSpec &scope_group(int group) {
    return kScopeGroups[static_cast<std::size_t>(
        std::clamp(group, 0, static_cast<int>(kScopeGroupCount) - 1))];
}

} // namespace lab
