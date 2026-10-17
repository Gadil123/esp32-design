"""Actual E BRep projections/sections, with explicit FRONT/REAR and local-scale labels."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from p1_preview import panel
from p1_checks import intersection
from model import box_between as box
from reference import bounds
from build123d import import_step


def render(out,parts,mounts,m,released,base,p,report):
    # Draw the verified exported geometry. Fresh STEP topology avoids stale
    # in-memory triangulations on fused/copied coplanar skin faces.
    m={**m,'front':import_step(out/'front_shell.step'),'rear':import_step(out/'rear_shell.step'),
       'caps':{k:import_step(out/(k.lower()+'_cap.step')) for k in m['caps']}}
    blue,amber,green='#526a80','#dba64d','#278774'
    source=[(parts[k],green if k=='PCB_BOARD' else '#38535b' if k=='DISPLAY' else '#b6a77c') for k in ['PCB_BOARD','DISPLAY','KEY1','KEY2','KEY3','TF','J2_USB_SIDE','MIC1','MX0','MX1']]
    source += [(s,'#b6a77c') for s in mounts]
    extra=[(m[k],'#bd7951' if k in ['battery','protection'] else '#64777e') for k in ['battery','speaker','foam','damping','adhesive','protection']]
    extra += [(s,amber) for s in m['caps'].values()]
    from t0_wiring import build_wiring
    plugs,wires,_=build_wiring(parts,base,m)
    extra += [(s,'#eee2bf') for s in plugs.values()]+[(s,'#c64f49') for ss in wires.values() for s in ss]
    scene=[(m['front'],blue),(m['rear'],amber),*source,*extra]
    views=[('front',[1,0,0],[0,1,0],[0,0,1],(-35,75,-40,46),'FRONT +Z / USB +Y TOP'),
           ('rear',[-1,0,0],[0,1,0],[0,0,-1],(-75,35,-40,46),'REAR -Z / USB +Y TOP'),
           ('side',[0,0,1],[0,1,0],[-1,0,0],(-13,2,-40,46),'LEFT -X / FRONT +Z right, REAR left / USB TOP')]
    for name,u,v,w,ext,title in views:
        fig,ax=plt.subplots(figsize=(11,8) if name!='side' else (4,9))
        panel(ax,scene,u,v,w,ext);ax.set_title('T0 E '+title+'\n99.6 x 77.86 body / full max 12.400mm / REVIEW ONLY');ax.set_xlabel('mm');ax.set_ylabel('mm')
        fig.tight_layout();fig.savefig(out/f'{name}.png',dpi=150);plt.close(fig)
    u=np.array([1,0,-1.]);u/=np.linalg.norm(u);w=np.array([1,.8,1.]);w/=np.linalg.norm(w);v=np.cross(w,u)
    fig,ax=plt.subplots(figsize=(11,8));panel(ax,scene,u,v,w,(-35,70,-55,50));ax.set_title('T0 E ISO FRONT / USB +Y | physical MJF function UNVERIFIED');fig.tight_layout();fig.savefig(out/'iso_front.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(15,7))
    items=[(m['front'],blue),*source,*extra]
    panel(axes[0],items,[-1,0,0],[0,1,0],[0,0,-1],(-75,35,-40,46));axes[0].set_title('REAR / cover removed: retained PCB + provisional bay\nSelected exact source parts; all 723 solids checked separately')
    panel(axes[1],[(m['front'],blue),(m['rear'],amber)], [1,0,0],[0,1,0],[0,0,1],(-35,75,-40,46));axes[1].set_title('FRONT / five short teeth placed by available space\nNot a claim of Passport tooth count or real sequential flexure')
    ox=base['outer_x_min_mm'];ex=ox+base['width_mm'];oy,ey=base['outer_y_mm']
    for i,q in enumerate(p['short_tooth_sites']):
        edge=q['edge'];at=q['coordinate_mm'];x,y={'bottom':(at,oy),'top':(at,ey),'left':(ox,at),'right':(ex,at)}[edge]
        axes[1].annotate(str(i+1),(x,y),(x+(-13 if edge=='right' else 5),y+4),arrowprops={'arrowstyle':'->'},fontsize=10)
    for j,data in enumerate(m['clip_data']):
        x,y=data['mount_axis_mm'];x=np.sign(x)*24.6
        axes[0].annotate('PCB '+str(p['pcb_clip_indices'][j]),(-x,y),(-x+7,y-8),arrowprops={'arrowstyle':'->'},fontsize=8)
    for ax in axes:ax.set_xlabel('mm');ax.set_ylabel('Y mm')
    fig.tight_layout();fig.savefig(out/'layout_and_opening_order.png',dpi=160);plt.close(fig)
    # Three contact cuts: same coordinates as measured actual PCB bearing faces.
    fig,axs=plt.subplots(1,3,figsize=(15,6))
    for j,ax in enumerate(axs):
        x,y=m['clip_data'][j]['mount_axis_mm'];xx=np.sign(x)*25.2;clip=box([xx-9,y-.04,-12,xx+9,y+.04,1])
        scene=[(parts['DISPLAY'],'#8aa8a0'),(parts['PCB_BOARD'],green),*[(s,'#b6a77c') for s in mounts],(m['front'],blue),(m['rear'],amber)]
        panel(ax,[(intersection(s,clip),c) for s,c in scene],[1,0,0],[0,0,1],[0,1,0],(xx-9,xx+9,-12,1))
        ax.set_title(f'A clip {p["pcb_clip_indices"][j]} / Y={y:.3f}\nE nominal PCB gap .000 / LCD gap .200');ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up, REAR down')
    fig.suptitle('E THREE NONCOLLINEAR PCB CONTACTS / LOCAL ENLARGEMENTS / no glass clamping');fig.tight_layout();fig.savefig(out/'PCB_contact_sections.png',dpi=160);plt.close(fig)
    # One true mount-axis section contains both rear nests; axial budget shown.
    y=m['nest_rows'][0]['axis_xy_mm'][1];clip=box([-32,y-.04,-12,72,y+.04,2])
    scene=[(parts['ASSEMBLY'],'#7a8e81'),(m['front'],blue),(m['rear'],amber),*extra]
    fig,ax=plt.subplots(figsize=(15,4));panel(ax,[(intersection(s,clip),c) for s,c in scene],[1,0,0],[0,0,1],[0,1,0],(-32,72,-13,2))
    for z in [.7,-11.7]:ax.axhline(z,ls='--',lw=.7,color='#bc5252')
    ax.set_title('E THICKNESS / actual original source section / FRONT +Z up, REAR down\nFULL ALL-SOLID MAX 12.400mm / .7 to -11.7; metal back -9.5 / nest seat -9.6 / rear inside -10.5')
    ax.set_xlabel('X mm');ax.set_ylabel('Z mm');fig.tight_layout();fig.savefig(out/'thickness_and_nests.png',dpi=170);plt.close(fig)
    # Clip bending and actual insertion poses, with REAR cover absent in all.
    fig,axs=plt.subplots(1,3,figsize=(15,7));j=0;x,y=m['clip_data'][j]['mount_axis_mm'];clip=box([-30,y-.05,-15,-22,y+.05,1])
    fixed=m['front']
    for s in m['pcb_clips']:fixed=fixed-s
    for ax,dz,held,title in [(axs[0],-6,True,'Hold root-fixed clip outward / LCD passes'),(axs[1],0,True,'Complete module at final Z; clip still held'),(axs[2],0,False,'Clip returned over PCB; cap installed afterwards')]:
        scene=[(parts['DISPLAY'].translate((0,0,dz)),'#8aa8a0'),(parts['PCB_BOARD'].translate((0,0,dz)),green),(fixed,blue),(released[0] if held else m['pcb_clips'][0],amber)]
        panel(ax,[(intersection(s,clip),c) for s,c in scene],[1,0,0],[0,0,1],[0,1,0],(-30,-22,-15,1));ax.set_title(title,fontsize=9);ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up')
    fig.suptitle('E LOCAL PCB INSERTION / REAR cover absent / held deformation is geometry proxy, actual MJF elasticity unverified');fig.tight_layout();fig.savefig(out/'PCB_insertion_sequence.png',dpi=160);plt.close(fig)
    # D-style short tooth in the actual complete shell at right lower site.
    site=m['short_pairs'][1];y=site['site']['coordinate_mm'];clip=box([65,y-.04,-15,74,y+.04,1])
    fig,axs=plt.subplots(1,2,figsize=(11,7))
    panel(axs[0],[(intersection(m['front'],clip),blue),(intersection(m['rear'],clip),amber)], [1,0,0],[0,0,1],[0,1,0],(65,74,-15,1));axs[0].set_title('Closed / short tooth in full shell\n0.4 overlap / 1.5 lower receiver ligament')
    rel=tuple(a*.5 for a in site['inward']);free=site['tongue'].translate(rel).translate((0,0,-2.8))
    scene=[(m['front'],blue),(site['fixed_rear'].translate((0,0,-2.8)),amber),(free,amber),(site['pick'],'#ae6275')]
    panel(axs[1],[(intersection(s,clip),c) for s,c in scene],[1,0,0],[0,0,1],[0,1,0],(65,74,-15,1));axs[1].set_title('ONE local release proxy / .35 pick\n.5 inward, >=2.8 local gap before relaxation')
    for ax in axs:ax.set_xlabel('X mm / outside right');ax.set_ylabel('Z mm / FRONT up, REAR down')
    fig.suptitle('SHORT TOOTH LOCAL ENLARGEMENT / not a physical whole-cover bending proof');fig.tight_layout();fig.savefig(out/'short_tooth_sections.png',dpi=160);plt.close(fig)
