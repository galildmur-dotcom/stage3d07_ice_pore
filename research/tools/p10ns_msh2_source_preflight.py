#!/usr/bin/env python3
"""Independent MSH2 text-only source quality check, no Gmsh API required."""
import hashlib
from pathlib import Path
import numpy as np
from p10ns_volume_audit import det_statistics, EDGES

SOURCE=Path(__file__).resolve().parent/'P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
EXPECTED='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'

def load_msh(path):
    nodes={}
    tets={}
    with path.open(encoding='utf-8') as f:
        it=iter(f)
        for line in it:
            if line.strip()=='$Nodes':
                count=int(next(it))
                for _ in range(count):
                    t=next(it).split()
                    nodes[int(t[0])]=np.asarray([float(x) for x in t[1:4]])
            if line.strip()=='$Elements':
                count=int(next(it))
                for _ in range(count):
                    t=[int(x) for x in next(it).split()]
                    if t[1]==11:
                        tets[t[0]]=tuple(t[3+t[2]:])
    return {'nodes':nodes,'tets':tets}

def main():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('source SHA mismatch')
    snap=load_msh(SOURCE)
    assert len(snap['nodes'])==26099 and len(snap['tets'])==18004
    # Check each midside node belongs to the intended edge on the known M13 source.
    mismatch=0
    maxerr=0.
    for c in snap['tets'].values():
        midpoint=np.array([(snap['nodes'][c[i]]+snap['nodes'][c[j]])/2 for i,j in EDGES])
        for k,(i,j) in enumerate(EDGES):
            distances=np.linalg.norm(midpoint-snap['nodes'][c[4+k]],axis=1)
            delta=distances[k]
            maxerr=max(maxerr,float(delta))
            mismatch+=int(np.argmin(distances)!=k)
    print('P10NS_SOURCE_MIDSIDES nearest_midpoint_mismatch',mismatch,'max_curved_offset_m',maxerr,flush=True)
    for n in (3,7,9):
        out=det_statistics(snap,n)
        print('P10NS_SOURCE_DETJ',n,'min',out['min_detJ'],'nonpositive',out['nonpositive_qps'],flush=True)
        assert out['nonpositive_qps']==0
    print('P10NS_SOURCE_PREFLIGHT_PASS',flush=True)

if __name__=='__main__':main()
