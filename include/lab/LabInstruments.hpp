#pragma once

#include "ma17/EmulatorEvent.hpp"
#include "ma17/EmulatorSnapshot.hpp"
#include "lab/DonorScene.hpp"

#include <SDL3/SDL.h>

#include <array>
#include <deque>
#include <vector>

class Gauge;

namespace lab {

class FontRenderer;

struct TrendPoint {
    long long tick = 0;
    double rpm = 0.0;
    double lambda = 0.0;
};

void draw_lab_gauge(SDL_Renderer *renderer, FontRenderer &font, float x,
                    float y, float radius, double value, double maximum,
                    const char *label, SDL_Color accent, float needle_position,
                    float ui_scale, const Gauge *style = nullptr);

void draw_lab_scope(SDL_Renderer *renderer, FontRenderer &font, int width,
                    int height, long long tick,
                    const std::vector<ma17::EmulatorEvent> &events,
                    const std::array<bool, 3> &channels_visible,
                    long long span_ticks);

int scope_channel_at(float x, float y, int width, int height);

void draw_lab_trends(SDL_Renderer *renderer, FontRenderer &font,
                     const SDL_FRect &panel, long long tick,
                     const std::deque<TrendPoint> &history);

void draw_oes_right_cluster(SDL_Renderer *renderer, FontRenderer &font,
                            const SDL_FRect &bounds,
                            const ma17::EmulatorSnapshot &snapshot,
                            const std::array<ScenePulse, 4> &pulses,
                            const std::array<float, 2> &spark_glows,
                            float ui_scale,
                            const std::array<Gauge, 3> *gauges = nullptr);

} // namespace lab
