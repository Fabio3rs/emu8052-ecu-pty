#include "lab/LabInstruments.hpp"

#include "constants.h"
#include "gauge.h"
#include "geometry_generator.h"
#include "lab/DigitalPulseMeasurements.hpp"
#include "lab/FontRenderer.hpp"
#include "lab/LabLayout.hpp"
#include "lab/ScopeCursor.hpp"
#include "lab/ScopeDecimation.hpp"
#include "lab/SevelInstrumentProfile.hpp"
#include "lab/SevelTransmission.hpp"
#include "lab/CylinderLabels.hpp"
#include "lab/SpeedReading.hpp"
#include "lab/TraceGeometry.hpp"
#include "labeled_gauge_layout.h"
#include "oscilloscope.h"
#include "oscilloscope_path.h"
#include "right_gauge_layout.h"
#include "ui_math.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iterator>
#include <limits>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lab {

namespace {

class OwnedGeometryGenerator final : public GeometryGenerator {
  public:
    ~OwnedGeometryGenerator() { destroy(); }

    // Grows (never shrinks) so one instance serves every shape of a frame
    // instead of allocating a generator per arc.
    void ensure_capacity(int vertices, int indices) {
        if (vertices <= vertex_capacity_ && indices <= index_capacity_)
            return;
        if (vertex_capacity_ > 0)
            destroy();
        vertex_capacity_ = std::max(vertices, vertex_capacity_ * 2);
        index_capacity_ = std::max(indices, index_capacity_ * 2);
        initialize(vertex_capacity_, index_capacity_);
    }

  private:
    int vertex_capacity_ = 0;
    int index_capacity_ = 0;
};

// Scratch buffers shared by every gauge arc drawn on this thread.
struct ArcScratch {
    OwnedGeometryGenerator generator;
    std::vector<SDL_Vertex> vertices;
    std::vector<int> indices;
};

void draw_gauge_arc(SDL_Renderer *renderer, float cx, float cy, float r_in,
                    float r_out, float th0, float th1, SDL_Color color) {
    if (!std::isfinite(r_in) || !std::isfinite(r_out) || !std::isfinite(th0) ||
        !std::isfinite(th1) || r_in < 0.0f || r_out <= r_in || th0 == th1)
        return;
    GeometryGenerator::Ring2dParameters ring;
    ring.innerRadius = r_in;
    ring.outerRadius = r_out;
    ring.startAngle = std::min(th0, th1);
    ring.endAngle = std::max(th0, th1);
    // Gauge::render uses a five-pixel edge limit. Clamp for tiny rings so
    // the donor's asin(maxEdgeLength / (2 * radius)) remains defined.
    ring.maxEdgeLength = std::min(5.0f, r_out);
    const float steps =
        std::ceil((ring.endAngle - ring.startAngle) /
                  std::asin(ring.maxEdgeLength / (2.0f * r_out)));
    if (!std::isfinite(steps) || steps > 32766.0f)
        return; // Donor indices are 16-bit.
    const int segments = std::max(3, static_cast<int>(steps));
    thread_local ArcScratch scratch;
    auto &generator = scratch.generator;
    generator.ensure_capacity((segments + 1) * 2, segments * 6);
    generator.reset();
    generator.startShape();
    if (!generator.generateRing2d(ring))
        return;
    GeometryGenerator::GeometryIndices shape;
    generator.endShape(&shape);
    auto &verts = scratch.vertices;
    auto &idxs = scratch.indices;
    verts.resize(static_cast<std::size_t>((segments + 1) * 2));
    idxs.resize(static_cast<std::size_t>(segments * 6));
    const SDL_FColor fcol{static_cast<float>(color.r) / 255.0f,
                          static_cast<float>(color.g) / 255.0f,
                          static_cast<float>(color.b) / 255.0f,
                          static_cast<float>(color.a) / 255.0f};
    for (std::size_t i = 0; i < verts.size(); ++i) {
        const auto &point = generator.getVertexData()[i].Pos;
        verts[i] = {{cx + point.x, cy - point.y}, fcol, {0.0f, 0.0f}};
    }
    for (std::size_t i = 0; i < idxs.size(); ++i)
        idxs[i] = generator.getIndexData()[i];
    SDL_RenderGeometry(renderer, nullptr, verts.data(),
                       static_cast<int>(verts.size()), idxs.data(),
                       static_cast<int>(idxs.size()));
}

void draw_filled_disc(SDL_Renderer *renderer, float cx, float cy, float radius,
                      SDL_Color color) {
    constexpr int steps = 24;
    std::array<SDL_Vertex, steps + 2> vertices{};
    std::array<int, steps * 3> indices{};
    const SDL_FColor fill{color.r / 255.0f, color.g / 255.0f, color.b / 255.0f,
                          color.a / 255.0f};
    vertices[0] = {{cx, cy}, fill, {0.0f, 0.0f}};
    for (int step = 0; step <= steps; ++step) {
        const float angle = 2.0f * static_cast<float>(constants::pi) *
                            static_cast<float>(step) / steps;
        vertices[static_cast<std::size_t>(step + 1)] = {
            {cx + radius * std::cos(angle), cy - radius * std::sin(angle)},
            fill,
            {0.0f, 0.0f}};
        if (step < steps) {
            indices[static_cast<std::size_t>(step * 3)] = 0;
            indices[static_cast<std::size_t>(step * 3 + 1)] = step + 1;
            indices[static_cast<std::size_t>(step * 3 + 2)] = step + 2;
        }
    }
    SDL_RenderGeometry(renderer, nullptr, vertices.data(),
                       static_cast<int>(vertices.size()), indices.data(),
                       static_cast<int>(indices.size()));
}

} // namespace

namespace {

void draw_donor_line(SDL_Renderer *renderer, GeometryGenerator &generator,
                     const GeometryGenerator::Line2dParameters &line,
                     SDL_FColor color) {
    if (line.lineWidth <= 0.0f || (line.x0 == line.x1 && line.y0 == line.y1))
        return;
    generator.reset();
    generator.startShape();
    if (!generator.generateLine2d(line))
        return;
    GeometryGenerator::GeometryIndices shape;
    generator.endShape(&shape);
    std::array<SDL_Vertex, 4> vertices{};
    std::array<int, 6> indices{};
    for (std::size_t i = 0; i < vertices.size(); ++i) {
        const auto &point = generator.getVertexData()[i].Pos;
        vertices[i] = {{point.x, point.y}, color, {0.0f, 0.0f}};
    }
    for (std::size_t i = 0; i < indices.size(); ++i)
        indices[i] = generator.getIndexData()[i];
    SDL_RenderGeometry(renderer, nullptr, vertices.data(), 4, indices.data(),
                       6);
}

// Device pixels per logical unit, so strokes never fall below one device pixel.
float trace_device_scale(SDL_Renderer *renderer) {
    int output_w = 0, output_h = 0, logical_w = 0, logical_h = 0;
    SDL_RendererLogicalPresentation mode = SDL_LOGICAL_PRESENTATION_DISABLED;
    if (!SDL_GetCurrentRenderOutputSize(renderer, &output_w, &output_h) ||
        !SDL_GetRenderLogicalPresentation(renderer, &logical_w, &logical_h,
                                          &mode) ||
        logical_w <= 0 || output_w <= 0)
        return 1.0f;
    return static_cast<float>(output_w) / static_cast<float>(logical_w);
}

// The single scope-trace path: a constant-width mesh with mitered joins,
// beveled sharp corners and 16-bit-sized batches (lab::build_trace_mesh).
void draw_trace_points(SDL_Renderer *renderer,
                       std::span<const lab::TracePoint> points, SDL_Color color,
                       float logical_width = 1.0f) {
    const float width =
        std::max(logical_width, 1.0f / trace_device_scale(renderer));
    const SDL_FColor tint{static_cast<float>(color.r) / 255.0f,
                          static_cast<float>(color.g) / 255.0f,
                          static_cast<float>(color.b) / 255.0f,
                          static_cast<float>(color.a) / 255.0f};
    for (const auto &batch : lab::build_trace_mesh(points, {width, 4.0f})) {
        std::vector<SDL_Vertex> vertices;
        vertices.reserve(batch.vertices.size());
        for (const auto &v : batch.vertices)
            vertices.push_back({{v.x, v.y}, tint, {0.0f, 0.0f}});
        std::vector<int> indices(batch.indices.begin(), batch.indices.end());
        SDL_RenderGeometry(renderer, nullptr, vertices.data(),
                           static_cast<int>(vertices.size()), indices.data(),
                           static_cast<int>(indices.size()));
    }
}

// Collects consecutive segments (each starting where the previous ended) into
// one polyline so joins are mitered; draws on flush/destruction with the draw
// color current when the run started.
class TraceBatcher {
  public:
    explicit TraceBatcher(SDL_Renderer *renderer) : renderer_(renderer) {}
    TraceBatcher(const TraceBatcher &) = delete;
    TraceBatcher &operator=(const TraceBatcher &) = delete;
    ~TraceBatcher() { flush(); }

    void segment(float x0, float y0, float x1, float y1) {
        if (!points_.empty() &&
            (points_.back().x != x0 || points_.back().y != y0))
            flush();
        if (points_.empty()) {
            SDL_GetRenderDrawColor(renderer_, &color_.r, &color_.g, &color_.b,
                                   &color_.a);
            points_.push_back({x0, y0});
        }
        points_.push_back({x1, y1});
    }
    void flush() {
        if (!points_.empty())
            draw_trace_points(renderer_, points_, color_);
        points_.clear();
    }

  private:
    SDL_Renderer *renderer_;
    SDL_Color color_{255, 255, 255, 255};
    std::vector<lab::TracePoint> points_;
};

// Optional aesthetic: the donor Oscilloscope's tapered path (width 0.5..1 with
// a widening head). Off by default; enable with SEVEL_SCOPE_TAPER=1. Limited to
// 5000 points by the donor generator's 16-bit indices.
bool scope_taper_enabled() {
    static const bool enabled = [] {
        const char *value = std::getenv("SEVEL_SCOPE_TAPER");
        return value && std::string_view(value) == "1";
    }();
    return enabled;
}

void draw_donor_tapered_trace(SDL_Renderer *renderer,
                              const std::vector<SDL_FPoint> &trace,
                              SDL_Color color) {
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
    path.width = oes::oscilloscope_path_width(0.0f);
    if (!generator.startPath(path))
        return;
    for (int index = 1; index < path.n0; ++index) {
        path.i = index;
        const float s = static_cast<float>(index) / static_cast<float>(path.n0);
        path.width = oes::oscilloscope_path_width(s);
        generator.generatePathSegment(path, false);
    }
    GeometryGenerator::GeometryIndices shape;
    generator.endShape(&shape);

    std::vector<SDL_Vertex> vertices;
    const SDL_FColor tint{static_cast<float>(color.r) / 255.0f,
                          static_cast<float>(color.g) / 255.0f,
                          static_cast<float>(color.b) / 255.0f, 1.0f};
    for (int index = 0; index < generator.getCurrentVertexCount(); ++index) {
        const auto &vertex = generator.getVertexData()[index];
        vertices.push_back({{vertex.Pos.x, vertex.Pos.y}, tint, {0.0f, 0.0f}});
    }
    std::vector<int> indices;
    for (int index = 0; index < generator.getCurrentIndexCount(); ++index)
        indices.push_back(generator.getIndexData()[index]);
    SDL_RenderGeometry(renderer, nullptr, vertices.data(),
                       static_cast<int>(vertices.size()), indices.data(),
                       static_cast<int>(indices.size()));
}

void draw_donor_trace(SDL_Renderer *renderer,
                      const std::vector<SDL_FPoint> &trace, SDL_Color color) {
    if (scope_taper_enabled() && trace.size() <= 5000) {
        draw_donor_tapered_trace(renderer, trace, color);
        return;
    }
    std::vector<lab::TracePoint> points;
    points.reserve(trace.size());
    for (const auto &point : trace)
        points.push_back({point.x, point.y});
    draw_trace_points(renderer, points, color);
}

float scope_scale(int width, int height) {
    return std::clamp(std::min(static_cast<float>(width) / 1280.0f,
                               static_cast<float>(height) / 720.0f),
                      1.0f, 2.0f);
}

float digital_cursor_strip(float panel_height) {
    return panel_height >= 280.0f ? 34.0f : 0.0f;
}

SDL_FRect analog_scope_plot_bounds(const LayoutState &layout_state, int width,
                                   int height, bool maximized) {
    const float panel_height =
        LabLayout::scope_height(layout_state, static_cast<float>(width),
                                static_cast<float>(height), maximized);
    if (panel_height < 145.0f)
        return {24.0f, static_cast<float>(height) - panel_height + 30.0f,
                static_cast<float>(width) - 48.0f, panel_height - 45.0f};
    const float left = 16.0f + 138.0f * scope_scale(width, height);
    const float preview_height = panel_height >= 360.0f   ? 108.0f
                                 : panel_height >= 248.0f ? 56.0f
                                                          : 0.0f;
    const float plot_height = panel_height - 105.0f - preview_height;
    const bool short_lanes =
        plot_height * 0.5f - 20.0f < 28.0f * scope_scale(width, height);
    const float right =
        static_cast<float>(width) -
        (short_lanes ? 16.0f + 140.0f * scope_scale(width, height) : 59.0f);
    return {left, static_cast<float>(height) - panel_height + 30.0f,
            right - left, plot_height};
}

SDL_FRect analog_scope_group_rect(const LayoutState &layout_state, int index,
                                  int width, int height, bool maximized) {
    const float panel_height =
        LabLayout::scope_height(layout_state, static_cast<float>(width),
                                static_cast<float>(height), maximized);
    if (panel_height < 248.0f || index < 0 || index >= 11)
        return {};
    const int rows = panel_height >= 360.0f ? 2 : 1;
    const int columns = (11 + rows - 1) / rows;
    const Bounds preview(21.0f, static_cast<float>(width) - 21.0f, 8.0f,
                         8.0f + 52.0f * static_cast<float>(rows));
    const Grid grid{columns, rows};
    const Bounds cell = grid.get(preview, index % columns, index / columns);
    return {cell.left(), static_cast<float>(height) - cell.top(),
            cell.width() - 3.0f, cell.height() - 4.0f};
}

SDL_FRect analog_scope_maximize_rect(const LayoutState &layout_state, int width,
                                     int height, bool maximized) {
    if (width < 360)
        return {};
    const float panel_height =
        LabLayout::scope_height(layout_state, static_cast<float>(width),
                                static_cast<float>(height), maximized);
    return {static_cast<float>(width) - 94.0f,
            static_cast<float>(height) - panel_height - 10.0f, 72.0f, 17.0f};
}

SDL_FRect analog_scope_fit_rect(const LayoutState &layout_state, int width,
                                int height, bool maximized) {
    const SDL_FRect maximize =
        analog_scope_maximize_rect(layout_state, width, height, maximized);
    return maximize.w > 0.0f
               ? SDL_FRect{maximize.x - 78.0f, maximize.y, 70.0f, maximize.h}
               : SDL_FRect{};
}

} // namespace

bool analog_scope_maximize_at(const LayoutState &layout_state, float x, float y,
                              int width, int height, bool maximized) {
    const SDL_FRect button =
        analog_scope_maximize_rect(layout_state, width, height, maximized);
    return button.w > 0.0f && x >= button.x && x < button.x + button.w &&
           y >= button.y && y < button.y + button.h;
}

bool analog_scope_fit_at(const LayoutState &layout_state, float x, float y,
                         int width, int height, bool maximized) {
    const SDL_FRect button =
        analog_scope_fit_rect(layout_state, width, height, maximized);
    return button.w > 0.0f && x >= button.x && x < button.x + button.w &&
           y >= button.y && y < button.y + button.h;
}

int analog_scope_group_at(const LayoutState &layout_state, float x, float y,
                          int width, int height, bool maximized) {
    for (int index = 0; index < 11; ++index) {
        const SDL_FRect card = analog_scope_group_rect(
            layout_state, index, width, height, maximized);
        if (card.w > 0.0f && x >= card.x && x < card.x + card.w &&
            y >= card.y && y < card.y + card.h)
            return index;
    }
    return -1;
}

std::optional<long long> analog_scope_tick_at(const LayoutState &layout_state,
                                              float x, float y, int width,
                                              int height, long long end_tick,
                                              long long span_ticks,
                                              bool maximized) {
    const SDL_FRect plot =
        analog_scope_plot_bounds(layout_state, width, height, maximized);
    if (plot.w <= 0.0f || x < plot.x || x > plot.x + plot.w || y < plot.y ||
        y > plot.y + plot.h)
        return std::nullopt;
    const long long span = std::clamp(span_ticks, 990000LL, 300LL * 990000);
    const long long first_tick = std::max(0LL, end_tick - span);
    const long long visible_ticks = std::max(1LL, end_tick - first_tick);
    const double fraction =
        static_cast<double>(x - plot.x) / static_cast<double>(plot.w);
    return first_tick + static_cast<long long>(std::llround(
                            fraction * static_cast<double>(visible_ticks)));
}

std::size_t analog_scope_signal_count(int group) {
    return group == 1 || group == 2 ? 3U : 2U;
}

int adc_scope_channel(int group, std::size_t signal) {
    constexpr std::array<std::array<int, 2>, 3> channels{
        {{{0, 6}}, {{1, 5}}, {{2, 3}}}};
    if (group == 9 && signal == 1)
        return 1;
    return group >= 6 && group <= 8 && signal < 2
               ? channels[static_cast<std::size_t>(group - 6)][signal]
               : -1;
}

const profile::Instrument &analog_scope_instrument(int group,
                                                   std::size_t signal) {
    switch (group) {
    case 1:
        return signal == 0   ? profile::tps_track1
               : signal == 1 ? profile::tps_track2
                             : profile::throttle_angle;
    case 2:
        return signal == 0   ? profile::ect_scope
               : signal == 1 ? profile::iat_scope
                             : profile::thermostat;
    case 3:
        return signal == 0 ? profile::manifold_pressure : profile::air_flow;
    case 4:
        return signal == 0 ? profile::rpm : profile::load;
    case 5:
        return signal == 0 ? profile::fuel_film : profile::fuel_vapor;
    case 6:
        return signal == 0 ? profile::adc0_tps2_pin : profile::adc6_tps1_pin;
    case 7:
        return signal == 0 ? profile::adc1_battery_pin
                           : profile::adc5_lambda_pin;
    case 8:
        return signal == 0 ? profile::adc2_iat_pin : profile::adc3_ect_pin;
    case 9:
        return signal == 0 ? profile::battery_supply
                           : profile::adc1_battery_pin;
    case 10:
        return signal == 0 ? profile::idle_stem : profile::idle_contact;
    default:
        return signal == 0 ? profile::lambda : profile::oxygen_voltage;
    }
}

std::optional<double> analog_scope_value(const ma17::EmulatorSnapshot &sample,
                                         int group, std::size_t signal) {
    if (signal >= analog_scope_signal_count(group))
        return std::nullopt;
    double value = 0.0;
    switch (group) {
    case 1:
        if (signal < 2 && !sample.tps_available)
            return std::nullopt;
        if (signal == 2 && !sample.throttle_available)
            return std::nullopt;
        value = signal == 0   ? sample.tps_track1_v
                : signal == 1 ? sample.tps_track2_v
                              : sample.throttle_angle_rad * 57.29577951308232;
        break;
    case 2:
        if (!sample.thermal_available)
            return std::nullopt;
        value = signal == 0   ? sample.coolant_c
                : signal == 1 ? sample.intake_air_c
                              : sample.thermostat_open_fraction * 100.0;
        break;
    case 3:
        if (!sample.intake_available)
            return std::nullopt;
        value = signal == 0 ? sample.manifold_pressure_pa / 1000.0
                            : sample.air_in_kg_s * 1000.0;
        break;
    case 4:
        if (!sample.crank_available)
            return std::nullopt;
        value = signal == 0 ? sample.rpm : sample.applied_load_nm;
        break;
    case 5:
        if (!sample.intake_available)
            return std::nullopt;
        value =
            (signal == 0 ? sample.fuel_film_kg : sample.fuel_vapor_kg) * 1e6;
        break;
    case 10:
        if (signal == 0 && !sample.idle_bridge_candidate)
            return std::nullopt;
        if (signal == 1 && !sample.throttle_available)
            return std::nullopt;
        value = signal == 0                  ? sample.idle_stem_m * 1000.0
                : sample.idle_contact_closed ? 1.0
                                             : 0.0;
        break;
    case 9:
        if (signal == 0) {
            if (!sample.battery_supply_available)
                return std::nullopt;
            value = sample.battery_supply_v;
            break;
        }
        [[fallthrough]];
    case 6:
    case 7:
    case 8: {
        const auto &adc = sample.adc_last_conversion[static_cast<std::size_t>(
            adc_scope_channel(group, signal))];
        if (!adc.sampled || !adc.voltage_available ||
            adc.tick > static_cast<uint64_t>(sample.tick) ||
            static_cast<uint64_t>(sample.tick) - adc.tick > 99000)
            return std::nullopt;
        value = adc.pin_voltage_v;
        break;
    }
    default:
        if (!sample.crank_available ||
            (signal == 0 && !sample.exhaust_sample_available))
            return std::nullopt;
        value = signal == 0 ? sample.lambda : sample.lambda_voltage_v;
        break;
    }
    return std::isfinite(value) ? std::optional<double>{value} : std::nullopt;
}

std::optional<ScopeAxisRanges>
fit_analog_scope_axes(const std::vector<ma17::EmulatorSnapshot> &history,
                      int group, long long first_tick, long long last_tick,
                      DisplayUnits units) {
    ScopeAxisRanges fitted{};
    std::array<bool, 2> found{};
    if (first_tick > last_tick)
        return std::nullopt;
    const bool overlay = group == 1 || group == 2;
    for (const auto &sample : history) {
        if (sample.tick < first_tick || sample.tick > last_tick)
            continue;
        for (std::size_t signal = 0; signal < analog_scope_signal_count(group);
             ++signal) {
            const std::size_t band = overlay && signal == 2 ? 1
                                     : overlay              ? 0
                                                            : signal;
            if (group == 10 && band == 1)
                continue; // Keep the sampled contact on its 0–1 state axis.
            const auto raw = analog_scope_value(sample, group, signal);
            if (!raw)
                continue;
            const double value = display_value(
                *raw, analog_scope_instrument(group, signal), units);
            if (!std::isfinite(value))
                continue;
            auto &range = fitted[band];
            if (!found[band])
                range = {value, value};
            else {
                range.minimum = std::min(range.minimum, value);
                range.maximum = std::max(range.maximum, value);
            }
            found[band] = true;
        }
    }
    if (!found[0] && !found[1])
        return std::nullopt;
    for (std::size_t band = 0; band < fitted.size(); ++band) {
        const auto spec = display_profile(
            analog_scope_instrument(group, overlay && band == 1 ? 2U : band),
            units);
        if (!found[band]) {
            fitted[band] = {spec.minimum, spec.maximum};
            continue;
        }
        auto &range = fitted[band];
        const double padding =
            std::max((range.maximum - range.minimum) * 0.1,
                     std::max((spec.maximum - spec.minimum) * 0.01, 1e-6));
        range.minimum -= padding;
        range.maximum += padding;
    }
    return fitted;
}

int scope_channel_at(const LayoutState &layout_state, float x, float y,
                     int width, int height) {
    const float label_width = 138.0f * scope_scale(width, height);
    if (width < 200 || height < 200 || x < 20.0f || x >= 20.0f + label_width)
        return -1;
    const float panel_height = LabLayout::scope_height(
        layout_state, static_cast<float>(width), static_cast<float>(height));
    const float strip = digital_cursor_strip(panel_height);
    const float first_row =
        static_cast<float>(height) - panel_height + 8.0f + strip;
    const float lane_step = (panel_height - 40.0f - strip) / 4.0f;
    for (int channel = 0; channel < 4; ++channel) {
        const float row = first_row + lane_step * static_cast<float>(channel);
        if (y >= row && y < row + lane_step - 4.0f)
            return channel;
    }
    return -1;
}

std::optional<long long> digital_scope_tick_at(const LayoutState &layout_state,
                                               float x, float y, int width,
                                               int height, long long end_tick,
                                               long long span_ticks) {
    const float scale = scope_scale(width, height);
    const float left = 26.0f + 138.0f * scale;
    const float right = static_cast<float>(width) - 24.0f;
    const float panel_height = LabLayout::scope_height(
        layout_state, static_cast<float>(width), static_cast<float>(height));
    const float top = static_cast<float>(height) - panel_height;
    if (width < 200 || height < 200 || x < left || x > right ||
        y < top - 12.0f || y >= static_cast<float>(height))
        return std::nullopt;
    const long long span = std::clamp(span_ticks, 9900LL, 4950000LL);
    return end_tick - span +
           static_cast<long long>(std::llround(
               static_cast<double>(x - left) /
               static_cast<double>(right - left) * static_cast<double>(span)));
}

std::optional<DigitalScopeCursor>
digital_scope_cursor_at(const LayoutState &layout_state, float x, float y,
                        int width, int height, long long end_tick,
                        long long span_ticks,
                        const std::vector<ma17::EmulatorEvent> &events,
                        const std::vector<ma17::EmulatorSnapshot> &history) {
    const float panel_height = LabLayout::scope_height(
        layout_state, static_cast<float>(width), static_cast<float>(height));
    const float top = static_cast<float>(height) - panel_height;
    const float strip = digital_cursor_strip(panel_height);
    const float lane_step = (panel_height - 40.0f - strip) / 4.0f;
    const auto target = digital_scope_tick_at(layout_state, x, y, width, height,
                                              end_tick, span_ticks);
    if (!target || lane_step <= 0.0f)
        return std::nullopt;
    const long long span = std::clamp(span_ticks, 9900LL, 4950000LL);
    const long long first_tick = end_tick - span;
    const float left = 26.0f + 138.0f * scope_scale(width, height);
    const float right = static_cast<float>(width) - 24.0f;
    const long long tolerance =
        std::max(1LL, static_cast<long long>(
                          std::llround(12.0 * static_cast<double>(span) /
                                       static_cast<double>(right - left))));
    for (unsigned channel = 0; channel < 4; ++channel) {
        const float row =
            top + 14.0f + strip + static_cast<float>(channel) * lane_step;
        if (y < row - 6.0f || y >= row + lane_step - 4.0f)
            continue;
        const auto edge =
            channel == 3
                ? nearest_idle_sample_transition(history, *target, first_tick,
                                                 end_tick, tolerance)
                : nearest_digital_edge(events, channel, *target, first_tick,
                                       end_tick, tolerance);
        if (edge)
            return DigitalScopeCursor{channel, *edge};
    }
    return std::nullopt;
}

void draw_lab_scope(
    const LayoutState &layout_state, SDL_Renderer *renderer, FontRenderer &font,
    int width, int height, long long tick,
    const std::vector<ma17::EmulatorEvent> &events,
    const std::vector<ma17::EmulatorSnapshot> &history,
    const std::array<bool, 4> &channels_visible, long long span_ticks,
    const std::array<std::optional<DigitalScopeCursor>, 2> &cursors,
    bool frozen, int focus_cylinder) {
    TraceBatcher batch(renderer);
    if (width < 200 || height < 200)
        return;
    const float scale = scope_scale(width, height);
    const float left = 26.0f + 138.0f * scale;
    const float right = static_cast<float>(width) - 24.0f;
    const float panel_height = LabLayout::scope_height(
        layout_state, static_cast<float>(width), static_cast<float>(height));
    const float top = static_cast<float>(height) - panel_height;
    const SDL_FRect panel{16.0f, top - 12.0f, static_cast<float>(width) - 32.0f,
                          panel_height};
    const float strip = digital_cursor_strip(panel_height);
    const float lane_step = (panel_height - 40.0f - strip) / 4.0f;
    const float signal_height = lane_step * 0.40f;
    SDL_SetRenderDrawColor(renderer, 20, 20, 24, 255);
    SDL_RenderFillRect(renderer, &panel);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &panel);
    const long long span = std::clamp(span_ticks, 9900LL, 4950000LL);
    char zoom_label[64];
    if (span < 990000LL)
        std::snprintf(zoom_label, sizeof(zoom_label),
                      "ECU %lld MS | %s | A:ANALOG", span / 990LL,
                      frozen ? "FROZEN X:LIVE" : "LIVE X:FREEZE");
    else
        std::snprintf(zoom_label, sizeof(zoom_label),
                      "ECU %.1f S | %s | A:ANALOG",
                      static_cast<double>(span) / 990000.0,
                      frozen ? "FROZEN X:LIVE" : "LIVE X:FREEZE");
    font.draw(renderer, right - font.measure(zoom_label) * scale,
              panel.y + 2.0f, zoom_label, {145, 177, 190, 255}, scale);
    if (const std::string focus_label = cylinder_focus_label(focus_cylinder);
        !focus_label.empty()) {
        font.draw(renderer, panel.x + 5.0f, panel.y + 2.0f, focus_label,
                  {184, 210, 140, 255}, scale);
    }
    const long long first_tick = tick - span;
    const auto x_for_tick = [first_tick, span, left, right](long long at) {
        return left + (right - left) * static_cast<float>(at - first_tick) /
                          static_cast<float>(span);
    };
    const int grid_divisions = right - left < 420.0f ? 2 : 4;
    SDL_SetRenderDrawColor(renderer, 55, 74, 88, 255);
    for (int i = 0; i <= grid_divisions; ++i) {
        const float x = left + (right - left) * static_cast<float>(i) /
                                   static_cast<float>(grid_divisions);
        SDL_RenderLine(renderer, x, top, x, top + panel_height - 40.0f);
        const double remaining = static_cast<double>(span) *
                                 (grid_divisions - i) /
                                 (static_cast<double>(grid_divisions) *
                                  (span < 990000LL ? 990.0 : 990000.0));
        char time_label[24];
        std::snprintf(time_label, sizeof(time_label), "%s%.3g %s",
                      i == grid_divisions ? "" : "-", remaining,
                      span < 990000LL ? "ms" : "s");
        if (right - left >= 160.0f) {
            const float label_width = font.measure(time_label) * scale;
            font.draw(
                renderer,
                std::clamp(x - label_width * 0.5f, left, right - label_width),
                top + panel_height - 34.0f, time_label, {145, 177, 190, 255},
                scale);
        }
    }
    constexpr std::array<const char *, 4> labels{"CC3", "P5.0", "P5.1",
                                                 "IDLE SW"};
    constexpr std::array<SDL_Color, 4> colors{{{249, 190, 96, 255},
                                               {99, 211, 220, 255},
                                               {200, 144, 232, 255},
                                               {184, 210, 140, 255}}};
    for (int channel = 0; channel < 4; ++channel) {
        const auto index = static_cast<std::size_t>(channel);
        const float y =
            top + 14.0f + strip + static_cast<float>(channel) * lane_step;
        const bool visible = channels_visible[index];
        const SDL_FRect selector{20.0f, y - 6.0f, 138.0f * scale,
                                 lane_step - 4.0f};
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
        SDL_RenderLine(renderer, left, y + signal_height, right,
                       y + signal_height);

        if (channel == 3) {
            bool previous_valid = false;
            long long previous_tick = 0;
            SDL_FPoint previous{};
            const auto &color = colors[index];
            SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, 255);
            for (const auto &sample : history) {
                if (sample.tick > tick)
                    break;
                if (!sample.throttle_available) {
                    previous_valid = false;
                    continue;
                }
                if (sample.tick < first_tick - 247500LL)
                    continue;
                const SDL_FPoint point{
                    std::clamp(x_for_tick(sample.tick), left, right),
                    y + (sample.idle_contact_closed ? 0.0f : signal_height)};
                if (previous_valid && sample.tick > previous_tick &&
                    sample.tick - previous_tick <= 247500LL) {
                    batch.segment(previous.x, previous.y, point.x, previous.y);
                    batch.segment(point.x, previous.y, point.x, point.y);
                } else {
                    SDL_RenderPoint(renderer, point.x, point.y);
                }
                previous = point;
                previous_tick = sample.tick;
                previous_valid = true;
            }
            font.draw(renderer, 24.0f, y + 1.0f, "IDLE SW SAMP", color, scale);
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
        bool known = false;
        const auto measurements = measure_digital_pulses(
            events, static_cast<unsigned>(channel), first_tick, tick);
        std::vector<SDL_FPoint> trace;
        trace.reserve(128);
        std::vector<SDL_FRect> high_rects;
        high_rects.reserve(32);
        float high_start_x = -1.0f;

        for (const auto &event : events) {
            if (!matches(event) || event.tick > tick)
                continue;
            if (event.tick < first_tick) {
                high = event.high;
                known = true;
                high_start_x = high ? left : -1.0f;
                continue;
            }
            if (!known) {
                const float x = x_for_tick(event.tick);
                high = event.high;
                known = true;
                high_start_x = high ? x : -1.0f;
                trace.push_back({x, y + (high ? 0.0f : signal_height)});
                continue;
            }
            if (trace.empty())
                trace.push_back({left, y + (high ? 0.0f : signal_height)});
            const float x = x_for_tick(event.tick);
            trace.push_back({x, y + (high ? 0.0f : signal_height)});

            if (event.high && !high) {
                high_start_x = x;
            } else if (!event.high && high) {
                const float start_x =
                    high_start_x >= 0.0f ? high_start_x : left;
                const float pulse_w = std::max(x - start_x, 1.5f);
                high_rects.push_back({start_x, y, pulse_w, signal_height});
                high_start_x = -1.0f;
            }

            high = event.high;
            trace.push_back({x, y + (high ? 0.0f : signal_height)});
        }
        if (trace.empty() && known)
            trace.push_back({left, y + (high ? 0.0f : signal_height)});
        if (known)
            trace.push_back({right, y + (high ? 0.0f : signal_height)});

        if (high && high_start_x >= 0.0f && right > high_start_x) {
            const float pulse_w = std::max(right - high_start_x, 1.5f);
            high_rects.push_back({high_start_x, y, pulse_w, signal_height});
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
        if (!known)
            std::snprintf(label.data(), label.size(), "%s NO EDGE",
                          labels[static_cast<std::size_t>(channel)]);
        else if (measurements.cycle_high_ticks || measurements.high_ticks)
            std::snprintf(
                label.data(), label.size(), "%s H %.2f ms",
                labels[static_cast<std::size_t>(channel)],
                static_cast<double>(measurements.cycle_high_ticks.value_or(
                    *measurements.high_ticks)) /
                    990.0);
        else
            std::snprintf(label.data(), label.size(), "%s H --",
                          labels[static_cast<std::size_t>(channel)]);
        font.draw(renderer, 24.0f, y + 1.0f, label.data(), color, scale);
        if (lane_step >= 44.0f) {
            char low[16] = "--", period[16] = "--", duty[16] = "--";
            if (measurements.low_ticks)
                std::snprintf(low, sizeof(low), "%.2f",
                              static_cast<double>(*measurements.low_ticks) /
                                  990.0);
            if (measurements.period_ticks)
                std::snprintf(period, sizeof(period), "%.2f",
                              static_cast<double>(*measurements.period_ticks) /
                                  990.0);
            if (measurements.duty_percent)
                std::snprintf(duty, sizeof(duty), "%.1f",
                              *measurements.duty_percent);
            char summary[80];
            std::snprintf(summary, sizeof(summary),
                          "L %s MS  P %s MS  DUTY %s%%", low, period, duty);
            const float text_scale = std::min(
                0.72f * scale,
                (right - left - 8.0f) / std::max(1.0f, font.measure(summary)));
            font.draw(renderer, right - font.measure(summary) * text_scale,
                      y + lane_step - 18.0f * scale, summary,
                      {145, 177, 190, 255}, text_scale);
        }
        if (trace.size() > 1) {
            draw_donor_trace(renderer, trace, color);
        }
    }
    constexpr std::array<SDL_Color, 2> cursor_colors{
        {{249, 190, 96, 255}, {99, 211, 220, 255}}};
    std::array<const DigitalScopeCursor *, 2> visible_cursors{};
    for (std::size_t index = 0; index < cursors.size(); ++index) {
        if (!cursors[index] || cursors[index]->edge.tick < first_tick ||
            cursors[index]->edge.tick > tick)
            continue;
        visible_cursors[index] = &*cursors[index];
        const auto color = cursor_colors[index];
        const float x = x_for_tick(cursors[index]->edge.tick);
        SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, 255);
        SDL_RenderLine(renderer, x, top + strip + 3.0f, x,
                       top + panel_height - 40.0f);
        if (strip <= 0.0f) {
            font.draw(renderer, x + 2.0f, top + 2.0f, index == 0 ? "A" : "B",
                      color, 0.65f * scale);
            continue;
        }
        char row[128];
        std::snprintf(
            row, sizeof(row), "%c %s %.6f S %s", index == 0 ? 'A' : 'B',
            cursors[index]->channel == 3 ? "IDLE SAMP"
                                         : labels[cursors[index]->channel],
            static_cast<double>(cursors[index]->edge.tick) / 990000.0,
            cursors[index]->channel == 3
                ? (cursors[index]->edge.high ? "CLOSED" : "OPEN")
                : (cursors[index]->edge.high ? "HIGH" : "LOW"));
        if (index == 1 && visible_cursors[0]) {
            const auto &a = *visible_cursors[0];
            const auto &b = *visible_cursors[1];
            const std::size_t used = std::strlen(row);
            if (a.channel == b.channel)
                std::snprintf(
                    row + used, sizeof(row) - used, "  DT %+.3f MS DV %+d",
                    static_cast<double>(b.edge.tick - a.edge.tick) / 990.0,
                    static_cast<int>(b.edge.high) -
                        static_cast<int>(a.edge.high));
            else
                std::snprintf(
                    row + used, sizeof(row) - used, "  DT %+.3f MS DV --",
                    static_cast<double>(b.edge.tick - a.edge.tick) / 990.0);
        }
        const float text_scale =
            std::min(0.78f * scale,
                     (right - left - 8.0f) / std::max(1.0f, font.measure(row)));
        font.draw(renderer, left + 5.0f,
                  top + 2.0f + static_cast<float>(index) * 15.0f, row, color,
                  text_scale);
    }
    if (panel_height >= 248.0f) {
        const float spark_y = top + panel_height - 55.0f;
        const float burn_y = top + panel_height - 45.0f;
        font.draw(renderer, 24.0f, top + panel_height - 34.0f, "S1/4 S2/3",
                  {145, 177, 190, 255}, 0.85f * scale);
        font.draw(renderer, 24.0f, top + panel_height - 22.0f, "BURN !MISS",
                  {145, 177, 190, 255}, 0.85f * scale);
        for (const auto &event : events) {
            if (event.tick < first_tick || event.tick > tick)
                continue;
            const float x = x_for_tick(event.tick);
            if (event.type == ma17::EmulatorEventType::Spark &&
                event.pair_index < 2) {
                const SDL_Color color = event.pair_index == 0
                                            ? SDL_Color{99, 211, 220, 255}
                                            : SDL_Color{249, 190, 96, 255};
                SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b,
                                       255);
                SDL_RenderLine(renderer, x - 3.0f, spark_y - 3.0f, x,
                               spark_y + 3.0f);
                SDL_RenderLine(renderer, x, spark_y + 3.0f, x + 3.0f,
                               spark_y - 3.0f);
            } else if (event.type == ma17::EmulatorEventType::Combustion &&
                       event.cylinder_index < 4) {
                const SDL_FRect mark{x - 2.0f, burn_y - 2.0f, 4.0f, 4.0f};
                SDL_SetRenderDrawColor(renderer, 184, 210, 140, 255);
                SDL_RenderFillRect(renderer, &mark);
            } else if (event.type == ma17::EmulatorEventType::Misfire &&
                       event.cylinder_index < 4) {
                SDL_SetRenderDrawColor(renderer, 238, 68, 69, 255);
                SDL_RenderLine(renderer, x - 3.0f, burn_y - 3.0f, x + 3.0f,
                               burn_y + 3.0f);
                SDL_RenderLine(renderer, x - 3.0f, burn_y + 3.0f, x + 3.0f,
                               burn_y - 3.0f);
            }
        }
    }
}

void draw_lab_analog_scope(
    const LayoutState &layout_state, SDL_Renderer *renderer, FontRenderer &font,
    int width, int height, const ma17::EmulatorSnapshot &current,
    const std::vector<ma17::EmulatorSnapshot> &history, int group,
    long long span_ticks, bool frozen,
    const std::array<long long, 2> &cursor_ticks, long long view_end_tick,
    long long trigger_tick, const char *trigger_status, std::size_t raw_evicted,
    std::size_t archive_evicted, bool maximized, DisplayUnits units,
    int focus_cylinder, const ScopeAxisRanges *fitted_axes) {
    TraceBatcher batch(renderer);
    if (width < 200 || height < 200)
        return;
    const bool tps_group = group == 1;
    const bool thermal_group = group == 2;
    const bool overlaid_group = tps_group || thermal_group;
    const auto value_of = [group, units](const ma17::EmulatorSnapshot &sample,
                                         std::size_t channel) {
        const auto value = analog_scope_value(sample, group, channel);
        return value ? display_value(*value,
                                     analog_scope_instrument(group, channel),
                                     units)
                     : std::numeric_limits<double>::quiet_NaN();
    };
    const long long span = std::clamp(span_ticks, 990000LL, 300LL * 990000);
    const long long first_tick = std::max(0LL, view_end_tick - span);
    const long long visible_ticks = std::max(1LL, view_end_tick - first_tick);
    const auto first_visible = std::lower_bound(
        history.begin(), history.end(), first_tick,
        [](const auto &sample, long long tick) { return sample.tick < tick; });
    const auto after_visible = std::upper_bound(
        first_visible, history.end(), view_end_tick,
        [](long long tick, const auto &sample) { return tick < sample.tick; });
    const std::size_t visible_samples =
        static_cast<std::size_t>(std::distance(first_visible, after_visible));
    const auto readout_index =
        frozen ? nearest_scope_sample(history, view_end_tick, first_tick,
                                      view_end_tick)
               : std::nullopt;
    const ma17::EmulatorSnapshot *readout =
        frozen ? (readout_index ? &history[*readout_index] : nullptr)
               : &current;
    const long long last_sample_tick =
        visible_samples > 0 ? std::prev(after_visible)->tick : first_tick;
    const double sample_rate_hz =
        visible_samples > 1 && last_sample_tick > first_visible->tick
            ? static_cast<double>(visible_samples - 1) * 990000.0 /
                  static_cast<double>(last_sample_tick - first_visible->tick)
            : 0.0;
    const bool partial =
        visible_samples == 0 ||
        first_visible->tick - first_tick > visible_ticks / 20 ||
        view_end_tick - last_sample_tick > visible_ticks / 20;
    long long min_interval = std::numeric_limits<long long>::max();
    long long max_interval = 0;
    if (visible_samples > 1) {
        for (auto next = std::next(first_visible); next != after_visible;
             ++next) {
            const long long interval = next->tick - std::prev(next)->tick;
            if (interval > 0) {
                min_interval = std::min(min_interval, interval);
                max_interval = std::max(max_interval, interval);
            }
        }
    }
    char rate_label[32];
    if (min_interval < max_interval / 2)
        std::snprintf(rate_label, sizeof(rate_label), "SNAP %.0f-%.0f HZ",
                      990000.0 / static_cast<double>(max_interval),
                      990000.0 / static_cast<double>(min_interval));
    else if (sample_rate_hz > 0.0)
        std::snprintf(rate_label, sizeof(rate_label), "SNAP %.0f HZ",
                      sample_rate_hz);
    else
        std::snprintf(rate_label, sizeof(rate_label), "SNAP N/D");
    const float scale = scope_scale(width, height);
    const float panel_height =
        LabLayout::scope_height(layout_state, static_cast<float>(width),
                                static_cast<float>(height), maximized);
    const SDL_FRect panel{16.0f,
                          static_cast<float>(height) - panel_height - 12.0f,
                          static_cast<float>(width) - 32.0f, panel_height};
    const SDL_FRect plot =
        analog_scope_plot_bounds(layout_state, width, height, maximized);
    const float left = plot.x;
    const float right = plot.x + plot.w;
    SDL_SetRenderDrawColor(renderer, 20, 20, 24, 255);
    SDL_RenderFillRect(renderer, &panel);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &panel);
    char heading[128];
    constexpr std::array<const char *, 11> group_titles{
        "LAMBDA / O2 SENSOR V", "TPS1 / TPS2 MODEL",
        "ECT / IAT PHYSICAL",   "MANIFOLD / AIR FLOW",
        "ENGINE SPEED / LOAD",  "FUEL FILM / VAPOR",
        "ADC0/6 TPS LAST",      "ADC1 BAT / ADC5 LAMBDA",
        "ADC2 IAT / ADC3 ECT",  "BATTERY / ADC1 DIVIDER",
        "IDLE STEM / CONTACT"};
    const char *group_title = group_titles[static_cast<std::size_t>(
        std::clamp(group, 0, static_cast<int>(group_titles.size()) - 1))];
    const std::string focus_text = cylinder_focus_label(focus_cylinder, true);
    const char *focus_label = focus_text.c_str();
    if (panel.w < 620.0f)
        std::snprintf(heading, sizeof(heading), "%s%s | %.1fS %zuPTS %s%s | %s",
                      focus_label, group_title,
                      static_cast<double>(visible_ticks) / 990000.0,
                      visible_samples, rate_label, partial ? " PART" : "",
                      frozen ? "HIST X:LIVE" : "LIVE X:FREEZE");
    else
        std::snprintf(heading, sizeof(heading),
                      "%s%s | %.1f S SIM | %zu PTS %s%s | %s", focus_label,
                      group_title,
                      static_cast<double>(visible_ticks) / 990000.0,
                      visible_samples, rate_label, partial ? " PARTIAL" : "",
                      frozen ? "FROZEN X:LIVE" : "LIVE X:FREEZE");
    const SDL_FRect maximize_button =
        analog_scope_maximize_rect(layout_state, width, height, maximized);
    const SDL_FRect fit_button =
        analog_scope_fit_rect(layout_state, width, height, maximized);
    const float heading_width =
        panel.w - 12.0f -
        (maximize_button.w > 0.0f ? maximize_button.w + fit_button.w + 16.0f
                                  : 0.0f);
    constexpr std::array<const char *, 11> short_titles{
        "LAMBDA",  "TPS",       "THERM",     "INTAKE",  "ENGINE", "FUEL",
        "ADC TPS", "ADC BAT/L", "ADC IAT/E", "BATTERY", "IDLE"};
    if (font.measure(heading) * scale > heading_width) {
        std::snprintf(
            heading, sizeof(heading), "%s%s %.1fS %zuPTS %s %s%s", focus_label,
            short_titles[static_cast<std::size_t>(std::clamp(group, 0, 10))],
            static_cast<double>(visible_ticks) / 990000.0, visible_samples,
            rate_label, frozen ? "HIST" : "LIVE", partial ? " PART" : "");
    }
    if (font.measure(heading) * scale > heading_width)
        std::snprintf(
            heading, sizeof(heading), "%s%s %.1fS %s %s", focus_label,
            short_titles[static_cast<std::size_t>(std::clamp(group, 0, 10))],
            static_cast<double>(visible_ticks) / 990000.0, rate_label,
            frozen ? "HIST" : "LIVE");
    if (font.measure(heading) * scale > heading_width)
        std::snprintf(
            heading, sizeof(heading), "%s%s %s", focus_label,
            short_titles[static_cast<std::size_t>(std::clamp(group, 0, 10))],
            frozen ? "HIST" : "LIVE");
    font.draw(renderer, panel.x + 5.0f, panel.y + 2.0f, heading,
              {145, 177, 190, 255}, scale);
    if (maximize_button.w > 0.0f) {
        SDL_SetRenderDrawColor(renderer, 35, 45, 52, 255);
        SDL_RenderFillRect(renderer, &maximize_button);
        SDL_SetRenderDrawColor(renderer, 99, 211, 220, 255);
        SDL_RenderRect(renderer, &maximize_button);
        font.draw(renderer, maximize_button.x + 4.0f, maximize_button.y + 1.0f,
                  maximized ? "Z:REST" : "Z:MAX", {99, 211, 220, 255},
                  0.72f * scale);
        SDL_SetRenderDrawColor(renderer, 35, 45, 52, 255);
        SDL_RenderFillRect(renderer, &fit_button);
        SDL_SetRenderDrawColor(renderer, 99, 211, 220, 255);
        SDL_RenderRect(renderer, &fit_button);
        font.draw(renderer, fit_button.x + 4.0f, fit_button.y + 1.0f,
                  fitted_axes ? "Y:RESET" : "FIT Y", {99, 211, 220, 255},
                  0.72f * scale);
    }
    if (panel.h < 145.0f) {
        auto spec = display_profile(analog_scope_instrument(group, 0), units);
        if (fitted_axes) {
            spec.minimum = (*fitted_axes)[0].minimum;
            spec.maximum = (*fitted_axes)[0].maximum;
        }
        const double latest = readout
                                  ? value_of(*readout, 0)
                                  : std::numeric_limits<double>::quiet_NaN();
        char label[64];
        if (std::isfinite(latest))
            std::snprintf(label, sizeof(label), "%s %.2f %s", spec.title,
                          latest, spec.unit);
        else
            std::snprintf(label, sizeof(label), "%s --", spec.title);
        font.draw(renderer, plot.x, panel.y + 21.0f, label,
                  {200, 144, 232, 255}, 0.72f * scale);
        SDL_SetRenderDrawColor(renderer, 45, 58, 66, 255);
        SDL_RenderRect(renderer, &plot);
        const auto selected = decimate_scope_samples(
            history, first_tick, view_end_tick,
            std::max(1, static_cast<int>(plot.w)), 247500LL,
            [group](const ma17::EmulatorSnapshot &sample) {
                return analog_scope_value(sample, group, 0);
            });
        bool connected = false;
        SDL_FPoint previous{};
        long long previous_tick = 0;
        SDL_SetRenderDrawColor(renderer, 200, 144, 232, 255);
        for (const std::size_t index : selected) {
            const auto &sample = history[index];
            const double value = value_of(sample, 0);
            if (!std::isfinite(value)) {
                connected = false;
                continue;
            }
            const float fraction = static_cast<float>(std::clamp(
                (value - spec.minimum) / (spec.maximum - spec.minimum), 0.0,
                1.0));
            const SDL_FPoint point{
                plot.x + plot.w * static_cast<float>(sample.tick - first_tick) /
                             static_cast<float>(visible_ticks),
                plot.y + plot.h * (1.0f - fraction)};
            if (connected && sample.tick > previous_tick &&
                sample.tick - previous_tick <= 247500LL) {
                if (adc_scope_channel(group, 0) >= 0) {
                    batch.segment(previous.x, previous.y, point.x, previous.y);
                    batch.segment(point.x, previous.y, point.x, point.y);
                } else {
                    batch.segment(previous.x, previous.y, point.x, point.y);
                }
            } else
                SDL_RenderPoint(renderer, point.x, point.y);
            previous = point;
            previous_tick = sample.tick;
            connected = true;
        }
        return;
    }
    constexpr std::array<const char *, 11> preview_titles{
        "LAMBDA",  "TPS",       "THERM",     "INTAKE",  "ENGINE", "FUEL",
        "ADC TPS", "ADC BAT/L", "ADC IAT/E", "BATTERY", "IDLE"};
    constexpr std::array<const char *, 11> compact_preview_titles{
        "LAM",   "TPS",   "TEMP",  "AIR", "RPM", "FUEL",
        "A TPS", "A B/L", "A T/E", "BAT", "IDLE"};
    for (int preview = 0; preview < 11; ++preview) {
        const SDL_FRect card = analog_scope_group_rect(
            layout_state, preview, width, height, maximized);
        if (card.w <= 0.0f)
            break;
        const bool selected = preview == group;
        SDL_SetRenderDrawColor(renderer, selected ? 34 : 16, selected ? 54 : 20,
                               selected ? 62 : 24, 255);
        SDL_RenderFillRect(renderer, &card);
        SDL_SetRenderDrawColor(renderer, selected ? 99 : 50,
                               selected ? 211 : 60, selected ? 220 : 70, 255);
        SDL_RenderRect(renderer, &card);
        font.draw(renderer, card.x + 4.0f, card.y + 2.0f,
                  (card.w < 65.0f
                       ? compact_preview_titles
                       : preview_titles)[static_cast<std::size_t>(preview)],
                  selected ? SDL_Color{99, 211, 220, 255}
                           : SDL_Color{145, 177, 190, 255},
                  0.72f * scale);
        const auto spec =
            display_profile(analog_scope_instrument(preview, 0), units);
        const auto points = decimate_scope_samples(
            history, first_tick, view_end_tick,
            std::max(1, static_cast<int>(card.w)), 247500LL,
            [preview](const ma17::EmulatorSnapshot &sample) {
                return analog_scope_value(sample, preview, 0);
            });
        bool connected = false;
        SDL_FPoint previous{};
        long long previous_tick = 0;
        for (const std::size_t index : points) {
            const auto &sample = history[index];
            const auto raw = analog_scope_value(sample, preview, 0);
            const auto value =
                raw ? std::optional<double>{display_value(
                          *raw, analog_scope_instrument(preview, 0), units)}
                    : std::nullopt;
            if (!value) {
                connected = false;
                continue;
            }
            const float fraction = static_cast<float>(std::clamp(
                (*value - spec.minimum) / (spec.maximum - spec.minimum), 0.0,
                1.0));
            const SDL_FPoint point{
                card.x + 3.0f +
                    (card.w - 6.0f) *
                        static_cast<float>(sample.tick - first_tick) /
                        static_cast<float>(visible_ticks),
                card.y + card.h - 4.0f - fraction * (card.h - 22.0f)};
            SDL_SetRenderDrawColor(renderer, selected ? 99 : 113,
                                   selected ? 211 : 137, selected ? 220 : 146,
                                   255);
            if (connected && sample.tick > previous_tick &&
                sample.tick - previous_tick <= 247500LL) {
                if (adc_scope_channel(preview, 0) >= 0) {
                    batch.segment(previous.x, previous.y, point.x, previous.y);
                    batch.segment(point.x, previous.y, point.x, point.y);
                } else {
                    batch.segment(previous.x, previous.y, point.x, point.y);
                }
            } else
                SDL_RenderPoint(renderer, point.x, point.y);
            previous = point;
            previous_tick = sample.tick;
            connected = true;
        }
    }
    constexpr std::array<SDL_Color, 3> colors{
        {{200, 144, 232, 255}, {99, 211, 220, 255}, {249, 190, 96, 255}}};
    std::array<profile::Instrument, 2> specs{
        display_profile(analog_scope_instrument(group, 0), units),
        display_profile(
            analog_scope_instrument(group, overlaid_group ? 2U : 1U), units)};
    if (fitted_axes) {
        for (std::size_t band = 0; band < specs.size(); ++band) {
            specs[band].minimum = (*fitted_axes)[band].minimum;
            specs[band].maximum = (*fitted_axes)[band].maximum;
        }
    }
    const float band_height = plot.h * 0.5f;
    const bool short_lanes = band_height - 20.0f < 28.0f * scale;
    for (std::size_t channel = 0; channel < specs.size(); ++channel) {
        const auto &spec = specs[channel];
        const float top =
            plot.y + static_cast<float>(channel) * (band_height + 4.0f);
        const float bottom = top + band_height - 4.0f;
        if (channel == 0 && panel.h >= 248.0f) {
            char retention_label[48];
            if (plot.h < 180.0f) {
                std::snprintf(retention_label, sizeof(retention_label),
                              "RAW -%zu ARCH -%zu", raw_evicted,
                              archive_evicted);
                const float label_scale = std::min(
                    scale, (left - panel.x - 10.0f) /
                               std::max(1.0f, font.measure(retention_label)));
                font.draw(renderer, panel.x + 5.0f, top + 32.0f,
                          retention_label, {113, 137, 146, 255}, label_scale);
            } else {
                std::snprintf(retention_label, sizeof(retention_label),
                              "RAW -%zu", raw_evicted);
                font.draw(renderer, panel.x + 5.0f, top + 52.0f,
                          retention_label, {113, 137, 146, 255}, scale);
                std::snprintf(retention_label, sizeof(retention_label),
                              "ARCH -%zu", archive_evicted);
                font.draw(renderer, panel.x + 5.0f, top + 68.0f,
                          retention_label, {113, 137, 146, 255}, scale);
            }
        }
        const float trace_bottom =
            overlaid_group && channel == 1 ? bottom - 16.0f : bottom;
        SDL_SetRenderDrawColor(renderer, 35, 45, 52, 255);
        for (int division = 0; division <= 4; ++division) {
            const float x =
                left + (right - left) * static_cast<float>(division) / 4.0f;
            SDL_RenderLine(renderer, x, top, x, bottom);
        }
        SDL_RenderLine(renderer, left, top, right, top);
        SDL_RenderLine(renderer, left, bottom, right, bottom);
        char axis[48];
        if (trace_bottom - top < 28.0f * scale) {
            std::snprintf(axis, sizeof(axis), "%.1f..%.1f", spec.minimum,
                          spec.maximum);
            font.draw(renderer, right + 4.0f, top, axis, {145, 177, 190, 255},
                      scale);
        } else {
            std::snprintf(axis, sizeof(axis), "%.1f", spec.maximum);
            font.draw(renderer, right + 4.0f, top, axis, {145, 177, 190, 255},
                      scale);
            std::snprintf(axis, sizeof(axis), "%.1f", spec.minimum);
            font.draw(renderer, right + 4.0f, trace_bottom - 14.0f * scale,
                      axis, {145, 177, 190, 255}, scale);
        }
        const std::size_t series_count = overlaid_group && channel == 0 ? 2 : 1;
        for (std::size_t series = 0; series < series_count; ++series) {
            const std::size_t signal =
                overlaid_group ? (channel == 0 ? series : 2) : channel;
            const auto series_spec =
                display_profile(analog_scope_instrument(group, signal), units);
            const auto trace_color = colors[signal];
            constexpr std::array<std::array<const char *, 3>, 11> short_labels{{
                {{"LAMBDA", "O2 SENSOR V", ""}},
                {{"TPS1", "TPS2", "ANGLE"}},
                {{"ECT", "IAT", "THERM"}},
                {{"MAP ABS", "AIR IN", ""}},
                {{"RPM", "LOAD", ""}},
                {{"FILM", "VAPOR", ""}},
                {{"ADC0 TPS2", "ADC6 TPS1", ""}},
                {{"ADC1 BAT", "ADC5 LAMBDA", ""}},
                {{"ADC2 IAT", "ADC3 ECT", ""}},
                {{"BAT SUP", "ADC1 DIV", ""}},
                {{"STEM", "IDLE SW", ""}},
            }};
            const char *short_label = short_labels[static_cast<std::size_t>(
                std::clamp(group, 0,
                           static_cast<int>(short_labels.size()) - 1))][signal];
            char label[48];
            const double current_value =
                readout ? value_of(*readout, signal)
                        : std::numeric_limits<double>::quiet_NaN();
            const int adc_channel = adc_scope_channel(group, signal);
            if (std::isfinite(current_value) && adc_channel >= 0 && readout) {
                const auto &adc =
                    readout->adc_last_conversion[static_cast<std::size_t>(
                        adc_channel)];
                const double age_ms =
                    static_cast<double>(static_cast<uint64_t>(readout->tick) -
                                        adc.tick) /
                    990.0;
                std::snprintf(label, sizeof(label), "%s %.2f %s AGE %.1fMS",
                              short_label, current_value, series_spec.unit,
                              age_ms);
            } else if (group == 10 && signal == 1 &&
                       std::isfinite(current_value)) {
                std::snprintf(label, sizeof(label), "IDLE SW %s SAMP",
                              current_value > 0.5 ? "CLOSED" : "OPEN");
            } else if (std::isfinite(current_value)) {
                std::snprintf(label, sizeof(label), "%s %.2f %s", short_label,
                              current_value, series_spec.unit);
            } else {
                std::snprintf(label, sizeof(label), "%s --", short_label);
            }
            if (std::isfinite(current_value) && adc_channel < 0 &&
                std::abs(current_value) >= 1000.0 &&
                font.measure(label) * scale > left - panel.x - 10.0f)
                std::snprintf(label, sizeof(label), "%s %.0f %s", short_label,
                              current_value, series_spec.unit);
            const float label_y =
                short_lanes
                    ? plot.y + static_cast<float>(signal) * 16.0f * scale
                    : top + (series_count == 2
                                 ? 12.0f + 19.0f * static_cast<float>(series)
                                 : 14.0f);
            font.draw(renderer, panel.x + 5.0f, label_y, label, trace_color,
                      scale);
            SDL_SetRenderDrawColor(renderer, trace_color.r, trace_color.g,
                                   trace_color.b, 255);
            bool has_previous = false;
            long long previous_tick = 0;
            SDL_FPoint previous{};
            std::size_t gap_count = 0;
            auto selected = decimate_scope_samples(
                history, first_tick, view_end_tick,
                std::max(1, static_cast<int>(std::ceil(right - left))),
                247500LL,
                [group, signal](const ma17::EmulatorSnapshot &sample) {
                    return analog_scope_value(sample, group, signal);
                });
            if (group == 10 && signal == 1) {
                for (std::size_t index = 1; index < history.size(); ++index) {
                    const auto &before = history[index - 1];
                    const auto &after = history[index];
                    if (before.tick < first_tick ||
                        after.tick > view_end_tick ||
                        !before.throttle_available ||
                        !after.throttle_available ||
                        before.idle_contact_closed == after.idle_contact_closed)
                        continue;
                    selected.push_back(index - 1);
                    selected.push_back(index);
                }
                std::sort(selected.begin(), selected.end());
                selected.erase(std::unique(selected.begin(), selected.end()),
                               selected.end());
            }
            for (const std::size_t index : selected) {
                const auto &sample = history[index];
                const double value = value_of(sample, signal);
                if (!std::isfinite(value)) {
                    if (has_previous) {
                        ++gap_count;
                        const float gap_x =
                            left +
                            (right - left) *
                                static_cast<float>(sample.tick - first_tick) /
                                static_cast<float>(visible_ticks);
                        SDL_RenderLine(renderer, gap_x, top, gap_x, top + 5.0f);
                    }
                    has_previous = false;
                    continue;
                }
                const float fraction = static_cast<float>(std::clamp(
                    (value - spec.minimum) / (spec.maximum - spec.minimum), 0.0,
                    1.0));
                const SDL_FPoint point{
                    left + (right - left) *
                               static_cast<float>(sample.tick - first_tick) /
                               static_cast<float>(visible_ticks),
                    trace_bottom - fraction * (trace_bottom - top)};
                const bool show_sample =
                    !has_previous || std::abs(point.x - previous.x) >= 4.0f;
                if (has_previous && sample.tick > previous_tick &&
                    sample.tick - previous_tick <= 247500LL) {
                    if (adc_scope_channel(group, signal) >= 0 ||
                        (group == 10 && signal == 1)) {
                        batch.segment(previous.x, previous.y, point.x,
                                      previous.y);
                        batch.segment(point.x, previous.y, point.x, point.y);
                    } else {
                        batch.segment(previous.x, previous.y, point.x, point.y);
                    }
                } else {
                    if (has_previous) {
                        ++gap_count;
                        const float gap_x = (previous.x + point.x) * 0.5f;
                        SDL_RenderLine(renderer, gap_x, top, gap_x, top + 5.0f);
                    }
                    SDL_RenderPoint(renderer, point.x, point.y);
                }
                if (show_sample) {
                    const SDL_FRect marker{point.x - 1.0f, point.y - 1.0f, 3.0f,
                                           3.0f};
                    SDL_RenderFillRect(renderer, &marker);
                }
                previous = point;
                previous_tick = sample.tick;
                has_previous = true;
            }
            if (gap_count > 0) {
                char gap_label[32];
                std::snprintf(gap_label, sizeof(gap_label), "GAPS %zu",
                              gap_count);
                font.draw(renderer, right - 66.0f * scale,
                          top + 3.0f + 13.0f * static_cast<float>(series),
                          gap_label, trace_color, scale);
            }
        }
        if (overlaid_group && channel == 1) {
            SDL_SetRenderDrawColor(renderer, 48, 58, 54, 255);
            SDL_RenderLine(renderer, left, trace_bottom + 3.0f, right,
                           trace_bottom + 3.0f);
            SDL_SetRenderDrawColor(renderer, 184, 210, 140, 255);
            bool previous_valid = false;
            long long previous_contact_tick = 0;
            SDL_FPoint previous_contact{};
            auto contact_indices = decimate_scope_samples(
                history, first_tick, view_end_tick,
                std::max(1, static_cast<int>(std::ceil(right - left))),
                247500LL,
                [thermal_group](const ma17::EmulatorSnapshot &sample)
                    -> std::optional<double> {
                    if (!(thermal_group ? sample.thermal_available
                                        : sample.throttle_available))
                        return std::nullopt;
                    return (thermal_group ? sample.radiator_fan_on
                                          : sample.idle_contact_closed)
                               ? 1.0
                               : 0.0;
                });
            for (std::size_t index = 1; index < history.size(); ++index) {
                const auto &before = history[index - 1];
                const auto &after = history[index];
                if (before.tick < first_tick || after.tick > view_end_tick ||
                    !(thermal_group ? before.thermal_available
                                    : before.throttle_available) ||
                    !(thermal_group ? after.thermal_available
                                    : after.throttle_available) ||
                    (thermal_group
                         ? before.radiator_fan_on == after.radiator_fan_on
                         : before.idle_contact_closed ==
                               after.idle_contact_closed))
                    continue;
                contact_indices.push_back(index - 1);
                contact_indices.push_back(index);
            }
            std::sort(contact_indices.begin(), contact_indices.end());
            contact_indices.erase(
                std::unique(contact_indices.begin(), contact_indices.end()),
                contact_indices.end());
            for (const std::size_t index : contact_indices) {
                const auto &sample = history[index];
                if (!(thermal_group ? sample.thermal_available
                                    : sample.throttle_available)) {
                    previous_valid = false;
                    continue;
                }
                const SDL_FPoint contact{
                    left + (right - left) *
                               static_cast<float>(sample.tick - first_tick) /
                               static_cast<float>(visible_ticks),
                    (thermal_group ? sample.radiator_fan_on
                                   : sample.idle_contact_closed)
                        ? bottom - 12.0f
                        : bottom - 4.0f};
                if (previous_valid && sample.tick > previous_contact_tick &&
                    sample.tick - previous_contact_tick <= 247500LL) {
                    batch.segment(previous_contact.x, previous_contact.y,
                                  contact.x, previous_contact.y);
                    batch.segment(contact.x, previous_contact.y, contact.x,
                                  contact.y);
                } else {
                    SDL_RenderPoint(renderer, contact.x, contact.y);
                }
                previous_contact = contact;
                previous_contact_tick = sample.tick;
                previous_valid = true;
            }
            font.draw(
                renderer, panel.x + 5.0f,
                short_lanes ? plot.y + 48.0f * scale : top + 33.0f,
                thermal_group
                    ? (!readout || !readout->thermal_available ? "FAN -- SAMP"
                       : readout->radiator_fan_on              ? "FAN ON SAMP"
                                                               : "FAN OFF SAMP")
                    : (!readout || !readout->throttle_available ? "SW -- SAMP"
                       : readout->idle_contact_closed ? "SW CLOSED SAMP"
                                                      : "SW OPEN SAMP"),
                {145, 177, 190, 255}, scale);
        }
    }
    if (trigger_tick >= first_tick && trigger_tick <= view_end_tick) {
        const float x =
            left + (right - left) *
                       static_cast<float>(trigger_tick - first_tick) /
                       static_cast<float>(visible_ticks);
        SDL_SetRenderDrawColor(renderer, 175, 203, 111, 255);
        SDL_RenderLine(renderer, x, plot.y, x, plot.y + plot.h);
        font.draw(renderer, x + 3.0f, plot.y + 2.0f, "TRIG",
                  {175, 203, 111, 255}, scale);
    }
    constexpr std::array<SDL_Color, 2> cursor_colors{
        {{249, 190, 96, 255}, {99, 211, 220, 255}}};
    std::array<const ma17::EmulatorSnapshot *, 2> selected{};
    std::array<std::string, 2> cursor_rows{};
    std::array<std::array<double, 3>, 2> cursor_values{};
    std::array<const char *, 3> cursor_units{};
    const std::size_t signal_count = analog_scope_signal_count(group);
    for (std::size_t signal = 0; signal < signal_count; ++signal)
        cursor_units[signal] =
            unit_transform(analog_scope_instrument(group, signal), units).unit;
    for (std::size_t cursor = 0; cursor < cursor_ticks.size(); ++cursor) {
        if (cursor_ticks[cursor] < 0)
            continue;
        const auto index = nearest_scope_sample(history, cursor_ticks[cursor],
                                                first_tick, view_end_tick);
        selected[cursor] = index ? &history[*index] : nullptr;
        const auto &color = cursor_colors[cursor];
        if (const auto *sample = selected[cursor]) {
            const float x =
                left + (right - left) *
                           static_cast<float>(sample->tick - first_tick) /
                           static_cast<float>(visible_ticks);
            SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, 255);
            SDL_RenderLine(renderer, x, plot.y, x, plot.y + plot.h);
            for (std::size_t signal = 0; signal < signal_count; ++signal)
                cursor_values[cursor][signal] = value_of(*sample, signal);
        }
        cursor_rows[cursor] = format_scope_cursor_row(
            cursor == 0 ? 'A' : 'B',
            selected[cursor] ? std::optional<long long>{selected[cursor]->tick}
                             : std::nullopt,
            std::span<const double>{cursor_values[cursor].data(), signal_count},
            std::span<const char *const>{cursor_units.data(), signal_count});
    }
    const bool cursor_visible =
        !cursor_rows[0].empty() || !cursor_rows[1].empty();
    const float cursor_scale = std::min(scale, 1.0f);
    for (std::size_t cursor = 0; cursor < cursor_rows.size(); ++cursor) {
        const auto &row = cursor_rows[cursor];
        if (row.empty())
            continue;
        const float slot_width = panel.w - 10.0f;
        const float row_scale = std::min(
            cursor_scale, slot_width / std::max(1.0f, font.measure(row)));
        font.draw(renderer, panel.x + 5.0f,
                  plot.y + plot.h + 2.0f + static_cast<float>(cursor) * 16.0f,
                  row, cursor_colors[cursor], row_scale);
    }
    if (selected[0] && selected[1]) {
        const std::string row = format_scope_cursor_delta(
            selected[0]->tick, selected[1]->tick,
            std::span<const double>{cursor_values[0].data(), signal_count},
            std::span<const double>{cursor_values[1].data(), signal_count},
            std::span<const char *const>{cursor_units.data(), signal_count});
        const float row_scale =
            std::min(cursor_scale,
                     (panel.w - 10.0f) / std::max(1.0f, font.measure(row)));
        font.draw(renderer, panel.x + 5.0f, plot.y + plot.h + 34.0f, row,
                  {210, 218, 226, 255}, row_scale);
    }
    char start_label[24];
    std::snprintf(start_label, sizeof(start_label), "-%.1f s",
                  static_cast<double>(visible_ticks) / 990000.0);
    const float footer_y = plot.y + plot.h + (cursor_visible ? 50.0f : 20.0f);
    font.draw(renderer, left, footer_y, start_label, {145, 177, 190, 255},
              scale);
    char available_label[64];
    if (visible_samples > 0)
        std::snprintf(available_label, sizeof(available_label),
                      "DATA %.2f..%.2f s",
                      static_cast<double>(first_visible->tick) / 990000.0,
                      static_cast<double>(last_sample_tick) / 990000.0);
    else
        std::snprintf(available_label, sizeof(available_label), "NO DATA");
    const float gap = 10.0f * scale;
    const float data_x = left + font.measure(start_label) * scale + gap;
    const float zero_x = right - font.measure("0 s") * scale;
    const float data_width = zero_x - gap - data_x;
    if (font.measure(available_label) * scale > data_width &&
        visible_samples > 0)
        std::snprintf(available_label, sizeof(available_label), "%.2f..%.2f s",
                      static_cast<double>(first_visible->tick) / 990000.0,
                      static_cast<double>(last_sample_tick) / 990000.0);
    if (font.measure(available_label) * scale <= data_width)
        font.draw(renderer, data_x, footer_y, available_label,
                  {145, 177, 190, 255}, scale);
    if (trigger_status) {
        std::string status = trigger_status;
        const float status_width = left - gap - (panel.x + 5.0f);
        if (font.measure(status) * scale > status_width) {
            while (!status.empty() &&
                   font.measure(status + "...") * scale > status_width)
                status.pop_back();
            status = status.empty() ? "" : status + "...";
        }
        font.draw(renderer, panel.x + 5.0f, footer_y, status,
                  {145, 177, 190, 255}, scale);
    }
    font.draw(renderer, zero_x, footer_y, "0 s", {145, 177, 190, 255}, scale);
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
        if (!trace.empty()) {
            SDL_Color current{255, 255, 255, 255};
            SDL_GetRenderDrawColor(renderer, &current.r, &current.g, &current.b,
                                   &current.a);
            draw_donor_trace(renderer, trace, current);
        }
    }
}

namespace {

// Minimum logical text height for titles and values (UI legibility floor).
constexpr float kMinTextPx = 12.0f;

void draw_oes_dial(SDL_Renderer *renderer, FontRenderer &font,
                   const SDL_FRect &box, const char *title, double value,
                   double v_min, double v_max, double major_step,
                   double minor_step, const char *value_str, float needle_pos,
                   float ui_scale, std::span<const profile::Band> bands = {},
                   bool available = true, const char *unavailable_text = "--",
                   const Gauge *geometry = nullptr, double label_step = 0.0,
                   double label_divisor = 1.0) {
    SDL_SetRenderDrawColor(renderer, 14, 14, 18, 255);
    SDL_RenderFillRect(renderer, &box);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &box);

    // One scale factor for the whole dial: margin comes from the frame, and
    // ticks, bands, needle and numerals from the resulting radius (radius 52.2
    // is the donor layout of a 136 px frame with a 10 px margin).
    constexpr float kDialReferenceRadius =
        0.9f * (136.0f - 2.0f * 10.0f) / 2.0f;
    const float frame_scale = std::min(box.w, box.h) / 136.0f;
    const auto layout = labeled_gauge_layout(
        Bounds(0.0f, box.w, 0.0f, box.h), 10.0f * frame_scale,
        -std::min(20.0f * frame_scale, box.h * 0.10f));
    // Legibility floor: text never renders below kMinTextPx logical units. A
    // title that does not fit at the floor is ellipsized, never shrunk away.
    const float min_scale = font.scale_for_px(kMinTextPx);
    const float title_avail = layout.title.width() - 12.0f * ui_scale;
    const float title_scale = std::max(
        min_scale, std::min(1.10f * ui_scale,
                            title_avail / std::max(1.0f, font.measure(title))));
    const std::string title_text =
        font.ellipsize(title, font.text_px(title_scale), title_avail);
    const float title_px = font.text_px(title_scale);
    const float title_w = font.measure_px(title_text, title_px);
    font.draw(renderer, box.x + (box.w - title_w) * 0.5f,
              box.y + box.h - layout.title.center_v() -
                  0.5f * font.line_height(title_px),
              title_text, {210, 218, 226, 255}, title_scale);
    const float cx = box.x + layout.center.x;
    const float cy = box.y + box.h - layout.center.y;
    const float radius = layout.radius;
    if (radius <= 6.0f)
        return;
    const float val_scale = std::max(
        min_scale, std::min(std::min(1.75f * ui_scale,
                                     std::max(0.72f * ui_scale,
                                              layout.value_font_size / 14.0f)),
                            (box.w - 12.0f * ui_scale) /
                                std::max(1.0f, font.measure(value_str))));
    const float value_y = box.y + box.h - layout.value.bottom() -
                          font.line_height(font.text_px(val_scale));

    constexpr float th_min = 1.20f * 3.14159265f;
    constexpr float th_max = -0.20f * 3.14159265f;
    const auto theta_at = [&](float fraction) {
        return geometry ? geometry->angleForFraction(fraction)
                        : th_min + std::clamp(fraction, 0.0f, 1.0f) *
                                       (th_max - th_min);
    };

    const float range = static_cast<float>(v_max - v_min);
    const float dial_scale = radius / kDialReferenceRadius;
    OwnedGeometryGenerator line_generator;
    line_generator.initialize(4, 6);

    for (const auto &b : bands) {
        if (range <= 0.0f)
            break;
        const float s0 = std::clamp(
            (static_cast<float>(b.start) - static_cast<float>(v_min)) / range,
            0.0f, 1.0f);
        const float s1 = std::clamp(
            (static_cast<float>(b.end) - static_cast<float>(v_min)) / range,
            0.0f, 1.0f);
        const float angle0 = theta_at(s0), angle1 = theta_at(s1);
        // Literal Gauge::render band placement, with SDL pixel/DPI units.
        const float start = std::min(angle0, angle1) + b.shorten_end;
        const float end = std::max(angle0, angle1) - b.shorten_start;
        if (end <= start)
            continue;
        draw_gauge_arc(
            renderer, cx, cy, radius + (b.radial_offset - b.width) * dial_scale,
            radius + b.radial_offset * dial_scale, start, end, b.color);
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
            const int offset = geometry
                                   ? i * geometry->m_minorStep
                                   : static_cast<int>(std::lround(
                                         static_cast<double>(i) * minor_step));
            const bool is_major =
                geometry
                    ? geometry->isMajorTick(offset)
                    : (major_step > 0.0) &&
                          (std::fmod(static_cast<double>(i) * minor_step + 1e-4,
                                     major_step) < 2e-4 ||
                           std::fmod(static_cast<double>(i) * minor_step - 1e-4,
                                     major_step) < 2e-4);
            if (geometry && !geometry->showsTick(offset))
                continue;
            const float tick_len =
                (geometry ? (is_major ? geometry->m_majorTickLength
                                      : geometry->m_minorTickLength)
                          : (is_major ? 10.0f : 5.0f)) *
                dial_scale;
            const SDL_FColor tcol =
                is_major
                    ? SDL_FColor{200.0f / 255, 208.0f / 255, 216.0f / 255, 1.0f}
                    : SDL_FColor{90.0f / 255, 98.0f / 255, 110.0f / 255, 1.0f};
            GeometryGenerator::Line2dParameters tick{};
            tick.x0 = cx + (radius - tick_len) * c;
            tick.y0 = cy - (radius - tick_len) * s;
            tick.x1 = cx + radius * c;
            tick.y1 = cy - radius * s;
            tick.lineWidth = (geometry ? (is_major ? geometry->m_majorTickWidth
                                                   : geometry->m_minorTickWidth)
                                       : (is_major ? 2.0f : 1.0f)) *
                             dial_scale;
            draw_donor_line(renderer, line_generator, tick, tcol);
        }
    }

    // Scale numerals (SEVEL adaptation: the donor gauge prints none).
    if (label_step > 0.0 && range > 0.0f) {
        const float label_px = std::max(8.0f, radius * 0.17f);
        const float label_scale = font.scale_for_px(label_px);
        const float label_text_px = font.text_px(label_scale);
        const float major_len =
            (geometry ? geometry->m_majorTickLength : 10.0f) * dial_scale;
        // Keep the whole numeral box inside the tick circle: the clearance is
        // the box half-extent along the radial direction.
        const float inner_r = radius - major_len - 2.0f * dial_scale;
        for (double label_v = v_min; label_v <= v_max + 1e-6;
             label_v += label_step) {
            const float th = theta_at(static_cast<float>(
                (label_v - v_min) / static_cast<double>(range)));
            char text[16];
            std::snprintf(text, sizeof(text), "%lld",
                          std::llround(label_v / label_divisor));
            const float w = font.measure_px(text, label_text_px);
            const float h = font.line_height(label_text_px);
            const float c = std::cos(th), s = std::sin(th);
            const float label_r =
                inner_r - 0.5f * (std::fabs(c) * w + std::fabs(s) * h);
            font.draw(renderer, cx + label_r * c - 0.5f * w,
                      cy - label_r * s - 0.5f * h, text, {176, 186, 198, 255},
                      label_scale);
        }
    }

    if (!available || !std::isfinite(value)) {
        font.draw(renderer,
                  box.x + (box.w - font.measure(unavailable_text) * val_scale) *
                              0.5f,
                  value_y, unavailable_text, {150, 165, 180, 255}, val_scale);
        return;
    }

    // needle_pos is Gauge::needlePosition(): it already includes the gauge
    // gamma, so it maps to an angle directly (angleForFraction would apply the
    // gamma a second time). Without it, convert the value's dial fraction.
    float needle_th = 0.0f;
    if (needle_pos >= 0.0f) {
        needle_th = geometry ? geometry->angleForPosition(needle_pos)
                             : th_min + std::clamp(needle_pos, 0.0f, 1.0f) *
                                            (th_max - th_min);
    } else {
        needle_th = theta_at(static_cast<float>(std::clamp(
            (value - v_min) / static_cast<double>(range), 0.0, 1.0)));
    }
    const float nx = std::cos(needle_th);
    const float ny = -std::sin(needle_th);
    const float tip_len = layout.needle_outer_radius;
    const float tail_len = layout.needle_inner_radius;
    // Gauge::render from OES generates the needle as a constant-width line.
    // Reuse its actual geometry generator rather than a separate SDL shape.
    GeometryGenerator::Line2dParameters line{};
    line.x0 = cx - nx * tail_len;
    line.y0 = cy - ny * tail_len;
    line.x1 = cx + nx * tip_len;
    line.y1 = cy + ny * tip_len;
    line.lineWidth = (geometry ? geometry->m_needleWidth : 4.0f) * dial_scale;
    const SDL_FColor needle_col{0.93f, 0.27f, 0.27f, 1.0f};
    draw_donor_line(renderer, line_generator, line, needle_col);

    const float val_w = font.measure(value_str) * val_scale;
    font.draw(renderer, box.x + (box.w - val_w) * 0.5f, value_y, value_str,
              {240, 244, 248, 255}, val_scale);
    // Out-of-range indicator at the scale end that the value passed (the value
    // text keeps the real reading). Arrow points away from the arc.
    const bool below = value < v_min;
    if (below || value > v_max) {
        const float th = theta_at(below ? 0.0f : 1.0f);
        const float c = std::cos(th), s = std::sin(th);
        const float tip = radius + 12.0f * dial_scale;
        const float base = radius + 4.0f * dial_scale;
        const float half = 4.0f * dial_scale;
        const SDL_FColor red{238.0f / 255, 68.0f / 255, 69.0f / 255, 1.0f};
        const SDL_Vertex vertices[3] = {
            {{cx + tip * c, cy - tip * s}, red, {0.0f, 0.0f}},
            {{cx + base * c - half * s, cy - base * s - half * c},
             red,
             {0.0f, 0.0f}},
            {{cx + base * c + half * s, cy - base * s + half * c},
             red,
             {0.0f, 0.0f}}};
        SDL_RenderGeometry(renderer, nullptr, vertices, 3, nullptr, 0);
        const char *limit = below ? "LOW" : "HIGH";
        const float text_scale = font.scale_for_px(kMinTextPx);
        const float text_px = font.text_px(text_scale);
        const float text_w = font.measure_px(limit, text_px);
        const float text_h = font.line_height(text_px);
        float tx = std::clamp(cx + (tip + 4.0f * dial_scale) * c -
                                  (c < 0.0f ? text_w : 0.0f),
                              box.x + 2.0f, box.x + box.w - text_w - 2.0f);
        float ty =
            std::clamp(cy - (tip + 4.0f * dial_scale) * s - 0.5f * text_h,
                       box.y + 2.0f, box.y + box.h - text_h - 2.0f);
        // The label must overlap neither the numeric value nor the arrow: try
        // the natural spot, then above the value, beside the arrow and above
        // the arrow; when none fits, keep only the arrow.
        const float value_x0 = box.x + (box.w - val_w) * 0.5f;
        const float value_y1 =
            value_y + font.line_height(font.text_px(val_scale));
        const float arrow_x0 =
            std::min({vertices[0].position.x, vertices[1].position.x,
                      vertices[2].position.x});
        const float arrow_x1 =
            std::max({vertices[0].position.x, vertices[1].position.x,
                      vertices[2].position.x});
        const float arrow_y0 =
            std::min({vertices[0].position.y, vertices[1].position.y,
                      vertices[2].position.y});
        const float arrow_y1 =
            std::max({vertices[0].position.y, vertices[1].position.y,
                      vertices[2].position.y});
        const auto fits = [&](float x, float y) {
            const bool inside =
                x >= box.x + 2.0f && x + text_w <= box.x + box.w - 2.0f &&
                y >= box.y + 2.0f && y + text_h <= box.y + box.h - 2.0f;
            const bool on_value = x < value_x0 + val_w &&
                                  x + text_w > value_x0 && y < value_y1 &&
                                  y + text_h > value_y;
            const bool on_arrow =
                x < arrow_x1 + 1.0f && x + text_w > arrow_x0 - 1.0f &&
                y < arrow_y1 + 1.0f && y + text_h > arrow_y0 - 1.0f;
            return inside && !on_value && !on_arrow;
        };
        const std::array<std::pair<float, float>, 5> candidates{
            {{tx, ty},
             {tx, value_y - text_h - 1.0f},
             {arrow_x1 + 2.0f, ty},
             {arrow_x0 - text_w - 2.0f, ty},
             {tx, arrow_y0 - text_h - 1.0f}}};
        const auto spot = std::find_if(
            candidates.begin(), candidates.end(), [&](const auto &candidate) {
                return fits(candidate.first, candidate.second);
            });
        if (spot == candidates.end())
            return;
        tx = spot->first;
        ty = spot->second;
        font.draw(renderer, tx, ty, limit, {238, 68, 69, 255}, text_scale);
    }
}

void draw_profile_dial(SDL_Renderer *renderer, FontRenderer &font,
                       const SDL_FRect &box, const profile::Instrument &spec,
                       double value, const char *value_str, float needle_pos,
                       float ui_scale, bool available = true,
                       const Gauge *geometry = nullptr) {
    Gauge adapted;
    if (!geometry && spec.maximum > spec.minimum && spec.minor_step > 0.0 &&
        spec.major_step > 0.0) {
        constexpr int tick_units = 1000;
        adapted.m_minorStep = tick_units;
        adapted.m_majorStep = static_cast<int>(
            std::lround(spec.major_step / spec.minor_step * tick_units));
        adapted.m_thetaMin = 1.20f * 3.14159265f;
        adapted.m_thetaMax = -0.20f * 3.14159265f;
        adapted.m_needleWidth = 4.0f;
        if (&spec == &profile::clutch) {
            adapted.m_thetaMin = 0.80f * 3.14159265f;
            adapted.m_thetaMax = 0.20f * 3.14159265f;
        }
        geometry = &adapted;
    }
    draw_oes_dial(renderer, font, box, spec.title, value, spec.minimum,
                  spec.maximum, spec.major_step, spec.minor_step, value_str,
                  needle_pos, ui_scale, {spec.bands.data(), spec.band_count},
                  available, spec.undefined ? "N/D" : "--", geometry,
                  spec.label_step, spec.label_divisor);
}

// Secondary P1.1 reading for the RPM tooltip. P1.1 is a candidate output, not
// a fixed-ratio tachometer (UI-15: pulses per crank revolution vary 0.17-1.0),
// so it is never the main pointer.
std::string p11_note(const ma17::EmulatorSnapshot &snapshot) {
    char text[96];
    if (snapshot.tachometer_available && std::isfinite(snapshot.tachometer_rpm))
        std::snprintf(text, sizeof(text),
                      "P1.1 candidate %.0f RPM @2 ppr (ratio varies)",
                      snapshot.tachometer_rpm);
    else
        std::snprintf(text, sizeof(text), "P1.1 candidate: no valid period");
    return text;
}

void draw_profile_tooltip(SDL_Renderer *renderer, FontRenderer &font,
                          const SDL_FRect &box, const profile::Instrument &spec,
                          long long tick, bool available, bool stale,
                          float ui_scale, const char *extra = nullptr) {
    float window_x = 0.0f;
    float window_y = 0.0f;
    SDL_GetMouseState(&window_x, &window_y);
    float mouse_x = 0.0f;
    float mouse_y = 0.0f;
    if (!SDL_RenderCoordinatesFromWindow(renderer, window_x, window_y, &mouse_x,
                                         &mouse_y) ||
        mouse_x < box.x || mouse_x >= box.x + box.w || mouse_y < box.y ||
        mouse_y >= box.y + box.h)
        return;
    int output_w = 0;
    int output_h = 0;
    if (!render_layout_size(renderer, &output_w, &output_h))
        return;
    char heading[96];
    char detail[96];
    std::snprintf(heading, sizeof(heading), "%s [%s]", spec.title, spec.unit);
    std::snprintf(detail, sizeof(detail), "ID %s  %s  TICK %lld", spec.id,
                  !available ? (spec.undefined ? "N/D" : "MISSING")
                  : stale    ? "STALE"
                             : "VALID",
                  tick);
    const float width =
        (std::max({font.measure(heading), font.measure(spec.source),
                   font.measure(detail), extra ? font.measure(extra) : 0.0f}) +
         16.0f) *
        ui_scale;
    const float height = (extra ? 64.0f : 49.0f) * ui_scale;
    const SDL_FRect panel{
        std::clamp(mouse_x + 12.0f, 8.0f,
                   std::max(8.0f, static_cast<float>(output_w) - width - 8.0f)),
        std::clamp(
            mouse_y + 12.0f, 8.0f,
            std::max(8.0f, static_cast<float>(output_h) - height - 8.0f)),
        width, height};
    SDL_SetRenderDrawColor(renderer, 20, 25, 31, 250);
    SDL_RenderFillRect(renderer, &panel);
    SDL_SetRenderDrawColor(renderer, 99, 211, 220, 255);
    SDL_RenderRect(renderer, &panel);
    font.draw(renderer, panel.x + 7.0f * ui_scale, panel.y + 4.0f * ui_scale,
              heading, {235, 241, 246, 255}, ui_scale);
    font.draw(renderer, panel.x + 7.0f * ui_scale, panel.y + 19.0f * ui_scale,
              spec.source, {145, 177, 190, 255}, ui_scale);
    font.draw(renderer, panel.x + 7.0f * ui_scale, panel.y + 34.0f * ui_scale,
              detail,
              available && !stale ? SDL_Color{99, 211, 220, 255}
                                  : SDL_Color{249, 190, 96, 255},
              ui_scale);
    if (extra)
        font.draw(renderer, panel.x + 7.0f * ui_scale,
                  panel.y + 49.0f * ui_scale, extra, {176, 186, 198, 255},
                  ui_scale);
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
    font.draw(renderer, box.x + 5.0f * ui_scale, box.y + 5.0f * ui_scale,
              "BURN", {145, 177, 190, 255}, 0.55f * ui_scale);
    const bool active_misfire =
        std::any_of(pulses.begin(), pulses.end(), [](const ScenePulse &pulse) {
            return pulse.misfire && pulse.strength > 0.05f;
        });
    const char *miss_label = active_misfire ? "! MISS" : "MISS";
    font.draw(renderer,
              box.x + box.w -
                  (font.measure(miss_label) * 0.55f + 5.0f) * ui_scale,
              box.y + 5.0f * ui_scale, miss_label,
              active_misfire ? SDL_Color{238, 68, 69, 255}
                             : SDL_Color{100, 110, 125, 255},
              0.55f * ui_scale);

    const float top_y = box.y + 20.0f * ui_scale;
    const float avail_h = box.h - 43.0f * ui_scale;
    const float step_y = avail_h / 4.0f;
    const float cx = box.x + box.w * 0.5f;
    const float max_r = std::min(box.w * 0.35f, step_y * 0.38f);

    for (int cyl = 0; cyl < 4; ++cyl) {
        const float cy = top_y + (static_cast<float>(cyl) + 0.5f) * step_y;
        const auto &pulse = pulses[static_cast<std::size_t>(cyl)];
        const float strength = pulse.strength;
        const bool lit = strength > 0.05f;

        draw_gauge_arc(renderer, cx, cy, max_r * 0.80f, max_r * 0.85f, 0.0f,
                       2.0f * static_cast<float>(constants::pi),
                       {42, 46, 56, 255});
        SDL_Color disc_color{24, 26, 32, 255};
        if (lit) {
            const SDL_Color base = pulse.misfire
                                       ? SDL_Color{238, 68, 69, 255}
                                       : SDL_Color{255, 230, 100, 255};
            disc_color = {static_cast<Uint8>(base.r * strength),
                          static_cast<Uint8>(base.g * strength),
                          static_cast<Uint8>(base.b * strength), 255};
        }
        draw_filled_disc(renderer, cx, cy, max_r * 0.75f, disc_color);

        char num[4];
        std::snprintf(num, sizeof(num), pulse.misfire && lit ? "%d!" : "%d",
                      cyl + 1);
        const float nw = font.measure(num) * 0.60f * ui_scale;
        font.draw(renderer, cx - nw * 0.5f, cy - 4.0f * ui_scale, num,
                  lit ? SDL_Color{20, 20, 20, 255}
                      : SDL_Color{100, 110, 125, 255},
                  0.60f * ui_scale);
    }
    for (std::size_t pair = 0; pair < spark_glows.size(); ++pair) {
        const float x = box.x + box.w * (pair == 0 ? 0.08f : 0.55f);
        const char *pair_label = ignition_pair_label(static_cast<int>(pair));
        const float pin = pulses[pair].pin_strength;
        for (int row = 0; row < 2; ++row) {
            const float y =
                box.y + box.h - (row == 0 ? 26.0f : 12.0f) * ui_scale;
            const bool active = (row == 0 ? pin : spark_glows[pair]) > 0.05f;
            draw_filled_disc(renderer, x, y, 2.5f * ui_scale,
                             active ? (row == 0 ? SDL_Color{145, 177, 190, 255}
                                                : SDL_Color{99, 211, 220, 255})
                                    : SDL_Color{70, 77, 87, 255});
            char label[16];
            std::snprintf(label, sizeof(label), "%s %s",
                          row == 0 ? "PIN" : "SPK", pair_label);
            font.draw(renderer, x + 4.0f * ui_scale, y - 4.0f * ui_scale, label,
                      {145, 177, 190, 255}, 0.65f * ui_scale);
        }
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
    const bool angle_available = snapshot.throttle_available &&
                                 std::isfinite(snapshot.throttle_angle_rad);
    const bool cable_available =
        snapshot.throttle_available && std::isfinite(snapshot.pedal_pull_m);

    const Bounds control =
        right_gauge_throttle_control(Bounds(0.0f, box.w, 0.0f, box.h));
    const SDL_FRect slider_box{box.x + control.left(),
                               box.y + box.h - control.top(), control.width(),
                               control.height()};
    SDL_SetRenderDrawColor(renderer, 24, 26, 32, 255);
    SDL_RenderFillRect(renderer, &slider_box);
    SDL_SetRenderDrawColor(renderer, 58, 64, 76, 255);
    SDL_RenderRect(renderer, &slider_box);

    const float pedal_frac = cable_available
                                 ? static_cast<float>(std::clamp(
                                       snapshot.pedal_pull_m / 0.025, 0.0, 1.0))
                                 : 0.0f;
    const float fill_h = (slider_box.h - 2.0f) * pedal_frac;
    const SDL_FRect slider_fill{slider_box.x + 1.0f,
                                slider_box.y + slider_box.h - 1.0f - fill_h,
                                slider_box.w - 2.0f, fill_h};
    SDL_SetRenderDrawColor(renderer, 238, 68, 69, 255);
    SDL_RenderFillRect(renderer, &slider_fill);
    if (!cable_available)
        font.draw(renderer, slider_box.x + 2.0f * ui_scale,
                  slider_box.y + slider_box.h * 0.5f, "--",
                  {150, 165, 180, 255}, 0.7f * ui_scale);

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

    if (angle_available) {
        const float th_angle = static_cast<float>(
            std::clamp(snapshot.throttle_angle_rad, -1.5707963267948966,
                       1.5707963267948966));
        const float plate_len = bore_w * 0.85f;
        const float c_th = std::cos(th_angle);
        const float s_th = std::sin(th_angle);
        SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
        SDL_RenderLine(renderer, cx - c_th * plate_len * 0.5f,
                       cy + s_th * plate_len * 0.5f,
                       cx + c_th * plate_len * 0.5f,
                       cy - s_th * plate_len * 0.5f);
    } else {
        font.draw(renderer, cx - 10.0f * ui_scale, cy - 5.0f * ui_scale, "--",
                  {150, 165, 180, 255}, 0.7f * ui_scale);
    }

    const float r_piv = 2.5f * ui_scale;
    const SDL_FRect piv_rect{cx - r_piv, cy - r_piv, r_piv * 2.0f,
                             r_piv * 2.0f};
    SDL_SetRenderDrawColor(renderer, 238, 68, 69, 255);
    SDL_RenderFillRect(renderer, &piv_rect);

    char stem_buf[32];
    if (snapshot.idle_bridge_candidate && std::isfinite(snapshot.idle_stem_m))
        std::snprintf(stem_buf, sizeof(stem_buf), "STEM: %.2f mm",
                      snapshot.idle_stem_m * 1000.0);
    else
        std::snprintf(stem_buf, sizeof(stem_buf), "STEM: --");
    font.draw(renderer, box.x + 6.0f * ui_scale,
              box.y + box.h - 22.0f * ui_scale, stem_buf, {160, 185, 200, 255},
              0.60f * ui_scale);

    const bool sw_closed = snapshot.idle_contact_closed;
    char sw_buf[32];
    std::snprintf(sw_buf, sizeof(sw_buf), "IDLE SW: %s",
                  !snapshot.throttle_available ? "--"
                  : sw_closed                  ? "CLOSED"
                                               : "OPEN");
    font.draw(renderer, box.x + 6.0f * ui_scale,
              box.y + box.h - 11.0f * ui_scale, sw_buf,
              snapshot.throttle_available && sw_closed
                  ? SDL_Color{60, 232, 130, 255}
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

    constexpr const char *title = "INJ. TOTAL";
    const float title_scale =
        std::min(0.90f * ui_scale, (box.w - 12.0f * ui_scale) /
                                       std::max(1.0f, font.measure(title)));
    const float title_w = font.measure(title) * title_scale;
    font.draw(renderer, box.x + (box.w - title_w) * 0.5f,
              box.y + 4.0f * ui_scale, title, {210, 218, 226, 255},
              title_scale);

    char injected_buf[32];
    const double injected_mg = snapshot.injected_fuel_total_kg * 1e6;
    if (!snapshot.intake_available || !std::isfinite(injected_mg))
        std::snprintf(injected_buf, sizeof(injected_buf), "--");
    else if (injected_mg >= 1000.0)
        std::snprintf(injected_buf, sizeof(injected_buf), "%.2f g",
                      injected_mg / 1000.0);
    else
        std::snprintf(injected_buf, sizeof(injected_buf), "%.1f mg",
                      injected_mg);
    font.draw(renderer, box.x + 8.0f * ui_scale, box.y + 20.0f * ui_scale,
              injected_buf, {255, 255, 255, 255}, 0.95f * ui_scale);

    char vapor_buf[32];
    if (snapshot.intake_available &&
        std::isfinite(snapshot.fuel_vapor_kg * 1e6))
        std::snprintf(vapor_buf, sizeof(vapor_buf), "VAPOR: %.1f mg",
                      snapshot.fuel_vapor_kg * 1e6);
    else
        std::snprintf(vapor_buf, sizeof(vapor_buf), "VAPOR: --");

    char film_buf[32];
    if (snapshot.intake_available && std::isfinite(snapshot.fuel_film_kg * 1e6))
        std::snprintf(film_buf, sizeof(film_buf), "FILM: %.1f mg",
                      snapshot.fuel_film_kg * 1e6);
    else
        std::snprintf(film_buf, sizeof(film_buf), "FILM: --");

    char inj_buf[32];
    if (snapshot.injector_available)
        std::snprintf(inj_buf, sizeof(inj_buf), "PULSES: %llu",
                      snapshot.injector_pulses);
    else
        std::snprintf(inj_buf, sizeof(inj_buf), "PULSES: --");
    const float widest =
        std::max({font.measure(vapor_buf), font.measure(film_buf),
                  font.measure(inj_buf)});
    const float detail_scale = std::min(
        0.85f * ui_scale, (box.w - 14.0f * ui_scale) / std::max(1.0f, widest));
    font.draw(renderer, box.x + 8.0f * ui_scale, box.y + 39.0f * ui_scale,
              vapor_buf, {150, 165, 180, 255}, detail_scale);
    font.draw(renderer, box.x + 8.0f * ui_scale, box.y + 55.0f * ui_scale,
              film_buf, {184, 210, 140, 255}, detail_scale);
    font.draw(renderer, box.x + 8.0f * ui_scale, box.y + 71.0f * ui_scale,
              inj_buf, {140, 180, 220, 255}, detail_scale);
}

} // namespace

void draw_clutch(SDL_Renderer *renderer, FontRenderer &font,
                 const SDL_FRect &bounds,
                 const ma17::EmulatorSnapshot &snapshot, float ui_scale,
                 bool stale) {
    const bool available = snapshot.drivetrain_available &&
                           std::isfinite(snapshot.clutch_pressure) &&
                           snapshot.clutch_pressure >= 0.0 &&
                           snapshot.clutch_pressure <= 1.0;
    const double percent = available ? snapshot.clutch_pressure * 100.0 : 0.0;
    char value[24];
    std::snprintf(value, sizeof(value), "%.0f %%", percent);
    draw_profile_dial(renderer, font, bounds, profile::clutch, percent, value,
                      -1.0f, ui_scale, available && !stale);
    draw_profile_tooltip(renderer, font, bounds, profile::clutch, snapshot.tick,
                         available, stale, ui_scale);
}

void draw_oes_left_cluster(SDL_Renderer *renderer, FontRenderer &font,
                           const SDL_FRect &bounds,
                           const ma17::EmulatorSnapshot &snapshot,
                           float ui_scale, bool stale, int selected_gear,
                           DisplayUnits units) {
    if (bounds.w < 100.0f || bounds.h < 220.0f)
        return;
    const float dial_h = bounds.h * 0.36f;
    const SDL_FRect coolant{bounds.x, bounds.y, bounds.w, dial_h};
    const SDL_FRect load{bounds.x, bounds.y + dial_h, bounds.w, dial_h};
    const SDL_FRect tbi{bounds.x, bounds.y + 2.0f * dial_h, bounds.w,
                        bounds.h - 2.0f * dial_h};
    const auto coolant_spec = display_profile(profile::coolant, units);
    const double coolant_value =
        display_value(snapshot.coolant_c, profile::coolant, units);
    char value[32];
    std::snprintf(value, sizeof(value), "%.1f %s", coolant_value,
                  coolant_spec.unit);
    draw_profile_dial(renderer, font, coolant, coolant_spec, coolant_value,
                      value, -1.0f, ui_scale, snapshot.thermal_available);
    std::snprintf(value, sizeof(value), "%.0f Nm", snapshot.applied_load_nm);
    draw_profile_dial(renderer, font, load, profile::load,
                      snapshot.applied_load_nm, value, -1.0f, ui_scale,
                      snapshot.crank_available);

    SDL_SetRenderDrawColor(renderer, 14, 14, 18, 255);
    SDL_RenderFillRect(renderer, &tbi);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &tbi);
    font.draw(renderer, tbi.x + 8.0f * ui_scale, tbi.y + 6.0f * ui_scale,
              "TBI / LENTA", {210, 218, 226, 255}, 0.75f * ui_scale);
    const float detail_x = tbi.x + tbi.w * 0.51f;
    const float detail_top = 26.0f * ui_scale;
    const float row_step = std::clamp((tbi.h - 40.0f * ui_scale) / 3.0f,
                                      12.0f * ui_scale, 18.0f * ui_scale);
    if (snapshot.throttle_available &&
        std::isfinite(snapshot.throttle_angle_rad))
        std::snprintf(value, sizeof(value), "ANGLE %.1f \xC2\xB0",
                      snapshot.throttle_angle_rad * 57.29577951308232);
    else
        std::snprintf(value, sizeof(value), "ANGLE --");
    font.draw(renderer, tbi.x + 8.0f * ui_scale, tbi.y + detail_top, value,
              {240, 244, 248, 255}, 0.75f * ui_scale);
    if (snapshot.throttle_available && std::isfinite(snapshot.pedal_pull_m))
        std::snprintf(value, sizeof(value), "CABLE %.1f mm",
                      snapshot.pedal_pull_m * 1000.0);
    else
        std::snprintf(value, sizeof(value), "CABLE --");
    font.draw(renderer, detail_x, tbi.y + detail_top, value,
              {240, 244, 248, 255}, 0.70f * ui_scale);
    if (snapshot.tps_available && std::isfinite(snapshot.tps_track1_v))
        std::snprintf(value, sizeof(value), "TPS1 %.2f V",
                      snapshot.tps_track1_v);
    else
        std::snprintf(value, sizeof(value), "TPS1 --");
    font.draw(renderer, tbi.x + 8.0f * ui_scale, tbi.y + detail_top + row_step,
              value, {176, 218, 226, 255}, 0.70f * ui_scale);
    if (snapshot.tps_available && std::isfinite(snapshot.tps_track2_v))
        std::snprintf(value, sizeof(value), "TPS2 %.2f V",
                      snapshot.tps_track2_v);
    else
        std::snprintf(value, sizeof(value), "TPS2 --");
    font.draw(renderer, detail_x, tbi.y + detail_top + row_step, value,
              {176, 218, 226, 255}, 0.70f * ui_scale);
    if (snapshot.idle_bridge_candidate && std::isfinite(snapshot.idle_stem_m))
        std::snprintf(value, sizeof(value), "IDLE STEM %.2f mm",
                      snapshot.idle_stem_m * 1000.0);
    else
        std::snprintf(value, sizeof(value), "IDLE STEM --");
    font.draw(renderer, tbi.x + 8.0f * ui_scale,
              tbi.y + detail_top + 2.0f * row_step, value, {176, 218, 226, 255},
              0.70f * ui_scale);
    font.draw(renderer, detail_x, tbi.y + detail_top + 2.0f * row_step,
              !snapshot.throttle_available   ? "IDLE --"
              : snapshot.idle_contact_closed ? "IDLE CLOSED"
                                             : "IDLE OPEN",
              {176, 218, 226, 255}, 0.70f * ui_scale);
    if (snapshot.drivetrain_available) {
        const char gear = selected_gear == -1 ? 'R'
                          : selected_gear == 0
                              ? 'N'
                              : static_cast<char>('0' + selected_gear);
        std::snprintf(value, sizeof(value), "GEAR %c  CLUTCH %.0f%%", gear,
                      snapshot.clutch_pressure * 100.0);
    } else if (selected_gear == 0)
        std::snprintf(value, sizeof(value), "GEAR N  REF --");
    else
        std::snprintf(value, sizeof(value), "GEAR %d  REF %.3f", selected_gear,
                      transmission::overall_ratio(selected_gear));
    font.draw(renderer, tbi.x + 8.0f * ui_scale,
              tbi.y + detail_top + 3.0f * row_step, value, {184, 210, 140, 255},
              0.70f * ui_scale);
    draw_profile_tooltip(renderer, font, coolant, coolant_spec, snapshot.tick,
                         snapshot.thermal_available &&
                             std::isfinite(snapshot.coolant_c),
                         stale, ui_scale);
    draw_profile_tooltip(renderer, font, load, profile::load, snapshot.tick,
                         snapshot.crank_available &&
                             std::isfinite(snapshot.applied_load_nm),
                         stale, ui_scale);
    const float half_w = tbi.w * 0.5f;
    const SDL_FRect angle_row{tbi.x, tbi.y + detail_top - 6.0f * ui_scale,
                              half_w, row_step};
    const SDL_FRect cable_row{tbi.x + half_w, angle_row.y, tbi.w - half_w,
                              angle_row.h};
    const SDL_FRect tps1_row{tbi.x, angle_row.y + angle_row.h, half_w,
                             angle_row.h};
    const SDL_FRect tps2_row{tbi.x + half_w, tps1_row.y, tbi.w - half_w,
                             angle_row.h};
    const SDL_FRect stem_row{tbi.x, tps1_row.y + tps1_row.h, half_w,
                             angle_row.h};
    const SDL_FRect contact_row{tbi.x + half_w, stem_row.y, tbi.w - half_w,
                                angle_row.h};
    draw_profile_tooltip(renderer, font, angle_row, profile::throttle_angle,
                         snapshot.tick,
                         snapshot.throttle_available &&
                             std::isfinite(snapshot.throttle_angle_rad),
                         stale, ui_scale);
    draw_profile_tooltip(
        renderer, font, cable_row, profile::cable_pull, snapshot.tick,
        snapshot.throttle_available && std::isfinite(snapshot.pedal_pull_m),
        stale, ui_scale);
    draw_profile_tooltip(
        renderer, font, tps1_row, profile::tps_track1, snapshot.tick,
        snapshot.tps_available && std::isfinite(snapshot.tps_track1_v), stale,
        ui_scale);
    draw_profile_tooltip(
        renderer, font, tps2_row, profile::tps_track2, snapshot.tick,
        snapshot.tps_available && std::isfinite(snapshot.tps_track2_v), stale,
        ui_scale);
    draw_profile_tooltip(
        renderer, font, stem_row, profile::idle_stem, snapshot.tick,
        snapshot.idle_bridge_candidate && std::isfinite(snapshot.idle_stem_m),
        stale, ui_scale);
    draw_profile_tooltip(renderer, font, contact_row, profile::idle_contact,
                         snapshot.tick, snapshot.throttle_available, stale,
                         ui_scale);
}

SDL_FRect compact_instrument_tab_rect(const SDL_FRect &bounds, int tab) {
    if (tab < 0 || tab > 2)
        return {};
    return {bounds.x + bounds.w / 3.0f * static_cast<float>(tab), bounds.y,
            bounds.w / 3.0f, 22.0f};
}

void draw_oes_right_cluster(SDL_Renderer *renderer, FontRenderer &font,
                            const SDL_FRect &bounds,
                            const ma17::EmulatorSnapshot &snapshot,
                            const std::array<ScenePulse, 4> &pulses,
                            const std::array<float, 2> &spark_glows,
                            float ui_scale, const std::array<Gauge, 3> *gauges,
                            bool stale, int compact_page, DisplayUnits units) {
    if (bounds.w < 100.0f || bounds.h < 100.0f)
        return;

    SDL_SetRenderDrawColor(renderer, 10, 10, 12, 255);
    SDL_RenderFillRect(renderer, &bounds);
    SDL_SetRenderDrawColor(renderer, 38, 38, 46, 255);
    SDL_RenderRect(renderer, &bounds);

    const auto coolant_spec = display_profile(profile::coolant, units);
    auto speed_spec = display_profile(profile::speed, units);
    if (snapshot.drivetrain_available)
        speed_spec.source = "physical drivetrain road speed (signed)";
    const auto pressure_spec =
        display_profile(profile::manifold_pressure, units);
    const double coolant_value =
        display_value(snapshot.coolant_c, profile::coolant, units);
    const double speed_value =
        display_value(snapshot.vehicle_speed_kmh, profile::speed, units);
    const double pressure_value =
        display_value(snapshot.manifold_pressure_pa / 1000.0,
                      profile::manifold_pressure, units);

    int output_w = 0;
    int output_h = 0;
    const bool compact = render_layout_size(renderer, &output_w, &output_h) &&
                         static_cast<float>(output_w) < kDesktopMinWidth;
    if (compact && output_w < 900 && output_h < 500) {
        for (int tab = 0; tab < 3; ++tab) {
            const SDL_FRect rect = compact_instrument_tab_rect(bounds, tab);
            SDL_SetRenderDrawColor(renderer, tab == compact_page ? 35 : 20,
                                   tab == compact_page ? 50 : 20,
                                   tab == compact_page ? 60 : 24, 255);
            SDL_RenderFillRect(renderer, &rect);
            SDL_SetRenderDrawColor(renderer, 70, 80, 90, 255);
            SDL_RenderRect(renderer, &rect);
            const char *label = tab == 0   ? "VITAL"
                                : tab == 1 ? "DATA"
                                           : "IGNITION";
            const float text_scale =
                std::min(0.72f * ui_scale,
                         (rect.w - 8.0f) / std::max(1.0f, font.measure(label)));
            font.draw(renderer,
                      rect.x +
                          (rect.w - font.measure(label) * text_scale) * 0.5f,
                      rect.y + 4.0f, label, {210, 218, 226, 255}, text_scale);
        }
        const SDL_FRect content{bounds.x, bounds.y + 22.0f, bounds.w,
                                bounds.h - 22.0f};
        if (compact_page == 2) {
            draw_oes_ignition(renderer, font, content, pulses, spark_glows,
                              ui_scale);
            return;
        }
        if (compact_page == 0) {
            const float row_h = content.h / 3.0f;
            const SDL_FRect rpm_box{content.x, content.y, content.w, row_h};
            const SDL_FRect coolant_box{content.x, content.y + row_h, content.w,
                                        row_h};
            const SDL_FRect lambda_box{content.x, content.y + 2.0f * row_h,
                                       content.w, row_h};
            char value[32];
            std::snprintf(value, sizeof(value), "%.0f RPM", snapshot.rpm);
            draw_profile_dial(renderer, font, rpm_box, profile::rpm,
                              snapshot.rpm, value,
                              gauges ? (*gauges)[0].needlePosition() : -1.0f,
                              ui_scale, snapshot.crank_available);
            std::snprintf(value, sizeof(value), "%.1f %s", coolant_value,
                          coolant_spec.unit);
            draw_profile_dial(renderer, font, coolant_box, coolant_spec,
                              coolant_value, value, -1.0f, ui_scale,
                              snapshot.thermal_available);
            std::snprintf(value, sizeof(value), "%.2f", snapshot.lambda);
            draw_profile_dial(renderer, font, lambda_box, profile::lambda,
                              snapshot.lambda, value, -1.0f, ui_scale,
                              snapshot.crank_available &&
                                  snapshot.exhaust_sample_available);
            const std::array<SDL_FRect, 3> rows{rpm_box, coolant_box,
                                                lambda_box};
            const std::array<const profile::Instrument *, 3> specs{
                &profile::rpm, &coolant_spec, &profile::lambda};
            const std::array<bool, 3> valid{
                snapshot.crank_available && std::isfinite(snapshot.rpm),
                snapshot.thermal_available && std::isfinite(snapshot.coolant_c),
                snapshot.crank_available && snapshot.exhaust_sample_available &&
                    std::isfinite(snapshot.lambda)};
            for (std::size_t i = 0; i < rows.size(); ++i)
                draw_profile_tooltip(renderer, font, rows[i], *specs[i],
                                     snapshot.tick, valid[i], stale, ui_scale);
            return;
        }
        const std::array<const profile::Instrument *, 7> specs{
            &profile::oxygen_voltage, &profile::manifold_pressure,
            &profile::air_flow,       &profile::injected_total,
            &profile::fuel_film,      &profile::fuel_vapor,
            &profile::injector_pulses};
        const double air_g_s = snapshot.air_in_kg_s * 1000.0;
        const std::array<double, 7> values{
            snapshot.lambda_voltage_v,
            pressure_value,
            std::abs(air_g_s) < 0.05 ? 0.0 : air_g_s,
            snapshot.injected_fuel_total_kg * 1e6,
            snapshot.fuel_film_kg * 1e6,
            snapshot.fuel_vapor_kg * 1e6,
            static_cast<double>(snapshot.injector_pulses)};
        const std::array<bool, 7> valid{
            snapshot.crank_available,   snapshot.intake_available,
            snapshot.intake_available,  snapshot.intake_available,
            snapshot.intake_available,  snapshot.intake_available,
            snapshot.injector_available};
        const float row_h = content.h / static_cast<float>(specs.size());
        for (std::size_t i = 0; i < specs.size(); ++i) {
            const SDL_FRect row{content.x,
                                content.y + row_h * static_cast<float>(i),
                                content.w, row_h};
            SDL_SetRenderDrawColor(renderer, 14, 14, 18, 255);
            SDL_RenderFillRect(renderer, &row);
            SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
            SDL_RenderRect(renderer, &row);
            const float title_scale =
                std::min(0.72f * ui_scale,
                         (row.w - 12.0f) /
                             std::max(1.0f, font.measure(specs[i]->title)));
            font.draw(renderer, row.x + 6.0f, row.y + 3.0f, specs[i]->title,
                      {210, 218, 226, 255}, title_scale);
            char value[32] = "--";
            if (valid[i] && std::isfinite(values[i])) {
                if (i == 6)
                    std::snprintf(value, sizeof(value), "%.0f", values[i]);
                else if (i == 3 && values[i] >= 1000.0)
                    std::snprintf(value, sizeof(value), "%.2f g",
                                  values[i] / 1000.0);
                else
                    std::snprintf(value, sizeof(value), "%.1f %s", values[i],
                                  i == 0   ? "V"
                                  : i == 1 ? pressure_spec.unit
                                  : i == 2 ? "g/s"
                                           : "mg");
            }
            font.draw(renderer, row.x + 6.0f, row.y + 20.0f, value,
                      {235, 241, 246, 255}, 0.88f * ui_scale);
        }
        for (std::size_t i = 0; i < specs.size(); ++i) {
            const SDL_FRect row{content.x,
                                content.y + row_h * static_cast<float>(i),
                                content.w, row_h};
            draw_profile_tooltip(
                renderer, font, row, i == 1 ? pressure_spec : *specs[i],
                snapshot.tick, valid[i] && std::isfinite(values[i]), stale,
                ui_scale);
        }
        return;
    }

    const RightGaugeLayout layout =
        right_gauge_layout(Bounds(0.0f, bounds.w, 0.0f, bounds.h));
    const auto cell = [&](const Bounds &band) {
        return SDL_FRect{bounds.x + band.left(),
                         bounds.y + bounds.h - band.top(), band.width(),
                         band.height()};
    };
    const SDL_FRect tach_box = cell(layout.tachometer);
    char rpm_str[32];
    std::snprintf(rpm_str, sizeof(rpm_str), "%.0f RPM", snapshot.rpm);
    const float tach_needle = gauges ? (*gauges)[0].needlePosition() : -1.0f;
    draw_profile_dial(renderer, font, tach_box, profile::rpm, snapshot.rpm,
                      rpm_str, tach_needle, ui_scale, snapshot.crank_available,
                      gauges ? &(*gauges)[0] : nullptr);

    const SDL_FRect speed_box = cell(layout.speedometer);
    char spd_str[32];
    if (compact) {
        std::snprintf(spd_str, sizeof(spd_str), "%.1f %s", coolant_value,
                      coolant_spec.unit);
        draw_profile_dial(renderer, font, speed_box, coolant_spec,
                          coolant_value, spd_str, -1.0f, ui_scale,
                          snapshot.thermal_available);
    } else {
        const SpeedReading speed = speed_reading(speed_value, speed_spec.unit);
        std::snprintf(spd_str, sizeof(spd_str), "%s", speed.text.c_str());
        draw_profile_dial(renderer, font, speed_box, speed_spec,
                          speed.dial_value, spd_str, -1.0f, ui_scale,
                          snapshot.vehicle_speed_available);
    }

    const SDL_FRect ign_box = cell(layout.ignition);
    draw_oes_ignition(renderer, font, ign_box, pulses, spark_glows, ui_scale);

    const SDL_FRect thr_box = cell(layout.throttle);
    draw_oes_throttle(renderer, font, thr_box, snapshot, ui_scale);
    const Bounds throttle_control =
        right_gauge_throttle_control(Bounds(0.0f, thr_box.w, 0.0f, thr_box.h));
    const SDL_FRect cable_box{thr_box.x + throttle_control.left(),
                              thr_box.y + thr_box.h - throttle_control.top(),
                              throttle_control.width(),
                              throttle_control.height()};
    const SDL_FRect angle_box{thr_box.x, thr_box.y, cable_box.x - thr_box.x,
                              std::max(0.0f, thr_box.h - 24.0f * ui_scale)};
    const SDL_FRect stem_box{thr_box.x,
                             thr_box.y + thr_box.h - 24.0f * ui_scale,
                             thr_box.w, 12.0f * ui_scale};
    const SDL_FRect contact_box{thr_box.x, stem_box.y + stem_box.h, thr_box.w,
                                12.0f * ui_scale};
    const SDL_FRect in_afr_box = cell(layout.oxygen_voltage);
    char sensor_str[16];
    std::snprintf(sensor_str, sizeof(sensor_str), "%.2f V",
                  snapshot.lambda_voltage_v);
    draw_profile_dial(renderer, font, in_afr_box, profile::oxygen_voltage,
                      snapshot.lambda_voltage_v, sensor_str, -1.0f, ui_scale,
                      snapshot.crank_available);

    const SDL_FRect ex_o2_box = cell(layout.lambda);
    char o2_str[16];
    std::snprintf(o2_str, sizeof(o2_str), "%.2f", snapshot.lambda);
    draw_profile_dial(renderer, font, ex_o2_box, profile::lambda,
                      snapshot.lambda, o2_str, -1.0f, ui_scale,
                      snapshot.crank_available &&
                          snapshot.exhaust_sample_available);

    const SDL_FRect fuel_box = cell(layout.fuel);
    draw_oes_fuel(renderer, font, fuel_box, snapshot, ui_scale);

    const SDL_FRect map_box = cell(layout.manifold_pressure);
    char map_str[32];
    std::snprintf(map_str, sizeof(map_str), "%.*f %s",
                  units == DisplayUnits::Metric ? 0 : 1, pressure_value,
                  pressure_spec.unit);
    draw_profile_dial(renderer, font, map_box, pressure_spec, pressure_value,
                      map_str, -1.0f, ui_scale, snapshot.intake_available);

    const SDL_FRect cfm_box = cell(layout.air_flow);
    const double air_g_s = snapshot.air_in_kg_s * 1000.0;
    const double displayed_air_g_s = std::abs(air_g_s) < 0.05 ? 0.0 : air_g_s;
    char cfm_str[32];
    std::snprintf(cfm_str, sizeof(cfm_str), "%.1f g/s", displayed_air_g_s);
    draw_profile_dial(renderer, font, cfm_box, profile::air_flow,
                      displayed_air_g_s, cfm_str, -1.0f, ui_scale,
                      snapshot.intake_available);

    const SDL_FRect ve_box = cell(layout.volumetric_efficiency);
    // VE and the energy balance come from the plant window (N/D until the first
    // 20-cycle window closes or while the crank is not turning).
    const bool plant_ok = snapshot.crank_available && snapshot.plant_window.valid &&
                          snapshot.plant_window.mean_rpm > 50.0;
    const double ve_percent = snapshot.plant_window.ve_ambient * 100.0;
    char ve_str[24];
    std::snprintf(ve_str, sizeof(ve_str), plant_ok ? "%.0f %%" : "N/D",
                  ve_percent);
    draw_profile_dial(renderer, font, ve_box, profile::volumetric_efficiency,
                      plant_ok ? ve_percent : 0.0, ve_str, -1.0f, ui_scale,
                      plant_ok);
    char ve_note[160];
    const auto &pw = snapshot.plant_window;
    std::snprintf(ve_note, sizeof(ve_note),
                  plant_ok
                      ? "T_b %.1f N.m  P %.1f kW (%.0f cv)  BMEP %.1f bar  "
                        "air %.0f mg/cyl  window %.2f s"
                      : "no plant window yet",
                  pw.brake_torque_nm, pw.brake_power_kw,
                  pw.brake_power_kw / 0.7355, pw.bmep_bar,
                  pw.air_mg_per_cyl_cycle, pw.window_s);
    const std::string tach_note = p11_note(snapshot);
    draw_profile_tooltip(renderer, font, tach_box, profile::rpm, snapshot.tick,
                         snapshot.crank_available &&
                             std::isfinite(snapshot.rpm),
                         stale, ui_scale, tach_note.c_str());
    draw_profile_tooltip(renderer, font, speed_box,
                         compact ? coolant_spec : speed_spec, snapshot.tick,
                         compact
                             ? snapshot.thermal_available &&
                                   std::isfinite(snapshot.coolant_c)
                             : snapshot.vehicle_speed_available &&
                                   std::isfinite(snapshot.vehicle_speed_kmh),
                         stale, ui_scale);
    draw_profile_tooltip(
        renderer, font, in_afr_box, profile::oxygen_voltage, snapshot.tick,
        snapshot.crank_available && std::isfinite(snapshot.lambda_voltage_v),
        stale, ui_scale);
    draw_profile_tooltip(
        renderer, font, ex_o2_box, profile::lambda, snapshot.tick,
        snapshot.crank_available && snapshot.exhaust_sample_available &&
            std::isfinite(snapshot.lambda),
        stale, ui_scale);
    draw_profile_tooltip(renderer, font, map_box, pressure_spec, snapshot.tick,
                         snapshot.intake_available &&
                             std::isfinite(snapshot.manifold_pressure_pa),
                         stale, ui_scale);
    draw_profile_tooltip(
        renderer, font, cfm_box, profile::air_flow, snapshot.tick,
        snapshot.intake_available && std::isfinite(snapshot.air_in_kg_s), stale,
        ui_scale);
    draw_profile_tooltip(renderer, font, ve_box, profile::volumetric_efficiency,
                         snapshot.tick, plant_ok, stale, ui_scale, ve_note);
    const float fuel_row_h = 16.0f * ui_scale;
    const auto fuel_row = [&](float y) {
        return SDL_FRect{fuel_box.x, fuel_box.y + y * ui_scale, fuel_box.w,
                         fuel_row_h};
    };
    draw_profile_tooltip(renderer, font, fuel_row(19.0f),
                         profile::injected_total, snapshot.tick,
                         snapshot.intake_available &&
                             std::isfinite(snapshot.injected_fuel_total_kg),
                         stale, ui_scale);
    draw_profile_tooltip(
        renderer, font, fuel_row(38.0f), profile::fuel_vapor, snapshot.tick,
        snapshot.intake_available && std::isfinite(snapshot.fuel_vapor_kg),
        stale, ui_scale);
    draw_profile_tooltip(
        renderer, font, fuel_row(54.0f), profile::fuel_film, snapshot.tick,
        snapshot.intake_available && std::isfinite(snapshot.fuel_film_kg),
        stale, ui_scale);
    draw_profile_tooltip(renderer, font, fuel_row(70.0f),
                         profile::injector_pulses, snapshot.tick,
                         snapshot.injector_available, stale, ui_scale);
    draw_profile_tooltip(renderer, font, angle_box, profile::throttle_angle,
                         snapshot.tick,
                         snapshot.throttle_available &&
                             std::isfinite(snapshot.throttle_angle_rad),
                         stale, ui_scale);
    draw_profile_tooltip(
        renderer, font, cable_box, profile::cable_pull, snapshot.tick,
        snapshot.throttle_available && std::isfinite(snapshot.pedal_pull_m),
        stale, ui_scale);
    draw_profile_tooltip(
        renderer, font, stem_box, profile::idle_stem, snapshot.tick,
        snapshot.idle_bridge_candidate && std::isfinite(snapshot.idle_stem_m),
        stale, ui_scale);
    draw_profile_tooltip(renderer, font, contact_box, profile::idle_contact,
                         snapshot.tick, snapshot.throttle_available, stale,
                         ui_scale);
}

} // namespace lab
