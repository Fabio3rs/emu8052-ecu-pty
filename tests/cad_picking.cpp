#include "lab/SevelCadView.hpp"

#include <iostream>

// The fixture places a thin box inside a larger box, both under the same pixel.
// Use the production world-space ray and section tests with a known projection.
int main() {
    lab::SevelCadView view;
    auto &scene = view.scene;
    for (float z : {-0.08f,0.08f}) for (float y : {-0.04f,0.04f}) for (float x : {-0.05f,0.05f})
        scene.vertices.push_back({{x,y,z,1},{0,0,1,0},{}});
    scene.indices = {0,2,3,0,3,1,4,5,7,4,7,6,0,1,5,0,5,4,2,6,7,2,7,3,0,4,6,0,6,2,1,3,7,1,7,5};
    scene.meshes["cube"].push_back({0,0,12,"solid"});
    scene.mesh_bounds["cube"] = {{-.05f,-.04f,-.08f},{.05f,.04f,.08f}};
    for (auto id : {"inner","outer"}) {
        lab::CadPart p;
        p.id = p.group = id;
        p.mesh = "cube";
        p.motion = "fixed";
        p.rest = ysMath::LoadIdentity();
        if (p.id == "inner") p.rest.m[2][3] = -.085f;
        scene.parts.push_back(p);
    }
    view.target = {};
    view.distance = 1;
    view.last_width = view.last_height = 200;
    view.last_view = view.last_projection = ysMath::LoadIdentity();
    view.orthographic = view.cap_supported = true;
    auto expect = [&](const char *id,float x=101,float y=99) {
        view.select(x,y);
        if (view.selected == id) return true;
        std::cerr << "Expected " << id << ", picked " << view.selected << '\n';
        return false;
    };
    if (!expect("outer")) return 1;
    view.hidden.insert("outer");
    if (!expect("inner")) return 1;
    view.hidden.clear();
    view.cut = view.invert = true;
    if (!expect("outer")) return 1; // cap at z=0 lies in front of inner box
    view.fill = false;
    if (!expect("inner")) return 1;
    view.fill = true;
    view.ghost.insert("outer");
    if (!expect("inner")) return 1;
    view.ghost.clear();
    view.second_cut = true;
    view.second_plane = {1,0,0,-.02f};
    if (!expect("") || !expect("outer",103,99)) return 1;
    view.orthographic = false;
    return expect("outer",103,99) && expect("",190,140) ? 0 : 1;
}
