#include "lab/TraceGeometry.hpp"

#include <algorithm>
#include <cmath>

namespace lab {
namespace {

struct Vec {
    float x = 0.0f;
    float y = 0.0f;
};

class Builder {
  public:
    std::vector<TraceBatch> finish() {
        if (!current_.indices.empty())
            batches_.push_back(std::move(current_));
        return std::move(batches_);
    }

    // Starts a strip with its first left/right pair.
    void begin_strip(const TracePoint &left, const TracePoint &right) {
        has_pair_ = false;
        push_pair(left, right);
    }

    // Extends the current strip by one left/right pair (one quad).
    void push_pair(const TracePoint &left, const TracePoint &right) {
        if (current_.vertices.size() + 2U > kMaxBatchVertices) {
            // Seamless split: the new batch repeats the previous pair.
            const TracePoint last_left = last_left_;
            const TracePoint last_right = last_right_;
            const bool had_pair = has_pair_;
            batches_.push_back(std::move(current_));
            current_ = {};
            if (had_pair)
                add_vertices(last_left, last_right, false);
        }
        add_vertices(left, right, has_pair_);
    }

    void bevel(const TracePoint &a, const TracePoint &b, const TracePoint &c) {
        if (current_.vertices.size() + 3U > kMaxBatchVertices) {
            batches_.push_back(std::move(current_));
            current_ = {};
            has_pair_ = false;
        }
        const auto base = static_cast<std::uint32_t>(current_.vertices.size());
        current_.vertices.push_back(a);
        current_.vertices.push_back(b);
        current_.vertices.push_back(c);
        current_.indices.insert(current_.indices.end(),
                                {base, base + 1U, base + 2U});
        has_pair_ = false; // the strip continues with a fresh pair
    }

  private:
    void add_vertices(const TracePoint &left, const TracePoint &right,
                      bool connect) {
        const auto base = static_cast<std::uint32_t>(current_.vertices.size());
        current_.vertices.push_back(left);
        current_.vertices.push_back(right);
        if (connect) {
            const std::uint32_t pl = base - 2U, pr = base - 1U;
            current_.indices.insert(current_.indices.end(),
                                    {pl, pr, base, pr, base + 1U, base});
        }
        last_left_ = left;
        last_right_ = right;
        has_pair_ = true;
    }

    std::vector<TraceBatch> batches_;
    TraceBatch current_;
    TracePoint last_left_, last_right_;
    bool has_pair_ = false;
};

TracePoint offset(const TracePoint &p, const Vec &n, float scale) {
    return {p.x + n.x * scale, p.y + n.y * scale};
}

} // namespace

std::vector<TraceBatch> build_trace_mesh(std::span<const TracePoint> input,
                                         const TraceStyle &style) {
    const float width =
        std::isfinite(style.width) && style.width > 0.0f ? style.width : 1.0f;
    const float half = 0.5f * width;
    const float limit = std::max(
        1.0f, std::isfinite(style.miter_limit) ? style.miter_limit : 4.0f);

    std::vector<TracePoint> points;
    points.reserve(input.size());
    for (const TracePoint &p : input) {
        if (!std::isfinite(p.x) || !std::isfinite(p.y))
            continue;
        if (!points.empty() && points.back().x == p.x && points.back().y == p.y)
            continue;
        points.push_back(p);
    }
    Builder builder;
    if (points.empty())
        return builder.finish();
    if (points.size() == 1) {
        const TracePoint &p = points[0];
        builder.begin_strip({p.x - half, p.y - half}, {p.x + half, p.y - half});
        builder.push_pair({p.x - half, p.y + half}, {p.x + half, p.y + half});
        return builder.finish();
    }

    const std::size_t segments = points.size() - 1U;
    std::vector<Vec> direction(segments), normal(segments);
    for (std::size_t i = 0; i < segments; ++i) {
        const float dx = points[i + 1U].x - points[i].x;
        const float dy = points[i + 1U].y - points[i].y;
        const float length = std::hypot(dx, dy);
        direction[i] = {dx / length, dy / length};
        normal[i] = {-direction[i].y, direction[i].x};
    }

    builder.begin_strip(offset(points[0], normal[0], half),
                        offset(points[0], normal[0], -half));
    for (std::size_t i = 1; i < points.size() - 1U; ++i) {
        const TracePoint &p = points[i];
        const Vec &n0 = normal[i - 1U];
        const Vec &n1 = normal[i];
        const Vec m{n0.x + n1.x, n0.y + n1.y};
        const float m_length = std::hypot(m.x, m.y);
        const float cos_half =
            0.5f * m_length; // cos(theta / 2), |n0| = |n1| = 1
        if (cos_half >= 1.0f / limit) {
            // half / cos(theta/2) along the normalized miter direction.
            const float scale = half / (cos_half * m_length);
            builder.push_pair(offset(p, m, scale), offset(p, m, -scale));
            continue;
        }
        // Sharp corner: close the strip with a butt end, bevel the outer side,
        // and restart so no spike or bow-tie is produced.
        builder.push_pair(offset(p, n0, half), offset(p, n0, -half));
        const float turn = direction[i - 1U].x * direction[i].y -
                           direction[i - 1U].y * direction[i].x;
        if (turn != 0.0f) {
            const float outer = turn > 0.0f ? -half : half;
            builder.bevel(p, offset(p, n0, outer), offset(p, n1, outer));
        }
        builder.begin_strip(offset(p, n1, half), offset(p, n1, -half));
    }
    const std::size_t last = points.size() - 1U;
    builder.push_pair(offset(points[last], normal[segments - 1U], half),
                      offset(points[last], normal[segments - 1U], -half));
    return builder.finish();
}

} // namespace lab
