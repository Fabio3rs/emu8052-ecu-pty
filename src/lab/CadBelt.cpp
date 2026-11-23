#include "CadManifest.hpp"

#include <algorithm>
#include <limits>
#include <numbers>

namespace lab::cad {

// Arc length on the CAD pitch path, with the idler's negative wrap.
void weight_belt(SevelCadScene &scene, const CadPart &p) {
    const auto &rig = scene.rig;
    for (const auto &batch : scene.meshes.at(p.mesh)) {
        for (int i=0; i<3*batch.triangles; ++i) {
            auto &v = scene.vertices[static_cast<std::size_t>(batch.first_vertex) +
                scene.indices[static_cast<std::size_t>(batch.first_index+i)]];
            const auto world = ysMath::MatMult(p.rest,v.Pos);
            const double y = -1000.*static_cast<double>(world.z), z = 1000.*static_cast<double>(world.y);
            double best = std::numeric_limits<double>::infinity();
            for (const auto &s : rig.belt) {
                double fraction, cy, cz;
                if (s.radius > 0) {
                    const double angle = std::atan2(z-s.center[1],y-s.center[0]);
                    const double midpoint = s.angle+.5*s.sweep;
                    const double delta = std::remainder(angle-midpoint,2*std::numbers::pi);
                    fraction = std::clamp(.5+delta/s.sweep,0.,1.);
                    cy = s.center[0]+s.radius*std::cos(s.angle+fraction*s.sweep);
                    cz = s.center[1]+s.radius*std::sin(s.angle+fraction*s.sweep);
                } else {
                    const double dy = s.end[0]-s.start[0], dz = s.end[1]-s.start[1];
                    fraction = std::clamp(((y-s.start[0])*dy+(z-s.start[1])*dz)/(s.length*s.length),0.,1.);
                    cy = s.start[0]+fraction*dy;
                    cz = s.start[1]+fraction*dz;
                }
                const double distance = std::hypot(cy-y,cz-z);
                if (distance < best) {
                    best = distance;
                    v.TexCoord.y = static_cast<float>((s.offset+fraction*s.length)/rig.pitch_mm);
                }
            }
        }
    }
}
} // namespace lab::cad
