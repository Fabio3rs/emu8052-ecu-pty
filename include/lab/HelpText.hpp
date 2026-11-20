#pragma once

#include <cstddef>
#include <string>
#include <vector>

namespace lab {

// The H overlay's lines. Keys that need Ctrl say so (a bare 7..9 is not FONT:
// bare 9 is the dyno view and bare 8 is RUN WOT).
inline std::vector<std::string> help_lines(bool drivetrain_available,
                                           bool png_enabled) {
    return {
        "K KEY  |  HOLD S START  |  UP/DOWN PEDAL  |  Q/E GEAR",
        "SPACE PAUSE  |  . STEP 10MS  |  , NEXT IGNITION",
        drivetrain_available
            ? "+/- SIM | PGUP/DN CLUTCH +10/-10% | L LOAD | M MUTE"
            : "+/- SIM | PGUP/DN ROAD INPUT | L LOAD | M MUTE",
        "V SHAFT/RADIAL/AXIAL PAIRS  |  WHEEL ZOOM  |  MIDDLE PAN",
        png_enabled ? "G GROUP  |  A ECU/ANALOG  |  X FREEZE  |  C CSV+PNG"
                    : "G GROUP  |  A ECU/ANALOG  |  X FREEZE  |  C CSV",
        "SCOPE Z MAX O FIT Y WHEEL/MID PAN/2X FIT | T MODE U CH Y EDGE",
        "TRIGGER I/J LEVEL B PRE  |  F11 FULL  F12 PNG  R FIT",
        "CTRL+U UNITS  |  CTRL+0..3 UI  |  CTRL+4..6 LAYOUT  |  CTRL+7..9 FONT",
        "P THEME  9 DYNO  8 RUN WOT  0 FREEZE CURVE  N CALIB  W TABLE  5 VARIANT  1/2 SNAP  3/4 LOAD A/B",
        "WHEEL ON PEDAL/LOAD/VOLUME 1% (SHIFT 0.1%)  |  CLICK 0.25X 1X 4X SPEED"};
}

// Height of the overlay for `lines` lines at logical scale 1: title band, 26 per
// line, bottom margin. (It used to be a fixed 260, which hid the last lines.)
inline float help_panel_height(std::size_t lines) {
    return 48.0f + 26.0f * static_cast<float>(lines) + 4.0f;
}

} // namespace lab
