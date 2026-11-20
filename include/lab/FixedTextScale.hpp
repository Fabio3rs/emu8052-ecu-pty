#pragma once

#include <algorithm>
#include <initializer_list>

namespace lab {

// L8: a text block's scale is a property of its box, not of the values shown.
// It is derived from worst-case sample strings of the widest realistic
// content, so a changing reading can never resize the font from one frame to
// the next. `measure(sample)` returns the unscaled width of a string.
template <typename Measure>
float fixed_block_scale(Measure &&measure,
                        std::initializer_list<const char *> worst_case_samples,
                        float max_scale, float available_width) {
    float widest = 1.0f;
    for (const char *sample : worst_case_samples)
        widest = std::max(widest, static_cast<float>(measure(sample)));
    return std::min(max_scale, available_width / widest);
}

} // namespace lab
