#include "lab/SevelScene.hpp"

#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

namespace {

class RecordingRenderer final : public Renderer {
  public:
    void beginFrame(const ysVector &) override { ++frames; }
    void setSceneViewport(float, float, float width, float height) override {
        viewport_width = width;
        viewport_height = height;
    }
    void uploadGeometry(const EngineSimVertex *source, int vertex_count,
                        const std::uint16_t *source_indices,
                        int index_count) override {
        vertices.assign(source, source + vertex_count);
        indices.assign(source_indices, source_indices + index_count);
    }
    void submitGeometry(const EngineSimVertex *, const std::uint16_t *, int,
                        int base_index, int face_count, const ysMatrix &,
                        const ysMatrix &, const ysMatrix &projection,
                        const ysVector &, std::uint32_t, int) override {
        EXPECT_GE(base_index, 0);
        EXPECT_LE(base_index + face_count * 3,
                  static_cast<int>(indices.size()));
        EXPECT_FLOAT_EQ(projection.m[0][0], 4.0f);
        ++draw_calls;
    }
    void endFrame() override { ++completed_frames; }

    float piston_y(int cylinder) const {
        const std::size_t segment =
            2 + static_cast<std::size_t>(cylinder) * 5 + 4;
        const std::size_t vertex = segment * 4;
        return (vertices[vertex].Pos.y + vertices[vertex + 1].Pos.y) / 2.0f;
    }

    float valve_head_y(int cylinder, int valve) const {
        const std::size_t segment = 23 +
                                    static_cast<std::size_t>(cylinder) * 6 +
                                    static_cast<std::size_t>(valve) * 3 + 1;
        const std::size_t vertex = segment * 4;
        return (vertices[vertex].Pos.y + vertices[vertex + 1].Pos.y) / 2.0f;
    }

    float segment_center_x(std::size_t segment) const {
        const std::size_t vertex = segment * 4;
        return (vertices[vertex].Pos.x + vertices[vertex + 1].Pos.x +
                vertices[vertex + 2].Pos.x + vertices[vertex + 3].Pos.x) /
               4.0f;
    }

    int frames = 0;
    int completed_frames = 0;
    int draw_calls = 0;
    float viewport_width = 0.0f;
    float viewport_height = 0.0f;
    std::vector<EngineSimVertex> vertices;
    std::vector<std::uint16_t> indices;
};

TEST(SevelScene, DrawsFourPhysicalSliderCranksFromSnapshot) {
    RecordingRenderer renderer;
    ma17::EmulatorSnapshot snapshot;
    snapshot.crank_angle_rad = 0.0;
    lab::render_sevel_scene(renderer, snapshot, 1280.0f, 720.0f);
    EXPECT_EQ(renderer.frames, 1);
    EXPECT_EQ(renderer.completed_frames, 1);
    EXPECT_EQ(renderer.draw_calls, 47);
    EXPECT_EQ(renderer.vertices.size(), 188u);
    EXPECT_EQ(renderer.indices.size(), 282u);
    EXPECT_FLOAT_EQ(renderer.viewport_width, 1280.0f);
    EXPECT_FLOAT_EQ(renderer.viewport_height, 720.0f);
    const float top = renderer.piston_y(0);
    const float bottom = renderer.piston_y(1);
    EXPECT_NEAR(top, renderer.piston_y(3), 1e-6);
    EXPECT_NEAR(bottom, renderer.piston_y(2), 1e-6);
    EXPECT_NEAR(top - bottom, 0.0674f, 1e-6);

    snapshot.crank_angle_rad = 3.14159265358979323846;
    lab::render_sevel_scene(renderer, snapshot, 1280.0f, 720.0f);
    EXPECT_EQ(renderer.frames, 2);
    EXPECT_EQ(renderer.completed_frames, 2);
    EXPECT_NEAR(renderer.piston_y(0), bottom, 1e-6);
    EXPECT_NEAR(renderer.piston_y(1), top, 1e-6);

    snapshot.crank_angle_rad = 250.0 * 3.14159265358979323846 / 180.0;
    lab::render_sevel_scene(renderer, snapshot, 1280.0f, 720.0f);
    const float closed_intake = renderer.valve_head_y(0, 0);
    snapshot.crank_angle_rad = 450.0 * 3.14159265358979323846 / 180.0;
    lab::render_sevel_scene(renderer, snapshot, 1280.0f, 720.0f);
    EXPECT_LT(renderer.valve_head_y(0, 0), closed_intake - 0.006f);
    EXPECT_NEAR(renderer.valve_head_y(0, 1), closed_intake, 1e-6);
}

TEST(SevelScene, KeepsCrankThrowsOnCylinderAxesInLongitudinalView) {
    RecordingRenderer renderer;
    ma17::EmulatorSnapshot snapshot;
    snapshot.crank_angle_rad = 3.14159265358979323846 / 2.0;
    lab::render_sevel_scene(renderer, snapshot, 1280.0f, 720.0f);
    for (std::size_t cylinder = 0; cylinder < 4; ++cylinder) {
        const float center = (static_cast<float>(cylinder) - 1.5f) * 0.095f;
        const std::size_t first_segment = 2 + cylinder * 5;
        EXPECT_NEAR(renderer.segment_center_x(first_segment + 2), center,
                    1e-6f);
        EXPECT_NEAR(renderer.segment_center_x(first_segment + 3), center,
                    1e-6f);
    }
}

} // namespace
