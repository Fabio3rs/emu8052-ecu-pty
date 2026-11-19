#pragma once

#include <array>
#include <string>

namespace lab {

// SEVEL 1.6 i.e. four-cylinder firing order 1-3-4-2 (wasted-spark coils: one
// coil serves cylinders 1/4, the other 2/3).
inline constexpr std::array<int, 4> firing_order{1, 3, 4, 2};

// Coil pair of a cylinder (0 = "1/4", 1 = "2/3"); -1 for an invalid cylinder.
inline constexpr int ignition_pair_of_cylinder(int cylinder) {
    if (cylinder == 1 || cylinder == 4)
        return 0;
    if (cylinder == 2 || cylinder == 3)
        return 1;
    return -1;
}

inline constexpr const char *ignition_pair_label(int pair) {
    return pair == 0 ? "1/4" : "2/3";
}

// Scope heading prefix for the cylinder in focus ("CYL 2 VIEW"), empty when no
// cylinder (0) or an invalid one is selected. `separator` appends " | ".
inline std::string cylinder_focus_label(int cylinder, bool separator = false) {
    if (cylinder < 1 || cylinder > 4)
        return {};
    return "CYL " + std::to_string(cylinder) + " VIEW" +
           (separator ? " | " : "");
}

} // namespace lab
