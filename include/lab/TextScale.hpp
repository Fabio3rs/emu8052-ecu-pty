#pragma once

namespace lab {

// L3: the Lab uses two text scales. `kTextSmall` replaces the 0.60 /
// 0.60 / 0.65 / 0.68 / 0.70 / 0.72 / 0.75 literals that were scattered over the
// drawing code; on the pixel face they all land in the same whole-design-pixel
// bucket (lab_font_test: AllSmallTextScalesRenderInOneBucket), so naming one
// value changes no rendering at ui scales 1.0, 1.5, 1.75 and 2.0 for the 0.60-0.72
// literals (0.72 is the most common old value; 0.75 would split from them at
// ui 2.0). At ui 1.25 the 0.60-0.70 sites move up one bucket: accepted.
// The measure/draw pair can no longer disagree either way.
inline constexpr float kTextNormal = 1.0f;
// The smallest bucket at high UI scales: 0.55 * 1.5 rounds to one design-pixel
// cell where 0.75 * 1.5 rounds to two, so hints, tags and the BURN/MISS captions
// keep this one to stay small on a 1080p window (checked in lab_font_test).
inline constexpr float kTextTiny = 0.55f;
inline constexpr float kTextSmall = 0.72f;

} // namespace lab
