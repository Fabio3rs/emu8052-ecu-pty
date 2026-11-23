#pragma once
#include <SDL3/SDL.h>
namespace lab {
class FontRenderer;
class SevelCadView;
class CadToolbar {
public:
    SDL_FRect bounds{};
    int plane_preset{}, dragging{};
    bool reload{};
    void draw(SDL_Renderer *screen,FontRenderer &font,SevelCadView &view,SDL_FRect region);
    bool input(const SDL_Event &e,SevelCadView &view);
};
} // namespace lab
