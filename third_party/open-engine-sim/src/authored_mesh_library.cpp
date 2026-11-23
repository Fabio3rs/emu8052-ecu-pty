#include "../include/authored_mesh_library.h"

#include <cstdint>
#include <charconv>
#include <cmath>
#include <algorithm>
#include <array>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <string_view>
#include <unordered_map>

namespace {
struct Vec3 { float x, y, z; };

bool required(const std::string &name) {
    return name == "Piston" || name == "ConnectingRod" || name == "CylinderHead"
        || name == "Crankshaft" || name == "CrankSnout" || name == "CrankSnoutThreads"
        || name == "Valve" || name == "Logo";
}

bool parseIndex(const std::string &token, unsigned int *position, unsigned int *normal) {
    const std::size_t separator = token.find("//");
    if (separator == std::string::npos) return false;
    const long parsedPosition = std::strtol(token.substr(0, separator).c_str(), nullptr, 10);
    const long parsedNormal = std::strtol(token.substr(separator + 2).c_str(), nullptr, 10);
    if (parsedPosition <= 0 || parsedNormal <= 0) return false;
    *position = static_cast<unsigned int>(parsedPosition - 1);
    *normal = static_cast<unsigned int>(parsedNormal - 1);
    return true;
}
}

bool AuthoredMeshLibrary::load(const std::string &path) {
    std::ifstream file(path);
    if (!file) return false;
    return load(file);
}

bool AuthoredMeshLibrary::load(std::istream &input) {
    return loadImpl(input, false);
}

bool AuthoredMeshLibrary::loadAll(const std::string &path) {
    std::ifstream file(path);
    if (!file) return false;
    return loadAll(file);
}

bool AuthoredMeshLibrary::loadAll(std::istream &input) {
    return loadImpl(input,true);
}

bool AuthoredMeshLibrary::loadSolid(std::istream &input) {
    // The versioned CAD OBJ dialect contains triangular position//normal
    // faces. Avoid allocating streams and strings for millions of corners.
    m_meshes.clear();
    std::vector<Vec3> positions, normals;
    std::unordered_map<std::uint64_t,unsigned short> corners;
    Mesh *batch = nullptr;
    std::vector<std::uint64_t> edges;
    double signedVolume = 0;
    std::string line;
    auto token = [](std::string_view &remaining) {
        auto first = remaining.find_first_not_of(" \t\r");
        if (first == remaining.npos) { remaining = {}; return std::string_view{}; }
        remaining.remove_prefix(first);
        auto end = remaining.find_first_of(" \t\r");
        auto word = remaining.substr(0,end);
        remaining.remove_prefix(word.size());
        return word;
    };
    auto value = [](std::string_view text, auto &out) {
        if (text.empty()) return false;
        auto result = std::from_chars(text.data(),text.data()+text.size(),out);
        return result.ec == std::errc{} && result.ptr == text.data()+text.size();
    };
    while (std::getline(input,line)) {
        std::string_view rest(line);
        const auto kind = token(rest);
        if (kind.empty() || kind.front() == '#') continue;
        if (kind == "v" || kind == "vn") {
            Vec3 p{};
            if (!value(token(rest),p.x) || !value(token(rest),p.y) || !value(token(rest),p.z) ||
                !std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) return false;
            (kind == "v" ? positions : normals).push_back(p);
        } else if (kind == "o") {
            const auto name = token(rest);
            if (name.empty()) return false;
            auto [it,inserted] = m_meshes.try_emplace(std::string(name));
            if (!inserted) return false;
            batch = &it->second;
            corners.clear();
        } else if (kind == "f" && batch) {
            std::array<unsigned,3> pos{}, norm{};
            for (int i=0; i<3; ++i) {
                auto pair = token(rest);
                const auto sep = pair.find("//");
                unsigned vi{}, ni{};
                if (sep == pair.npos || !value(pair.substr(0,sep),vi) || !value(pair.substr(sep+2),ni) ||
                    vi == 0 || vi > positions.size() || ni == 0 || ni > normals.size()) return false;
                const auto key = (static_cast<std::uint64_t>(vi)<<32) | ni;
                auto [it,inserted] = corners.try_emplace(key,static_cast<unsigned short>(batch->vertices.size()));
                if (inserted) {
                    if (batch->vertices.size() >= 65536) return false;
                    const auto &p = positions[vi-1], &n = normals[ni-1];
                    batch->vertices.push_back({{p.x,p.y,p.z,1},{n.x,n.y,n.z,0},{}});
                }
                batch->indices.push_back(it->second);
                pos[static_cast<std::size_t>(i)] = vi-1;
                norm[static_cast<std::size_t>(i)] = ni-1;
            }
            {
                const auto &a = positions[pos[0]], &b = positions[pos[1]], &c = positions[pos[2]];
                const auto ux = b.x-a.x, uy = b.y-a.y, uz = b.z-a.z;
                const auto vx = c.x-a.x, vy = c.y-a.y, vz = c.z-a.z;
                const auto nx = uy*vz-uz*vy, ny = uz*vx-ux*vz, nz = ux*vy-uy*vx;
                const auto mag = std::hypot(nx,ny,nz);
                if (mag == 0) return false;
                for (auto n : norm) {
                    const auto &v = normals[n];
                    if (nx*v.x+ny*v.y+nz*v.z < .80f*mag) return false;
                }
                signedVolume += static_cast<double>(nx*a.x+ny*a.y+nz*a.z);
                for (std::size_t k=0; k<3; ++k) {
                    auto x = pos[k], y = pos[(k+1)%3];
                    const auto edge = (static_cast<std::uint64_t>(std::min(x,y))<<32)|std::max(x,y);
                    edges.push_back((edge<<1) | static_cast<unsigned>(x>y));
                }
            }
        } else return false;
        if (!token(rest).empty()) return false;
    }
    if (m_meshes.empty()) return false;
    if (signedVolume <= 0 || edges.size()%2) return false;
    std::sort(edges.begin(),edges.end());
    for (std::size_t i=0; i<edges.size(); i+=2) {
        if ((edges[i]^1) != edges[i+1] || (i && edges[i-1]/2 == edges[i]/2)) return false;
    }
    m_positions = positions.size();
    for (const auto &entry : m_meshes) if (entry.second.indices.empty()) return false;
    return true;
}

bool AuthoredMeshLibrary::loadImpl(std::istream &input, bool allObjects) {
    m_meshes.clear();
    std::vector<Vec3> positions;
    std::vector<Vec3> normals;
    Mesh *currentMesh = nullptr;
    std::unordered_map<std::uint64_t, unsigned short> vertexIndices;
    std::string line;

    while (std::getline(input, line)) {
        std::istringstream stream(line);
        std::string kind;
        stream >> kind;
        if (kind == "v") {
            Vec3 position = {};
            if (!(stream >> position.x >> position.y >> position.z)) return false;
            positions.push_back(position);
        }
        else if (kind == "vn") {
            Vec3 normal = {};
            if (!(stream >> normal.x >> normal.y >> normal.z)) return false;
            normals.push_back(normal);
        }
        else if (kind == "o") {
            std::string name;
            if (!(stream >> name)) return false;
            currentMesh = nullptr;
            vertexIndices.clear();
            if (allObjects || required(name)) {
                if (allObjects && m_meshes.count(name)) return false;
                currentMesh = &m_meshes[name];
            }
        }
        else if (kind == "f") {
            if (currentMesh == nullptr) continue;
            std::string token;
            unsigned int position = 0;
            unsigned int normal = 0;
            int corners = 0;
            while (stream >> token) {
                if (!parseIndex(token, &position, &normal) || position >= positions.size() || normal >= normals.size()) return false;
                const std::uint64_t key = (static_cast<std::uint64_t>(position) << 32) | normal;
                const auto existing = vertexIndices.find(key);
                if (existing != vertexIndices.end()) {
                    currentMesh->indices.push_back(existing->second);
                }
                else {
                    if (currentMesh->vertices.size() > 65535) return false;
                    const unsigned short index = static_cast<unsigned short>(currentMesh->vertices.size());
                    const Vec3 &p = positions[position];
                    const Vec3 &n = normals[normal];
                    currentMesh->vertices.push_back({ { p.x, p.y, p.z, 1 }, { n.x, n.y, n.z, 0 }, {} });
                    currentMesh->indices.push_back(index);
                    vertexIndices.emplace(key, index);
                }
                ++corners;
            }
            if (corners != 3) return false;
        }
    }

    if (allObjects) {
        if (m_meshes.empty()) return false;
        for (const auto &entry : m_meshes) {
            if (entry.second.vertices.empty() || entry.second.indices.empty()) return false;
        }
        return true;
    }
    return find("Piston") != nullptr && find("ConnectingRod") != nullptr
        && find("CylinderHead") != nullptr && find("Crankshaft") != nullptr
        && find("CrankSnout") != nullptr && find("CrankSnoutThreads") != nullptr
        && find("Valve") != nullptr && find("Logo") != nullptr;
}

const AuthoredMeshLibrary::Mesh *AuthoredMeshLibrary::find(const std::string &name) const {
    const auto found = m_meshes.find(name);
    return found == m_meshes.end() ? nullptr : &found->second;
}
