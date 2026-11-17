#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace lab {

bool save_mono_wav(const std::string &path,
                   const std::vector<std::int16_t> &samples,
                   std::uint32_t sample_rate);

} // namespace lab
