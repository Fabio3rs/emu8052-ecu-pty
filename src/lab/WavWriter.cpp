#include "lab/WavWriter.hpp"

#include <array>
#include <fstream>
#include <limits>

namespace lab {
namespace {

void write_u16(std::ofstream &file, std::uint16_t value) {
    const std::array<char, 2> bytes{static_cast<char>(value & 0xff),
                                    static_cast<char>(value >> 8)};
    file.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
}

void write_u32(std::ofstream &file, std::uint32_t value) {
    write_u16(file, static_cast<std::uint16_t>(value & 0xffff));
    write_u16(file, static_cast<std::uint16_t>(value >> 16));
}

} // namespace

bool save_mono_wav(const std::string &path,
                   const std::vector<std::int16_t> &samples,
                   std::uint32_t sample_rate) {
    if (sample_rate == 0 ||
        sample_rate > std::numeric_limits<std::uint32_t>::max() / 2U ||
        samples.size() > (std::numeric_limits<std::uint32_t>::max() - 36U) / 2U)
        return false;
    const auto bytes = static_cast<std::uint32_t>(samples.size() * 2U);
    std::ofstream file(path, std::ios::binary);
    if (!file)
        return false;
    file.write("RIFF", 4);
    write_u32(file, 36U + bytes);
    file.write("WAVEfmt ", 8);
    write_u32(file, 16);
    write_u16(file, 1);
    write_u16(file, 1);
    write_u32(file, sample_rate);
    write_u32(file, sample_rate * 2U);
    write_u16(file, 2);
    write_u16(file, 16);
    file.write("data", 4);
    write_u32(file, bytes);
    for (const auto sample : samples)
        write_u16(file, static_cast<std::uint16_t>(sample));
    return file.good();
}

} // namespace lab
