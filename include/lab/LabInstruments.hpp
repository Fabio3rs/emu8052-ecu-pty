#pragma once

#include "ma17/EmulatorEvent.hpp"

#include <SDL3/SDL.h>

#include <array>
#include <deque>
#include <vector>

namespace lab {

class FontRenderer;

struct TrendPoint {
    long long tick = 0;
    double rpm = 0.0;
    double lambda = 0.0;
};

void draw_lab_gauge(SDL_Renderer *renderer, FontRenderer &font, float x,
                    float y, float radius, double value, double maximum,
                    const char *label, SDL_Color accent, float needle_position);

void draw_lab_scope(SDL_Renderer *renderer, FontRenderer &font, int width,
                    int height, long long tick,
                    const std::vector<ma17::EmulatorEvent> &events,
                    const std::array<bool, 3> &channels_visible);

int scope_channel_at(float x, float y, int width, int height);

void draw_lab_trends(SDL_Renderer *renderer, FontRenderer &font,
                     const SDL_FRect &panel, long long tick,
                     const std::deque<TrendPoint> &history);

} // namespace lab
