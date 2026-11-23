#include "lab/SevelCadScene.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>

int main(int argc, char **argv) {
    if (argc < 2 || argc > 4) {
        std::cerr << "usage: sevel-cad-check PACKAGE [--compare PACKAGE | --pose DEGREES]\n";
        return 2;
    }
    try {
        const auto scene = lab::load_cad_scene(argv[1]);
        if (argc == 4 && std::string_view(argv[2]) == "--compare") {
            lab::validate_cad_replacement(scene,lab::load_cad_scene(argv[3]));
        } else if (argc == 4 && std::string_view(argv[2]) == "--pose") {
            std::size_t used{};
            const double angle = std::stod(argv[3],&used);
            if (!std::isfinite(angle) || argv[3][used] != '\0') return 2;
            std::cout << "pose " << lab::cad_pose_hash(scene,angle) << '\n' << std::setprecision(10);
            for (const auto &part : scene.parts) {
                const auto pose = lab::cad_pose(scene.rig,part,angle);
                std::cout << part.id;
                for (auto &row : pose.model.m) for (const float n : row) std::cout << ' ' << n;
                std::cout << ' ' << pose.spring_delta << '\n';
            }
        } else if (argc != 2) return 2;
        std::cerr << "valid parts=" << scene.parts.size() << " geometries=" << scene.meshes.size()
                  << " revision=" << scene.revision << '\n';
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
