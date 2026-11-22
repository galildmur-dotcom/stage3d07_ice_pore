#!/usr/bin/env python3
"""P10FJ: isolate straight-corner vs curved27QP contribution for the same P10FI pairs."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from p10ed_verify_original_m1_m2_raw_spatial import parse_msh2,rule27,audit_mesh,CENTRE,EDGES
from p10er_three_raw_msh_local_topology_forensics import coordinates,FACES

M2_SHA='ff6500e2da4f4697e1788669e2404d33cdeb9435c1230cf14f5cc7619f1f6a44'


def summary(x):
    return {'count':int(len(x)), 'median':float(np.median(x)),
            'p95':float(np.quantile(x,.95)), 'max':float(np.max(x))} if len(x) else {'count':0}


def main(msh:Path):
    mesh=parse_msh2(msh,M2_SHA)
    _,_,audit=audit_mesh(mesh,'P10FB_M2',*rule27())
    curved_vol=audit['vol']; cent=audit['centroid']
    p=mesh['nodes'][mesh['tet10'][:,:4]]
    det=np.linalg.det(p[:,1:4]-p[:,:1]); corner_vol=det/6
    assert np.all(corner_vol>0) and len(corner_vol)==10094
    correction=curved_vol/corner_vol
    d,mu,_=coordinates(cent)
    edge=np.stack([np.linalg.norm(p[:,a]-p[:,b],axis=1) for a,b in EDGES],axis=1)
    edge_aspect=np.max(edge,axis=1)/np.min(edge,axis=1)
    # Scale-invariant condition number of the affine corner Jacobian.
    affine=p[:,1:4]-p[:,:1]
    cond=np.linalg.cond(affine)
    faces=defaultdict(list)
    for i,t in enumerate(mesh['tet10'][:,:4]):
        for f in FACES:
            faces[tuple(sorted(int(t[a]) for a in f))].append(i)
    pairs=np.asarray([z for z in faces.values() if len(z)==2],dtype=np.int64)
    assert len(pairs)==19541
    i,j=pairs.T
    qc=np.exp(np.abs(np.log(curved_vol[i]/curved_vol[j]))/3)
    qs=np.exp(np.abs(np.log(corner_vol[i]/corner_vol[j]))/3)
    radial=np.maximum(d[i],d[j]); abs_mu=np.minimum(np.abs(mu[i]),np.abs(mu[j]))
    polar=(radial<.0005)&(abs_mu>=.6)
    severe=polar&(qc>1.25)
    assert int(severe.sum())==95
    pair_curvature_ratio=np.exp(np.abs(np.log(correction[i]/correction[j]))/3)
    delta=np.abs(np.log(qc/qs))
    def select(mask):
        ix=np.flatnonzero(mask)
        return {'pairs':int(len(ix)), 'q_curved':summary(qc[ix]),
                'q_corner':summary(qs[ix]),
                'curvature_correction_ratio':summary(pair_curvature_ratio[ix]),
                'abs_log_qcurved_over_qcorner':summary(delta[ix]),
                'corner_q_gt_1p25':int(np.count_nonzero(qs[ix]>1.25)),
                'curvature_q_change_gt_1pct':int(np.count_nonzero(abs(qc[ix]/qs[ix]-1)>.01)),
                'corner_edge_aspect_max_element':summary(np.maximum(edge_aspect[i[ix]],edge_aspect[j[ix]])),
                'corner_affine_condition_max_element':summary(np.maximum(cond[i[ix]],cond[j[ix]]))}
    result={'status':'READ_ONLY_P10FJ_NO_GMSH_NO_FEM', 'm2_sha256':M2_SHA,
            'full_internal_pairs':select(np.ones(len(qc),dtype=bool)),
            'polar_0_500um':select(polar),
            'severe_curved_q_gt_1p25':select(severe),
            'north_severe':select(severe&(mu[i]>0)&(mu[j]>0)),
            'south_severe':select(severe&(mu[i]<0)&(mu[j]<0)),
            'curved_corner_cell_correction_all':summary(correction),
            'selection':'same P10FI 95 pairs by curved27QP q>1.25, radial<.5mm and minabs(mu)>=.6',
            'limitations':'corner/curved parity measures geometry curvature, not direct Gmsh topology causality'}
    ix=np.flatnonzero(severe)
    rank=ix[np.argsort(-qc[ix])[:20]]
    result['top20_severe']=[{'tet0':[int(i[k]),int(j[k])],
         'q_curved':float(qc[k]),'q_corner':float(qs[k]),
         'q_curved_over_corner':float(qc[k]/qs[k]),
         'centroid_d_mm':[float(d[i[k]]*1000),float(d[j[k]]*1000)],
         'centroid_mu':[float(mu[i[k]]),float(mu[j[k]])],
         'edge_aspect':[float(edge_aspect[i[k]]),float(edge_aspect[j[k]])],
         'affine_condition':[float(cond[i[k]]),float(cond[j[k]])]}
        for k in rank]
    return result


if __name__=='__main__':
    arg=argparse.ArgumentParser()
    arg.add_argument('--m2',type=Path,required=True)
    arg.add_argument('--out',type=Path,required=True)
    a=arg.parse_args()
    x=main(a.m2)
    a.out.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    for k in ('severe_curved_q_gt_1p25','north_severe','south_severe'):
        r=x[k]; print(k,r['pairs'],r['corner_q_gt_1p25'],r['curvature_correction_ratio']['p95'])
