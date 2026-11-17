#include "lab/DonorScene.hpp"
#ifdef SEVEL_LAB_MESH_ASSET
#include "lab/MeshAsset.hpp"
#endif
#include "gauge.h"
#include "lab/RecordingRenderer.hpp"
#include "lab/SevelScene.hpp"
#include "oscilloscope.h"

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

using Bounds = std::array<float, 4>;

TEST(DonorGauge, TracksValueWithoutEscapingDial) {
    Gauge gauge;
    gauge.m_max = 7000.0f;
    gauge.reset(0.0f);
    gauge.m_value = 3500.0f;
    for (int frame = 0; frame < 30; ++frame)
        gauge.update(1.0f / 60.0f);
    EXPECT_GT(gauge.needlePosition(), 0.25f);
    EXPECT_LE(gauge.needlePosition(), 1.0f);
    gauge.m_value = 9000.0f;
    for (int frame = 0; frame < 60; ++frame)
        gauge.update(1.0f / 60.0f);
    EXPECT_NEAR(gauge.needlePosition(), 1.0f, 0.02f);
    gauge.setBandCount(-1);
    EXPECT_THROW(gauge.setBand({}, 0), std::out_of_range);
}

TEST(DonorOscilloscope, KeepsRecentSamplesInTimeOrder) {
    Oscilloscope scope;
    scope.setBufferSize(3);
    for (int x = 1; x <= 4; ++x)
        scope.addDataPoint(x, x * 10);
    const auto points = scope.orderedPoints();
    ASSERT_EQ(points.size(), 3U);
    EXPECT_FLOAT_EQ(points[0].x, 2.0f);
    EXPECT_FLOAT_EQ(points[1].x, 3.0f);
    EXPECT_FLOAT_EQ(points[2].x, 4.0f);
    EXPECT_FLOAT_EQ(points[2].y, 40.0f);
    scope.setBufferSize(0);
    scope.addDataPoint(5.0, 50.0);
    EXPECT_TRUE(scope.orderedPoints().empty());
}

std::vector<Bounds> segment_bounds(const lab::RecordingRenderer &renderer) {
    std::vector<Bounds> bounds;
    std::size_t triangle = 0;
    renderer.for_each_triangle([&](const auto &points, const ysVector &) {
        if (triangle++ % 2 == 0)
            bounds.push_back({std::numeric_limits<float>::max(),
                              std::numeric_limits<float>::max(),
                              std::numeric_limits<float>::lowest(),
                              std::numeric_limits<float>::lowest()});
        for (const auto &point : points) {
            auto &box = bounds.back();
            box[0] = std::min(box[0], point.x);
            box[1] = std::min(box[1], point.y);
            box[2] = std::max(box[2], point.x);
            box[3] = std::max(box[3], point.y);
        }
    });
    return bounds;
}

TEST(DonorScene, MatchesPhysicalSceneAtCrankAndValvePhases) {
    for (double angle : {0.0, 1.2, 4.36, 7.85}) {
        ma17::EmulatorSnapshot snapshot;
        snapshot.crank_angle_rad = angle;
        lab::RecordingRenderer original;
        lab::RecordingRenderer donor;
        lab::render_sevel_scene(original, snapshot, 1280.0f, 720.0f);
        lab::render_sevel_scene_donor(donor, snapshot, 1280.0f, 720.0f);
        ASSERT_EQ(original.draw_calls(), 47);
        ASSERT_EQ(donor.draw_calls(), original.draw_calls());
        ASSERT_EQ(donor.triangle_count(), original.triangle_count());
        const auto expected = segment_bounds(original);
        const auto actual = segment_bounds(donor);
        ASSERT_EQ(actual.size(), expected.size());
        for (std::size_t segment = 0; segment < expected.size(); ++segment)
            for (std::size_t edge = 0; edge < 4; ++edge)
                EXPECT_NEAR(actual[segment][edge], expected[segment][edge],
                            0.001f)
                    << "segment " << segment << ", edge " << edge;
    }
}

TEST(DonorScene, CameraZoomAndPanTransformMechanicalGeometry) {
    ma17::EmulatorSnapshot snapshot;
    snapshot.crank_angle_rad = 1.2;
    lab::RecordingRenderer base;
    lab::RecordingRenderer moved;
    lab::render_sevel_scene_donor(base, snapshot, 1280.0f, 720.0f);
    lab::render_sevel_scene_donor(moved, snapshot, 1280.0f, 720.0f, {}, {},
                                  {2.0f, 40.0f, -20.0f});
    const auto original = segment_bounds(base);
    const auto transformed = segment_bounds(moved);
    ASSERT_EQ(original.size(), transformed.size());
    for (std::size_t segment = 0; segment < original.size(); ++segment) {
        for (std::size_t edge = 0; edge < 4; ++edge) {
            // The donor scene's default Y projection offsets its origin
            // by 0.4 clip units, so zoom pivots around pixel Y=504.
            const float center = edge % 2 == 0 ? 640.0f : 504.0f;
            const float pan = edge % 2 == 0 ? 40.0f : -20.0f;
            EXPECT_NEAR(transformed[segment][edge],
                        center + (original[segment][edge] - center) * 2.0f +
                            pan,
                        0.001f);
        }
    }
}

TEST(DonorScene, ShowsCombustionAndMisfireAsTemporaryMarkers) {
    ma17::EmulatorSnapshot snapshot;
    std::array<lab::ScenePulse, 4> pulses{};
    pulses[0] = {1.0f, false};
    pulses[2] = {0.6f, true};
    lab::RecordingRenderer renderer;
    lab::render_sevel_scene_donor(renderer, snapshot, 1280.0f, 720.0f, {}, {},
                                  {}, nullptr, pulses);
    EXPECT_EQ(renderer.draw_calls(), 49);
    EXPECT_EQ(renderer.triangle_count(), 102U);
    ysVector last_color{};
    renderer.for_each_triangle(
        [&](const auto &, const ysVector &color) { last_color = color; });
    EXPECT_NEAR(last_color.x, 0.93f, 0.001f);
    EXPECT_NEAR(last_color.y, 0.35f, 0.001f);
}

#ifdef SEVEL_LAB_MESH_ASSET
TEST(DonorScene, RendersImportedMechanicalMeshes) {
    AuthoredMeshLibrary library;
    ASSERT_TRUE(lab::load_packaged_meshes(library, LAB_MESH_ASSET_PATH));
    ma17::EmulatorSnapshot snapshot;
    snapshot.crank_angle_rad = 1.2;
    lab::RecordingRenderer renderer;
    lab::render_sevel_scene_donor(renderer, snapshot, 1280.0f, 720.0f, {}, {},
                                  {}, &library);
    std::size_t expected_faces = 94;
    for (const char *name : {"ConnectingRod", "Piston"})
        expected_faces += 4 * library.find(name)->indices.size() / 3;
    expected_faces += library.find("CylinderHead")->indices.size() / 3;
    expected_faces += 8 * library.find("Valve")->indices.size() / 3;
    EXPECT_EQ(renderer.draw_calls(), 64);
    EXPECT_EQ(renderer.triangle_count(), expected_faces);
}

TEST(DonorScene, AxialCrankPairsAreOpposed) {
    AuthoredMeshLibrary library;
    ASSERT_TRUE(lab::load_packaged_meshes(library, LAB_MESH_ASSET_PATH));
    ma17::EmulatorSnapshot snapshot;
    snapshot.crank_angle_rad = 1.2;
    lab::RecordingRenderer pair_14;
    lab::RecordingRenderer pair_23;
    lab::render_axial_crank_donor(pair_14, snapshot, 88.0f, library, 1);
    lab::render_axial_crank_donor(pair_23, snapshot, 88.0f, library, 2);
    const auto expected_faces = library.find("Crankshaft")->indices.size() / 3;
    EXPECT_EQ(pair_14.draw_calls(), 1);
    EXPECT_EQ(pair_14.triangle_count(), expected_faces);
    EXPECT_EQ(pair_23.triangle_count(), expected_faces);
    std::array<float, 2> first{};
    std::array<float, 2> opposite{};
    bool seen = false;
    pair_14.for_each_triangle([&](const auto &points, const auto &) {
        if (!seen) {
            first = {points[0].x, points[0].y};
            seen = true;
        }
    });
    seen = false;
    pair_23.for_each_triangle([&](const auto &points, const auto &) {
        if (!seen) {
            opposite = {points[0].x, points[0].y};
            seen = true;
        }
    });
    EXPECT_NEAR(first[0] + opposite[0], 88.0f, 0.001f);
    EXPECT_NEAR(first[1] + opposite[1], 88.0f, 0.001f);
    EXPECT_THROW(
        lab::render_axial_crank_donor(pair_14, snapshot, 88.0f, library, 3),
        std::invalid_argument);
}
#endif

} // namespace
