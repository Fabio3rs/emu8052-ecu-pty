#include "lab/CadToolbar.hpp"
#include "lab/FontRenderer.hpp"
#include "lab/SevelCadView.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace lab {
namespace {
constexpr int columns = 6;
constexpr float row_height = 18.f;
constexpr std::array<SDL_Keycode,18> keys{SDLK_I,SDLK_SPACE,SDLK_RIGHT,SDLK_TAB,SDLK_H,SDLK_G,
    SDLK_C,0,SDLK_F,SDLK_M,SDLK_K,SDLK_F5,SDLK_O,SDLK_HOME,SDLK_J,SDLK_E,SDLK_U,SDLK_B};
}

void CadToolbar::draw(SDL_Renderer *screen, FontRenderer &font, SevelCadView &v, SDL_FRect region) {
    bounds = {region.x,region.y,region.w,5*row_height};
    const auto plane_label = std::abs(v.normal.z)>.999f ? "LONG" : std::abs(v.normal.y)>.999f ? "TOP" :
        std::abs(v.normal.x)<.999f ? "FREE" : plane_preset>=1 && plane_preset<=4 ?
        "C"+std::to_string(plane_preset) : "TRANS";
    const std::array<std::string,18> labels{v.inspect?"INSPECT":v.scene.rig.available?"LIVE":"STATIC",v.playing?"PAUSE":"PLAY","+1 DEG",
        v.group,v.hidden.contains(v.group)?"SHOW":"HIDE",v.ghost.contains(v.group)?"SOLID":"GHOST",
        v.cut?"CUT ON":"CUT OFF",plane_label,
        "INVERT",v.cut_moving?"ALL PARTS":"FIXED",v.fill && v.cap_supported?"CAP":"CLIP ONLY","RELOAD",
        v.orthographic?"ORTHO":"PERSP","FIT",v.isolate?"SHOW ALL":"ISOLATE",
        v.explode_mm != 0 ? "EXP "+std::to_string(std::lround(v.explode_mm)):"EXPLODE",
        v.uncut.contains(v.group)?"KEEP GROUP":"CUT GROUP",v.second_cut?"2 PLANES":"PIN PLANE"};
    SDL_SetRenderDrawColor(screen,24,29,34,255);
    SDL_RenderFillRect(screen,&bounds);
    const float w = bounds.w/columns;
    for (int i=0; i<18; ++i) {
        const SDL_FRect box{bounds.x+w*static_cast<float>(i%columns),bounds.y+row_height*static_cast<float>(i/columns),w,row_height};
        SDL_SetRenderDrawColor(screen,62,73,83,255);
        SDL_RenderRect(screen,&box);
        font.draw(screen,box.x+3,box.y+2,font.ellipsize(labels[static_cast<std::size_t>(i)],11,w-5),
                  {181,211,216,255},.92f);
    }
    const float half = bounds.w*.5f;
    float phase = static_cast<float>(std::fmod(v.presented_phase,720.));
    if (phase < 0) phase += 720.f;
    if (v.inspect && v.presented_phase == 720.) phase = 720.f;
    for (int i=0; i<2; ++i) {
        const float x = bounds.x+static_cast<float>(i)*half;
        const float y = bounds.y+3*row_height;
        const float fraction = i ? std::clamp(v.offset_mm/800.f+.5f,0.f,1.f) : phase/720.f;
        SDL_SetRenderDrawColor(screen,59,133,146,255);
        SDL_FRect fill{x,y,half*fraction,row_height};
        SDL_RenderFillRect(screen,&fill);
        auto label = i ? "PLANE "+std::to_string(std::lround(v.offset_mm))+" MM" :
                         "PHASE "+std::to_string(std::lround(phase))+" DEG";
        font.draw(screen,x+4,y+2,label,{229,236,237,255},.8f);
    }
    std::string hint = "Drag orbit / RMB pan / XYZ tilt plane / F6 save / F7 load";
    if (!v.reload_status.empty()) hint = v.reload_status;
    for (const auto &part : v.scene.parts) if (part.id == v.selected) {
        hint = part.label+" | "+part.id+" | "+part.motion+
               (part.cylinder ? " C"+std::to_string(part.cylinder) : "")+" | "+part.evidence;
        break;
    }
    font.draw(screen,bounds.x+3,bounds.y+4*row_height+1,
              font.ellipsize(hint,11,bounds.w-6),{182,196,206,255},.9f);
    if (v.cut) {
        const auto plane = v.clipPlane();
        auto n = ysMath::MatMult(v.last_view,ysVector{plane.x,plane.y,plane.z,0});
        const float x = bounds.x+bounds.w-14, y = bounds.y+3.5f*row_height;
        SDL_SetRenderDrawColor(screen,253,183,90,255);
        SDL_RenderLine(screen,x,y,x+11*n.x,y-8*n.y);
        SDL_FRect tip{x+11*n.x-2,y-8*n.y-2,4,4};
        SDL_RenderFillRect(screen,&tip);
    }
}

bool CadToolbar::input(const SDL_Event &e, SevelCadView &v) {
    const bool motion = e.type == SDL_EVENT_MOUSE_MOTION;
    if (e.type == SDL_EVENT_MOUSE_BUTTON_UP && dragging) { dragging = 0; return true; }
    if (!(motion && dragging) && (e.type != SDL_EVENT_MOUSE_BUTTON_DOWN || e.button.button != SDL_BUTTON_LEFT)) return false;
    const SDL_FPoint pos{motion ? e.motion.x : e.button.x,motion ? e.motion.y : e.button.y};
    if (!dragging && !SDL_PointInRectFloat(&pos,&bounds)) return false;
    const int row = static_cast<int>((pos.y-bounds.y)/row_height);
    if (dragging || row == 3) {
        if (!dragging) dragging = pos.x < bounds.x+bounds.w*.5f ? 1 : 2;
        const float f = std::clamp(2*(pos.x-bounds.x)/bounds.w-static_cast<float>(dragging-1),0.f,1.f);
        if (dragging == 1) { v.inspect = true; v.playing = false; v.inspected_phase = static_cast<double>(f)*720.; }
        else { v.cut = true; v.offset_mm = (f-.5f)*800; }
    } else if (row < 3) {
        auto i = static_cast<std::size_t>(row*columns+std::clamp(static_cast<int>((pos.x-bounds.x)*columns/bounds.w),0,columns-1));
        if (i == 7) { plane_preset = (plane_preset+1)%6; v.orientPlane(plane_preset); }
        else if (i == 11) reload = true;
        else {
            if ((i == 1 || i == 2) && !v.inspect) { v.inspect = true; v.inspected_phase = v.presented_phase; }
            SDL_Event key{}; key.type = SDL_EVENT_KEY_DOWN; key.key.key = keys[i]; v.event(key);
        }
    }
    return true;
}
} // namespace lab
