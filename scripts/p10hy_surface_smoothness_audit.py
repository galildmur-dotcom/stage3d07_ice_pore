#!/usr/bin/env python3
"""Read-only Gmsh Tri6 wall edge and exact C2 kappa audit for pinned M1/P10HV."""
import csv
import hashlib
import io
import json
import math
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    import p10hw_independent_three_alpha_scan as qpa
except ModuleNotFoundError:
    import p10hv_independent_scan as qpa

C=np.array([0.,0.,.03])
R=.001
R_SCALE=.75
A_SCALE=.60
DEN=.012553396310432353
EPS=1e-12

def source(path):
    xyz=[];scores=[]
    with path.open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==1200
    for i,r in enumerate(rows):
        assert (int(r['radial_bin']),int(r['mu_bin']),int(r['phi_bin']))==(i//120,(i%120)//12,i%12)
        dlo=float(r['d_lower_mm'])
        dhi=float(r['d_upper_mm']) if r['d_upper_mm'] else None
        d=(dlo+dhi)*.5 if dhi is not None else dlo
        t=float(r['theta_mid_rad']);phi=float(r['phi_mid_rad'])
        xyz.append([np.log1p(d/.05),np.sin(t)*np.cos(phi),np.sin(t)*np.sin(phi),np.cos(t)])
        scores.append(float(r['mechanical_robust_score25']))
    return np.array(xyz),np.array(scores)

def eval_kappa(src,val,points):
    p=np.asarray(points)
    local=p-C
    rho=np.linalg.norm(local,axis=1)
    d=np.maximum(rho-R,0)*1000
    query=np.column_stack([np.log1p(d/.05),local/rho[:,None]])
    srcscaled=src/np.array([R_SCALE,A_SCALE,A_SCALE,A_SCALE])
    result=[]
    for v in query/np.array([R_SCALE,A_SCALE,A_SCALE,A_SCALE]):
        loc=np.flatnonzero(abs(srcscaled[:,0]-v[0])<1)
        d2=((srcscaled[loc]-v)**2).sum(axis=1)
        good=d2<1
        t=np.sqrt(np.maximum(d2[good],0))
        w=np.maximum(1-t,0)**4*(4*t+1)
        result.append(np.clip(np.dot(w,val[loc[good]])/(w.sum()+EPS)/DEN,0,1))
    return np.asarray(result)

def read_faces(data):
    f=io.StringIO(data.decode('ascii'))
    faces=[]
    for line in f:
        if line.strip()=='$Elements':
            n=int(next(f))
            for _ in range(n):
                q=list(map(int,next(f).split()))
                typ,nt=q[1:3]
                if typ==9 and q[3]==8:
                    assert len(q[3+nt:])==6
                    faces.append(q[3+nt:])
    return np.array(faces,dtype=int)

def stats(x):
    x=np.asarray(x)
    if len(x)==0:return dict(n=0)
    return dict(n=len(x),median=float(np.median(x)),p05=float(np.percentile(x,5)),p95=float(np.percentile(x,95)),max=float(np.max(x)))

def mesh_report(raw,src,val):
    nodes,tet,face_counts=qpa.read_msh(raw)
    faces=read_faces(raw)
    wall_ids=np.unique(faces)
    assert np.max(abs(np.linalg.norm(nodes[wall_ids]-C,axis=1)-R))<1e-10
    k_wall=eval_kappa(src,val,nodes[wall_ids])
    corner_edges=set()
    edge_to_faces=defaultdict(list)
    hface=[]
    for faceid,f in enumerate(faces):
        pts=nodes[f[:3]]-C
        lengths=[]
        for i,j in ((0,1),(1,2),(2,0)):
            a,b=int(f[i]),int(f[j]);edge=tuple(sorted((a,b)))
            corner_edges.add(edge);edge_to_faces[edge].append(faceid)
            cosang=np.clip(np.dot(pts[i],pts[j])/(R*R),-1,1)
            lengths.append(float(R*np.arccos(cosang)*1000))
        hface.append(np.median(lengths))
    hface=np.asarray(hface)
    edges=np.array(sorted(corner_edges),int)
    points=nodes[edges].sum(axis=1)*.5-C
    points=C+R*points/np.linalg.norm(points,axis=1)[:,None]
    kappas=eval_kappa(src,val,points)
    pts=nodes[edges]-C
    cosang=np.einsum('ij,ij->i',pts[:,0,:],pts[:,1,:])/(R*R)
    h=R*np.arccos(np.clip(cosang,-1,1))*1000
    mu=(points[:,2]-C[2])/R
    sectors={'north_polar':mu>=.8,'south_polar':mu<=-.8,
             'north_taper':(mu>=.6)&(mu<.8),
             'south_taper':(mu<=-.6)&(mu>-.8),
             'off_polar':abs(mu)<=.6,
             'kappa_ge_0p8':kappas>=.8,
             'kappa_ge_0p6':kappas>=.6,
             'kappa_lt_0p2':kappas<.2}
    edge_report={name:{'h_mm':stats(h[mask]),'kappa':stats(kappas[mask])}
                 for name,mask in sectors.items()}
    q=[]
    for ids in edge_to_faces.values():
        if len(ids)!=2:raise ValueError('Pore surface edge must be paired')
        v0,v1=hface[ids]
        q.append(max(v0,v1)/min(v0,v1))
    return {
        'tet10':len(tet),'pore_tri6':len(faces),
        'wall_nodes':len(wall_ids),'wall_node_kappa':stats(k_wall),
        'edge_total':len(edges),'edge_report':edge_report,
        'surface_triangle_h_mm':stats(hface),
        'surface_neighbor_tri_h_ratio':stats(q),
        'surface_neighbor_p95':float(np.percentile(q,95)),
        'surface_neighbor_fraction_q_gt_1p25':float(np.mean(np.array(q)>1.25))
    }

def main():
    src,val=source(Path(sys.argv[1]))
    a=Path(sys.argv[2]).read_bytes()
    assert hashlib.sha256(a).hexdigest()=='47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'
    result={'M1':mesh_report(a,src,val)}
    with zipfile.ZipFile(sys.argv[3]) as z:
        worker=json.loads(z.read('P10HV_WORKER_RESULT.json'))
        for c in worker['results']:
            raw=z.read(c['mesh_filename'])
            assert hashlib.sha256(raw).hexdigest()==c['mesh_sha256']
            result[f"alpha_{c['alpha']:.2f}"]=mesh_report(raw,src,val)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
