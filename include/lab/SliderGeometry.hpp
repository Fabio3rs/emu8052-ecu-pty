#pragma once

#include <SDL3/SDL_rect.h>

#include <algorithm>
#include <array>
#include <cmath>

namespace lab {

// C2: geometry of the pedal / volume slider. The track spans the whole box so a
// pointer maps to the same fraction as before ((x - box.x) / box.w); only the
// look changes: a visible track, a thumb, tick marks and snap presets.
struct SliderGeometry {
    SDL_FRect track;                 // the groove, along the box bottom
    std::array<float, 5> tick_x{};   // x of the 0/25/50/75/100 % marks
    float tick_top = 0.0f;           // ticks run from tick_top to track.y
};

inline constexpr std::array<float, 5> kSliderPresets{0.0f, 0.25f, 0.5f, 0.75f,
                                                     1.0f};

// C2: the pedal slider's mark names ("0 · 25 · 50 · 75 · WOT"): the last mark
// is wide-open throttle.
inline constexpr std::array<const char *, 5> kPedalPresetLabels{"0", "25", "50",
                                                               "75", "WOT"};

inline SliderGeometry compute_slider_geometry(const SDL_FRect &box,
                                              float scale) {
    SliderGeometry geometry;
    const float track_h = 4.0f * scale;
    geometry.track = {box.x + 1.0f, box.y + box.h - track_h - 3.0f * scale,
                      std::max(0.0f, box.w - 2.0f), track_h};
    for (std::size_t i = 0; i < kSliderPresets.size(); ++i)
        geometry.tick_x[i] =
            geometry.track.x + geometry.track.w * kSliderPresets[i];
    geometry.tick_top = geometry.track.y - 3.0f * scale;
    return geometry;
}

// The thumb: 6 x 10 logical units centred on the value, kept inside the box.
inline SDL_FRect slider_thumb_rect(const SliderGeometry &geometry,
                                   const SDL_FRect &box, float fraction,
                                   float scale) {
    const float w = 6.0f * scale;
    const float h = 10.0f * scale;
    const float cx =
        geometry.track.x + geometry.track.w * std::clamp(fraction, 0.0f, 1.0f);
    const float x = std::clamp(cx - w * 0.5f, box.x, box.x + box.w - w);
    return {x, geometry.track.y + geometry.track.h * 0.5f - h * 0.5f, w, h};
}

// Click preset: a press within `snap_px` of a 0/25/50/75/100 % mark lands
// exactly on it; a drag never snaps (the caller passes drag = false only for
// the initial press).
inline float snap_to_preset(float fraction, float track_width_px,
                            float snap_px = 3.0f) {
    for (const float preset : kSliderPresets)
        if (std::fabs(fraction - preset) * track_width_px <= snap_px)
            return preset;
    return fraction;
}

// Mouse wheel: 1 % per notch, 0.1 % with Shift; positive = up = more.
inline float slider_wheel_step(float fraction, float notches, bool shift) {
    const float step = shift ? 0.001f : 0.01f;
    const float direction = notches > 0.0f ? 1.0f : notches < 0.0f ? -1.0f : 0.0f;
    return std::clamp(fraction + direction * step, 0.0f, 1.0f);
}

} // namespace lab
