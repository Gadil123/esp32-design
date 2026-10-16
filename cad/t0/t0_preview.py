"""CAD-derived review views; axes always say FRONT/REAR. No dimensions from renders."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from model import box_between as box
from p1_preview import panel
from p1_checks import intersection
from reference import bounds


def render_side(out,parts,m):
    items=[(m['front'],'#526a80'),(m['rear'],'#8293a4')]
    items += [(parts[k],'#c2b17f') for k in ['TF','J2_USB_SIDE','KEY1','KEY2','KEY3']]
    items += [(s,'#d5a24f') for s in m['caps'].values()]
    fig,ax=plt.subplots(figsize=(4,9))
    panel(ax,items,[0,0,1],[0,1,0],[-1,0,0],(-13,2,-40,46))
    ax.set_title('SIDE -X / USB +Y TOP\nFRONT +Z right / REAR left')
    ax.set_xlabel('Z mm');ax.set_ylabel('Y mm');fig.tight_layout();fig.savefig(out/'side.png',dpi=160);plt.close(fig)


def render_all(out,parts,m,p,plugs,wires,tfprobe,report):
    render_side(out,parts,m)
    blue,gray,amber='#526a80','#8293a4','#d5a24f'
    board=[(parts[k],'#25323c' if k=='DISPLAY' else '#1e806b' if k=='PCB_BOARD' else '#c2b17f') for k in ['PCB_BOARD','DISPLAY','KEY1','KEY2','KEY3','J2_USB_SIDE','TF','MX0','MX1','MIC1']]
    if 'RF_MODULE' in parts:board.append((parts['RF_MODULE'],'#7a8a8b'))
    extra=[(m['battery'],'#c27b53'),(m['speaker'],'#59636b'),(m['foam'],'#30363c'),(m['damping'],'#7f6e7a'),(m['protection'],'#dbb479')]
    extra += [(s,amber) for s in m['caps'].values()]+[(s,'#b2bac2') for s in m['screws']]+[(s,'#b49e6d') for s in m['nuts']]
    extra += [(s,'#eee2bf') for s in plugs.values()]+[(s,'#c74743') for pair in wires.values() for s in pair]
    allitems=[(m['front'],blue),(m['rear'],gray),*board,*extra]
    extent=(-35,76,-40,46)
    fig,axes=plt.subplots(1,2,figsize=(15,7))
    for ax,items,title in [(axes[0],allitems,'FRONT +Z / USB +Y TOP'),(axes[1],board+extra,'FRONT +Z / shell hidden: provisional side bay')]:
        panel(ax,items,[1,0,0],[0,1,0],[0,0,1],extent);ax.set_title(title);ax.set_xlabel('X mm');ax.set_ylabel('Y mm')
    axes[1].text(30,34,'BAT 34 x 50 x 5\nUNVERIFIED',fontsize=8);axes[1].text(31,-31,'SPK 30 x 20 x 6.8\nUNVERIFIED',fontsize=8)
    fig.suptitle('Pocket Pi / Pocket OS T0 | nominal flush screen | REVIEW ONLY');fig.tight_layout();fig.savefig(out/'front.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(15,7))
    for ax,items,title in [(axes[0],allitems,'REAR -Z / USB +Y TOP'),(axes[1],board+extra,'REAR -Z / cover hidden: wire envelopes')]:
        panel(ax,items,[-1,0,0],[0,1,0],[0,0,-1],(-76,35,-40,46));ax.set_title(title);ax.set_xlabel('-X mm');ax.set_ylabel('Y mm')
    axes[1].text(-65,35,'PROVISIONAL ACCESSORIES\nmatching plugs/lead exits UNKNOWN',fontsize=8)
    fig.tight_layout();fig.savefig(out/'rear.png',dpi=140);plt.close(fig)
    w=np.array([1,.8,1.]);w/=np.linalg.norm(w);u=np.array([1,0,-1.]);u/=np.linalg.norm(u);v=np.cross(w,u)
    fig,ax=plt.subplots(figsize=(10,8));panel(ax,allitems,u,v,w,(-35,70,-55,50));ax.set_title('T0 ISO FRONT | FRONT +Z / REAR -Z | USB +Y');fig.tight_layout();fig.savefig(out/'iso_front.png',dpi=140);plt.close(fig)
    # A section through the lowest original nut, plus the side-bay thickness stack.
    y=m['clip_data'][0]['mount_axis_mm'][1]
    clip=box([-32,y-.10,-12.5,73,y+.10,1.5])
    section=[(intersection(parts['ASSEMBLY'],clip),'#7a8b7d'),(intersection(m['front'],clip),blue),(intersection(m['rear'],clip),gray)]
    section += [(intersection(s,clip),c) for s,c in extra]
    fig,ax=plt.subplots(figsize=(14,4));panel(ax,section,[1,0,0],[0,0,1],[0,1,0],(-32,73,-13,3));ax.set_xlabel('X mm');ax.set_ylabel('Z mm')
    d=report['checks']['maximum_complete_assembly_thickness']['actual_maximum_mm'];ax.set_title(f'THICKNESS SECTION Y={y:.2f} | FRONT +Z up / REAR down | FULL ASSEMBLY MAX {d:.3f} mm')
    ax.axhline(m['dimensions']['glass_and_front_z_mm'],color='#c84443',ls='--',lw=.7);ax.axhline(m['dimensions']['rear_bottom_z_mm'],color='#c84443',ls='--',lw=.7)
    fig.tight_layout();fig.savefig(out/'thickness_section.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,6))
    # M2 axis and nut loading slot.
    x,y=p['m2_axes_xy_mm'][0];clip=box([x-4,y-.07,-12,x+4,y+.07,1])
    items=[(intersection(s,clip),c) for s,c in [(m['front'],blue),(m['rear'],gray),(m['screws'][0],'#b2bac2'),(m['nuts'][0],'#b49e6d')]]
    panel(axes[0],items,[1,0,0],[0,0,1],[0,1,0],(x-4,x+4,-12,1));axes[0].set_title('M2 SIDE-BAY SECTION\nFRONT +Z up / REAR down')
    snap=m['snap_data'][0];x=snap['free_x_mm'];y=p['outer_y_mm'][0]+p['wall_mm'];clip=box([x-.08,y-2,-10,x+.08,y+2,0])
    items=[(intersection(m['front'],clip),blue),(intersection(m['rear'],clip),gray)]
    panel(axes[1],items,[0,1,0],[0,0,1],[1,0,0],(y-2,y+2,-10,-4));axes[1].set_title('PERIPHERAL SNAP SECTION\nFRONT +Z up / REAR down');axes[1].set_xlabel('Y mm')
    x,y=m['clip_data'][0]['mount_axis_mm'];xx=24.8 if x>0 else -24.8;clip=box([xx-4,y-.08,-10,xx+4,y+.08,-1])
    items=[(intersection(parts['ASSEMBLY'],clip),'#7a8b7d'),(intersection(m['front'],clip),blue),(intersection(m['rear'],clip),gray)]
    panel(axes[2],items,[1,0,0],[0,0,1],[0,1,0],(xx-4,xx+4,-10,-1));axes[2].set_title('PCB EDGE RETAINER SECTION\nFRONT +Z up / REAR down');axes[2].set_xlabel('X mm')
    for ax in axes:ax.set_ylabel('Z mm')
    fig.suptitle('Connection B: peripheral snaps + TWO bay screws / PCB independently retained');fig.tight_layout();fig.savefig(out/'connection_sections.png',dpi=160);plt.close(fig)
    # Rear cutaway shows real connector shapes and full provisional wire envelopes.
    fig,ax=plt.subplots(figsize=(11,8));items=[(parts[k],'#b9a56f') for k in ['MX0','MX1','MIC1']]+[(parts['PCB_BOARD'],'#1c8069')]+extra
    panel(ax,items,[-1,0,0],[0,1,0],[0,0,-1],(-72,-5,-36,40));ax.set_title('RIGHT CONNECTORS / VIEW REAR -Z\nMX0 upper / MX1 lower; SPK-BAT identity NOT confirmed');ax.set_xlabel('-X mm');ax.set_ylabel('Y mm')
    for k in ['MX0','MX1','MIC1']:
        b=bounds(parts[k]);x,y=-(b[0]+b[3])/2,(b[1]+b[4])/2;ax.annotate(k,(x,y),(-8,y),arrowprops={'arrowstyle':'->'},fontsize=8)
    fig.tight_layout();fig.savefig(out/'connector_layout.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,6))
    # USB top mouth, then left-edge TF and three native keys.
    panel(axes[0],[(m['front'],blue),(m['rear'],gray),(parts['J2_USB_SIDE'],'#b2bac2')],[1,0,0],[0,0,1],[0,1,0],(-10,10,-12,1));axes[0].set_title('USB TOP +Y\nFRONT +Z up / REAR down')
    left=[(m['front'],blue),(m['rear'],gray),*[(parts[k],'#b9a56f') for k in ['TF','KEY1','KEY2','KEY3']],*[(s,amber) for s in m['caps'].values()]]
    panel(axes[1],left,[0,1,0],[0,0,1],[-1,0,0],(-32,15,-11,1));axes[1].set_title('LEFT -X / TF + NATIVE KEYS\nFRONT +Z up / REAR down');axes[1].set_xlabel('Y mm')
    tb=bounds(parts['TF']);yc=(tb[1]+tb[4])/2;clip=box([-33,yc-.08,-8,-10,yc+.08,-4.8])
    panel(axes[2],[(intersection(s,clip),c) for s,c in [(m['front'],blue),(m['rear'],gray),(parts['TF'],'#b9a56f'),(tfprobe,'#5ca8b9')]], [1,0,0],[0,0,1],[0,1,0],(-33,-10,-8,-4.8));axes[2].set_title('TF EXTERNAL APPROACH SECTION\nFRONT +Z up / REAR down');axes[2].set_xlabel('X mm')
    for ax in axes:ax.set_ylabel('Z mm')
    fig.suptitle('Interface positions from original STEP / TF seat, eject and actual switch travel UNVERIFIED');fig.tight_layout();fig.savefig(out/'interface_openings.png',dpi=160);plt.close(fig)
