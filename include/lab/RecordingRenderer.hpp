#pragma once

#include "renderer.h"
#include "shaders.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace lab {

class RecordingRenderer final : public Renderer {
  public:
    // M-groups: draw calls submitted after set_group("cyl1-piston") belong to
    // that group; save_svg wraps them in <g id="...">. An empty id means "no
    // group". The id is a plain token, sanitised on output.
    void set_group(const std::string &id) {
        if (id.empty()) {
            current_group_ = -1;
            return;
        }
        const auto found = std::find(groups_.begin(), groups_.end(), id);
        if (found == groups_.end()) {
            groups_.push_back(id);
            current_group_ = static_cast<int>(groups_.size()) - 1;
        } else {
            current_group_ = static_cast<int>(found - groups_.begin());
        }
    }

    void beginFrame(const ysVector &clear_color) override {
        clear_color_ = clear_color;
        groups_.clear();
        current_group_ = -1;
        triangles_.clear();
        draw_calls_ = 0;
        scene_draw_calls_ = 0;
    }

    void setSceneViewport(float, float, float width, float height) override {
        width_ = width;
        height_ = height;
    }

    void uploadGeometry(const EngineSimVertex *vertices, int vertex_count,
                        const std::uint16_t *indices,
                        int index_count) override {
        vertices_.assign(vertices, vertices + vertex_count);
        indices_.assign(indices, indices + index_count);
    }

    void submitGeometry(const EngineSimVertex *, const std::uint16_t *,
                        int base_vertex, int base_index, int face_count,
                        const ysMatrix &transform, const ysMatrix &camera_view,
                        const ysMatrix &projection, const ysVector &color,
                        std::uint32_t stage, int) override {
        if (base_vertex < 0 || base_index < 0 || face_count < 0)
            throw std::out_of_range("recorded draw indices");
        const auto start = static_cast<std::size_t>(base_index);
        const auto count = static_cast<std::size_t>(face_count);
        if (start > indices_.size() || count > (indices_.size() - start) / 3)
            throw std::out_of_range("recorded draw indices");
        ++draw_calls_;
        if ((stage & Shaders::SceneStage) != 0)
            ++scene_draw_calls_;
        for (int face = 0; face < face_count; ++face) {
            Triangle triangle;
            triangle.color = color;
            triangle.call = draw_calls_;
            triangle.group = current_group_;
            for (int corner = 0; corner < 3; ++corner) {
                const auto offset = start + static_cast<std::size_t>(face) * 3 +
                                    static_cast<std::size_t>(corner);
                const auto vertex_index =
                    static_cast<std::size_t>(base_vertex) + indices_[offset];
                if (vertex_index >= vertices_.size())
                    throw std::out_of_range("recorded vertex index");
                const ysVector world =
                    ysMath::MatMult(transform, vertices_[vertex_index].Pos);
                const ysVector eye = ysMath::MatMult(camera_view, world);
                const ysVector clip = ysMath::MatMult(projection, eye);
                triangle.points[static_cast<std::size_t>(corner)] = {
                    (clip.x / clip.w + 1.0f) * width_ / 2.0f,
                    (1.0f - clip.y / clip.w) * height_ / 2.0f};
            }
            triangles_.push_back(triangle);
        }
    }

    void endFrame() override {}

    const ysVector &clear_color() const { return clear_color_; }
    int draw_calls() const { return draw_calls_; }
    int scene_draw_calls() const { return scene_draw_calls_; }
    std::size_t triangle_count() const { return triangles_.size(); }
    // Draw calls that emitted at least one triangle (one SVG path each).
    std::size_t drawn_call_count() const {
        std::size_t groups = 0;
        int previous = 0;
        for (const auto &triangle : triangles_) {
            if (triangle.call != previous)
                ++groups;
            previous = triangle.call;
        }
        return groups;
    }

    bool pixel_bounds(float &min_x, float &min_y, float &max_x,
                      float &max_y) const {
        if (triangles_.empty())
            return false;
        min_x = min_y = std::numeric_limits<float>::max();
        max_x = max_y = std::numeric_limits<float>::lowest();
        for (const auto &triangle : triangles_)
            for (const auto &point : triangle.points) {
                min_x = std::min(min_x, point.x);
                min_y = std::min(min_y, point.y);
                max_x = std::max(max_x, point.x);
                max_y = std::max(max_y, point.y);
            }
        return true;
    }

    template <typename Visitor> void for_each_triangle(Visitor &&visit) const {
        for (const auto &triangle : triangles_)
            visit(triangle.points, triangle.color);
    }

    bool save_svg(const std::string &path) const {
        std::ofstream out(path);
        if (!out || width_ <= 0.0f || height_ <= 0.0f)
            return false;
        out << "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" << width_
            << "\" height=\"" << height_ << "\" viewBox=\"0 0 " << width_ << ' '
            << height_ << "\">\n";
        out << "<rect width=\"100%\" height=\"100%\" fill=\""
            << color_hex(clear_color_) << "\"/>\n";
        out << std::fixed << std::setprecision(2);
        // One <path> per draw call: all its triangles are subpaths of a single
        // fill, so abutting triangles raster as one shape (no seams) and a
        // translucent call is blended once. Opaque calls also disable
        // anti-aliasing at shared edges (crispEdges); translucent ones keep it.
        std::size_t index = 0;
        int open_group = -1;
        while (index < triangles_.size()) {
            const Triangle &first = triangles_[index];
            if (first.group != open_group) {
                if (open_group >= 0)
                    out << "</g>\n";
                if (first.group >= 0)
                    out << "<g id=\""
                        << svg_id(groups_[static_cast<std::size_t>(first.group)])
                        << "\">\n";
                open_group = first.group;
            }
            const float alpha = std::clamp(first.color.w, 0.0f, 1.0f);
            out << "<path d=\"";
            for (; index < triangles_.size() &&
                   triangles_[index].call == first.call;
                 ++index) {
                const auto &points = triangles_[index].points;
                out << 'M' << points[0].x << ',' << points[0].y << 'L'
                    << points[1].x << ',' << points[1].y << 'L' << points[2].x
                    << ',' << points[2].y << 'Z';
            }
            out << "\" fill=\"" << color_hex(first.color) << '"';
            if (alpha < 1.0f)
                out << " fill-opacity=\"" << alpha << '"';
            else
                out << " shape-rendering=\"crispEdges\"";
            out << "/>\n";
        }
        if (open_group >= 0)
            out << "</g>\n";
        out << "</svg>\n";
        return static_cast<bool>(out);
    }

  private:
    struct Point {
        float x;
        float y;
    };
    struct Triangle {
        std::array<Point, 3> points{};
        ysVector color{};
        int call = 0; // 1-based draw call that emitted this triangle
        int group = -1; // index into groups_, -1 for none
    };

    // Keep only [A-Za-z0-9_-] so an id can never break the XML.
    static std::string svg_id(const std::string &text) {
        std::string id;
        for (const char c : text)
            id += (std::isalnum(static_cast<unsigned char>(c)) || c == '-' ||
                   c == '_')
                      ? c
                      : '_';
        return id;
    }

    static std::string color_hex(const ysVector &color) {
        constexpr char hex[] = "0123456789ABCDEF";
        std::string text = "#000000";
        const std::array<float, 3> channels{color.x, color.y, color.z};
        for (std::size_t index = 0; index < channels.size(); ++index) {
            const int value = static_cast<int>(
                std::clamp(channels[index], 0.0f, 1.0f) * 255.0f);
            text[1 + index * 2] = hex[value >> 4];
            text[2 + index * 2] = hex[value & 0x0f];
        }
        return text;
    }

    float width_ = 0.0f;
    float height_ = 0.0f;
    int draw_calls_ = 0;
    int scene_draw_calls_ = 0;
    ysVector clear_color_{};
    std::vector<EngineSimVertex> vertices_;
    std::vector<std::uint16_t> indices_;
    std::vector<Triangle> triangles_;
    std::vector<std::string> groups_;
    int current_group_ = -1;
};

} // namespace lab
