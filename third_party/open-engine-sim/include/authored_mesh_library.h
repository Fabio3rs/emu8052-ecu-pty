#ifndef ATG_ENGINE_SIM_AUTHORED_MESH_LIBRARY_H
#define ATG_ENGINE_SIM_AUTHORED_MESH_LIBRARY_H

#include "render_math.h"

#include <iosfwd>
#include <string>
#include <unordered_map>
#include <vector>

// Loads the portable OBJ exported from art/assets.blend.
class AuthoredMeshLibrary {
public:
    struct Mesh {
        std::vector<EngineSimVertex> vertices;
        std::vector<unsigned short> indices;
    };

    bool load(const std::string &path);
    bool load(std::istream &input);
    // CAD exports use stable component/batch names instead of the donor set.
    bool loadAll(const std::string &path);
    bool loadAll(std::istream &input);
    const Mesh *find(const std::string &name) const;

private:
    bool loadImpl(std::istream &input, bool allObjects);
    std::unordered_map<std::string, Mesh> m_meshes;
};

#endif
