#pragma once

struct em8051;

namespace ma17 {

bool load_bin_to_code(em8051 *cpu, const char *path, unsigned base = 0);

} // namespace ma17
