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
#include <cmath>
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

    ma17::EmulatorSnapshot reference;
    ma17::EmulatorSnapshot shifted;
    shifted.crank_angle_rad = 2.0 * 3.14159265358979323846 / 3.0;
    shifted.tdc_phase_rad = shifted.crank_angle_rad;
    lab::RecordingRenderer at_tdc;
    lab::RecordingRenderer shifted_tdc;
    lab::render_sevel_scene_donor(at_tdc, reference, 1280.0f, 720.0f);
    lab::render_sevel_scene_donor(shifted_tdc, shifted, 1280.0f, 720.0f);
    const auto expected = segment_bounds(at_tdc);
    const auto actual = segment_bounds(shifted_tdc);
    ASSERT_EQ(actual.size(), expected.size());
    for (std::size_t segment = 0; segment < expected.size(); ++segment)
        for (std::size_t edge = 0; edge < 4; ++edge)
            EXPECT_NEAR(actual[segment][edge], expected[segment][edge], 0.001f)
                << "segment " << segment << ", edge " << edge;
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

TEST(DonorScene, ShowsBothSparkGapsWithoutDuplicatingCombustion) {
    ma17::EmulatorSnapshot snapshot;
    std::array<lab::ScenePulse, 4> pulses{};
    pulses[0] = {1.0f, false, 1.0f};
    pulses[3].spark_strength = 1.0f;
    lab::RecordingRenderer renderer;
    lab::render_sevel_scene_donor(renderer, snapshot, 1280.0f, 720.0f, {}, {},
                                  {}, nullptr, pulses);
    EXPECT_EQ(renderer.draw_calls(), 50);
    EXPECT_EQ(renderer.triangle_count(), 106U);
    int spark_triangles = 0;
    int burn_triangles = 0;
    renderer.for_each_triangle([&](const auto &, const ysVector &color) {
        if (std::abs(color.x - 0.39f) < 0.001f &&
            std::abs(color.y - 0.83f) < 0.001f)
            ++spark_triangles;
        if (std::abs(color.x - 1.0f) < 0.001f &&
            std::abs(color.y - 0.82f) < 0.001f)
            ++burn_triangles;
    });
    EXPECT_EQ(spark_triangles, 8);
    EXPECT_EQ(burn_triangles, 4);
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
    expected_faces += 4 * library.find("Piston")->indices.size() / 3;
    expected_faces += 8 * library.find("Valve")->indices.size() / 3;
    EXPECT_EQ(renderer.draw_calls(), 59);
    EXPECT_EQ(renderer.scene_draw_calls(), renderer.draw_calls());
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
    EXPECT_EQ(pair_14.scene_draw_calls(), pair_14.draw_calls());
    EXPECT_EQ(pair_23.scene_draw_calls(), pair_23.draw_calls());
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
    snapshot.tdc_phase_rad = 1.2;
    lab::RecordingRenderer shifted_to_tdc;
    ma17::EmulatorSnapshot tdc;
    lab::RecordingRenderer reference_tdc;
    lab::render_axial_crank_donor(shifted_to_tdc, snapshot, 88.0f, library, 1);
    lab::render_axial_crank_donor(reference_tdc, tdc, 88.0f, library, 1);
    std::array<float, 2> shifted_point{};
    std::array<float, 2> reference_point{};
    bool first_shifted = true;
    shifted_to_tdc.for_each_triangle(
        [&](const auto &points, const auto &) {
            if (first_shifted) {
                shifted_point = {points[0].x, points[0].y};
                first_shifted = false;
            }
        });
    bool first_reference = true;
    reference_tdc.for_each_triangle(
        [&](const auto &points, const auto &) {
            if (first_reference) {
                reference_point = {points[0].x, points[0].y};
                first_reference = false;
            }
        });
    EXPECT_FALSE(first_shifted);
    EXPECT_FALSE(first_reference);
    EXPECT_NEAR(shifted_point[0], reference_point[0], 0.001f);
    EXPECT_NEAR(shifted_point[1], reference_point[1], 0.001f);
    const auto &crank_mesh = *library.find("Crankshaft");
    const auto &local = crank_mesh.vertices[crank_mesh.indices[0]].Pos;
    EXPECT_NEAR(reference_point[0], 44.0f - 22.88f * local.y, 0.001f);
    EXPECT_NEAR(reference_point[1], 44.0f - 22.88f * local.x, 0.001f);
    EXPECT_THROW(
        lab::render_axial_crank_donor(pair_14, snapshot, 88.0f, library, 3),
        std::invalid_argument);
}

TEST(DonorScene, RadialRodFollowsCrankAndOpposedPairs) {
    AuthoredMeshLibrary library;
    ASSERT_TRUE(lab::load_packaged_meshes(library, LAB_MESH_ASSET_PATH));
    ma17::EmulatorSnapshot snapshot;
    lab::RecordingRenderer tdc;
    lab::render_sevel_radial_donor(tdc, snapshot, 1280.0f, 720.0f, library);
    const std::size_t mesh_faces =
        (library.find("Crankshaft")->indices.size() +
         library.find("ConnectingRod")->indices.size() +
         library.find("Piston")->indices.size()) /
        3;
    const std::size_t head_faces =
        library.find("CylinderHead")->indices.size() / 3;
    const std::size_t valve_faces = library.find("Valve")->indices.size() / 3;
    EXPECT_EQ(tdc.draw_calls(), 41);
    EXPECT_EQ(tdc.scene_draw_calls(), tdc.draw_calls());
    EXPECT_EQ(tdc.triangle_count(),
              34U + 4 * (mesh_faces + head_faces) + 8 * valve_faces);
    const auto aligned = segment_bounds(tdc);
    ASSERT_GE(aligned.size(), 17U);
    EXPECT_NEAR(aligned[3][1], aligned[15][1], 0.001f);
    EXPECT_NEAR(aligned[7][1], aligned[11][1], 0.001f);
    EXPECT_GT(std::abs(aligned[3][1] - aligned[7][1]), 50.0f);
    EXPECT_GT(aligned[16][2] - aligned[16][0], 500.0f);
    EXPECT_LT(aligned[16][3] - aligned[16][1], 20.0f);
    const auto &crank_mesh = *library.find("Crankshaft");
    const auto &crank_local = crank_mesh.vertices[crank_mesh.indices[0]].Pos;
    const std::size_t crank_triangle = 34U + head_faces + 2 * valve_faces;
    std::array<float, 2> crank_point{};
    std::size_t triangle = 0;
    tdc.for_each_triangle([&](const auto &points, const auto &) {
        if (triangle++ == crank_triangle)
            crank_point = {points[0].x, points[0].y};
    });
    const float radius =
        static_cast<float>(lab::SevelVisualGeometry::crank_radius_m);
    const float center = -1.5f * lab::visual_estimate_radial_section_spacing_m;
    EXPECT_NEAR(crank_point[0],
                (4.0f * (center - radius * crank_local.y) + 1.0f) * 640.0f,
                0.02f);
    EXPECT_NEAR(crank_point[1],
                (1.62f - 4.0f * radius * crank_local.x) * 360.0f, 0.02f);

    const auto first_intake_top = [](const lab::RecordingRenderer &frame) {
        float top = std::numeric_limits<float>::max();
        frame.for_each_triangle([&](const auto &points, const ysVector &color) {
            if (std::abs(color.x - 0.38f) > 0.001f ||
                std::abs(color.y - 0.79f) > 0.001f)
                return;
            for (const auto &point : points)
                if (point.x < 350.0f)
                    top = std::min(top, point.y);
        });
        return top;
    };
    snapshot.crank_angle_rad = 2.5 * 3.14159265358979323846;
    lab::RecordingRenderer intake_open;
    lab::render_sevel_radial_donor(intake_open, snapshot, 1280.0f, 720.0f,
                                   library);
    EXPECT_GT(first_intake_top(intake_open), first_intake_top(tdc) + 5.0f);

    snapshot.crank_angle_rad = 570.0 * 3.14159265358979323846 / 180.0;
    snapshot.tdc_phase_rad = 120.0 * 3.14159265358979323846 / 180.0;
    lab::RecordingRenderer shifted_intake;
    lab::render_sevel_radial_donor(shifted_intake, snapshot, 1280.0f, 720.0f,
                                   library);
    EXPECT_NEAR(first_intake_top(shifted_intake), first_intake_top(intake_open),
                0.001f);
    const auto shifted_segments = segment_bounds(shifted_intake);
    const auto open_segments = segment_bounds(intake_open);
    ASSERT_GE(shifted_segments.size(), 16U);
    ASSERT_GE(open_segments.size(), 16U);
    for (std::size_t segment = 0; segment < 16; ++segment)
        for (std::size_t edge = 0; edge < 4; ++edge)
            EXPECT_NEAR(shifted_segments[segment][edge],
                        open_segments[segment][edge], 0.001f);
    snapshot.tdc_phase_rad = 0.0;

    snapshot.crank_angle_rad = 3.14159265358979323846 / 2.0;
    lab::RecordingRenderer quarter_turn;
    lab::render_sevel_radial_donor(quarter_turn, snapshot, 1280.0f, 720.0f,
                                   library);
    const auto swept = segment_bounds(quarter_turn);
    ASSERT_GE(swept.size(), 16U);
    EXPECT_GT(swept[3][2], aligned[3][2] + 50.0f);
    const auto &rod_mesh = *library.find("ConnectingRod");
    const auto &rod_local = rod_mesh.vertices[rod_mesh.indices[0]].Pos;
    const auto pose = lab::cylinder_pose(3.14159265358979323846 / 2.0, 1);
    const float dx = static_cast<float>(pose.crank_pin_x_m);
    const float dy = static_cast<float>(pose.piston_pin_y_m - pose.crank_pin_y_m);
    const float rod_rotation = std::atan2(dx, dy);
    const float world_x =
        center + dx + radius * (std::cos(rod_rotation) * rod_local.x -
                                std::sin(rod_rotation) * rod_local.y);
    const float world_y =
        radius * (std::sin(rod_rotation) * rod_local.x +
                  std::cos(rod_rotation) * rod_local.y);
    const std::size_t rod_triangle = 34U + head_faces + 2 * valve_faces +
                                     crank_mesh.indices.size() / 3;
    std::array<float, 2> rod_point{};
    triangle = 0;
    quarter_turn.for_each_triangle([&](const auto &points, const auto &) {
        if (triangle++ == rod_triangle)
            rod_point = {points[0].x, points[0].y};
    });
    EXPECT_NEAR(rod_point[0], (4.0f * world_x + 1.0f) * 640.0f, 0.02f);
    EXPECT_NEAR(rod_point[1], (1.62f - 4.0f * world_y) * 360.0f, 0.02f);

    snapshot.crank_angle_rad = 4.0 * 3.14159265358979323846;
    lab::RecordingRenderer next_cycle;
    lab::render_sevel_radial_donor(next_cycle, snapshot, 1280.0f, 720.0f,
                                   library);
    const auto wrapped = segment_bounds(next_cycle);
    ASSERT_GE(wrapped.size(), 17U);
    for (std::size_t segment = 0; segment < 17; ++segment)
        for (std::size_t edge = 0; edge < 4; ++edge)
            EXPECT_NEAR(wrapped[segment][edge], aligned[segment][edge], 0.001f);

    std::array<lab::ScenePulse, 4> pulses{};
    pulses[0] = {1.0f, false};
    pulses[2] = {0.6f, true};
    lab::RecordingRenderer with_pulses;
    lab::render_sevel_radial_donor(with_pulses, snapshot, 1280.0f, 720.0f,
                                   library, {}, {}, {}, pulses);
    EXPECT_EQ(with_pulses.draw_calls(), 43);
    EXPECT_EQ(with_pulses.triangle_count(),
              42U + 4 * (mesh_faces + head_faces) + 8 * valve_faces);
    ysVector last_color{};
    with_pulses.for_each_triangle(
        [&](const auto &, const ysVector &color) { last_color = color; });
    EXPECT_NEAR(last_color.x, 0.93f, 0.001f);
    EXPECT_NEAR(last_color.y, 0.35f, 0.001f);

    pulses[0].spark_strength = 1.0f;
    pulses[3].spark_strength = 1.0f;
    lab::RecordingRenderer with_sparks;
    lab::render_sevel_radial_donor(with_sparks, snapshot, 1280.0f, 720.0f,
                                   library, {}, {}, {}, pulses);
    EXPECT_EQ(with_sparks.draw_calls(), 45);
    EXPECT_EQ(with_sparks.triangle_count(),
              50U + 4 * (mesh_faces + head_faces) + 8 * valve_faces);
}

TEST(DonorScene, FocusedAxialSectionKeepsPhysicalPairPhases) {
    AuthoredMeshLibrary library;
    ASSERT_TRUE(lab::load_packaged_meshes(library, LAB_MESH_ASSET_PATH));
    ma17::EmulatorSnapshot snapshot;
    const auto *crank_mesh = library.find("Crankshaft");
    ASSERT_NE(crank_mesh, nullptr);
    const auto &local = crank_mesh->vertices[crank_mesh->indices[0]].Pos;
    const std::size_t head_faces =
        library.find("CylinderHead")->indices.size() / 3;
    const std::size_t valve_faces = library.find("Valve")->indices.size() / 3;
    const std::size_t crank_triangle = 10U + head_faces + 2 * valve_faces;
    const auto crank_point = [&](int cylinder) {
        lab::RecordingRenderer frame;
        lab::render_sevel_radial_donor(frame, snapshot, 1280.0f, 720.0f,
                                       library, {}, {}, {}, {}, cylinder);
        EXPECT_EQ(frame.draw_calls(), 11);
        std::array<float, 2> point{};
        std::size_t triangle = 0;
        frame.for_each_triangle([&](const auto &points, const auto &) {
            if (triangle++ == crank_triangle)
                point = {points[0].x, points[0].y};
        });
        EXPECT_GT(triangle, crank_triangle);
        return point;
    };
    const auto one = crank_point(1);
    const auto two = crank_point(2);
    const auto four = crank_point(4);
    const float radius =
        static_cast<float>(lab::SevelVisualGeometry::crank_radius_m);
    EXPECT_NEAR(one[0], (1.0f - 4.0f * radius * local.y) * 640.0f, 0.02f);
    EXPECT_NEAR(two[0], (1.0f + 4.0f * radius * local.y) * 640.0f, 0.02f);
    EXPECT_NEAR(one[0], four[0], 0.02f);
    EXPECT_NEAR(one[1], four[1], 0.02f);
    lab::RecordingRenderer invalid;
    EXPECT_THROW(lab::render_sevel_radial_donor(
                     invalid, snapshot, 1280.0f, 720.0f, library, {}, {}, {},
                     {}, 5),
                 std::invalid_argument);
}
#endif

} // namespace
