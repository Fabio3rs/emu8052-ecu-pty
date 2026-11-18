#pragma once

#include "lab/DonorScene.hpp"
#include "lab/RecordingRenderer.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace lab {

// Shared by the GUI and mesh-envelope tests; Rect supplies x/y/w/h in pixels.
template <typename Rect, typename Render>
void fit_scene_camera(SceneCamera &camera,
                      const ma17::EmulatorSnapshot &snapshot,
                      float viewport_width, float viewport_height,
                      const Rect &target, Render &&render) {
    float min_x = std::numeric_limits<float>::max();
    float min_y = min_x;
    float max_x = std::numeric_limits<float>::lowest();
    float max_y = max_x;
    constexpr double pi = 3.14159265358979323846;
    for (int phase = 0; phase < 16; ++phase) {
        auto sample = snapshot;
        sample.crank_angle_rad = sample.tdc_phase_rad +
            static_cast<double>(phase) * (4.0 * pi / 16.0);
        RecordingRenderer probe;
        render(probe, sample, camera);
        float x0, y0, x1, y1;
        if (!probe.pixel_bounds(x0, y0, x1, y1))
            continue;
        min_x = std::min(min_x, x0);
        min_y = std::min(min_y, y0);
        max_x = std::max(max_x, x1);
        max_y = std::max(max_y, y1);
    }
    const float span_x = max_x - min_x;
    const float span_y = max_y - min_y;
    if (!(span_x > 0.0f && span_y > 0.0f) ||
        !std::isfinite(span_x) || !std::isfinite(span_y))
        return;
    const float requested = std::min(target.w / span_x, target.h / span_y);
    const float zoom = std::clamp(camera.zoom * requested, 0.5f, 3.0f);
    const float factor = zoom / camera.zoom;
    const float anchor_x = viewport_width * 0.5f + camera.pan_x;
    const float anchor_y = viewport_height * 0.42f + camera.pan_y;
    const float next_x = anchor_x + ((min_x + max_x) * 0.5f - anchor_x) * factor;
    const float next_y = anchor_y + ((min_y + max_y) * 0.5f - anchor_y) * factor;
    camera.zoom = zoom;
    camera.pan_x += target.x + target.w * 0.5f - next_x;
    camera.pan_y += target.y + target.h * 0.5f - next_y;
}

} // namespace lab
