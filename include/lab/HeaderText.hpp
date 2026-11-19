#pragma once

#include "lab/FontRenderer.hpp"

#include <string>

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

} // namespace lab
