"""Verify external stock against every moving part and both sealing interfaces."""
from assembly import apply_pose
from check_auxiliary import volume
from spi_filter_wall import casting_stock

def run(doc, params, frame):
    stock = casting_stock(params,frame)
    parts = [o for o in doc.Objects if hasattr(o,"MotionType") and o.MotionType!="fixed"]
    candidates = set()
    result = {}
    original_angle = doc.Phase.ThetaDeg
    try:
        for a in sorted(set(range(0,721,15))|{359}):
            apply_pose(doc,a,params,frame,update_springs=False)
            maximum = 0.
            for obj in parts:
                if stock.BoundBox.intersect(obj.Shape.BoundBox):
                    candidates.add(obj.Name)
                    overlap = abs(volume(stock.common(obj.Shape)))
                    assert overlap<1e-5,(a,obj.Name,overlap)
                    maximum = max(maximum,overlap)
            result[a] = maximum
    finally:
        apply_pose(doc,original_angle,params,frame,update_springs=False)
    # The full sealing faces and the bottom of the v017 water recesses are
    # outside the z range of the added material, including the spline extrema.
    assert stock.BoundBox.ZMin > -params["block_visual_estimated"]["value"]["height"]+3
    assert stock.BoundBox.ZMax < -params["head_lower_casting_estimated"]["value"]["deck_coolant_recess_depth_mm"]-.25
    return {"moving_parts_checked_each_phase":len(parts),"bounding_box_candidates":sorted(candidates),
            "maximum_overlap_mm3_by_angle":result,"stock_z_mm":[stock.BoundBox.ZMin,stock.BoundBox.ZMax]}
