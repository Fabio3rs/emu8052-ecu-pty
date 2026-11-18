#pragma once

#include "authored_mesh_library.h"
#include "lab/SevelSegments.hpp"
#include "renderer.h"

#include <algorithm>
#include <array>

namespace lab {

struct SceneCamera {
    float zoom = 1.0f;
    float pan_x = 0.0f;
    float pan_y = 0.0f;
};

struct ScenePulse {
    float strength = 0.0f;
    bool misfire = false;
    float spark_strength = 0.0f;
    float pin_strength = 0.0f;
};

inline constexpr float visual_estimate_radial_section_spacing_m = 0.12f;

inline ysMatrix scene_fit_projection(SceneCamera camera, float viewport_width,
                                     float viewport_height, float world_width,
                                     float world_height,
                                     float world_center_y = 0.105f) {
    const float pixels_per_metre =
        std::min(viewport_width / world_width,
                 viewport_height * 0.72f / world_height) * camera.zoom;
    ysMatrix projection = ysMath::LoadIdentity();
    projection.m[0][0] = 2.0f * pixels_per_metre / viewport_width;
    projection.m[1][1] = 2.0f * pixels_per_metre / viewport_height;
    projection.m[0][3] = 2.0f * camera.pan_x / viewport_width;
    projection.m[1][3] =
        0.16f - projection.m[1][1] * world_center_y -
        2.0f * camera.pan_y / viewport_height;
    return projection;
}

void render_sevel_scene_donor(Renderer &renderer,
                              const ma17::EmulatorSnapshot &snapshot,
                              float viewport_width, float viewport_height,
                              SevelVisualGeometry geometry = {},
                              SceneDimensions dimensions = {},
                              SceneCamera camera = {},
                              const AuthoredMeshLibrary *mesh_library = nullptr,
                              std::array<ScenePulse, 4> pulses = {});

void render_sevel_radial_donor(Renderer &renderer,
                               const ma17::EmulatorSnapshot &snapshot,
                               float viewport_width, float viewport_height,
                               const AuthoredMeshLibrary &mesh_library,
                               SevelVisualGeometry geometry = {},
                               SceneDimensions dimensions = {},
                               SceneCamera camera = {},
                               std::array<ScenePulse, 4> pulses = {},
                               int focus_cylinder = 0);

void render_axial_crank_donor(Renderer &renderer,
                              const ma17::EmulatorSnapshot &snapshot,
                              float viewport_size,
                              const AuthoredMeshLibrary &mesh_library,
                              int cylinder);

} // namespace lab
