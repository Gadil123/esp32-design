"""Original STEP occurrence geometry; preserve every parent placement."""
from build123d import import_step,Compound,Location,export_brep
from reference import bounds,to_pocket,hole_axes,compare_recorded,SELECT


def load(path,cache=None):
    root=import_step(path);parts={};mounts=[];connectors=[];tree=[]
    names={**SELECT,'TF1_ASM':'TF','U5_ASM':'RF_MODULE'}
    def walk(n,parent=Location(),depth=0):
        if n.label in names or n.label in ['SMTSO-M2_5-4ET','HP1_25MM-2P-SMT-HORIZONTAL']:
            s=Compound.cast(n.wrapped.Moved(parent.wrapped));s.parent=None;s=to_pocket(s)
            tree.append({'label':n.label,'bounds_mm':bounds(s),'children':[c.label for c in n.children]})
            if n.label in names:parts[names[n.label]]=s
            elif n.label=='SMTSO-M2_5-4ET':mounts.append(s)
            else:connectors.append(s)
        for c in n.children:walk(c,parent*n.location,depth+1)
    walk(root);parts['ASSEMBLY']=to_pocket(Compound(root.wrapped))
    for i,s in enumerate(sorted(connectors,key=lambda s:s.center().Y,reverse=True)):parts[f'MX{i}']=s
    assert len(mounts)==4 and len(connectors)==2 and 'TF' in parts
    if cache:
        cache.mkdir(parents=True,exist_ok=True)
        for k,s in parts.items():export_brep(s,cache/f'{k}.brep')
        for i,s in enumerate(mounts):export_brep(s,cache/f'MOUNT{i}.brep')
    return parts,mounts,tree
