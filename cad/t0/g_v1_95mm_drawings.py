"""Same-scale exterior and real BRep bay/latch sections, no concept renders."""
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from build123d import Compound,FilletPolyline
from model import box_between as box
from reference import bounds
from p1_checks import intersection
from t0_g_v1_preview import panel
from t0_g_v1_integrated_drawings import section
from g_v1_95mm_wiring import build as wiring

BLUE='#587f96';REAR='#80a4b5';BOARD='#b6bec6';CELL='#d2a64e';SPK='#ba7769';FOAM='#765789'
def save(fig,out,name):
    fig.tight_layout(rect=(0,0,1,.90),h_pad=3);fig.savefig(out/(name+'.png'),dpi=160);plt.close(fig)
def parts_scene(parts,m):
    return [(m['front'],BLUE),(m['rear'],REAR),(Compound(parts['ASSEMBLY'].solids()),BOARD),(m['battery'],CELL),(m['speaker'],SPK),(m['foam'],FOAM),(m['damping'],FOAM)]
def render(out,parts,old,m,b0,base,c0,c,cfg,r):
    fig,axs=plt.subplots(1,2,figsize=(13,9));ext=(-32,73,-38,44)
    for ax,mm,width in zip(axs,[old,m],[99.6,95.6]):
        panel(ax,[(mm['front'],BLUE),(parts['DISPLAY'],BOARD),(parts['J2_USB_SIDE'],BOARD),(mm['speaker'],SPK)],[1,0,0],[0,1,0],[0,0,1],ext)
        ax.set_title(f'{width:.2f} x 77.86 x 12.369521mm\nFRONT +Z / USB +Y TOP',fontsize=10);ax.set_xlabel('X mm');ax.set_ylabel('Y mm')
    fig.suptitle('FROZEN ee8ec9d vs95.60 CANDIDATE / SAME SCALE\nOriginal display/PCB/keys fixed. Speaker+grille X-1.5; right shell+latch X-4. Nominal CAD only.')
    save(fig,out,'old_new_same_scale_FRONT')
    fig,axs=plt.subplots(1,2,figsize=(13,9));slab=box([-30,-36,-6.52,71,42,-6.28])
    for ax,mm,width in zip(axs,[old,m],[99.6,95.6]):
        items=[(section(s,slab),co) for s,co in parts_scene(parts,mm) if s is not mm['rear']]
        panel(ax,items,[1,0,0],[0,1,0],[0,0,1],ext)
        ax.set_title(f'{width:.2f}mm / FRONT +Z cutaway\nZ=-6.40 +/-0.12; REAR removed; USB +Y',fontsize=10);ax.set_xlabel('X mm');ax.set_ylabel('Y mm')
        ax.annotate('MIC1 candidate space',(27.3,1.395),(33,1),fontsize=8,arrowprops={'arrowstyle':'->'})
    fig.suptitle('RIGHT BAY / actual sectioned case+723-board BReps, measured accessory envelopes\nBattery complete29.49x42.26x7.61; speaker30x20x6.5. Dashed/omitted wiring is not real harness certification.')
    save(fig,out,'old_new_bay_same_scale_FRONT_cutaway')
    fig,axs=plt.subplots(1,2,figsize=(13,7));slab=box([25,-34,-6.52,69,-10,-6.28])
    oldfence=intersection(old['front'],box([29.4,-34,-8.2,62.6,-10.8,-.5001]));shifted=intersection(old['front'],box([65.7,-30,-9.5,67.45,-26,-1])).translate((-4,0,0))
    items=[(oldfence,SPK),(shifted,'#d54949')]
    panel(axs[0],[(section(s,slab),co) for s,co in items],[1,0,0],[0,1,0],[0,0,1],(25,69,-34,-10))
    axs[0].set_title('PR5 direct receiver X-4 only\n17.1252mm3 overlap / BLOCKED',fontsize=10)
    panel(axs[1],[(section(m['front'],slab),BLUE),(section(m['speaker'],slab),SPK)],[1,0,0],[0,1,0],[0,0,1],(25,69,-34,-10))
    axs[1].set_title('Joint layout: speaker+fence X-1.5, receiver X-4\n0.83mm nominal gap / frame and tooth retained',fontsize=10)
    for ax in axs:ax.set_xlabel('X mm');ax.set_ylabel('Y mm / FRONT +Z observer')
    fig.suptitle('Resolve the original collision by MOVING the complete speaker/frame/grille/support system\nNo fence thinning, removed support, smaller tooth or reduced clearance. Real section Z=-6.40 +/-0.12.')
    save(fig,out,'receiver_speaker_interference_resolved')
    fig,axs=plt.subplots(1,3,figsize=(14,7));y=c['clip_sites'][0]['y_mm'];slab=box([-30,y-.12,-12,71,y+.12,1])
    for ax,mm,cc,title in zip(axs[:2],[old,m],[c0,c],['Frozen lower latch','95.60 lower latch / identical translated geometry']):
        a=cc['clip_x_mm'][0]
        panel(ax,[(section(mm['front'],slab),BLUE),(section(mm['rear'],slab),REAR)],[1,0,0],[0,0,1],[0,-1,0],(a-2.6,a+3,-11.6,-.4))
        ax.set_title(title+'\nXZ section Y=-28 +/-0.12',fontsize=9);ax.set_xlabel('X mm');ax.set_ylabel('Z / FRONT up, REAR down')
    row=m['screw_rows'][2];sx,sy=row['axis_xy_mm'];slab2=box([sx-4,sy-.08,-12,sx+4,sy+.08,-5])
    panel(axs[2],[(section(m['rear'],slab2),REAR),(section(Compound(parts['ASSEMBLY'].solids()),slab2),BOARD),(section(m['screws'][2],slab2),'#a0a5ac')],[1,0,0],[0,0,1],[0,-1,0],(sx-4,sx+4,-11.7,-5))
    axs[2].set_title('Original M2.5 metal mount / screw / PA12 seat\n1.000mm seat; same XY, bearing and thread envelope',fontsize=9);axs[2].set_xlabel('X mm');axs[2].set_ylabel('Z / FRONT up')
    fig.suptitle('LOAD PATH / latch1.1 x1.2, L10, slot1, same root/tooth/play; four native screw seats retained\nGeometry agreement does NOT certify PA12 force/fatigue, global stiffness, torque or creep.')
    save(fig,out,'latch_and_native_screw_sections')
    fig,axs=plt.subplots(2,1,figsize=(12,9),gridspec_kw={'height_ratios':[1,1]});slab=box([42.88,-36,-12,43.12,42,1])
    panel(axs[0],[(section(s,slab),co) for s,co in parts_scene(parts,m)],[0,1,0],[0,0,1],[1,0,0],(-36,42,-12,1))
    axs[0].set_title('95.60 SIDE +X / YZ section X=43 +/-0.12\nFRONT +Z up; speaker damping/support contact restored; no battery clamp',fontsize=10);axs[0].set_xlabel('Y mm');axs[0].set_ylabel('Z mm')
    axs[1].axis('off');axs[1].text(.03,.85,'BATTERY COMPLETE measured7.61 + candidate adhesive0.20 on rear1.20\nFront headroom1.84; candidate swelling1.00 + Z tolerance0.30 leaves0.54mm\nXY size+position conservative budget0.50 per side; tray wall1.00, clearance0.75\nSpeaker front foam0.50 + damping0.30 retained; four3x3 pads raised0.30\nBoth pads/foam are candidates, not verified compression or adhesive specifications.\nNominal complete max12.369521mm; retained-lid bound in checks.json.\nNo extra battery protection PCB stack. Terminal keepout is free space.',fontsize=11,va='top',linespacing=1.6)
    fig.suptitle('REAL Z SECTION / blue case, ochre COMPLETE battery envelope, red speaker body, purple cushioning\nNo added thickness, glass pressure or battery compression used to reach target.')
    save(fig,out,'bay_Z_stack_and_support_section')
    mic_wiring_view(out,parts,m,base,r)
    fig,axs=plt.subplots(1,2,figsize=(13,8))
    exterior=[(m['front'],BLUE),(m['rear'],REAR),(parts['DISPLAY'],BOARD),(parts['J2_USB_SIDE'],BOARD),(Compound(m['screws']),'#a0a5ac')]
    panel(axs[0],exterior,[-1,0,0],[0,1,0],[0,0,-1],(-69,33,-38,44))
    axs[0].set_title('95.60 REAR -Z / USB +Y TOP\nFour original-position screws and two rear U-slot clips',fontsize=10)
    axs[0].set_xlabel('-X mm (REAR mirrored)');axs[0].set_ylabel('Y mm')
    panel(axs[1],exterior,[.70710678,.70710678,0],[-.40824829,.40824829,.81649658],[.57735027,-.57735027,.57735027],(-49,80,-55,34))
    axs[1].set_title('95.60 FRONT +Z isometric / true case solids\nView from +X,-Y,+Z; USB remains physical +Y',fontsize=10)
    axs[1].set_xlabel('Projected mm');axs[1].set_ylabel('Projected mm')
    fig.suptitle('EXTERIOR CAD PREVIEW / original key structure, recessed removable rear, no new parts\nNominal fit and physical/PA12 limitations remain separate.')
    save(fig,out,'REAR_and_FRONT_ISO')


def mic_wiring_view(out,parts,m,base,r):
    fig,axs=plt.subplots(1,2,figsize=(14,8));slab=box([19,1.275,-12,32,1.515,1])
    panel(axs[0],[(section(s,slab),co) for s,co in parts_scene(parts,m)],[1,0,0],[0,0,1],[0,-1,0],(19,32,-12,1))
    pts=r['additional_geometry']['microphone_air_probe_points_mm']
    for a,b in zip(pts,pts[1:]):axs[0].plot([a[0],b[0]],[a[2],b[2]],'--',color='#20a087',lw=2)
    axs[0].set_title('MIC XZ / FRONT +Z up\nCandidateD1.5 atX27.30/Y1.395 NOT drilled\nAir path to package exterior clear; actual inlet UNVERIFIED',fontsize=9);axs[0].set_xlabel('X mm');axs[0].set_ylabel('Z mm')
    plugs,wires,data=wiring(parts,base,m)
    # Actual connector, board substrate and accessory geometry, selected to make
    # candidate routes visible. Full723 solids are used in checks, not hidden here.
    panel(axs[1],[(parts['PCB_BOARD'],BOARD),(parts['MX0'],BOARD),(parts['MX1'],BOARD),(m['battery'],CELL),(m['speaker'],SPK)],[1,0,0],[0,1,0],[0,0,1],(5,66,-35,41))
    for name,row in data.items():
        path=row['wire_centerline_polyline_before_fillets_mm'][0]
        curve=FilletPolyline(*path,radius=base['wire_bend_radius_mm'])
        for j,e in enumerate(curve.edges()):
            pts=[e.position_at(k/24) for k in range(25)]
            axs[1].plot([a.X for a in pts],[a.Y for a in pts],color=('#1f77b4' if name=='MX0' else '#ff7f0e'),lw=2,label=(f'{name} {row["filleted_centerline_length_mm"]:.2f}mm candidate' if j==0 else None))
    axs[1].legend(fontsize=8,loc='lower left');axs[1].set_title('FRONT +Z wiring placement / USB +Y TOP\nLowerMX1=SPK user confirmed; upperBAT allocation pending\nUser40mm fit accepted; staged endpoint/service slack pending',fontsize=9);axs[1].set_xlabel('X mm');axs[1].set_ylabel('Y mm')
    fig.suptitle('MIC SPACE AND SERVICE ROUTING / exact checked paths, not supplier harness CAD\nOld79.46mm proxy is not used as evidence against the user-tested40mm lead.')
    save(fig,out,'MIC_and_conditional_wiring')
