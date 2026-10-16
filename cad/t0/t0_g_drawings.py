"""Orthographic BRep drawings, exact section slabs and matched E/G scales."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from build123d import import_step, Polygon, extrude
from p1_preview import panel
from p1_checks import intersection, common_volume
from model import box_between as box
from reference import bounds


def render(out,parts,mounts,m,held,accessories,parked,base,kp,p,report):
    # Fresh exported topology avoids stale triangulation on coplanar boolean faces.
    m={**m,'front':import_step(out/'front_shell.step'),'rear':import_step(out/'rear_shell.step'),
       'caps':{k:import_step(out/(k.lower()+'_cap.step')) for k in m['caps']}}
    # Measure local features on freshly read STEP, rather than only echoing input
    # thickness parameters. These are named local sections, not a global medial-
    # axis minimum-wall certificate or manufacturing pass.
    def span(s,region,axis):
        b=bounds(intersection(s,box(region)));return b[axis+3]-b[axis]
    d=m['dimensions'];x,y=m['screw_rows'][0]['axis_xy_mm'];yc,zc=m['key_data']['KEY3']['center_yz_mm'];ox=base['outer_x_min_mm'];ex=ox+base['width_mm'];oy,ey=base['outer_y_mm']
    right=m['latch_pairs'][1];qy=right['site']['coordinate_mm'];groove_outer=right['outer']+p['latch']['groove_depth_mm'];ub=bounds(m['usbcut'])
    measured=dict(rear_plate_mm=span(m['rear'],[-.02,-.02,-12,.02,.02,-9],2),
        first_M2_5_bearing_annulus_axial_mm=span(m['rear'],[x+1.98,y-.02,-12,x+2.02,y+.02,-9.4],2),
        FRONT_lip_mm=span(m['front'],[25.19,-.02,.5,25.21,.02,1.5],2),
        RESET_face_off_hole_mm=span(m['front'],[ox-.1,yc+.78,zc-.02,ox+1,yc+.82,zc+.02],0),
        right_lower_blind_groove_outer_wall_mm=span(m['front'],[groove_outer-.1,qy-.02,-4.02,ex+.1,qy+.02,-3.98],0),
        right_lower_free_beam_mm=span(m['rear'],[right['inner']-.1,qy-.02,-6.52,right['outer']+.1,qy+.02,-6.48],0),
        USB_lower_web_mm=span(m['front'],[(ub[0]+ub[3])/2-.02,ey-.3,-12,(ub[0]+ub[3])/2+.02,ey-.26,ub[2]+.1],2))
    report['exported_STEP_named_local_feature_measurements']=measured
    report['exported_STEP_named_local_feature_measurements_note']='Measured actual section spans, no material/process acceptance. Other corners/root transitions may be thinner; no global minimum-wall claim.'
    # Opposed, non-glass zero-gap contacts must restrain rigid rear translation
    # AND pitch/roll; a thickness check of just two planes would miss lid tilt.
    contacts=[]
    for dz in [-.0001,.0001]:
        touch=intersection(m['front'],m['rear'].translate((0,0,dz)))
        xy=[(s.center().X,s.center().Y) for s in touch.solids() if s.volume>1e-10]
        assert len(xy)==4
        center=np.mean(xy,axis=0);xy.sort(key=lambda a:np.arctan2(a[1]-center[1],a[0]-center[0]))
        rank=int(np.linalg.matrix_rank([[1,y,-x] for x,y in xy]));assert rank==3
        contacts.append((xy,rank))
    hulls=[extrude(Polygon(*xy,align=None),amount=1,dir=(0,0,1)) for xy,_ in contacts]
    overlap=common_volume(*hulls);assert overlap>1
    report['exported_STEP_zero_axial_constraint']={'rearward_hook_contacts_xy_mm':contacts[0][0],
        'forward_shoulder_contacts_xy_mm':contacts[1][0],'both_contact_ranks': [q[1] for q in contacts],
        'opposed_contact_hull_overlap_mm2':overlap,'probe_dz_mm':.0001,
        'scope':'Opposed zero-nominal-gap contact hulls restrain rigid Z/pitch/roll. Not a physical stiffness, warp or manufacturing tolerance proof.'}
    front,rear,metal,glass='#424a52','#7f8991','#b8bec4','#171d23'
    source=[(parts[k],glass if k=='DISPLAY' else '#747d82') for k in ['DISPLAY','PCB_BOARD','J2_USB_SIDE','KEY1','KEY2','KEY3','TF','MIC1','MX0','MX1']]+[(s,metal) for s in mounts]
    # Exterior views only expose these source parts. Internal sections/layout
    # include EVERY original component, not a selected-components illustration.
    all_source=[(parts['ASSEMBLY'],'#747d82'),(parts['DISPLAY'],glass)]
    extra=[(s,'#9ca6ab' if k in ['battery','protection'] else '#606d78') for k,s in accessories]
    screws=[(s,metal) for s in m['screws']];caps=[(s,front) for s in m['caps'].values()]
    scene=[(m['front'],front),(m['rear'],rear),*source,*caps,*screws,*extra]
    u=np.array([1.,0,-1]);u/=np.linalg.norm(u);w=np.array([1.,.8,1]);w/=np.linalg.norm(w);v=np.cross(w,u)
    views=[('front',[1,0,0],[0,1,0],[0,0,1],(-35,75,-40,46),'FRONT +Z / USB +Y TOP'),
           ('rear',[-1,0,0],[0,1,0],[0,0,-1],(-75,35,-40,46),'REAR -Z / USB +Y TOP'),
           ('left',[0,0,1],[0,1,0],[-1,0,0],(-13,2,-40,46),'LEFT -X / FRONT right, REAR left / USB TOP'),
           ('iso_front',u,v,w,(-35,70,-60,55),'ISO FRONT / USB +Y')]
    def save(fig,name):
        fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=165);plt.close(fig)
    for name,a,b,c,ext,title in views:
        fig,ax=plt.subplots(figsize=(11,8) if name!='left' else (4,9));panel(ax,scene,a,b,c,ext)
        ax.set_title('T0 G '+title+'\n12.900mm full nominal max | active display/touch boundary UNVERIFIED | REVIEW ONLY',fontsize=11)
        ax.set_xlabel('mm');ax.set_ylabel('mm');save(fig,name)
    # Glass lip is a non-load-bearing .25mm skin, separated .25mm from glass.
    clip=box([-30,-.035,-13,-22,.035,2]);section=[(intersection(s,clip),c) for s,c in [(m['front'],front),(m['rear'],rear),*all_source]]
    fig,axs=plt.subplots(1,2,figsize=(13,6))
    panel(axs[0],section,[1,0,0],[0,0,1],[0,1,0],(-30,-22,-12,1.6))
    panel(axs[1],section,[1,0,0],[0,0,1],[0,1,0],(-26,-24.5,-.2,1.5))
    for ax in axs:
        for z in [.7,.95,1.2]:ax.axhline(z,lw=.6,ls='--',color='#737373')
        ax.set_xlabel('X mm / LEFT');ax.set_ylabel('Z mm / FRONT up, REAR down')
    axs[0].set_title('Deep sidewall / no PCB or glass axial clamp')
    axs[1].set_title('Glass +.700 / lip underside +.950 / FRONT +1.200\n.500 recess; .250 air gap; .150 overlap UNVERIFIED',fontsize=9)
    fig.suptitle('G SCREEN SECTION Y=0 / effective display & touch boundary UNVERIFIED');save(fig,'screen_recess_section')
    fig,axs=plt.subplots(1,2,figsize=(15,6));row=m['screw_rows'][0];x,y=row['axis_xy_mm'];slab=box([-33,y-.03,-13,72,y+.03,2])
    section=[(intersection(s,slab),c) for s,c in [(m['front'],front),(m['rear'],rear),*all_source,*screws,*extra]]
    panel(axs[0],section,[1,0,0],[0,0,1],[0,1,0],(-33,72,-13,2))
    panel(axs[1],section,[1,0,0],[0,0,1],[0,1,0],(x-4.2,x+4.2,-12,-3))
    axs[0].set_title('Complete true CAD section / max Z -11.700 to +1.200 = 12.900')
    axs[1].set_title('M2.5x4 / head D5 x H1.3\nhead -11.6..-10.3 / metal back -9.5\nPA12 .800 seat; nominal engagement 3.200',fontsize=10)
    for ax in axs:
        ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up, REAR down')
        for z in [-11.7,-10.3,-9.5,1.2]:ax.axhline(z,lw=.5,ls='--',color='#777777')
    fig.suptitle('G FOUR-SCREW LOAD PATH: head -> printed seat -> native metal; NOT FRONT / torque & creep UNVERIFIED');save(fig,'screw_and_thickness_section')
    # One actual blind-groove pair in the complete shell, not a conceptual sketch.
    i=1;y=p['latch']['sites'][i]['coordinate_mm'];slab=box([67,y-.03,-14,71,y+.03,2])
    fixed=m['rear']
    for pair in m['latch_pairs']:fixed=fixed-pair['tongue']
    fig,axs=plt.subplots(1,3,figsize=(13,7))
    states=[[(m['front'],front),(m['rear'],rear)],[(m['front'],front),(fixed,rear),(held[i],metal)],[(m['front'],front),(fixed.translate((0,0,-1)),rear),(held[i].translate((0,0,-1)),metal)]]
    for ax,items,title in zip(axs,states,['Closed: blind groove / zero axial play','Held: root-fixed .45mm free-end proxy','Held at -1mm; NOT safe to relax\nKeep four shims through -8.3mm']):
        panel(ax,[(intersection(s,slab),c) for s,c in items],[1,0,0],[0,0,1],[0,1,0],(67,71,-13,1.5));ax.set_title(title,fontsize=9);ax.set_xlabel('X mm');ax.set_ylabel('Z / FRONT up, REAR down')
    q=p['latch'];fig.suptitle(f'G HIDDEN TONGUE SECTION / L={q["beam_tip_z_mm"]-q["beam_root_z_mm"]:.1f}, t=.8 / physical material and 0.15mm tool handling UNVERIFIED');save(fig,'hidden_latch_section')
    # Tool enters alongside root, then sweeps in X at hook: show the actual lane.
    pair=m['latch_pairs'][i];fig,ax=plt.subplots(figsize=(8,7));slab=box([67,y+2.3,-14,71,y+2.8,1])
    panel(ax,[(intersection(s,slab),c) for s,c in [(m['front'],front),(fixed,rear),(pair['pick'],'#b9c4ca')]], [1,0,0],[0,0,1],[0,1,0],(67,71,-13,-2.5))
    ax.set_title('REAR-entry shim alongside root (Y +2.3..+2.8 slab)\nActual candidate tool, .15mm section; sourcing/stiffness UNVERIFIED');ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up, REAR down');save(fig,'rear_shim_lane')
    # Complete original source is sectioned, including native switch and glass.
    y=m['key_data']['KEY1']['center_yz_mm'][0];slab=box([-33,y-.03,-33,-19,y+.03,2])
    fig,axs=plt.subplots(1,3,figsize=(13,8))
    for ax,dz in zip(axs,[-15,-6,0]):
        items=[(m['front'],front),*[(s,front) for s in parked.values()],(parts['ASSEMBLY'].translate((0,0,dz)),'#959da3'),(m['rear'].translate((0,0,dz)),rear)]
        panel(ax,[(intersection(s,slab),c) for s,c in items],[1,0,0],[0,0,1],[0,1,0],(-33,-19,-32,2))
        ax.set_title(f'PCB + four-screw REAR unit: Z offset {dz}mm\nCaps parked outward .300 / LEFT DOWN',fontsize=9);ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up (+Z), REAR down')
    fig.suptitle('G ASSEMBLY / rotate device LEFT down; horizontally translate module +Z\nNominal glass/cap clearance >=.074mm: tolerance & gravity/friction reliability UNVERIFIED');save(fig,'assembly_sequence')
    fig,ax=plt.subplots(figsize=(11,8));panel(ax,[(m['front'],front),*all_source,*source[-7:],*extra],[-1,0,0],[0,1,0],[0,0,-1],(-75,35,-40,46))
    for text,(x,y),pos in [('MIC1 port UNVERIFIED',(22.8,1.4),(-60,0)),('MX0: -X mouth',(20,24.3),(-60,32)),('MX1: -X mouth',(20,-19.5),(-55,-36)),('cell / protection UNVERIFIED',(48,16),(-60,43))]:
        ax.annotate(text,(-x,y),pos,fontsize=9,arrowprops={'arrowstyle':'->'})
    ax.set_title('G REAR cutaway / lid HIDDEN only; PCB follows REAR at opening\nSpeaker supported on REAR pads; MX BAT/SPK identity, actual lead exits UNVERIFIED');ax.set_xlabel('mirrored X mm');ax.set_ylabel('Y mm / USB TOP');save(fig,'connector_and_bay_layout')
    # Same exported E, same view vectors, extents, axes sizes and colours.
    epath=out.parents[1]/'deliverables/t0-e';ef=import_step(epath/'front_shell.step');er=import_step(epath/'rear_shell.step');ec=[(import_step(epath/(k.lower()+'_cap.step')),front) for k in m['caps']]
    eextra=[(s.translate((0,0,-p['screen_recess_mm'])) if k in ['speaker','foam','damping'] else s,'#9ca6ab' if k in ['battery','protection'] else '#606d78') for k,s in accessories]
    escene=[(ef,front),(er,rear),*source,*ec,*eextra]
    fig,axs=plt.subplots(2,4,figsize=(20,10),gridspec_kw={'width_ratios':[1,1,1,1.1]})
    for j,(label,items) in enumerate([('E frozen',escene),('G candidate',scene)]):
        for col,vi in enumerate([0,1,3]):
            name,a,b,c,extent,title=views[vi];panel(axs[j,col],items,a,b,c,extent);axs[j,col].set_title(label+' / '+title,fontsize=9)
        axs[j,3].axis('off')
    axs[0,3].text(0,.95,'E (unchanged)\nBody 99.60 x 77.86\nSide caps: nominal width 101.50\nMax Z 12.400 / flush glass\n3 PCB clips + 4 shallow nests\n5 short shell teeth / no rear screws\nPCB first, caps from REAR\nPA12 creep, clip strain and\nsequential lid flex UNVERIFIED',va='top',fontsize=11,linespacing=1.7)
    axs[1,3].text(0,.95,'G (nominal only)\nSame body / rest width 101.50\nParked caps: max width 101.80\nMax Z 12.900 / .500 recess\n4 native M2.5 -> REAR seats\n4 hidden tongues / .8mm seats\nWhole module follows REAR\nLEFT-down parked-cap assembly\n.15 screw play > .074 cap gap\nXY robustness BLOCKED\nPA12 & tool UNVERIFIED',va='top',fontsize=11,linespacing=1.7)
    fig.suptitle('E / G SAME mm SCALE AND VIEW PER COLUMN / original CAD projections, no concept rendering\nBlack-border masking & display/touch boundary UNVERIFIED; neither candidate approved for printing',fontsize=13)
    save(fig,'E_vs_G_same_scale')
