// Uses the repository's real OBJ loader, transforms and recording renderer.
#include "authored_mesh_library.h"
#include "lab/RecordingRenderer.hpp"
#include <array>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>

struct CadBounds {
    std::array<float, 6> actual{1e9f, 1e9f, 1e9f, -1e9f, -1e9f, -1e9f};
    std::array<float, 6> expected{};
};

void check_pose(const std::string &path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open pose input");
    std::map<std::string, AuthoredMeshLibrary> libraries;
    std::map<std::string, CadBounds> parts;
    lab::RecordingRenderer renderer;
    renderer.beginFrame({0.06f, 0.07f, 0.09f, 1.0f});
    renderer.setSceneViewport(0, 0, 1280, 960);
    const auto identity = ysMath::LoadIdentity();
    auto projection = identity;
    projection.m[0][0] = 3.5f;
    projection.m[1][1] = 3.5f;
    projection.m[0][3] = -0.5f;
    projection.m[1][3] = 0.2f;
    std::string line;
    std::size_t loaded_batches = 0;
    while (std::getline(input, line)) {
        std::istringstream row(line);
        std::string id, file, batch;
        ysVector color{0, 0, 0, 1};
        ysMatrix transform{};
        row >> id >> std::quoted(file) >> batch >> color.x >> color.y >> color.z;
        for (auto &matrix_row : transform.m)
            for (auto &value : matrix_row) row >> value;
        auto &bounds = parts[id];
        for (auto &value : bounds.expected) row >> value;
        bool visible = false;
        if (!(row >> visible)) throw std::runtime_error("malformed pose row");
        std::string trailing;
        if (row >> trailing) throw std::runtime_error("extra fields in pose row");
        if (!libraries.count(file) && !libraries[file].loadAll(file))
            throw std::runtime_error("OBJ loader rejected " + file);
        const auto *mesh = libraries.at(file).find(batch);
        if (!mesh || mesh->indices.size() % 3 != 0)
            throw std::runtime_error("missing or invalid batch");
        ++loaded_batches;
        for (const auto &vertex : mesh->vertices) {
            const auto world = ysMath::MatMult(transform, vertex.Pos);
            const std::array<float, 3> p{world.x, world.y, world.z};
            for (std::size_t i = 0; i < 3; ++i) {
                if (!std::isfinite(p[i])) throw std::runtime_error("nonfinite vertex");
                bounds.actual[i] = std::min(bounds.actual[i], p[i]);
                bounds.actual[i + 3] = std::max(bounds.actual[i + 3], p[i]);
            }
            const auto normal = ysMath::MatMult(transform, vertex.Normal);
            if (std::abs(ysMath::GetScalar(ysMath::Magnitude(normal)) - 1.0f) > 1e-5f)
                throw std::runtime_error("invalid transformed normal: " + id + " length=" +
                    std::to_string(ysMath::GetScalar(ysMath::Magnitude(normal))));
        }
        if (visible) {
            std::vector<unsigned short> front_indices;
            for (std::size_t face = 0; face < mesh->indices.size(); face += 3) {
                std::array<ysVector, 3> p;
                for (std::size_t j = 0; j < 3; ++j)
                    p[j] = ysMath::MatMult(transform, mesh->vertices[mesh->indices[face + j]].Pos);
                const auto n = ysMath::Cross(ysMath::Sub(p[1], p[0]), ysMath::Sub(p[2], p[0]));
                // Orthographic XY camera looks along -Z. Closed back surfaces
                // otherwise cancel front winding inside RecordingRenderer SVG paths.
                if (n.z > 1e-14f)
                    front_indices.insert(front_indices.end(), mesh->indices.begin() + face,
                                         mesh->indices.begin() + face + 3);
            }
            if (front_indices.empty()) continue;
            renderer.set_group(id);
            renderer.uploadGeometry(mesh->vertices.data(), static_cast<int>(mesh->vertices.size()),
                                    front_indices.data(), static_cast<int>(front_indices.size()));
            renderer.submitGeometry(mesh->vertices.data(), front_indices.data(), 0, 0,
                static_cast<int>(front_indices.size() / 3), transform, identity, projection,
                color, Shaders::SceneStage, 0);
        }
    }
    float worst = 0;
    for (const auto &[id, bounds] : parts)
        for (std::size_t i = 0; i < 6; ++i) {
            const float error = std::abs(bounds.actual[i] - bounds.expected[i]);
            if (error > 0.00025f) throw std::runtime_error("CAD bbox mismatch: " + id);
            worst = std::max(worst, error);
        }
    renderer.endFrame();
    if (parts.empty() || !renderer.triangle_count() || !renderer.save_svg(path + ".svg"))
        throw std::runtime_error("empty or unsaved renderer output");
    std::cout << "{\"pose\":" << std::quoted(path) << ",\"status\":\"PASS_RENDERER_POSE_ONLY\","
              << "\"parts\":" << parts.size() << ",\"batches\":" << loaded_batches
              << ",\"max_bbox_error_m\":" << worst
              << ",\"draw_calls\":" << renderer.draw_calls()
              << ",\"rendered_triangles\":" << renderer.triangle_count() << "}\n";
}

int main(int argc, char **argv) {
    try {
        if (argc < 2) throw std::runtime_error("provide CAD pose input paths");
        for (int i = 1; i < argc; ++i) check_pose(argv[i]);
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
