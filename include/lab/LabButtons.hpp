#pragma once

#include "LabLayout.hpp"
#include "LabTheme.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
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

// C5: the keyboard shortcut of each button, as handled in SdlDisplay.cpp and
// listed in HELP. `underline_first` marks buttons whose shortcut is the first
// letter of the label (KEY, START, LOAD, MUTE): that letter is underlined;
// the others (arrows, Space, -/+) show the key as a small tag.
struct LabButtonShortcut {
    std::string_view key;
    bool underline_first;
};

inline constexpr std::array<LabButtonShortcut, 9> lab_button_shortcuts{{
    {"K", true},   {"S", true},   {"DN", false},
    {"UP", false}, {"L", true},   {"SPC", false},
    {"-", false},  {"+", false},  {"M", true},
}};

// C5: the tooltip shown while the pointer rests on a button: what it does and
// its key, e.g. "PEDAL DOWN (DOWN ARROW)". Same keys as HELP and the tags.
inline constexpr std::array<std::string_view, 9> lab_button_tooltips{{
    "KEY ON/OFF (K)", "HOLD TO CRANK (S)", "PEDAL DOWN (DOWN ARROW)",
    "PEDAL UP (UP ARROW)", "LOAD ON/OFF (L), WHEEL 1%", "PAUSE/RESUME (SPACE)",
    "SPEED HALF (-)", "SPEED DOUBLE (+)", "MUTE (M)"}};

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

// C1: five visual states per button (normal, hover, pressed, on, disabled),
// with an accent colour per action instead of one inverted-white style that
// meant toggle, momentary action and focus all at once.
struct ButtonRgba {
    std::uint8_t r = 0, g = 0, b = 0, a = 255;
    friend bool operator==(const ButtonRgba &, const ButtonRgba &) = default;
};

enum class LabButtonKind { Toggle, Momentary, Level };

inline LabButtonKind lab_button_kind(LabButtonAction action) {
    switch (action) {
    case LabButtonAction::Key:
    case LabButtonAction::Pause:
    case LabButtonAction::Mute:
        return LabButtonKind::Toggle;
    case LabButtonAction::Load:
    case LabButtonAction::Slower:
    case LabButtonAction::Faster:
        return LabButtonKind::Level;
    case LabButtonAction::Starter:
    case LabButtonAction::PedalDown:
    case LabButtonAction::PedalUp:
    case LabButtonAction::None:
        return LabButtonKind::Momentary;
    }
    return LabButtonKind::Momentary;
}

// Accent: green = engine key, amber = pause/starter, red = mute, cyan = the rest.
inline ButtonRgba lab_button_accent(LabButtonAction action) {
    switch (action) {
    case LabButtonAction::Key: return {60, 232, 130, 255};
    case LabButtonAction::Pause:
    case LabButtonAction::Starter: return {249, 190, 96, 255};
    case LabButtonAction::Mute: return {222, 96, 96, 255};
    case LabButtonAction::PedalDown:
    case LabButtonAction::PedalUp:
    case LabButtonAction::Load:
    case LabButtonAction::Slower:
    case LabButtonAction::Faster:
    case LabButtonAction::None: return {kAccent.r, kAccent.g, kAccent.b, kAccent.a};
    }
    return {kAccent.r, kAccent.g, kAccent.b, kAccent.a};
}

struct LabButtonVisual {
    ButtonRgba fill;
    ButtonRgba frame;
    ButtonRgba text;
    ButtonRgba bar;       // accent bar on the left edge
    float bar_width = 0.0f; // logical units; 0 = no bar (only the "on" state)
};

inline ButtonRgba mix_button_color(ButtonRgba a, ButtonRgba b, float t) {
    const auto lerp = [t](std::uint8_t x, std::uint8_t y) {
        return static_cast<std::uint8_t>(static_cast<float>(x) +
                                         (static_cast<float>(y) -
                                          static_cast<float>(x)) *
                                             t);
    };
    return {lerp(a.r, b.r), lerp(a.g, b.g), lerp(a.b, b.b), 255};
}

inline LabButtonVisual compute_button_visual(LabButtonAction action, bool on,
                                             bool held, bool hover,
                                             bool enabled) {
    constexpr ButtonRgba surface{22, 25, 32, 255};     // lead-grey
    constexpr ButtonRgba border{48, 56, 70, 255};      // subtle border
    constexpr ButtonRgba text{216, 224, 234, 255};     // light text
    const ButtonRgba accent = lab_button_accent(action);
    LabButtonVisual visual{surface, border, text, accent, 0.0f};
    if (!enabled) { // disabled: text at 40 %, no hover/on emphasis
        visual.text = mix_button_color(surface, text, 0.40f);
        visual.frame = mix_button_color(surface, border, 0.70f);
        return visual;
    }
    if (on) { // on: tinted fill + 3 px accent bar, text stays light
        visual.fill = mix_button_color(surface, accent, 0.20f);
        visual.frame = mix_button_color(border, accent, 0.55f);
        visual.bar_width = 3.0f;
    }
    if (hover)
        visual.frame = mix_button_color(visual.frame, text, 0.55f);
    if (held) { // pressed: stronger fill than "on", frame in the accent
        visual.fill = mix_button_color(surface, accent, 0.38f);
        visual.frame = accent;
    }
    return visual;
}

} // namespace lab
