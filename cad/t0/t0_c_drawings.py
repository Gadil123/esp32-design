"""Actual CAD stage-gate drawings, never a completed C enclosure rendering."""
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from p1_preview import panel
from p1_checks import intersection
from model import box_between as box
from reference import bounds


def render(out,parts,mounts,rows,seats,stops,patches,backup,screws,usb,fixtures,release):
    blue,gray,orange='#526a80','#8293a4','#edac4a'
    y=rows[0]['axis_xy_mm'][1];clip=box([-31,y-.06,-12,30,y+.06,2])
    fig,axes=plt.subplots(3,1,figsize=(14,10))
    for ax,dz,title in [(axes[0],0,'Final pose: nominal static fit only'),(axes[1],-2,'Blocked REAR insertion: module 2mm behind final / REAR cover absent')]:
        scene=[(m.translate((0,0,dz)),'#b6a77a') for m in mounts]+[(parts['DISPLAY'].translate((0,0,dz)),'#9eafaa'),(parts['PCB_BOARD'].translate((0,0,dz)),'#258870')]+[(s,orange) for s in stops]+([(s,gray) for s in seats+patches] if dz==0 else [])
        panel(ax,[(intersection(s,clip),c) for s,c in scene],[1,0,0],[0,0,1],[0,1,0],(-31,30,-12,2));ax.set_title(title);ax.set_xlabel('X mm');ax.set_ylabel('Z mm / FRONT up')
    x=rows[0]['axis_xy_mm'][0];local=box([x-5,y-.05,-12,x+5,y+.05,-2])
    scene=[(parts['ASSEMBLY'],'#73a58e')]+[(s,gray) for s in backup]+[(s,'#bd9661') for s in screws]
    panel(axes[2],[(intersection(s,local),c) for s,c in scene],[1,0,0],[0,0,1],[0,1,0],(x-5,x+5,-12,-2));axes[2].set_title('Backup: two M2.5 to REAR, not FRONT | 0.8mm seat MANUFACTURING_RISK');axes[2].set_xlabel('X mm');axes[2].set_ylabel('Z mm / FRONT up')
    fig.suptitle('C STAGE GATE BLOCKED / local sections only | FRONT +Z, REAR -Z, USB +Y | not whole C assembly')
    fig.tight_layout();fig.savefig(out/'mount_assembly_sections.png',dpi=160);plt.close(fig)
    # True original board proportions with local fixtures, not a claimed four-latch shell.
    fig,axes=plt.subplots(1,3,figsize=(15,8));scene=[(m,'#b6a77a') for m in mounts]+[(parts['DISPLAY'],'#35505b'),(parts['PCB_BOARD'],'#258870')]+[(s,orange) for s in stops]+[(s,gray) for s in seats+patches]
    for ax,u,v,w,extent,title in [(axes[0],[1,0,0],[0,1,0],[0,0,1],(-31,31,-36,43),'FRONT +Z / USB +Y TOP'),(axes[1],[0,0,1],[0,1,0],[-1,0,0],(-12,2,-36,43),'LEFT -X / FRONT right / USB TOP'),(axes[2],[-1,0,0],[0,1,0],[0,0,-1],(-31,31,-36,43),'REAR -Z / USB +Y TOP')]:
        panel(ax,scene,u,v,w,extent);ax.set_title(title);ax.set_xlabel('mm');ax.set_ylabel('Y mm')
    fig.suptitle('C local mounting study | board at true proportions; NO completed C enclosure / insertion BLOCKED');fig.tight_layout();fig.savefig(out/'mount_orthographic.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,5));front,rear,ribs,probe=usb
    panel(axes[0],[(front,blue),(rear,gray),(parts['J2_USB_SIDE'],'#bba875')],[1,0,0],[0,0,1],[0,1,0],(-11,11,-12,1));axes[0].set_title('USB +Y TOP | FRONT up / REAR down\nOriginal opening retained; lower web ~0.880mm')
    panel(axes[1],[(rear,gray),*[(s,orange) for s in ribs]], [1,0,0],[0,1,0],[0,0,-1],(-11,11,35,43));axes[1].set_title('Local two-side buttresses / rear view\nThin bottom web still MANUFACTURING_RISK')
    for ax in axes:ax.set_xlabel('X mm')
    fig.suptitle('USB local study within existing 12.4mm envelope, not whole C approval');fig.tight_layout();fig.savefig(out/'usb_local.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    for ax,key in zip(axes,['KEY1','KEY3']):
        front,rear,cap,d=fixtures[key];y,z=d['center_yz_mm'];clip=box([-32,y-.04,-10,-21,y+.04,-3])
        panel(ax,[(intersection(s,clip),c) for s,c in [(front,blue),(rear,gray),(cap,orange),(parts[key],'#258870')]], [1,0,0],[0,0,1],[0,1,0],(-32,-21,-10,-3));ax.set_title(key+' / FRONT +Z up, REAR down');ax.set_xlabel('X mm');ax.set_ylabel('Z mm')
    fig.suptitle('LOCAL ENLARGEMENT | PA12 trial .3mm guide / RESET D2.2, recess1.0 | no functional approval');fig.tight_layout();fig.savefig(out/'key_sample_sections.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,7))
    scene=[(parts['PCB_BOARD'],'#258870'),(parts['DISPLAY'],'#35505b')]+[(s,orange) for s in release['snaps']]
    panel(axes[0],scene,[1,0,0],[0,1,0],[0,0,1],(-32,72,-38,44))
    axes[0].plot([-29.47,70.13,70.13,-29.47,-29.47],[-35.93,-35.93,41.93,41.93,-35.93],'--',color=blue)
    for n,(x,y) in enumerate(release['locations']):axes[0].annotate(str(n+1),(x,y),(x+4,y+4),arrowprops={'arrowstyle':'->'})
    axes[0].set_title('FRONT +Z / USB +Y TOP\nFour locations only; dashed outline is target envelope')
    f,r=release['coupon'];clip=box([25.96,-37,-12,26.04,-30,-4])
    panel(axes[1],[(intersection(s,clip),c) for s,c in [(f,blue),(r,gray)]],[0,1,0],[0,0,1],[1,0,0],(-37,-30,-12,-4))
    axes[1].set_title('Bottom snap local section / FRONT up\nPush inward .8mm, hold local gap >=3mm')
    fig.suptitle('Opening concept: 1 bottom -> 2 right -> 3 top -> 4 left; hand supports opened cover\nLOCAL tool/anti-recapture fixture only. Continuous flexible-cover sequence UNVERIFIED; C mounting gate BLOCKED.')
    fig.tight_layout();fig.savefig(out/'four_latch_release_plan.png',dpi=160);plt.close(fig)
