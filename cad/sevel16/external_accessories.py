"""Accessory assembly and independent opening/connection checks."""
import FreeCAD as App
import Part
from valvetrain_layout import valves
from head_passages import chambers
from trigger_layout import axial_layout
import spark_plugs
import manifold_profiles
import intake_manifold
import exhaust_manifold
import water_pump

V = App.Vector


def color(name):
    if 'Ceramic' in name:
        return (0.90,0.89,0.83)
    if 'Exhaust' in name:
        return (0.40,0.32,0.27)
    if 'Gasket' in name or 'Pulley' in name:
        return (0.22,0.23,0.25)
    return (0.68,0.70,0.72)


def build(params,frame):
    shapes,contacts = spark_plugs.build(params,frame)
    shapes.update(manifold_profiles.gaskets(params,frame))
    shapes['IntakeManifold'],intake = intake_manifold.build(params,frame)
    shapes['ExhaustManifold'],exhaust = exhaust_manifold.build(params,frame)
    pump,pump_contacts = water_pump.build(params,frame)
    shapes.update(pump)
    contacts += pump_contacts
    for i in (1,2):
        contacts.extend([(f'ManifoldGasket{i}','HeadLower'),
                         ('IntakeManifold',f'ManifoldGasket{i}'),
                         ('ExhaustManifold',f'ManifoldGasket{i}')])
    assert len(shapes)==20 and len(contacts)==22
    h,p = params['head_lower_casting_estimated']['value'],params['manifold_visual_estimated']['value']
    openings = []
    for row in valves(params,frame):
        kind = row['kind']
        tool = Part.makeCylinder(h[kind+'_port_radius_mm']-0.1,1,
            V(row['axis_origin_mm'][0],h['manifold_face_y_mm']+p['gasket_mm'],h[kind+'_port_z_mm']),V(0,1,0))
        body = shapes['IntakeManifold' if kind=='intake' else 'ExhaustManifold']
        obstruction = body.common(tool).Volume
        assert obstruction<1e-5,row['id']
        passage = intake['air'] if kind=='intake' else exhaust['gas']
        missing = tool.cut(passage).Volume
        assert missing<1e-5,row['id']
        openings.append({'id':row['id'],'obstruction_mm3':obstruction,
                         'missing_passage_mm3':missing,'side':'+Y'})
    origin = V(0,h['spark_plug_y_mm'],h['spark_plug_z_mm'])
    reach = (V(0,-10,h['head_gasket_thickness_mm']+3)-origin).Length
    sp = params['spark_plug_visual_estimated']['value']
    tip = reach-sp['tip_setback_mm']-0.8-sp['spark_gap_mm']
    chamber_checks = []
    for i,chamber in enumerate(chambers(params,frame),1):
        point = shapes[f'C{i}_SparkElectrode'].Placement.multVec(V(0,0,tip))
        probe = Part.makeSphere(0.1,point)
        missing = probe.cut(chamber).Volume
        assert missing<1e-7,('spark outside chamber',i)
        chamber_checks.append({'cylinder':i,'electrode_tip_mm':list(point),'outside_chamber_mm3':missing})
    ax = axial_layout(params)
    center = ax['pulley_front']+params['accessory_visual_estimated']['value']['pulley_width_mm']/2
    alignment = abs(shapes['WaterPumpPulley'].BoundBox.Center.x-center)
    assert alignment<1e-7
    metrics = {'ports':openings,'spark_tips':chamber_checks,
        'intake_air_water_separation_mm':intake['air_water_separation_mm'],
        'intake_air_solids':len(intake['air'].Solids),'intake_water_solids':len(intake['water'].Solids),
        'exhaust_runner_probe_margin_mm':exhaust['runner_probe_margin_mm'],
        'exhaust_runner_probe_missing_mm3':exhaust['runner_probe_missing_mm3'],
        'exhaust_gas_solids':len(exhaust['gas'].Solids),'accessory_pulley_alignment_mm':alignment,
        'water_pump_drive':'accessory circuit; static visual pulley, speed ratio unknown'}
    return shapes,contacts,metrics
