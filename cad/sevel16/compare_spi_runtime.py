"""Audit the final published models, including the renderer's effective materials."""
import argparse
import json
from pathlib import Path
import subprocess


def poses(checker, package, angle):
    out = subprocess.check_output([checker,package,"--pose",str(angle)],text=True)
    return {row[0]:row[1:] for row in (s.split() for s in out.splitlines()[1:])}


def compare(before, after, checker, changed, added, *, expected_rgb=None):
    a,b = [json.loads((p/"parts_manifest.json").read_text()) for p in (before,after)]
    old,new = [{r["id"]:r for r in m["parts"]} for m in (a,b)]
    assert old.keys()<=new.keys() and set(new)-set(old)==set(added)
    changed_meshes = {i:[r["mesh_id"],new[i]["mesh_id"]] for i,r in old.items()
                      if r["mesh_id"]!=new[i]["mesh_id"]}
    assert set(changed_meshes)==set(changed),changed_meshes
    expected_rgb = expected_rgb or {}
    assert set(expected_rgb)<=set(changed_meshes)
    for key in ("root","cad_to_runtime","compression_tdc_deg","pose_policy","theta_zero","units"):
        assert a[key]==b[key],key
    immutable = ("motion_type","angular_ratio_to_crank","transform_period_crank_deg","pivot_local_m",
                 "rest_translation_m","rest_rotation_xyzw","rest_scale","motion_axis_local","deformation",
                 "connection_points_local_m","cylinder_id","parent_id")
    for i,row in old.items():
        for key in immutable:
            assert row[key]==new[i][key],(i,key)
        if i in expected_rgb:
            # A documented recolour must reach the rendered uniform body as
            # well as the CAD material. Keep every other material field.
            for m,r in ((a,row),(b,new[i])):
                assert set(r["material_bindings"])=={"body_surface_batch_000"},i
                binding = r["material_bindings"]["body_surface_batch_000"]
                assert m["materials"][binding]==r["visual_material"],i
            old_material = row["visual_material"]
            new_material = new[i]["visual_material"]
            assert {**old_material,"rgb":new_material["rgb"]}==new_material,i
            assert len(new_material["rgb"])==len(expected_rgb[i])==3
            assert max(abs(a-b) for a,b in zip(new_material["rgb"],expected_rgb[i]))<=1/255,i
            assert old_material["rgb"]!=new_material["rgb"],i
            continue
        assert row["visual_material"]==new[i]["visual_material"],i
        if i in changed_meshes:
            # Mesh splitting can change the batch count of a revised casting.
            def regions(part):
                return {(slot.split("_batch_")[0],binding) for slot,binding in part["material_bindings"].items()}
            assert regions(row)==regions(new[i]),(i,"material regions")
        else:
            assert row["material_bindings"]==new[i]["material_bindings"],(i,"material batches")
        for binding in row["material_bindings"].values():
            assert a["materials"][binding]==b["materials"][binding],(i,binding)
    counts = {}
    for angle in (0,90,180,270,359,360,540,719,720,-90):
        left,right = (poses(checker,p,angle) for p in (before,after))
        assert left.keys()==old.keys() and right.keys()==new.keys()
        assert all(left[i]==right[i] for i in old),angle
        counts[angle]=len(left)
    return {"baseline":before.name,"candidate":after.name,"parts":len(new),"meshes":len(b["meshes"]),
            "preserved_materials_and_rigs":len(old)-len(expected_rgb),"phase_rows_identical":counts,
            "preserved_rigs":len(old),"verified_recolours":sorted(expected_rgb),
            "changed_mesh_ids":changed_meshes,"new_parts":sorted(added)}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("before","after","checker","output"):
        p.add_argument(name,type=Path)
    p.add_argument("--changed",nargs="+",required=True)
    p.add_argument("--added",nargs="*",default=[])
    args=p.parse_args()
    result=compare(args.before,args.after,args.checker,args.changed,args.added)
    with args.output.open("x") as handle:
        json.dump(result,handle,indent=2)
        handle.write("\n")
