#include "CadManifest.hpp"

#include <algorithm>
#include <limits>
#include <set>

namespace lab {
using namespace cad;

static void validate_members(const Json &node) {
    std::set<std::string_view> keys;
    for (const auto &member : node.object) {
        require(keys.insert(member.key).second,"duplicate JSON key " + member.key);
        validate_members(member);
    }
    for (const auto &item : node.array) validate_members(item);
}

static std::string legacy_group(const Json &row, const CadPart &p) {
    if (const auto *explicit_group = row.get("scene_group"))
        return string(*explicit_group);
    const auto &name = string(field(row,"source_object"));
    for (const auto &[token, group] : {
        std::pair{"Spark","spark_plugs"}, {"IntakeManifold","intake"}, {"ExhaustManifold","exhaust"},
        {"OilPan","oil_pan"}, {"OilDrain","oil_pan"}, {"ValveCover","cover"}, {"OilFiller","cover"},
        {"Head","head"}, {"Carrier","head"}, {"Block","block"}, {"CorePlug","block"}, {"MainCap","block"},
        {"Timing","timing"}, {"Sprocket","timing"}, {"Tensioner","timing"}})
        if (name.find(token) != std::string::npos)
            return group;
    return p.motion == "fixed" ? "accessories" : p.motion;
}

SevelCadScene load_cad_scene(std::filesystem::path path) {
    std::string expected;
    if (std::filesystem::is_directory(path)) {
        if (std::filesystem::exists(path/"current.json")) {
            auto pointer = parse_json(read_asset(path/"current.json",4096));
            require(pointer && number(field(*pointer,"schema_version")) == 1, "invalid revision pointer");
            expected = string(field(*pointer,"asset_revision"));
            require(expected.size() == 64 && expected.find_first_not_of("0123456789abcdef") == expected.npos,
                    "invalid revision digest");
            const auto revision = std::filesystem::canonical(path/expected);
            require(revision.parent_path() == std::filesystem::canonical(path), "revision outside package");
            path = revision;
        }
        path /= "parts_manifest.json";
    }
    SevelCadScene scene;
    scene.manifest_path = std::filesystem::canonical(path);
    require(scene.manifest_path.parent_path() == std::filesystem::weakly_canonical(
            std::filesystem::absolute(path).parent_path()),"manifest outside package");
    auto bytes = read_asset(scene.manifest_path, 16u*1024*1024);
    scene.revision = digest(bytes);
    require(expected.empty() || expected == scene.revision, "manifest SHA-256 mismatch");
    const auto parsed = parse_json(bytes);
    require(parsed.has_value(), "invalid JSON in " + path.string());
    const auto &root = *parsed;
    validate_members(root);
    require(string(field(root,"schema")) == "sevel.parts.v1", "unsupported manifest schema");
    require(string(field(field(root,"units"),"length")) == "m" &&
            string(field(field(root,"units"),"angle")) == "rad" &&
            number(field(root,"theta_deg")) == 0, "unit or zero phase mismatch");
    require(string(field(root,"theta_zero")) == "C1 compression TDC", "phase origin");
    require(string(field(field(root,"units"),"time")) == "s", "time unit");
    const auto &engine = field(root,"root");
    require(string(field(engine,"id")) == "engine_root" && field(engine,"parent_id").type == Json::Type::Null &&
            array<3>(field(engine,"translation_m")) == std::array{0.f,0.f,0.f} &&
            array<4>(field(engine,"rotation_xyzw")) == std::array{0.f,0.f,0.f,1.f}, "engine root transform");
    if (auto *generator = root.get("generator"))
        scene.datum_hash = string(field(*generator,"datum_sha256"));
    if (auto *runtime = root.get("runtime"))
        scene.rig = read_rig(*runtime);
    load_meshes(scene, field(root,"meshes"));
    std::map<std::string,ysVector> materials;
    for (const auto &m : field(root,"materials").object) {
        const auto [r,g,b] = array<3>(field(m,"rgb"));
        float a = number(field(m,"opacity"));
        require(std::min({r,g,b,a}) >= 0 && std::max({r,g,b,a}) <= 1, "invalid color");
        require(materials.emplace(m.key, ysVector{r,g,b,a}).second, "duplicate material");
    }
    const auto &rows = field(root,"parts");
    require(rows.is_array() && !rows.array.empty() && rows.array.size() <= 8192, "part count");
    std::set<std::string> ids;
    scene.lower = {10,10,10};
    scene.upper = {-10,-10,-10};
    for (const auto &row : rows.array) {
        CadPart p;
        p.id = string(field(row,"id"));
        require(ids.insert(p.id).second, "duplicate PartId " + p.id);
        require(string(field(row,"parent_id")) == "engine_root", "invalid parent " + p.id);
        p.label = string(field(row,"display_label"));
        p.motion = string(field(row,"motion_type"));
        p.mesh = string(field(row,"mesh_id"));
        p.group = legacy_group(row,p);
        const auto &cyl = field(row,"cylinder_id");
        if (cyl.type != Json::Type::Null) {
            const auto id = number(cyl);
            require(id >= 1 && id <= 4 && std::trunc(id) == id, "invalid cylinder " + p.id);
            p.cylinder = static_cast<int>(id);
        }
        const auto &ratio = field(row,"angular_ratio_to_crank");
        if (ratio.type != Json::Type::Null) p.ratio = real(ratio);
        p.valve = field(row,"valve_kind").string;
        p.spring = field(row,"spring_kind").string;
        static const std::set<std::string> motions{"fixed","piston","rod","valve","spring","cam","crank","tensioner","aux"};
        require(motions.contains(p.motion), "unknown motion " + p.id);
        if (p.motion == "valve" || p.motion == "spring")
            require(p.valve == "exhaust" || p.valve == "intake", "valve kind " + p.id);
        if (p.motion == "spring" || p.motion == "valve" || p.motion == "piston" || p.motion == "rod")
            require(p.cylinder > 0, "missing cylinder " + p.id);
        if (p.motion == "spring")
            require(p.spring == "inner" || p.spring == "outer", "spring kind " + p.id);
        for (const auto &e : field(row,"evidence_refs").array)
            p.evidence += (p.evidence.empty() ? "" : ", ") + string(e);
        p.rest = rest_matrix(row);
        for (int i=0; i<3; ++i) require(std::abs(p.rest.m[i][3]) < 10, "out-of-bounds translation " + p.id);
        require(scene.meshes.contains(p.mesh), "unknown geometry " + p.id);
        const auto &batch_names = field(row,"mesh_batches").array;
        require(batch_names.size() == scene.meshes.at(p.mesh).size(), "batch references " + p.id);
        for (const auto &batch : scene.meshes.at(p.mesh)) {
            require(string(batch_names[p.colors.size()]) == batch.name, "batch reference " + p.id);
            const auto *bindings = row.get("material_bindings");
            const auto &id = string(bindings ? field(*bindings,batch.name) :
                                    field(field(root,"material_bindings"),p.id));
            require(materials.contains(id), "unknown material " + id);
            p.colors.push_back(materials.at(id));
            for (int i = batch.first_index; i < batch.first_index + 3*batch.triangles; ++i) {
                const auto vertex = static_cast<std::size_t>(batch.first_vertex) +
                                    scene.indices[static_cast<std::size_t>(i)];
                const auto v = ysMath::MatMult(p.rest, scene.vertices[vertex].Pos);
                scene.lower = {std::min(scene.lower.x,v.x),std::min(scene.lower.y,v.y),std::min(scene.lower.z,v.z)};
                scene.upper = {std::max(scene.upper.x,v.x),std::max(scene.upper.y,v.y),std::max(scene.upper.z,v.z)};
            }
        }
        if (p.motion == "spring" && scene.rig.available)
            weight_spring(scene,p);
        if (p.id == "sevel.timingbelt" && scene.rig.available)
            weight_belt(scene,p);
        scene.parts.push_back(std::move(p));
    }
    return scene;
}
} // namespace lab
