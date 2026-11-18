#include "lab/DonorScene.hpp"
#ifdef SEVEL_LAB_MESH_ASSET
#include "lab/MeshAsset.hpp"
#endif
#include "ecu_hw/Ma17Tachometer.hpp"
#include "gauge.h"
#include "geometry_generator.h"
#include "lab/RecordingRenderer.hpp"
#include "lab/SceneCameraFit.hpp"
#include "lab/ScopeDecimation.hpp"
#include "lab/SevelScene.hpp"
#include "labeled_gauge_layout.h"
#include "oscilloscope.h"
#include "oscilloscope_path.h"

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using Bounds = std::array<float, 4>;

TEST(DonorScope, PathWidthPreservesDonorTaperAndTip) {
    EXPECT_FLOAT_EQ(oes::oscilloscope_path_width(0.0f), 0.5f);
    EXPECT_FLOAT_EQ(oes::oscilloscope_path_width(0.5f), 0.5f);
    EXPECT_FLOAT_EQ(oes::oscilloscope_path_width(0.75f), 0.75f);
    EXPECT_FLOAT_EQ(oes::oscilloscope_path_width(0.95f), 0.95f);
    // A 100-point path ends at s=99/100, not at 1: tip width is 2.59 px.
    EXPECT_NEAR(oes::oscilloscope_path_width(0.99f), 2.59f, 0.00001f);
    // The donor adds the tip highlight after scaling the base stroke.
    EXPECT_NEAR(oes::oscilloscope_path_width(0.99f, 2.0f), 3.58f, 0.00001f);
    float previous = 0.0f;
    for (int i = 0; i < 100; ++i) {
        const float width =
            oes::oscilloscope_path_width(static_cast<float>(i) / 100.0f);
        EXPECT_GE(width, previous);
        EXPECT_GE(width, 0.5f);
        EXPECT_LT(width, 3.0f);
        previous = width;
    }
}

TEST(DonorGauge, LabelLayoutPreservesDonorCoordinatesAndUniformScale) {
    // OES LabeledGauge::render: 10 px inset, 90% dial band, -20 px center.
    // A 340x204 cell gives a 320x165.6 dial, radius 82.8 and center (170,72.8).
    for (const float scale : {1.0f, 1.5f, 2.0f}) {
        const auto layout = labeled_gauge_layout(
            ::Bounds(0.0f, 340.0f * scale, 0.0f, 204.0f * scale), 10.0f * scale,
            -20.0f * scale);
        EXPECT_NEAR(layout.title.bottom(), 175.6f * scale, 0.0001f);
        EXPECT_NEAR(layout.title.top(), 194.0f * scale, 0.0001f);
        EXPECT_NEAR(layout.gauge.width(), 320.0f * scale, 0.0001f);
        EXPECT_NEAR(layout.gauge.height(), 165.6f * scale, 0.0001f);
        EXPECT_NEAR(layout.radius, 82.8f * scale, 0.0001f);
        EXPECT_NEAR(layout.center.x, 170.0f * scale, 0.0001f);
        EXPECT_NEAR(layout.center.y, 72.8f * scale, 0.0001f);
        EXPECT_NEAR(layout.needle_outer_radius, 57.96f * scale, 0.0001f);
        EXPECT_NEAR(layout.needle_inner_radius, 8.28f * scale, 0.0001f);
        EXPECT_NEAR(layout.value.height(), 41.4f * scale, 0.0001f);
    }
}

TEST(Tachometer, MeasuresEdgesAndTimesOutWithoutCrankInput) {
    ecu_hw::Ma17Tachometer meter;
    EXPECT_FALSE(meter.available());
    meter.observe(true, 0); // Initial high level is not a pulse.
    EXPECT_EQ(meter.pulses(), 0U);
    meter.observe(false, 1);
    meter.observe(true, 100);
    EXPECT_DOUBLE_EQ(meter.rpm(100), 0.0);
    meter.observe(false, 200);
    meter.observe(true, 29800);
    EXPECT_DOUBLE_EQ(meter.rpm(29800), 1000.0);
    meter.observe(true, 30000); // A held level must not add an edge.
    EXPECT_EQ(meter.pulses(), 2U);
    EXPECT_DOUBLE_EQ(meter.rpm(524800), 0.0);
    meter.observe(false, 524801);
    meter.observe(true, 524802);
    EXPECT_DOUBLE_EQ(meter.rpm(524802), 0.0);
    meter.observe(false, 524803);
    meter.observe(true, 539652);
    EXPECT_DOUBLE_EQ(meter.rpm(539652), 2000.0);
}

TEST(DonorScene, FittedProjectionPreservesPhysicalAspectRatio) {
    for (const auto &[width, height] :
         {std::pair{269.0f, 576.0f}, std::pair{403.0f, 864.0f},
          std::pair{720.0f, 1152.0f}}) {
        const auto projection = lab::scene_fit_projection(
            {0.78f, 0.0f, 0.0f}, width, height, 0.403f, 0.34f);
        EXPECT_NEAR(projection.m[0][0] * width, projection.m[1][1] * height,
                    0.001f);
    }
}

TEST(DonorGauge, NeedlePositionAlreadyIncludesGammaAndIsNotAppliedTwice) {
    Gauge gauge;
    gauge.m_min = 0.0f;
    gauge.m_max = 100.0f;
    gauge.m_gamma = 2.0f;
    gauge.m_thetaMin = 1.2f * 3.14159265f;
    gauge.m_thetaMax = -0.2f * 3.14159265f;
    gauge.reset(50.0f);
    // The tick for value 50 sits at fraction 0.5; gamma maps it to s = 0.25.
    EXPECT_NEAR(gauge.needlePosition(), 0.25f, 1e-6f);
    const float tick_angle = gauge.angleForFraction(0.5f);
    EXPECT_NEAR(gauge.angleForPosition(gauge.needlePosition()), tick_angle,
                1e-5f);
    // Feeding the post-gamma position back through angleForFraction applies
    // gamma twice (s = 0.0625) and misplaces the needle by about 0.7 rad.
    EXPECT_GT(
        std::fabs(gauge.angleForFraction(gauge.needlePosition()) - tick_angle),
        0.5f);
    // gamma = 1 keeps both conversions identical.
    gauge.m_gamma = 1.0f;
    gauge.reset(50.0f);
    EXPECT_NEAR(gauge.angleForPosition(gauge.needlePosition()),
                gauge.angleForFraction(0.5f), 1e-6f);
}

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

TEST(DonorGauge, GeneratedNeedleKeepsWidthAtEveryAngleAndDpi) {
    struct Generator : GeometryGenerator {
        ~Generator() { destroy(); }
    } generator;
    generator.initialize(4, 6);
    for (const float scale : {1.0f, 1.5f, 2.0f}) {
        for (const float theta : {-0.6283185f, 1.5707963f, 3.7699112f}) {
            generator.reset();
            generator.startShape();
            const float x = std::cos(theta), y = std::sin(theta);
            GeometryGenerator::Line2dParameters line{};
            line.x0 = -8.28f * scale * x;
            line.y0 = -8.28f * scale * y;
            line.x1 = 57.96f * scale * x;
            line.y1 = 57.96f * scale * y;
            line.lineWidth = 4.0f * scale;
            ASSERT_TRUE(generator.generateLine2d(line));
            GeometryGenerator::GeometryIndices shape;
            generator.endShape(&shape);
            ASSERT_EQ(generator.getCurrentVertexCount(), 4);
            ASSERT_EQ(generator.getCurrentIndexCount(), 6);
            for (int i = 0; i < 4; ++i) {
                const auto &p = generator.getVertexData()[i].Pos;
                EXPECT_NEAR(std::abs(-y * p.x + x * p.y), 2.0f * scale,
                            0.0001f);
                EXPECT_NEAR(x * p.x + y * p.y,
                            (i < 2 ? -8.28f : 57.96f) * scale, 0.0001f);
            }
            for (int i = 0; i < 6; ++i)
                EXPECT_LT(generator.getIndexData()[i], 4);
        }
    }
}

TEST(DonorGauge, GeneratedBandsPreserveRadiiAndAngularEndpoints) {
    struct Generator : GeometryGenerator {
        ~Generator() { destroy(); }
    } generator;
    generator.initialize(4096, 12288);
    for (const float scale : {1.0f, 1.5f, 2.0f}) {
        generator.reset();
        generator.startShape();
        GeometryGenerator::Ring2dParameters ring;
        ring.innerRadius = 79.8f * scale;
        ring.outerRadius = 82.8f * scale;
        ring.startAngle = -0.6283185f;
        ring.endAngle = 3.7699112f;
        ring.maxEdgeLength = 5.0f;
        ASSERT_TRUE(generator.generateRing2d(ring));
        GeometryGenerator::GeometryIndices shape;
        generator.endShape(&shape);
        const int count = generator.getCurrentVertexCount();
        ASSERT_GT(count, 6);
        ASSERT_EQ(count % 2, 0);
        for (int i = 0; i < count; ++i) {
            const auto &p = generator.getVertexData()[i].Pos;
            const float radius = i % 2 ? ring.innerRadius : ring.outerRadius;
            EXPECT_NEAR(std::hypot(p.x, p.y), radius, 0.0001f);
            if (i < 2 || i >= count - 2) {
                const float angle = i < 2 ? ring.startAngle : ring.endAngle;
                EXPECT_NEAR(p.x, radius * std::cos(angle), 0.0001f);
                EXPECT_NEAR(p.y, radius * std::sin(angle), 0.0001f);
            }
        }
        for (int i = 0; i < generator.getCurrentIndexCount(); ++i)
            EXPECT_LT(generator.getIndexData()[i], count);
    }
}

TEST(DonorGauge, LowPassIsMonotonicAndFrameRateIndependent) {
    for (const int fps : {20, 60, 144}) {
        Gauge gauge;
        gauge.m_max = 7000.0f;
        gauge.m_needleTimeConstant = 0.2f;
        gauge.reset(1000.0f);
        gauge.m_value = 4000.0f;
        float previous = gauge.needlePosition();
        for (int frame = 0; frame < fps; ++frame) {
            gauge.update(1.0f / static_cast<float>(fps));
            EXPECT_GE(gauge.needlePosition(), previous);
            EXPECT_LE(gauge.needlePosition(), 4000.0f / 7000.0f);
            previous = gauge.needlePosition();
        }
        EXPECT_NEAR(gauge.needlePosition(),
                    (4000.0f - 3000.0f * std::exp(-5.0f)) / 7000.0f, 1e-6f);
        gauge.m_value = 0.0f;
        gauge.update(0.2f);
        EXPECT_NEAR(gauge.needlePosition(), previous * std::exp(-1.0f), 1e-6f);
        previous = gauge.needlePosition();
        gauge.m_value = std::numeric_limits<float>::quiet_NaN();
        gauge.update(0.1f);
        EXPECT_FLOAT_EQ(gauge.needlePosition(), previous);
    }
}

TEST(DonorGauge, ReusesSweepAndTickGeometry) {
    Gauge gauge;
    gauge.m_thetaMin = 1.2f * 3.14159265f;
    gauge.m_thetaMax = -0.2f * 3.14159265f;
    gauge.m_minorStep = 200;
    gauge.m_majorStep = 1000;
    gauge.m_maxMinorTick = 600;
    EXPECT_NEAR(gauge.angleForFraction(0.0f), gauge.m_thetaMin, 1e-6f);
    EXPECT_NEAR(gauge.angleForFraction(0.5f), 0.5f * 3.14159265f, 1e-6f);
    EXPECT_NEAR(gauge.angleForFraction(1.0f), gauge.m_thetaMax, 1e-6f);
    EXPECT_TRUE(gauge.isMajorTick(1000));
    EXPECT_FALSE(gauge.isMajorTick(200));
    EXPECT_TRUE(gauge.showsTick(200));
    EXPECT_FALSE(gauge.showsTick(600));
    EXPECT_TRUE(gauge.showsTick(1000));
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

TEST(LabScope, DecimationKeepsPeakAndGap) {
    struct Sample {
        long long tick;
        double value;
        bool valid;
    };
    const std::vector<Sample> samples{
        {0, 1.0, true}, {1, 1.1, true},  {2, 8.0, true}, {3, -2.0, true},
        {4, 1.2, true}, {5, 0.0, false}, {6, 3.0, true}, {20, 4.0, true}};
    const auto indices = lab::decimate_scope_samples(
        samples, 0, 20, 2, 8,
        [](const Sample &sample) -> std::optional<double> {
            return sample.valid ? std::optional<double>{sample.value}
                                : std::nullopt;
        });
    EXPECT_TRUE(std::is_sorted(indices.begin(), indices.end()));
    for (const std::size_t index : {0U, 2U, 3U, 4U, 5U, 6U, 7U})
        EXPECT_TRUE(std::binary_search(indices.begin(), indices.end(), index));
}

TEST(LabScope, DecimationKeepsNonfiniteAndResetBoundaries) {
    struct Sample {
        long long tick;
        double value;
    };
    const std::vector<Sample> samples{
        {0, 1.0},  {1, 1.0},  {2, 9.0},
        {3, 1.0},  {4, 1.0},  {5, std::numeric_limits<double>::quiet_NaN()},
        {6, 2.0},  {7, 2.0},  {8, 2.0},
        {30, 3.0}, {31, 3.0}, {9, -4.0},
        {10, 2.0}};
    const auto indices = lab::decimate_scope_samples(
        samples, 0, 31, 1, 10,
        [](const Sample &sample) -> std::optional<double> {
            return sample.value;
        });
    EXPECT_TRUE(std::is_sorted(indices.begin(), indices.end()));
    for (const std::size_t boundary : {2U, 5U, 6U, 8U, 9U, 10U, 11U, 12U})
        EXPECT_TRUE(
            std::binary_search(indices.begin(), indices.end(), boundary))
            << boundary;
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
    const auto fitted = lab::scene_fit_projection({}, 1280.0f, 720.0f,
                                                  3.4f * 0.095f + 0.08f, 0.34f);
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
            for (std::size_t edge = 0; edge < 4; ++edge) {
                const float old = expected[segment][edge];
                const float mapped =
                    edge % 2 == 0
                        ? (1.0f + fitted.m[0][0] * (old - 640.0f) / 2560.0f) *
                              640.0f
                        : (1.0f - fitted.m[1][1] * (504.0f - old) / 1440.0f -
                           fitted.m[1][3]) *
                              360.0f;
                EXPECT_NEAR(actual[segment][edge], mapped, 0.001f)
                    << "segment " << segment << ", edge " << edge;
            }
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
            // Zoom pivots around the fitted scene center in each viewport.
            const float center = edge % 2 == 0 ? 640.0f : 302.4f;
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
TEST(DonorScene, AutomaticFitContainsFullCycleWithMarkers) {
    AuthoredMeshLibrary library;
    ASSERT_TRUE(lab::load_packaged_meshes(library, LAB_MESH_ASSET_PATH));
    struct Rect {
        float x, y, w, h;
    };
    for (const auto &[width, height] :
         {std::pair{269.0f, 576.0f}, std::pair{720.0f, 350.0f}}) {
        const Rect target{width * 0.1f, 108.0f, width * 0.8f, height - 124.0f};
        for (int view = -1; view <= 4; ++view) {
            ma17::EmulatorSnapshot snapshot;
            lab::SceneCamera camera{0.78f, 0.0f, 0.0f};
            const auto render = [&](lab::RecordingRenderer &frame,
                                    const ma17::EmulatorSnapshot &sample,
                                    lab::SceneCamera candidate,
                                    std::array<lab::ScenePulse, 4> pulses) {
                if (view == -1)
                    lab::render_sevel_scene_donor(frame, sample, width, height,
                                                  {}, {}, candidate, &library,
                                                  pulses);
                else
                    lab::render_sevel_radial_donor(frame, sample, width, height,
                                                   library, {}, {}, candidate,
                                                   pulses, view);
            };
            lab::fit_scene_camera(
                camera, snapshot, width, height, target,
                [&](auto &frame, const auto &sample, auto candidate) {
                    render(frame, sample, candidate, {});
                });
            std::array<lab::ScenePulse, 4> pulses{};
            for (auto &pulse : pulses)
                pulse = {1.0f, false, 1.0f, 1.0f};
            for (int degrees = 0; degrees <= 720; degrees += 5) {
                SCOPED_TRACE(::testing::Message()
                             << width << 'x' << height << " view=" << view
                             << " degrees=" << degrees);
                snapshot.crank_angle_rad =
                    degrees * 3.14159265358979323846 / 180.0;
                lab::RecordingRenderer frame;
                render(frame, snapshot, camera, pulses);
                float left, top, right, bottom;
                ASSERT_TRUE(frame.pixel_bounds(left, top, right, bottom));
                ASSERT_GE(left, target.x - 0.1f);
                ASSERT_GE(top, target.y - 0.1f);
                ASSERT_LE(right, target.x + target.w + 0.1f);
                ASSERT_LE(bottom, target.y + target.h + 0.1f);
            }
        }
    }
}

TEST(DonorScene, FullCycleMeshesStayInsideDefaultViewports) {
    AuthoredMeshLibrary library;
    ASSERT_TRUE(lab::load_packaged_meshes(library, LAB_MESH_ASSET_PATH));
    // Test actual submitted mesh vertices, before rasterizer clipping.
    // Includes narrow/tall and wide/short panes and all selectable sections.
    std::array<float, 4> minimum_margins{1.0f, 1.0f, 1.0f, 1.0f};
    for (const auto &[width, height] :
         {std::pair{180.0f, 240.0f}, std::pair{269.0f, 576.0f},
          std::pair{403.0f, 864.0f}, std::pair{720.0f, 350.0f}}) {
        for (int degrees = 0; degrees <= 720; degrees += 5) {
            ma17::EmulatorSnapshot snapshot;
            snapshot.crank_angle_rad =
                static_cast<double>(degrees) * 3.14159265358979323846 / 180.0;
            std::array<lab::ScenePulse, 4> pulses{};
            for (auto &pulse : pulses)
                pulse = {1.0f, false, 1.0f, 1.0f};
            for (int view = -1; view <= 4; ++view) {
                SCOPED_TRACE(::testing::Message()
                             << width << 'x' << height << " degrees=" << degrees
                             << " view=" << view);
                lab::RecordingRenderer frame;
                const lab::SceneCamera camera{0.78f, 0.0f, 0.0f};
                if (view == -1)
                    lab::render_sevel_scene_donor(frame, snapshot, width,
                                                  height, {}, {}, camera,
                                                  &library, pulses);
                else
                    lab::render_sevel_radial_donor(frame, snapshot, width,
                                                   height, library, {}, {},
                                                   camera, pulses, view);
                float left, top, right, bottom;
                ASSERT_TRUE(frame.pixel_bounds(left, top, right, bottom));
                minimum_margins[0] = std::min(minimum_margins[0], left / width);
                minimum_margins[1] = std::min(minimum_margins[1], top / height);
                minimum_margins[2] =
                    std::min(minimum_margins[2], 1.0f - right / width);
                minimum_margins[3] =
                    std::min(minimum_margins[3], 1.0f - bottom / height);
                ASSERT_GE(left, width * 0.10f);
                ASSERT_GE(top, height * 0.10f);
                ASSERT_LE(right, width * 0.90f);
                ASSERT_LE(bottom, height * 0.90f);
                frame.for_each_triangle([&](const auto &points, const auto &) {
                    for (const auto &point : points) {
                        ASSERT_TRUE(std::isfinite(point.x));
                        ASSERT_TRUE(std::isfinite(point.y));
                    }
                });
            }
        }
    }
    for (std::size_t side = 0; side < minimum_margins.size(); ++side)
        RecordProperty("minimum_margin_" + std::to_string(side),
                       std::to_string(minimum_margins[side]));
}

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

TEST(DonorScene, ImportedPistonKeepsDonorCrownAndSevelBore) {
    AuthoredMeshLibrary library;
    ASSERT_TRUE(lab::load_packaged_meshes(library, LAB_MESH_ASSET_PATH));
    ma17::EmulatorSnapshot snapshot;
    lab::RecordingRenderer renderer;
    lab::render_sevel_radial_donor(renderer, snapshot, 1280.0f, 720.0f, library,
                                   {}, {}, {}, {}, 1);
    Bounds box{std::numeric_limits<float>::max(),
               std::numeric_limits<float>::max(),
               std::numeric_limits<float>::lowest(),
               std::numeric_limits<float>::lowest()};
    renderer.for_each_triangle([&](const auto &points, const ysVector &color) {
        if (std::abs(color.x - 0.94f) > 0.001f ||
            std::abs(color.y - 0.94f) > 0.001f)
            return;
        for (const auto &point : points) {
            box[0] = std::min(box[0], point.x);
            box[1] = std::min(box[1], point.y);
            box[2] = std::max(box[2], point.x);
            box[3] = std::max(box[3], point.y);
        }
    });
    const auto projection =
        lab::scene_fit_projection({}, 1280.0f, 720.0f, 0.14f, 0.34f);
    const float pixels_per_metre = projection.m[0][0] * 640.0f;
    const float crown_y =
        static_cast<float>(lab::cylinder_pose(0.0, 1).piston_pin_y_m) + 0.023f;
    const float expected_top =
        (1.0f - projection.m[1][1] * crown_y - projection.m[1][3]) * 360.0f;
    EXPECT_NEAR(box[2] - box[0], 0.0864f * pixels_per_metre, 0.1f);
    EXPECT_NEAR(box[1], expected_top, 0.1f);
    const auto *piston = library.find("Piston");
    ASSERT_NE(piston, nullptr);
    const auto vertex =
        std::find_if(piston->indices.begin(), piston->indices.end(),
                     [&](unsigned short index) {
                         return piston->vertices[index].Pos.y > 0.5f;
                     });
    ASSERT_NE(vertex, piston->indices.end());
    const auto &local = piston->vertices[*vertex].Pos;
    const float expected_vertex_x =
        640.0f + local.x * 0.0432f * pixels_per_metre;
    const float expected_vertex_y =
        expected_top + local.y * 0.0432f * pixels_per_metre;
    bool found_vertex = false;
    renderer.for_each_triangle([&](const auto &points, const ysVector &color) {
        if (std::abs(color.x - 0.94f) > 0.001f ||
            std::abs(color.y - 0.94f) > 0.001f)
            return;
        for (const auto &point : points)
            found_vertex |= std::abs(point.x - expected_vertex_x) < 0.1f &&
                            std::abs(point.y - expected_vertex_y) < 0.1f;
    });
    EXPECT_TRUE(found_vertex);
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
    shifted_to_tdc.for_each_triangle([&](const auto &points, const auto &) {
        if (first_shifted) {
            shifted_point = {points[0].x, points[0].y};
            first_shifted = false;
        }
    });
    bool first_reference = true;
    reference_tdc.for_each_triangle([&](const auto &points, const auto &) {
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
    const auto projection = lab::scene_fit_projection(
        {}, 1280.0f, 720.0f,
        3.0f * lab::visual_estimate_radial_section_spacing_m + 0.14f, 0.34f);
    const auto screen_x = [&](float x) {
        return (1.0f + projection.m[0][0] * x + projection.m[0][3]) * 640.0f;
    };
    const auto screen_y = [&](float y) {
        return (1.0f - projection.m[1][1] * y - projection.m[1][3]) * 360.0f;
    };
    EXPECT_NEAR(crank_point[0], screen_x(center - radius * crank_local.y),
                0.02f);
    EXPECT_NEAR(crank_point[1], screen_y(radius * crank_local.x), 0.02f);

    const auto first_intake_top = [](const lab::RecordingRenderer &frame) {
        float top = std::numeric_limits<float>::max();
        frame.for_each_triangle([&](const auto &points, const ysVector &color) {
            if (std::abs(color.x - 0.38f) > 0.001f ||
                std::abs(color.y - 0.79f) > 0.001f)
                return;
            for (const auto &point : points)
                if (point.x < 450.0f)
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
    const float dy =
        static_cast<float>(pose.piston_pin_y_m - pose.crank_pin_y_m);
    const float rod_rotation = std::atan2(dx, dy);
    const float world_x = center + dx +
                          radius * (std::cos(rod_rotation) * rod_local.x -
                                    std::sin(rod_rotation) * rod_local.y);
    const float world_y = radius * (std::sin(rod_rotation) * rod_local.x +
                                    std::cos(rod_rotation) * rod_local.y);
    const std::size_t rod_triangle =
        34U + head_faces + 2 * valve_faces + crank_mesh.indices.size() / 3;
    std::array<float, 2> rod_point{};
    triangle = 0;
    quarter_turn.for_each_triangle([&](const auto &points, const auto &) {
        if (triangle++ == rod_triangle)
            rod_point = {points[0].x, points[0].y};
    });
    EXPECT_NEAR(rod_point[0], screen_x(world_x), 0.02f);
    EXPECT_NEAR(rod_point[1], screen_y(world_y), 0.02f);

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
    const auto projection =
        lab::scene_fit_projection({}, 1280.0f, 720.0f, 0.14f, 0.34f);
    EXPECT_NEAR(one[0], (1.0f - projection.m[0][0] * radius * local.y) * 640.0f,
                0.02f);
    EXPECT_NEAR(two[0], (1.0f + projection.m[0][0] * radius * local.y) * 640.0f,
                0.02f);
    EXPECT_NEAR(one[0], four[0], 0.02f);
    EXPECT_NEAR(one[1], four[1], 0.02f);
    lab::RecordingRenderer invalid;
    EXPECT_THROW(lab::render_sevel_radial_donor(invalid, snapshot, 1280.0f,
                                                720.0f, library, {}, {}, {}, {},
                                                5),
                 std::invalid_argument);
}
#endif

} // namespace
