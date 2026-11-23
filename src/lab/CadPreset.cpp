#include "lab/SevelCadView.hpp"
#include "CadManifest.hpp"
#include "lab/RunSnapshot.hpp"

#include <fstream>
#include <iomanip>

namespace lab {

void SevelCadView::applyPreset(const std::filesystem::path &path) {
    using namespace cad;
    const auto j = parse_json(read_asset(path,65536));
    require(j && number(field(*j,"version")) == 1, "unsupported camera preset");
    CadViewSettings s = *this;
    auto scalar = [&](const char *key, auto &value, float lo, float hi) {
        if (auto *item = j->get(key)) {
            const float n = number(*item);
            require(n >= lo && n <= hi,key);
            value = static_cast<std::remove_reference_t<decltype(value)>>(n);
        }
    };
    scalar("yaw_rad",s.yaw,-1000,1000);
    scalar("pitch_rad",s.pitch,-1.571f,1.571f);
    float distance_mm = 1000*s.distance;
    scalar("distance_mm",distance_mm,1,20000);
    s.distance = distance_mm*.001f;
    scalar("offset_mm",s.offset_mm,-10000,10000);
    scalar("explode_mm",s.explode_mm,0,500);
    scalar("phase_deg",s.inspected_phase,-1e8f,1e8f);
    scalar("speed_deg_s",s.speed_deg_s,1,720);
    auto flag = [&](const char *key, bool &b) {
        if (auto *v = j->get(key)) {
            require(v->type == Json::Type::Bool,key);
            b = v->boolean;
        }
    };
    flag("ortho",s.orthographic); flag("cut",s.cut); flag("invert",s.invert);
    flag("second_cut",s.second_cut);
    if (auto *v = j->get("second_plane_mm")) {
        const auto [x,y,z,w] = array<4>(*v);
        require(std::abs(x*x+y*y+z*z-1)<.001f,"second plane unit normal");
        s.second_plane = {x,y,z,w*.001f};
    }
    flag("cut_moving",s.cut_moving); flag("fill",s.fill); flag("inspect",s.inspect); flag("isolate",s.isolate);
    if (auto *v = j->get("target_mm")) {
        const auto [x,y,z] = array<3>(*v);
        s.target = {x*.001f,y*.001f,z*.001f};
    }
    if (auto *v = j->get("normal")) {
        const auto [x,y,z] = array<3>(*v);
        require(std::abs(x*x+y*y+z*z-1) < .001f,"unit plane normal");
        s.normal = ysMath::Normalize({x,y,z});
    }
    auto set = [&](const char *key, std::set<std::string> &values) {
        if (const auto *v = j->get(key)) {
            require(v->is_array(),key);
            values.clear();
            for (const auto &entry : v->array) values.insert(string(entry));
        }
    };
    set("hidden",s.hidden); set("ghost",s.ghost); set("uncut",s.uncut);
    if (const auto *v = j->get("selected")) s.selected = v->string;
    if (const auto *v = j->get("group")) s.group = string(*v);
    static_cast<CadViewSettings&>(*this) = std::move(s);
    playing = false;
}

void SevelCadView::savePreset(const std::filesystem::path &path) const {
    std::ofstream out(path);
    out << std::setprecision(10) << std::boolalpha << "{\"version\":1,\"target_mm\":["
        << target.x*1000 << ',' << target.y*1000 << ',' << target.z*1000
        << "],\"distance_mm\":" << distance*1000 << ",\"yaw_rad\":" << yaw << ",\"pitch_rad\":" << pitch
        << ",\"normal\":[" << normal.x << ',' << normal.y << ',' << normal.z
        << "],\"ortho\":" << orthographic << ",\"cut\":" << cut << ",\"invert\":" << invert
        << ",\"cut_moving\":" << cut_moving << ",\"fill\":" << fill << ",\"inspect\":" << inspect
        << ",\"phase_deg\":" << inspected_phase << ",\"speed_deg_s\":" << speed_deg_s
        << ",\"offset_mm\":" << offset_mm << ",\"explode_mm\":" << explode_mm
        << ",\"isolate\":" << isolate << ",\"selected\":" << detail::json_string(selected)
        << ",\"group\":" << detail::json_string(group);
    auto set = [&](const char *name, const auto &values) {
        out << ",\"" << name << "\":[";
        for (auto it=values.begin(); it!=values.end(); ++it)
            out << (it == values.begin() ? "" : ",") << detail::json_string(*it);
        out << ']';
    };
    out << ",\"second_cut\":" << second_cut << ",\"second_plane_mm\":[" << second_plane.x << ','
        << second_plane.y << ',' << second_plane.z << ',' << second_plane.w*1000 << ']';
    set("hidden",hidden); set("ghost",ghost); set("uncut",uncut);
    out << "}\n";
    out.close();
    cad::require(out.good(),"cannot save " + path.string());
}
} // namespace lab
