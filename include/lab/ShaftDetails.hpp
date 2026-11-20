#pragma once

#include "lab/DonorScene.hpp"
#include "ma17/EmulatorSnapshot.hpp"

#include <SDL3/SDL_render.h>

namespace lab {

// The SDL detail layer over the longitudinal view: runners, springs, rings,
// crank webs and the wrist pin. Frente 0 of the v2 analysis moved it out of
// SdlDisplay.cpp unchanged; M2 will turn it into scene geometry.
void draw_shaft_mechanical_details(SDL_Renderer *screen,
                                   const ma17::EmulatorSnapshot &snapshot,
                                   SceneCamera camera, float scene_width,
                                   float scene_height, float ui_scale);

} // namespace lab
