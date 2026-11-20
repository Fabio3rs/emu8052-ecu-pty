#pragma once

#include <cmath>

namespace lab {

// V1: the connecting rod beam is an "I": two bright flanges either side of a
// darker web. This is the unit normal of the beam from (x0,y0) to (x1,y1), used
// to offset the flange lines; a zero-length beam has no direction, so it yields
// (0, 0) and the flanges collapse onto the web.
struct RodNormal {
    float x = 0.0f;
    float y = 0.0f;
};

inline RodNormal rod_normal(float x0, float y0, float x1, float y1) {
    const float dx = x1 - x0;
    const float dy = y1 - y0;
    const float length = std::hypot(dx, dy);
    if (!(length > 1e-6f))
        return {};
    return {-dy / length, dx / length};
}

} // namespace lab
