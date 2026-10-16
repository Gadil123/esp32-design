"""First-gate failure drawings from original and exported BReps, no concept art."""
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.collections import PolyCollection
from build123d import import_step
from model import box_between as box
from p1_checks import intersection
from p1_preview import panel


def render(out,parts,m,base,q,rows):
    front=import_step(out/'deep_front_GATE_ONLY.step')
    rear=import_step(out/'rear_seats_GATE_ONLY.step')
    caps={k:import_step(out/(k.lower()+'_cap.step')) for k in m['caps']}
    def save(fig,name):
        fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=160);plt.close(fig)
    # EVERY original component is used in the local section.
    for row in rows:
        k=row['key'];yc=m['key_data'][k]['center_yz_mm'][0]
        slab=box([-33,yc-.04,-17,-20,yc+.04,2])
        fig,axs=plt.subplots(1,3,figsize=(12,8))
        for ax,dz in zip(axs,[-6,q['collision_witness_cap_z_offset_mm'],0]):
            cap=caps[k].translate((0,0,dz))
            hit=intersection(front,cap)
            items=[(front,'#58758a'),(parts['ASSEMBLY'],'#aab4b9'),(cap,'#e0a547'),(hit,'#db3636')]
            panel(ax,[(intersection(s,slab),c) for s,c in items],[1,0,0],[0,0,1],[0,1,0],(-33,-20,-17,1.5))
            # Overlay the ACTUAL intersection silhouette: coincident section
            # faces otherwise tie in the z-buffer and can hide the red witness.
            section_hit=intersection(hit,slab)
            if len(section_hit.faces()):
                vertices,triangles=section_hit.tessellate(.02,.1)
                xz=[(v.X,v.Z) for v in vertices]
                ax.add_collection(PolyCollection([[xz[j] for j in t] for t in triangles],facecolors='#db3636',edgecolors='none'))
            ax.set_title(f'{k}: cap Z offset {dz:+.1f}mm\n'+('Final position only' if dz==0 else 'REAR insertion / removal'),fontsize=10)
            ax.set_xlabel('X mm / LEFT');ax.set_ylabel('Z mm / FRONT up, REAR down')
        fig.suptitle(f'G-V1 FIRST GATE BLOCKED / actual CAD section Y={yc:.4f}\nBlue: deep FRONT; amber: cap; red: real overlap. At -3mm: {row["actual_cap_front_overlap_mm3"]:.6f} mm3')
        save(fig,k.lower()+'_rear_insertion_section')
    # Flush rim section. Entire window is through, not the old .25mm skin.
    slab=box([-30,-.04,-13,-22,.04,1.5]);fig,ax=plt.subplots(figsize=(8,7))
    panel(ax,[(intersection(s,slab),c) for s,c in [(front,'#58758a'),(rear,'#7c8c98'),(parts['ASSEMBLY'],'#aab4b9')]],
          [1,0,0],[0,0,1],[0,1,0],(-30,-22,-12,1.5))
    ax.axhline(.7,color='#777',ls='--',lw=.7);ax.set_title('G-V1 gate fixture / through glass window\nFRONT +.700 = glass +.700 / lateral clearance .600\nNo over-glass lip; PCB forward support NOT VERIFIED')
    ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up, REAR down');save(fig,'flush_gate_section')
    x,y=m['screw_rows'][0]['axis_xy_mm'];slab=box([x-4,y-.04,-12,x+4,y+.04,-3])
    fig,ax=plt.subplots(figsize=(8,7))
    panel(ax,[(intersection(s,slab),c) for s,c in [(rear,'#58758a'),(parts['ASSEMBLY'],'#aab4b9'),(m['screws'][0],'#d5a04b')]],
          [1,0,0],[0,0,1],[0,1,0],(x-4,x+4,-12,-3))
    ax.set_title('Preliminary G-V1 M2.5x4 envelope / NOT gate release\nHead .850 flush / seat 1.350 / engagement 2.650 nominal\nAlignment, effective thread and torque NOT VERIFIED')
    ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up, REAR down');save(fig,'preliminary_screw_section')
    ep=out.parents[1]/'deliverables/t0-e'
    ef=import_step(ep/'front_shell.step');er=import_step(ep/'rear_shell.step')
    ec=[import_step(ep/(k.lower()+'_cap.step')) for k in ['KEY1','KEY2','KEY3']]
    views=[([1,0,0],[0,1,0],[0,0,1],(-35,75,-40,46),'FRONT +Z / USB +Y TOP'),
           ([-1,0,0],[0,1,0],[0,0,-1],(-75,35,-40,46),'REAR -Z / USB +Y TOP')]
    fig,axs=plt.subplots(2,2,figsize=(13,11))
    for i,(name,f,r,cs) in enumerate([('E frozen',ef,er,ec),('G-V1 UNFINISHED gate fixture',front,rear,list(caps.values()))]):
        scene=[(f,'#58758a'),(r,'#8b9da8'),(parts['DISPLAY'],'#1d2730'),*[(s,'#d5a04b') for s in cs]]
        for ax,(u,v,w,ext,title) in zip(axs[i],views):
            panel(ax,scene,u,v,w,ext);ax.set_title(name+'\n'+title,fontsize=10);ax.set_xlabel('mm');ax.set_ylabel('mm')
    fig.suptitle('E / G-V1 same mm scale per column / native CAD projections\nG-V1 has NO new closure latches: first cap gate FAILED; not a completed enclosure. Neither approved for printing.')
    save(fig,'E_vs_G_V1_gate_same_scale')
