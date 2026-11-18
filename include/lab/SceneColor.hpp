#pragma once

#include <SDL3/SDL.h>

#include <algorithm>
#include <cmath>

namespace lab {

// Donor scene colors keep their alpha (the combustion flame is 0.70/0.95).
// Out-of-range values are clamped; NaN becomes 0 instead of reaching SDL.
inline float scene_unit(float value) {
    return std::isfinite(value) ? std::clamp(value, 0.0f, 1.0f) : 0.0f;
}

template <typename Color> SDL_FColor scene_fcolor(const Color &color) {
    return {scene_unit(color.x), scene_unit(color.y), scene_unit(color.z),
            scene_unit(color.w)};
}

// Same blend as the donor GPU pipeline (sdl_gpu_renderer.cpp): color =
// src * srcA + dst * (1 - srcA), alpha = srcA + dstA * (1 - srcA), which is
// SDL_BLENDMODE_BLEND. The scene replay must draw with it.
inline constexpr SDL_BlendMode kSceneBlendMode = SDL_BLENDMODE_BLEND;

} // namespace lab
