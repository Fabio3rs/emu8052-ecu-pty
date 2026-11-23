"""Derived assembly block: explicit estimated crank rotation clearance bays."""
import FreeCAD as App
import Part
import importlib.util
from config import layout, OUTPUT

_spec = importlib.util.spec_from_file_location('sump_profile',OUTPUT/'generator/sump_profile.py')
_sump = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sump)


def lower_envelopes(params, frame):
    p = params['block_visual_estimated']['value']
    sp = params['sump_outline_estimated']['value']
    h, ft, w = p['height'],p['flange_thickness'],p['half_width']
    ztop = -h+sp['wall_blend_height']+0.1
    outline = lambda z, inset=0, width=None: _sump.outline(params,frame,z,inset,width)
    old = Part.makeLoft([outline(-h,sp['wall_inset']),outline(-h+ft,sp['wall_inset']),
                         outline(ztop,width=w-4)],True,True)
    old = old.fuse(Part.Face(outline(-h)).extrude(App.Vector(0,0,ft)))
    levels = params['assembly_lower_casting_estimated']['value']['levels_z_width_mm']
    end_z = levels[-1][0]
    waist = params['casting_visual_estimated']['value']['waist_half_width']
    end_w = w-4+(waist-(w-4))*(end_z-(-h+40))/(-112-(-h+40))
    old = old.fuse(Part.makeLoft([outline(-h+40,width=w-4),outline(end_z,width=end_w)],True,True))
    new = Part.makeLoft([outline(-h)]+[outline(z,width=width) for z,width in levels],True,True)
    return old, new


def clear_crank_bays(original, params, frame, include_rods=False):
    g = layout(params,frame)
    p = params['moving_geometry_estimated']['value']
    half_web = params['block_visual_estimated']['value']['web_thickness']/2
    sweep_radius = max(p['counterweight_radius_mm'],
                       g['radius']+params['moving_nominal']['crankpin_diameter_mm']['value']/2)
    radius = sweep_radius+p['crankcase_clearance_mm']
    body = original
    if include_rods:
        rp = params['piston_rod_visual_estimated']['value']
        # Conservative rotation envelope of the rod cap and hex head corners.
        rod_bound = ((rp['rod_bolt_y_mm']+rp['rod_bolt_head_radius_mm'])**2+
                     (rp['rod_bolt_half_length_mm']+4)**2)**0.5
        radius = max(radius,g['radius']+rod_bound+p['crankcase_clearance_mm'])
        old_envelope,new_envelope = lower_envelopes(params,frame)
        # Preserve existing voids while adding only the revised outer casting.
        original_voids = old_envelope.cut(original)
        body = original.fuse(new_envelope).cut(original_voids)
    tools = [Part.makeCylinder(radius,b-a-2*half_web,
             App.Vector(a+half_web,0,-g['height']),App.Vector(1,0,0))
             for a,b in zip(g['supports'],g['supports'][1:])]
    result = body.cut(Part.makeCompound(tools)).removeSplitter()
    assert result.isValid() and len(result.Solids)==1
    # The new cuts must not affect the deck or the upper bores.
    top = Part.makeBox(600,400,100,App.Vector(-150,-200,-100))
    before, after = original.common(top), result.common(top)
    delta = before.cut(after).Volume+after.cut(before).Volume
    assert abs(delta)<1e-6
    return result, {'evidence':'ASSUMPTION','swept_clearance_radius_mm':radius,
                    'net_volume_change_mm3':result.Volume-original.Volume,
                    'upper_100mm_symmetric_difference_mm3':delta,
                    'rods_included':include_rods,
                    'note':'Estimated assembly casting; source remains unchanged. Seal outline retained; full collision scan required.'}
