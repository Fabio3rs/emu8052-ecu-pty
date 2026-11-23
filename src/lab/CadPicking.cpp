#include "lab/SevelCadView.hpp"

#include <algorithm>
#include <limits>

namespace lab {
namespace {
bool hits_bounds(ysVector o, ysVector d, ysVector low, ysVector high, float maximum) {
    float near = 0, far = maximum;
    auto slab = [&](float origin,float direction,float a,float b) {
        if (std::abs(direction)<1e-8f) return origin >= a && origin <= b;
        const float t1 = (a-origin)/direction, t2 = (b-origin)/direction;
        near = std::max(near,std::min(t1,t2)); far = std::min(far,std::max(t1,t2));
        return near <= far;
    };
    return slab(o.x,d.x,low.x,high.x) && slab(o.y,d.y,low.y,high.y) && slab(o.z,d.z,low.z,high.z);
}

float hit_triangle(ysVector origin, ysVector dir, ysVector a, ysVector b, ysVector c) {
    const auto ab = ysMath::Sub(b,a), ac = ysMath::Sub(c,a);
    const auto h = ysMath::Cross(dir,ac);
    const float det = ysMath::Dot(ab,h).x;
    if (std::abs(det)<1e-12f) return -1;
    const auto offset = ysMath::Sub(origin,a);
    const float u = ysMath::Dot(offset,h).x/det;
    const auto q = ysMath::Cross(offset,ab);
    const float v = ysMath::Dot(dir,q).x/det;
    return u >= 0 && v >= 0 && u+v <= 1 ? ysMath::Dot(ac,q).x/det : -1;
}
}

void SevelCadView::select(float x,float y) {
    if (!last_width || !last_height) return;
    const float sx = 2*x/static_cast<float>(last_width)-1, sy = 1-2*y/static_cast<float>(last_height);
    const ysVector back{last_view.m[2][0],last_view.m[2][1],last_view.m[2][2]};
    const auto pixel = ysMath::MatMult(ysMath::Transpose(last_view),
        ysVector{sx/last_projection.m[0][0],sy/last_projection.m[1][1],0,0});
    auto origin = ysMath::Add(target,ysMath::Mul(back,ysMath::LoadScalar(distance)));
    if (orthographic) origin = ysMath::Add(origin,pixel);
    auto dir = ysMath::Normalize(ysMath::Sub(orthographic ? ysVector{} : pixel,back));
    origin.w = 1; dir.w = 0;
    float best = std::numeric_limits<float>::infinity();
    std::string closest;
    const auto plane = clipPlane();
    const float plane_distance = ysMath::Dot(plane,origin).x+plane.w;
    const float plane_slope = ysMath::Dot(plane,dir).x;
    const float plane_t = std::abs(plane_slope)>1e-8f ? -plane_distance/plane_slope : -1;
    const float d2 = ysMath::Dot(second_plane,origin).x+second_plane.w;
    const float slope2 = ysMath::Dot(second_plane,dir).x;
    const float t2 = std::abs(slope2)>1e-8f ? -d2/slope2 : -1;
    for (const auto &p : scene.parts) {
        if (hidden.contains(p.group) || (isolate && p.id != selected)) continue;
        const auto pose = partPose(p);
        const auto &m = pose.model;
        const auto rotation = ysMath::Transpose(m);
        auto o = ysMath::MatMult(rotation,ysMath::Sub(origin,{m.m[0][3],m.m[1][3],m.m[2][3],1}));
        auto d = ysMath::MatMult(rotation,dir);
        auto [low,high] = scene.mesh_bounds.at(p.mesh);
        low.y += std::min(0.f,pose.spring_delta); high.y += std::max(0.f,pose.spring_delta);
        if (!hits_bounds(o,d,low,high,best)) continue;
        const bool clipped = cut && !uncut.contains(p.group) && (p.motion == "fixed" || cut_moving);
        std::vector<float> crossings;
        for (const auto &b : scene.meshes.at(p.mesh)) {
            auto vertex = [&](int i) {
                const auto &v = scene.vertices[static_cast<std::size_t>(b.first_vertex) +
                    scene.indices[static_cast<std::size_t>(b.first_index+i)]];
                auto point = v.Pos;
                point.y += pose.spring_delta*v.TexCoord.x;
                return point;
            };
            for (int i=0; i<3*b.triangles; i+=3) {
                const float t = hit_triangle(o,d,vertex(i),vertex(i+1),vertex(i+2));
                if (t <= 0) continue;
                if (clipped && fill) crossings.push_back(t);
                if (t < best && (!clipped || (plane_distance+t*plane_slope >= 0 &&
                                              (!second_cut || d2+t*slope2 >= 0)))) {
                    best = t; closest = p.id;
                }
            }
        }
        if (clipped && fill && cap_supported && !ghost.contains(p.group)) {
            std::sort(crossings.begin(),crossings.end());
            auto end = std::unique(crossings.begin(),crossings.end(),[](float a,float b){return std::abs(a-b)<1e-7f;});
            auto pick_cap = [&](float t) {
                if (t <= 0 || t >= best) return;
                const auto start = std::upper_bound(crossings.begin(),end,t);
                if ((end-start)%2) { best = t; closest = p.id; }
            };
            if (!second_cut || d2+plane_t*slope2 >= 0) pick_cap(plane_t);
            if (second_cut && plane_distance+t2*plane_slope >= 0) pick_cap(t2);
        }
    }
    if (!isolate) selected = closest;
    if (!selected.empty()) {
        for (const auto &p : scene.parts) if (p.id == selected) { group = p.group; break; }
        std::printf("[LAB-CAD] picked=%s distance_m=%.6f\n",selected.c_str(),static_cast<double>(best));
    }
}
} // namespace lab
