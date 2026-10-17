"""Task26 native CAD projections; same-scale old/new, no concept images."""
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from build123d import import_step,Compound,GeomType
from t0_g_v1_preview import panel
from t0_g_v1_integrated_drawings import section
from t0_g_v1_integrated_keys import press_pose
from reference import bounds
from model import box_between as box
from p1_checks import intersection


def save(fig,out,name):
    fig.tight_layout(rect=(0,0,1,.91),h_pad=3);fig.savefig(out/(name+'.png'),dpi=160);plt.close(fig)


def left_edges(ax,front,ox):
    # Native facing-wall topology distinguishes an open slot from a distant
    # opposite wall of the SAME shell seen through it in a solid projection.
    for f in front.faces():
        if f.geom_type!=GeomType.PLANE or abs(f.center().X-ox)>1e-5 or f.normal_at().X>-.99:continue
        for e in f.edges():
            n=1 if e.geom_type==GeomType.LINE else 24
            ps=[e.position_at(i/n) for i in range(n+1)]
            ax.plot([v.Z for v in ps],[v.Y for v in ps],color='#24333b',lw=.6)


def local_views(out,parts,m,base,q,report):
    row=m['integrated_keys'][1];front=import_step(out/'front_local_GATE_ONLY.step')
    old=import_step(out.parents[1]/'deliverables/t0-g-v1/front_shell.step')
    visible=[(parts[k],'#b7bec3') for k in ['PCB_BOARD','DISPLAY','KEY2']]
    fig,axs=plt.subplots(1,2,figsize=(12,10));extent=(-10.5,.8,-34,-15)
    for ax,s,title in zip(axs,[old,front],['e805d38 L profile / preserved','Task26 rounded rectangle / same scale']):
        panel(ax,[(section(s,box([-30,-35,-11,-25.5,-15,1])),'#58778a'),*visible],[0,0,1],[0,1,0],[-1,0,0],extent)
        left_edges(ax,s,base['outer_x_min_mm'])
        ax.set_title(title+'\nLEFT wall cutaway / FRONT right / REAR left',fontsize=10);ax.set_xlabel('Z mm');ax.set_ylabel('Y mm / USB TOP')
        ax.annotate('PRESS distal end\nnot fixed root',(row['z'],row['y']),(-1.5,row['y']+2),fontsize=8,arrowprops={'arrowstyle':'->'})
        ax.plot([-9.5,-9.5],[row['root_y']+q['fixed_root_length_mm'],row['y']],color='#c18e28')
        ax.text(-9.3,row['y']-7,'11mm effective',rotation=90,fontsize=8)
    fig.suptitle('BOOT ONLY / native LEFT wall cutaway X[-30,-25.5], mm coordinates\nNew rounded body13x3mm; free leaf12mm, effective bending11mm; NOT a separate small keycap')
    save(fig,out,'BOOT_old_new_same_scale_LEFT')
    sy=row['y'];slab=box([-31,sy-1.2,-10,-20,sy+1.2,1]);fixed=front-row['free']
    fig,axs=plt.subplots(1,4,figsize=(16,7))
    for ax,d,title in zip(axs,[0,.4,1.4,0],['REST','CANDIDATE .4','SHELL STOP1.4','RETURN to0 geometry']):
        pose,angle=press_pose(row,base,q,d)
        items=[(fixed,'#58778a'),(parts['ASSEMBLY'],'#b7bec3'),(pose,'#dfac49')]
        panel(ax,[(section(s,slab),c) for s,c in items],[1,0,0],[0,0,1],[0,-1,0],(-30,-23.7,-10,-3.5))
        ax.set_title(f'{title}\nPad reference {d:.1f}mm / end rotation{angle:.2f}deg',fontsize=9);ax.set_xlabel('X mm');ax.set_ylabel('Z / FRONT up, REAR down')
    fig.suptitle('BOOT XZ Y slab +/-1.2mm / root-fixed clearance proxies\nActual native travel, PA12 recovery, force and fatigue UNVERIFIED; whole-KEY intersection is not triggering proof')
    save(fig,out,'BOOT_states_and_return_section')
    # Include the relocated stop at its actual Y, rather than hide it in the
    # end-pad slice. Its top foot is a fixed wall connection, not a second leaf.
    sy=row['y']+sum(q['boot_rectangle']['stop_y_relative_mm'])/2;slab=box([-31,sy-.12,-10,-24,sy+.12,1])
    fig,axs=plt.subplots(1,2,figsize=(12,7))
    for ax,d in zip(axs,[0,1.4]):
        pose,_=press_pose(row,base,q,d)
        panel(ax,[(section(s,slab),c) for s,c in [(fixed,'#58778a'),(pose,'#dfac49'),(parts['ASSEMBLY'],'#b7bec3')]],
              [1,0,0],[0,0,1],[0,-1,0],(-30,-24,-10,.8))
        ax.set_title(f'BOOT local stop / pad reference {d:.1f}mm\nY={sy:.3f}mm, FRONT up / REAR down',fontsize=9);ax.set_xlabel('X mm');ax.set_ylabel('Z mm')
    fig.suptitle('Only BOOT stop relocated: top foot .8mm, post .9mm, width1.2mm\nClear of bump in Y; no .05mm moving slit. Overpressure protection still needs actual switch data')
    save(fig,out,'BOOT_relocated_stop_section')
    sy=row['y'];slab=box([-31,sy-1.2,-32,-20,sy+1.2,1]);fig,axs=plt.subplots(1,3,figsize=(12,8))
    for ax,d in zip(axs,[-14,-6,0]):
        panel(ax,[(section(s,slab),c) for s,c in [(front,'#58778a'),(parts['ASSEMBLY'].translate((0,0,d)),'#b7bec3')]],
              [1,0,0],[0,0,1],[0,-1,0],(-31,-20,-30,1))
        ax.set_title(f'Complete original module Z{d:+}mm',fontsize=9);ax.set_xlabel('X mm');ax.set_ylabel('Z / FRONT up, REAR down')
    fig.suptitle('REAR +Z insertion / -Z removal / both integral keys at REST\nAll723-source continuous envelope checked; the three drawings are explanatory snapshots only')
    save(fig,out,'BOOT_complete_module_insertion')


def full_views(out,parts,m,mounts,base,q,report):
    front=import_step(out/'front_shell.step');rear=import_step(out.parents[1]/'deliverables/t0-g-v1/rear_shell.step')
    scene=[(front,'#526d7b'),(rear,'#9aa6ad')]+[(parts[k],'#14222b' if k=='DISPLAY' else '#b4bec2') for k in ['DISPLAY','PCB_BOARD','J2_USB_SIDE','KEY1','KEY2','KEY3','TF','MX0','MX1','MIC1']]+[(s,'#b7bec3') for s in [*mounts,*m['screws']]]
    u=np.array([1.,0,-1]);u/=np.linalg.norm(u);w=np.array([1.,.8,1]);w/=np.linalg.norm(w);v=np.cross(w,u)
    for name,a,b,c,extent,title,size in [('LEFT',[0,0,1],[0,1,0],[-1,0,0],(-12.4,1.1,-39,45),'LEFT -X / FRONT right / USB TOP',(4,9)),('ISO',u,v,w,(-35,70,-60,55),'ISO FRONT / USB +Y',(11,8))]:
        fig,ax=plt.subplots(figsize=size);panel(ax,scene,a,b,c,extent)
        if name=='LEFT':left_edges(ax,front,base['outer_x_min_mm'])
        bb=report['complete_STEP_roundtrip'];ax.set_title(f'Task26 BOOT rectangle / BAT_PWR L unchanged\n{title}\nmax {bb["maximum_thickness_mm"]:.3f} / rigid bound {bb["maximum_with_retained_rear_play_mm"]:.3f}mm; physical fit pending',fontsize=9)
        ax.set_xlabel('mm');ax.set_ylabel('mm');save(fig,out,name)
    row=m['integrated_keys'][1];ox=base['outer_x_min_mm'];y=row['y']-4;zl=row['leaf_z_mm'][0];g=q['slot_mm']
    s=intersection(front,box([ox+.2,y-.02,-10.5,ox+.4,y+.02,zl-g+.1]));bb=bounds(s)
    report['BOOT_exported_local_features']=dict(lower_U_to_front_rear_edge_ligament_mm=bb[5]-bb[2],
        stop_to_bump_rest_gap_mm=row['stop'].distance_to(row['bump']),stop_foot_thickness_mm=q['boot_rectangle']['stop_foot_z_mm'][1]-q['boot_rectangle']['stop_foot_z_mm'][0],
        note='Named actual BRep sections, not a global minimum wall certificate.')
