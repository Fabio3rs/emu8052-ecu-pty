#pragma once

#include "lab/SevelSegments.hpp"
#include "renderer.h"

#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace lab {

inline void render_sevel_scene(Renderer &renderer,
                               const ma17::EmulatorSnapshot &snapshot,
                               float viewport_width, float viewport_height,
                               SevelVisualGeometry geometry = {},
                               SceneDimensions dimensions = {}) {
    struct DrawCall {
        int base_index;
        ysVector color;
    };
    std::vector<EngineSimVertex> vertices;
    std::vector<std::uint16_t> indices;
    std::vector<DrawCall> calls;
    vertices.reserve(256);
    indices.reserve(384);
    calls.reserve(64);
    const auto add_segment = [&](float x0, float y0, float x1, float y1,
                                 float width, ysVector color) {
        const float dx = x1 - x0;
        const float dy = y1 - y0;
        const float length = std::hypot(dx, dy);
        if (length <= 0.0f)
            return;
        if (vertices.size() > std::numeric_limits<std::uint16_t>::max() - 3U)
            throw std::length_error("SEVEL scene vertex limit");
        const float nx = -dy * width / (2.0f * length);
        const float ny = dx * width / (2.0f * length);
        const auto base = static_cast<std::uint16_t>(vertices.size());
        const auto push = [&](float x, float y) {
            vertices.push_back(
                {{x, y, 0.0f, 1.0f}, {0.0f, 0.0f, 1.0f, 0.0f}, {0.0f, 0.0f}});
        };
        push(x0 + nx, y0 + ny);
        push(x0 - nx, y0 - ny);
        push(x1 + nx, y1 + ny);
        push(x1 - nx, y1 - ny);
        const int base_index = static_cast<int>(indices.size());
        indices.insert(indices.end(),
                       {base, static_cast<std::uint16_t>(base + 1),
                        static_cast<std::uint16_t>(base + 2),
                        static_cast<std::uint16_t>(base + 2),
                        static_cast<std::uint16_t>(base + 1),
                        static_cast<std::uint16_t>(base + 3)});
        calls.push_back({base_index, color});
    };

    for_each_sevel_segment(snapshot, geometry, dimensions, add_segment);

    renderer.beginFrame({0.027f, 0.027f, 0.035f, 1.0f});
    renderer.setSceneViewport(0.0f, 0.0f, viewport_width, viewport_height);
    renderer.uploadGeometry(vertices.data(), static_cast<int>(vertices.size()),
                            indices.data(), static_cast<int>(indices.size()));
    const ysMatrix identity = ysMath::LoadIdentity();
    ysMatrix projection = identity;
    projection.m[0][0] = 4.0f;
    projection.m[1][1] = 4.0f;
    projection.m[1][3] = -0.4f;
    for (const auto &call : calls)
        renderer.submitGeometry(vertices.data(), indices.data(), 0,
                                call.base_index, 2, identity, identity,
                                projection, call.color, 0, 0);
    renderer.endFrame();
}

} // namespace lab
