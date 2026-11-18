#pragma once

#include "LabLayout.hpp"

#include <array>
#include <cstddef>
#include <string_view>

namespace lab {

enum class LabButtonAction {
    Key,
    Starter,
    PedalDown,
    PedalUp,
    Load,
    Pause,
    Slower,
    Faster,
    Mute,
    None,
};

inline constexpr std::array<std::string_view, 9> lab_button_labels{
    "KEY",   "START",  "PED-",   "PED+", "LOAD",
    "PAUSE", "SPEED-", "SPEED+", "MUTE"};

struct LabButtonRect {
    float x = 0.0f;
    float y = 0.0f;
    float width = 0.0f;
    float height = 0.0f;

    bool contains(float px, float py) const {
        return px >= x && px < x + width && py >= y && py < y + height;
    }
};

inline bool lab_buttons_visible(int width, int height) {
    return (width >= 900 && height >= 620) ||
           (width >= 600 && width < 1100 && height >= 350);
}

inline LabButtonRect lab_button_rect(std::size_t index, int width, int height,
                                     float desktop_left_width = -1.0f,
                                     const LayoutState &state = LayoutState{}) {
    constexpr float left = 16.0f;
    constexpr float gap = 6.0f;
    const LabLayout layout = LabLayout::compute(
        state, static_cast<float>(width), static_cast<float>(height));
    if (width >= 1100) {
        const float column_width =
            desktop_left_width > 0.0f ? desktop_left_width : layout.left.w;
        const float button_width =
            (column_width - left * 2.0f - gap * 2.0f) / 3.0f;
        return {left + static_cast<float>(index % 3) * (button_width + gap),
                static_cast<float>(height) - 270.0f +
                    static_cast<float>(index / 3) * 46.0f,
                button_width, 40.0f};
    }
    if (height < 620) {
        const float scene_width = layout.mechanical.w;
        if (width < 900) {
            const float button_width =
                (scene_width - 140.0f - left - gap * 4.0f) / 5.0f;
            return {left + static_cast<float>(index % 5) * (button_width + gap),
                    62.0f + static_cast<float>(index / 5) * 28.0f, button_width,
                    24.0f};
        }
        const float button_width = (scene_width - 160.0f - gap * 8.0f) /
                                   static_cast<float>(lab_button_labels.size());
        return {left + static_cast<float>(index) * (button_width + gap), 62.0f,
                button_width, 26.0f};
    }
    const float right = layout.instruments.x - 16.0f;
    const float button_width = (right - left - gap * 8.0f) /
                               static_cast<float>(lab_button_labels.size());
    return {left + static_cast<float>(index) * (button_width + gap),
            static_cast<float>(height) * 0.50f, button_width, 40.0f};
}

inline LabButtonAction hit_test_lab_button(float x, float y, int width,
                                           int height,
                                           float desktop_left_width = -1.0f) {
    if (!lab_buttons_visible(width, height))
        return LabButtonAction::None;
    for (std::size_t index = 0; index < lab_button_labels.size(); ++index) {
        if (lab_button_rect(index, width, height, desktop_left_width)
                .contains(x, y))
            return static_cast<LabButtonAction>(index);
    }
    return LabButtonAction::None;
}

} // namespace lab
