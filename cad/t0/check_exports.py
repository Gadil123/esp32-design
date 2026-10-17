"""Round-trip STEP plus independent STL mesh closure and unit checks."""
from collections import Counter
import struct
import numpy as np
from build123d import import_step
from reference import bounds


def verify_exports(out, names=('front_shell','rear_shell')):
    results={}
    for name in names:
        solid=import_step(out/f'{name}.step')
        data=(out/f'{name}.stl').read_bytes()
        count=struct.unpack_from('<I',data,80)[0]
        assert len(data)==84+50*count, 'Expected binary STL'
        triangles=[];edges=Counter()
        for i in range(count):
            points=struct.unpack_from('<12fH',data,84+50*i)[3:12]
            tri=[tuple(points[j:j+3]) for j in [0,3,6]]
            triangles.append(tri)
            for a,b in [(0,1),(1,2),(2,0)]:
                edges[tuple(sorted([tri[a],tri[b]]))]+=1
        t=np.asarray(triangles)
        bad_edges=sum(n!=2 for n in edges.values())
        mesh_bounds=[*t.min(axis=(0,1)),*t.max(axis=(0,1))]
        bounds_error=max(abs(a-b) for a,b in zip(mesh_bounds,bounds(solid)))
        mesh_volume=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
        relative_volume_error=abs(mesh_volume-solid.volume)/solid.volume
        assert solid.is_valid and len(solid.solids())==1
        assert bad_edges==0 and bounds_error<.05 and relative_volume_error<.005
        results[name]={'step_valid':solid.is_valid,'step_solid_count':len(solid.solids()),
                       'stl_triangles':count,'stl_nonmanifold_edges':bad_edges,
                       'step_stl_bounds_error_mm':bounds_error,
                       'step_stl_relative_volume_error':relative_volume_error}
    return results
