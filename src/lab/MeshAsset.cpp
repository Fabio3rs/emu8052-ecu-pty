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
    std::vector<unsigned char> obj;
    std::ifstream input(path);
    if (!input)
        return obj;
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
            return obj;
        unsigned int digit = 0;
        if (character >= 'A' && character <= 'Z')
            digit = static_cast<unsigned int>(character - 'A');
        else if (character >= 'a' && character <= 'z')
            digit = static_cast<unsigned int>(character - 'a' + 26);
        else if (character >= '0' && character <= '9')
            digit = static_cast<unsigned int>(character - '0' + 52);
        else if (character == '+')
            digit = 62;
        else if (character == '/')
            digit = 63;
        else
            return obj;
        quartet = (quartet << 6) | digit;
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            compressed.push_back(
                static_cast<unsigned char>((quartet >> bits) & 0xff));
        }
    }
    if (compressed.empty() || encoded.empty() || bits >= 6)
        return obj;
    if (expected_size == 0) {
        // Unknown size: grow until the stream fits (bounded at 64 MiB).
        constexpr std::size_t kMaxBytes = 64U * 1024U * 1024U;
        std::size_t capacity = compressed.size() * 4U + 4096U;
        while (capacity <= kMaxBytes) {
            obj.resize(capacity);
            uLongf size = obj.size();
            const int status =
                uncompress(obj.data(), &size, compressed.data(),
                           static_cast<uLong>(compressed.size()));
            if (status == Z_OK) {
                obj.resize(size);
                return obj;
            }
            if (status != Z_BUF_ERROR)
                break;
            capacity *= 2U;
        }
        obj.clear();
        return obj;
    }
    obj.resize(expected_size);
    uLongf decoded_size = obj.size();
    if (uncompress(obj.data(), &decoded_size, compressed.data(),
                   static_cast<uLong>(compressed.size())) != Z_OK ||
        decoded_size != expected_size) {
        obj.clear();
        return obj;
    }
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
