#pragma once

#include <cstdint>
#include <span>
#include <vector>

namespace lab {

struct TracePoint {
    float x = 0.0f;
    float y = 0.0f;
};

struct TraceStyle {
    // Constant stroke width in the caller's units (>= 1 device pixel is the
    // caller's responsibility: pass max(width, 1 / device_scale)).
    float width = 1.0f;
    // Miter length / half-width ratio above which a corner is beveled.
    float miter_limit = 4.0f;
};

// One drawable mesh. Indices are 32-bit but every batch holds at most
// kMaxBatchVertices vertices so it also fits 16-bit index GPU paths.
struct TraceBatch {
    std::vector<TracePoint> vertices;
    std::vector<std::uint32_t> indices;
};

inline constexpr std::size_t kMaxBatchVertices = 65532;

// Builds a constant-width polyline: joins use a miter scaled by 1/cos(theta/2),
// corners sharper than the miter limit (including hairpin reversals) are
// beveled with detached segment ends instead of extending a spike. Non-finite
// points and repeated points are dropped; a single point yields a width x
// width square so it stays visible. Never produces NaN vertices.
std::vector<TraceBatch> build_trace_mesh(std::span<const TracePoint> points,
                                         const TraceStyle &style);

} // namespace lab
