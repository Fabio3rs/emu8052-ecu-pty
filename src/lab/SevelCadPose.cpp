#include "lab/SevelCadScene.hpp"
#include "CadManifest.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>
#include <sstream>

namespace lab {
namespace {
constexpr double radians = std::numbers::pi / 180.0;
}

double cad_valve_lift(const CadRig &rig, const CadPart &part, double phase_deg) {
    const std::size_t i = part.valve == "intake" ? 0 : 1;
    const double cycle = phase_deg - rig.compression.at(static_cast<std::size_t>(part.cylinder-1));
    const double center = (rig.opening[i]+rig.closing[i])/2;
    const double half_window = (rig.closing[i]-rig.opening[i])*radians/4;
    const double offset = (rig.cam_height-rig.checking_lash)/(1-std::cos(half_window));
    const double angle = (cycle+2*rig.cam_phase-center)*radians/2;
    // CAD smoothing lies entirely below the running lash of both valves.
    return std::max(0.,rig.cam_height+offset*(std::cos(angle)-1)-rig.lash[i]);
}

CadPose cad_pose(const CadRig &rig, const CadPart &part, double phase_deg) {
    CadPose pose{part.rest,0};
    if (!rig.available || !std::isfinite(phase_deg) || part.motion == "fixed")
        return pose;
    if (part.motion == "valve" || part.motion == "spring") {
        const auto delta = static_cast<float>(cad_valve_lift(rig,part,0)-cad_valve_lift(rig,part,phase_deg));
        if (part.motion == "valve")
            pose.model.m[1][3] += delta;
        else
            pose.spring_delta = delta;
        return pose;
    }
    double angle = phase_deg*part.ratio*radians;
    if (part.motion == "rod" || part.motion == "piston") {
        const double offset = rig.compression.at(static_cast<std::size_t>(part.cylinder-1));
        const double phi = (phase_deg-offset)*radians;
        const double lateral = rig.radius*std::sin(phi);
        const double rise = std::sqrt(rig.rod*rig.rod-lateral*lateral);
        pose.model.m[1][3] += static_cast<float>(rig.radius*(std::cos(phi)-std::cos(offset*radians)));
        if (part.motion == "piston") {
            pose.model.m[1][3] += static_cast<float>(rise-rig.rod);
            return pose;
        }
        pose.model.m[2][3] += static_cast<float>(lateral);
        angle = std::atan2(-lateral,rise);
    }
    const auto rotation = ysMath::RotationTransform(ysMath::Constants::XAxis,
        static_cast<float>(std::remainder(angle,2*std::numbers::pi)));
    pose.model = ysMath::MatMult(pose.model,rotation);
    return pose;
}

void validate_cad_replacement(const SevelCadScene &active, const SevelCadScene &candidate) {
    cad::require(active.datum_hash == candidate.datum_hash && active.rig == candidate.rig,
                 "incompatible datum or kinematics");
    std::map<std::string,const CadPart*> by_id;
    for (const auto &p : candidate.parts) by_id.emplace(p.id,&p);
    for (const auto &old : active.parts) {
        auto it = by_id.find(old.id);
        if (it == by_id.end()) continue;
        const auto &p = *it->second;
        cad::require(old.motion == p.motion && old.group == p.group && old.cylinder == p.cylinder &&
                     old.ratio == p.ratio && old.valve == p.valve && old.spring == p.spring,
                     "rigging changed for " + p.id);
        for (int row=0; row<4; ++row) for (int col=0; col<4; ++col)
            cad::require(std::abs(old.rest.m[row][col]-p.rest.m[row][col])<1e-7f,
                         "rest transform changed for " + p.id);
    }
}

std::string cad_pose_hash(const SevelCadScene &scene, double phase_deg) {
    std::map<std::string,CadPose> poses;
    for (const auto &p : scene.parts) poses.emplace(p.id,cad_pose(scene.rig,p,phase_deg));
    std::ostringstream values;
    for (const auto &[id,pose] : poses) {
        values << id;
        for (const auto &row : pose.model.m) for (float n : row)
            values << ' ' << std::llround(static_cast<double>(n)*1e7);
        values << ' ' << std::llround(static_cast<double>(pose.spring_delta)*1e7) << '\n';
    }
    values << std::llround(std::remainder(phase_deg*scene.rig.crank_teeth/360.,1.)*1e7);
    return cad::digest(values.str());
}
} // namespace lab
