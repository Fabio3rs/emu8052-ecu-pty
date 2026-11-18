#pragma once

#include "lab/SevelInstrumentProfile.hpp"

#include <string_view>

namespace lab {

enum class DisplayUnits { Metric, Imperial };

struct UnitTransform {
    double factor = 1.0;
    double offset = 0.0;
    const char *unit = nullptr;
};

inline constexpr UnitTransform unit_transform(const profile::Instrument &spec,
                                              DisplayUnits units) {
    if (units == DisplayUnits::Metric)
        return {1.0, 0.0, spec.unit};
    const std::string_view id{spec.id ? spec.id : ""};
    if (id == "coolant" || id == "ect_physical" || id == "iat_physical")
        return {9.0 / 5.0, 32.0, "F"};
    if (id == "vehicle_speed")
        return {0.621371192237334, 0.0, "MPH"};
    if (id == "manifold_pressure")
        return {0.2952998750804, 0.0, "INHG"};
    return {1.0, 0.0, spec.unit};
}

inline constexpr double display_value(double value,
                                      const profile::Instrument &spec,
                                      DisplayUnits units) {
    const auto transform = unit_transform(spec, units);
    return value * transform.factor + transform.offset;
}

inline constexpr profile::Instrument display_profile(
    profile::Instrument spec, DisplayUnits units) {
    const auto transform = unit_transform(spec, units);
    spec.unit = transform.unit;
    spec.minimum = spec.minimum * transform.factor + transform.offset;
    spec.maximum = spec.maximum * transform.factor + transform.offset;
    spec.major_step *= transform.factor;
    spec.minor_step *= transform.factor;
    for (std::size_t index = 0;
         index < spec.band_count && index < spec.bands.size(); ++index) {
        spec.bands[index].start =
            spec.bands[index].start * transform.factor + transform.offset;
        spec.bands[index].end =
            spec.bands[index].end * transform.factor + transform.offset;
    }
    return spec;
}

static_assert(display_value(90.0, profile::coolant,
                            DisplayUnits::Imperial) == 194.0);
static_assert(display_profile(profile::coolant,
                              DisplayUnits::Imperial).bands[0].start == 248.0);
static_assert(display_value(100.0, profile::speed,
                            DisplayUnits::Imperial) > 62.13);

} // namespace lab
