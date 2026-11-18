#include "lab/DonorScene.hpp"

#include "geometry_generator.h"
#include "shaders.h"

#include <algorithm>
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

// The authored Piston has ring marks at local Y=0 and a curved skirt at
// Y=1.599286. Flip local Y so the flat, ringed crown faces the head.
constexpr float piston_mesh_scale_m = 0.0864f / 2.0f;
constexpr float piston_crown_above_pin_m = 0.023f;

float piston_mesh_origin_y(float pin_y) {
    return pin_y + piston_crown_above_pin_m;
}

} // namespace

void render_sevel_scene_donor(Renderer &renderer,
                              const ma17::EmulatorSnapshot &snapshot,
                              float viewport_width, float viewport_height,
                              SevelVisualGeometry geometry,
                              SceneDimensions dimensions, SceneCamera camera,
                              const AuthoredMeshLibrary *mesh_library,
                              std::array<ScenePulse, 4> pulses) {
    constexpr std::array<const char *, 2> names{"Piston", "Valve"};
    std::array<const AuthoredMeshLibrary::Mesh *, 2> meshes{};
    int vertex_capacity = 512;
    int index_capacity = 768;
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
    pulse_calls.reserve(8);
    const float pitch =
        static_cast<float>(dimensions.visual_estimate_cylinder_pitch_m);
    const float head_y =
        static_cast<float>(geometry.visual_estimate_rod_length_m +
                           SevelVisualGeometry::crank_radius_m +
                           dimensions.visual_estimate_head_height_m);
    for (std::size_t cylinder = 0; cylinder < pulses.size(); ++cylinder) {
        const auto &pulse = pulses[cylinder];
        const float x = (static_cast<float>(cylinder) - 1.5f) * pitch;
        if (pulse.spark_strength > 0.0f) {
            const float y = head_y + 0.005f;
            generator.startShape();
            if (!generator.generateLine2d(
                    {x - 0.006f, y + 0.006f, x + 0.002f, y, 0.002f}) ||
                !generator.generateLine2d(
                    {x + 0.002f, y, x - 0.001f, y - 0.008f, 0.002f}))
                throw std::length_error("SEVEL spark scene capacity");
            GeometryGenerator::GeometryIndices indices;
            generator.endShape(&indices);
            pulse_calls.push_back({indices, {0.39f, 0.83f, 0.86f, 1.0f}});
        }
        if (pulse.strength <= 0.0f)
            continue;
        if (!mesh_library) {
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
        } else {
            const auto poses = sevel_cylinder_poses(
                snapshot.crank_angle_rad - snapshot.tdc_phase_rad, geometry);
            const float piston_crown_y =
                static_cast<float>(poses[cylinder].piston_pin_y_m) + 0.008f;
            const float chamber_height =
                std::clamp(head_y - piston_crown_y, 0.008f, 0.055f);
            const float center_y = head_y - chamber_height * 0.5f;
            constexpr float bore = 0.0864f;

            GeometryGenerator::Trapezoid2dParameters trap;
            trap.center_x = x;
            trap.center_y = center_y;
            trap.height = chamber_height;
            trap.top = bore * 0.62f;
            trap.base = bore * 0.74f;

            generator.startShape();
            if (!generator.generateTrapezoid2d(trap))
                throw std::length_error("SEVEL combustion chamber fire capacity");
            GeometryGenerator::GeometryIndices indices;
            generator.endShape(&indices);

            ysVector flame_color;
            if (pulse.misfire) {
                flame_color = {0.85f, 0.22f, 0.18f, 0.70f};
            } else if (pulse.strength > 0.7f) {
                const float s = (pulse.strength - 0.7f) / 0.3f;
                flame_color = {1.0f, 0.85f + 0.15f * s, 0.20f + 0.60f * s, 0.95f};
            } else if (pulse.strength > 0.3f) {
                const float s = (pulse.strength - 0.3f) / 0.4f;
                flame_color = {1.0f, 0.45f + 0.40f * s, 0.05f + 0.15f * s, 0.85f};
            } else {
                const float s = pulse.strength / 0.3f;
                flame_color = {0.65f + 0.30f * s, 0.18f + 0.25f * s, 0.05f, 0.50f + 0.30f * s};
            }
            pulse_calls.push_back({indices, flame_color});
        }
    }
    std::array<GeometryGenerator::GeometryIndices, 2> mesh_indices{};
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

    renderer.beginFrame({0.027f, 0.027f, 0.035f, 1.0f});
    renderer.setSceneViewport(0.0f, 0.0f, viewport_width, viewport_height);
    renderer.uploadGeometry(
        generator.getVertexData(), generator.getCurrentVertexCount(),
        generator.getIndexData(), generator.getCurrentIndexCount());
    const ysMatrix identity = ysMath::LoadIdentity();
    const ysMatrix projection = scene_fit_projection(
        camera, viewport_width, viewport_height,
        3.4f * pitch + 0.08f, 0.34f);
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
    for (const auto &call : calls)
        submit_shape(call.indices, identity, call.color);
    if (mesh_library) {
        constexpr float visual_estimate_valve_width_scale_m = 0.018f;
        constexpr float visual_estimate_valve_height_scale_m = 0.015f;
        const auto &valve_shape = mesh_indices[1];
        for (std::size_t cylinder = 0; cylinder < 4; ++cylinder) {
            const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
            for (int valve = 0; valve < 2; ++valve) {
                const auto kind =
                    valve == 0 ? ValveKind::Intake : ValveKind::Exhaust;
                const float lift = static_cast<float>(
                    valve_lift_fraction(snapshot.crank_angle_rad, cylinder,
                                        kind, snapshot.tdc_phase_rad) *
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
                submit_shape(valve_shape, transform, color);
            }
        }
    }
    if (mesh_library) {
        const auto poses = sevel_cylinder_poses(
            snapshot.crank_angle_rad - snapshot.tdc_phase_rad, geometry);
        for (std::size_t cylinder = 0; cylinder < poses.size(); ++cylinder) {
            const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
            const auto &pose = poses[cylinder];
            const ysMatrix piston = ysMath::MatMult(
                ysMath::TranslationTransform(
                    {center, piston_mesh_origin_y(
                                 static_cast<float>(pose.piston_pin_y_m)),
                     0.0f, 0.0f}),
                ysMath::ScaleTransform({piston_mesh_scale_m,
                                        -piston_mesh_scale_m, 1.0f, 1.0f}));
            // The donor rod-end and crank meshes are radial silhouettes;
            // only the piston section belongs in this shaft-longitudinal view.
            submit_shape(mesh_indices[0], piston, {0.94f, 0.94f, 0.94f, 1.0f});
        }
    }
    for (const auto &call : pulse_calls)
        submit_shape(call.indices, identity, call.color);
    renderer.endFrame();
}

void render_sevel_radial_donor(Renderer &renderer,
                               const ma17::EmulatorSnapshot &snapshot,
                               float viewport_width, float viewport_height,
                               const AuthoredMeshLibrary &mesh_library,
                               SevelVisualGeometry geometry,
                               SceneDimensions dimensions, SceneCamera camera,
                               std::array<ScenePulse, 4> pulses,
                               int focus_cylinder) {
    if (focus_cylinder < 0 || focus_cylinder > 4)
        throw std::invalid_argument("invalid focused cylinder");
    constexpr std::array<const char *, 5> names{
        "Crankshaft", "ConnectingRod", "Piston", "CylinderHead", "Valve"};
    std::array<const AuthoredMeshLibrary::Mesh *, 5> meshes{};
    int vertex_capacity = 128;
    int index_capacity = 192;
    for (std::size_t index = 0; index < meshes.size(); ++index) {
        meshes[index] = mesh_library.find(names[index]);
        if (!meshes[index])
            throw std::invalid_argument("missing radial donor mesh");
        vertex_capacity += static_cast<int>(meshes[index]->vertices.size());
        index_capacity += static_cast<int>(meshes[index]->indices.size());
    }
    OwnedGeometryGenerator generator;
    generator.initialize(vertex_capacity, index_capacity);
    std::vector<DrawCall> segments;
    segments.reserve(17);
    std::vector<DrawCall> pulse_calls;
    pulse_calls.reserve(8);
    const auto line = [&](float x0, float y0, float x1, float y1, float width,
                          ysVector color) {
        generator.startShape();
        if (!generator.generateLine2d({x0, y0, x1, y1, width}))
            throw std::length_error("SEVEL radial scene capacity");
        GeometryGenerator::GeometryIndices indices;
        generator.endShape(&indices);
        segments.push_back({indices, color});
    };
    // Radial sections are laid out side by side for inspection, not to scale
    // as a measurement of the SEVEL's axial cylinder spacing.
    const float pitch = visual_estimate_radial_section_spacing_m;
    const float head_y =
        static_cast<float>(geometry.visual_estimate_rod_length_m +
                           SevelVisualGeometry::crank_radius_m +
                           dimensions.visual_estimate_head_height_m);
    const auto poses = sevel_cylinder_poses(
        snapshot.crank_angle_rad - snapshot.tdc_phase_rad, geometry);
    for (std::size_t cylinder = 0; cylinder < poses.size(); ++cylinder) {
        if (focus_cylinder != 0 &&
            cylinder + 1 != static_cast<std::size_t>(focus_cylinder))
            continue;
        const float center = focus_cylinder != 0
                                 ? 0.0f
                                 : (static_cast<float>(cylinder) - 1.5f) *
                                       pitch;
        const auto &pose = poses[cylinder];
        const float bore = 0.0864f;
        const ysVector housing{0.20f, 0.34f, 0.42f, 1.0f};
        line(center - bore / 2.0f, -0.05f, center - bore / 2.0f, head_y, 0.003f,
             housing);
        line(center + bore / 2.0f, -0.05f, center + bore / 2.0f, head_y, 0.003f,
             housing);
        line(center - bore / 2.0f, head_y, center + bore / 2.0f, head_y, 0.012f,
             housing);
        line(center + static_cast<float>(pose.crank_pin_x_m),
             static_cast<float>(pose.crank_pin_y_m), center,
             static_cast<float>(pose.piston_pin_y_m), 0.011f,
             {0.70f, 0.77f, 0.78f, 1.0f});
    }
    // One schematic shaft joins the four axial sections behind the journals.
    line(focus_cylinder != 0 ? -pitch / 2.0f : -1.5f * pitch, 0.0f,
         focus_cylinder != 0 ? pitch / 2.0f : 1.5f * pitch, 0.0f, 0.008f,
         {0.48f, 0.62f, 0.69f, 1.0f});
    for (std::size_t cylinder = 0; cylinder < pulses.size(); ++cylinder) {
        if (focus_cylinder != 0 &&
            cylinder + 1 != static_cast<std::size_t>(focus_cylinder))
            continue;
        const auto &pulse = pulses[cylinder];
        const float center = focus_cylinder != 0
                                 ? 0.0f
                                 : (static_cast<float>(cylinder) - 1.5f) *
                                       pitch;
        if (pulse.spark_strength > 0.0f) {
            const float x = center + 0.027f;
            const float y = head_y - 0.012f;
            generator.startShape();
            if (!generator.generateLine2d(
                    {x - 0.006f, y + 0.006f, x + 0.002f, y, 0.002f}) ||
                !generator.generateLine2d(
                    {x + 0.002f, y, x - 0.001f, y - 0.008f, 0.002f}))
                throw std::length_error("SEVEL radial spark capacity");
            GeometryGenerator::GeometryIndices indices;
            generator.endShape(&indices);
            pulse_calls.push_back({indices, {0.39f, 0.83f, 0.86f, 1.0f}});
        }
        if (pulse.strength <= 0.0f)
            continue;
        const float y = head_y - 0.015f;
        const float radius = 0.008f + 0.004f * pulse.strength;
        generator.startShape();
        if (!generator.generateLine2d({center - radius, y - radius,
                                       center + radius, y + radius, 0.003f}) ||
            !generator.generateLine2d({center - radius, y + radius,
                                       center + radius, y - radius, 0.003f}))
            throw std::length_error("SEVEL radial pulse scene capacity");
        GeometryGenerator::GeometryIndices indices;
        generator.endShape(&indices);
        pulse_calls.push_back(
            {indices, pulse.misfire ? ysVector{0.93f, 0.35f, 0.30f, 1.0f}
                                    : ysVector{1.0f, 0.82f, 0.36f, 1.0f}});
    }
    std::array<GeometryGenerator::GeometryIndices, 5> shapes{};
    for (std::size_t index = 0; index < meshes.size(); ++index) {
        generator.startShape();
        if (!generator.generateRawMesh(
                meshes[index]->vertices.data(),
                static_cast<int>(meshes[index]->vertices.size()),
                meshes[index]->indices.data(),
                static_cast<int>(meshes[index]->indices.size())))
            throw std::length_error("SEVEL radial mesh capacity");
        generator.endShape(&shapes[index]);
    }
    renderer.beginFrame({0.027f, 0.027f, 0.035f, 1.0f});
    renderer.setSceneViewport(0.0f, 0.0f, viewport_width, viewport_height);
    renderer.uploadGeometry(
        generator.getVertexData(), generator.getCurrentVertexCount(),
        generator.getIndexData(), generator.getCurrentIndexCount());
    const ysMatrix identity = ysMath::LoadIdentity();
    const ysMatrix projection = scene_fit_projection(
        camera, viewport_width, viewport_height,
        focus_cylinder != 0 ? 0.14f : 3.0f * pitch + 0.14f, 0.34f);
    const auto draw = [&](const GeometryGenerator::GeometryIndices &shape,
                          const ysMatrix &transform, const ysVector &color) {
        renderer.submitGeometry(
            generator.getVertexData(), generator.getIndexData(),
            shape.BaseVertex, shape.BaseIndex, shape.FaceCount, transform,
            identity, projection, color, Shaders::SceneStage, 0);
    };
    for (const auto &segment : segments)
        draw(segment.indices, identity, segment.color);
    for (std::size_t cylinder = 0; cylinder < poses.size(); ++cylinder) {
        if (focus_cylinder != 0 &&
            cylinder + 1 != static_cast<std::size_t>(focus_cylinder))
            continue;
        const float center = focus_cylinder != 0
                                 ? 0.0f
                                 : (static_cast<float>(cylinder) - 1.5f) *
                                       pitch;
        const auto &pose = poses[cylinder];
        // The donor crank mesh points to +X; the physical pose starts at +Y.
        const float angle = static_cast<float>(
            std::atan2(pose.crank_pin_y_m, pose.crank_pin_x_m));
        const float rod_angle = -static_cast<float>(pose.rod_angle_rad);
        const auto transform = [&](float x, float y, float rotation,
                                   ysVector scale) {
            return ysMath::MatMult(
                ysMath::TranslationTransform({x, y, 0.0f, 0.0f}),
                ysMath::MatMult(ysMath::RotationTransform(
                                    {0.0f, 0.0f, 1.0f, 0.0f}, rotation),
                                ysMath::ScaleTransform(scale)));
        };
        constexpr float radius =
            static_cast<float>(SevelVisualGeometry::crank_radius_m);
        const ysVector radial_scale{radius, radius, 1.0f, 1.0f};
        constexpr float bore = 0.0864f;
        const float head_scale = bore / 2.0f;
        const ysVector head_mesh_scale{head_scale, head_scale, 1.0f, 1.0f};
        draw(shapes[3], transform(center, head_y, 0.0f, head_mesh_scale),
             {0.84f, 0.50f, 0.66f, 1.0f});
        for (int valve = 0; valve < 2; ++valve) {
            const ValveKind kind =
                valve == 0 ? ValveKind::Intake : ValveKind::Exhaust;
            const float lift = static_cast<float>(
                valve_lift_fraction(snapshot.crank_angle_rad, cylinder, kind,
                                    snapshot.tdc_phase_rad) *
                dimensions.visual_estimate_valve_lift_m);
            const float valve_x =
                center + (valve == 0 ? -0.5f : 0.5f) * head_scale;
            draw(shapes[4],
                 transform(valve_x, head_y - lift, 0.0f, head_mesh_scale),
                 valve == 0 ? ysVector{0.38f, 0.79f, 0.81f, 1.0f}
                            : ysVector{0.78f, 0.52f, 0.41f, 1.0f});
        }
        draw(shapes[0], transform(center, 0.0f, angle, radial_scale),
             cylinder == 0 || cylinder == 3
                 ? ysVector{0.42f, 0.72f, 0.79f, 1.0f}
                 : ysVector{0.85f, 0.59f, 0.36f, 1.0f});
        draw(shapes[1],
             transform(center + static_cast<float>(pose.crank_pin_x_m),
                       static_cast<float>(pose.crank_pin_y_m), rod_angle,
                       radial_scale),
             {0.70f, 0.77f, 0.78f, 1.0f});
        draw(shapes[2],
             transform(center,
                       piston_mesh_origin_y(
                           static_cast<float>(pose.piston_pin_y_m)),
                       0.0f,
                       {piston_mesh_scale_m, -piston_mesh_scale_m, 1.0f, 1.0f}),
             {0.94f, 0.94f, 0.94f, 1.0f});
    }
    for (const auto &call : pulse_calls)
        draw(call.indices, identity, call.color);
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
    const float angle = static_cast<float>(std::remainder(
        pi / 2.0 - (snapshot.crank_angle_rad - snapshot.tdc_phase_rad + phase),
        2.0 * pi));
    const ysMatrix identity = ysMath::LoadIdentity();
    const ysMatrix transform =
        ysMath::RotationTransform({0.0f, 0.0f, 1.0f, 0.0f}, angle);
    ysMatrix projection = identity;
    projection.m[0][0] = 0.52f;
    projection.m[1][1] = 0.52f;
    renderer.beginFrame({0.027f, 0.027f, 0.035f, 1.0f});
    renderer.setSceneViewport(0.0f, 0.0f, viewport_size, viewport_size);
    renderer.uploadGeometry(
        mesh->vertices.data(), static_cast<int>(mesh->vertices.size()),
        mesh->indices.data(), static_cast<int>(mesh->indices.size()));
    renderer.submitGeometry(mesh->vertices.data(), mesh->indices.data(), 0, 0,
                            static_cast<int>(mesh->indices.size() / 3),
                            transform, identity, projection,
                            cylinder == 1 ? ysVector{0.42f, 0.72f, 0.79f, 1.0f}
                                          : ysVector{0.85f, 0.59f, 0.36f, 1.0f},
                            Shaders::SceneStage, 0);
    renderer.endFrame();
}

} // namespace lab
