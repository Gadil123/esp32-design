"""Conditional geometry screening, never a print/process qualification."""
from model import box_between
from reference import bounds
from p1_checks import common_volume, intersection


def feature_metrics(features):
    sizes={name:[b[i+3]-b[i] for i in range(3)]
           for name,shape in features.items() for b in [bounds(shape)]}
    body,flange,tip=sizes['body'],sizes['flange'],sizes['contact']
    transition=sizes['transition']
    return {'body_section_mm':min(body[1:]),'body_length_mm':body[0],
            'body_slenderness':body[0]/min(body[1:]),'flange_thickness_mm':flange[0],
            'contact_thickness_mm':min(tip[1:]),'contact_flat_length_mm':tip[0],
            'contact_projection_mm':tip[0]+transition[0],
            'contact_slenderness':(tip[0]+transition[0])/min(tip[1:])}


def screen(metrics,profile):
    l=profile['engineering_screening_limits'];eps=1e-5
    return {'body_section':metrics['body_section_mm']>=l['body_min_section_mm']-eps,
            'body_slenderness':metrics['body_slenderness']<=l['body_max_slenderness']+eps,
            'flange_thickness':metrics['flange_thickness_mm']>=l['flange_min_thickness_mm']-eps,
            'local_contact_thickness':metrics['contact_thickness_mm']>=l['local_contact_min_thickness_mm']-eps,
            'local_contact_projection':metrics['contact_projection_mm']<=l['local_contact_max_projection_mm']+eps,
            'local_contact_slenderness':metrics['contact_slenderness']<=l['local_contact_max_slenderness']+eps}


def tolerance_budget(p,profile):
    t=profile['conditional_tolerance_budget'];e=t['per_part_size_error_mm'];f=t['per_face_position_error_mm'];r=t['cleanup_reserve_mm']
    # Aperture and cap size errors each contribute half to a centered per-side gap.
    # Both independent face position errors contribute fully to the head gap.
    return {'transverse_effective_per_side_mm':p['key_guide_clearance_mm']-e-r,
            'head_end_nominal_mm':p['key_head_motion_gap_mm']-p['key_cap_design_motion_mm'],
            'head_end_effective_mm':p['key_head_motion_gap_mm']-p['key_cap_design_motion_mm']-2*f-r,
            'axial_cavity_freeplay_mm':p['key_cap_design_motion_mm']+2*p['key_axial_clearance_mm'],
            'axial_extra_after_motion_and_errors_mm':2*p['key_axial_clearance_mm']-2*e,
            'cage_stock_after_size_error_mm':min(p['key_flange_rest_offset_mm']-p['key_axial_clearance_mm'],
                 p['wall_mm']+p['key_side_wall_extra_mm']-p['key_flange_rest_offset_mm']-p['key_flange_thickness_mm']-p['key_cap_design_motion_mm']-p['key_axial_clearance_mm'])-e}


def budget_pass(b,profile):
    l=profile['engineering_screening_limits'];eps=1e-5
    return (b['transverse_effective_per_side_mm']>=l['guide_effective_gap_min_mm']-eps
            and b['head_end_effective_mm']>=l['head_effective_gap_min_mm']-eps
            and b['axial_extra_after_motion_and_errors_mm']>=l['axial_extra_clearance_min_mm']-eps
            and b['cage_stock_after_size_error_mm']>=profile['published_sla_reference']['unsupported_wall_min_mm']-eps)


def validate_manufacturing(m,p,profile):
    checks={};metrics={}
    for key,features in m['cap_features'].items():
        mm=feature_metrics(features);metrics[key]=mm;tests=screen(mm,profile)
        fb=m['key_data'][key]['static_actuator_face_bounds_mm'];tb=bounds(features['contact'])
        mm['nominal_contact_face_edge_margins_yz_mm']=[min(tb[i]-fb[i],fb[i+3]-tb[i+3]) for i in [1,2]]
        mm['nominal_guide_float_per_side_mm']=p['key_guide_clearance_mm']
        mm['full_contact_coverage_for_all_guide_float']=all(v>=p['key_guide_clearance_mm'] for v in mm['nominal_contact_face_edge_margins_yz_mm'])
        # Measure the generated B-rep, and verify every measured feature belongs to its cap.
        contained=all(abs(common_volume(s,m['caps'][key])-s.volume)<1e-5 for s in features.values())
        checks[f'{key}_minimum_features']={'pass':all(tests.values()) and contained,
                    'criteria':tests,'measured_from_BRep':mm,'features_contained_in_cap':contained,
                    'scope':'conditional local feature screen; contact pad is a short exception to the 1mm long-pin rule, not strength qualified'}
    b=tolerance_budget(p,profile)
    checks['key_conditional_tolerance_budget']={'pass':budget_pass(b,profile),'budget':b,
            'nominal_transverse_gap_meets_published_reference':p['key_guide_clearance_mm']>=profile['published_sla_reference']['moving_gap_nominal_min_mm'],
            'supplier_confirmed':False,'includes_switch_datum_or_warp':False}
    checks['key_conditional_tolerance_budget']['pass'] &= checks['key_conditional_tolerance_budget']['nominal_transverse_gap_meets_published_reference']
    # Geometric mutations exercise the exact same feature reader and screening rules.
    good=m['cap_features']['KEY1'];bad=dict(good);bb=bounds(good['body'])
    bad['body']=box_between([bb[0],bb[1],bb[2],bb[3],bb[4],bb[2]+.5])
    thin_body=not all(screen(feature_metrics(bad),profile).values())
    bad=dict(good);bb=bounds(good['flange']);bad['flange']=box_between([bb[0],bb[1],bb[2],bb[0]+.4,bb[4],bb[5]])
    thin_flange=not all(screen(feature_metrics(bad),profile).values())
    bad=dict(good);bb=bounds(good['contact']);bad['contact']=box_between([bb[0]-1,bb[1],bb[2],bb[3],bb[4],bb[5]])
    long_tip=not all(screen(feature_metrics(bad),profile).values())
    fixtures={'legacy_thin_long_body':thin_body,'legacy_0_4mm_flange':thin_flange,'overlong_contact_pad':long_tip,
              'legacy_0_05mm_head_end_gap':not budget_pass(tolerance_budget({**p,'key_head_motion_gap_mm':.45},profile),profile),
              'legacy_0_15mm_guide_gap':not budget_pass(tolerance_budget({**p,'key_guide_clearance_mm':.15},profile),profile)}
    checks['manufacturing_negative_fixtures']={'pass':all(fixtures.values()),'fixtures':{k:{'detected':bool(v),'mutated_geometry_check_result':'FAIL' if v else 'PASS_UNEXPECTED'} for k,v in fixtures.items()}}
    # Comparison is intentionally not a PASS for FDM. Do not silently switch processes.
    fdm_ok=all(min(mm['contact_thickness_mm'],mm['flange_thickness_mm'])>=profile['fdm_comparison_min_wall_mm'] for mm in metrics.values())
    return checks,{'status':'manufacturing_unverified','candidate_profile':profile,
                   'conditional_key_feature_screen':'PASS' if all(v['pass'] for v in checks.values()) else 'FAIL',
                   'fdm_qualified':False,'fdm_minimum_feature_comparison_pass':fdm_ok,
                   'contact_strength_qualified':False,'switch_actuation_verified':False,
                   'off_axis_actuation_status':'UNVERIFIED','datum_preload_status':'UNVERIFIED',
                   'tolerance_budget':b,'metrics':metrics}


def make_coupon(m,profile):
    """Exact KEY1 guide crop and unchanged cap; local fixture, not a new mechanism."""
    yc,zc=m['key_data']['KEY1']['center_yz_mm'];hy,hz=profile['coupon_half_extent_yz_mm']
    cap=m['caps']['KEY1'];cb=bounds(cap)
    crop=box_between([cb[0]-.2,yc-hy,zc-hz,profile['coupon_inner_end_x_mm'],yc+hy,zc+hz])
    return {'coupon_front_guide':intersection(m['front'],crop),
            'coupon_rear_guide':intersection(m['rear'],crop),'coupon_key1_cap':cap}
