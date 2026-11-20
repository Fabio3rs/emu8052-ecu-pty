#pragma once

#include "lab/FontRenderer.hpp"
#include "ma17/EmulatorSnapshot.hpp"

#include <SDL3/SDL_rect.h>
#include <SDL3/SDL_render.h>

#include <array>

namespace lab {

// Frente 0 of the v2 analysis: the control drawing (buttons, ECU badges and the
// slider groove) moved out of SdlDisplay.cpp. The caller supplies the width of
// the left column and the UI scale, so this file needs no layout state.

// C1/C5: the 3x3 button grid with its five states and shortcut hints.
void draw_lab_buttons(SDL_Renderer *screen, FontRenderer &font, int width,
                      int height, float left_width, float scale,
                      const std::array<bool, 9> &selected,
                      const std::array<bool, 9> &enabled, double load_nm,
                      bool replay_locked = false);

// D4: ECU state badges above the button grid.
void draw_ecu_badges(SDL_Renderer *screen, FontRenderer &font, int width,
                     int height, float left_width, float scale,
                     const ma17::EmulatorSnapshot &snapshot);

// C2: groove, ticks, fill and thumb of the pedal / volume sliders.
void draw_slider_track(SDL_Renderer *screen, const SDL_FRect &box,
                       float fraction, bool enabled, float scale);

} // namespace lab
