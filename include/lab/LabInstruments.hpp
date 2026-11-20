#pragma once

#include "lab/PulseStats.hpp"
#include "lab/DigitalPulseMeasurements.hpp"
#include "lab/DisplayUnits.hpp"
#include "lab/DonorScene.hpp"
#include "lab/LabLayout.hpp"
#include "lab/SevelInstrumentProfile.hpp"
#include "ma17/EmulatorEvent.hpp"
#include "ma17/EmulatorSnapshot.hpp"

#include <SDL3/SDL.h>

#include <array>
#include <deque>
#include <optional>
#include <vector>

class Gauge;

namespace lab {

class FontRenderer;

struct ScopeAxisRange {
    double minimum = 0.0;
    double maximum = 0.0;
};
using ScopeAxisRanges = std::array<ScopeAxisRange, 2>;

struct TrendPoint {
    long long tick = 0;
    double rpm = 0.0;
    double lambda = 0.0;
};

void draw_lab_scope(
    const LayoutState &layout_state, SDL_Renderer *renderer, FontRenderer &font,
    int width, int height, long long tick,
    const std::vector<ma17::EmulatorEvent> &events,
    const std::vector<ma17::EmulatorSnapshot> &history,
    const std::array<bool, 4> &channels_visible, long long span_ticks,
    const std::array<std::optional<DigitalScopeCursor>, 2> &cursors,
    bool frozen, int focus_cylinder = 0);

void draw_lab_analog_scope(
    const LayoutState &layout_state, SDL_Renderer *renderer, FontRenderer &font,
    int width, int height, const ma17::EmulatorSnapshot &current,
    const std::vector<ma17::EmulatorSnapshot> &history, int group,
    long long span_ticks, bool frozen,
    const std::array<long long, 2> &cursor_ticks, long long view_end_tick,
    long long trigger_tick, const char *trigger_status,
    std::size_t raw_evicted = 0, std::size_t archive_evicted = 0,
    bool maximized = false, DisplayUnits units = DisplayUnits::Metric,
    int focus_cylinder = 0, const ScopeAxisRanges *fitted_axes = nullptr);

std::optional<ScopeAxisRanges>
fit_analog_scope_axes(const std::vector<ma17::EmulatorSnapshot> &history,
                      int group, long long first_tick, long long last_tick,
                      DisplayUnits units);
bool analog_scope_fit_at(const LayoutState &layout_state, float x, float y,
                         int width, int height, bool maximized = false);

std::optional<long long> analog_scope_tick_at(const LayoutState &layout_state,
                                              float x, float y, int width,
                                              int height, long long end_tick,
                                              long long span_ticks,
                                              bool maximized = false);
int analog_scope_group_at(const LayoutState &layout_state, float x, float y,
                          int width, int height, bool maximized = false);
bool analog_scope_maximize_at(const LayoutState &layout_state, float x, float y,
                              int width, int height, bool maximized = false);

std::size_t analog_scope_signal_count(int group);
int adc_scope_channel(int group, std::size_t signal);
const profile::Instrument &analog_scope_instrument(int group,
                                                   std::size_t signal);
std::optional<double> analog_scope_value(const ma17::EmulatorSnapshot &sample,
                                         int group, std::size_t signal);

int scope_channel_at(const LayoutState &layout_state, float x, float y,
                     int width, int height);
std::optional<long long> digital_scope_tick_at(const LayoutState &layout_state,
                                               float x, float y, int width,
                                               int height, long long end_tick,
                                               long long span_ticks);
std::optional<DigitalScopeCursor>
digital_scope_cursor_at(const LayoutState &layout_state, float x, float y,
                        int width, int height, long long end_tick,
                        long long span_ticks,
                        const std::vector<ma17::EmulatorEvent> &events,
                        const std::vector<ma17::EmulatorSnapshot> &history);

void draw_lab_trends(SDL_Renderer *renderer, FontRenderer &font,
                     const SDL_FRect &panel, long long tick,
                     const std::deque<TrendPoint> &history);

void draw_oes_left_cluster(SDL_Renderer *renderer, FontRenderer &font,
                           const SDL_FRect &bounds,
                           const ma17::EmulatorSnapshot &snapshot,
                           float ui_scale, bool stale, int selected_gear,
                           DisplayUnits units);

void draw_clutch(SDL_Renderer *renderer, FontRenderer &font,
                 const SDL_FRect &bounds,
                 const ma17::EmulatorSnapshot &snapshot, float ui_scale,
                 bool stale);

SDL_FRect compact_instrument_tab_rect(const SDL_FRect &bounds, int tab);

// What the right cluster needs besides the snapshot: the P5 line that drove each
// coil pair, and the latest measured pulses (D2 injector, D3 coil low time).
struct PulseCluster {
    std::array<int, 2> spark_channels{-1, -1};
    PulseStat injector;
    std::array<PulseStat, 2> coil_low;
};

void draw_oes_right_cluster(SDL_Renderer *renderer, FontRenderer &font,
                            const SDL_FRect &bounds,
                            const ma17::EmulatorSnapshot &snapshot,
                            const std::array<ScenePulse, 4> &pulses,
                            const std::array<float, 2> &spark_glows,
                            float ui_scale, const std::array<Gauge, 3> *gauges,
                            bool stale, int compact_page, DisplayUnits units,
                            const PulseCluster &pulse_data = {});

} // namespace lab
