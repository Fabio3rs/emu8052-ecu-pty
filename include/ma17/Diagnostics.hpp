#pragma once

#include <cstdarg>
#include <cstdio>

namespace ma17 {

// The standalone harness emits traces. The Lab sets this before starting its workers.
inline bool verbose_diagnostics = true;

[[gnu::format(printf, 2, 3)]]
inline void diagnostic_log(std::FILE *stream, const char *format, ...) {
    if (!verbose_diagnostics) return;
    std::va_list args;
    va_start(args, format);
    std::vfprintf(stream, format, args);
    va_end(args);
}

} // namespace ma17
