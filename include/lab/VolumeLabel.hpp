#pragma once

#include <cstdio>
#include <string>
#include <string_view>

namespace lab {

// C3: the audio bar shows the volume ("VOL 100%") and, apart from it, a short
// state tag when the sound is not simply playing. The simulation speed has its
// own selector, so the bar no longer carries "SUSP>1X" as its main text.
struct VolumeLabel {
    std::string text;
    std::string tag;
};

inline VolumeLabel volume_label(bool enabled, std::string_view sound_state,
                                double volume) {
    if (!enabled)
        return {std::string("AUDIO ") + (sound_state == "off" ? "OFF" : "N/D"),
                ""};
    char text[24];
    std::snprintf(text, sizeof(text), "VOL %.0f%%", volume * 100.0);
    const char *tag = sound_state == "muted"       ? "MUTED"
                      : sound_state == "paused"    ? "PAUSED"
                      : sound_state == "key off"   ? "KEY OFF"
                      : sound_state == "speed"     ? "SPD>1X"
                      : sound_state == "suspended" ? "SUSP"
                                                   : "";
    return {text, tag};
}

} // namespace lab
