"""Actual local BRep projections and sections. Deformed poses labeled proxies."""
import math
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from build123d import import_step,Axis,Compound
from t0_g_v1_preview import panel
from p1_checks import intersection
from model import box_between as box
from t0_g_v1_integrated_keys import press_pose
from reference import bounds


def section(shape,slab):
    # Render physical solids, not the STEP's 298 non-solid reference faces or
    # isolated tangent faces produced by a Boolean section.
    return Compound(intersection(shape,slab).solids())


def render(out,parts,m,base,q,report):
    from generate_t0_g_v1_integrated import shortened
    full=(out/'front_shell.step').exists()
    front=import_step(out/('front_shell.step' if full else 'front_integrated_GATE_ONLY.step'));ox=base['outer_x_min_mm']
    def save(fig,name):
        fig.tight_layout(rect=(0,0,1,.92),h_pad=3);fig.savefig(out/(name+'.png'),dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(5,11))
    panel(ax,[(front,'#58778a'),(Compound(parts['ASSEMBLY'].solids()),'#b7bec3')],[0,0,1],[0,1,0],[-1,0,0],(-12.3,1.3,-35,15))
    ax.set_title('LEFT -X / USB +Y TOP\nFRONT +Z right / REAR -Z left\nFRONT part only / rear hidden',fontsize=10)
    for row in m['integrated_keys']:
        ax.annotate(row['key']+' integral leaf',(row['z'],row['y']),(0,row['y']+3),fontsize=9,arrowprops={'arrowstyle':'->'})
    ax.set_xlabel('Z mm');ax.set_ylabel('Y mm');save(fig,'integral_key_layout_LEFT')
    for row,result in zip(m['integrated_keys'],report['buttons']):
        key=row['key'];er,cut=shortened(row,q);fixed=front-row['free']
        # Actual XZ sections pass through the pressed bump. The source is ALL
        # 723 solids, not a proxy chosen to hide surrounding geometry.
        sy=row['y']
        slab=box([-31,sy-1.2,-12,-20,sy+1.2,1])
        fig,axs=plt.subplots(1,4,figsize=(15,7))
        for ax,delta,error in zip(axs,[0,q['candidate_press_mm'],q['candidate_stop_mm'],q['candidate_stop_mm']],[False,False,False,True]):
            pose,angle=press_pose(er if error else row,base,q,delta)
            source=parts['ASSEMBLY'].translate((q['pcb_xy_radial_play_mm'] if error else 0,0,0))
            items=[(fixed,'#58778a'),(source,'#b7bec3'),(pose,'#dfac49')]
            panel(ax,[(section(s,slab),c) for s,c in items],[1,0,0],[0,0,1],[0,1,0],(-30,-23.7,-10.5,.8))
            title=f'Pad reference +{delta:.1f}mm\nEnd rotation {angle:+.2f} deg'
            if error:title+='\nBump -.300 / PCB +.150 X'
            ax.set_title(title,fontsize=9);ax.set_xlabel('X mm / LEFT');ax.set_ylabel('Z / FRONT up, REAR down')
        fig.suptitle(key+' / REST, .4 CANDIDATE, SHELL STOP, TOLERANCE WITNESS / Y slab +/-1.2mm\nRoot-fixed end-force clearance proxies; actual travel, force, PA12 elasticity UNVERIFIED')
        save(fig,key.lower()+'_states')
        # Orthographic projection of the ENTIRE contact bump and actual native
        # switch, to make the global closest-point gap visible without choosing
        # a favorable slice. No other source solids are used as substitutes.
        theta=-row['direction']*math.degrees(math.atan(1.5*q['candidate_stop_mm']/(q['root_to_pad_mm']-q['fixed_root_length_mm'])))
        bump=er['bump'].rotate(Axis((ox+q['leaf_thickness_mm']/2,row['y'],0),(0,0,1)),theta).translate((q['candidate_stop_mm'],0,0))
        native=parts[key].translate((q['pcb_xy_radial_play_mm'],0,0))
        fig,ax=plt.subplots(figsize=(9,6))
        panel(ax,[(bump,'#dfac49'),(native,'#aeb9c0')],[1,0,0],[0,0,1],[0,1,0],(-25.5,-23.8,row['z']-1.2,row['z']+1.2))
        gap=result['tolerance_witness']['whole_native_switch_gap_mm']
        ax.set_title(f'{key}: all-bump / whole-native-switch XZ projection\nAt actual modeled shell stop: closest 3D gap {gap:.6f}mm / contact only\nPA12 protrusion reach -.300mm; PCB +.150mm. Actual moving head and triggering UNVERIFIED.',fontsize=10)
        ax.set_xlabel('X mm / LEFT');ax.set_ylabel('Z mm / FRONT up, REAR down');save(fig,key.lower()+'_tolerance_reach')
    row=m['integrated_keys'][0];sy=row['y'];slab=box([-31,sy-1.2,-30,-20,sy+1.2,1])
    fig,axs=plt.subplots(1,3,figsize=(12,8))
    for ax,dz in zip(axs,[-14,-6,0]):
        panel(ax,[(section(s,slab),c) for s,c in [(front,'#58778a'),(parts['ASSEMBLY'].translate((0,0,dz)),'#b7bec3')]],
              [1,0,0],[0,0,1],[0,1,0],(-31,-20,-25,1))
        ax.set_title(f'Whole official module Z {dz:+}mm\nIntegral leaf & bump at REST',fontsize=10);ax.set_xlabel('X mm');ax.set_ylabel('Z / FRONT up, REAR down')
    fig.suptitle('REAR +Z insertion / -Z removal: no leaf holding\nFull continuous723-solid envelope check, not just these3 pictured positions');save(fig,'complete_module_insertion')
    fig,axs=plt.subplots(1,2,figsize=(12,8));row=m['integrated_keys'][0]
    z=(q['leaf_z_mm'][0]+q['leaf_z_mm'][1])/2
    slab=box([ox-.1,row['root_y']-2,z-.03,ox+3,row['root_y']+2,z+.03])
    panel(axs[0],[(section(front,slab),'#58778a')],[1,0,0],[0,1,0],[0,0,1],(ox-.1,ox+2.5,row['root_y']-1.5,row['root_y']+1.5))
    axs[0].set_title('Actual XY root section / R.500 transition\nleaf1.200 / wall1.800; FRONT +Z observer',fontsize=10);axs[0].set_xlabel('X mm');axs[0].set_ylabel('Y mm')
    slab=box([ox+.58,-7,-12,ox+.62,9,1])
    panel(axs[1],[(section(front,slab),'#58778a')],[0,0,1],[0,1,0],[-1,0,0],(-12,1,-7,9))
    axs[1].set_title('Actual YZ wall section / LEFT view\nTF / U slot / FRONT rim remain distinct',fontsize=10);axs[1].set_xlabel('Z mm / FRONT right');axs[1].set_ylabel('Y mm')
    fig.suptitle('PRINT FEATURES / nominal sections only, not supplier acceptance or fatigue proof');save(fig,'root_and_wall_sections')
