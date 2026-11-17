#pragma once

#include "authored_mesh_library.h"
#include "lab/SevelSegments.hpp"
#include "renderer.h"

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
};

void render_sevel_scene_donor(Renderer &renderer,
                              const ma17::EmulatorSnapshot &snapshot,
                              float viewport_width, float viewport_height,
                              SevelVisualGeometry geometry = {},
                              SceneDimensions dimensions = {},
                              SceneCamera camera = {},
                              const AuthoredMeshLibrary *mesh_library = nullptr,
                              std::array<ScenePulse, 4> pulses = {});

void render_axial_crank_donor(Renderer &renderer,
                              const ma17::EmulatorSnapshot &snapshot,
                              float viewport_size,
                              const AuthoredMeshLibrary &mesh_library,
                              int cylinder);

} // namespace lab
