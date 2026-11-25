#!/usr/bin/env python3
"""Read-only P10LE mechanistic descriptive audit of accepted M7/M8/M9 signed4D.

Separates genuine signed component changes from their cellwise absolute norms;
no PDE, mesh, Gmsh, model or one-shot writes.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from p10kw_m8_m7_signed4d_audit import read_zip, FIELDS, KEY


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def joined(a,b):
    x=a.merge(b,on=KEY,suffixes=('_old','_new'),validate='one_to_one')
    assert len(x)==43236
    for col in ('time_start_s','time_end_s','r_lower_mm','r_upper_mm',
                'theta_lower_rad','theta_upper_rad','phi_lower_rad','phi_upper_rad'):
        assert np.allclose(x[col+'_old'],x[col+'_new'],equal_nan=True)
    for f in [*FIELDS,'total_per_m']:
        x['delta_'+f]=x[f+'_new']-x[f+'_old']
    x['l1_cell']=x.delta_total_per_m.abs()
    return x[x.region=='VOLUME'].copy()


def select(x,radial=None,mu=None,late=False):
    if radial is not None:x=x[x.radial_bin.isin(radial)]
    if mu is not None:x=x[x.mu_bin.isin(mu)]
    if late:x=x[x.step>=31]
    return x


def describe(x):
    signed=float(x.delta_total_per_m.sum())
    l1=float(x.l1_cell.sum())
    components={f:float(x['delta_'+f].sum()) for f in FIELDS}
    assert abs(sum(components.values())-signed)<1e-9
    return {'cells':int(len(x)),'signed_delta_per_m':signed,
            'absolute_cellwise_l1_per_m':l1,
            'cell_cancellation_factor':float(l1/abs(signed)) if signed else None,
            'components_signed_delta_per_m':components,
            'sum_abs_components_aggregated_per_m':float(sum(abs(v) for v in components.values()))}


def main():
    ap=argparse.ArgumentParser()
    for name in ('m7','m8','m9','source','out'):ap.add_argument('--'+name,required=True,type=Path)
    a=ap.parse_args()
    datasets=[read_zip(p)[0] for p in (a.m7,a.m8,a.m9)]
    old=joined(datasets[0],datasets[1]);new=joined(datasets[1],datasets[2])
    zones={'all':{},'first_20um':{'radial':[0]},
           'wall_0_50um':{'radial':[0,1]},
           'wall_0_100um':{'radial':[0,1,2]},
           'outside_20um':{'radial':list(range(1,10))},
           'north_extreme':{'mu':[9]},'south_extreme':{'mu':[0]},
           'nonpolar':{'mu':list(range(1,9))},
           'wall20_north':{'radial':[0],'mu':[9]},
           'wall20_south':{'radial':[0],'mu':[0]},
           'wall20_nonpolar':{'radial':[0],'mu':list(range(1,9))},
           'late_31_36':{'late':True},
           'late_wall20':{'radial':[0],'late':True},
           'late_wall20_north':{'radial':[0],'mu':[9],'late':True},
           'late_wall20_south':{'radial':[0],'mu':[0],'late':True}}
    results={name:{'M7_to_M8':describe(select(old,**opts)),
                   'M8_to_M9':describe(select(new,**opts))} for name,opts in zones.items()}
    # Full M9-M8 4D cells most responsible for unsigned mismatch: exact keys.
    ranking=new.nlargest(15,'l1_cell')
    top=[]
    for _,r in ranking.iterrows():
        top.append({'step':int(r.step),'radial_bin':int(r.radial_bin),
                    'mu_bin':int(r.mu_bin),'phi_bin':int(r.phi_bin),
                    'time_end_s':float(r.time_end_s_new),
                    'r_lower_mm':float(r.r_lower_mm_new),
                    'r_upper_mm':float(r.r_upper_mm_new),
                    'signed_delta_per_m':float(r.delta_total_per_m),
                    'M8_mechanical_qp':int(r.mechanical_qp_old),
                    'M9_mechanical_qp':int(r.mechanical_qp_new),
                    'components':{f:float(r['delta_'+f]) for f in FIELDS}})
    # Is the M9 SOURCE-ONLY priority predictive of the *observed* M8->M9 change?
    source=pd.read_csv(a.source)
    key=['radial_bin','mu_bin','phi_bin']
    spatial=new.groupby(key,as_index=False).agg(observed_l1=('l1_cell','sum'),
                  signed=('delta_total_per_m','sum'))
    fit=source[key+['beta_0.1_score']].merge(spatial,on=key,validate='one_to_one')
    assert len(fit)==1200
    score=fit['beta_0.1_score'].to_numpy();effect=fit.observed_l1.to_numpy()
    pearson=float(np.corrcoef(score,effect)[0,1])
    spearman=float(pd.Series(score).corr(pd.Series(effect),method='spearman'))
    top10=np.argsort(-score)[:120]
    share=float(effect[top10].sum()/effect.sum())
    observed_top10=set(np.argsort(-effect)[:120]);source_top10=set(top10)
    checks={
        'P10KX_source_score_vs_observed_M9_M8_bin_l1_pearson':pearson,
        'P10KX_source_score_vs_observed_M9_M8_bin_l1_spearman':spearman,
        'observed_M9_M8_l1_in_top10percent_source_bins':share,
        'top10percent_source_vs_observed_bin_overlap_count':len(source_top10 & observed_top10),
        'top10percent_count':120,
        'observed_l1_in_first_20um_fraction':float(results['first_20um']['M8_to_M9']['absolute_cellwise_l1_per_m']/results['all']['M8_to_M9']['absolute_cellwise_l1_per_m']),
        'observed_l1_in_late_31_36_fraction':float(results['late_31_36']['M8_to_M9']['absolute_cellwise_l1_per_m']/results['all']['M8_to_M9']['absolute_cellwise_l1_per_m']),
    }
    out={'protocol':'P10LE_M7_M8_M9_COMPONENT_POLAR_WALL_LATE_TIME_READONLY',
         'status':'PASS_DESCRIPTIVE_DIAGNOSIS_NO_FEM_NO_MESH',
         'inputs_sha256':{name:sha(p) for name,p in [('M7',a.m7),('M8',a.m8),('M9',a.m9),('P10KX_source',a.source)]},
         'full4d_physical_cells_each_pair':int(len(new)),
         'zones':results,'top15_observed_cells_M9_minus_M8':top,
         'P10KX_priority_predictivity':checks,
         'limitations':['Descriptive difference of binned FE gradients is not a local PDE error estimator',
                        'Cannot identify a numerical root cause from signed 4D coefficients alone',
                        'No change of physics, mesh, marker or solver; no new FEM'],
         'mesh_generation_attempts':0,'FEM_attempts':0}
    assert not a.out.exists()
    a.out.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({'status':out['status'],'predictivity':checks,
                      'selected':{k:v['M8_to_M9'] for k,v in results.items()
                                  if k in ('first_20um','wall20_north','wall20_south','late_wall20')}},indent=2))

if __name__=='__main__':main()
