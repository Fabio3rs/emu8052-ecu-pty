#pragma once

#include <algorithm>
#include <cmath>
#include <limits>

namespace lab {

// Radial geometry of a gauge's scale numerals (G1). A numeral box of size
// w x h at dial angle `theta` sits inside the tick circle of radius `inner_r`;
// `support` is the half extent of the box along the radial direction.
inline float gauge_numeral_support(float w, float h, float theta) {
    return 0.5f * (std::fabs(std::cos(theta)) * w +
                   std::fabs(std::sin(theta)) * h);
}

// Distance from the dial centre to the numeral's centre.
inline float gauge_numeral_center_radius(float inner_r, float w, float h,
                                         float theta) {
    return inner_r - gauge_numeral_support(w, h, theta);
}

// Distance from the dial centre to the closest point of the numeral box along
// its own radial direction (a lower bound of where a needle would touch it).
inline float gauge_numeral_inner_edge(float inner_r, float w, float h,
                                      float theta) {
    return inner_r - 2.0f * gauge_numeral_support(w, h, theta);
}

// The needle tip never goes past the innermost numeral edge, minus a margin.
inline float gauge_needle_tip_limit(float requested_tip, float numeral_edge_min,
                                    float margin) {
    return std::min(requested_tip, numeral_edge_min - margin);
}

inline constexpr float kNoNumerals = std::numeric_limits<float>::infinity();

} // namespace lab
