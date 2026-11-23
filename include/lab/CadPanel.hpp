#pragma once

#include <SDL3/SDL.h>

class SdlGpuRenderer;
namespace lab {
class SevelCadView;

struct CadPanel {
    SDL_Texture *target = nullptr; // Owned by the window renderer.
    SDL_Rect area{};
    bool visible = false;
    bool focused = false;
    bool pointer(SevelCadView &view, SDL_Event event);
    bool present(SdlGpuRenderer &gpu, SevelCadView &view, SDL_Renderer *screen,
                 SDL_FRect region, double phase, bool show);
};
} // namespace lab
