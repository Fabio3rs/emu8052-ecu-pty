#pragma once

#include "lab/SevelCadScene.hpp"
#include <set>
#include <future>

class SdlGpuRenderer;
union SDL_Event;

namespace lab {

struct CadViewSettings {
    ysVector target;
    float yaw = -0.68f, pitch = 0.32f, distance = 1;
    bool orthographic = false, cut = false, invert = false, cut_moving = false, fill = true;
    bool inspect = false, isolate = false;
    bool second_cut = false;
    float offset_mm = 0, explode_mm = 0;
    double inspected_phase = 0, speed_deg_s = 30;
    ysVector normal{0,0,1};
    ysVector second_plane{1,0,0,0}; // world unit normal and offset in metres
    std::string group = "block", selected;
    std::set<std::string> hidden, ghost, uncut;
};

class SevelCadView : public CadViewSettings {
public:
    void load(SdlGpuRenderer &renderer, const std::filesystem::path &path);
    void requestReload(const std::filesystem::path &path);
    void pollReload(SdlGpuRenderer &renderer);
    void draw(SdlGpuRenderer &renderer, int width, int height, double phase_deg, int x=0, int y=0);
    void event(const SDL_Event &event);
    void updatePhase(double phase_deg);
    void applyPreset(const std::filesystem::path &path);
    void savePreset(const std::filesystem::path &path) const;
    std::string status() const;
    ysVector clipPlane() const;
    void orientPlane(int preset);
    void select(float x, float y);
    SevelCadScene scene;
    float radius = 0.5f;
    bool cap_supported = false, playing = false;
    std::string reload_status;
    double presented_phase = 0;
    std::vector<std::string> groups;
    int quad_vertex{}, quad_index{}, last_width{}, last_height{}, view_draws{};
    float pressed_x{}, pressed_y{};
    bool dragged = false;
    std::uint64_t last_time{};
    ysMatrix last_view{}, last_projection{};
    CadPose partPose(const CadPart &p) const;
private:
    void install(SdlGpuRenderer &renderer,SevelCadScene candidate,double decode_ms);
    std::future<SevelCadScene> pending;
    std::uint64_t reload_start{};
};

} // namespace lab
