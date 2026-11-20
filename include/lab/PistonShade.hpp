#pragma once

#include <algorithm>
#include <cmath>

namespace lab {

// V1: the piston is a cylinder, so across its width it is darker at both edges
// and has a highlight a third of the way in. `t` runs 0 (left edge) .. 1 (right
// edge). Alpha of a black overlay (0 = untouched, up to ~150 at the edges) and of
// a white highlight; the two never overlap.
inline unsigned char piston_shade_alpha(double t) {
    t = std::clamp(t, 0.0, 1.0);
    const double edge = std::abs(2.0 * t - 1.0);
    return static_cast<unsigned char>(150.0 * std::pow(edge, 2.2) + 0.5);
}

inline unsigned char piston_highlight_alpha(double t) {
    t = std::clamp(t, 0.0, 1.0);
    const double distance = std::abs(t - 0.33);
    return distance >= 0.07
               ? 0
               : static_cast<unsigned char>(45.0 * (1.0 - distance / 0.07) + 0.5);
}

} // namespace lab
