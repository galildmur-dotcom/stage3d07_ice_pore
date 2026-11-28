#!/usr/bin/env python3
"""P10FI: read-only M2 face-neighbour volume jump versus exact smooth P10EY h."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from p10ed_verify_original_m1_m2_raw_spatial import parse_msh2,rule27,audit_mesh
from p10er_three_raw_msh_local_topology_forensics import coordinates,FACES
from p10ey_audit_p10ex_real_math_stop_and_sign_source import field_expr
from p10eu_generate_joint_c1_gmsh_source_only import compile_safe,eval_expr

M2='ff6500e2da4f4697e1788669e2404d33cdeb9435c1230cf14f5cc7619f1f6a44'
ROOT=Path(__file__).resolve().parents[1]


def quant(x):
    return {'n':len(x),'median':float(np.median(x)),'p95':float(np.quantile(x,.95)),
            'max':float(np.max(x))} if len(x) else {'n':0}


def run(msh):
    m=parse_msh2(msh,M2)
    _,_,a=audit_mesh(m,'P10FB_M2',*rule27())
    vol=a['vol']; cent=a['centroid']; d,mu,phi=coordinates(cent)
    geo=(ROOT/'gmsh/P10EY_M2_C1_JOINT_STRCAT_SIGN_SOURCE_ONLY.geo').read_text()
    expr,_=field_expr(geo); code=compile_safe(expr)
    h=np.array([eval_expr(code,p) for p in cent])
    assert np.isfinite(h).all() and np.all(h>0)
    faces=defaultdict(list)
    for i,tet in enumerate(m['tet10'][:,:4]):
        for f in FACES: faces[tuple(sorted(int(tet[j]) for j in f))].append(i)
    links=np.array([ids for ids in faces.values() if len(ids)==2],dtype=np.int64)
    assert len(links)==19541 and all(len(ids)<=2 for ids in faces.values())
    i,j=links.T
    observed=np.exp(abs(np.log(vol[i]/vol[j]))/3)
    expected=np.exp(abs(np.log(h[i]/h[j])))
    radial=np.maximum(d[i],d[j]); mu_pair=np.minimum(abs(mu[i]),abs(mu[j]))
    same_hemi=(mu[i]*mu[j]>0)
    def group(mask):
        pick=np.flatnonzero(mask)
        severe=pick[observed[pick]>1.25]
        return {'all':int(len(pick)),'obs_q':quant(observed[pick]),
                'field_q':quant(expected[pick]),
                'obs_gt_1p25':int(len(severe)),
                'obs_gt_1p25_frac':float(len(severe)/len(pick)) if len(pick) else None,
                'field_q_on_severe':quant(expected[severe]),
                'severe_where_field_lt_1p05':int(np.count_nonzero(expected[severe]<1.05)),
                'severe_where_field_lt_1p10':int(np.count_nonzero(expected[severe]<1.10))}
    result={
        'm2_sha256':M2,
        'smooth_field':'exact P10EY SHA 2aec3e2626b3500388954e428d880c702a4bb820116af93924b8d590bf9b26f1',
        'comparison':'curved27QP effective cell linear size ratio vs MathEval field at pair centroids',
        'all_faces':group(np.ones(len(links),dtype=bool)),
        'polar_near_0_500um':group((radial<.0005)&(mu_pair>=.6)),
        'north_polar_0_500um':group((radial<.0005)&(mu_pair>=.6)&same_hemi&(mu[i]>0)),
        'south_polar_0_500um':group((radial<.0005)&(mu_pair>=.6)&same_hemi&(mu[i]<0)),
        'north_polar_0_100um':group((radial<.0001)&(mu_pair>=.8)&same_hemi&(mu[i]>0)),
        'south_polar_0_100um':group((radial<.0001)&(mu_pair>=.8)&same_hemi&(mu[i]<0)),
        'off_0_500um':group((radial<.0005)&(mu_pair<.6)),
        'note':'Field evaluated at centroids; cannot uniquely attribute residual to Gmsh topology, curvature or finite-size meshing response'}
    polar=(radial<.0005)&(mu_pair>=.6)
    severe=np.flatnonzero(polar&(observed>1.25))
    worst=severe[np.argsort(-observed[severe])[:20]]
    result['top20_polar_pairs']=[{'tet_index0':[int(i[k]),int(j[k])],
                                  'obs_q':float(observed[k]),
                                  'field_q':float(expected[k]),
                                  'd_mm':[float(d[i[k]]*1e3),float(d[j[k]]*1e3)],
                                  'mu':[float(mu[i[k]]),float(mu[j[k]])],
                                  'h_mm':[float(h[i[k]]*1e3),float(h[j[k]]*1e3)]}
                                 for k in worst]
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--m2',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    x=ap.parse_args(); res=run(x.m2)
    x.out.write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    for tag in ('north_polar_0_500um','south_polar_0_500um'):
        d=res[tag]; print(tag,d['obs_gt_1p25'],d['all'],d['field_q_on_severe'])
