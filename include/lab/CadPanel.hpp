#pragma once

#include <SDL3/SDL.h>
#include <memory>

class SdlGpuRenderer;
namespace lab {
class FontRenderer;
class SevelCadView;

struct CadPanel {
    std::unique_ptr<SDL_Surface,decltype(&SDL_DestroySurface)> surface{nullptr,SDL_DestroySurface};
    SDL_Rect area{};
    bool visible = false;
    bool focused = false;
    bool resize(SDL_Window *window, SDL_Renderer *&screen, FontRenderer *font);
    void coordinates(SDL_Window *window, SDL_Renderer *screen, SDL_Event &event) const;
    bool pointer(SevelCadView &view, SDL_Event event);
    bool present(SdlGpuRenderer &gpu, SevelCadView &view, SDL_Renderer *screen,
                 SDL_FRect region, double phase, bool show);
    void compose_capture(SdlGpuRenderer &gpu, SDL_Surface *frame) const;
};
} // namespace lab
