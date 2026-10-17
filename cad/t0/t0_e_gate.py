"""E's one assembly gate; source solids, root-fixed clip proxies and real contacts."""
import math
import numpy as np
from build123d import Axis, GeomType, Plane, Polygon, extrude
from reference import bounds
from p1_checks import clashes, common_volume, intersection, translated_box_sweep
from model import box_between as box


def source_clashes(shape,parts,source,tol):
    # Exact broad-phase clipping leaves only fixture material inside the full
    # source envelope. Testing its individual solids avoids hundreds of booleans
    # against a hollow shell's enormous empty cavity; no source solid is omitted.
    clipped=intersection(shape,box(bounds(parts['ASSEMBLY'])))
    return [dict(fixture_piece=i,**hit) for i,s in enumerate(clipped.solids()) for hit in clashes(s,source,tol)]


def axial_sweep(shape,direction,distance):
    """Exact union of leading planar face prisms for these axis-aligned fixtures.

    The cap's round head is parallel to Z: its downward boundary is curved, so
    cap insertion uses the conservative split-piece AABBs separately instead.
    """
    result=shape
    for f in shape.faces():
        if f.geom_type==GeomType.PLANE and sum(a*b for a,b in zip(f.normal_at(),direction))>.0001:
            result=result+extrude(f,amount=distance,dir=direction)
    return result


def clip_parts(m,base,local_index,displacement):
    """Same A rest geometry; only the released beam is a root-fixed clearance proxy.

    Smoothstep centerline has zero root/tip slope. It is a held deformation shape,
    NOT a force-derived elastic solution. The hook/stop move together at free end.
    """
    data=m['clip_data'][local_index];x,y=data['mount_axis_mm'];side=1 if x>0 else -1
    root=y+(base['pcb_clip_beam_length_mm'] if y<0 else -base['pcb_clip_beam_length_mm'])
    sign=1 if y>root else -1;ya,yb=sorted([root,y]);xc=side*base['pcb_clip_beam_x_abs_mm']
    t=base['pcb_clip_beam_thickness_mm'];z=base['pcb_clip_beam_bottom_z_mm'];h=base['pcb_clip_beam_height_mm']
    beam=box([xc-t/2,ya,z,xc+t/2,yb,z+h]);free=m['pcb_clips'][local_index]-beam
    # Keep a .7mm root region at rest, contained in its unchanged A anchor.
    fixed=base['clip_root_fixed_length_mm'];L=abs(y-root)-fixed
    points=[]
    for edge in [-1,1]:
        row=[]
        for j in range(base['clip_deformation_segments']+1):
            s=j/base['clip_deformation_segments'];shift=displacement*(3*s*s-2*s*s*s)
            row.append((xc+side*shift+edge*t/2,root+sign*(fixed+s*L)))
        if edge>0:row.reverse()
        points+=row
    bent=extrude(Polygon(*points,align=None),amount=h,dir=(0,0,1)).translate((0,0,z))
    lo,hi=sorted([root,root+sign*(fixed+.001)])
    bent=bent+box([xc-t/2,lo,z,xc+t/2,hi,z+h])
    return free.translate((side*displacement,0,0))+bent,free,beam


def evaluate(parts,mounts,m,nests,base,p,kp):
    tol=base['volume_tolerance_mm3'];source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    fixed=m['front']
    for s in m['pcb_clips']:fixed=fixed-s
    released=[];rows=[];all_paths=[];return_rows=[];back_contacts=[]
    module_path=translated_box_sweep(parts['ASSEMBLY'],(0,0,-p['board_insertion_z_mm']))
    for j,i in enumerate(p['pcb_clip_indices']):
        rel,free,beam=clip_parts(m,base,j,base['pcb_clip_release_mm']);released.append(rel)
        path=clashes(module_path,[(f'held_clip_{i}',rel)],tol)
        held_fixed=clashes(rel,[('FRONT_fixed',fixed)],tol)
        # Entire inward return is bounded by the original free-end exact -/+X
        # prism and the outer beam envelope, not just the final rest pose.
        side=m['clip_data'][j]['release_direction'][0]
        free_return=axial_sweep(free,(side,0,0),base['pcb_clip_release_mm'])
        bb=bounds(beam);dx=side*base['pcb_clip_release_mm']
        beam_envelope=box([bb[0]+min(0,dx),bb[1],bb[2],bb[3]+max(0,dx),bb[4],bb[5]])
        ret=clashes(free_return+beam_envelope,source,tol)
        # The FRONT contact is the lower plane of the existing stop, over PCB.
        b=m['clip_data'][j];x,y=b['mount_axis_mm'];xc=side*base['pcb_clip_beam_x_abs_mm']
        xl,xh=sorted([side*base['pcb_clip_edge_x_mm'],xc+side*base['pcb_clip_beam_thickness_mm']/2])
        half=base['pcb_clip_bearing_y_mm']/2;sz=b['FRONT_stop_z_mm']
        stop=box([xl,y-half,sz,xh,y+half,sz+base['pcb_front_stop_thickness_mm']])
        gap=stop.distance_to(parts['PCB_BOARD'])
        touch=intersection(stop,parts['PCB_BOARD'].translate((0,0,gap+1e-4)))
        contact=touch.center();row={'A_index':i,'mount_axis_xy_mm':[x,y],
            'stop_contact_witness_xy_mm':[contact.X,contact.Y],'contact_probe_extra_z_mm':.0001,
            'PCB_front_gap_mm':gap,'stop_to_LCD_gap_mm':stop.distance_to(parts['DISPLAY']),
            'PCB_contact_volume_at_0_1um_penetration_mm3':touch.volume,
            'positive_0_4_PCB_stop_overlap_mm3':common_volume(stop,parts['PCB_BOARD'].translate((0,0,p['positive_z_witness_mm']))),
            'stop_glass_or_display_overlap_at_first_PCB_contact_mm3':common_volume(stop,parts['DISPLAY'].translate((0,0,gap))),
            'released_geometry_vs_source':clashes(rel,source,tol),'released_vs_fixed_front':held_fixed,
            'continuous_board_insertion_vs_released_clip':path,'continuous_free_end_return_and_beam_envelope_vs_source':ret,
            'root_fixed_deformation_proxy':True,'released_geometry_valid':rel.is_valid,
            'actual_MJF_elasticity':'UNVERIFIED','smoothstep_beam_linear_strain_estimate':3*base['pcb_clip_beam_thickness_mm']*base['pcb_clip_release_mm']/(base['pcb_clip_beam_length_mm']-base['clip_root_fixed_length_mm'])**2}
        rear_gap=m['supports'][j].distance_to(parts['PCB_BOARD'])
        back_touch=intersection(m['supports'][j],parts['PCB_BOARD'].translate((0,0,-rear_gap-.0001)))
        bc=back_touch.center();back_contacts.append((bc.X,bc.Y))
        row.update(A_rear_bearing_PCB_gap_mm=rear_gap,A_rear_bearing_contact_probe_volume_mm3=back_touch.volume,A_rear_bearing_contact_xy_mm=[bc.X,bc.Y])
        rows.append(row);all_paths+=path+held_fixed;return_rows+=ret
    # A conservative continuous box containing EVERY original source solid is
    # sufficient here if clear. Unlike D's nest escape, it fills no fixture holes.
    fixed_path=clashes(module_path,[('FRONT_fixed',fixed)],tol)
    nominal={name:source_clashes(s,parts,source,tol) for name,s in [('front',m['front']),*[(f'nest_{i}',s) for i,s in enumerate(nests)]]}
    # Known counterexample forces the practical assembly order change.
    cap_first=[];cap_after=[]
    for key,cap in m['caps'].items():
        cap_first.append({'key':key,'module_z_mm':-6,'hits':clashes(cap,[(f'LCD_{i}',s.translate((0,0,-6))) for i,s in enumerate(parts['DISPLAY'].solids())],tol)})
        # Split body/head/flange and use tight AABB sweeps for rear placement.
        from p1_checks import cap_components
        hits=[]
        for piece in cap_components(cap,m['key_data'][key],kp):
            swept=translated_box_sweep(piece,(0,0,-p['board_insertion_z_mm']))
            hits+=clashes(swept,[('FRONT',m['front']),*source],tol)
        cap_after.append({'key':key,'continuous_REAR_insertion_hits':hits})
    contacts=[r['stop_contact_witness_xy_mm'] for r in rows]
    matrix=np.array([[1,y,-x] for x,y in contacts]);area=abs(np.linalg.det(np.array([[x,y,1] for x,y in contacts])))/2
    rear_xy=[]
    for mount in mounts:
        f=next(f for f in mount.faces() if f.geom_type==GeomType.CYLINDER and abs(f.axis_of_rotation.direction.Z)>.99)
        rear_xy.append(tuple(f.axis_of_rotation.position)[:2])
    rear_xy=sorted(rear_xy);rear_xy=[rear_xy[i] for i in [0,2,3,1]]
    # A unit-height exact prism avoids coincident planar-face boolean ambiguity.
    contact_hull_overlap=common_volume(extrude(Polygon(*(tuple(c) for c in contacts),align=None),amount=1,dir=(0,0,1)),
                                       extrude(Polygon(*rear_xy,align=None),amount=1,dir=(0,0,1)))
    captured_hull_overlap=common_volume(extrude(Polygon(*(tuple(c) for c in contacts),align=None),amount=1,dir=(0,0,1)),
                                        extrude(Polygon(*back_contacts,align=None),amount=1,dir=(0,0,1)))
    tilts=[];pivot=parts['PCB_BOARD'].center()
    for axis_name,axis in [('pitch_X',(1,0,0)),('roll_Y',(0,1,0))]:
        for sign in [-1,1]:
            board=parts['PCB_BOARD'].rotate(Axis(pivot,axis),sign*p['tilt_witness_degrees'])
            metal=[(f'MOUNT_{i}',s.rotate(Axis(pivot,axis),sign*p['tilt_witness_degrees'])) for i,s in enumerate(mounts)]
            front_hits=[{'clip':p['pcb_clip_indices'][j],'PCB_volume_mm3':common_volume(s,board)} for j,s in enumerate(m['pcb_clips'])]
            rear_hits=[{'nest':i,'hits':clashes(s,metal,tol)} for i,s in enumerate(nests)]
            tilts.append({'axis':axis_name,'degrees':sign*p['tilt_witness_degrees'],'PCB_clip_reactions':front_hits,'metal_nest_reactions':rear_hits,
                          'restrained':any(r['PCB_volume_mm3']>tol for r in front_hits) or any(r['hits'] for r in rear_hits)})
    cover=[]
    for dz in [-8,-2,-1,0]:cover.append({'REAR_dz_mm':dz,'nest_vs_source':[clashes(s.translate((0,0,dz)),source,tol) for s in nests]})
    ok=not all_paths and not return_rows and not fixed_path and not any(nominal.values()) and not any(r['continuous_REAR_insertion_hits'] for r in cap_after)
    ok=ok and all(r['positive_0_4_PCB_stop_overlap_mm3']>tol and r['PCB_contact_volume_at_0_1um_penetration_mm3']>0 and r['stop_glass_or_display_overlap_at_first_PCB_contact_mm3']<tol for r in rows)
    ok=ok and np.linalg.matrix_rank(matrix)==3 and captured_hull_overlap>1 and all(r['A_rear_bearing_PCB_gap_mm']<.00001 and r['A_rear_bearing_contact_probe_volume_mm3']>0 for r in rows) and all(r['restrained'] for r in tilts) and not any(h for r in cover for h in r['nest_vs_source'])
    report={'status':'NOMINAL_ASSEMBLY_GATE_PASS' if ok else 'BLOCKED_ASSEMBLY_GATE','clips':rows,'fixed_FRONT_continuous_insertion':fixed_path,
        'nominal_source_collisions':nominal,'three_noncollinear_contact_triangle_area_mm2':area,'contact_constraint_rank':int(np.linalg.matrix_rank(matrix)),
        'FRONT_REAR_contact_hull_overlap_area_mm2':contact_hull_overlap,
        'FRONT_A_back_bearing_contact_hull_overlap_area_mm2':captured_hull_overlap,
        'REAR_nest_axial_clearance_mm':p['nest_axial_clearance_mm'],
        'nominal_axial_float_mm':base['pcb_clip_front_gap_mm'],
        'rigid_nominal_zero_float_note':'Three A clips capture PCB between their own FRONT stops and REAR bearings, with positive-area overlap of those contact hulls and zero nominal gaps. Four D nests have .1mm axial relief, bound XY and supply secondary rear support. Peripheral stops bypass PCB for shell closure. Real tolerances/elasticity UNVERIFIED.',
        'keycaps_first_actual_LCD_counterexample':cap_first,'keycaps_AFTER_PCB_from_REAR':cap_after,'tilt_witnesses':tilts,'REAR_nest_closure_samples':cover,
        'assembly_order':['Hold three PCB clips outward 1.2mm (root-fixed clearance proxies; real elasticity unverified)','Insert COMPLETE original board/display from REAR along Z, then return clips onto PCB perimeter','Install existing independent caps from REAR AFTER board (cap-first LCD collision)','Seat four shallow REAR nests and close short shell teeth'],
        'scope':'Conservative continuous Z envelope of ALL original solids vs fixed front/released clips; source BReps vs free-end return/beam envelope. Actual bend force, holding-tool access, material creep/tolerance, key function and real leads unverified.'}
    return report,released
