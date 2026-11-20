#pragma once

#include <array>
#include <cstring>

namespace lab {

// T1, SDL-free half of the theme: the scene colours a theme may change, as
// 0..1 floats so scene code (which has no SDL) can use them. The SDL colours
// shared by every theme live in LabTheme.hpp.
struct ThemePalette {
    const char *name;
    std::array<float, 3> intake;  // intake flow / valves
    std::array<float, 3> exhaust; // exhaust flow / valves
    std::array<float, 3> needle;  // gauge needle
};

// "Lab": the needle is warm white so it never competes with `critical`.
inline constexpr ThemePalette kLabPalette{"lab",
                                          {0.0f, 0.898f, 1.0f},
                                          {1.0f, 0.25f, 0.50f},
                                          {0.96f, 0.93f, 0.86f}};
// "OES classic": the donor's own flow colours and red needle.
inline constexpr ThemePalette kOesPalette{"oes",
                                          {0.38f, 0.79f, 0.81f},
                                          {0.78f, 0.52f, 0.41f},
                                          {0.93f, 0.27f, 0.27f}};

inline const ThemePalette *&active_palette_slot() {
    static const ThemePalette *slot = &kLabPalette;
    return slot;
}
inline const ThemePalette &palette() { return *active_palette_slot(); }

// "lab" / "oes"; anything else keeps the current theme. Returns whether it
// matched.
inline bool select_theme(const char *name) {
    for (const ThemePalette *candidate : {&kLabPalette, &kOesPalette})
        if (name && std::strcmp(name, candidate->name) == 0) {
            active_palette_slot() = candidate;
            return true;
        }
    return false;
}

} // namespace lab
