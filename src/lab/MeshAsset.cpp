#include "lab/MeshAsset.hpp"

#include <zlib.h>

#include <cctype>
#include <fstream>
#include <iterator>
#include <sstream>
#include <vector>

namespace lab {

std::vector<unsigned char> decode_packaged_bytes(const std::string &path,
                                                 std::size_t expected_size) {
    std::ifstream input(path);
    if (!input)
        return {};
    const std::string encoded(std::istreambuf_iterator<char>{input}, {});
    std::vector<unsigned char> compressed;
    compressed.reserve(encoded.size() * 3 / 4);
    unsigned int quartet = 0;
    int bits = 0;
    bool padding = false;
    for (char encoded_character : encoded) {
        const auto character = static_cast<unsigned char>(encoded_character);
        if (std::isspace(character))
            continue;
        if (character == '=') {
            padding = true;
            continue;
        }
        if (padding)
            return {};
        unsigned int digit = 0;
        if (character >= 'A' && character <= 'Z')
            digit = character - 'A';
        else if (character >= 'a' && character <= 'z')
            digit = character - 'a' + 26;
        else if (character >= '0' && character <= '9')
            digit = character - '0' + 52;
        else if (character == '+')
            digit = 62;
        else if (character == '/')
            digit = 63;
        else
            return {};
        quartet = (quartet << 6) | digit;
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            compressed.push_back(
                static_cast<unsigned char>((quartet >> bits) & 0xff));
        }
    }
    if (compressed.empty() || encoded.empty() || bits >= 6)
        return {};
    std::vector<unsigned char> obj(expected_size);
    uLongf decoded_size = obj.size();
    if (uncompress(obj.data(), &decoded_size, compressed.data(),
                   static_cast<uLong>(compressed.size())) != Z_OK ||
        decoded_size != expected_size)
        return {};
    return obj;
}

bool load_packaged_meshes(AuthoredMeshLibrary &library,
                          const std::string &path) {
    const auto obj = decode_packaged_bytes(path, 918973);
    if (obj.empty())
        return false;
    std::istringstream mesh_input(
        std::string(reinterpret_cast<const char *>(obj.data()), obj.size()));
    return library.load(mesh_input);
}

} // namespace lab
