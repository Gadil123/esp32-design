"""CAD-measured contact gate; travel and process capability remain unverified."""
import math
from reference import bounds


def evaluate(parts,m,p,kp):
    result={}
    for key,data in m['key_data'].items():
        fb=data['static_actuator_face_bounds_mm'];tb=bounds(m['cap_features'][key]['contact'])
        c=kp['key_guide_clearance_mm'];outer=p['outer_x_min_mm']+(p.get('reset_face_stock_mm',.2) if data['function']=='RESET' else .2)
        # Both enclosures have wall material around the two stem-bearing ends;
        # the intervening flange pocket is relieved. A tightens these real guides.
        inner=data['body_end_x_mm']
        length=inner-outer;overhang=tb[3]+kp['key_cap_design_motion_mm']-inner
        outer_play=(kp['reset_hole_radius_mm']-p['reset_nose_radius_mm']) if data['function']=='RESET' and p.get('variant')=='A' else c
        angle=math.atan((outer_play+c)/length);worst=c+max(0,overhang)*math.tan(angle)
        size={i:tb[i+3]-tb[i] for i in [1,2]}
        # Inscribed rectangle of a doubly tilted pad projection: deduct cross-axis
        # shear as well as cosine foreshortening, rather than use an optimistic AABB.
        half={i:max(0,(size[i]*math.cos(angle)-size[3-i]*math.sin(angle)**2)/2) for i in [1,2]}
        center={i:(tb[i+3]+tb[i])/2 for i in [1,2]}
        samples=[]
        for dy in [-worst,worst]:
            for dz in [-worst,worst]:
                dims=[max(0,min(fb[i+3],center[i]+half[i]+v)-max(fb[i],center[i]-half[i]+v)) for i,v in [(1,dy),(2,dz)]]
                samples.append({'offset_yz_mm':[dy,dz],'overlap_yz_mm':dims,'overlap_area_mm2':dims[0]*dims[1]})
        area=(fb[4]-fb[1])*(fb[5]-fb[2]);minimum=min(t['overlap_area_mm2'] for t in samples)
        full=all(tb[i]-worst>=fb[i]-1e-6 and tb[i+3]+worst<=fb[i+3]+1e-6 for i in [1,2])
        result[key]={'status':'UNVERIFIED' if minimum>0 else 'FAIL','full_pad_coverage_gate':'PASS' if full else 'FAIL',
            'worst_case_positive_overlap_gate':'PASS' if minimum>0 else 'FAIL',
            'bearing_station_x_mm':[outer,inner],'per_side_nominal_play_mm':c,'outer_bearing_play_bound_mm':outer_play,
            'axial_candidate_envelope_mm':kp['key_cap_design_motion_mm'],
            'conservative_tilt_degrees':math.degrees(angle),'tip_offset_bound_mm':worst,
            'actuator_face_bounds_mm':fb,'pad_bounds_mm':tb,
            'minimum_actuator_area_fraction':minimum/area,'corners':samples,
            'scope':'CAD face bounds, opposing guide-end float gives conservative two-axis tilt envelope; not elastic/contact-force simulation. Contact overlap alone does not prove actuation.',
            'fixed_switch_body_and_tilted_contact_force':'UNVERIFIED',
            'actual_switch_travel_mm':None,'physical_return_and_off_axis_test_passed':False}
    return {'status':'FAIL' if any(v['status']=='FAIL' for v in result.values()) else 'FUNCTIONAL_UNVERIFIED',
            'keys':result,'qualified_functional_actuation':False}
