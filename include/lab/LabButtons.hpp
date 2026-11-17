#pragma once

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
    return width >= 900 && height >= 620;
}

inline LabButtonRect lab_button_rect(std::size_t index, int width, int height) {
    constexpr float left = 16.0f;
    constexpr float gap = 6.0f;
    const float right = static_cast<float>(width) * 0.66f - 16.0f;
    const float button_width = (right - left - gap * 8.0f) /
                               static_cast<float>(lab_button_labels.size());
    return {left + static_cast<float>(index) * (button_width + gap),
            static_cast<float>(height) - 218.0f, button_width, 40.0f};
}

inline LabButtonAction hit_test_lab_button(float x, float y, int width,
                                           int height) {
    if (!lab_buttons_visible(width, height))
        return LabButtonAction::None;
    for (std::size_t index = 0; index < lab_button_labels.size(); ++index) {
        if (lab_button_rect(index, width, height).contains(x, y))
            return static_cast<LabButtonAction>(index);
    }
    return LabButtonAction::None;
}

} // namespace lab
