#include "lab/DonorScene.hpp"

#include "geometry_generator.h"
#include "shaders.h"

#include <array>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace lab {
namespace {

class OwnedGeometryGenerator final : public GeometryGenerator {
  public:
    ~OwnedGeometryGenerator() { destroy(); }
};

struct DrawCall {
    GeometryGenerator::GeometryIndices indices;
    ysVector color;
};

} // namespace

void render_sevel_scene_donor(Renderer &renderer,
                              const ma17::EmulatorSnapshot &snapshot,
                              float viewport_width, float viewport_height,
                              SevelVisualGeometry geometry,
                              SceneDimensions dimensions, SceneCamera camera,
                              const AuthoredMeshLibrary *mesh_library,
                              std::array<ScenePulse, 4> pulses) {
    constexpr std::array<const char *, 4> names{"ConnectingRod", "Piston",
                                                "CylinderHead", "Valve"};
    std::array<const AuthoredMeshLibrary::Mesh *, 4> meshes{};
    int vertex_capacity = 256;
    int index_capacity = 384;
    if (mesh_library) {
        for (std::size_t index = 0; index < meshes.size(); ++index) {
            meshes[index] = mesh_library->find(names[index]);
            if (!meshes[index])
                throw std::invalid_argument("missing donor mesh");
            vertex_capacity += static_cast<int>(meshes[index]->vertices.size());
            index_capacity += static_cast<int>(meshes[index]->indices.size());
        }
    }
    OwnedGeometryGenerator generator;
    generator.initialize(vertex_capacity, index_capacity);
    std::vector<DrawCall> calls;
    calls.reserve(64);
    const auto add_segment = [&](float x0, float y0, float x1, float y1,
                                 float width, ysVector color) {
        if (std::hypot(x1 - x0, y1 - y0) <= 0.0f)
            return;
        generator.startShape();
        if (!generator.generateLine2d({x0, y0, x1, y1, width}))
            throw std::length_error("SEVEL donor scene capacity");
        GeometryGenerator::GeometryIndices indices;
        generator.endShape(&indices);
        calls.push_back({indices, color});
    };
    for_each_sevel_segment(snapshot, geometry, dimensions, add_segment);
    std::vector<DrawCall> pulse_calls;
    pulse_calls.reserve(4);
    const float pitch =
        static_cast<float>(dimensions.visual_estimate_cylinder_pitch_m);
    const float head_y =
        static_cast<float>(geometry.visual_estimate_rod_length_m +
                           SevelVisualGeometry::crank_radius_m +
                           dimensions.visual_estimate_head_height_m);
    for (std::size_t cylinder = 0; cylinder < pulses.size(); ++cylinder) {
        const auto &pulse = pulses[cylinder];
        if (pulse.strength <= 0.0f)
            continue;
        const float x = (static_cast<float>(cylinder) - 1.5f) * pitch;
        const float y = head_y - 0.015f;
        const float radius = 0.008f + 0.004f * pulse.strength;
        generator.startShape();
        if (!generator.generateLine2d(
                {x - radius, y - radius, x + radius, y + radius, 0.003f}) ||
            !generator.generateLine2d(
                {x - radius, y + radius, x + radius, y - radius, 0.003f}))
            throw std::length_error("SEVEL pulse scene capacity");
        GeometryGenerator::GeometryIndices indices;
        generator.endShape(&indices);
        const ysVector color = pulse.misfire
                                   ? ysVector{0.93f, 0.35f, 0.30f, 1.0f}
                                   : ysVector{1.0f, 0.82f, 0.36f, 1.0f};
        pulse_calls.push_back({indices, color});
    }
    std::array<GeometryGenerator::GeometryIndices, 4> mesh_indices{};
    if (mesh_library) {
        for (std::size_t index = 0; index < meshes.size(); ++index) {
            generator.startShape();
            if (!generator.generateRawMesh(
                    meshes[index]->vertices.data(),
                    static_cast<int>(meshes[index]->vertices.size()),
                    meshes[index]->indices.data(),
                    static_cast<int>(meshes[index]->indices.size())))
                throw std::length_error("SEVEL donor mesh capacity");
            generator.endShape(&mesh_indices[index]);
        }
    }

    renderer.beginFrame({0.035f, 0.07f, 0.10f, 1.0f});
    renderer.setSceneViewport(0.0f, 0.0f, viewport_width, viewport_height);
    renderer.uploadGeometry(
        generator.getVertexData(), generator.getCurrentVertexCount(),
        generator.getIndexData(), generator.getCurrentIndexCount());
    const ysMatrix identity = ysMath::LoadIdentity();
    ysMatrix projection = identity;
    projection.m[0][0] = 4.0f * camera.zoom;
    projection.m[1][1] = 4.0f * camera.zoom;
    projection.m[0][3] = 2.0f * camera.pan_x / viewport_width;
    projection.m[1][3] = -0.4f - 2.0f * camera.pan_y / viewport_height;
    Shaders shaders;
    const auto submit_shape =
        [&](const GeometryGenerator::GeometryIndices &shape,
            const ysMatrix &transform, const ysVector &color) {
            shaders.SetObjectTransform(transform);
            shaders.SetBaseColor(color);
            renderer.submitGeometry(
                generator.getVertexData(), generator.getIndexData(),
                shape.BaseVertex, shape.BaseIndex, shape.FaceCount,
                shaders.m_objectVariables.Transform, identity, projection,
                shaders.m_objectVariables.BaseColor, shaders.GetRegularFlags(),
                0);
        };
    if (mesh_library) {
        constexpr float visual_estimate_head_half_width_m = 0.17f;
        constexpr float visual_estimate_head_height_scale_m = 0.016f;
        const float head_y =
            static_cast<float>(geometry.visual_estimate_rod_length_m +
                               SevelVisualGeometry::crank_radius_m +
                               dimensions.visual_estimate_head_height_m);
        const ysMatrix head = ysMath::MatMult(
            ysMath::TranslationTransform({0.0f, head_y, 0.0f, 0.0f}),
            ysMath::ScaleTransform({visual_estimate_head_half_width_m / 1.406f,
                                    visual_estimate_head_height_scale_m, 1.0f,
                                    1.0f}));
        const auto &shape = mesh_indices[2];
        submit_shape(shape, head, {0.24f, 0.37f, 0.45f, 1.0f});
    }
    for (const auto &call : calls)
        submit_shape(call.indices, identity, call.color);
    if (mesh_library) {
        const float pitch =
            static_cast<float>(dimensions.visual_estimate_cylinder_pitch_m);
        const float head_y =
            static_cast<float>(geometry.visual_estimate_rod_length_m +
                               SevelVisualGeometry::crank_radius_m +
                               dimensions.visual_estimate_head_height_m);
        constexpr float visual_estimate_valve_width_scale_m = 0.018f;
        constexpr float visual_estimate_valve_height_scale_m = 0.015f;
        const auto &shape = mesh_indices[3];
        for (std::size_t cylinder = 0; cylinder < 4; ++cylinder) {
            const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
            for (int valve = 0; valve < 2; ++valve) {
                const auto kind =
                    valve == 0 ? ValveKind::Intake : ValveKind::Exhaust;
                const float lift = static_cast<float>(
                    valve_lift_fraction(snapshot.crank_angle_rad, cylinder,
                                        kind) *
                    dimensions.visual_estimate_valve_lift_m);
                const float x = center + (valve == 0 ? -0.021f : 0.021f);
                const ysMatrix transform = ysMath::MatMult(
                    ysMath::TranslationTransform(
                        {x, head_y + 0.002f - lift, 0.0f, 0.0f}),
                    ysMath::ScaleTransform(
                        {visual_estimate_valve_width_scale_m,
                         visual_estimate_valve_height_scale_m, 1.0f, 1.0f}));
                const ysVector color =
                    valve == 0 ? ysVector{0.38f, 0.79f, 0.81f, 1.0f}
                               : ysVector{0.78f, 0.52f, 0.41f, 1.0f};
                submit_shape(shape, transform, color);
            }
        }
    }
    if (mesh_library) {
        const auto poses =
            sevel_cylinder_poses(snapshot.crank_angle_rad, geometry);
        const float pitch =
            static_cast<float>(dimensions.visual_estimate_cylinder_pitch_m);
        const std::array<ysVector, 2> colors{
            {{0.70f, 0.77f, 0.78f, 1.0f}, {0.93f, 0.72f, 0.43f, 1.0f}}};
        for (std::size_t cylinder = 0; cylinder < poses.size(); ++cylinder) {
            const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
            const auto &pose = poses[cylinder];
            const ysMatrix rod = ysMath::MatMult(
                ysMath::TranslationTransform(
                    {center, static_cast<float>(pose.crank_pin_y_m), 0.0f,
                     0.0f}),
                ysMath::ScaleTransform({0.012f, 0.012f, 1.0f, 1.0f}));
            const ysMatrix piston = ysMath::MatMult(
                ysMath::TranslationTransform(
                    {center, static_cast<float>(pose.piston_pin_y_m), 0.0f,
                     0.0f}),
                ysMath::ScaleTransform({0.033f, 0.012f, 1.0f, 1.0f}));
            // The donor Crankshaft mesh is an axial silhouette; this scene
            // shows all four cylinders along the shaft instead.
            const std::array<ysMatrix, 2> transforms{rod, piston};
            for (std::size_t index = 0; index < transforms.size(); ++index) {
                const auto &shape = mesh_indices[index];
                submit_shape(shape, transforms[index], colors[index]);
            }
        }
    }
    for (const auto &call : pulse_calls)
        submit_shape(call.indices, identity, call.color);
    renderer.endFrame();
}

void render_axial_crank_donor(Renderer &renderer,
                              const ma17::EmulatorSnapshot &snapshot,
                              float viewport_size,
                              const AuthoredMeshLibrary &mesh_library,
                              int cylinder) {
    if ((cylinder != 1 && cylinder != 2) || viewport_size <= 0.0f)
        throw std::invalid_argument("invalid axial crank view");
    const auto *mesh = mesh_library.find("Crankshaft");
    if (!mesh)
        throw std::invalid_argument("missing donor crankshaft mesh");
    constexpr double pi = 3.14159265358979323846;
    const double phase = cylinder == 2 ? pi : 0.0;
    const float angle = static_cast<float>(
        std::remainder(snapshot.crank_angle_rad + phase, 2.0 * pi));
    const ysMatrix identity = ysMath::LoadIdentity();
    const ysMatrix transform =
        ysMath::RotationTransform({0.0f, 0.0f, 1.0f, 0.0f}, angle);
    ysMatrix projection = identity;
    projection.m[0][0] = 0.52f;
    projection.m[1][1] = 0.52f;
    renderer.beginFrame({0.035f, 0.07f, 0.10f, 1.0f});
    renderer.setSceneViewport(0.0f, 0.0f, viewport_size, viewport_size);
    renderer.uploadGeometry(
        mesh->vertices.data(), static_cast<int>(mesh->vertices.size()),
        mesh->indices.data(), static_cast<int>(mesh->indices.size()));
    renderer.submitGeometry(mesh->vertices.data(), mesh->indices.data(), 0, 0,
                            static_cast<int>(mesh->indices.size() / 3),
                            transform, identity, projection,
                            cylinder == 1 ? ysVector{0.42f, 0.72f, 0.79f, 1.0f}
                                          : ysVector{0.85f, 0.59f, 0.36f, 1.0f},
                            0, 0);
    renderer.endFrame();
}

} // namespace lab
