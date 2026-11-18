#pragma once

#include <algorithm>
#include <cmath>

namespace lab {

struct PixelSpan {
    int x = 0;
    int w = 0;
};

// Snaps [start, start + length) to whole pixels by rounding both edges, never
// x and width separately: adjacent spans then share an edge exactly, with no
// gap or overlap.
inline PixelSpan pixel_span(float start, float length) {
    if (!std::isfinite(start) || !std::isfinite(length) || length <= 0.0f)
        return {};
    const int left = static_cast<int>(std::lround(start));
    const int right = static_cast<int>(std::lround(start + length));
    return {left, std::max(0, right - left)};
}

} // namespace lab
