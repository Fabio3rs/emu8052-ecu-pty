"""Estimated sensor support connected to the existing auxiliary housing end face."""
import math
import FreeCAD as App
import Part
from config import layout
from trigger_layout import radial, axial_layout


def build(params, frame):
    p = params['accessory_visual_estimated']['value']
    t = params['timing_visual_estimated']['value']
    c = params['casting_visual_estimated']['value']
    a = params['trigger_pattern_estimated']['value']['sensor_angle_deg']
    ax = axial_layout(params)
    z0 = -layout(params,frame)['height']
    cy,cz = radial(a,p['collar_radial_distance_mm'])
    start = (c['aux_y']+p['bracket_mount_y_offset_mm'],c['aux_z']+p['bracket_mount_z_offset_mm'])
    end = (cy,cz+z0)
    dy,dz = end[0]-start[0],end[1]-start[1]
    distance,r = math.hypot(dy,dz),p['bracket_arm_radius_mm']
    ny,nz = -dz*r/distance,dy*r/distance
    x = t['pulley_center_x_mm']+t['pulley_width_mm']/2
    width = p['bracket_plate_width_mm']
    v,axis = App.Vector,App.Vector(1,0,0)
    points = [v(x,start[0]+ny,start[1]+nz),v(x,end[0]+ny,end[1]+nz),
              v(x,end[0]-ny,end[1]-nz),v(x,start[0]-ny,start[1]-nz)]
    arm = Part.Face(Part.makePolygon(points+[points[0]])).extrude(v(width,0,0))
    for y,z in (start,end):
        arm = arm.fuse(Part.makeCylinder(r,width,v(x,y,z),axis))
    face = frame['bore_circle_centers_mm'][0]['x']-params['block_visual_estimated']['value']['end_margin']-c['end_plate_thickness']
    foot = Part.makeCylinder(r,face-x-width,v(x+width,*start),axis)
    collar_start = ax['sensor_x']-p['collar_front_offset_mm']
    collar = Part.makeCylinder(p['collar_radius_mm'],x+width-collar_start,v(collar_start,*end),axis)
    arm = arm.multiFuse([foot,collar]).removeSplitter()
    sy,sz = radial(a,p['wheel_tip_radius_mm']+params['rotation_sensor_gap']['value']-1)
    uy,uz = radial(a,1)
    bore = Part.makeCylinder(p['sensor_radius_mm']+p['sensor_mount_clearance_mm'],
                            p['sensor_length_mm']+2,v(ax['sensor_x'],sy,sz+z0),v(0,uy,uz))
    return arm.cut(bore).removeSplitter()
