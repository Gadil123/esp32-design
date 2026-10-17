"""Native exported G-V1 CAD, full-source sections and matched frozen-E views."""
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from build123d import import_step,Axis,Compound
from t0_g_v1_integrated_drawings import section
from t0_g_v1_preview import panel
from p1_checks import intersection,common_volume,clashes
from model import box_between as box
from reference import bounds


def render(out,parts,mounts,m,base,kq,q,report,held,accessories):
    front=import_step(out/'front_shell.step');rear=import_step(out/'rear_shell.step')
    fc,rc,metal,glass='#526d7b','#9aa6ad','#c1c9cc','#14222b'
    visible=[(parts[k],glass if k=='DISPLAY' else '#b4bec2') for k in ['DISPLAY','PCB_BOARD','J2_USB_SIDE','KEY1','KEY2','KEY3','TF','MX0','MX1','MIC1']]+[(s,metal) for s in mounts]
    extras=[(s,'#b28661' if name in ['battery','protection'] else '#6e7f89') for name,s in accessories]
    screws=[(s,metal) for s in m['screws']];source=[(Compound(parts['ASSEMBLY'].solids()),'#b4bec2')]
    scene=[(front,fc),(rear,rc),*visible,*screws,*extras]
    u=np.array([1.,0,-1]);u/=np.linalg.norm(u);w=np.array([1.,.8,1]);w/=np.linalg.norm(w);v=np.cross(w,u)
    views=[('FRONT',[1,0,0],[0,1,0],[0,0,1],(-34,75,-39,45),'FRONT +Z / USB +Y TOP'),
           ('REAR',[-1,0,0],[0,1,0],[0,0,-1],(-75,34,-39,45),'REAR -Z / USB +Y TOP'),
           ('LEFT',[0,0,1],[0,1,0],[-1,0,0],(-12.4,1.1,-39,45),'LEFT -X / FRONT right, REAR left / USB TOP'),
           ('ISO',u,v,w,(-35,70,-60,55),'ISO FRONT / USB +Y')]
    def save(fig,name):
        fig.tight_layout(rect=(0,0,1,.93),h_pad=3);fig.savefig(out/(name+'.png'),dpi=160);plt.close(fig)
    thick=report['complete_STEP_roundtrip']['maximum_thickness_mm'];bound=report['full_assembly_gate']['maximum_with_retained_rear_play_mm']
    from generate_t0_g_v1_integrated import shortened
    from t0_g_v1_integrated_keys import press_pose
    combined=q['registration_radial_clearance_mm']+kq['pcb_xy_radial_play_mm']
    reach=report['combined_register_bore_print_reach']['witnesses']
    for name,a,b,c,extent,title in views:
        fig,ax=plt.subplots(figsize=(11,8) if name!='LEFT' else (4,9));panel(ax,scene,a,b,c,extent)
        ax.set_title(f'G-V1 {title}\nNominal max {thick:.3f}mm / retained rigid bound {bound:.3f}mm / PA12 & function pending',fontsize=10)
        ax.set_xlabel('mm');ax.set_ylabel('mm');save(fig,name)
    fig,axs=plt.subplots(1,2,figsize=(12,6))
    for ax,row,witness in zip(axs,m['integrated_keys'],reach):
        error,_=shortened(row,kq);pose,_=press_pose(error,base,kq,kq['candidate_stop_mm'])
        native=parts[row['key']].translate((combined,0,0))
        panel(ax,[(pose,'#dfac49'),(native,metal)],[1,0,0],[0,0,1],[0,1,0],(-25.6,-23.5,row['z']-1.2,row['z']+1.2))
        ax.set_title(f'{row["key"]}: whole native BRep gap {witness["gap_at_shell_stop_mm"]:.4f}mm\nPCB +.350 X / tip -.300 / pad-stop1.400',fontsize=10)
        ax.set_xlabel('X mm / LEFT');ax.set_ylabel('Z / FRONT up, REAR down')
    fig.suptitle('CONDITIONAL PRINT-FIT WITNESS: register + bore play combined\nNot actual switch travel; no print or functioning-key approval');save(fig,'combined_register_bore_print_reach')
    # Named measurements on the EXPORTED STEP; never label an input value as
    # an independent global minimum-wall test.
    ox=base['outer_x_min_mm'];ex=ox+base['width_mm'];ey=base['outer_y_mm'][1];row=m['screw_rows'][0];x,y=row['axis_xy_mm'];floor=m['closure_dimensions']['rear_floor_mm'];rb=m['closure_dimensions']['rear_bottom_mm']
    def span(s,b,axis):
        bb=bounds(intersection(s,box(b)));return bb[axis+3]-bb[axis]
    ub=bounds(m['usbcut']);reset_y,reset_z=m['key_data']['KEY3']['center_yz_mm'];c0=m['rear_clips'][0]
    measured=dict(rear_main_panel_mm=span(rear,[-.02,-.02,-12,.02,.02,-9],2),
        rear_outer_rabbet_mm=span(rear,[ox+.3,-.02,-12,ox+.4,.02,-10],2),
        M2_5_bearing_seat_mm=span(rear,[x+1.98,y-.02,-12,x+2.02,y+.02,-9.4],2),
        USB_lower_web_mm=span(front,[-.02,ey-.3,-12,.02,ey-.25,ub[2]+.02],2),
        RESET_wall_off_bore_mm=span(front,[ox-.1,reset_y+1.3,reset_z-.02,ox+2,reset_y+1.4,reset_z+.02],0),
        right_release_relief_outer_wall_mm=span(front,[69.2,c0['y']-.02,-9.8,ex+.1,c0['y']+.02,-9.75],0),
        right_receiver_backing_mm=span(front,[65.7,c0['y']-.02,-9.0,66.8,c0['y']+.02,-8.95],0),
        right_receiver_floor_mm=span(front,[67.2,c0['y']-.02,floor-.1,67.25,c0['y']+.02,q['hook_z_mm'][0]-.1],2))
    report['exported_named_local_features']=measured
    report['exported_named_local_features_note']='Named true STEP sections only, not a global minimum-wall certificate or supplier approval.'
    # Glass/frame flush section and whole-device YZ thickness through USB.
    fig,axs=plt.subplots(1,2,figsize=(14,6))
    slab=box([-31,-.04,-12,-22,.04,1]);items=[(front,fc),(rear,rc),*source]
    panel(axs[0],[(section(s,slab),c) for s,c in items],[1,0,0],[0,0,1],[0,1,0],(-30,-22,-12,1))
    axs[0].axhline(.7,ls='--',lw=.7,color='#777');axs[0].set_title('Glass +.700 = FRONT +.700\nThrough window / .600 lateral gap / no lip');axs[0].set_xlabel('X mm');axs[0].set_ylabel('Z / FRONT up, REAR down')
    slab=box([-.04,-37,-12,.04,43,1])
    panel(axs[1],[(section(s,slab),c) for s,c in items],[0,1,0],[0,0,1],[1,0,0],(-36,42,-12,1))
    axs[1].set_title(f'Full original reference YZ section X=0\nUSB frame included: nominal {thick:.3f} / rigid bound {bound:.3f}',fontsize=10)
    axs[1].set_xlabel('Y mm / USB +Y');axs[1].set_ylabel('Z / FRONT up, REAR down');save(fig,'flush_and_thickness_sections')
    fig,ax=plt.subplots(figsize=(8,7));slab=box([x-4,y-.04,-12,x+4,y+.04,-3])
    panel(ax,[(section(s,slab),c) for s,c in [*items,*screws]],[1,0,0],[0,0,1],[0,1,0],(x-4,x+4,-12,-3))
    ax.set_title(f'Native M2.5x4: head .850 candidate / bearing {row["seat_mm"]:.3f}mm\nNominal engagement {row["nominal_engagement_mm"]:.3f} / rear face {rb:.3f}\nHead -> PA12 -> native metal; torque & effective thread pending',fontsize=10)
    ax.set_xlabel('X mm');ax.set_ylabel('Z / FRONT up, REAR down');save(fig,'four_screw_load_section')
    # Closed / released lower latch, exact geometry; fixed rear and source stay.
    fig,axs=plt.subplots(1,2,figsize=(12,7));row=m['rear_clips'][0];slab=box([65.3,row['y']-.2,-12,70.4,row['y']+.2,-7.8]);fixed=rear-row['free']
    for ax,pieces,title in zip(axs,[[(rear,rc)],[(fixed,rc),(held[0],'#d2a757')]],['Closed: shallow tooth + positive axial gap','Held outward .500 / root-fixed point-load proxy']):
        panel(ax,[(section(s,slab),c) for s,c in [(front,fc),*pieces]],[1,0,0],[0,0,1],[0,1,0],(65.3,70.4,-12,-7.8))
        ax.set_title(title,fontsize=10);ax.set_xlabel('X mm');ax.set_ylabel('Z / FRONT up, REAR down')
    fig.suptitle('LOWER LATCH actual Y slab +/- .2mm / no four simultaneous release shims');save(fig,'shallow_latch_sections')
    render_opening(out,parts,mounts,m,q,report,held)
    # Native interfaces: both exterior projections are real CAD.
    fig,axs=plt.subplots(1,2,figsize=(14,7));panel(axs[0],scene,[-1,0,0],[0,0,1],[0,1,0],(-72,32,-12,1))
    axs[0].set_title('TOP +Y / FRONT up / mirrored X\nIndependent plug12.2x6.3 checked / real plug pending');axs[0].set_xlabel('-X mm');axs[0].set_ylabel('Z / FRONT up, REAR down')
    panel(axs[1],scene,[0,0,1],[0,1,0],[-1,0,0],(-12,1,-35,15));axs[1].set_title('LEFT -X / FRONT right\nTF, two integrated keys, RESET pinhole');axs[1].set_xlabel('Z mm');axs[1].set_ylabel('Y mm / USB TOP');save(fig,'native_interfaces')
    fig,ax=plt.subplots(figsize=(11,8));panel(ax,[(front,fc),*source,*extras],[-1,0,0],[0,1,0],[0,0,-1],(-75,34,-39,45))
    for text,xy,pos in [('MIC1 port / audio UNVERIFIED',(-22.8,1.4),(-65,0)),('MX0 mouth -X / identity pending',(-17.44,24.3),(-62,31)),('MX1 mouth -X / identity pending',(-17.44,-19.5),(-63,-36)),('cell / protection UNVERIFIED',(-48.4,14.5),(-64,43))]:ax.annotate(text,xy,pos,fontsize=8,arrowprops={'arrowstyle':'->'})
    ax.set_title('REAR cutaway / lid hidden / ALL original723 solids\nConditional BAT/SPK lead envelopes; no verified plug/polarity/terminal or acoustic path');ax.set_xlabel('mirrored X mm');ax.set_ylabel('Y mm / USB TOP');save(fig,'connector_and_accessory_layout')
    # Frozen E from its independent STEP, same vectors/axes/extents per column.
    ep=out.parents[1]/'deliverables/t0-e';ef=import_step(ep/'front_shell.step');er=import_step(ep/'rear_shell.step');ec=[(import_step(ep/f'key{i}_cap.step'),fc) for i in [1,2,3]]
    e_scene=[(ef,fc),(er,rc),*visible,*ec]
    g_exterior=[(front,fc),(rear,rc),*visible,*screws]
    fig,axs=plt.subplots(2,5,figsize=(23,11),gridspec_kw={'width_ratios':[1,1,.35,1.05,.75]})
    for ri,(label,items) in enumerate([('E frozen',e_scene),('G-V1 candidate',g_exterior)]):
        for ci,(_,a,b,c,extent,title) in enumerate(views):panel(axs[ri,ci],items,a,b,c,extent);axs[ri,ci].set_title(label+' / '+title,fontsize=8)
        axs[ri,4].axis('off')
    axs[0,4].text(0,.95,'E unchanged\n99.60x77.86 body\n101.50 incl caps\n12.400 nominal\n3 PCB clips / 4 nests\n5 shell teeth\n3 separate caps\nPCB first, caps next\nManufacture/function pending',va='top',fontsize=10,linespacing=1.7)
    axs[1,4].text(0,.95,f'G-V1\n99.60x77.86 complete\n{thick:.3f} closed max\n{bound:.3f} rigid pose bound\n4 native M2.5 screws\n2 diagonal shallow latches\n2 integral PA12 keys\nNo cap assembly step\nSame pick used twice\nPA12/function pending',va='top',fontsize=10,linespacing=1.7)
    fig.suptitle('E / G-V1 same mm scale per column / native CAD, no concept rendering\nExterior comparison: provisional accessories/harness hidden in BOTH rows; E shells/caps unchanged');save(fig,'E_vs_G_V1_same_scale')


def render_opening(out,parts,mounts,m,q,report,held):
    """Actual exported shells; unclipped tool and case, selected native solids."""
    front=import_step(out/'front_shell.step');rear=import_step(out/'rear_shell.step')
    fc,rc='#526d7b','#9aa6ad';floor=m['closure_dimensions']['rear_floor_mm']
    visible=[(parts[k],'#b4bec2') for k in ['DISPLAY','PCB_BOARD','J2_USB_SIDE','KEY1','KEY2','KEY3','TF','MX0','MX1','MIC1']]+[(s,'#c1c9cc') for s in mounts]
    # One tool, lower first then upper. NO PCB attached to lid after screws out.
    py=q['upper_bearing_pivot_y_mm'];pz=floor;angle=report['full_assembly_gate']['first_lift_degrees'];axis=Axis((0,py,pz),(1,0,0))
    rear0=rear-m['rear_clips'][0]['free']+held[0]
    rear1=rear.rotate(axis,angle)
    rear2=(rear-m['rear_clips'][1]['free']+held[1]).rotate(axis,angle).translate((0,0,-8))
    uu=np.array([-1.,0,-1]);uu/=np.linalg.norm(uu);ww=np.array([1.,.8,-1]);ww/=np.linalg.norm(ww);vv=np.cross(ww,uu)
    fig,axs=plt.subplots(1,3,figsize=(18,8))
    for i,(ax,cover,title) in enumerate(zip(axs,[rear0,rear1,rear2],['1: screws OUT / lower pick release','2: lower corner2.2mm / lower tooth relaxed','3: SAME pick to upper U-slot / lid withdrawn'])):
        rows=[(front,fc),(cover,rc),*visible]
        if i in [0,2]:
            n=0 if i==0 else 1;row=m['rear_clips'][n];tr=report['full_assembly_gate']['single_pick'][n];a=row['clip_x_mm'][0];ty=row['root_y']+row['direction']*q['clip_tool_point_from_root_mm']
            from t0_g_v1_closure import released
            _,point,theta=released(row,m,q)
            pick=row['pick'].rotate(Axis((a,ty,0),(0,0,1)),theta).translate((point,0,0))
            if i==2:pick=pick.rotate(axis,angle).translate((0,0,-8))
            rows.append((pick,'#d4ae57'))
        panel(ax,rows,uu,vv,ww,(-80,70,-95,75));ax.set_title(title,fontsize=10);ax.set_xlabel('mm');ax.set_ylabel('mm')
    fig.suptitle('ISO REAR / USB +Y / ONE .8mm plastic pick moved sequentially\nNative PCB/display/mounts shown; other original components hidden. Full723-solid checks are separate\nPCB stays in FRONT on soft support; real tool force and lead service slack pending');fig.tight_layout(rect=(0,0,1,.90),h_pad=3);fig.savefig(out/'single_pick_opening_sequence.png',dpi=160);plt.close(fig)
