#include "CadManifest.hpp"
#include "authored_mesh_library.h"
#include "lab/RunSnapshot.hpp"

#include <fstream>
#include <set>
#include <sstream>
#ifdef SEVEL_CAD_OPENSSL
#include <openssl/evp.h>
#endif

namespace lab::cad {

std::string read_asset(const std::filesystem::path &path, std::uintmax_t limit) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    require(input.good(), "cannot open " + path.string());
    const auto size = input.tellg();
    require(size > 0 && static_cast<std::uintmax_t>(size) <= limit, "file size " + path.string());
    std::string bytes(static_cast<std::size_t>(size), '\0');
    input.seekg(0);
    require(static_cast<bool>(input.read(bytes.data(), size)), "cannot read " + path.string());
    return bytes;
}

std::string digest(const std::string &bytes) {
#ifdef SEVEL_CAD_OPENSSL
    unsigned char hash[EVP_MAX_MD_SIZE];
    unsigned length{};
    require(EVP_Digest(bytes.data(),bytes.size(),hash,&length,EVP_sha256(),nullptr) && length == 32,
            "SHA-256 unavailable");
    constexpr char hex[] = "0123456789abcdef";
    std::string result(64,'0');
    for (unsigned i=0; i<length; ++i) {
        result[2*i] = hex[hash[i]>>4];
        result[2*i+1] = hex[hash[i]&15];
    }
    return result;
#else
    return sha256_hex({bytes.begin(), bytes.end()});
#endif
}

void load_meshes(SevelCadScene &scene, const Json &meshes) {
    require(meshes.is_object() && !meshes.object.empty() && meshes.object.size() <= 4096, "mesh count");
    const auto root = scene.manifest_path.parent_path();
    std::uintmax_t total = 0;
    for (const auto &mesh : meshes.object) {
        const auto &name = string(field(mesh, "file"));
        const auto &hash = string(field(mesh, "sha256"));
        const auto path = std::filesystem::canonical(root / name);
        require(path.parent_path() == root && std::filesystem::path(name).filename() == name,
                "mesh outside package: " + name);
        require(hash.size() == 64 && mesh.key == "mesh_" + hash.substr(0,20), "mesh ID " + name);
        total += std::filesystem::file_size(path);
        require(total <= 512u*1024*1024, "package exceeds 512 MiB");
        auto bytes = read_asset(path, 96u*1024*1024);
        require(digest(bytes) == hash, "SHA-256 mismatch: " + name);
        std::istringstream input(std::move(bytes));
        AuthoredMeshLibrary library;
        require(library.loadSolid(input), "invalid closed OBJ, winding or indices: " + name);
        require(static_cast<double>(library.positionCount()) == real(field(mesh,"vertices")), "vertex count " + name);
        auto [entry, inserted] = scene.meshes.try_emplace(mesh.key);
        require(inserted, "duplicate mesh " + mesh.key);
        const auto &batches = field(mesh, "batches");
        require(batches.is_array() && batches.array.size() == library.size(), "batch count " + name);
        std::size_t triangles = 0;
        ysVector lower{10,10,10}, upper{-10,-10,-10};
        std::set<std::string> seen;
        for (const auto &item : batches.array) {
            const auto &batch = string(item);
            const auto *data = library.find(batch);
            require(data && seen.insert(batch).second, "invalid batch " + batch);
            for (const auto &v : data->vertices) {
                const auto &p = v.Pos;
                const auto &n = v.Normal;
                require(std::abs(p.x) < 10 && std::abs(p.y) < 10 && std::abs(p.z) < 10 &&
                        std::abs(n.x*n.x+n.y*n.y+n.z*n.z-1) < 0.001f, "invalid vertex " + name);
                lower = {std::min(p.x,lower.x),std::min(p.y,lower.y),std::min(p.z,lower.z)};
                upper = {std::max(p.x,upper.x),std::max(p.y,upper.y),std::max(p.z,upper.z)};
            }
            const auto faces = data->indices.size()/3;
            triangles += faces;
            require(scene.vertices.size()+data->vertices.size() < 5000000 &&
                    scene.indices.size()+data->indices.size() < 18000000, "geometry budget");
            entry->second.push_back({static_cast<int>(scene.vertices.size()), static_cast<int>(scene.indices.size()),
                                     static_cast<int>(faces), batch});
            scene.vertices.insert(scene.vertices.end(), data->vertices.begin(), data->vertices.end());
            scene.indices.insert(scene.indices.end(), data->indices.begin(), data->indices.end());
        }
        require(static_cast<double>(triangles) == field(mesh,"triangles").number, "triangle count " + name);
        scene.mesh_bounds.emplace(mesh.key,std::pair{lower,upper});
    }
}

} // namespace lab::cad
