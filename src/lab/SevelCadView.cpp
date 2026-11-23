#include "lab/SevelCadView.hpp"
#include "sdl_gpu_renderer.h"
#include "shaders.h"

#include <SDL3/SDL.h>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <stdexcept>

namespace lab {

static ysMatrix section_model(ysVector plane, ysVector center, float size) {
    auto normal = plane; normal.w = 0;
    auto u = ysMath::Normalize(ysMath::Cross(normal,std::abs(normal.y)<.9f ?
                                             ysMath::Constants::YAxis : ysMath::Constants::XAxis));
    center = ysMath::Sub(center,ysMath::Mul(normal,ysMath::LoadScalar(ysMath::Dot(center,normal).x+plane.w)));
    center.w = 1;
    return ysMath::LoadMatrix(ysMath::Mul(u,ysMath::LoadScalar(size)),
        ysMath::Mul(ysMath::Cross(normal,u),ysMath::LoadScalar(size)),normal,center);
}

void SevelCadView::load(SdlGpuRenderer &renderer, const std::filesystem::path &path) {
    const auto begin = std::chrono::steady_clock::now();
    auto candidate = load_cad_scene(path);
    const auto now = std::chrono::steady_clock::now();
    install(renderer,std::move(candidate),std::chrono::duration<double,std::milli>(now-begin).count());
}

void SevelCadView::requestReload(const std::filesystem::path &path) {
    if (pending.valid()) return;
    reload_status = "Loading CAD";
    reload_start = SDL_GetTicks();
    pending = std::async(std::launch::async,[path] {return load_cad_scene(path);});
}

void SevelCadView::pollReload(SdlGpuRenderer &renderer) {
    if (!pending.valid() || pending.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
    try {
        auto candidate = pending.get();
        if (candidate.revision != scene.revision)
            install(renderer,std::move(candidate),static_cast<double>(SDL_GetTicks()-reload_start));
        reload_status = "Loaded "+scene.revision.substr(0,8);
        std::printf("[LAB-CAD] reload=ready revision=%s\n",scene.revision.c_str());
    } catch (const std::exception &e) {
        reload_status = "Reload failed: "+std::string(e.what());
        std::fprintf(stderr,"[LAB-CAD] reload=rejected active=%s error=%s\n",scene.revision.c_str(),e.what());
    }
}

void SevelCadView::install(SdlGpuRenderer &renderer,SevelCadScene candidate,double decode_ms) {
    if (!scene.parts.empty()) validate_cad_replacement(scene,candidate);
    const auto decoded = std::chrono::steady_clock::now();
    const int quad_v = static_cast<int>(candidate.vertices.size());
    const int quad_i = static_cast<int>(candidate.indices.size());
    for (const auto xy : {ysVector{-1,-1,0,1},{1,-1,0,1},{1,1,0,1},{-1,1,0,1}})
        candidate.vertices.push_back({xy,{0,0,1,0},{}});
    candidate.indices.insert(candidate.indices.end(),{0,1,2,0,2,3});
    std::string error;
    if (!renderer.installStaticGeometry(candidate.vertices,candidate.indices,error))
        throw std::runtime_error("CAD upload: " + error);
    radius = ysMath::Magnitude(ysMath::Sub(candidate.upper,candidate.lower)).x * 0.5f;
    if (scene.parts.empty()) {
        target = ysMath::Mul(ysMath::Add(candidate.upper,candidate.lower), ysMath::LoadScalar(0.5f));
        distance = radius * 2.55f;
    }
    scene = std::move(candidate);
    if (!selected.empty() && std::none_of(scene.parts.begin(),scene.parts.end(),
        [&](const auto &p) { return p.id == selected; })) { selected.clear(); isolate = false; }
    quad_vertex = quad_v;
    quad_index = quad_i;
    cap_supported = renderer.supportsSectionCaps();
    std::set<std::string> unique_groups;
    for (const auto &p : scene.parts) unique_groups.insert(p.group);
    groups.assign(unique_groups.begin(),unique_groups.end());
    if (!unique_groups.contains(group)) group = groups.front();
    const auto now = std::chrono::steady_clock::now();
    std::printf("[LAB-CAD] parts=%zu meshes=%zu vertices=%zu triangles=%zu gpu_bytes=%zu load_ms=%.1f upload_ms=%.1f revision=%s\n",
        scene.parts.size(),scene.meshes.size(),scene.vertices.size(),scene.indices.size()/3,
        scene.vertices.size()*sizeof(EngineSimVertex)+scene.indices.size()*sizeof(std::uint16_t),
        decode_ms,
        std::chrono::duration<double,std::milli>(now-decoded).count(),scene.revision.c_str());
}

void SevelCadView::updatePhase(double phase_deg) {
    const auto now = SDL_GetTicks();
    if (inspect && playing && last_time)
        inspected_phase = std::fmod(inspected_phase+speed_deg_s*static_cast<double>(now-last_time)/1000,720.);
    last_time = now;
    presented_phase = inspect ? inspected_phase : phase_deg;
}

void SevelCadView::draw(SdlGpuRenderer &renderer, int width, int height, double phase_deg, int viewport_x, int viewport_y) {
    auto frame_start = SDL_GetPerformanceCounter();
    updatePhase(phase_deg);
    const ysVector back{std::sin(yaw)*std::cos(pitch), std::sin(pitch), std::cos(yaw)*std::cos(pitch)};
    const ysVector right{std::cos(yaw),0,-std::sin(yaw)};
    const auto up = ysMath::Cross(back,right);
    const auto eye = ysMath::Add(target,ysMath::Mul(back,ysMath::LoadScalar(distance)));
    auto view = ysMath::Transpose(ysMath::LoadMatrix(right,up,back,{0,0,0,1}));
    view.m[0][3] = -ysMath::Dot(right,eye).x;
    view.m[1][3] = -ysMath::Dot(up,eye).x;
    view.m[2][3] = -ysMath::Dot(back,eye).x;
    const float near = std::max(.002f, distance-radius*2.f);
    const float far = distance+radius*4.f;
    const float aspect = static_cast<float>(width)/static_cast<float>(height);
    ysMatrix projection{};
    projection.m[1][1] = 2.4f / (orthographic ? distance : 1.f);
    projection.m[0][0] = projection.m[1][1] / aspect;
    projection.m[2][2] = (orthographic ? 1.f : far) / (near-far);
    projection.m[2][3] = near * (orthographic ? 1.f : far) / (near-far);
    projection.m[3][orthographic ? 3 : 2] = orthographic ? 1.f : -1.f;
    last_width = width;
    last_height = height;
    last_view = view;
    last_projection = projection;
    renderer.beginFrame({.075f,.09f,.115f,1});
    renderer.setSceneViewport(static_cast<float>(viewport_x),static_cast<float>(viewport_y),
                              static_cast<float>(width),static_cast<float>(height));
    const auto plane = clipPlane();
    const auto center = ysMath::Mul(ysMath::Add(scene.lower,scene.upper),ysMath::LoadScalar(.5f));
    const float size = radius*2+std::abs(explode_mm)*.002f;
    const auto plane_model = section_model(plane,center,size);
    const auto second_model = section_model(second_plane,center,size);
    const auto view_projection = ysMath::MatMult(projection,view);
    for (const auto &p : scene.parts) {
        if (hidden.contains(p.group) || (isolate && selected != p.id)) continue;
        const auto pose = partPose(p);
        auto [lo,hi] = scene.mesh_bounds.at(p.mesh);
        lo.y += std::min(0.f,pose.spring_delta);
        hi.y += std::max(0.f,pose.spring_delta);
        // Reject only if all eight posed AABB corners lie beyond one clip face.
        const auto mvp = ysMath::MatMult(view_projection,pose.model);
        unsigned outside = 63;
        for (const auto x : {lo.x,hi.x}) for (const auto y : {lo.y,hi.y}) for (const auto z : {lo.z,hi.z}) {
            const auto q = ysMath::MatMult(mvp,ysVector{x,y,z,1});
            unsigned mask = 0;
            if (q.x < -q.w) mask |= 1;
            if (q.x > q.w) mask |= 2;
            if (q.y < -q.w) mask |= 4;
            if (q.y > q.w) mask |= 8;
            if (q.z < 0) mask |= 16;
            if (q.z > q.w) mask |= 32;
            outside &= mask;
        }
        if (outside) continue;
        const bool clipped = cut && !uncut.contains(p.group) && (p.motion == "fixed" || cut_moving);
        bool intersects = false, crosses_second = false;
        if (clipped) {
            float low = 100, high = -100, low2 = 100, high2 = -100;
            for (const auto x : {lo.x,hi.x}) for (const auto y : {lo.y,hi.y}) for (const auto z : {lo.z,hi.z}) {
                const auto corner = ysMath::MatMult(pose.model,ysVector{x,y,z,1});
                const auto dist = ysMath::Dot(plane,corner).x+plane.w;
                low = std::min(low,dist);
                high = std::max(high,dist);
                const float d2 = ysMath::Dot(second_plane,corner).x+second_plane.w;
                low2 = std::min(low2,d2); high2 = std::max(high2,d2);
            }
            if (high < 0) continue;
            intersects = low < 0;
            if (second_cut && high2 < 0) continue;
            crosses_second = second_cut && low2 < 0;
        }
        renderer.setClipPlane(clipped ? plane : ysVector{},clipped && second_cut ? second_plane : ysVector{});
        const bool belt = p.id == "sevel.timingbelt" && scene.rig.available;
        renderer.setCadDeformation({pose.spring_delta,
            static_cast<float>(std::remainder(presented_phase*scene.rig.crank_teeth/360.,1.)),
            belt ? 1.f : 0.f,0});
        const auto first = renderer.drawCount();
        const auto &batches = scene.meshes.at(p.mesh);
        auto mesh_center = ysMath::Mul(ysMath::Add(lo,hi),ysMath::LoadScalar(.5f));
        mesh_center.w = 1;
        const auto eye_z = ysMath::MatMult(view,ysMath::MatMult(pose.model,mesh_center)).z;
        for (std::size_t i=0; i<batches.size(); ++i) {
            const auto &b = batches[i];
            auto color = p.id == selected ? ysVector{1,.76f,.19f,1} : p.colors[i];
            if (ghost.contains(p.group)) color.w *= .26f;
            const int layer = color.w < 1.f ? 100000+static_cast<int>(eye_z*1000) : 0;
            renderer.submitGeometry(nullptr,nullptr,b.first_vertex,b.first_index,b.triangles,
                pose.model,view,projection,color,Shaders::SceneStage,layer);
        }
        if (fill && intersects && !ghost.contains(p.group))
            renderer.endSectionPart(first,quad_vertex,quad_index,plane_model);
        if (fill && crosses_second && !ghost.contains(p.group))
            renderer.endSectionPart(first,quad_vertex,quad_index,second_model,true);
    }
    view_draws = static_cast<int>(renderer.drawCount());
    renderer.endFrame();
    renderer.profileScene(frame_start);
}

void SevelCadView::event(const SDL_Event &e) {
    if (e.type == SDL_EVENT_MOUSE_BUTTON_DOWN && e.button.button == SDL_BUTTON_LEFT) {
        pressed_x = e.button.x; pressed_y = e.button.y; dragged = false;
    }
    if (e.type == SDL_EVENT_MOUSE_WHEEL) {
        if (cut && (SDL_GetModState() & SDL_KMOD_SHIFT)) offset_mm += 2*e.wheel.y;
        else distance = std::clamp(distance*std::exp(-0.12f*e.wheel.y),radius*.12f,radius*12);
    }
    if (e.type == SDL_EVENT_MOUSE_MOTION && (e.motion.state & SDL_BUTTON_LMASK)) {
        dragged |= std::hypot(e.motion.x-pressed_x,e.motion.y-pressed_y) > 3;
        yaw -= 0.008f*e.motion.xrel;
        pitch = std::clamp(pitch+0.008f*e.motion.yrel,-1.56f,1.56f);
    }
    if (e.type == SDL_EVENT_MOUSE_BUTTON_UP && e.button.button == SDL_BUTTON_LEFT && !dragged) {
        auto *window = SDL_GetWindowFromID(e.button.windowID);
        const float scale = window ? SDL_GetWindowPixelDensity(window) : 1.f;
        select(e.button.x*scale,e.button.y*scale);
    }
    if (e.type == SDL_EVENT_MOUSE_MOTION && (e.motion.state & SDL_BUTTON_RMASK)) {
        const float dx = -e.motion.xrel*distance*.0015f, dy = e.motion.yrel*distance*.0015f;
        target.x += dx*std::cos(yaw)-dy*std::sin(yaw)*std::sin(pitch);
        target.y += dy*std::cos(pitch);
        target.z -= dx*std::sin(yaw)+dy*std::cos(yaw)*std::sin(pitch);
    }
    if (e.type == SDL_EVENT_KEY_DOWN && !e.key.repeat) {
        if (e.key.key == SDLK_O) orthographic = !orthographic;
        const auto key = e.key.key;
        if (key == SDLK_C) cut = !cut;
        if (key == SDLK_F) invert = !invert;
        if (key == SDLK_M) cut_moving = !cut_moving;
        if (key == SDLK_K) fill = !fill;
        if (key == SDLK_U && !uncut.erase(group)) uncut.insert(group);
        if (key == SDLK_B) {
            if (!second_cut) second_plane = clipPlane();
            second_cut = !second_cut;
        }
        if (key >= SDLK_1 && key <= SDLK_6) orientPlane(static_cast<int>(key-SDLK_1));
        if (key == SDLK_LEFTBRACKET) offset_mm -= 2;
        if (key == SDLK_RIGHTBRACKET) offset_mm += 2;
        if (key == SDLK_X || key == SDLK_Y || key == SDLK_Z) {
            const auto axis = key == SDLK_X ? ysMath::Constants::XAxis :
                              key == SDLK_Y ? ysMath::Constants::YAxis : ysMath::Constants::ZAxis;
            normal = ysMath::Normalize(ysMath::MatMult(ysMath::RotationTransform(axis,
                (e.key.mod & SDL_KMOD_SHIFT) ? -.1f : .1f), normal));
            cut = true;
        }
        if (key == SDLK_TAB && !groups.empty()) {
            auto it = std::find(groups.begin(),groups.end(),group);
            group = it == groups.end() || ++it == groups.end() ? groups.front() : *it;
        }
        if (key == SDLK_H && !hidden.erase(group)) hidden.insert(group);
        if (key == SDLK_G && !ghost.erase(group)) ghost.insert(group);
        if (key == SDLK_E) explode_mm = std::fmod(explode_mm+25.f,125.f);
        if (key == SDLK_I) {
            if (!inspect) inspected_phase = presented_phase;
            inspect = !inspect;
            playing = false;
        }
        if (inspect && key == SDLK_SPACE) playing = !playing;
        if (inspect && (key == SDLK_LEFT || key == SDLK_RIGHT)) {
            inspected_phase += (key == SDLK_LEFT ? -1 : 1)*((e.key.mod & SDL_KMOD_SHIFT) ? 90 : 1);
            playing = false;
        }
        if (inspect && key == SDLK_MINUS) speed_deg_s = std::max(1.,speed_deg_s/2);
        if (inspect && key == SDLK_EQUALS) speed_deg_s = std::min(720.,speed_deg_s*2);
        if (key == SDLK_J && !selected.empty()) isolate = !isolate;
        if (key == SDLK_RETURN && !selected.empty()) {
            for (const auto &p : scene.parts) if (p.id == selected) {
                const auto &[lo,hi] = scene.mesh_bounds.at(p.mesh);
                auto center = ysMath::Mul(ysMath::Add(lo,hi),ysMath::LoadScalar(.5f));
                center.w = 1;
                target = ysMath::MatMult(partPose(p).model,center);
                distance = std::max(.012f,1.7f*ysMath::Magnitude(ysMath::Sub(hi,lo)).x);
                break;
            }
        }
        if (key == SDLK_F1 || key == SDLK_F2 || key == SDLK_F3 || key == SDLK_F4) {
            const float half_pi = ysMath::Constants::PI/2;
            yaw = key == SDLK_F2 ? 2*half_pi : key == SDLK_F3 ? half_pi : 0;
            pitch = key == SDLK_F4 ? half_pi : 0;
            if (e.key.mod & SDL_KMOD_SHIFT) {
                if (key == SDLK_F3) yaw = -yaw;
                if (key == SDLK_F4) pitch = -pitch;
            }
        }
        if (e.key.key == SDLK_HOME) {
            target = ysMath::Mul(ysMath::Add(scene.upper,scene.lower),ysMath::LoadScalar(.5f));
            distance = radius*2.55f;
            yaw = -.68f;
            pitch = .32f;
        }
    }
}
} // namespace lab
