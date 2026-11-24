#!/usr/bin/env python3
"""P10HZ: at identical spherical points, compare C0 local wall-size proxies."""
import hashlib
import io
import json
import math
import sys
import zipfile
from pathlib import Path
import numpy as np

import p10hy_surface_smoothness_audit as wall
import p10hv_independent_scan as meshqa

C=np.array([0.,0.,.03])
R=.001

def surface(raw,mode='median'):
    nodes,tets,counts=meshqa.read_msh(raw)
    faces=wall.read_faces(raw)
    corners=np.unique(faces[:,:3])
    edges=set()
    incid={int(node):[] for node in corners}
    for f in faces:
        for i,j in ((0,1),(1,2),(2,0)):
            a,b=map(int, (f[i],f[j]))
            edge=tuple(sorted((a,b)))
            if edge in edges:continue
            edges.add(edge)
            pa,pb=nodes[a]-C,nodes[b]-C
            length=R*np.arccos(np.clip(np.dot(pa,pb)/R**2,-1,1))*1000
            incid[a].append(length);incid[b].append(length)
    assert all(len(v)>=3 for v in incid.values())
    h_node=np.zeros(len(nodes))
    for node,vals in incid.items():
        h_node[node]=(np.median(vals) if mode=='median' else np.mean(vals))
    idx=faces[:,:3].astype(int)
    vertices=(nodes[idx]-C)/R
    areas=np.cross(vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0])
    return {'nodes':nodes,'faces':idx,'vertices':vertices,'h_node':h_node,
            'normals':areas,'wall_corners':len(corners),'edge_count':len(edges)}

def evaluate(s,dirs,block=256):
    """Spherical ray intersects one of the straight corner-face planes."""
    v=s['vertices']; a=v[:,0];b=v[:,1];c=v[:,2]
    v0=b-a;v1=c-a
    d00=(v0*v0).sum(axis=1);d01=(v0*v1).sum(axis=1)
    d11=(v1*v1).sum(axis=1)
    denom=d00*d11-d01*d01
    n=s['normals'];na=(n*a).sum(axis=1)
    out=[];ambiguous=0;uncovered=0;maxneg=0.
    for begin in range(0,len(dirs),block):
        q=dirs[begin:begin+block]
        tden=q@n.T
        t=np.divide(na[None,:],tden,out=np.full_like(tden,np.nan),where=abs(tden)>1e-14)
        x=q[:,None,:]*t[:,:,None]
        v2=x-a[None,:,:]
        d20=np.einsum('qfi,fi->qf',v2,v0)
        d21=np.einsum('qfi,fi->qf',v2,v1)
        beta=(d11[None,:]*d20-d01[None,:]*d21)/denom[None,:]
        gamma=(d00[None,:]*d21-d01[None,:]*d20)/denom[None,:]
        lam=1-beta-gamma
        bary=np.stack([lam,beta,gamma],axis=2)
        margin=np.min(np.where(np.isfinite(bary),bary,-np.inf),axis=2)
        positive=(t>0)&np.isfinite(margin)
        allowed=positive&(margin>=-1e-9)
        ncover=allowed.sum(axis=1)
        uncovered+=int((ncover==0).sum())
        ambiguous+=int((ncover>1).sum())
        if np.any(ncover==0):
            raise ValueError(f"Uncovered physical spherical probe: {uncovered}; min margins {np.nanmax(margin[ncover==0],axis=1)}")
        chosen=np.argmax(allowed,axis=1)
        h=s['h_node'][s['faces'][chosen]]
        bar=bary[np.arange(len(q)),chosen]
        out.extend(np.einsum('ij,ij->i',bar,h))
    return np.asarray(out), {'uncovered':uncovered,'multiple_face_hits':ambiguous}

def directions_from_M1(s):
    # Original M1 corner-edge midpoints, mapped exactly onto CAD sphere.
    edge=set()
    for f in s['faces']:
        for i,j in ((0,1),(1,2),(2,0)):
            edge.add(tuple(sorted((int(f[i]),int(f[j])))))
    e=np.array(sorted(edge),int)
    v=s['nodes'][e].mean(axis=1)-C
    return v/np.linalg.norm(v,axis=1)[:,None]

def fixed_sphere_directions():
    # Pole-biased but deterministic independent sample, no new mesh.
    mu=np.concatenate([np.linspace(-.995,-.60,25),np.linspace(-.59,.59,31),
                       np.linspace(.60,.995,25),[-1.,1.]])
    out=[]
    for m in mu:
        for phi in np.linspace(-np.pi,np.pi,96,endpoint=False):
            out.append([np.sqrt(max(0,1-m*m))*np.cos(phi),
                        np.sqrt(max(0,1-m*m))*np.sin(phi),m])
    return np.array(out)

def summarize(x):
    if not len(x):return {'n':0}
    return {'n':int(len(x)),'median':float(np.median(x)),
            'p05':float(np.percentile(x,5)), 'p95':float(np.percentile(x,95)),
            'min':float(np.min(x)), 'max':float(np.max(x))}

def compare(s,dirs,base,ka):
    hh,g=evaluate(s,dirs)
    ratio=hh/base
    mu=dirs[:,2]
    zones={'all':np.ones(len(mu),bool),'north_polar':mu>=.8,
           'south_polar':mu<=-.8,'north_taper':(mu>=.6)&(mu<.8),
           'south_taper':(mu<=-.6)&(mu>-.8),
           'off_polar':abs(mu)<=.6,
           'kappa_ge_0p8':ka>=.8, 'kappa_ge_0p6':ka>=.6,
           'kappa_lt_0p2':ka<.2}
    return {'coverage':g,'zones':{k:{'h_ratio':summarize(ratio[sel]),
                                  'nominal_volume_proxy_ratio_median':float(np.median(ratio[sel])**3),
                                  'fraction_h_refined':float(np.mean(ratio[sel]<1.))}
                            for k,sel in zones.items() if np.any(sel)}}

def main(pathcsv,pathm1,pathzip,mode='median'):
    source,values=wall.source(pathcsv)
    original=pathm1.read_bytes()
    assert hashlib.sha256(original).hexdigest()=='47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'
    models={'M1':surface(original,mode)}
    with zipfile.ZipFile(pathzip) as z:
        assert z.testzip() is None
        for case in json.loads(z.read('P10HV_WORKER_RESULT.json'))['results']:
            raw=z.read(case['mesh_filename'])
            assert hashlib.sha256(raw).hexdigest()==case['mesh_sha256']
            models[f"alpha_{case['alpha']:.2f}"]=surface(raw,mode)
    probes={'M1_wall_edge_midpoints':directions_from_M1(models['M1']),
            'fixed_spherical_grid':fixed_sphere_directions()}
    result={'method':f'M1-anchored identical physical sphere rays; C0 barycentric interpolation of {mode} incident corner-edge length',
            'probes':{},'mesh_corner_counts':{k:v['wall_corners'] for k,v in models.items()}}
    for pname,dirs in probes.items():
        pts=C+R*dirs
        kap=wall.eval_kappa(source,values,pts)
        baseline,cov=evaluate(models['M1'],dirs)
        item={'sample_count':len(dirs),'kappa':summarize(kap),'M1_coverage':cov}
        for name,s in models.items():
            if name=='M1':continue
            item[name]=compare(s,dirs,baseline,kap)
        result['probes'][pname]=item
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':
    main(*map(Path,sys.argv[1:4]),mode=sys.argv[4] if len(sys.argv)>4 else 'median')
