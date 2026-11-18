#include "lab/TraceGeometry.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>
#include <vector>

namespace {

using lab::TraceBatch;
using lab::TracePoint;
using lab::TraceStyle;

// Width of a two-point stroke measured across its direction.
float measured_width(TracePoint a, TracePoint b, float width) {
    const auto batches = lab::build_trace_mesh(std::vector<TracePoint>{a, b},
                                               TraceStyle{width, 4.0f});
    EXPECT_EQ(batches.size(), 1U);
    const float dx = b.x - a.x, dy = b.y - a.y;
    const float length = std::hypot(dx, dy);
    const float nx = -dy / length, ny = dx / length;
    float lo = std::numeric_limits<float>::max(), hi = -lo;
    for (const TracePoint &v : batches[0].vertices) {
        const float across = (v.x - a.x) * nx + (v.y - a.y) * ny;
        lo = std::min(lo, across);
        hi = std::max(hi, across);
    }
    return hi - lo;
}

bool all_finite_and_indexed(const std::vector<TraceBatch> &batches) {
    for (const TraceBatch &batch : batches) {
        for (const TracePoint &v : batch.vertices)
            if (!std::isfinite(v.x) || !std::isfinite(v.y))
                return false;
        for (const std::uint32_t index : batch.indices)
            if (index >= batch.vertices.size())
                return false;
        if (batch.indices.size() % 3U != 0U)
            return false;
    }
    return true;
}

} // namespace

TEST(TraceGeometry, StrokeWidthIsConstantAtEveryDirection) {
    for (const float width : {1.0f, 2.0f, 3.5f}) {
        // 0, 90 and 180 degrees plus a diagonal and its reverse.
        EXPECT_NEAR(measured_width({0, 0}, {10, 0}, width), width,
                    0.1f * width);
        EXPECT_NEAR(measured_width({0, 0}, {0, 10}, width), width,
                    0.1f * width);
        EXPECT_NEAR(measured_width({10, 0}, {0, 0}, width), width,
                    0.1f * width);
        EXPECT_NEAR(measured_width({0, 0}, {7, 7}, width), width, 0.1f * width);
        EXPECT_NEAR(measured_width({7, 7}, {0, 0}, width), width, 0.1f * width);
    }
}

TEST(TraceGeometry, DigitalStepCornerKeepsFullWidth) {
    // ZOH step: right then up. The outer corner must reach half * sqrt(2) from
    // the corner point (a thinned corner would stay near half).
    const float width = 4.0f;
    const auto batches = lab::build_trace_mesh(
        std::vector<TracePoint>{{0, 0}, {10, 0}, {10, 10}},
        TraceStyle{width, 4.0f});
    ASSERT_EQ(batches.size(), 1U);
    // Only the vertices at the corner: the stroke ends are 10 units away.
    float farthest = 0.0f;
    for (const TracePoint &v : batches[0].vertices) {
        const float d = std::hypot(v.x - 10.0f, v.y - 0.0f);
        if (d < 5.0f)
            farthest = std::max(farthest, d);
    }
    EXPECT_NEAR(farthest, 0.5f * width * std::numbers::sqrt2_v<float>, 0.05f);
}

TEST(TraceGeometry, HairpinReversalHasNoSpikeOrBowTie) {
    // Out-and-back peak: a naive miter would extend without bound.
    const float width = 2.0f;
    const auto batches = lab::build_trace_mesh(
        std::vector<TracePoint>{{0, 0}, {10, 0}, {0, 0.001f}},
        TraceStyle{width, 4.0f});
    ASSERT_TRUE(all_finite_and_indexed(batches));
    for (const TraceBatch &batch : batches)
        for (const TracePoint &v : batch.vertices) {
            EXPECT_GE(v.x, -0.5f * width * 4.0f);
            EXPECT_LE(v.x, 10.0f + 0.5f * width * 4.0f);
            EXPECT_LE(std::fabs(v.y), 0.5f * width * 4.0f + 0.01f);
        }
}

TEST(TraceGeometry, SharpCornerAboveLimitIsBeveledNotExtended) {
    // 10 degree turn-back: miter ratio ~ 11 > limit 4.
    const float width = 2.0f;
    const float limit = 4.0f;
    const float angle = 170.0f * std::numbers::pi_v<float> / 180.0f;
    const std::vector<TracePoint> points{
        {0, 0}, {10, 0}, {10 + 10 * std::cos(angle), 10 * std::sin(angle)}};
    const auto batches =
        lab::build_trace_mesh(points, TraceStyle{width, limit});
    ASSERT_TRUE(all_finite_and_indexed(batches));
    // No spike: every vertex stays within half a stroke width of the polyline
    // (a 170-degree miter would reach ~11x half-width past the corner).
    const auto distance_to_segment = [](TracePoint p, TracePoint a,
                                        TracePoint b) {
        const float dx = b.x - a.x, dy = b.y - a.y;
        const float t = std::clamp(((p.x - a.x) * dx + (p.y - a.y) * dy) /
                                       (dx * dx + dy * dy),
                                   0.0f, 1.0f);
        return std::hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
    };
    for (const TraceBatch &batch : batches)
        for (const TracePoint &v : batch.vertices) {
            const float d =
                std::min(distance_to_segment(v, points[0], points[1]),
                         distance_to_segment(v, points[1], points[2]));
            EXPECT_LE(d, 0.5f * width + 1e-3f);
        }
}

TEST(TraceGeometry, RepeatedCollinearAndNonFinitePointsAreSafe) {
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float inf = std::numeric_limits<float>::infinity();
    const std::vector<TracePoint> points{{1, 1},   {1, 1}, {1, 1},
                                         {2, 2},   {3, 3}, {nan, 4},
                                         {5, inf}, {4, 4}, {4, 4}};
    const auto batches = lab::build_trace_mesh(points, TraceStyle{1.0f, 4.0f});
    EXPECT_TRUE(all_finite_and_indexed(batches));
    ASSERT_EQ(batches.size(), 1U);
    // 4 distinct finite points -> 3 segments -> 6 triangles on a straight
    // strip.
    EXPECT_EQ(batches[0].indices.size(), 3U * 6U);

    EXPECT_TRUE(lab::build_trace_mesh({}, {}).empty());
    const auto dot = lab::build_trace_mesh(
        std::vector<TracePoint>{{5, 5}, {5, 5}}, TraceStyle{2.0f, 4.0f});
    ASSERT_EQ(dot.size(), 1U);
    EXPECT_TRUE(all_finite_and_indexed(dot));
    // Invalid style values fall back instead of producing NaN.
    EXPECT_TRUE(all_finite_and_indexed(lab::build_trace_mesh(
        std::vector<TracePoint>{{0, 0}, {1, 1}}, TraceStyle{nan, nan})));
}

TEST(TraceGeometry, LongTracesSplitIntoSeamlessBatchesWithin16BitVertexCount) {
    std::vector<TracePoint> points;
    for (int i = 0; i < 80000; ++i)
        points.push_back({static_cast<float>(i) * 0.01f,
                          (i % 2 == 0) ? 0.0f : 5.0f}); // zig-zag, 80k points
    const auto batches = lab::build_trace_mesh(points, TraceStyle{1.0f, 4.0f});
    ASSERT_GT(batches.size(), 1U);
    ASSERT_TRUE(all_finite_and_indexed(batches));
    std::size_t triangles = 0;
    for (const TraceBatch &batch : batches) {
        EXPECT_LE(batch.vertices.size(), lab::kMaxBatchVertices);
        triangles += batch.indices.size() / 3U;
    }
    // Every segment is covered: at least 2 triangles per segment, no gaps.
    EXPECT_GE(triangles, 2U * (points.size() - 1U));
}
