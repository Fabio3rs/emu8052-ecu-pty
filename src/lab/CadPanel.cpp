#include "lab/CadPanel.hpp"
#include "lab/FontRenderer.hpp"
#include "lab/SevelCadView.hpp"
#include "sdl_gpu_renderer.h"
#include <algorithm>
#include <cmath>

namespace lab {
bool CadPanel::resize(SDL_Window *window, SDL_Renderer *&screen, FontRenderer *font) {
    int w{}, h{};
    if (!SDL_GetWindowSizeInPixels(window,&w,&h) || w <= 0 || h <= 0) return false;
    if (surface && surface->w == w && surface->h == h) return true;
    decltype(surface) next(SDL_CreateSurface(w,h,SDL_PIXELFORMAT_RGBA32),SDL_DestroySurface);
    auto *renderer = next ? SDL_CreateSoftwareRenderer(next.get()) : nullptr;
    if (!renderer) return false;
    if (font) font->release_textures();
    if (screen) SDL_DestroyRenderer(screen);
    screen = renderer;
    surface = std::move(next);
    return true;
}

void CadPanel::coordinates(SDL_Window *window, SDL_Renderer *screen, SDL_Event &event) const {
    int w{},h{},lw{},lh{};
    SDL_RendererLogicalPresentation mode{};
    SDL_GetWindowSize(window,&w,&h);
    SDL_GetRenderLogicalPresentation(screen,&lw,&lh,&mode);
    if (!lw || !lh) { lw=surface->w; lh=surface->h; }
    const float sx = static_cast<float>(lw)/static_cast<float>(std::max(w,1));
    const float sy = static_cast<float>(lh)/static_cast<float>(std::max(h,1));
    if (event.type == SDL_EVENT_MOUSE_WHEEL) { event.wheel.mouse_x *= sx; event.wheel.mouse_y *= sy; }
    else if (event.type == SDL_EVENT_MOUSE_MOTION) {
        event.motion.x *= sx; event.motion.y *= sy;
        event.motion.xrel *= sx; event.motion.yrel *= sy;
    } else { event.button.x *= sx; event.button.y *= sy; }
}

bool CadPanel::pointer(SevelCadView &view, SDL_Event e) {
    if (!visible) return false;
    const bool motion = e.type == SDL_EVENT_MOUSE_MOTION, wheel = e.type == SDL_EVENT_MOUSE_WHEEL;
    const auto *window = SDL_GetWindowFromEvent(&e);
    const float scale = window ? SDL_GetWindowPixelDensity(const_cast<SDL_Window*>(window)) : 1.f;
    const float x = (motion ? e.motion.x : wheel ? e.wheel.mouse_x : e.button.x)*scale;
    const float y = (motion ? e.motion.y : wheel ? e.wheel.mouse_y : e.button.y)*scale;
    SDL_Point point{static_cast<int>(x),static_cast<int>(y)};
    const bool inside = SDL_PointInRect(&point,&area);
    if (e.type == SDL_EVENT_MOUSE_BUTTON_DOWN) focused = inside;
    const bool drag = motion && (e.motion.state & (SDL_BUTTON_LMASK | SDL_BUTTON_RMASK));
    if (!inside && !(focused && (drag || e.type == SDL_EVENT_MOUSE_BUTTON_UP))) return false;
    if (motion) {
        e.motion.x -= static_cast<float>(area.x)/scale; e.motion.y -= static_cast<float>(area.y)/scale;
    } else if (!wheel) {
        e.button.x -= static_cast<float>(area.x)/scale; e.button.y -= static_cast<float>(area.y)/scale;
    }
    view.event(e);
    return true;
}

bool CadPanel::present(SdlGpuRenderer &gpu, SevelCadView &view, SDL_Renderer *screen,
                       SDL_FRect region,double phase,bool show) {
    if (!SDL_FlushRenderer(screen) || !gpu.setPanelBackground(surface.get())) return false;
    int lw{},lh{};
    SDL_RendererLogicalPresentation mode{};
    SDL_GetRenderLogicalPresentation(screen,&lw,&lh,&mode);
    const float sx = lw ? static_cast<float>(surface->w)/static_cast<float>(lw) : 1.f;
    const float sy = lh ? static_cast<float>(surface->h)/static_cast<float>(lh) : 1.f;
    area = {static_cast<int>(region.x*sx),static_cast<int>(region.y*sy),
            static_cast<int>(region.w*sx),static_cast<int>(region.h*sy)};
    visible = show && area.w > 0 && area.h > 0;
    if (visible) view.draw(gpu,area.w,area.h,phase,area.x,area.y);
    else { gpu.beginFrame({0,0,0,1}); gpu.setSceneViewport(0,0,1,1); gpu.endFrame(); }
    return !gpu.failed();
}

void CadPanel::compose_capture(SdlGpuRenderer &gpu, SDL_Surface *frame) const {
    if (!visible || !frame) return;
    std::vector<std::uint8_t> pixels;
    std::uint32_t w{},h{};
    std::string error;
    if (!gpu.captureSceneRgba(pixels,w,h,error)) return;
    auto *cad = SDL_CreateSurfaceFrom(static_cast<int>(w),static_cast<int>(h),SDL_PIXELFORMAT_RGBA32,
                                      pixels.data(),static_cast<int>(w*4));
    if (cad) { SDL_BlitSurface(cad,nullptr,frame,&area); SDL_DestroySurface(cad); }
}
} // namespace lab
