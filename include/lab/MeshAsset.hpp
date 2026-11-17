#pragma once

#include "authored_mesh_library.h"

#include <cstddef>
#include <string>
#include <vector>

namespace lab {

std::vector<unsigned char> decode_packaged_bytes(const std::string &path,
                                                 std::size_t expected_size);
bool load_packaged_meshes(AuthoredMeshLibrary &library,
                          const std::string &path);

} // namespace lab
