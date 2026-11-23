"""Snapshot component IDs, local pivots and transforms from the actual CAD tree."""
import hashlib
import json
import math
from pathlib import Path
import FreeCAD as App
from config import ROOT, OUTPUT, load


def run(doc, generator_entrypoint=None, folder=None):
    assert abs(doc.Phase.ThetaDeg)<1e-9
    params,frame = load()
    basis = App.Rotation(App.Vector(1,0,0),-90)
    rows = []
    for obj in doc.Objects:
        if not hasattr(obj,'Shape'):
            continue
        motion = obj.MotionType
        ratio = {'crank':1.0,'cam':0.5}.get(motion)
        if motion in ('aux','tensioner'):
            timing = params['timing_visual_estimated']['value']
            ratio = (timing['crank_teeth']/timing['aux_teeth'] if motion=='aux' else
                     -timing['crank_teeth']*timing['pitch_mm']/(2*math.pi*timing['tensioner_radius_mm']))
        period = (360/abs(ratio) if ratio else
                  {'rod':360,'piston':360,'valve':720,'spring':720}.get(motion))
        position = basis.multVec(obj.Placement.Base)*0.001
        rotation = basis.multiply(obj.Placement.Rotation).multiply(basis.inverted())
        axis = [1,0,0] if motion in ('crank','rod','cam','aux','tensioner') else [0,1,0]
        connections = None
        if motion=='rod':
            connections = {'big_end':[0,0,0],
                           'small_end':[0,params['moving_geometry_estimated']['value']['rod_length_mm']/1000,0]}
        rows.append({'id':obj.PartId,'source_object':obj.Name,'display_label':obj.Label,'parent_id':'engine_root',
                     'part_type':obj.Name.split('_',1)[-1], 'cylinder_id':obj.CylinderId or None,
                     'cad_prototype_id':obj.Name.split('_',1)[-1] if obj.CylinderId else obj.Name,
                     'mesh_id':None,'mesh_status':'not_exported_yet',
                     'pivot_local_m':[0,0,0], 'rest_translation_m':list(position),
                     'rest_rotation_xyzw':list(rotation.Q),'rest_scale':[1,1,1],
                     'motion_type':motion,'motion_axis_local':axis,
                     'angular_ratio_to_crank':ratio,'transform_period_crank_deg':period,
                     'valve_kind':getattr(obj,'ValveKind',None),
                     'spring_kind':getattr(obj,'SpringKind',None),
                     'deformation':('constant circular wire, recomputed helix centerline'
                                    if motion=='spring' else None),
                     'connection_points_local_m':connections,
                     'visual_material':{'rgb':list(obj.ViewObject.ShapeColor)[:3],
                                        'opacity':1-obj.ViewObject.Transparency/100,
                                        'physical_material_verified':False},
                     'cad_placement_mm':list(obj.Placement.Base),
                     'cad_rotation_xyzw':list(obj.Placement.Rotation.Q),
                     'evidence_refs':['parameters.json','reports/moving_sources.json'],
                     'cutaway_group':'stationary' if motion=='fixed' else 'mechanism'})
    assert len({r['id'] for r in rows})==len(rows)
    manifest = {'schema':'sevel.parts.v1','status':'CAD_CHECKPOINT_MESH_DELIVERY_PENDING',
                'source_fcstd':doc.FileName,
                'source_sha256':hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest(),
                'units':{'length':'m','angle':'rad','time':'s'},'theta_deg':0,
                'theta_zero':'C1 compression TDC','compression_tdc_deg':[0,540,180,360],
                'pose_policy':'absolute in engine frame; all dynamic parts have engine_root parent',
                'cad_to_runtime':'(x,y,z) mm -> 0.001*(x,z,-y) m; vertices and poses converted exactly once',
                'conversion_owner':'future mesh exporter; this manifest already contains converted poses',
                'root':{'id':'engine_root','parent_id':None,'translation_m':[0,0,0],'rotation_xyzw':[0,0,0,1]},
                'reference_status':frame['status'],'parts':rows}
    if doc.getObject('TriggerWheel'):
        manifest['trigger_reference'] = {
            'wheel_part_id':doc.TriggerWheel.PartId,'sensor_part_id':doc.RotationSensor.PartId,
            'angular_frame':'CAD: slot zero along +Z, positive rotation about +X',
            'pattern':params['trigger_pattern_estimated']['value'],
            'pattern_evidence':'ASSUMPTION; project-context 60-2, not OEM-calibrated',
            'sensor_gap_mm':params['rotation_sensor_gap']['value'],
            'sensor_gap_documented_range_mm':params['rotation_sensor_gap']['range_mm'],
            'tdc_reference':'theta=0: cylinder 1 compression TDC',
            'sync_edge':None,'sync_edge_evidence':'UNKNOWN',
            'geometry_policy':'Wheel mounting phase baked into local geometry; pose adds crank rotation once'}
    if doc.getObject('AuxiliaryRearBush'):
        manifest['auxiliary_reference'] = {
            'shaft_part_id':doc.AuxiliaryFrontShaft.PartId,
            'identity_note':'Original front-shaft PartId retained; geometry now includes both journals',
            'bush_part_ids':[doc.AuxiliaryFrontBush.PartId,doc.AuxiliaryRearBush.PartId],
            'nominal_diameters':params['auxiliary_nominal'],
            'estimated_internal_geometry':params['auxiliary_internal_estimated'],
            'gear_contact_verified':False}
    if doc.Name.startswith(('SEVEL_Carrier_A3_','SEVEL_Head_A3_','SEVEL_Casting_A4_',
                            'SEVEL_Closures_A5_','SEVEL_Accessories_A5_')):
        manifest['carrier_reference'] = {
            'part_id':doc.CamCarrier.PartId,
            'estimated_section':params['carrier_section_estimated'],
            'catalogue_interface':'10101, PDF 14-15, gasket 7784728; topology only',
            'valve_axes_inferred_from_casting':False,
            'dimensional_certification':False}
    if doc.getObject('HeadLower'):
        prefixes = sorted({o.Name.removesuffix('_InnerSpringSeat') for o in doc.Objects
                           if o.Name.endswith('_InnerSpringSeat')})
        supported = len(prefixes)==8 and all(
            doc.getObject(p+'_InnerSpringSeat').Shape.distToShape(doc.getObject(p+'_OuterSpringSeat').Shape)[0]<1e-7
            and doc.getObject(p+'_OuterSpringSeat').Shape.distToShape(doc.HeadLower.Shape)[0]<1e-7
            for p in prefixes)
        manifest['head_reference'] = {
            'part_ids':[doc.getObject(n).PartId for n in ('HeadLower','HeadGasket','CarrierGasket')],
            'estimated_casting':params['head_lower_casting_estimated'],
            'documented_chamber_volume':params['head_chamber_documented_volume'],
            'measured_model_chamber_volume_matches_manual':False,
            'cooling_passages_connected':False,
            'inner_spring_seat_support_complete':supported,
            'catalogue_interfaces':'10101, PDF 12-15; 5889188, 7667675, 7648903, 7784728',
            'dimensional_certification':False}
        if supported:
            manifest['lower_spring_seat_reference'] = {
                'catalogue_part':'4371517','catalogue_quantity':8,'catalogue_pdf_pages':[36,38],
                'representation':'Two contacting CAD regions per single stepped lower seat',
                'estimated_geometry':params['spring_seat_support_estimated'],
                'component_groups':[[doc.getObject(p+'_'+k+'SpringSeat').PartId for k in ('Outer','Inner')]
                                    for p in prefixes]}
    if doc.getObject('OilPan'):
        manifest['closure_reference'] = {
            'part_ids':[doc.getObject(n).PartId for n in ('ValveCover','ValveCoverGasket',
                'OilFillerCap','OilPan','OilPanGasket','OilDrainPlug')],
            'estimated_geometry':params['external_closures_estimated'],
            'catalogue_pdf_pages':[14,15,22,23],
            'drain_plug_catalogue_identity':'14325311, M22x1.5; smooth nominal envelope only',
            'dimensional_certification':False}
    if doc.getObject('IntakeManifold'):
        manifest['external_accessories_reference'] = {
            'part_ids':[o.PartId for o in doc.Objects if hasattr(o,'PartId') and
                ('Spark' in o.Name or 'Manifold' in o.Name or o.Name.startswith('WaterPump'))],
            'estimated_manifolds':params['manifold_visual_estimated'],
            'estimated_spark_plugs':params['spark_plug_visual_estimated'],
            'estimated_water_pump':params['water_pump_visual_estimated'],
            'water_pump_drive':'accessories, static preview; ratio unknown',
            'catalogue_pdf_pages':[67,68,69,70,89,90],
            'dimensional_certification':False}
    if generator_entrypoint is not None:
        source = (ROOT/generator_entrypoint).resolve()
        assert source.is_relative_to(ROOT/'cad/sevel16') and source.is_file()
        manifest['generator'] = {'entrypoint':str(source.relative_to(ROOT)),
            'entrypoint_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'freecad_version':App.Version()[:3],
            'parameter_sha256':hashlib.sha256((OUTPUT/'parameters.json').read_bytes()).hexdigest(),
            'datum_sha256':hashlib.sha256((OUTPUT/'datums/reference_frame.json').read_bytes()).hexdigest()}
    materials,bindings = {},{}
    for row in rows:
        material = row['visual_material']
        key = 'visual_'+hashlib.sha256(json.dumps(material,sort_keys=True).encode()).hexdigest()[:12]
        materials[key] = material
        bindings[row['id']] = key
    manifest.update(materials=materials,material_bindings=bindings)
    target = (Path(folder) if folder is not None else OUTPUT/'exports'/doc.Name)/'parts_manifest.json'
    target.write_text(json.dumps(manifest,indent=2)+'\n')
    print(target)
    return manifest
