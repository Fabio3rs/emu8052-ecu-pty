#include "ma17/FirmwareLoader.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cstdio>
#include <vector>

namespace ma17 {

bool load_bin_to_code(em8051 *cpu, const char *path, unsigned base) {
    FILE *file = fopen(path, "rb");
    if (!file) {
        perror("fopen");
        return false;
    }

    std::vector<unsigned char> bytes;
    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    fseek(file, 0, SEEK_SET);
    if (length <= 0) {
        fclose(file);
        fprintf(stderr, "ROM vazia?\n");
        return false;
    }
    bytes.resize(static_cast<size_t>(length));
    if (static_cast<long>(fread(bytes.data(), 1, static_cast<size_t>(length),
                                file)) != length) {
        perror("fread");
        fclose(file);
        return false;
    }
    fclose(file);

    for (size_t index = 0; index < bytes.size(); ++index) {
        unsigned address = base + static_cast<unsigned>(index);
        if (address < 0x10000u)
            cpu->mCodeMem[address] = bytes[index];
    }
    fprintf(stderr,
            "[emu8051-pty] ROM carregada: %ld bytes em 0x%04X..0x%04X\n",
            length, base, static_cast<unsigned>(base + length - 1));
    return true;
}

} // namespace ma17
