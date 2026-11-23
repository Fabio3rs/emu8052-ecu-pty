#include "CadManifest.hpp"

#include <algorithm>
#include <numbers>

namespace lab::cad {

CadRig read_rig(const Json &runtime) {
    require(real(field(runtime,"schema_version")) == 1, "unsupported runtime schema");
    const auto &source = field(runtime,"rig");
    CadRig r;
    r.radius = real(field(source,"radius_m"));
    r.rod = real(field(source,"rod_m"));
    require(r.radius > 0 && r.rod > r.radius && r.rod < 1, "slider-crank dimensions");
    const auto phases = array<4>(field(source,"compression_tdc_deg"));
    std::copy(phases.begin(),phases.end(),r.compression.begin());
    require(phases == std::array{0.f,540.f,180.f,360.f}, "compression phases");
    r.cam_phase = real(field(source,"cam_phase_deg"));
    const auto &v = field(source,"valves");
    r.cam_height = real(field(v,"cam_height_mm"))*.001;
    r.checking_lash = real(field(v,"checking_lash_mm"))*.001;
    for (std::size_t i=0; i<2; ++i) {
        std::string kind = i == 0 ? "intake" : "exhaust";
        auto events = array<2,double>(field(v,kind+"_events_deg"));
        r.opening[i] = events[0];
        r.closing[i] = events[1];
        r.lash[i] = real(field(v,kind+"_lash_mm"))*.001;
        require(events[1] > events[0] && events[1]-events[0] < 720 &&
                r.lash[i] >= 0 && r.cam_height > r.checking_lash, "valve profile");
    }
    const auto &springs = field(source,"springs");
    for (const std::string kind : {"inner","outer"}) {
        auto &s = r.springs[kind];
        s.seat = real(field(springs,kind+"_spring_seat_z_mm"))*.001;
        s.top = real(field(springs,"retainer_bottom_z_mm"))*.001;
        s.wire = real(field(springs,kind+"_spring_wire_radius_mm"))*.001;
        s.turns = real(field(springs,kind+"_spring_turns"));
        require(s.wire > 0 && s.turns > 0 && s.top-s.seat > 2*s.wire+r.cam_height, "spring dimensions");
    }
    r.crank_teeth = static_cast<int>(real(field(source,"crank_teeth")));
    r.pitch_mm = real(field(source,"pitch_mm"));
    require(r.crank_teeth > 0 && r.pitch_mm > 0, "invalid timing pitch");
    double offset = 0;
    for (const auto &row : field(source,"belt_segments").array) {
        CadRig::BeltSegment b;
        const auto &points = field(row,"points").array;
        require(points.size() == 2, "belt endpoints");
        b.start = array<2,double>(points.front());
        b.end = array<2,double>(points.back());
        b.offset = offset;
        if (string(field(row,"kind")) == "arc") {
            b.center = array<2,double>(field(row,"center"));
            b.radius = real(field(row,"radius"));
            b.angle = real(field(row,"start"));
            b.sweep = real(field(row,"sweep"));
            b.length = b.radius*std::abs(b.sweep);
        } else {
            require(string(field(row,"kind")) == "line", "unknown belt segment");
            b.length = std::hypot(b.end[0]-b.start[0],b.end[1]-b.start[1]);
        }
        require(b.length > 0 && b.length < 1000, "belt segment length");
        offset += b.length;
        r.belt.push_back(b);
    }
    require(r.belt.size() == 8, "timing belt path");
    r.available = true;
    return r;
}

void weight_spring(SevelCadScene &scene, const CadPart &p) {
    const auto &s = scene.rig.springs.at(p.spring);
    const double height = s.top - s.seat - 2*s.wire - cad_valve_lift(scene.rig,p,0);
    for (const auto &b : scene.meshes.at(p.mesh)) {
        for (int i=0; i<3*b.triangles; ++i) {
            auto &v = scene.vertices[static_cast<std::size_t>(b.first_vertex) +
                scene.indices[static_cast<std::size_t>(b.first_index+i)]];
            const double estimate = s.turns*(static_cast<double>(v.Pos.y)-s.seat-s.wire)/height;
            const double fraction = std::atan2(-static_cast<double>(v.Pos.z),static_cast<double>(v.Pos.x))/(2*std::numbers::pi);
            const double turns = fraction+std::round(estimate-fraction);
            v.TexCoord.x = static_cast<float>(std::clamp(turns/s.turns,0.,1.));
        }
    }
}
} // namespace lab::cad
