#include "lab/CadPanel.hpp"
#include "lab/SevelCadView.hpp"
#include "sdl_gpu_renderer.h"

namespace lab {
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
    visible = false;
    if (!show || region.w <= 0 || region.h <= 0) return true;
    int w{}, h{}, lw{}, lh{};
    if (!SDL_GetRenderOutputSize(screen,&w,&h)) return false;
    SDL_RendererLogicalPresentation mode{};
    SDL_GetRenderLogicalPresentation(screen,&lw,&lh,&mode);
    const float sx = lw ? static_cast<float>(w)/static_cast<float>(lw) : 1.f;
    const float sy = lh ? static_cast<float>(h)/static_cast<float>(lh) : 1.f;
    area = {static_cast<int>(region.x*sx),static_cast<int>(region.y*sy),
            static_cast<int>(region.w*sx),static_cast<int>(region.h*sy)};
    if (area.w <= 0 || area.h <= 0) return true;
    if (!target || target->w != area.w || target->h != area.h) {
        gpu.setPanelTarget(nullptr);
        SDL_DestroyTexture(target);
        target = SDL_CreateTexture(screen, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_TARGET, area.w, area.h);
        if (!target || !SDL_SetTextureBlendMode(target, SDL_BLENDMODE_NONE) ||
            !SDL_SetTextureScaleMode(target, SDL_SCALEMODE_NEAREST)) return false;
        auto *texture = static_cast<SDL_GPUTexture *>(SDL_GetPointerProperty(
            SDL_GetTextureProperties(target), SDL_PROP_TEXTURE_GPU_TEXTURE_POINTER, nullptr));
        if (!texture) return false;
        gpu.setPanelTarget(texture);
    }
    view.draw(gpu,area.w,area.h,phase);
    const SDL_FRect destination{static_cast<float>(area.x)/sx, static_cast<float>(area.y)/sy,
                                static_cast<float>(area.w)/sx, static_cast<float>(area.h)/sy};
    visible = !gpu.failed() && SDL_RenderTexture(screen,target,nullptr,&destination);
    return visible;
}
} // namespace lab
