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
    const int tick_count = donor_ticks
                               ? static_cast<int>(range /
                                                  static_cast<float>(minor_step))
                               : 10;
    for (int i = 0; i <= tick_count; ++i) {
        const long long tick_value =
            static_cast<long long>(i) * static_cast<long long>(minor_step);
        const float fraction = donor_ticks
                                   ? static_cast<float>(tick_value) / range
                                   : static_cast<float>(i) /
                                         static_cast<float>(tick_count);
        const float theta = theta_at(fraction);
        const bool major = donor_ticks ? tick_value % major_step == 0
                                       : i % 2 == 0;
        const float length = donor_ticks
                                 ? (major ? style->m_majorTickLength
                                          : style->m_minorTickLength)
                                 : (major ? 15.0f : 8.0f);
        const float inner = radius - length * ui_scale;
        SDL_RenderLine(
            renderer, x + inner * std::cos(theta), y - inner * std::sin(theta),
            x + radius * std::cos(theta), y - radius * std::sin(theta));
    }
    const float needle = theta_at(needle_position);
    SDL_SetRenderDrawColor(renderer, accent.r, accent.g, accent.b, 255);
    SDL_RenderLine(renderer, x, y, x + radius * 0.75f * std::cos(needle),
                   y - radius * 0.75f * std::sin(needle));
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
        scope.addDataPoint(point.x, point.y);
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
    SDL_SetRenderDrawColor(renderer, 24, 36, 49, 255);
    SDL_RenderFillRect(renderer, &panel);
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
        trace.reserve(64);
        for (const auto &event : events) {
            if (!matches(event) || event.tick > tick)
                continue;
            if (event.high && !high)
                rise_tick = event.tick;
            else if (!event.high && high && rise_tick >= 0)
                last_high_ticks = event.tick - rise_tick;
            if (event.tick < first_tick) {
                high = event.high;
                continue;
            }
            if (trace.empty())
                trace.push_back({left, y + (high ? 0.0f : 13.0f)});
            const float x = x_for_tick(event.tick);
            trace.push_back({x, y + (high ? 0.0f : 13.0f)});
            high = event.high;
            trace.push_back({x, y + (high ? 0.0f : 13.0f)});
        }
        if (trace.empty())
            trace.push_back({left, y + (high ? 0.0f : 13.0f)});
        trace.push_back({right, y + (high ? 0.0f : 13.0f)});
        const auto &color = colors[static_cast<std::size_t>(channel)];
        SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, 255);
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
    }
}

void draw_lab_trends(SDL_Renderer *renderer, FontRenderer &font,
                     const SDL_FRect &panel, long long tick,
                     const std::deque<TrendPoint> &history) {
    SDL_SetRenderDrawColor(renderer, 24, 36, 49, 255);
    SDL_RenderFillRect(renderer, &panel);
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
            const double maximum = channel == 0 ? 7000.0 : 5.0;
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

} // namespace lab
