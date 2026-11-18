#pragma once

#include <cmath>
#include <cstdio>
#include <string>

namespace lab {

// Presentation of a signed road speed on a 0..max dial. Rolling backwards is
// shown as |v| with an "R" marker; the signed value itself stays in telemetry.
// Without this a negative value would read as the dial's under-range arrow.
struct SpeedReading {
    double dial_value = 0.0;
    bool reversing = false;
    std::string text;
};

inline SpeedReading speed_reading(double signed_speed, const char *unit) {
    SpeedReading reading;
    reading.reversing = std::isfinite(signed_speed) && signed_speed < 0.0;
    reading.dial_value = reading.reversing ? -signed_speed : signed_speed;
    char buffer[48];
    std::snprintf(buffer, sizeof(buffer), "%s%.0f %s",
                  reading.reversing ? "R " : "", reading.dial_value,
                  unit ? unit : "");
    reading.text = buffer;
    return reading;
}

} // namespace lab
