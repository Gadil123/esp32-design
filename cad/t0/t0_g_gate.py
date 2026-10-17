"""One G assembly gate; true source BReps and continuous conservative paths."""
import math
from build123d import Axis, Plane, Polygon, extrude
from reference import bounds
from model import box_between as box
from p1_checks import clashes, common_volume, intersection, translated_box_sweep, cap_components
from t0_e_gate import source_clashes, axial_sweep
from t0_wiring import build_wiring


def deformed_tongue(pair,m,base,p):
    """Root-fixed smoothstep clearance proxy, NOT a force/strain solution."""
    q=p['latch'];ex=base['outer_x_min_mm']+base['width_mm'];outer=ex-base['wall_mm']+q['beam_inner_offset_from_wall_mm']+q['beam_thickness_mm'];inner=outer-q['beam_thickness_mm']
    root=q['beam_root_z_mm'];tip=q['beam_tip_z_mm'];w=q['beam_width_mm'];delta=q['release_deflection_mm']
    points=[]
    for edge in [inner,outer]:
        row=[]
        for j in range(17):
            s=j/16;row.append((edge-delta*(3*s*s-2*s*s*s),root+s*(tip-root)))
        if edge==outer:row.reverse()
        points+=row
    beam=extrude(Plane.XZ*Polygon(*points,align=None),amount=w/2,both=True)
    beam=beam+box([inner,-w/2,m['dimensions']['rear_inside_z_mm']-.01,outer,w/2,root+.001])
    hook=extrude(Plane.XZ*Polygon((outer-delta,tip-q['hook_height_mm']),(outer+q['hook_projection_mm']-delta,tip-q['hook_height_mm']),(outer-delta,tip),align=None),amount=w/2,both=True)
    local=beam+hook
    ox=base['outer_x_min_mm'];oy,ey=base['outer_y_mm'];at=pair['site']['coordinate_mm']
    shift={'right':(0,at,0),'left':(ox+ex,at,0),'top':(at,ey-ex,0),'bottom':(at,oy+ex,0)}[pair['site']['edge']]
    return local.rotate(Axis.Z,pair['angle']).translate(shift)


def evaluate(parts,mounts,m,base,kp,p,include_latches=False):
    tol=base['volume_tolerance_mm3'];source=[(f'official_{i}',s) for i,s in enumerate(parts['ASSEMBLY'].solids())]
    plugs,wires,wiredata=build_wiring(parts,base,m)
    accessories=[(k,m[k]) for k in ['battery','speaker','protection','adhesive','foam','damping']]+list(plugs.items())+[(f'{k}_wire_{i}',s) for k,ss in wires.items() for i,s in enumerate(ss)]
    parked={k:s.translate((-p['key_assembly_outward_mm'],0,0)) for k,s in m['caps'].items()}
    boardpath=translated_box_sweep(parts['ASSEMBLY'],(0,0,-p['assembly_translation_mm']))
    path=clashes(boardpath,[('FRONT',m['front']),*parked.items()],tol)
    installed=[('FRONT',m['front']),('REAR',m['rear']),*m['caps'].items(),*accessories]
    installed_source={k:source_clashes(s,parts,source,tol) for k,s in installed}
    pairs=[]
    for i,(k,s) in enumerate(installed):
        for name,t in installed[i+1:]:
            v=common_volume(s,t)
            if v>tol:pairs.append(dict(a=k,b=name,volume_mm3=v))
    caps=[]
    for k,c in m['caps'].items():
        # Counterexample and the explicit gravity/outward-stop correction.
        bad=clashes(c,[(f'LCD_{i}',s.translate((0,0,-6))) for i,s in enumerate(parts['DISPLAY'].solids())],tol)
        # Diagnostic, not a fabricated PASS: a board offset still permitted by
        # the screw clearance can consume the tiny nominal cap/glass allowance.
        play=p['PCB_XY_play_witness_mm']
        assert play<=(p['screw']['shaft_bore_diameter_mm']-p['screw']['thread_diameter_mm'])/2
        misplaced=clashes(parked[k],[(f'LCD_{i}',s.translate((-play,0,-6))) for i,s in enumerate(parts['DISPLAY'].solids())],tol)
        from build123d import Compound
        move=Compound([translated_box_sweep(s,(-p['key_assembly_outward_mm'],0,0)) for s in cap_components(c,m['key_data'][k],kp)])
        from t0_checks import cap_axial_sweep
        operating=[hit for piece in cap_components(c,m['key_data'][k],kp) for hit in clashes(cap_axial_sweep(piece,m['key_data'][k],kp),[('FRONT',m['front']),('REAR',m['rear'])],tol)]
        caps.append(dict(key=k,rest_cap_first_LCD_at_minus6=bad,outward_mm=p['key_assembly_outward_mm'],
                         parked_vs_front_and_rear=clashes(parked[k],[('FRONT',m['front']),('REAR',m['rear'])],tol),
                         outward_staging_continuous=clashes(move,[('FRONT',m['front']),('REAR',m['rear']),*source],tol),
                         candidate_inward_0_4_shell_motion=operating,
                         permitted_PCB_X_offset_negative_witness_mm=-play,
                         permitted_PCB_X_offset_insertion_collisions=misplaced,
                         complete_module_path_to_parked_gap_mm=parked[k].distance_to(boardpath),
                         extra_outward_bound_to_cover_current_screw_play_WITH_ZERO_PROCESS_MARGIN_mm=max(0,(p['screw']['shaft_bore_diameter_mm']-p['screw']['thread_diameter_mm'])/2-parked[k].distance_to(boardpath)),
                         cap_path_note='Place caps before board with LEFT down; gravity seats their outward stops. RESET guide relief enlarged .3mm, face stock .5mm. Gravity/friction/PA12 tolerance unverified.'))
    metal_bounds=[bounds(s) for s in mounts]
    nonmetal=[(n,s) for n,s in source if not any(max(abs(a-b) for a,b in zip(bounds(s),mb))<1e-5 for mb in metal_bounds)]
    assert len(source)-len(nonmetal)==4
    screwrows=[]
    for i,(row,s) in enumerate(zip(m['screw_rows'],m['screws'])):
        x,y=row['axis_xy_mm'];sp=p['screw'];z0=row['head_bottom_z_mm'];z1=row['head_seat_z_mm']
        from t0_model import cyl
        tool=cyl(sp['tool_probe_radius_mm'],m['dimensions']['rear_bottom_z_mm']-10,z0+.5,x,y)
        metal=sorted(mounts,key=lambda s:(s.center().X,s.center().Y))[i]
        screwrows.append(row|dict(head_bearing_annulus_area_mm2=math.pi*((sp['head_diameter_mm']/2)**2-(sp['shaft_bore_diameter_mm']/2)**2),
            nonmating_source_collisions=clashes(s,nonmetal,tol),rear_clearance=clashes(s,[('REAR',m['rear'])],tol),
            rear_tool_path=clashes(tool,[('REAR',m['rear']),*source],tol),
            rear_to_metal_contact_mm=m['rear'].distance_to(metal),
            metal_contact_probe_volume_mm3=common_volume(m['rear'],metal.translate((0,0,-.0001))),
            thread_note='Major-diameter shaft envelope: mating metal thread solids excluded ONLY for screw check; all other source solids retained. Actual thread depth/pitch/tightening torque pending supplied-board measurement.',
            PA12_status='0.8mm seat remains a manufacturing/torque/creep risk, not qualified'))
    latches=[];held=[];fixedrear=m['rear']
    if include_latches:
        for pair in m['latch_pairs']:fixedrear=fixedrear-pair['tongue']
        for i,pair in enumerate(m['latch_pairs']):
            q=p['latch'];rel=deformed_tongue(pair,m,base,p);held.append(rel)
            inward={'right':(-1,0,0),'left':(1,0,0),'top':(0,-1,0),'bottom':(0,1,0)}[pair['site']['edge']]
            # Ordered path: enter at rest, THEN push inward at full depth.
            # Cartesian combinations of both motions would falsely move the
            # inward tool through the rigid root before it has entered.
            from build123d import Compound
            toolpath=Compound([axial_sweep(pair['pick'],(0,0,-1),p['assembly_translation_mm']),
                               axial_sweep(pair['pick'],inward,q['release_deflection_mm'])])
            released_pick=pair['pick'].translate(tuple(v*q['release_deflection_mm'] for v in inward))
            withdrawal_pick=axial_sweep(released_pick,(0,0,-1),p['assembly_translation_mm'])
            # Keep tongue contact out of the tool obstacle set: pushing it is intended.
            hits=clashes(toolpath,[('FRONT',m['front']),('fixed_REAR',fixedrear),*source,*accessories],tol)
            tool_withdrawal=clashes(withdrawal_pick,[('FRONT',m['front']),*parked.items()],tol)
            heldpath=axial_sweep(rel,(0,0,-1),p['assembly_translation_mm'])
            return_envelope=Compound([axial_sweep(pair[k],inward,q['release_deflection_mm']) for k in ['freebeam','hook']])
            return_hits=clashes(return_envelope,[('FRONT',m['front']),('fixed_REAR',fixedrear),*source,*accessories],tol)
            latches.append(dict(index=i,site=pair['site'],root_fixed_held_valid=rel.is_valid,
                root_fixed_held_vs_source=source_clashes(rel,parts,source,tol),
                continuous_held_insertion=clashes(heldpath,[('FRONT',m['front']),*parked.items()],tol),
                full_deflection_return_envelope=return_hits,
                relaxed_pull_minus0_01_overlap_mm3=common_volume(pair['tongue'].translate((0,0,-.01)),m['front']),
                relaxed_pull_minus0_3_overlap_mm3=common_volume(pair['tongue'].translate((0,0,-.3)),m['front']),
                thin_shim_access_and_inward_path=hits,
                shim_follows_module_withdrawal=tool_withdrawal,
                held_tool_hook_overlap_mm3=common_volume(released_pick,rel),
                relaxed_after_minus1_pull_overlap_mm3=common_volume(pair['tongue'].translate((0,0,-1)),m['front']),
                relaxed_after_full_pull_overlap_mm3=common_volume(pair['tongue'].translate((0,0,-q['local_pull_before_relax_mm'])),m['front']),
                effective_beam_length_mm=q['beam_tip_z_mm']-q['beam_root_z_mm'],beam_thickness_mm=q['beam_thickness_mm'],
                smoothstep_linear_strain_estimate=3*q['beam_thickness_mm']*q['release_deflection_mm']/(q['beam_tip_z_mm']-q['beam_root_z_mm'])**2,
                physical_acceptance='UNVERIFIED: 0.15mm external shim availability/stiffness, actual ramp force, root fillet, creep, fatigue, four-shim handling; no cycle-life claim'))
    # Exact planar-face translation envelope preserves screw holes and latch channels.
    # All curved faces of this rear geometry are Z-parallel; no rounded Z skins.
    rearpath=axial_sweep(fixedrear,(0,0,-1),p['assembly_translation_mm'])
    rearhits=clashes(rearpath,[('FRONT',m['front']),*parked.items()],tol)
    moving=[]
    for k,s in [*accessories,*[(f'screw_{i}',s) for i,s in enumerate(m['screws'])]]:
        # The bundle's tight box may give a false positive; any such hit blocks,
        # rather than being discarded as an acceptable approximation.
        obstacles=[('FRONT',m['front']),*parked.items()]
        swept=[translated_box_sweep(s,(0,0,-p['assembly_translation_mm']))];coverage=None
        if '_wire_' in k:
            # Exact BRep strips partition the ENTIRE tube before conservative
            # Z sweeps, so a bend's enormous whole-wire AABB is not used as if
            # it were real material. Sum-volume check prevents omitted material.
            b=bounds(s);r=base['wire_bundle_radius_mm'];datum=k.split('_wire_')[0]
            sy=base['speaker']['center_xy_mm'][1]
            ys=sorted(set([b[1],b[4]]+[max(b[1],min(b[4],y)) for y in [sy-1.3,sy+1.3]]+[max(b[1],min(b[4],pt[1]+d)) for pt in wiredata[datum]['wire_centerline_polyline_before_fillets_mm'][0] for d in [-r,0,r]]))
            pieces=[]
            for a,z in zip(ys,ys[1:]):
                if z-a>1e-6:pieces+=list(intersection(s,box([b[0]-.1,a,b[2]-.1,b[3]+.1,z,b[5]+.1])).solids())
            coverage=abs(sum(v.volume for v in pieces)-s.volume)/s.volume
            assert coverage<1e-6
            swept=[translated_box_sweep(piece,(0,0,-p['assembly_translation_mm'])) for piece in pieces]
        hits=[hit for sweep in swept for hit in clashes(sweep,obstacles,tol)]
        moving.append(dict(part=k,continuous_module_insertion=hits,wire_partition_relative_volume_error=coverage))
    bb={k:bounds(s) for k,s in [('original_all',parts['ASSEMBLY']),*installed,*[(f'screw_{i}',s) for i,s in enumerate(m['screws'])],*[(k+'_parked',s) for k,s in parked.items()]]}
    lo=min(b[2] for b in bb.values());hi=max(b[5] for b in bb.values());xmin=min(b[0] for b in bb.values());xmax=max(b[3] for b in bb.values())
    usb=clashes(m['usbprobe'],[('FRONT',m['front']),('REAR',m['rear']),*source],tol)
    tb=bounds(parts['TF']);y=(tb[1]+tb[4])/2;z=(tb[2]+tb[5])/2
    tf=box([base['outer_x_min_mm']-20,y-5.5,z-.5,tb[0],y+5.5,z+.5]);tfhits=clashes(tf,[('FRONT',m['front']),('REAR',m['rear']),*source],tol)
    stop_witness=[common_volume(s,m['rear'].translate((0,0,.05))) for s in m['stops']]
    fail=bool(path or any(installed_source.values()) or pairs or rearhits or any(r['continuous_module_insertion'] for r in moving) or usb or tfhits)
    fail=fail or any(r['parked_vs_front_and_rear'] or r['outward_staging_continuous'] or r['candidate_inward_0_4_shell_motion'] for r in caps)
    fail=fail or any(r['nonmating_source_collisions'] or r['rear_clearance'] or r['rear_tool_path'] or r['metal_contact_probe_volume_mm3']<=0 for r in screwrows)
    retained_z_max=hi-lo+p['latch']['groove_axial_clearance_mm']
    fail=fail or retained_z_max>p['maximum_thickness_mm']+1e-6 or not all(v>tol for v in stop_witness)
    if include_latches:fail=fail or any(not r['root_fixed_held_valid'] or r['root_fixed_held_vs_source'] or r['continuous_held_insertion'] or r['full_deflection_return_envelope'] or r['thin_shim_access_and_inward_path'] or r['shim_follows_module_withdrawal'] or r['held_tool_hook_overlap_mm3']>tol or r['relaxed_pull_minus0_01_overlap_mm3']<=tol or r['relaxed_after_full_pull_overlap_mm3']>tol for r in latches)
    report=dict(status='BLOCKED_ASSEMBLY_GATE' if fail else 'NOMINAL_GEOMETRY_GATE_PASS',official_solids=len(source),
        complete_original_continuous_insertion=path,installed_source_collisions=installed_source,installed_pair_collisions=pairs,
        cap_sequence=caps,four_M2_5=screwrows,hidden_latches=latches,noncompliant_rear_continuous_insertion=rearhits,moving_with_rear=moving,
        complete_bounds=dict(z_min_mm=lo,z_max_mm=hi,maximum_thickness_mm=hi-lo,x_min_mm=xmin,x_max_mm=xmax,maximum_width_including_parked_caps_mm=xmax-xmin,
            nominal_retained_axial_play_mm=p['latch']['groove_axial_clearance_mm'],maximum_thickness_including_nominal_retained_play_mm=retained_z_max),
        independent_closure_stop_plus0_05_contact_volumes_mm3=stop_witness,
        glass_to_lip_nominal_gap_mm=m['dimensions']['lipbase_z_mm']-m['dimensions']['glass_z_mm'],
        USB_independent_plug=usb,TF_independent_card=tfhits,wiring=wiredata,
        limits=['All dimensions nominal; glass .25mm axial gap, parked key lateral gap ~.074mm do not absorb PA12 and board tolerances.',
                'Zero nominal hook/shoulder axial play is required for the 12.9mm limit. A .1mm rearward latch gap would allow 13.0mm. Zero axial tolerance-fit is NOT manufacturing-qualified.',
                'The .15mm radial screw-bore clearance exceeds the .074mm cap margin. A -.1mm PCB/REAR offset is a negative insertion witness, not a passed robustness check. Manual XY alignment must be verified before tightening; self-location and tolerance robustness NOT proven.',
                'Screw seats carry board independently from FRONT: head -> .8mm printed annulus -> original metal. Four coplanar bearing sites constrain Z/pitch/roll; shaft bores allow nominal .15mm XY float. Clamp friction/torque/thread depth unverified.',
                'Keep all four tongues held with external shims before STRAIGHT withdrawal. No claimed flexible sequential whole-lid peeling with the glass attached.',
                'Speaker rear pads support provisional damping; final foam has zero nominal compression. Actual speaker/cell/plugs/lead exits/lead retention unverified.',
                'MIC1 port direction/acoustics, TF eject distance, real switch travel/return, active display/touch boundary remain unverified.'])
    return report,held,accessories,parked
