#pragma once

#include "Lifetime.hpp"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

namespace lab {

// L5: the unit text of a scope lane. The dimensionless unit "1" (lambda) is
// meaningless next to the number and was the stray "1" in "LAMBDA 1.20 1".
inline const char *scope_unit_text(const char *unit EMU_LIFETIMEBOUND) {
    return (unit == nullptr || std::strcmp(unit, "1") == 0) ? "" : unit;
}

// The value shown in a lane label. A reading outside the lane's scale is shown
// as "> max" / "< min" rather than a raw number (a stopped engine reads
// lambda 5.00, which is "no exhaust sample", not a mixture).
inline std::string scope_value_text(double value, double minimum,
                                    double maximum) {
    char text[32];
    if (value > maximum)
        std::snprintf(text, sizeof(text), "> %.2f", maximum);
    else if (value < minimum)
        std::snprintf(text, sizeof(text), "< %.2f", minimum);
    else
        std::snprintf(text, sizeof(text), "%.2f", value);
    return text;
}

// G2: text of a scale-end numeral on a dial that has no regular numerals.
// Whole values print without decimals, small fractional ones with one.
inline std::string scale_end_text(double value) {
    char text[16];
    if (std::fabs(value - std::round(value)) < 1e-9 || std::fabs(value) >= 10.0)
        std::snprintf(text, sizeof(text), "%.0f", value);
    else
        std::snprintf(text, sizeof(text), "%.1f", value);
    return text;
}

// D1: the ignition block shows the commanded spark advance next to the
// model's MBT; their difference is information. Without an ignition event
// (no burns yet) both read "--" rather than a misleading 0.
struct IgnitionAdvanceText {
    std::string advance;
    std::string mbt;
    std::string difference;
};

inline IgnitionAdvanceText ignition_advance_text(bool valid, double advance_deg,
                                                 double mbt_deg) {
    if (!valid || !std::isfinite(advance_deg) || !std::isfinite(mbt_deg))
        return {"ADV --", "MBT --", "DIFF --"};
    char adv[24], mbt[24], diff[24];
    std::snprintf(adv, sizeof(adv), "ADV %.1f\xC2\xB0", advance_deg);
    std::snprintf(mbt, sizeof(mbt), "MBT %.1f\xC2\xB0", mbt_deg);
    std::snprintf(diff, sizeof(diff), "DIFF %+.1f\xC2\xB0",
                  advance_deg - mbt_deg);
    return {adv, mbt, diff};
}

// C3: the simulation speed multiplier, always visible, separate from audio.
// Powers of two within 0.1..16 print compactly: 0.25X, 0.5X, 1X, 2X, 4X, 16X.
inline std::string speed_multiplier_text(double multiplier) {
    char text[24];
    std::snprintf(text, sizeof(text), "%.3gX", multiplier);
    return text;
}

// D7: tooltip line for the ignition column. Before the first ignition event
// there is nothing to report, so it says "--" rather than 0.
inline std::string spark_quality_text(bool valid, double efficiency,
                                      double residual_fraction) {
    if (!valid || !std::isfinite(efficiency) || !std::isfinite(residual_fraction))
        return "SPARK EFF --  RESIDUAL --";
    char text[48];
    std::snprintf(text, sizeof(text), "SPARK EFF %.2f  RESIDUAL %.2f", efficiency,
                  residual_fraction);
    return text;
}

} // namespace lab
