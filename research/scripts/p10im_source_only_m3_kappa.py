#!/usr/bin/env python3
"""P10IM source-only M3 κ hypotheses from real M1→M2 signed 4D spatial data.

This is neither an error estimator nor a Gmsh size field until CAD continuation.
"""
import argparse
import csv
import json
from pathlib import Path
import math

import numpy as np

PARTS=['mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
       'thermal_mass_per_m','thermal_diffusion_per_m']
BETAS=(0.,.1,.25,.5)


def load(path):
    with path.open(newline='',encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def dorfler(weights,theta=.5):
    order=np.argsort(-weights)
    cutoff=np.searchsorted(np.cumsum(weights[order]),theta*weights.sum(),side='left')+1
    return set(map(int,order[:cutoff]))


def smooth(xyz,u,raw):
    """Same compact C2 Wendland coordinate scales as P10HA; bin-center sample."""
    result=np.zeros(len(raw))
    for i in range(len(raw)):
        dis=np.sqrt(((u-u[i])/.75)**2+((xyz-xyz[i])**2).sum(axis=1)/(.60**2))
        active=dis<1.
        q=dis[active]
        weights=(1-q)**4*(4*q+1)
        result[i]=(weights@raw[active])/weights.sum()
    maxv=result.max()
    return result/maxv if maxv>0 else result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--p10il',type=Path,required=True)
    ap.add_argument('--p10ha',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    current=load(args.p10il)
    previous=load(args.p10ha)
    assert len(current)==len(previous)==1200
    index=lambda r:tuple(int(r[k]) for k in ('radial_bin','mu_bin','phi_bin'))
    old={index(r):r for r in previous}
    assert len(old)==1200
    previous=[old[index(r)] for r in current]
    delta=np.asarray([[float(r['M2_minus_M1_'+p]) for p in PARTS]
                      for r in current])
    need_support=np.asarray([int(r['M1_mechanical_QP'])>0 and
                             int(r['M2_mechanical_QP'])>0 for r in current])
    amps=np.abs(delta)
    den=amps.sum(axis=0)
    assert np.all(den>0)
    normalized=amps/den
    mech=normalized[:,:3].mean(axis=1)
    thermal=normalized[:,3:].mean(axis=1)
    theta=np.array([float(r['theta_mid_rad']) for r in previous])
    phi=np.array([float(r['phi_mid_rad']) for r in previous])
    xyz=np.column_stack([np.sin(theta)*np.cos(phi),np.sin(theta)*np.sin(phi),np.cos(theta)])
    centers=[]
    for r in previous:
        lower=float(r['d_lower_mm']);high=r['d_upper_mm']
        centers.append(.5*(lower+float(high)) if high else lower)
    u=np.log1p(np.array(centers)/.05)
    old_kappa=np.array([float(r['kappa25_primary_for_M2_source_only']) for r in previous])
    supported=np.array([int(r['radial_bin'])<=4 and int(r['mu_bin']) in (0,9)
                        for r in current])
    summary={'protocol':'P10IM_R1_SOURCE_ONLY_KAPPA_HYPOTHESES',
             'no_FEM_no_Gmsh':True,'n_bins':len(current),
             'unsupported_mechanical_QP_bins':[index(r) for r,s in zip(current,need_support) if not s],
             'weights':'(1-beta)*mean(normalized absolute 3 mechanical Δ)+beta*mean(normalized absolute 2 thermal Δ)',
             'time_uncertainty':'M1 dt36-to25 diagnostic only; M2 dt36 unknown; no temporal robustness weight imposed',
             'smoothing':'P10HA-style compact Wendland C2 on log radial + sphere Cartesian angular coordinates',
             'beta':{}}
    outputs=[]
    for beta in BETAS:
        name='beta_'+str(beta).replace('.','p')
        score=(1-beta)*mech+beta*thermal
        score=np.where(need_support,score,0.)
        smoothed=smooth(xyz,u,score)
        selected=dorfler(score)
        old_selection=dorfler(np.array([float(r['mechanical_robust_score25']) for r in previous]))
        overlap=len(selected&old_selection)/len(selected|old_selection)
        summary['beta'][str(beta)]={
            'selected_theta0p5':len(selected),
            'selected_in_supported_polar':int(sum(supported[list(selected)])),
            'polar_score_fraction':float(score[supported].sum()/score.sum()),
            'old_P10HA_mechanical_dorfler_jaccard':overlap,
            'smooth_kappa_max':float(smoothed.max()),
            'smooth_kappa_mean':float(smoothed.mean()),
            'smooth_kappa_MAE_vs_old':float(np.abs(smoothed-old_kappa).mean()),
            'smooth_top_10_bins':[index(current[i]) for i in np.argsort(-smoothed)[:10]]}
        for i,r in enumerate(current):
            if len(outputs)<=i:outputs.append({**{k:r[k] for k in ('radial_bin','mu_bin','phi_bin')},
                                                'source_kappa_M0_M1':old_kappa[i],
                                                'M1_QP':r['M1_mechanical_QP'],
                                                'M2_QP':r['M2_mechanical_QP'],
                                                'M1_dt36_to25_temporal_proxy':r['M1_dt36_to25_abs_total_per_m'],
                                                'M2_minus_M1_abs_total':abs(float(r['M2_minus_M1_total_per_m'])),
                                                'mech_source_score':mech[i],
                                                'thermal_source_score':thermal[i]})
            outputs[i][name+'_score']=score[i]
            outputs[i][name+'_kappa_smoothed']=smoothed[i]
            outputs[i][name+'_dorfler_selected']=int(i in selected)
    summary['warning']='No M3 volume ratios: 25-50% target requires future actual mesh and independent CAD region audit.'
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'P10IM_QA.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    with (args.out/'P10IM_M3_KAPPA_HYPOTHESES_1200_BINS.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(outputs[0]));writer.writeheader();writer.writerows(outputs)
    print(json.dumps(summary,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
