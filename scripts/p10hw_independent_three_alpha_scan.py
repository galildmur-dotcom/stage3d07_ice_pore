#!/usr/bin/env python3
"""Read-only curved Tet10 comparison of the three original P10HV alpha meshes."""
import hashlib
import io
import json
import math
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np

EDGE = ((0,1),(1,2),(2,0),(0,3),(2,3),(1,3))
DL = np.array([[-1.,-1.,-1.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
CAD_VOL = .06*.06*.05 - 4*math.pi*.001**3/3

def rule(order):
    pt,wt=np.polynomial.legendre.leggauss(order)
    pt=(pt+1)/2;wt=wt/2
    ns=[];ds=[];ws=[]
    for a,aw in zip(pt,wt):
        for b,bw in zip(pt,wt):
            for c,cw in zip(pt,wt):
                r=a;s=(1-r)*b;t=(1-r)*(1-b)*c
                L=np.array([1-r-s-t,r,s,t])
                ns.append(list(L*(2*L-1))+[4*L[i]*L[j] for i,j in EDGE])
                ds.append(list((4*L[:,None]-1)*DL)+[4*(L[i]*DL[j]+L[j]*DL[i]) for i,j in EDGE])
                ws.append(aw*bw*cw*(1-r)**2*(1-b))
    return np.asarray(ns),np.asarray(ds),np.asarray(ws)

def read_msh(raw):
    f=io.StringIO(raw.decode("ascii"))
    nodes={};tets=[];faces=Counter()
    for line in f:
        if line.strip()=="$Nodes":
            n=int(next(f))
            for _ in range(n):
                q=next(f).split();nodes[int(q[0])]=[float(x) for x in q[1:]]
        if line.strip()=="$Elements":
            n=int(next(f))
            for _ in range(n):
                row=list(map(int,next(f).split()))
                kind,nt=row[1:3];phys=row[3];indices=row[3+nt:]
                if kind==11:
                    assert phys==1 and len(indices)==10
                    tets.append(indices)
                elif kind==9:
                    assert 2<=phys<=9 and len(indices)==6
                    faces[phys]+=1
                else:raise ValueError(f"Unexpected element type {kind}")
    assert set(faces)==set(range(2,10))
    arr=np.zeros((max(nodes)+1,3))
    for k,v in nodes.items():arr[k]=v
    return arr,np.asarray(tets),faces

def evaluate(nodes,tets,order,full):
    N,D,W=rule(order)
    regvol=np.zeros(18);neff=np.zeros(18)
    volume=np.zeros(len(tets))
    minj=math.inf
    for k in range(0,len(tets),48):
        p=nodes[tets[k:k+48]]
        J=np.einsum('nic,qij->nqcj',p,D,optimize=True)
        det=np.linalg.det(J)
        if not np.all(np.isfinite(det)) or np.any(det<=0):
            raise ValueError(f"Nonpositive Jacobian at order {order}, tet {k}")
        minj=min(minj,float(det.min()))
        w=det*W[None,:]
        volume[k:k+len(p)]=w.sum(axis=1)
        if order==3:continue
        x=np.einsum('nic,qi->nqc',p,N,optimize=True)
        v=x-np.array([0.,0.,.03])
        rr=np.linalg.norm(v,axis=2)
        d=rr-.001
        mu=v[:,:,2]/rr
        rad=np.where(d<.0001,0,np.where(d<.0005,1,2))
        pol=np.where(np.abs(mu)>=.8,0,np.where(np.abs(mu)>.6,1,2))
        code=(rad*3+pol)*2+(mu<0).astype(int)
        regvol+=np.bincount(code.ravel(),weights=w.ravel(),minlength=18)
        neff+=np.bincount(code.ravel(),weights=(w/full[k:k+len(p),None]).ravel(),minlength=18)
    return {'volume':volume,'regvol':regvol,'neff':neff,'minj':minj}

def groups(q):
    v=q['regvol'];n=q['neff']
    out={}
    for r in range(3):
        for p in range(3):
            for h in range(2):
                i=(r*3+p)*2+h
                out[f"r{r}_p{p}_{'N' if h==0 else 'S'}"]={'Veff':float(v[i]/n[i]),'Neff':float(n[i]),'region_m3':float(v[i])}
    for p in range(3):
        for h,name in enumerate(('N','S')):
            ids=[(r*3+p)*2+h for r in (0,1)]
            out[f"near_p{p}_{name}"]={'Veff':float(v[ids].sum()/n[ids].sum()),'Neff':float(n[ids].sum())}
    return out

def neighbour_quality(nodes,tets,vol):
    face_map={}
    for k,t in enumerate(tets):
        a,b,c,d=map(int,t[:4])
        for face in ((a,b,c),(a,b,d),(a,c,d),(b,c,d)):
            key=tuple(sorted(face))
            face_map.setdefault(key,[]).append(k)
    cent=nodes[tets[:,:4]].mean(axis=1)
    radial=cent-np.array([0.,0.,.03])
    distance=np.linalg.norm(radial,axis=1)-.001
    mu=np.abs(radial[:,2]/np.linalg.norm(radial,axis=1))
    near=(distance<=.0005)&(mu>=.8)
    qa=[];polar=[]
    for pair in face_map.values():
        if len(pair)!=2:continue
        i,j=pair
        q=float(max(vol[i],vol[j])/min(vol[i],vol[j]))
        qa.append(q)
        if near[i] or near[j]:polar.append(q)
    def summarize(v):
        a=np.asarray(v,float)
        return {'pairs':len(v),'p95':float(np.percentile(a,95)),
                'max':float(a.max()),'count_q_gt_1p25':int(np.sum(a>1.25)),
                'fraction_q_gt_1p25':float(np.mean(a>1.25))}
    return {'all':summarize(qa),'near_polar_either_centroid':summarize(polar)}

def main(path):
    raw=path.read_bytes();result={'zip_sha256':hashlib.sha256(raw).hexdigest(),'meshes':{}}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        guard=json.loads(z.read('P10HV_GUARD_RESULT.json'))
        report=json.loads(z.read('P10HV_WORKER_RESULT.json'))
        assert guard['status']=='WORKER_FINISHED' and guard['exit_code']==0
        assert report['FEM_attempts']==0 and not report['accepted_M2']
        for item in report['results']:
            alpha=item['alpha'];label=f"{alpha:.2f}"
            mesh=z.read(item['mesh_filename'])
            assert hashlib.sha256(mesh).hexdigest()==item['mesh_sha256']
            nodes,tets,faces=read_msh(mesh)
            assert len(nodes)-1==item['mesh_nodes'] and len(tets)==item['tet10']
            full=evaluate(nodes,tets,3,None)
            q7=evaluate(nodes,tets,7,full['volume'])
            q9=evaluate(nodes,tets,9,full['volume'])
            a=groups(q7);b=groups(q9)
            result['meshes'][label]={
                'alpha':alpha,'sha256':item['mesh_sha256'],
                'nodes':len(nodes)-1,'tet10':len(tets),
                'faces':dict(faces),
                'total_volume_343':float(q7['volume'].sum()),
                'total_volume_729':float(q9['volume'].sum()),
                'CAD_closure_rel729':float(q9['volume'].sum()/CAD_VOL-1),
                'min_detJ_27_343_729':[full['minj'],q7['minj'],q9['minj']],
                'mean_Veff':float(q9['volume'].sum()/len(tets)),
                'neighbour_quality':neighbour_quality(nodes,tets,q9['volume']),
                'groups_729':b,
                'max_relative_Veff343_729':float(max(abs(a[k]['Veff']/b[k]['Veff']-1) for k in a)),
                'max_absolute_group_ratio_difference_343_729':float(max(abs(a[k]['Veff']-b[k]['Veff'])/b[k]['Veff'] for k in a))
            }
            print(f"COMPLETE alpha={alpha:.2f}",flush=True)
    reference=result['meshes']['0.20']['groups_729']
    for label,item in result['meshes'].items():
        item['near_ratios_vs_alpha20']={key:float(item['groups_729'][key]['Veff']/value['Veff']) for key,value in reference.items() if key.startswith('near_')}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main(Path(sys.argv[1]))
