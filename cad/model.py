"""P0 only: two shell outlines and rear PCB supports, no final battery thickness."""
from build123d import (Align, Box, Cylinder, RectangleRounded, extrude)
from reference import bounds


def box_between(b):
    x0,y0,z0,x1,y1,z1 = b
    return Box(x1-x0, y1-y0, z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))


def make_shells(parts, mounts, holes, p):
    display, full = bounds(parts['DISPLAY']), bounds(parts['ASSEMBLY'])
    x0,y0,_,x1,y1,zglass = display
    wall, clearance = p['wall_mm'], p['panel_xy_clearance_mm']
    width, height = x1-x0+2*(wall+clearance), y1-y0+2*(wall+clearance)
    cx,cy = (x0+x1)/2,(y0+y1)/2
    split, gap = p['split_z_mm'], p['seam_gap_mm']
    front_top = zglass + p['front_above_glass_mm']
    floor_top = full[2] - p['rear_extra_depth_mm']
    rear_bottom = floor_top-wall

    def outer(z0,z1):
        return extrude(RectangleRounded(width,height,p['outer_corner_radius_mm']),
                       amount=z1-z0).translate((cx,cy,z0))

    # A full-panel opening derived from the STEP touch-panel envelope. No guessed AA origin.
    inner_xy = [x0-clearance, y0-clearance, 0, x1+clearance, y1+clearance, 0]
    def cavity(z0,z1):
        return box_between([*inner_xy[:2],z0,*inner_xy[3:5],z1])
    front = outer(split+gap/2,front_top) - cavity(split-1,front_top+1)
    rear = outer(rear_bottom,split-gap/2) - cavity(floor_top,front_top+1)

    supports = []
    for hole, mount in zip(holes, sorted(mounts, key=lambda m: (round(m.center().X,3),round(m.center().Y,3)))):
        x,y,r = hole
        # Sort alignment is checked explicitly against each actual nut below.
        mb = bounds(mount)
        assert abs((mb[0]+mb[3])/2-x) < 0.05 and abs((mb[1]+mb[4])/2-y) < 0.05
        top = mb[2]-p['support_contact_gap_mm']
        support = Cylinder(p['support_outer_radius_mm'],top-floor_top,
                           align=(Align.CENTER,Align.CENTER,Align.MIN)).translate((x,y,floor_top))
        supports.append(support)
        rear = rear + support
        drill = Cylinder(p['mount_screw_clearance_radius_mm'],front_top-rear_bottom+2,
                         align=(Align.CENTER,Align.CENTER,Align.MIN)).translate((x,y,rear_bottom-1))
        rear = rear-drill

    # Open an explicit straight +Y insertion corridor all the way through the top wall.
    usb = bounds(parts['J2_USB_SIDE'])
    ux,uy,uz = p['usb_clearance_xyz_mm']
    usb_corridor = box_between([usb[0]-ux,usb[1]-uy,usb[2]-uz,
                               usb[3]+ux,cy+height/2+1,usb[5]+uz])
    front, rear = front-usb_corridor, rear-usb_corridor
    key_corridors = []
    ky,kz = p['key_clearance_yz_mm']
    for name in ['KEY1','KEY3','KEY2']:
        b = bounds(parts[name])
        corridor = box_between([cx-width/2-1,b[1]-ky,b[2]-kz,b[3],b[4]+ky,b[5]+kz])
        key_corridors.append(corridor)
        front, rear = front-corridor, rear-corridor
    front.label, rear.label = 'FRONT_shell_P0', 'REAR_shell_P0_with_PCB_supports'
    return front, rear, usb_corridor, key_corridors, {
        'outer_width_mm':width, 'outer_height_mm':height,
        'provisional_total_depth_mm':front_top-rear_bottom,
        'front_top_z_mm':front_top,'rear_floor_top_z_mm':floor_top,
        'rear_bottom_z_mm':rear_bottom,'split_z_mm':split,
        'panel_opening_xy_mm':inner_xy, 'final_device_thickness':None}
