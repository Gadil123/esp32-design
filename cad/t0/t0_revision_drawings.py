"""Orthographic and section drawings from the modeled B-reps, equal mm scales."""
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Patch
from p1_preview import panel
from p1_checks import intersection
from model import box_between as box
from reference import bounds

BLUE='#526a80';REAR='#8293a4';CAP='#edac4a';PCB='#26856b'


def render_revision(out,parts,m,p):
    ox,ex=m['dimensions']['outer_x_mm'];oy,ey=m['dimensions']['outer_y_mm'];bottom=m['dimensions']['rear_bottom_z_mm'];top=m['dimensions']['glass_and_front_z_mm']
    shells=[(m['front'],BLUE),(m['rear'],REAR)];caps=[(s,CAP) for s in m['caps'].values()]
    refs=[(parts[k],PCB if k=='PCB_BOARD' else '#bba875') for k in ['PCB_BOARD','DISPLAY','KEY1','KEY2','KEY3','TF','J2_USB_SIDE']]
    full=shells+caps+refs
    w=ex-ox;h=ey-oy;t=top-bottom
    fig=plt.figure(figsize=(17,7));gs=fig.add_gridspec(1,3,width_ratios=[w+8,t+8,w+8])
    axes=[fig.add_subplot(gs[0,i]) for i in range(3)]
    panel(axes[0],full,[1,0,0],[0,1,0],[0,0,1],(ox-4,ex+4,oy-4,ey+4))
    panel(axes[1],full,[0,0,1],[0,1,0],[-1,0,0],(bottom-4,top+4,oy-4,ey+4))
    panel(axes[2],full,[-1,0,0],[0,1,0],[0,0,-1],(-ex-4,-ox+4,oy-4,ey+4))
    for ax,title in zip(axes,['FRONT +Z','LEFT -X\nFRONT right','REAR -Z']):
        ax.set_title(title+'\nUSB +Y TOP');ax.set_ylabel('Y mm');ax.axhline(ey,color='#777777',ls=':',lw=.5)
    axes[0].set_xlabel(f'X mm | shell {w:.2f} x {h:.2f} mm')
    axes[1].set_xlabel(f'Z mm\n{t:.2f} mm')
    axes[2].set_xlabel('-X mm | REAR mirrors FRONT')
    fig.suptitle(f"T0 {p.get('variant','B')} | CAD orthographic, equal mm scale | 2 exposed heads + recessed RESET | REVIEW ONLY")
    fig.tight_layout();fig.savefig(out/'orthographic.png',dpi=180);plt.close(fig)
    # External detail and separate moving-cap sections: all geometry is cut from CAD.
    fig,axes=plt.subplots(1,3,figsize=(15,7))
    panel(axes[0],full,[0,0,1],[0,1,0],[-1,0,0],(-10,-3,-24,1))
    for k in ['KEY1','KEY3','KEY2']:
        y,z=m['key_data'][k]['center_yz_mm'];name=m['key_data'][k]['function']
        axes[0].annotate(k+' / '+name,(-5.5,y),(-3.2,y),fontsize=7,arrowprops={'arrowstyle':'->'})
    axes[0].set_title(('LEFT -X / external\nTwo heads 4.6 x 2.2; RESET hole D1.30' if p.get('variant')=='A' else 'B preserved: RESET rectangular guide\nbreaks through nominal D1.30 hole'))
    for ax,k in zip(axes[1:],['KEY1','KEY3']):
        y,z=m['key_data'][k]['center_yz_mm'];crop=box([ox-2.5,y-.035,-9.5,-21,y+.035,-3.5])
        items=[(intersection(s,crop),c) for s,c in shells+[(parts[k],PCB),(m['caps'][k],CAP)]]
        panel(ax,items,[1,0,0],[0,0,1],[0,1,0],(ox-2.5,-21,-9.5,-3.5))
        ax.set_title(k+(' exposed head' if k=='KEY1' else ' recessed RESET / needle access')+'\nSECTION Y='+f'{y:.3f}'+' / FRONT +Z up')
        ax.set_xlabel('X mm');ax.set_ylabel('Z mm')
    axes[0].set_xlabel('Z mm / FRONT right');axes[0].set_ylabel('Y mm / USB up')
    fig.legend(handles=[Patch(color=BLUE,label='fixed FRONT guide'),Patch(color=REAR,label='fixed REAR guide'),Patch(color=CAP,label='one moving printed cap'),Patch(color=PCB,label='original switch')],loc='lower center',ncol=4)
    fig.suptitle('LOCAL ENLARGEMENT / not whole-device scale | provisional functions, actual switch travel UNKNOWN')
    fig.tight_layout(rect=(0,.06,1,.95));fig.savefig(out/'key_sections.png',dpi=180);plt.close(fig)
    if p.get('variant')!='A':return
    fig,axes=plt.subplots(1,3,figsize=(14,6))
    spec=p['side_snaps'][1];y=spec['end_y_mm'];xx=ex-p['wall_mm']
    crop=box([xx-3,y-.05,-10,ex+.1,y+.05,-4])
    panel(axes[0],[(intersection(s,crop),c) for s,c in shells],[1,0,0],[0,0,1],[0,1,0],(xx-3,ex+.1,-10,-4))
    axes[0].set_title(f'RIGHT shell snap Y={y:g}\nPull -Z blocked; release -X then -Z')
    spec=p['side_snaps'][2];y=spec['end_y_mm'];xx=ox+p['wall_mm'];crop=box([ox-.1,y-.05,-10,xx+3,y+.05,-4])
    panel(axes[1],[(intersection(s,crop),c) for s,c in shells],[1,0,0],[0,0,1],[0,1,0],(ox-.1,xx+3,-10,-4))
    axes[1].set_title(f'LEFT shell snap Y={y:g}\nTF and keys are below this latch')
    x,y=m['clip_data'][0]['mount_axis_mm'];xx=24.8 if x>0 else -24.8;crop=box([xx-4,y-.05,-10,xx+4,y+.05,-1])
    panel(axes[2],[(intersection(s,crop),c) for s,c in shells+[(parts['ASSEMBLY'],PCB)]],[1,0,0],[0,0,1],[0,1,0],(xx-4,xx+4,-10,-1))
    axes[2].set_title('Independent PCB retainer\nPCB stays in FRONT when cover removed')
    for ax in axes:ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up, REAR down')
    fig.suptitle('LOCAL ENLARGEMENT / not whole-device scale | elastic release and seam warp UNVERIFIED')
    fig.tight_layout();fig.savefig(out/'long_edge_sections.png',dpi=180);plt.close(fig)
