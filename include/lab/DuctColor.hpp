#pragma once

#include <cmath>

namespace lab {

// 4.4: the intake runners glow in proportion to the manifold pressure: dim at
// a closed-throttle vacuum, bright at atmospheric. 0..101325 Pa maps to alpha
// 70..255; a non-finite or negative reading is shown as the dimmest value, so
// a missing sample never looks like a full manifold.
inline unsigned char intake_duct_alpha(double manifold_pressure_pa) {
    constexpr double atmosphere_pa = 101325.0;
    if (!std::isfinite(manifold_pressure_pa) || manifold_pressure_pa <= 0.0)
        return 70;
    const double fraction =
        manifold_pressure_pa >= atmosphere_pa ? 1.0
                                              : manifold_pressure_pa / atmosphere_pa;
    return static_cast<unsigned char>(70.0 + 185.0 * fraction + 0.5);
}

} // namespace lab
