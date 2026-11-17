#include "lab/LabInstruments.hpp"

#include "constants.h"
#include "gauge.h"
#include "geometry_generator.h"
#include "lab/FontRenderer.hpp"
#include "oscilloscope.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <vector>

namespace lab {

namespace {

void draw_gauge_arc(SDL_Renderer *renderer, float cx, float cy, float r_in,
                    float r_out, float th0, float th1, SDL_Color color) {
    constexpr int max_steps = 24;
    const int steps =
        std::clamp(static_cast<int>(std::abs(th1 - th0) * 12.0f), 4, max_steps);
    std::vector<SDL_Vertex> verts;
    std::vector<int> idxs;
    verts.reserve(static_cast<std::size_t>((steps + 1) * 2));
    idxs.reserve(static_cast<std::size_t>(steps * 6));
    const SDL_FColor fcol{static_cast<float>(color.r) / 255.0f,
                          static_cast<float>(color.g) / 255.0f,
                          static_cast<float>(color.b) / 255.0f,
                          static_cast<float>(color.a) / 255.0f};
    for (int i = 0; i <= steps; ++i) {
        const float t = th0 + (th1 - th0) * (static_cast<float>(i) /
                                             static_cast<float>(steps));
        const float c = std::cos(t), s = std::sin(t);
        verts.push_back({{cx + r_out * c, cy - r_out * s}, fcol, {0.0f, 0.0f}});
        verts.push_back({{cx + r_in * c, cy - r_in * s}, fcol, {0.0f, 0.0f}});
    }
    for (int i = 0; i < steps; ++i) {
        const int i0 = i * 2;
        idxs.push_back(i0);
        idxs.push_back(i0 + 1);
        idxs.push_back(i0 + 2);
        idxs.push_back(i0 + 2);
        idxs.push_back(i0 + 1);
        idxs.push_back(i0 + 3);
    }
    SDL_RenderGeometry(renderer, nullptr, verts.data(),
                       static_cast<int>(verts.size()), idxs.data(),
                       static_cast<int>(idxs.size()));
}

} // namespace

void draw_lab_gauge(SDL_Renderer *renderer, FontRenderer &font, float x,
                    float y, float radius, double value, double maximum,
                    const char *label, SDL_Color accent, float needle_position,
                    float ui_scale, const Gauge *style) {
    // The donor Gauge supplies the sweep and tick intervals when present.
    // Screen coordinates invert the Y direction.
    constexpr float pi = static_cast<float>(constants::pi);
    constexpr int steps = 64;
    const float theta_min = style ? style->m_thetaMin : pi;
    const float theta_max = style ? style->m_thetaMax : 0.0f;
    const auto theta_at = [theta_min, theta_max](float fraction) {
        return theta_min + (theta_max - theta_min) * fraction;
    };
    std::array<SDL_FPoint, steps + 1> arc{};
    SDL_SetRenderDrawColor(renderer, 119, 145, 157, 255);
    for (int i = 0; i <= steps; ++i) {
        const float theta = theta_at(static_cast<float>(i) / steps);
        arc[static_cast<std::size_t>(i)] = {x + radius * std::cos(theta),
                                            y - radius * std::sin(theta)};
    }
    SDL_RenderLines(renderer, arc.data(), static_cast<int>(arc.size()));
    const float range = style ? style->m_max - style->m_min : 10.0f;
    const int minor_step = style ? style->m_minorStep : 1;
    const int major_step = style ? style->m_majorStep : 2;
    const bool donor_ticks = style && std::isfinite(range) && range > 0.0f &&
                             minor_step > 0 && major_step > 0 &&
                             range / static_cast<float>(minor_step) <= 512.0f;
    const int tick_count =
        donor_ticks ? static_cast<int>(range / static_cast<float>(minor_step))
                    : 10;
    for (int i = 0; i <= tick_count; ++i) {
        const long long tick_value =
            static_cast<long long>(i) * static_cast<long long>(minor_step);
        const float fraction =
            donor_ticks
                ? static_cast<float>(tick_value) / range
                : static_cast<float>(i) / static_cast<float>(tick_count);
        const float theta = theta_at(fraction);
        const bool major =
            donor_ticks ? tick_value % major_step == 0 : i % 2 == 0;
        const float length = donor_ticks ? (major ? style->m_majorTickLength
                                                  : style->m_minorTickLength)
                                         : (major ? 15.0f : 8.0f);
        const float inner = radius - length * ui_scale;
        SDL_RenderLine(
            renderer, x + inner * std::cos(theta), y - inner * std::sin(theta),
            x + radius * std::cos(theta), y - radius * std::sin(theta));
    }
    if (style && !style->bands().empty()) {
        for (const auto &band : style->bands()) {
            const float s0 =
                std::clamp((band.start - style->m_min) / range, 0.0f, 1.0f);
            const float s1 =
                std::clamp((band.end - style->m_min) / range, 0.0f, 1.0f);
            const SDL_Color bcol{static_cast<Uint8>(std::clamp(
                                     band.color.x * 255.0f, 0.0f, 255.0f)),
                                 static_cast<Uint8>(std::clamp(
                                     band.color.y * 255.0f, 0.0f, 255.0f)),
                                 static_cast<Uint8>(std::clamp(
                                     band.color.z * 255.0f, 0.0f, 255.0f)),
                                 255};
            draw_gauge_arc(renderer, x, y, radius - 3.5f * ui_scale, radius,
                           theta_at(s0), theta_at(s1), bcol);
        }
    } else if (maximum >= 6000.0) {
        const float s5600 = 5600.0f / static_cast<float>(maximum);
        const float s6000 = 6000.0f / static_cast<float>(maximum);
        draw_gauge_arc(renderer, x, y, radius - 3.5f * ui_scale, radius,
                       theta_at(s5600), theta_at(s6000), {245, 205, 30, 255});
        draw_gauge_arc(renderer, x, y, radius - 3.5f * ui_scale, radius,
                       theta_at(s6000), theta_at(1.0f), {238, 68, 69, 255});
    }

    const float needle = theta_at(needle_position);
    const float nx = std::cos(needle);
    const float ny = -std::sin(needle);
    const float px = -ny;
    const float py = nx;
    const float tip_len = radius * 0.85f;
    const float tail_len = radius * 0.12f;
    const float base_w = 3.0f * ui_scale;

    const SDL_FPoint tip{x + nx * tip_len, y + ny * tip_len};
    const SDL_FPoint tail{x - nx * tail_len, y - ny * tail_len};
    const SDL_FPoint p_l{x + px * base_w, y + py * base_w};
    const SDL_FPoint p_r{x - px * base_w, y - py * base_w};
    const SDL_FColor accent_f{static_cast<float>(accent.r) / 255.0f,
                              static_cast<float>(accent.g) / 255.0f,
                              static_cast<float>(accent.b) / 255.0f, 1.0f};
    std::array<SDL_Vertex, 4> nverts{{
        {tip, accent_f, {0.0f, 0.0f}},
        {p_l, accent_f, {0.0f, 0.0f}},
        {p_r, accent_f, {0.0f, 0.0f}},
        {tail, accent_f, {0.0f, 0.0f}},
    }};
    std::array<int, 6> nidxs{0, 1, 2, 3, 2, 1};
    SDL_RenderGeometry(renderer, nullptr, nverts.data(), 4, nidxs.data(), 6);

    const float r_hub = 5.0f * ui_scale;
    constexpr int hub_steps = 16;
    std::vector<SDL_Vertex> hub_verts;
    std::vector<int> hub_idxs;
    hub_verts.reserve(hub_steps + 2);
    hub_idxs.reserve(hub_steps * 3);
    const SDL_FColor hub_center_col{0.08f, 0.08f, 0.10f, 1.0f};
    const SDL_FColor hub_outer_col{0.18f, 0.20f, 0.24f, 1.0f};
    hub_verts.push_back({{x, y}, hub_center_col, {0.0f, 0.0f}});
    for (int i = 0; i <= hub_steps; ++i) {
        const float a = static_cast<float>(i) * (2.0f * pi / hub_steps);
        hub_verts.push_back({{x + r_hub * std::cos(a), y + r_hub * std::sin(a)},
                             hub_outer_col,
                             {0.0f, 0.0f}});
    }
    for (int i = 1; i <= hub_steps; ++i) {
        hub_idxs.push_back(0);
        hub_idxs.push_back(i);
        hub_idxs.push_back(i + 1);
    }
    SDL_RenderGeometry(renderer, nullptr, hub_verts.data(),
                       static_cast<int>(hub_verts.size()), hub_idxs.data(),
                       static_cast<int>(hub_idxs.size()));
    std::array<SDL_FPoint, hub_steps + 1> rim_pts{};
    for (int i = 0; i <= hub_steps; ++i) {
        const float a = static_cast<float>(i) * (2.0f * pi / hub_steps);
        rim_pts[static_cast<std::size_t>(i)] = {x + r_hub * std::cos(a),
                                                y + r_hub * std::sin(a)};
    }
    SDL_SetRenderDrawColor(renderer, accent.r, accent.g, accent.b, 255);
    SDL_RenderLines(renderer, rim_pts.data(), static_cast<int>(rim_pts.size()));
    std::array<char, 80> text{};
    std::snprintf(text.data(), text.size(), "%s %.0f", label, value);
    font.draw(renderer, x - font.measure(text.data()) * ui_scale / 2.0f,
              y + 13.0f * ui_scale, text.data(), accent, ui_scale);
    std::array<char, 16> scale_text{};
    std::snprintf(scale_text.data(), scale_text.size(), "%.0f", maximum);
    font.draw(renderer, x + radius - font.measure(scale_text.data()) * ui_scale,
              y + 2.0f * ui_scale, scale_text.data(), accent, ui_scale);
}

namespace {

class OwnedGeometryGenerator final : public GeometryGenerator {
  public:
    ~OwnedGeometryGenerator() { destroy(); }
};

void draw_donor_trace(SDL_Renderer *renderer,
                      const std::vector<SDL_FPoint> &trace, SDL_Color color) {
    // The donor Oscilloscope builds a tapered path with GeometryGenerator.
    // Keep SDL's line path for oversized windows beyond 16-bit mesh indices.
    if (trace.size() > 5000) {
        SDL_RenderLines(renderer, trace.data(), static_cast<int>(trace.size()));
        return;
    }
    Oscilloscope scope;
    scope.setBufferSize(trace.size());
    Point previous;
    bool has_previous = false;
    for (const auto &point : trace) {
        if (has_previous && previous.x == point.x && previous.y == point.y)
            continue;
        scope.addDataPoint(static_cast<double>(point.x),
                           static_cast<double>(point.y));
        previous = Point(point.x, point.y);
        has_previous = true;
    }
    auto points = scope.orderedPoints();
    if (points.size() < 2)
        return;

    OwnedGeometryGenerator generator;
    generator.initialize(static_cast<int>(points.size() * 2),
                         static_cast<int>((points.size() - 1) * 6));
    generator.startShape();
    GeometryGenerator::PathParameters path{};
    path.p0 = points.data();
    path.n0 = static_cast<int>(points.size());
    path.width = 1.4f;
    if (!generator.startPath(path))
        return;
    for (int index = 1; index < path.n0; ++index) {
        path.i = index;
        generator.generatePathSegment(path, false);
    }
    GeometryGenerator::GeometryIndices shape;
    generator.endShape(&shape);

    std::vector<SDL_Vertex> vertices;
    vertices.reserve(
        static_cast<std::size_t>(generator.getCurrentVertexCount()));
    const SDL_FColor tint{static_cast<float>(color.r) / 255.0f,
                          static_cast<float>(color.g) / 255.0f,
                          static_cast<float>(color.b) / 255.0f, 1.0f};
    for (int index = 0; index < generator.getCurrentVertexCount(); ++index) {
        const auto &vertex = generator.getVertexData()[index];
        vertices.push_back({{vertex.Pos.x, vertex.Pos.y}, tint, {0.0f, 0.0f}});
    }
    std::vector<int> indices;
    indices.reserve(static_cast<std::size_t>(generator.getCurrentIndexCount()));
    for (int index = 0; index < generator.getCurrentIndexCount(); ++index)
        indices.push_back(generator.getIndexData()[index]);
    SDL_RenderGeometry(renderer, nullptr, vertices.data(),
                       static_cast<int>(vertices.size()), indices.data(),
                       static_cast<int>(indices.size()));
}

float scope_scale(int width, int height) {
    return std::clamp(std::min(static_cast<float>(width) / 1280.0f,
                               static_cast<float>(height) / 720.0f),
                      1.0f, 2.0f);
}

} // namespace

int scope_channel_at(float x, float y, int width, int height) {
    const float label_width = 138.0f * scope_scale(width, height);
    if (width < 200 || height < 200 || x < 20.0f || x >= 20.0f + label_width)
        return -1;
    const float first_row = static_cast<float>(height) - 138.0f;
    for (int channel = 0; channel < 3; ++channel) {
        const float row = first_row + 36.0f * static_cast<float>(channel);
        if (y >= row && y < row + 32.0f)
            return channel;
    }
    return -1;
}

void draw_lab_scope(SDL_Renderer *renderer, FontRenderer &font, int width,
                    int height, long long tick,
                    const std::vector<ma17::EmulatorEvent> &events,
                    const std::array<bool, 3> &channels_visible,
                    long long span_ticks) {
    const float scale = scope_scale(width, height);
    const float left = 26.0f + 138.0f * scale;
    const float right = static_cast<float>(width) - 24.0f;
    const float top = static_cast<float>(height) - 146.0f;
    const SDL_FRect panel{16.0f, top - 12.0f, static_cast<float>(width) - 32.0f,
                          146.0f};
    SDL_SetRenderDrawColor(renderer, 20, 20, 24, 255);
    SDL_RenderFillRect(renderer, &panel);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &panel);
    const long long span = std::clamp(span_ticks, 247500LL, 3960000LL);
    char zoom_label[48];
    std::snprintf(zoom_label, sizeof(zoom_label), "SCOPE %.2f S | WHEEL ZOOM",
                  static_cast<double>(span) / 990000.0);
    font.draw(renderer, right - font.measure(zoom_label) * scale,
              panel.y + 2.0f, zoom_label, {145, 177, 190, 255}, scale);
    const long long first_tick = std::max(0LL, tick - span);
    const auto x_for_tick = [first_tick, span, left, right](long long at) {
        return left + (right - left) * static_cast<float>(at - first_tick) /
                          static_cast<float>(span);
    };
    SDL_SetRenderDrawColor(renderer, 55, 74, 88, 255);
    for (int i = 0; i <= 4; ++i) {
        const float x = left + (right - left) * static_cast<float>(i) / 4.0f;
        SDL_RenderLine(renderer, x, top, x, top + 106.0f);
    }
    constexpr std::array<const char *, 3> labels{"CC3", "P5.0", "P5.1"};
    constexpr std::array<SDL_Color, 3> colors{
        {{249, 190, 96, 255}, {99, 211, 220, 255}, {200, 144, 232, 255}}};
    for (int channel = 0; channel < 3; ++channel) {
        const auto index = static_cast<std::size_t>(channel);
        const float y = top + 14.0f + static_cast<float>(channel) * 36.0f;
        const bool visible = channels_visible[index];
        const SDL_FRect selector{20.0f, y - 6.0f, 138.0f * scale, 32.0f};
        SDL_SetRenderDrawColor(renderer, visible ? 40 : 27, visible ? 58 : 38,
                               visible ? 68 : 48, 255);
        SDL_RenderFillRect(renderer, &selector);
        const auto &accent = colors[index];
        SDL_SetRenderDrawColor(renderer, visible ? accent.r : 69,
                               visible ? accent.g : 84, visible ? accent.b : 94,
                               255);
        SDL_RenderRect(renderer, &selector);
        if (!visible) {
            font.draw(renderer, 24.0f, y + 1.0f, labels[index],
                      {105, 121, 131, 255}, scale);
            continue;
        }

        // Channel baseline guide
        SDL_SetRenderDrawColor(renderer, 35, 45, 52, 255);
        SDL_RenderLine(renderer, left, y + 13.0f, right, y + 13.0f);

        const auto matches = [channel](const ma17::EmulatorEvent &event) {
            return channel == 0
                       ? event.type == ma17::EmulatorEventType::InjectorPin
                       : event.type == ma17::EmulatorEventType::IgnitionPin &&
                             event.channel ==
                                 static_cast<unsigned>(channel - 1);
        };
        bool high = false;
        long long rise_tick = -1;
        long long last_high_ticks = -1;
        std::vector<SDL_FPoint> trace;
        trace.reserve(128);
        std::vector<SDL_FRect> high_rects;
        high_rects.reserve(32);
        float high_start_x = -1.0f;

        for (const auto &event : events) {
            if (!matches(event) || event.tick > tick)
                continue;
            if (event.high && !high)
                rise_tick = event.tick;
            else if (!event.high && high && rise_tick >= 0)
                last_high_ticks = event.tick - rise_tick;
            if (event.tick < first_tick) {
                high = event.high;
                high_start_x = high ? left : -1.0f;
                continue;
            }
            if (trace.empty())
                trace.push_back({left, y + (high ? 0.0f : 13.0f)});
            const float x = x_for_tick(event.tick);
            trace.push_back({x, y + (high ? 0.0f : 13.0f)});

            if (event.high && !high) {
                high_start_x = x;
            } else if (!event.high && high) {
                const float start_x =
                    high_start_x >= 0.0f ? high_start_x : left;
                const float pulse_w = std::max(x - start_x, 1.5f);
                high_rects.push_back({start_x, y, pulse_w, 13.0f});
                high_start_x = -1.0f;
            }

            high = event.high;
            trace.push_back({x, y + (high ? 0.0f : 13.0f)});
        }
        if (trace.empty())
            trace.push_back({left, y + (high ? 0.0f : 13.0f)});
        trace.push_back({right, y + (high ? 0.0f : 13.0f)});

        if (high && high_start_x >= 0.0f && right > high_start_x) {
            const float pulse_w = std::max(right - high_start_x, 1.5f);
            high_rects.push_back({high_start_x, y, pulse_w, 13.0f});
        }

        const auto &color = colors[static_cast<std::size_t>(channel)];

        // Render translucent filled high pulses (dwell / injection duration)
        SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
        SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, 65);
        for (const auto &rect : high_rects) {
            SDL_RenderFillRect(renderer, &rect);
        }
        SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);

        std::array<char, 32> label{};
        if (last_high_ticks >= 0)
            std::snprintf(label.data(), label.size(), "%s H %.2f ms",
                          labels[static_cast<std::size_t>(channel)],
                          static_cast<double>(last_high_ticks) / 990.0);
        else
            std::snprintf(label.data(), label.size(), "%s H --",
                          labels[static_cast<std::size_t>(channel)]);
        font.draw(renderer, 24.0f, y + 1.0f, label.data(), color, scale);
        draw_donor_trace(renderer, trace, color);
        SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, 255);
        SDL_RenderLines(renderer, trace.data(), static_cast<int>(trace.size()));
    }
}

void draw_lab_trends(SDL_Renderer *renderer, FontRenderer &font,
                     const SDL_FRect &panel, long long tick,
                     const std::deque<TrendPoint> &history) {
    SDL_SetRenderDrawColor(renderer, 20, 20, 24, 255);
    SDL_RenderFillRect(renderer, &panel);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &panel);
    constexpr long long span_ticks = 5LL * 990000;
    const long long first_tick = std::max(0LL, tick - span_ticks);
    const float visible_span =
        static_cast<float>(std::max(1LL, tick - first_tick));
    constexpr std::array<const char *, 2> labels{"RPM", "LAM"};
    constexpr std::array<SDL_Color, 2> colors{
        {{249, 190, 96, 255}, {200, 144, 232, 255}}};
    const float band_height = (panel.h - 14.0f) / 2.0f;
    for (std::size_t channel = 0; channel < labels.size(); ++channel) {
        const float baseline =
            panel.y + 11.0f + band_height * static_cast<float>(channel + 1);
        SDL_SetRenderDrawColor(renderer, 55, 74, 88, 255);
        SDL_RenderLine(renderer, panel.x + 44.0f, baseline,
                       panel.x + panel.w - 8.0f, baseline);
        const auto &color = colors[channel];
        SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, 255);
        font.draw(renderer, panel.x + 7.0f, baseline - band_height + 2.0f,
                  labels[channel], color);
        std::vector<SDL_FPoint> trace;
        trace.reserve(history.size());
        for (const auto &point : history) {
            if (point.tick < first_tick || point.tick > tick)
                continue;
            const double value = channel == 0 ? point.rpm : point.lambda;
            const double maximum = channel == 0 ? 8000.0 : 5.0;
            const float fraction =
                static_cast<float>(std::clamp(value / maximum, 0.0, 1.0));
            const float time =
                static_cast<float>(point.tick - first_tick) / visible_span;
            trace.push_back({panel.x + 44.0f + time * (panel.w - 52.0f),
                             baseline - fraction * (band_height - 4.0f)});
        }
        if (trace.size() >= 2)
            SDL_RenderLines(renderer, trace.data(),
                            static_cast<int>(trace.size()));
        else if (trace.size() == 1)
            SDL_RenderLine(renderer, trace[0].x, trace[0].y, trace[0].x + 1.0f,
                           trace[0].y);
    }
}

namespace {

struct OesDialBand {
    float start;
    float end;
    SDL_Color color;
};

void draw_oes_dial(SDL_Renderer *renderer, FontRenderer &font,
                   const SDL_FRect &box, const char *title, double value,
                   double v_min, double v_max, double major_step,
                   double minor_step, const char *value_str, float needle_pos,
                   float ui_scale, const std::vector<OesDialBand> &bands = {}) {
    SDL_SetRenderDrawColor(renderer, 14, 14, 18, 255);
    SDL_RenderFillRect(renderer, &box);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &box);

    const float title_h = 16.0f * ui_scale;
    const float title_w = font.measure(title) * 0.70f * ui_scale;
    font.draw(renderer, box.x + (box.w - title_w) * 0.5f,
              box.y + 4.0f * ui_scale, title, {210, 218, 226, 255},
              0.70f * ui_scale);

    const float cx = box.x + box.w * 0.5f;
    const float cy =
        box.y + title_h + (box.h - title_h - 14.0f * ui_scale) * 0.52f;
    const float radius =
        std::min(box.w * 0.44f, (box.h - title_h - 16.0f * ui_scale) * 0.50f);
    if (radius <= 6.0f)
        return;

    constexpr float th_min = 1.20f * 3.14159265f;
    constexpr float th_max = -0.20f * 3.14159265f;
    const auto theta_at = [&](float fraction) {
        return th_min + std::clamp(fraction, 0.0f, 1.0f) * (th_max - th_min);
    };

    const float range = static_cast<float>(v_max - v_min);

    for (const auto &b : bands) {
        const float s0 = std::clamp(
            (b.start - static_cast<float>(v_min)) / range, 0.0f, 1.0f);
        const float s1 =
            std::clamp((b.end - static_cast<float>(v_min)) / range, 0.0f, 1.0f);
        draw_gauge_arc(renderer, cx, cy, radius - 3.0f * ui_scale, radius,
                       theta_at(s0), theta_at(s1), b.color);
    }

    if (minor_step > 0.0 && range > 0.0f) {
        const int n_ticks = static_cast<int>(
            std::round(static_cast<double>(range) / minor_step));
        for (int i = 0; i <= n_ticks; ++i) {
            const double cur_v = v_min + static_cast<double>(i) * minor_step;
            const float frac = static_cast<float>((cur_v - v_min) /
                                                  static_cast<double>(range));
            const float th = theta_at(frac);
            const float c = std::cos(th), s = std::sin(th);
            const bool is_major =
                (major_step > 0.0) &&
                (std::fmod(static_cast<double>(i) * minor_step + 1e-4,
                           major_step) < 2e-4 ||
                 std::fmod(static_cast<double>(i) * minor_step - 1e-4,
                           major_step) < 2e-4);
            const float tick_len = (is_major ? 5.5f : 3.0f) * ui_scale;
            const SDL_Color tcol = is_major ? SDL_Color{200, 208, 216, 255}
                                            : SDL_Color{90, 98, 110, 255};
            SDL_SetRenderDrawColor(renderer, tcol.r, tcol.g, tcol.b, 255);
            SDL_RenderLine(renderer, cx + (radius - tick_len) * c,
                           cy - (radius - tick_len) * s, cx + radius * c,
                           cy - radius * s);
        }
    }

    const float n_frac =
        needle_pos >= 0.0f
            ? needle_pos
            : static_cast<float>(std::clamp(
                  (value - v_min) / static_cast<double>(range), 0.0, 1.0));
    const float needle_th = theta_at(n_frac);
    const float nx = std::cos(needle_th);
    const float ny = -std::sin(needle_th);
    const float px = -ny, py = nx;
    const float tip_len = radius * 0.88f;
    const float tail_len = radius * 0.14f;
    const float base_w = 2.0f * ui_scale;

    const SDL_FPoint tip{cx + nx * tip_len, cy + ny * tip_len};
    const SDL_FPoint tail{cx - nx * tail_len, cy - ny * tail_len};
    const SDL_FPoint p_l{cx + px * base_w, cy + py * base_w};
    const SDL_FPoint p_r{cx - px * base_w, cy - py * base_w};
    const SDL_FColor needle_col{0.93f, 0.27f, 0.27f, 1.0f};
    std::array<SDL_Vertex, 4> nverts{{
        {tip, needle_col, {0.0f, 0.0f}},
        {p_l, needle_col, {0.0f, 0.0f}},
        {p_r, needle_col, {0.0f, 0.0f}},
        {tail, needle_col, {0.0f, 0.0f}},
    }};
    std::array<int, 6> nidxs{0, 1, 2, 3, 2, 1};
    SDL_RenderGeometry(renderer, nullptr, nverts.data(), 4, nidxs.data(), 6);

    const float r_hub = 4.0f * ui_scale;
    const SDL_FRect hub_rect{cx - r_hub, cy - r_hub, r_hub * 2.0f,
                             r_hub * 2.0f};
    SDL_SetRenderDrawColor(renderer, 28, 30, 36, 255);
    SDL_RenderFillRect(renderer, &hub_rect);
    SDL_SetRenderDrawColor(renderer, 70, 75, 88, 255);
    SDL_RenderRect(renderer, &hub_rect);

    const float val_scale = (radius < 35.0f ? 0.65f : 0.80f) * ui_scale;
    const float val_w = font.measure(value_str) * val_scale;
    font.draw(renderer, box.x + (box.w - val_w) * 0.5f,
              box.y + box.h - 13.0f * ui_scale, value_str, {240, 244, 248, 255},
              val_scale);
}

void draw_oes_ignition(SDL_Renderer *renderer, FontRenderer &font,
                       const SDL_FRect &box,
                       const std::array<ScenePulse, 4> &pulses,
                       const std::array<float, 2> &spark_glows,
                       float ui_scale) {
    SDL_SetRenderDrawColor(renderer, 14, 14, 18, 255);
    SDL_RenderFillRect(renderer, &box);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &box);

    const float title_w = font.measure("IGNITION") * 0.65f * ui_scale;
    font.draw(renderer, box.x + (box.w - title_w) * 0.5f,
              box.y + 4.0f * ui_scale, "IGNITION", {210, 218, 226, 255},
              0.65f * ui_scale);

    const float top_y = box.y + 20.0f * ui_scale;
    const float avail_h = box.h - 24.0f * ui_scale;
    const float step_y = avail_h / 4.0f;
    const float cx = box.x + box.w * 0.5f;
    const float max_r = std::min(box.w * 0.35f, step_y * 0.38f);

    for (int cyl = 0; cyl < 4; ++cyl) {
        const float cy = top_y + (static_cast<float>(cyl) + 0.5f) * step_y;
        const float spark_glow = spark_glows[cyl == 0 || cyl == 3 ? 0 : 1];
        const float strength = std::max(
            pulses[static_cast<std::size_t>(cyl)].strength, spark_glow);
        const bool lit = strength > 0.05f;

        const SDL_FRect ring_rect{cx - max_r, cy - max_r, max_r * 2.0f,
                                  max_r * 2.0f};
        SDL_SetRenderDrawColor(renderer, 42, 46, 56, 255);
        SDL_RenderRect(renderer, &ring_rect);

        const float r_inner = max_r - 2.0f * ui_scale;
        const SDL_FRect disc_rect{cx - r_inner, cy - r_inner, r_inner * 2.0f,
                                  r_inner * 2.0f};
        if (lit) {
            const Uint8 r =
                static_cast<Uint8>(std::clamp(255.0f * strength, 0.0f, 255.0f));
            const Uint8 g =
                static_cast<Uint8>(std::clamp(230.0f * strength, 0.0f, 255.0f));
            const Uint8 b =
                static_cast<Uint8>(std::clamp(100.0f * strength, 0.0f, 255.0f));
            SDL_SetRenderDrawColor(renderer, r, g, b, 255);
        } else {
            SDL_SetRenderDrawColor(renderer, 24, 26, 32, 255);
        }
        SDL_RenderFillRect(renderer, &disc_rect);

        char num[4];
        std::snprintf(num, sizeof(num), "%d", cyl + 1);
        const float nw = font.measure(num) * 0.60f * ui_scale;
        font.draw(renderer, cx - nw * 0.5f, cy - 4.0f * ui_scale, num,
                  lit ? SDL_Color{20, 20, 20, 255}
                      : SDL_Color{100, 110, 125, 255},
                  0.60f * ui_scale);
    }
}

void draw_oes_throttle(SDL_Renderer *renderer, FontRenderer &font,
                       const SDL_FRect &box,
                       const ma17::EmulatorSnapshot &snapshot, float ui_scale) {
    SDL_SetRenderDrawColor(renderer, 14, 14, 18, 255);
    SDL_RenderFillRect(renderer, &box);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &box);

    const float title_w = font.measure("THROTTLE") * 0.70f * ui_scale;
    font.draw(renderer, box.x + (box.w - title_w) * 0.5f,
              box.y + 4.0f * ui_scale, "THROTTLE", {210, 218, 226, 255},
              0.70f * ui_scale);

    const float slider_w = 12.0f * ui_scale;
    const SDL_FRect slider_box{box.x + box.w - slider_w - 6.0f * ui_scale,
                               box.y + 20.0f * ui_scale, slider_w,
                               box.h - 26.0f * ui_scale};
    SDL_SetRenderDrawColor(renderer, 24, 26, 32, 255);
    SDL_RenderFillRect(renderer, &slider_box);
    SDL_SetRenderDrawColor(renderer, 58, 64, 76, 255);
    SDL_RenderRect(renderer, &slider_box);

    const float pedal_frac =
        static_cast<float>(std::clamp(snapshot.pedal_pull_m / 0.025, 0.0, 1.0));
    const float fill_h = (slider_box.h - 2.0f) * pedal_frac;
    const SDL_FRect slider_fill{slider_box.x + 1.0f,
                                slider_box.y + slider_box.h - 1.0f - fill_h,
                                slider_box.w - 2.0f, fill_h};
    SDL_SetRenderDrawColor(renderer, 238, 68, 69, 255);
    SDL_RenderFillRect(renderer, &slider_fill);

    const float bore_area_w = slider_box.x - box.x - 8.0f * ui_scale;
    const float cx = box.x + bore_area_w * 0.5f;
    const float cy =
        box.y + 20.0f * ui_scale + (box.h - 48.0f * ui_scale) * 0.45f;
    const float bore_w =
        std::min(bore_area_w * 0.50f, (box.h - 48.0f * ui_scale) * 0.50f);
    const float bore_h = bore_w * 1.30f;

    SDL_SetRenderDrawColor(renderer, 210, 218, 226, 255);
    SDL_RenderLine(renderer, cx - bore_w * 0.5f, cy - bore_h * 0.5f,
                   cx - bore_w * 0.5f, cy + bore_h * 0.5f);
    SDL_RenderLine(renderer, cx + bore_w * 0.5f, cy - bore_h * 0.5f,
                   cx + bore_w * 0.5f, cy + bore_h * 0.5f);

    const float th_angle = static_cast<float>(snapshot.throttle_angle_rad);
    const float plate_len = bore_w * 0.85f;
    const float c_th = std::cos(th_angle);
    const float s_th = std::sin(th_angle);
    SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
    SDL_RenderLine(renderer, cx - c_th * plate_len * 0.5f,
                   cy + s_th * plate_len * 0.5f, cx + c_th * plate_len * 0.5f,
                   cy - s_th * plate_len * 0.5f);

    const float r_piv = 2.5f * ui_scale;
    const SDL_FRect piv_rect{cx - r_piv, cy - r_piv, r_piv * 2.0f,
                             r_piv * 2.0f};
    SDL_SetRenderDrawColor(renderer, 238, 68, 69, 255);
    SDL_RenderFillRect(renderer, &piv_rect);

    char stem_buf[32];
    std::snprintf(stem_buf, sizeof(stem_buf), "STEM: %.2f mm",
                  snapshot.idle_stem_m * 1000.0);
    font.draw(renderer, box.x + 6.0f * ui_scale,
              box.y + box.h - 22.0f * ui_scale, stem_buf, {160, 185, 200, 255},
              0.60f * ui_scale);

    const bool sw_closed = snapshot.idle_contact_closed;
    char sw_buf[32];
    std::snprintf(sw_buf, sizeof(sw_buf), "IDLE SW: %s",
                  sw_closed ? "CLOSED" : "OPEN");
    font.draw(renderer, box.x + 6.0f * ui_scale,
              box.y + box.h - 11.0f * ui_scale, sw_buf,
              sw_closed ? SDL_Color{60, 232, 130, 255}
                        : SDL_Color{130, 140, 155, 255},
              0.60f * ui_scale);
}

void draw_oes_fuel(SDL_Renderer *renderer, FontRenderer &font,
                   const SDL_FRect &box, const ma17::EmulatorSnapshot &snapshot,
                   float ui_scale) {
    SDL_SetRenderDrawColor(renderer, 14, 14, 18, 255);
    SDL_RenderFillRect(renderer, &box);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &box);

    const float title_w = font.measure("FUEL") * 0.70f * ui_scale;
    font.draw(renderer, box.x + (box.w - title_w) * 0.5f,
              box.y + 4.0f * ui_scale, "FUEL", {210, 218, 226, 255},
              0.70f * ui_scale);

    const double fuel_l =
        static_cast<double>(snapshot.injector_pulses) * 0.000003;
    char liters_buf[32];
    std::snprintf(liters_buf, sizeof(liters_buf), "%.3f L", fuel_l);
    font.draw(renderer, box.x + 8.0f * ui_scale, box.y + 20.0f * ui_scale,
              liters_buf, {255, 255, 255, 255}, 0.95f * ui_scale);

    char gal_buf[32];
    std::snprintf(gal_buf, sizeof(gal_buf), "%.3f GAL", fuel_l * 0.264172);
    font.draw(renderer, box.x + 8.0f * ui_scale, box.y + 36.0f * ui_scale,
              gal_buf, {150, 165, 180, 255}, 0.60f * ui_scale);

    char film_buf[32];
    std::snprintf(film_buf, sizeof(film_buf), "FILM: %.1f mg",
                  snapshot.fuel_film_kg * 1e6);
    font.draw(renderer, box.x + 8.0f * ui_scale, box.y + 48.0f * ui_scale,
              film_buf, {184, 210, 140, 255}, 0.60f * ui_scale);

    char inj_buf[32];
    std::snprintf(inj_buf, sizeof(inj_buf), "PULSES: %llu",
                  snapshot.injector_pulses);
    font.draw(renderer, box.x + 8.0f * ui_scale, box.y + 60.0f * ui_scale,
              inj_buf, {140, 180, 220, 255}, 0.60f * ui_scale);
}

} // namespace

void draw_oes_right_cluster(SDL_Renderer *renderer, FontRenderer &font,
                            const SDL_FRect &bounds,
                            const ma17::EmulatorSnapshot &snapshot,
                            const std::array<ScenePulse, 4> &pulses,
                            const std::array<float, 2> &spark_glows,
                            float ui_scale,
                            const std::array<Gauge, 3> *gauges) {
    if (bounds.w < 100.0f || bounds.h < 100.0f)
        return;

    SDL_SetRenderDrawColor(renderer, 10, 10, 12, 255);
    SDL_RenderFillRect(renderer, &bounds);
    SDL_SetRenderDrawColor(renderer, 38, 38, 46, 255);
    SDL_RenderRect(renderer, &bounds);

    const float mid_gap_h = (bounds.h >= 400.0f) ? 36.0f * ui_scale : 4.0f;
    const float top_h = (bounds.h - mid_gap_h) * 0.60f;
    const float bot_y = bounds.y + top_h + mid_gap_h;
    const float bot_h = bounds.y + bounds.h - bot_y;

    const float top_left_w = bounds.w * 0.72f;
    const float top_right_w = bounds.w - top_left_w;
    const float dial_h = top_h * 0.50f;

    const SDL_FRect tach_box{bounds.x, bounds.y, top_left_w, dial_h};
    char rpm_str[32];
    std::snprintf(rpm_str, sizeof(rpm_str), "%.0f RPM", snapshot.rpm);
    const float tach_needle = gauges ? (*gauges)[0].needlePosition() : -1.0f;
    std::vector<OesDialBand> tach_bands{
        {400.0f, 1000.0f, {0, 229, 255, 255}},
        {5600.0f, 6000.0f, {245, 205, 30, 255}},
        {6000.0f, 8000.0f, {238, 68, 69, 255}},
    };
    draw_oes_dial(renderer, font, tach_box, "ENGINE SPEED", snapshot.rpm, 0.0,
                  8000.0, 1000.0, 200.0, rpm_str, tach_needle, ui_scale,
                  tach_bands);

    const SDL_FRect speed_box{bounds.x, bounds.y + dial_h, top_left_w, dial_h};
    char spd_str[32];
    std::snprintf(spd_str, sizeof(spd_str), "%.0f KM/H",
                  snapshot.vehicle_speed_kmh);
    draw_oes_dial(renderer, font, speed_box, "VEHICLE SPEED",
                  snapshot.vehicle_speed_kmh, 0.0, 200.0, 20.0, 10.0, spd_str,
                  -1.0f, ui_scale);

    const SDL_FRect ign_box{bounds.x + top_left_w, bounds.y, top_right_w,
                            top_h};
    draw_oes_ignition(renderer, font, ign_box, pulses, spark_glows, ui_scale);

    const float bot_left_w = bounds.w * 0.50f;
    const float bot_right_w = bounds.w - bot_left_w;
    const float bot_sub_h = bot_h * 0.50f;

    const SDL_FRect thr_box{bounds.x, bot_y, bot_left_w, bot_sub_h};
    draw_oes_throttle(renderer, font, thr_box, snapshot, ui_scale);

    const float afr_w = bot_left_w * 0.48f;
    const float fuel_w = bot_left_w - afr_w;
    const float afr_sub_h = bot_sub_h * 0.50f;

    const SDL_FRect in_afr_box{bounds.x, bot_y + bot_sub_h, afr_w, afr_sub_h};
    const double in_afr_val = snapshot.lambda * 14.7;
    char afr_str[16];
    std::snprintf(afr_str, sizeof(afr_str), "%.1f", in_afr_val);
    draw_oes_dial(renderer, font, in_afr_box, "IN. AFR", in_afr_val, 0.0, 25.0,
                  5.0, 1.0, afr_str, -1.0f, ui_scale);

    const SDL_FRect ex_o2_box{bounds.x, bot_y + bot_sub_h + afr_sub_h, afr_w,
                              afr_sub_h};
    char o2_str[16];
    std::snprintf(o2_str, sizeof(o2_str), "%.2f", snapshot.lambda);
    draw_oes_dial(renderer, font, ex_o2_box, "EX. O2", snapshot.lambda, 0.0,
                  2.0, 0.5, 0.1, o2_str, -1.0f, ui_scale);

    const SDL_FRect fuel_box{bounds.x + afr_w, bot_y + bot_sub_h, fuel_w,
                             bot_sub_h};
    draw_oes_fuel(renderer, font, fuel_box, snapshot, ui_scale);

    const float g3_h = bot_h / 3.0f;
    const float g3_x = bounds.x + bot_left_w;

    const SDL_FRect map_box{g3_x, bot_y, bot_right_w, g3_h};
    const double p_manifold_bar =
        0.28 + 0.72 * std::sin(snapshot.throttle_angle_rad);
    const double inhg = (p_manifold_bar - 1.0) * 29.92;
    char map_str[32];
    std::snprintf(map_str, sizeof(map_str), "%.0f INHG", inhg);
    std::vector<OesDialBand> map_bands{
        {-30.0f, -10.0f, {0, 229, 255, 255}},
        {-10.0f, 0.0f, {244, 128, 42, 255}},
        {0.0f, 5.0f, {238, 68, 69, 255}},
    };
    draw_oes_dial(renderer, font, map_box, "MANIFOLD PRESSURE", inhg, -30.0,
                  5.0, 5.0, 1.0, map_str, -1.0f, ui_scale, map_bands);

    const SDL_FRect cfm_box{g3_x, bot_y + g3_h, bot_right_w, g3_h};
    const double ve_ratio =
        0.85 * (0.25 + 0.75 * std::sin(snapshot.throttle_angle_rad));
    const double air_scfm = 0.0279 * snapshot.rpm * ve_ratio;
    char cfm_str[32];
    std::snprintf(cfm_str, sizeof(cfm_str), "%.1f SCFM", air_scfm);
    draw_oes_dial(renderer, font, cfm_box, "AIR SCFM", air_scfm, 0.0, 150.0,
                  25.0, 5.0, cfm_str, -1.0f, ui_scale);

    const SDL_FRect ve_box{g3_x, bot_y + g3_h * 2.0f, bot_right_w, g3_h};
    const double ve_pct = ve_ratio * 100.0;
    char ve_str[32];
    std::snprintf(ve_str, sizeof(ve_str), "%.1f%%", ve_pct);
    std::vector<OesDialBand> ve_bands{
        {30.0f, 80.0f, {52, 152, 219, 255}},
        {80.0f, 100.0f, {46, 204, 113, 255}},
        {100.0f, 120.0f, {238, 68, 69, 255}},
    };
    draw_oes_dial(renderer, font, ve_box, "VOLUMETRIC EFF.", ve_pct, 0.0, 120.0,
                  20.0, 5.0, ve_str, -1.0f, ui_scale, ve_bands);
}

} // namespace lab
