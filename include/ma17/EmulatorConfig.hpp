#pragma once

#include <optional>

namespace ma17 {

struct EmulatorConfig {
    const char *rom_path;
    int crank_rpm = 1000;
    bool crank_immediate = false;
};

std::optional<EmulatorConfig> parse_emulator_config(int argc, char **argv);

} // namespace ma17
