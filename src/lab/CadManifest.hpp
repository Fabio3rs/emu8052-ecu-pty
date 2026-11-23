#pragma once

#include "lab/MiniJson.hpp"
#include "lab/SevelCadScene.hpp"

#include <array>
#include <cmath>
#include <stdexcept>

namespace lab::cad {

inline void require(bool valid, const std::string &message) {
    if (!valid)
        throw std::runtime_error("CAD: " + message);
}

inline const Json &field(const Json &value, const std::string &key) {
    const auto *member = value.get(key);
    require(member != nullptr, "missing " + key);
    return *member;
}

inline const std::string &string(const Json &v) {
    require(v.is_string() && !v.string.empty(), "invalid string " + v.key);
    return v.string;
}

inline double real(const Json &v) {
    require(v.type == Json::Type::Number && std::isfinite(v.number) &&
            std::abs(v.number) <= 1e9, "invalid number " + v.key);
    return v.number;
}

inline float number(const Json &v) { return static_cast<float>(real(v)); }

template<std::size_t N, class T=float> std::array<T,N> array(const Json &v) {
    require(v.is_array() && v.array.size() == N, "invalid vector " + v.key);
    std::array<T,N> values;
    for (std::size_t i = 0; i < N; ++i)
        values[i] = static_cast<T>(real(v.array[i]));
    return values;
}

inline ysMatrix rest_matrix(const Json &row) {
    const auto [x,y,z,w] = array<4>(field(row, "rest_rotation_xyzw"));
    require(std::abs(x*x+y*y+z*z+w*w-1) < 1e-5f, "invalid quaternion");
    auto matrix = ysMath::LoadIdentity();
    matrix.m[0][0] = 1-2*(y*y+z*z);
    matrix.m[0][1] = 2*(x*y-z*w);
    matrix.m[0][2] = 2*(x*z+y*w);
    matrix.m[1][0] = 2*(x*y+z*w);
    matrix.m[1][1] = 1-2*(x*x+z*z);
    matrix.m[1][2] = 2*(y*z-x*w);
    matrix.m[2][0] = 2*(x*z-y*w);
    matrix.m[2][1] = 2*(y*z+x*w);
    matrix.m[2][2] = 1-2*(x*x+y*y);
    const auto position = array<3>(field(row, "rest_translation_m"));
    for (std::size_t i = 0; i < 3; ++i)
        matrix.m[i][3] = position[i];
    require(array<3>(field(row,"rest_scale")) == std::array{1.f,1.f,1.f}, "unsupported rest scale");
    require(array<3>(field(row,"pivot_local_m")) == std::array{0.f,0.f,0.f}, "unsupported local pivot");
    return matrix;
}

void load_meshes(SevelCadScene &scene, const Json &meshes);
CadRig read_rig(const Json &runtime);
void weight_spring(SevelCadScene &scene, const CadPart &part);
void weight_belt(SevelCadScene &scene, const CadPart &part);
std::string read_asset(const std::filesystem::path &path, std::uintmax_t limit);
std::string digest(const std::string &bytes);

} // namespace lab::cad
