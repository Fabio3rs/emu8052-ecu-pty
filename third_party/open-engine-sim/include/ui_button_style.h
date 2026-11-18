// Adapted from src/ui_button.cpp and src/ui_utilities.cpp.
// Copyright (c) 2022 Ange Yaghi. MIT license; see ../LICENSE.
#ifndef ATG_ENGINE_SIM_UI_BUTTON_STYLE_H
#define ATG_ENGINE_SIM_UI_BUTTON_STYLE_H

#include <array>
#include <cstddef>

namespace oes {
using ButtonColor = std::array<float, 4>;

struct ButtonStyle {
    ButtonColor fill;
    ButtonColor foreground;
};

// UiButton::render's presentation, independent of EngineSimApplication.
// The caller provides palette and input state; frame and text share foreground.
inline ButtonStyle button_style(const ButtonColor &foreground,
                                const ButtonColor &background,
                                bool inverted, bool held, bool over) {
    ButtonColor color = inverted ? foreground : background;
    const ButtonColor ink = inverted ? background : foreground;
    const float s = held ? 0.08f : over ? 0.04f : 0.0f;
    for (std::size_t i = 0; i < color.size(); ++i) {
        color[i] = color[i] * (1.0f - s) + ink[i] * s;
    }
    return {color, ink};
}
} // namespace oes

#endif
