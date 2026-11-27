"""Check the SPI polish package against the original inspected v012 and its datum."""
import hashlib
import json

from compare_spi_runtime import compare
from config import OUTPUT, ROOT


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    work = OUTPUT/"polish/exterior-02"
    initial = work/"baseline"
    first = OUTPUT/"reviews/head-v012/lab-assets"
    registry = work/"lab-assets"
    base = first/read(initial/"baseline.json")["revision"]
    final = registry/read(registry/"current.json")["asset_revision"]
    audit = OUTPUT/"runtime_exports/SEVEL_Accessories_A5_v022_SPIBridgeWindows/v001"
    saved = audit/"SEVEL_Accessories_A5_v022_SPIBridgeWindows.FCStd"
    assert sha(base/"parts_manifest.json")==base.name and sha(final/"parts_manifest.json")==final.name
    manifest = read(final/"parts_manifest.json")
    native = read(work/"reports/v012-v022-native.json")
    assert sha(saved)==native["final_sha256"]==read(audit/"export.json")["checkpoint_sha256"]
    assert sha(initial/"SEVEL_Accessories_A5_v012_IntakeWall.FCStd")==native["source_sha256"]
    assert sha(initial/"reference_frame.json")==sha(audit/"reference_frame.json")==manifest["generator"]["datum_sha256"]
    assert sha(audit/"parameters.json")==manifest["generator"]["parameter_sha256"]
    old,params = read(initial/"parameters.json"),read(audit/"parameters.json")
    assert all(params.get(k)==v for k,v in old.items())
    frame = read(audit/"reference_frame.json")
    assert frame["status"]=="PASS_PROVISIONAL_FOR_VISUAL_ONLY"
    assert (frame["stroke_mm"],frame["cylinder_bore_diameter_mm"])==(67.4,86.4)
    changed = ["block","headlower","headgasket","camcarrier","valvecover","oilpan","intakemanifold",
               "exhaustmanifold","pcvbreatheroutlet","ignitioncoilmount","thermostathousing",
               "thermostatmainhose","thermostatbranchhose"]
    added = ["intakemanifoldhosetail","intakemanifoldplugbase","intakemanifoldsocket",
             "thermostatbridge","thermostatelement","thermostatseat","thermostatreturnspring",
             "thermostatmainclamp","thermostatbranchclamp","thermostatvalvedisc"]
    added += ["ignition"+piece+site for site in ("upperfar","uppernear","lowernear") for piece in ("boot","lead")]
    changed,added = ({"sevel."+name for name in group} for group in (changed,added))
    assert changed==set(native["changed"]) and added==set(native["added"])
    report = compare(base,final,ROOT/"build-lab/sevel-cad-check",changed,added,
                     expected_rgb={"sevel.pcvbreatheroutlet":(.18,.17,.16)})
    meshes = read(audit/"geometry/meshes_v001/mesh_checks.json")
    assert meshes["parts"]==len(meshes["checks"])==report["parts"]
    assert all(row["closed_mesh"] and row["outward_winding_and_normals"] and row["material_batches_complete"]
               for row in meshes["checks"])
    for mesh in manifest["meshes"].values():
        assert sha(final/mesh["file"])==mesh["sha256"]
    step = read(audit/"geometry/export_checks.json")
    assert step["status"]=="PASS" and step["solids"]==report["parts"]
    assert sha(audit/"geometry/assembly.step")==step["step_sha256"]
    report.update(unchanged_native_parts=len(native["unchanged"]),mesh_checks=len(meshes["checks"]),
                  published_obj_payloads=len(manifest["meshes"]),step_sha256=step["step_sha256"],
                  unchanged_baseline_parameter_groups=len(old),datum_sha256=sha(audit/"reference_frame.json"),
                  datum_status=frame["status"],step_relative_volume_error=step["relative_volume_error"])
    (work/"reports/v012-v022-delivery.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    print(run()["candidate"])
