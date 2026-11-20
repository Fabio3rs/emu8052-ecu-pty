#pragma once

#include <array>
#include <cmath>
#include <cstddef>

namespace lab {

// C3: a three-segment simulation-speed selector (0.25X / 1X / 4X) in the
// toolbar, next to the SPEED-/SPEED+ buttons (which keep halving/doubling).
inline constexpr std::array<double, 3> kSpeedPresets{0.25, 1.0, 4.0};

// Index of the preset equal to `speed`, or -1 (e.g. after SPEED+ gave 2X): no
// segment is highlighted rather than the nearest one being claimed.
inline int active_speed_preset(double speed) {
    for (std::size_t i = 0; i < kSpeedPresets.size(); ++i)
        if (std::abs(speed - kSpeedPresets[i]) < 1e-9)
            return static_cast<int>(i);
    return -1;
}

struct SpeedSegment {
    float x, y, w, h;
};

// Segment `index` of a selector whose first segment starts at (x, y). Equal
// widths, no gaps, so a click maps to exactly one segment.
inline SpeedSegment speed_segment(std::size_t index, float x, float y,
                                  float segment_w, float h) {
    return {x + static_cast<float>(index) * segment_w, y, segment_w, h};
}

// Which preset is under (px, py); -1 for none.
inline int speed_preset_at(float px, float py, float x, float y, float segment_w,
                           float h) {
    for (std::size_t i = 0; i < kSpeedPresets.size(); ++i) {
        const SpeedSegment s = speed_segment(i, x, y, segment_w, h);
        if (px >= s.x && px < s.x + s.w && py >= s.y && py < s.y + s.h)
            return static_cast<int>(i);
    }
    return -1;
}

} // namespace lab
