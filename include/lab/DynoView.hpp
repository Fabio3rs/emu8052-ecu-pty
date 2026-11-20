#pragma once

#include "lab/DynoCurve.hpp"
#include "lab/FontRenderer.hpp"

#include <SDL3/SDL_rect.h>
#include <SDL3/SDL_render.h>

#include <array>
#include <cstdio>
#include <optional>
#include <string>
#include <vector>

namespace lab {

// One stacked panel of the dyno view. Every panel has exactly ONE vertical
// axis (never a dual axis); all panels share the same rpm axis.
struct DynoPanelLayout {
    const char *title;
    const char *unit;
    SDL_FRect plot; // plot area, without the left axis labels
    double y_min;
    double y_max;
};

struct DynoLayout {
    SDL_FRect area;
    double rpm_min = 1000.0;
    double rpm_max = 6500.0;
    std::array<DynoPanelLayout, 4> panels;

    float x_for_rpm(double rpm, const SDL_FRect &plot) const {
        return plot.x + static_cast<float>((rpm - rpm_min) / (rpm_max - rpm_min)) *
                            plot.w;
    }
    static float y_for(double value, const DynoPanelLayout &panel) {
        const double t = (value - panel.y_min) / (panel.y_max - panel.y_min);
        return panel.plot.y + panel.plot.h - static_cast<float>(t) * panel.plot.h;
    }
};

// Pure layout of the four stacked panels (torque, power, advance, lambda)
// inside `area`. `left_margin` is the width reserved for axis labels.
inline DynoLayout compute_dyno_layout(const SDL_FRect &area, float ui_scale,
                                      double rpm_min = 1000.0,
                                      double rpm_max = 6500.0) {
    DynoLayout layout;
    layout.area = area;
    layout.rpm_min = rpm_min;
    layout.rpm_max = rpm_max;
    const float left_margin = 46.0f * ui_scale;
    const float right_margin = 10.0f * ui_scale;
    const float top_margin = 18.0f * ui_scale;   // legend row
    const float bottom_margin = 16.0f * ui_scale; // rpm axis labels
    const float gap = 6.0f * ui_scale;
    const float inner_h = std::max(
        0.0f, area.h - top_margin - bottom_margin - 3.0f * gap);
    // Torque is the main panel; the others are equal and smaller.
    const float torque_h = inner_h * 0.34f;
    const float small_h = (inner_h - torque_h) / 3.0f;
    const std::array<float, 4> heights{torque_h, small_h, small_h, small_h};
    constexpr std::array<const char *, 4> titles{"TORQUE", "POWER", "ADVANCE",
                                                 "LAMBDA"};
    constexpr std::array<const char *, 4> units{"N.m", "kW", "deg BTDC", ""};
    constexpr std::array<double, 4> y_min{60.0, 0.0, 0.0, 0.7};
    constexpr std::array<double, 4> y_max{140.0, 70.0, 40.0, 1.3};
    float y = area.y + top_margin;
    for (std::size_t i = 0; i < layout.panels.size(); ++i) {
        layout.panels[i] = {titles[i], units[i],
                            {area.x + left_margin, y,
                             std::max(0.0f, area.w - left_margin - right_margin),
                             heights[i]},
                            y_min[i], y_max[i]};
        y += heights[i] + gap;
    }
    return layout;
}

// What the view shows. `live` is the steady-state window of the running plant
// (only when valid); the view never invents a point for an N/D window.
struct DynoLivePoint {
    double rpm = 0.0;
    double torque_nm = 0.0;
};

// D6: the live steady-state window as bench measurements. `valid` is false for
// an N/D window (no rotation or an empty window): the readout then says N/D and
// no crosshair is drawn.
struct DynoReadout {
    bool valid = false;
    double rpm = 0.0;
    double torque_nm = 0.0;
    double power_kw = 0.0;
    double bsfc_g_kwh = 0.0; // 0 when the power is too low to define it
    double ve = 0.0;
    double lambda = 0.0;
};

inline std::vector<std::string> dyno_readout_lines(const DynoReadout &readout) {
    if (!readout.valid)
        return {"LIVE N/D"};
    char first[64], second[64];
    std::snprintf(first, sizeof(first), "LIVE %.0f RPM  %.1f N.M  %.1f KW",
                  readout.rpm, readout.torque_nm, readout.power_kw);
    if (readout.bsfc_g_kwh > 0.0)
        std::snprintf(second, sizeof(second), "BSFC %.0f  VE %.2f  LAM %.2f",
                      readout.bsfc_g_kwh, readout.ve, readout.lambda);
    else
        std::snprintf(second, sizeof(second), "BSFC --  VE %.2f  LAM %.2f",
                      readout.ve, readout.lambda);
    return {first, second};
}

// D8: the lines of the BENCH panel that takes the vehicle speed dial's place
// when there is no road input. One value per line, so it reads at a glance;
// an invalid (N/D) window says so and invents nothing.
inline std::vector<std::string> bench_panel_lines(const DynoReadout &readout) {
    if (!readout.valid)
        return {"N/D"};
    char text[5][40];
    std::snprintf(text[0], sizeof(text[0]), "%.0f RPM", readout.rpm);
    std::snprintf(text[1], sizeof(text[1]), "%.1f N.M", readout.torque_nm);
    std::snprintf(text[2], sizeof(text[2]), "%.1f KW", readout.power_kw);
    if (readout.bsfc_g_kwh > 0.0)
        std::snprintf(text[3], sizeof(text[3]), "BSFC %.0f", readout.bsfc_g_kwh);
    else
        std::snprintf(text[3], sizeof(text[3]), "BSFC --");
    std::snprintf(text[4], sizeof(text[4]), "VE %.2f  LAM %.2f", readout.ve,
                  readout.lambda);
    return {text[0], text[1], text[2], text[3], text[4]};
}

struct DynoScene {
    std::vector<DynoCurve> curves; // drawn in order; first with provenance is the ROM
    // Shaded torque band between two ROM curves (the TDC 117..123 hypotheses).
    std::optional<std::pair<DynoCurve, DynoCurve>> rom_band;
    std::optional<DynoLivePoint> live;
    DynoReadout readout;
    std::vector<std::string> sweep_lines;   // RUN WOT: per-point state, newest first
    std::vector<std::string> compare_lines; // K4: deltas between snapshots A and B
    std::string status; // e.g. "no curve data"
};

void draw_dyno_view(SDL_Renderer *renderer, FontRenderer &font,
                    const SDL_FRect &area, const DynoScene &scene,
                    float ui_scale);

// Loads the shipped curves from `docs_dir` (model E0, ROM TDC 120 and the
// 117/123 band). Missing files only shorten the scene; `status` says why.
DynoScene load_default_dyno_scene(const std::string &docs_dir);

} // namespace lab
