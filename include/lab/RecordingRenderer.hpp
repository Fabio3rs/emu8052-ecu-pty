#pragma once

#include "renderer.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>
#include <vector>

namespace lab {

class RecordingRenderer final : public Renderer {
  public:
    void beginFrame(const ysVector &clear_color) override {
        clear_color_ = clear_color;
        triangles_.clear();
        draw_calls_ = 0;
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
                        std::uint32_t, int) override {
        if (base_vertex < 0 || base_index < 0 || face_count < 0)
            throw std::out_of_range("recorded draw indices");
        const auto start = static_cast<std::size_t>(base_index);
        const auto count = static_cast<std::size_t>(face_count);
        if (start > indices_.size() || count > (indices_.size() - start) / 3)
            throw std::out_of_range("recorded draw indices");
        ++draw_calls_;
        for (int face = 0; face < face_count; ++face) {
            Triangle triangle;
            triangle.color = color;
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

    int draw_calls() const { return draw_calls_; }
    std::size_t triangle_count() const { return triangles_.size(); }

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
        for (const auto &triangle : triangles_) {
            out << "<polygon points=\"";
            for (const auto &point : triangle.points)
                out << point.x << ',' << point.y << ' ';
            out << "\" fill=\"" << color_hex(triangle.color) << "\"/>\n";
        }
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
    };

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
    ysVector clear_color_{};
    std::vector<EngineSimVertex> vertices_;
    std::vector<std::uint16_t> indices_;
    std::vector<Triangle> triangles_;
};

} // namespace lab
