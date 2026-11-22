#!/usr/bin/env python3
"""P10FK: classify M2 polar face jumps by corner aspect, orientation and depth."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from p10ed_verify_original_m1_m2_raw_spatial import parse_msh2,rule27,audit_mesh,CENTRE,EDGES
from p10er_three_raw_msh_local_topology_forensics import coordinates,FACES

SHA='ff6500e2da4f4697e1788669e2404d33cdeb9435c1230cf14f5cc7619f1f6a44'


def stats(a):
    return {'count':int(len(a)), 'median':float(np.median(a)),
            'p90':float(np.quantile(a,.9)), 'p95':float(np.quantile(a,.95)),
            'max':float(np.max(a))} if len(a) else {'count':0}


def compute(path):
    m=parse_msh2(path,SHA)
    _,_,a=audit_mesh(m,'P10FB_M2',*rule27())
    vol,cent=a['vol'],a['centroid']
    d,mu,_=coordinates(cent)
    p=m['nodes'][m['tet10'][:,:4]]
    vectors=np.stack([p[:,b]-p[:,a] for a,b in EDGES],axis=1)
    lengths=np.linalg.norm(vectors,axis=2)
    maxedge=np.argmax(lengths,axis=1)
    longest=vectors[np.arange(len(p)),maxedge]
    radial=(cent-CENTRE)
    radial/=np.linalg.norm(radial,axis=1)[:,None]
    radial_alignment=np.abs(np.einsum('ij,ij->i',longest,radial)/
                            np.linalg.norm(longest,axis=1))
    aspect=lengths.max(axis=1)/lengths.min(axis=1)
    cond=np.linalg.cond(p[:,1:4]-p[:,:1])
    # Purely geometric anisotropy: four corner points centered around their centroid.
    eig=np.linalg.eigvalsh(np.einsum('nvi,nvj->nij',p-cent[:,None],p-cent[:,None]))
    pca_ratio=np.sqrt(eig[:,-1]/eig[:,0])
    face_map=defaultdict(list)
    for k,t in enumerate(m['tet10'][:,:4]):
        for f in FACES: face_map[tuple(sorted(int(t[x]) for x in f))].append(k)
    links=np.array([z for z in face_map.values() if len(z)==2],dtype=int)
    i,j=links.T
    ratio=np.exp(abs(np.log(vol[i]/vol[j]))/3)
    polar=(np.maximum(d[i],d[j])<.0005)&(np.minimum(abs(mu[i]),abs(mu[j]))>=.6)
    severe=polar&(ratio>1.25)
    assert len(links)==19541 and severe.sum()==95
    def group(mask):
        ix=np.flatnonzero(mask)
        def pair_max(arr): return np.maximum(arr[i[ix]],arr[j[ix]])
        def pair_mean(arr): return .5*(arr[i[ix]]+arr[j[ix]])
        return {'pairs':len(ix), 'q':stats(ratio[ix]),
                'max_corner_edge_aspect':stats(pair_max(aspect)),
                'max_affine_condition':stats(pair_max(cond)),
                'max_pca_axis_ratio':stats(pair_max(pca_ratio)),
                'mean_longest_edge_radial_alignment':stats(pair_mean(radial_alignment)),
                'pair_max_centroid_distance_mm':stats(1000*np.maximum(d[i[ix]],d[j[ix]])),
                'pair_min_centroid_distance_mm':stats(1000*np.minimum(d[i[ix]],d[j[ix]])),
                'max_edge_aspect_gt3':int(np.count_nonzero(pair_max(aspect)>3)),
                'max_affine_condition_gt10':int(np.count_nonzero(pair_max(cond)>10))}
    result={'m2_sha256':SHA,'selection':'P10FI/P10FJ same 95 severe polar pairs',
       'polar_all':group(polar),'polar_severe':group(severe),
       'polar_nonsevere':group(polar&~severe),
       'north_severe':group(severe&(mu[i]>0)&(mu[j]>0)),
       'south_severe':group(severe&(mu[i]<0)&(mu[j]<0)),
       'inner_0_200um_severe':group(severe&(np.maximum(d[i],d[j])<.0002)),
       'outer_200_500um_severe':group(severe&(np.maximum(d[i],d[j])>=.0002)),
       'warnings':['pair classification based on centroid; QP fixed3D D025 is a different construction',
                   'affine condition depends on node ordering; PCA ratio is permutation invariant',
                   'association with geometric shape is not causality']}
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--m2',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    x=compute(a.m2)
    a.out.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    for name in ('polar_severe','polar_nonsevere','north_severe','south_severe'):
        q=x[name];print(name,q['pairs'],q['max_pca_axis_ratio']['median'],
                        q['mean_longest_edge_radial_alignment']['median'])
