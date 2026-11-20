#pragma once

#include "lab/LabLayout.hpp"

#include <SDL3/SDL_rect.h>

namespace lab {

// Frente 0: the rectangles of the Lab's widgets (toolbar buttons, sliders, the
// gear and clutch cards, ...) as pure functions of the layout state and the
// output size. They used to live in SdlDisplay.cpp.

// The UI scale in force at an output size: 1 when the user fixed a percentage
// (Ctrl+0..3), otherwise the window size over 1280x720, clamped to 1..2.
void set_configured_ui_scale_percent(int percent);
float lab_ui_scale(int width, int height);

inline LabLayout layout_for(const LayoutState &state, int width, int height,
                            bool scope_maximized = false) {
    return LabLayout::compute(state, static_cast<float>(width),
                              static_cast<float>(height), scope_maximized);
}

SDL_FRect instrument_cluster_rect(const LayoutState &layout_state, int width,
                                  int height);
SDL_FRect view_selector_rect(const LayoutState &layout_state, int width,
                             int height);
SDL_FRect fit_button_rect(const LayoutState &layout_state, int width,
                          int height);
SDL_FRect speed_selector_rect(const LayoutState &layout_state, int width,
                              int height);
bool speed_selector_visible(const LayoutState &layout_state, int width,
                            int height);
SDL_FRect fullscreen_button_rect(const LayoutState &layout_state, int width,
                                 int height);
SDL_FRect pedal_slider_rect(const LayoutState &layout_state, int width,
                            int height);
SDL_FRect volume_slider_rect(const LayoutState &layout_state, int width,
                             int height);
SDL_FRect gear_widget_rect(const LayoutState &layout_state, int width,
                           int height);
SDL_FRect clutch_widget_rect(const LayoutState &layout_state, int width,
                             int height);

} // namespace lab
