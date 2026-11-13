#include "ma17/EmulatorConfig.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>

namespace ma17 {

std::optional<EmulatorConfig> parse_emulator_config(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Uso: %s <rom.bin> [--8052]\n", argv[0]);
        return std::nullopt;
    }

    EmulatorConfig config{argv[1]};
    // Size rejects the known 64 KiB Renault dump; it cannot identify another
    // 32 KiB image. The override still runs the Fiat clock and port model.
    fprintf(stderr,
            "[PROFILE] Fiat MA1.7/C517A harness: 11.88 MHz, P4 K-line, "
            "P1.0 crank input; verify hardware before using another ROM\n");
    std::error_code rom_size_error;
    const auto rom_size =
        std::filesystem::file_size(config.rom_path, rom_size_error);
    if (!rom_size_error && rom_size != 32768) {
        fprintf(stderr,
                "[PROFILE] ROM has %llu bytes (Fiat reference: 32768); "
                "clock and port stimuli are unverified for this image\n",
                static_cast<unsigned long long>(rom_size));
        const char *foreign_override = std::getenv("MA17_ALLOW_FOREIGN_ROM");
        if (!foreign_override || strcmp(foreign_override, "1") != 0) {
            fprintf(stderr,
                    "[PROFILE] Refusing Fiat hardware emulation for this ROM; "
                    "set MA17_ALLOW_FOREIGN_ROM=1 for experimental use\n");
            return std::nullopt;
        }
        fprintf(
            stderr,
            "[PROFILE] Experimental Fiat hardware profile override enabled\n");
    }

    if (const char *setting = std::getenv("MA17_CRANK_RPM")) {
        char *end = nullptr;
        const long rpm = std::strtol(setting, &end, 10);
        if (*setting && *end == '\0' && rpm >= 300 && rpm <= 6000)
            config.crank_rpm = static_cast<int>(rpm);
        else
            fprintf(stderr,
                    "[CRANKSHAFT] invalid MA17_CRANK_RPM=%s; using 1000\n",
                    setting);
    }
    config.crank_immediate = std::getenv("MA17_CRANK_IMMEDIATE") != nullptr;
    return config;
}

} // namespace ma17
