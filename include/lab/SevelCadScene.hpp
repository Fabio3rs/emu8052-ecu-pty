#pragma once

#include "render_math.h"

#include <cstdint>
#include <array>
#include <filesystem>
#include <map>
#include <string>
#include <vector>

namespace lab {

struct CadBatch {
    int first_vertex{}, first_index{}, triangles{};
    std::string name;
};

struct CadPart {
    std::string id, label, mesh, group, motion, valve, spring, evidence;
    int cylinder{};
    double ratio{};
    ysMatrix rest = ysMath::LoadIdentity();
    std::vector<ysVector> colors; // Ordered like the referenced geometry's batches.
};

struct CadRig {
    bool available{};
    double radius{}, rod{}, cam_phase{}, cam_height{}, checking_lash{};
    std::array<double, 4> compression{};
    // Intake then exhaust, in crank degrees and metres.
    std::array<double, 2> opening{}, closing{}, lash{};
    struct Spring {
        double seat{}, top{}, wire{}, turns{};
        bool operator==(const Spring &) const = default;
    };
    std::map<std::string,Spring> springs;
    int crank_teeth{};
    double pitch_mm{};
    struct BeltSegment {
        std::array<double,2> start{}, end{}, center{};
        double radius{}, angle{}, sweep{}, length{}, offset{};
        bool operator==(const BeltSegment &) const = default;
    };
    std::vector<BeltSegment> belt;
    bool operator==(const CadRig &) const = default;
};

struct SevelCadScene {
    CadRig rig;
    std::filesystem::path manifest_path;
    std::string revision, datum_hash;
    std::vector<EngineSimVertex> vertices;
    std::vector<std::uint16_t> indices;
    std::map<std::string, std::vector<CadBatch>> meshes;
    std::map<std::string,std::pair<ysVector,ysVector>> mesh_bounds;
    std::vector<CadPart> parts;
    ysVector lower, upper;
};

// Constructs a candidate in isolation. Errors identify the offending file or field.
SevelCadScene load_cad_scene(std::filesystem::path path);
struct CadPose { ysMatrix model; float spring_delta{}; };
CadPose cad_pose(const CadRig &rig, const CadPart &part, double phase_deg);
double cad_valve_lift(const CadRig &rig, const CadPart &part, double phase_deg);
void validate_cad_replacement(const SevelCadScene &active, const SevelCadScene &candidate);
std::string cad_pose_hash(const SevelCadScene &scene, double phase_deg);

} // namespace lab
