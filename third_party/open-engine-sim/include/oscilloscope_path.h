// Extracted from src/oscilloscope.cpp, Oscilloscope::render.
// Copyright (c) 2022 Ange Yaghi. MIT license; see ../LICENSE.
#ifndef ATG_ENGINE_SIM_OSCILLOSCOPE_PATH_H
#define ATG_ENGINE_SIM_OSCILLOSCOPE_PATH_H

#include <cmath>

namespace oes {

// s = point index / point count, as in the donor (not index / (count - 1)).
// UiElement::pixelsToUnits is identity in the donor desktop implementation.
inline float oscilloscope_path_width(float s, float line_width = 1.0f) {
    float width = line_width * std::fmaxf(1.0f * s, 0.5f);
    if (s > 0.95f) {
        width += ((s - 0.95f) / 0.05f) * 2;
    }
    return width;
}

} // namespace oes

#endif
