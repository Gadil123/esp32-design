"""Actual BRep sections. Colored accessory bodies and air probes are explicit proxies."""
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from build123d import Compound
from model import box_between as box
from t0_g_v1_integrated_drawings import section
from t0_g_v1_preview import panel
from reference import bounds
from p1_checks import intersection, clashes
import json

def render(out,parts,m,h,report,bore,air):
    board=Compound(parts['ASSEMBLY'].solids())
    # Local translation sensitivity only, NOT a redesigned narrower shell.
    zone=box([65.7,-30,-9.5,67.45,-26,-1])
    receiver=intersection(m['front'],zone)
    fixed=m['front']-zone
    width_rows=[]
    for reduction in [2.0,4.0]:
        probe=receiver.translate((-reduction,0,0))
        width_rows.append(dict(reduction_mm=reduction,receiver_bounds_mm=bounds(probe),
            hits=clashes(probe,[('unchanged_front_including_speaker_fence',fixed),('speaker_body',m['speaker']),('battery_body',m['battery'])],.001)))
    (out/'width_local_checks.json').write_text(json.dumps(dict(
        frozen_receiver_probe_bounds_mm=bounds(receiver),rows=width_rows,
        limitation='Only a cropped real lower-right latch receiver translated in X. Rear beam, support, registration, wall, tray and tool paths NOT redesigned or validated. A clear local probe is not full-case approval.'),indent=2)+'\n')
    def save(fig,name):
        fig.tight_layout(rect=(0,0,1,.91));fig.savefig(out/name,dpi=170);plt.close(fig)
    colors=[(m['front'],'#547b92'),(m['rear'],'#789eb3'),(board,'#b9bdc2'),(m['battery'],'#d7ac57'),(m['speaker'],'#b87768'),(m['foam'],'#72517f'),(m['damping'],'#72517f')]
    fig,axs=plt.subplots(1,2,figsize=(14,7));x,y=h['mic_candidate']['front_xy_mm']
    slab=box([19,y-.12,-12,32,y+.12,1])
    items=[(section(s,slab),c) for s,c in colors]+[(section(parts['MIC1'],slab),'#e95143')]
    panel(axs[0],items,[1,0,0],[0,0,1],[0,1,0],(19,32,-12,1))
    for a,b in zip(report['microphone']['air_probe_points_mm'],report['microphone']['air_probe_points_mm'][1:]):
        axs[0].plot([a[0],b[0]],[a[2],b[2]],'--',color='#21a088',lw=2)
    axs[0].plot([x,x],[-.5,.7],'--',color='#e95143',lw=4)
    axs[0].annotate('PROPOSED FRONT hole D1.5\nNOT cut / port UNVERIFIED',(x,.1),(29,-2),arrowprops={'arrowstyle':'->'},fontsize=8)
    axs[0].annotate('MIC1 exterior, NOT proven inlet',(22.8,-6.6),(19.2,-9.4),arrowprops={'arrowstyle':'->'},fontsize=8)
    axs[0].set_title(f'MIC local XZ section / Y={y:.3f} +/-0.12\nFRONT +Z up; REAR -Z down',fontsize=10)
    axs[0].set_xlabel('X mm');axs[0].set_ylabel('Z mm')
    slab=box([-30,14.38,-12,71,14.62,1])
    panel(axs[1],[(section(s,slab),c) for s,c in colors],[1,0,0],[0,0,1],[0,1,0],(-30,71,-12,1))
    z=report['battery_z_chain']
    axs[1].set_title('PCB / battery transverse XZ section Y=14.5 +/-0.12\nSpeaker lies at Y=-22.4; see companion plan',fontsize=10)
    fig.text(.54,.14,f'Rear panel 1.20 + adhesive candidate 0.20 + body 7.61\nFront inner Z {z["front_inner_mm"]:.2f}; body front {z["body_front_mm"]:.2f}\nHeadroom {z["geometric_headroom_mm"]:.2f}; after candidate 1mm swelling: {z["remaining_after_candidate_swelling_mm"]:.2f}\nProtection / connector / bend envelope UNKNOWN; no battery clamping accepted.',fontsize=9)
    axs[1].set_xlabel('X mm / FRONT-facing coordinates')
    fig.suptitle('Frozen G-V1 real BRep sections / measured accessory BODY envelopes only\nDashed green = geometric air probe, NOT a duct or proven acoustic path')
    save(fig,'MIC_and_battery_XZ_sections.png')
    fig,axs=plt.subplots(1,2,figsize=(15,9))
    # Remove lid from plan and cut at Z=-6.4 to expose actual internal structure.
    slab=box([-30,-36,-6.52,71,42,-6.28])
    panel(axs[0],[(section(s,slab),c) for s,c in colors if s is not m['rear']],[1,0,0],[0,1,0],[0,0,1],(-30,71,-36,42))
    axs[0].plot(x,y,'rx');axs[0].set_title('FRONT +Z cutaway / Z=-6.40 +/-0.12\nUSB +Y TOP / lid omitted',fontsize=10)
    axs[0].annotate('MIC1 / actual exterior',(22.8,1.395),(32,0),fontsize=8,arrowprops={'arrowstyle':'->'})
    axs[0].text(35,18,'BATTERY\n29.49 X\n42.26 Y\n7.61 Z\nBODY ONLY',fontsize=9)
    axs[0].text(34,-25,'SPEAKER\n30 X 20 X 6.5\n40mm lead approx',fontsize=8)
    # Longitudinal real cut through both accessory bodies.
    slab=box([45.88,-36,-12,46.12,42,1])
    panel(axs[1],[(section(s,slab),c) for s,c in colors],[0,1,0],[0,0,1],[1,0,0],(-36,42,-12,1))
    axs[1].set_title('SIDE +X observer / YZ section X=46 +/-0.12\nFRONT +Z up; USB +Y right',fontsize=10)
    axs[1].set_xlabel('Y mm');axs[1].set_ylabel('Z mm')
    fig.text(.54,.14,'Speaker front foam is a candidate perimeter ring.\nWire-side fence notch remains open; no sealed partition proved.\nNew 6.5mm body leaves 0.3mm rear-support gap with old damping.\nNo new chamber or battery-compressing seal is introduced.',fontsize=9)
    fig.suptitle('PCB / battery / speaker functional separation: real solids, not an acoustic simulation\nBlue=case; gray=board; ochre=battery body; red=speaker body; purple=foam/damping candidate')
    save(fig,'PCB_battery_speaker_sections.png')
    fig,axs=plt.subplots(1,2,figsize=(14,8))
    for ax,old in zip(axs,[True,False]):
        layer=[(m['front'],'#547b92')]
        # Hide FRONT panel: use actual rear shell as outline/background instead.
        layer=[(m['rear'],'#789eb3'),(board,'#b9bdc2')]
        if old:
            layer.extend([(box(report['old_battery_body_bounds_mm']),'#d7ac57'),(box(report['old_speaker_body_bounds_mm']),'#b87768')])
        else: layer.extend([(m['battery'],'#d7ac57'),(m['speaker'],'#b87768')])
        panel(ax,layer,[1,0,0],[0,1,0],[0,0,1],(-32,73,-38,44))
        ax.set_title(('FROZEN old placeholders' if old else 'MEASURED BODIES / full package unknown')+'\nFRONT +Z cutaway / lid structure visible / USB +Y',fontsize=10)
        ax.set_xlabel('X mm');ax.set_ylabel('Y mm')
    fig.suptitle('SAME SCALE: outer size remains 99.60 x 77.86 x 12.369521mm\nNo narrower shell released; original keys, screws, closure, grille preserved')
    save(fig,'old_new_body_same_scale_FRONT.png')
