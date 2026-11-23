#include "lab/SevelCadView.hpp"
#include "CadManifest.hpp"
#include "lab/RunSnapshot.hpp"

#include <fstream>
#include <iomanip>

namespace lab {

ysVector SevelCadView::clipPlane() const {
    const float side = invert ? -1.f : 1.f;
    return {side*normal.x,side*normal.y,side*normal.z,-side*offset_mm*.001f};
}

void SevelCadView::orientPlane(int preset) {
    cut = true;
    normal = preset == 0 ? ysVector{0,0,1} : preset == 5 ? ysVector{0,1,0} : ysVector{1,0,0};
    offset_mm = 0;
    if (preset >= 1 && preset <= 4) {
        for (const auto &p : scene.parts)
            if (p.cylinder == preset && p.motion == "piston") {
                offset_mm = p.rest.m[0][3]*1000;
                break;
            }
    }
}

CadPose SevelCadView::partPose(const CadPart &p) const {
    auto pose = cad_pose(scene.rig,p,presented_phase);
    if (explode_mm != 0) {
        const auto &[low,high] = scene.mesh_bounds.at(p.mesh);
        auto local = ysMath::Mul(ysMath::Add(low,high),ysMath::LoadScalar(.5f));
        local.w = 1;
        auto center = ysMath::MatMult(p.rest,local);
        auto middle = ysMath::Mul(ysMath::Add(scene.lower,scene.upper),ysMath::LoadScalar(.5f));
        auto direction = ysMath::Normalize(ysMath::Sub(center,middle));
        pose.model.m[0][3] += direction.x*explode_mm*.001f;
        pose.model.m[1][3] += direction.y*explode_mm*.001f;
        pose.model.m[2][3] += direction.z*explode_mm*.001f;
    }
    return pose;
}

std::string SevelCadView::status() const {
    std::ostringstream s;
    s << "SEVEL 3D CAD | " << (inspect ? "INSPECT" : scene.rig.available ? "LIVE" : "STATIC")
      << " " << std::fixed << std::setprecision(1) << presented_phase << " deg | " << group;
    if (cut) s << " | " << offset_mm << " mm " << (fill && cap_supported ? "section" : "clip only");
    if (!selected.empty()) {
        for (const auto &p : scene.parts) if (p.id == selected) {
            s << " | " << p.label << " (" << p.id << ") " << p.motion;
            if (p.cylinder) s << " C" << p.cylinder;
            s << " | " << p.evidence;
            break;
        }
    }
    return s.str();
}

} // namespace lab
