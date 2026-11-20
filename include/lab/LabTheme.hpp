#pragma once

#include "lab/ThemePalette.hpp"

#include <SDL3/SDL_pixels.h>
#include <SDL3/SDL_render.h>

#include <array>

namespace lab {

// T1: every colour with a meaning is a token. The SDL colours below are shared
// by every theme; the scene colours a theme may change are in ThemePalette.hpp.
// No other file may spell these colours as literals: lab_theme_test.cpp fails
// if one does (T3), so one role is one colour on every layer.
inline constexpr SDL_Color kAccent{99, 211, 220, 255};   // UI accent / selection
inline constexpr SDL_Color kCritical{238, 68, 69, 255};  // alarm, fault, red zone
inline constexpr SDL_Color kPairA{60, 200, 190, 255};    // cylinders 1/4
inline constexpr SDL_Color kPairB{236, 160, 90, 255};    // cylinders 2/3

inline void set_draw_color(SDL_Renderer *renderer, SDL_Color color) {
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
}

} // namespace lab
