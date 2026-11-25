#!/usr/bin/env python3
"""P10KX: M9 source-only spatial priorities from true M7→M8 signed4D drift.

No mesh generation, Gmsh import, solver, marker, or modification of evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        import pandas as pd
        return pd.read_csv(io.BytesIO(z.read('P10DD_SIGNED_R_THETA_PHI_T.csv')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--m7', required=True, type=Path)
    ap.add_argument('--m8', required=True, type=Path)
    ap.add_argument('--source', required=True, type=Path,
                    help='Pinned P10KM 1200-bin support and QP counts')
    ap.add_argument('--coordinates', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    m7, m8 = load(a.m7), load(a.m8)
    key = ['step','region','radial_bin','mu_bin','phi_bin']
    cell = m7.merge(m8, on=key, suffixes=('_7','_8'), validate='one_to_one')
    assert len(cell)==43236 and not cell[key].duplicated().any()
    v = cell[cell.region=='VOLUME'].copy()
    assert len(v)==43200 and v.step.nunique()==36
    v['abs_delta'] = (v.total_per_m_8-v.total_per_m_7).abs()
    g = ['radial_bin','mu_bin','phi_bin']
    every = v.groupby(g).abs_delta.sum().rename('all_l1_per_m')
    late = v[v.step>=31].groupby(g).abs_delta.sum().rename('late_l1_per_m')
    scores = every.to_frame().join(late).reset_index()
    assert len(scores)==1200 and (scores.all_l1_per_m>=0).all() and scores.all_l1_per_m.max()>0
    with a.source.open(encoding='utf-8-sig',newline='') as f:
        old = list(csv.DictReader(f))
    lookup = {(int(r['radial_bin']),int(r['mu_bin']),int(r['phi_bin'])):r for r in old}
    assert len(lookup)==1200
    ea = scores.all_l1_per_m.to_numpy()
    el = scores.late_l1_per_m.to_numpy()
    polar = np.where(scores.mu_bin.isin([0,9]),1.2,1.)
    normalized = (.4*ea/ea.max()+.6*el/el.max())*polar
    assert np.isfinite(normalized).all() and normalized.max()>0
    scores['beta_0.1_score'] = normalized
    scores['polar_soft_priority'] = polar
    scores['M3_QP'] = [int(lookup[tuple(map(int,row))]['M3_QP'])
                       for row in scores[g].itertuples(index=False,name=None)]
    # Import only the established smooth spatial interpolator; no Gmsh.
    import sys
    sys.path.insert(0,str(a.coordinates.parent))
    from p10iu_continuous_m4 import Field, rows
    srcrows = scores.to_dict('records')
    field = Field(rows(a.coordinates),srcrows,'0.1')
    assert abs(float(field.center_kappa.max())-1)<1e-12
    # A C2 full-strength core at both poles is retained; source field remains nonzero elsewhere.
    from p10kp_m8_r2_polar_plateau import kappa_r2, size_ratio
    samples=[]
    for i, key_tuple in enumerate(field.keys):
        point=field.center_points[i]
        d=float(field.dmm[i]);mu=float(field.xyz[i,2])
        final_k=kappa_r2(field.kappa(point),d,mu)
        samples.append((key_tuple,final_k,size_ratio(final_k)**3))
    assert all(0<=k<=1 and .8-1e-12<=vr<=1 for _,k,vr in samples)
    qa={'protocol':'P10KX_M9_REAL_M8_MINUS_M7_SIGNED4D_SOURCE_ONLY',
        'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM',
        'm7_evidence_sha256':sha(a.m7),'m8_evidence_sha256':sha(a.m8),
        'prior_m8_source_sha256':sha(a.source),'coordinate_source_sha256':sha(a.coordinates),
        'aligned_4d_rows':len(cell),'volume_rows':len(v),'bins':len(scores),
        'global_signed_delta_per_m':float((v.total_per_m_8-v.total_per_m_7).sum()),
        'global_cellwise_l1_per_m':float(ea.sum()),
        'late_l1_fraction':float(el.sum()/ea.sum()),
        'priority_formula':'(0.4*all_L1/max_all + 0.6*last6_L1/max_last6)*polar_factor',
        'polar_factor':'1.2 for mu_bin 0 and 9; 1.0 elsewhere',
        'interpolator':'pinned positive compact Wendland C2, quintic smoothstep; no angular singularity',
        'polar_core':'kappa_base + (1-kappa_base)*C2_polar_plateau, |mu|>=0.8, d<=0.5mm',
        'incremental_nominal_volume_ratio':'1-0.20*kappa, in [0.80,1.00]',
        'center_kappa_min_max':[float(min(k for _,k,_ in samples)),float(max(k for _,k,_ in samples))],
        'center_nominal_volume_ratio_min_max':[float(min(vr for _,_,vr in samples)),float(max(vr for _,_,vr in samples))],
        'top10_source_bins':[list(map(int,row)) for row in scores.iloc[np.argsort(-normalized)[:10]][g].itertuples(index=False,name=None)],
        'mesh_attempts':0,'FEM_attempts':0,
        'limitations':['Nominal size law is not actual curved Tet10 Veff reduction',
                       'No M9 mesh; D029/D031 gate pending',
                       'Do not infer converged spatial gradient from M6/M7/M8']}
    a.out.mkdir(parents=True,exist_ok=False)
    csvpath=a.out/'P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv'
    scores.to_csv(csvpath,index=False,float_format='%.17g')
    qa['source_csv_sha256']=sha(csvpath)
    (a.out/'P10KX_M9_SOURCE_ONLY_QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(qa,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
