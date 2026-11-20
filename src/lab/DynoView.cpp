#include "lab/DynoView.hpp"
#include "lab/TextScale.hpp"
#include "lab/LabTheme.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

namespace lab {
namespace {

constexpr SDL_Color kModelColor{245, 160, 60, 255};   // plant model (E0)
constexpr SDL_Color kRomColor{90, 160, 255, 255};     // ROM sweep (TDC 120)
constexpr SDL_Color kFrozenColor{150, 160, 175, 255}; // kept copy for comparison
constexpr SDL_Color kMbtColor{245, 160, 60, 140};     // model MBT, dim
constexpr SDL_Color kRefColor{235, 241, 246, 255};    // manual reference points
constexpr SDL_Color kAxisColor{145, 177, 190, 255};
constexpr SDL_Color kGridColor{42, 48, 58, 255};

void polyline(SDL_Renderer *renderer, const std::vector<SDL_FPoint> &points,
              SDL_Color color) {
    if (points.size() < 2)
        return;
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_RenderLines(renderer, points.data(), static_cast<int>(points.size()));
}

template <typename Value>
std::vector<SDL_FPoint> curve_points(const DynoLayout &layout, int panel,
                                     const DynoCurve &curve, Value &&value) {
    std::vector<SDL_FPoint> points;
    const auto &p = layout.panels[static_cast<std::size_t>(panel)];
    for (const auto &point : curve.points) {
        const double v = value(point);
        if (!std::isfinite(v))
            continue;
        points.push_back({layout.x_for_rpm(point.rpm, p.plot),
                          DynoLayout::y_for(std::clamp(v, p.y_min, p.y_max), p)});
    }
    return points;
}

void diamond(SDL_Renderer *renderer, float x, float y, float r, SDL_Color c) {
    SDL_SetRenderDrawColor(renderer, c.r, c.g, c.b, c.a);
    const SDL_FPoint pts[5] = {{x, y - r}, {x + r, y}, {x, y + r},
                               {x - r, y}, {x, y - r}};
    SDL_RenderLines(renderer, pts, 5);
}

} // namespace

void draw_dyno_view(SDL_Renderer *renderer, FontRenderer &font,
                    const SDL_FRect &area, const DynoScene &scene,
                    float ui_scale) {
    SDL_SetRenderDrawColor(renderer, 14, 14, 18, 255);
    SDL_RenderFillRect(renderer, &area);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &area);

    const DynoLayout layout = compute_dyno_layout(area, ui_scale);
    const float label_scale = kTextSmall * ui_scale;

    // Legend row.
    float legend_x = area.x + 8.0f * ui_scale;
    const float legend_y = area.y + 4.0f * ui_scale;
    const auto legend = [&](const std::string &text, SDL_Color color) {
        font.draw(renderer, legend_x, legend_y, text, color, label_scale);
        legend_x += (font.width(text, label_scale)) + 14.0f * ui_scale;
    };
    legend("DYNO WOT", {210, 218, 226, 255});
    for (const auto &curve : scene.curves)
        legend(curve.label, curve.frozen ? kFrozenColor
                                         : curve.provenance ? kRomColor : kModelColor);
    if (scene.rom_band)
        legend("ROM TDC 117-123", {90, 160, 255, 140});
    legend("MANUAL", kRefColor);

    for (std::size_t i = 0; i < layout.panels.size(); ++i) {
        const auto &panel = layout.panels[i];
        SDL_SetRenderDrawColor(renderer, 24, 26, 32, 255);
        SDL_RenderFillRect(renderer, &panel.plot);
        SDL_SetRenderDrawColor(renderer, kGridColor.r, kGridColor.g, kGridColor.b,
                               255);
        SDL_RenderRect(renderer, &panel.plot);
        // Vertical grid every 1000 rpm and the rpm labels under the last panel.
        for (double rpm = std::ceil(layout.rpm_min / 1000.0) * 1000.0;
             rpm <= layout.rpm_max; rpm += 1000.0) {
            const float x = layout.x_for_rpm(rpm, panel.plot);
            SDL_RenderLine(renderer, x, panel.plot.y, x,
                           panel.plot.y + panel.plot.h);
            if (i + 1 == layout.panels.size()) {
                char text[16];
                std::snprintf(text, sizeof(text), "%.0f", rpm);
                font.draw(renderer,
                          x - font.width(text, label_scale) * 0.5f,
                          panel.plot.y + panel.plot.h + 3.0f * ui_scale, text,
                          kAxisColor, label_scale);
            }
        }
        // One Y axis per panel: min, max and the panel title.
        char top[16], bottom[16];
        std::snprintf(top, sizeof(top), "%g", panel.y_max);
        std::snprintf(bottom, sizeof(bottom), "%g", panel.y_min);
        font.draw(renderer, area.x + 4.0f * ui_scale, panel.plot.y, top,
                  kAxisColor, label_scale);
        font.draw(renderer, area.x + 4.0f * ui_scale,
                  panel.plot.y + panel.plot.h - 8.0f * ui_scale, bottom,
                  kAxisColor, label_scale);
        std::string title = panel.title;
        if (*panel.unit)
            title += std::string(" ") + panel.unit;
        font.draw(renderer, panel.plot.x + 4.0f * ui_scale,
                  panel.plot.y + 2.0f * ui_scale, title, kAxisColor,
                  label_scale);
    }

    // ROM band: shaded torque between the two TDC hypotheses.
    if (scene.rom_band) {
        const auto &p = layout.panels[0];
        const auto low = curve_points(layout, 0, scene.rom_band->first,
                                      [](const DynoPoint &d) { return d.torque_nm; });
        const auto high = curve_points(layout, 0, scene.rom_band->second,
                                       [](const DynoPoint &d) { return d.torque_nm; });
        const std::size_t n = std::min(low.size(), high.size());
        for (std::size_t i = 0; i + 1 < n; ++i) {
            const SDL_FColor c{0.35f, 0.63f, 1.0f, 0.22f};
            const SDL_Vertex v[6] = {
                {low[i], c, {}},      {low[i + 1], c, {}},  {high[i], c, {}},
                {high[i], c, {}},     {low[i + 1], c, {}},  {high[i + 1], c, {}}};
            SDL_RenderGeometry(renderer, nullptr, v, 6, nullptr, 0);
        }
        (void)p;
    }

    // Curves, each panel with its own axis.
    for (const auto &curve : scene.curves) {
        const bool rom = curve.provenance.has_value();
        const SDL_Color color =
            curve.frozen ? kFrozenColor : rom ? kRomColor : kModelColor;
        polyline(renderer, curve_points(layout, 0, curve,
                     [](const DynoPoint &d) { return d.torque_nm; }), color);
        polyline(renderer, curve_points(layout, 1, curve,
                     [](const DynoPoint &d) { return d.power_kw; }), color);
        polyline(renderer, curve_points(layout, 2, curve,
                     [](const DynoPoint &d) { return d.advance_deg; }), color);
        polyline(renderer, curve_points(layout, 3, curve,
                     [](const DynoPoint &d) { return d.lambda; }), color);
        if (!rom)
            polyline(renderer, curve_points(layout, 2, curve,
                         [](const DynoPoint &d) { return d.mbt_deg; }), kMbtColor);
        if (const DynoPoint *peak = peak_torque(curve)) {
            const auto &p = layout.panels[0];
            const float x = layout.x_for_rpm(peak->rpm, p.plot);
            const float y = DynoLayout::y_for(peak->torque_nm, p);
            diamond(renderer, x, y, 3.0f * ui_scale, color);
            font.draw(renderer, x + 4.0f * ui_scale, y - 10.0f * ui_scale,
                      dyno_point_text(*peak), color, label_scale);
        }
    }

    // Manual reference points (ABNT): 133 N.m @ 3000 rpm, 60.4 kW @ 6000 rpm.
    diamond(renderer, layout.x_for_rpm(3000.0, layout.panels[0].plot),
            DynoLayout::y_for(133.0, layout.panels[0]), 3.5f * ui_scale, kRefColor);
    diamond(renderer, layout.x_for_rpm(6000.0, layout.panels[1].plot),
            DynoLayout::y_for(60.4, layout.panels[1]), 3.5f * ui_scale, kRefColor);

    // Live steady-state window, only when valid.
    if (scene.live) {
        const auto &p = layout.panels[0];
        const float x = layout.x_for_rpm(scene.live->rpm, p.plot);
        const float y = DynoLayout::y_for(scene.live->torque_nm, p);
        SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
        SDL_RenderLine(renderer, x - 5.0f * ui_scale, y, x + 5.0f * ui_scale, y);
        SDL_RenderLine(renderer, x, y - 5.0f * ui_scale, x, y + 5.0f * ui_scale);
    }
    // D6: bench measurements of the live window, right-aligned in the lambda
    // panel (the emptiest one), measured with the snapped draw metrics.
    {
        const auto &p = layout.panels[3];
        float y = p.plot.y + 3.0f * ui_scale;
        const float px = font.text_px(label_scale);
        for (const std::string &line : dyno_readout_lines(scene.readout)) {
            const float w = font.measure_px(line, px);
            font.draw(renderer, p.plot.x + p.plot.w - w - 6.0f * ui_scale, y,
                      line,
                      scene.readout.valid ? SDL_Color{235, 241, 246, 255}
                                          : SDL_Color{145, 177, 190, 255},
                      label_scale);
            y += font.line_height(px) + 2.0f * ui_scale;
        }
    }
    // RUN WOT: the point being measured and the finished ones with their
    // state (STAB / ACC / INVALID: reason), top-left of the lambda panel.
    if (!scene.sweep_lines.empty()) {
        const auto &p = layout.panels[3];
        float y = p.plot.y + 12.0f * ui_scale; // below the panel title
        const float px = font.text_px(label_scale);
        for (const std::string &line : scene.sweep_lines) {
            if (y + font.line_height(px) > p.plot.y + p.plot.h)
                break;
            const bool bad = line.find("INVALID") != std::string::npos;
            font.draw(renderer, p.plot.x + 6.0f * ui_scale, y, line,
                      bad ? SDL_Color{249, 190, 96, 255}
                          : SDL_Color{235, 241, 246, 255},
                      label_scale);
            y += font.line_height(px) + 1.0f * ui_scale;
        }
    }
    // K4: deltas of snapshot B relative to A, top-left of the power panel
    // (power is low at low rpm, so the corner is free).
    if (!scene.compare_lines.empty()) {
        const auto &p = layout.panels[1];
        float y = p.plot.y + 12.0f * ui_scale;
        const float px = font.text_px(label_scale);
        for (const std::string &line : scene.compare_lines) {
            if (y + font.line_height(px) > p.plot.y + p.plot.h)
                break;
            font.draw(renderer, p.plot.x + 6.0f * ui_scale, y, line,
                      {235, 241, 246, 255}, label_scale);
            y += font.line_height(px) + 1.0f * ui_scale;
        }
    }
    if (!scene.status.empty())
        font.draw(renderer, area.x + 8.0f * ui_scale,
                  area.y + area.h - 12.0f * ui_scale, scene.status,
                  kCritical, label_scale);
}

DynoScene load_default_dyno_scene(const std::string &docs_dir) {
    DynoScene scene;
    const auto add = [&](const std::string &file, const std::string &label,
                         std::optional<DynoCurve> *out = nullptr) {
        auto loaded = load_dyno_csv(docs_dir + "/" + file, label);
        if (!loaded.curve) {
            scene.status = label + ": " + loaded.error;
            return;
        }
        if (out)
            *out = *loaded.curve;
        else
            scene.curves.push_back(*loaded.curve);
    };
    add("dyno_wot_e0.csv", "MODEL E0");
    add("dyno/rom/sweep_tdc120.csv", "ROM TDC 120");
    std::optional<DynoCurve> low, high;
    add("dyno/rom/sweep_tdc117.csv", "ROM TDC 117", &low);
    add("dyno/rom/sweep_tdc123.csv", "ROM TDC 123", &high);
    if (low && high)
        scene.rom_band = std::make_pair(*low, *high);
    if (scene.curves.empty() && scene.status.empty())
        scene.status = "no curve data";
    return scene;
}

} // namespace lab
