"""Independent material, motion, capture and service gates for printed sliders."""
import math
from build123d import GeomType
from OCP.BRepAdaptor import BRepAdaptor_Surface
from model import box_between as box
from reference import bounds
from p1_checks import intersection
from g_v4_interfaces import xcyl
from g_v4_printed_keys import table


def annulus(ro,ri,x0,x1,y,z):
    return xcyl(ro,x0,x1,y,z)-xcyl(ri,x0-.01,x1+.01,y,z)


def windows(plate,v):
    import g_v4_checks as C
    k=v['printed_keys'];t=table(v);rows=[]
    for y in k['y_mm']:
        hole=xcyl(t['aperture_d']/2-.001,t['exterior_x']-.01,t['outer_x']+.01,y,k['z_center'])
        capture=annulus(k['flange_diameter_mm']/2-.01,t['aperture_d']/2+.01,
                        t['exterior_x']+.02,t['outer_x']-.02,y,k['z_center'])
        rows.append(dict(y_mm=y,full_window_mm3=C.clear(plate,hole,'slider retainer window'),
                         capture_ring_mm3=C.material(plate,capture,'slider outer capture')))
    p=v['reset_pinhole']
    reset=xcyl(p['diameter_mm']/2-.001,t['exterior_x']-.01,t['outer_x']+.01,p['y_mm'],p['z_mm'])
    return dict(keys=rows,reset_mm3=C.clear(plate,reset,'slider retainer RESET'))


def pockets(front,v):
    import g_v4_checks as C
    k=v['printed_keys'];t=table(v);rows=[];z=k['z_center']
    for y in k['y_mm']:
        counter=xcyl(t['pocket_d']/2-.001,t['outer_x']-.01,t['seat_x']-.001,y,z)
        guide=xcyl(t['guide_d']/2-.001,t['seat_x']-.001,t['inner_x']+.01,y,z)
        stop=annulus(k['flange_diameter_mm']/2-.02,t['guide_d']/2+.02,
                     t['seat_x']+.02,t['seat_x']+.06,y,z)
        bridge_mm=z-t['pocket_d']/2-k['local_seam_z_mm']
        assert bridge_mm>=k['bridge_required_mm']-1e-7,('slider bridge',bridge_mm)
        bridge=box([t['outer_x']+.05,y-.25,k['local_seam_z_mm']+.01,
                    t['seat_x']-.05,y+.25,z-t['pocket_d']/2-.01])
        rows.append(dict(y_mm=y,counter_mm3=C.clear(front,counter,'slider full pocket'),
                         guide_mm3=C.clear(front,guide,'slider full guide'),
                         stop_ring_mm3=C.material(front,stop,'slider inner stop'),
                         bridge_mm=bridge_mm,bridge_material_mm3=C.material(front,bridge,'slider bridge material')))
    return rows


def measured_motion(shape,v,y,switch):
    """Derive flange faces and tip from the actual slider, including STEP rereads."""
    import g_v4_checks as C
    k=v['printed_keys'];t=table(v);z=k['z_center'];b=bounds(shape);sx=bounds(switch)[0]
    rim=intersection(shape,annulus(k['flange_diameter_mm']/2-.02,
        max(k['head_diameter_mm'],k['stem_diameter_mm'])/2+.05,
        t['outer_x']-.1,t['seat_x']+.1,y,z))
    assert rim.volume>1e-6,'slider flange missing'
    fb=bounds(rim);stroke=t['seat_x']-fb[3];gap=sx-b[3]
    assert abs(fb[0]-t['outer_x'])<1e-5,'slider outward stop plane'
    assert .2<stroke<.9,('slider travel',stroke)
    assert gap>=.05-1e-6,('slider resting preload',gap)
    hit=C.overlap(shape.translate((stroke,0,0)),switch)
    assert hit>1e-6,('slider reaches switch',gap,stroke,hit)
    assert b[0]<t['exterior_x']-.5,'slider finger access'
    return dict(flange_x_mm=fb[0::3],actual_tip_x_mm=b[3],switch_tip_x_mm=sx,
                rest_gap_mm=gap,geometric_stroke_mm=stroke,
                switch_displacement_at_stop_mm=stroke-gap,
                static_switch_overlap_at_stop_mm3=hit,
                exposed_head_mm=t['exterior_x']-b[0],
                actual_switch_travel_mm=k['switch_actuation_travel_mm'],
                max_safe_switch_displacement_mm=k['switch_max_safe_displacement_mm'],
                status='GEOMETRIC_CONTACT_PASS_SWITCH_TRAVEL_FORCE_UNVERIFIED')


def axial_sweep(shape,travel):
    """Continuous +X union derived from actual coaxial cylindrical faces.

    No builder cutters reused. This gate rejects added non-cylindrical profiles
    instead of silently omitting them from a sweep.
    """
    import g_v4_checks as C
    pieces=[]
    for f in shape.faces():
        if f.geom_type!=GeomType.CYLINDER:continue
        a=f.axis_of_rotation
        assert abs(a.direction.X)>.99999,'slider has non-axial cylinder'
        r=BRepAdaptor_Surface(f.wrapped).Cylinder().Radius();b=bounds(f)
        pieces.append(xcyl(r,b[0],b[3]+travel,a.position.Y,a.position.Z))
    assert pieces,'slider cylindrical sweep missing'
    result=pieces[0]
    for piece in pieces[1:]:result+=piece
    C.clear(shape,result-shape,'slider sweep subtraction consistency')
    missing=shape-result
    assert missing.volume<1e-6,('slider sweep omitted material',missing.volume)
    return result


def check(m,parts,v):
    import g_v4_checks as C
    k=v['printed_keys'];r=k['retainer'];t=table(v);z=k['z_center'];result={}
    result['retainer']=windows(m['key_bezel'],v);result['pockets']=pockets(m['front'],v)
    result['keys']={};result['variant_parts']={};result['retainer_screws']=[]
    for i,y in enumerate(k['y_mm'],1):
        key=f'KEY{i}';switch=parts[key];sx=bounds(switch)[0]
        # The ONLY allowed static overlap is the modelled actuator, not its frame,
        # the board edge, glass, or an arbitrarily enlarged switch envelope.
        mask=box([sx-.001,y-1.02,-6.91,sx+.81,y+1.02,-5.89])
        actuator=intersection(switch,mask)
        scope=box([-38,y-5,z-5,-23.5,y+5,z+5])
        local_obstacles=intersection(parts['ASSEMBLY'],scope)-actuator
        for label in k['variants_mm']:
            name=f'button_{"power" if i==1 else "boot"}_{label}';shape=m['button_exports'][name]
            row=measured_motion(shape,v,y,switch);travel=row['geometric_stroke_mm']
            swept=axial_sweep(shape,travel)
            row['continuous_axial_sweep']={n:C.clear(m[n],swept,'slider sweep '+n) for n in ['front','rear','key_bezel']}
            row['non_actuator_board_sweep_mm3']=C.clear(swept,local_obstacles,'slider sweep non-actuator board')
            row['rest_board_mm3']=C.clear(shape,parts['ASSEMBLY'],'slider at rest board')
            row['screw_sweep_mm3']=max([C.clear(s,swept,'slider vs locked screw') for s in [*m['screws'],*m['retainer_screws']]]+[0])
            # Continuous outside extraction: each actual cylinder extended -X.
            extraction=axial_sweep(shape.translate((-15,0,0)),15)
            row['continuous_extraction']={n:C.clear(m[n],extraction,'slider extraction '+n) for n in ['front','rear']}
            row['extraction_board_mm3']=C.clear(extraction,parts['ASSEMBLY'],'slider extraction board')
            assert C.overlap(m['key_bezel'],shape.translate((-.1,0,0)))>1e-5,'slider outward retention missing'
            assert C.overlap(m['front'],shape.translate((travel+.1,0,0)))>1e-5,'slider inward stop missing'
            row['outward_and_inward_stop_blocked']=True
            result['variant_parts'][name]=row
            if label=='nominal':
                result['keys'][key]=row
                radial=[]
                # Bound the nominal translational play; no claim about tilt or
                # supplier tolerances is made by these deliberately named poses.
                for angle in range(0,360,45):
                    dy=k['radial_clearance_mm']*math.cos(math.radians(angle))*.99
                    dz=k['radial_clearance_mm']*math.sin(math.radians(angle))*.99
                    moved=swept.translate((0,dy,dz))
                    radial.append(dict(offset_yz_mm=[dy,dz],non_actuator_board_mm3=C.clear(moved,local_obstacles,'slider radial play vs board'),
                        shells_mm3={n:C.clear(m[n],moved,'slider radial play '+n) for n in ['front','rear','key_bezel']}))
                row['radial_translation_poses']=radial
    for y,zs in r['fastener_yz_mm']:
        hs=t['exterior_x'];tip=hs+r['screw_length_mm']
        head=xcyl(r['head_max_diameter_mm']/2,hs-r['head_max_height_mm'],hs,y,zs)
        tool=xcyl(1.4,hs-15,hs-.01,y,zs)
        bottom=xcyl(r['pilot_mm']/2-.01,t['outer_x']+r['pilot_depth_mm']+.02,t['outer_x']+r['pilot_depth_mm']+.22,y,zs)
        assert t['outer_x']+r['pilot_depth_mm']-tip>=.8
        result['retainer_screws'].append(dict(yz_mm=[y,zs],pilot_mm3=C.clear(m['front'],xcyl(r['pilot_mm']/2-.01,t['outer_x']+.01,t['outer_x']+r['pilot_depth_mm']-.01,y,zs),'slider retainer pilot'),
            passage_mm3=C.clear(m['key_bezel'],xcyl(r['screw_diameter_mm']/2+.149,hs-.01,t['outer_x']+.001,y,zs),'slider retainer screw passage'),
            bottom_material_mm3=C.material(m['front'],bottom,'slider retainer blind bottom'),
            head_vs_shells_mm3={n:C.clear(m[n],head,'slider retainer head '+n) for n in ['front','rear','key_bezel']},
            tool_vs_shells_mm3={n:C.clear(m[n],tool,'slider retainer tool '+n) for n in ['front','rear','key_bezel']},
            bottom_clearance_mm=t['outer_x']+r['pilot_depth_mm']-tip))
    for rs in m['retainer_screws']:
        C.clear(rs,parts['ASSEMBLY'],'slider retainer screw board')
        for s in m['screws']:C.clear(rs,s,'slider retainer orthogonal screws')
    p=v['reset_pinhole'];sx=bounds(parts['KEY3'])[0]
    needle=xcyl(p['tool_diameter_mm']/2,t['exterior_x']-.01,sx+.02,p['y_mm'],p['z_mm'])
    reach=sx-t['exterior_x'];assert p['tool_free_length_mm']>reach+.5
    result['reset']={n:C.clear(m[n],needle,'RESET through '+n) for n in ['front','rear','key_bezel']}
    for key,shape in m['buttons'].items():result['reset'][key]=C.clear(shape,needle,'RESET vs slider')
    result['reset']['other_parts_mm3']={name:C.clear(parts[name],needle,'RESET non-target '+name) for name in ['KEY1','KEY2','DISPLAY','PCB_BOARD','TF']}
    result['reset'].update(reach_from_retainer_exterior_mm=reach,tool_free_length_mm=p['tool_free_length_mm'],contact_mm3=C.overlap(needle,parts['KEY3']))
    assert result['reset']['contact_mm3']>0
    result['functional_status']='NOMINAL_GEOMETRIC_REACH_PASS_PHYSICAL_RETURN_AND_SWITCH_TRAVEL_UNVERIFIED'
    result['release_behavior']='0..rest_gap is unforced free play; switch return alone does not force the cap against its outer stop. Friction, rattle and actual electrical activation require physical verification.'
    result['limits']='Axis translation is continuous; radial samples are discrete, not a tilt/fatigue/friction proof. Unknown switch ratings remain null.'
    return result


def negative_controls(m,parts,v):
    import g_v4_checks as C
    k=v['printed_keys'];t=table(v);z=k['z_center'];rows=[]
    def reject(name,call,expected):
        try:call()
        except AssertionError as exc:
            assert expected in str(exc),('wrong negative control reason',name,str(exc))
            rows.append(dict(mutation=name,rejected=True,reason=str(exc)))
        else:raise AssertionError(('slider gate missed mutation',name))
    for i,y in enumerate(k['y_mm'],1):
        seal=xcyl(t['aperture_d']/2,t['exterior_x'],t['outer_x'],y,z)
        reject(f'KEY{i} retainer window sealed',lambda:windows(m['key_bezel']+seal,v),'slider retainer window')
        seal=xcyl(t['guide_d']/2,t['seat_x'],t['inner_x'],y,z)
        reject(f'KEY{i} guide sealed',lambda:pockets(m['front']+seal,v),'slider full guide')
        cut=xcyl(t['pocket_d']/2,t['seat_x']-.01,t['inner_x']+.01,y,z)
        reject(f'KEY{i} inner stop removed',lambda:pockets(m['front']-cut,v),'slider inner stop')
        cut=xcyl(k['flange_diameter_mm']/2+.01,t['exterior_x']-.01,t['outer_x']+.01,y,z)
        reject(f'KEY{i} outer capture removed',lambda:windows(m['key_bezel']-cut,v),'slider outer capture')
        sx=bounds(parts[f'KEY{i}'])[0];cap=m['buttons'][f'KEY{i}']
        cut=box([sx-.8,y-5,z-5,sx+1,y+5,z+5])
        reject(f'KEY{i} tip shortened',lambda:measured_motion(cap-cut,v,y,parts[f'KEY{i}']),'slider reaches switch')
        bad=cap+xcyl(k['tip_diameter_mm']/2,sx-.3,sx+.1,y,z)
        reject(f'KEY{i} tip preloads switch',lambda:measured_motion(bad,v,y,parts[f'KEY{i}']),'slider resting preload')
    p=v['reset_pinhole'];seal=xcyl(p['diameter_mm']/2,t['exterior_x'],t['outer_x'],p['y_mm'],p['z_mm'])
    reject('RESET sealed in retainer',lambda:windows(m['key_bezel']+seal,v),'slider retainer RESET')
    return rows
