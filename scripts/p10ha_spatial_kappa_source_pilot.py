#!/usr/bin/env python3
"""P10HA: read-only, component-aware 4D -> spatial kappa source pilot.

No Gmsh, FEM, geometric remeshing, or equivalence to a DWR estimator.
Input is the immutable 12-run P10GY ZIP and the two dt150 baseline ZIPs
already pinned by p10gz_independent_seven_dt_signed_4d.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p10gz_independent_seven_dt_signed_4d as p10gz

COMPONENTS = p10gz.FIELDS
THETAS = (0.35, 0.5, 0.65)  # diagnostic Dörfler thresholds, not approved gates


def read_pair(outer_path: Path, dt: int):
    raw = outer_path.read_bytes()
    p10gz.check(p10gz.sha(raw) == p10gz.OUTER_SHA, 'P10GY SHA')
    grids = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        p10gz.check(outer.testzip() is None, 'outer CRC')
        for m in ('M0', 'M1'):
            name = f'P10GY_{m}_DT{dt}_EVIDENCE.zip'
            hits = [x for x in outer.namelist() if x.endswith(name)]
            p10gz.check(len(hits) == 1, 'unique pinned ZIP '+name)
            grids[m] = p10gz.parse_one(outer.read(hits[0]), m, dt, True)
    p10gz.check(grids['M0']['bounds'] == grids['M1']['bounds'], 'shared physical bins')
    return grids


def geometry(bounds):
    # Physical shells are d from pore wall, NOT a Cartesian volume mesh.
    # Open outer shell is represented by its 15 mm lower limit only for QA;
    # no fictitious finite geometric centroid is declared.
    center = np.empty((1200, 4), float)
    meta = []
    for i in range(1200):
        lo, hi, tl, tu, pl, pu = bounds[i]
        d0 = float(lo)
        d1 = float(hi) if hi else None
        # transform keeps near-wall 0.02 mm shell resolved and outer bin finite
        d_rep = (d0+d1)/2 if d1 is not None else d0
        theta = (float(tl)+float(tu))/2
        phi = (float(pl)+float(pu))/2
        center[i] = [np.log1p(d_rep/0.05),
                     np.sin(theta)*np.cos(phi),
                     np.sin(theta)*np.sin(phi), np.cos(theta)]
        ir,rem = divmod(i,120)
        im,ip = divmod(rem,12)
        meta.append((ir,im,ip,d0,d1,theta,phi,d1 is None))
    return center, meta


def smooth(values, xyz, radial_band=0.75, angular_band=0.60):
    # Compact support Wendland C2, W(q)=(1-q)^4(4q+1), q<1.
    # Using x,y,z direction cosines removes azimuth seam artifacts.
    scaled = xyz.copy()
    scaled[:,0] /= radial_band
    scaled[:,1:] /= angular_band
    kdt = cKDTree(scaled)
    neighbors = kdt.query_ball_point(scaled, r=1.0)
    out = np.zeros(len(values),float)
    for i,ids in enumerate(neighbors):
        z = scaled[ids]-scaled[i]
        q = np.linalg.norm(z,axis=1)
        w = np.maximum(1-q,0)**4*(4*q+1)
        out[i] = float(np.dot(w,values[ids])/w.sum())
    return out, [len(x) for x in neighbors]


def dorfler(weights, theta):
    w = np.maximum(np.asarray(weights,float),0)
    order=np.argsort(-w,kind='stable')
    target=theta*float(w.sum())
    count=int(np.searchsorted(np.cumsum(w[order]),target,side='left')+1)
    selected=np.zeros(len(w),bool)
    selected[order[:count]]=True
    return selected


def main(args):
    p25=read_pair(args.input,25)
    p36=read_pair(args.input,36)
    p10gz.check(p25['M0']['bounds']==p36['M0']['bounds'],'same geometry across dt')
    xyz,meta=geometry(p25['M0']['bounds'])
    difference={}
    for dt,p in ((25,p25),(36,p36)):
        difference[dt]=p['M1']['vals'].sum(axis=0)-p['M0']['vals'].sum(axis=0)
        p10gz.check(np.isfinite(difference[dt]).all(),'finite components')
    # 6 physical signed components normalized by each component's spatial
    # global L1: no single large signed equilibrium/history may cancel another.
    # This is *difference sensitivity*, NOT an error estimator.
    raw_norms=np.abs(difference[25][:,:6]).sum(axis=0)
    active=raw_norms > 1e-12*max(float(raw_norms.max()),1e-15)
    p10gz.check(active[:3].all(),'all three mechanical components active')
    norms=np.maximum(raw_norms,1e-15)
    score={dt:(np.abs(difference[dt][:,:6][:,active])/norms[active]).mean(axis=1)
           for dt in (25,36)}
    # Independent component-wise temporal noise: distinguish fragile bins.
    temporal=np.abs(difference[36][:,:6]-difference[25][:,:6])
    meaningful=np.abs(difference[25][:,:6][:,active])>5*temporal[:,active]
    reliability=meaningful.mean(axis=1)
    robust={dt:score[dt]*(0.5+0.5*reliability) for dt in (25,36)}
    smooth25,nneigh=smooth(robust[25],xyz)
    smooth36,_=smooth(robust[36],xyz)
    # κ must stay [0,1], with max attained in the most marked region.
    den=max(float(smooth25.max()),float(smooth36.max()),1e-20)
    k25=np.clip(smooth25/den,0,1)
    k36=np.clip(smooth36/den,0,1)
    p10gz.check(np.isfinite(k25).all() and np.isfinite(k36).all() and
                k25.min()>=0 and k25.max()<=1 and k36.min()>=0 and k36.max()<=1,
                'kappa finite and bounded')
    support25={m:p25[m]['support'][:,:,0].sum(axis=0) for m in ('M0','M1')}
    support36={m:p36[m]['support'][:,:,0].sum(axis=0) for m in ('M0','M1')}
    missing_support=np.logical_or.reduce([support25[m]==0 for m in ('M0','M1')]+
                                         [support36[m]==0 for m in ('M0','M1')])
    mech25=np.abs(difference[25][:,:3])/norms[:3]
    mech36=np.abs(difference[36][:,:3])/norms[:3]
    mech_noise=np.abs(difference[36][:,:3]-difference[25][:,:3])
    mech_reliability=(np.abs(difference[25][:,:3])>5*mech_noise).mean(axis=1)
    mech_robust25=mech25.mean(axis=1)*(0.5+0.5*mech_reliability)
    mech_robust36=mech36.mean(axis=1)*(0.5+0.5*mech_reliability)
    ms25,_=smooth(mech_robust25,xyz)
    ms36,_=smooth(mech_robust36,xyz)
    mden=max(float(ms25.max()),float(ms36.max()),1e-20)
    mk25=np.clip(ms25/mden,0,1)
    mk36=np.clip(ms36/mden,0,1)
    mech_sel25=dorfler(mech_robust25,0.5)
    full_sel25=dorfler(robust[25],0.5)
    mech_delta=difference[25][:,:3].sum(axis=1)
    therm_delta=difference[25][:,3:6].sum(axis=1)
    thermal_exceeds_mech=np.abs(therm_delta)>np.abs(mech_delta)
    thermal_to_mech_ratio=float(np.abs(therm_delta).sum()/np.abs(mech_delta).sum())
    cap=np.isin(np.arange(1200)//12%10,[0,9])
    wall=np.arange(1200)//120<=2
    selected={str(th):dorfler(robust[25],th) for th in THETAS}
    diagnostics={
        'protocol':'P10HA_R1_SOURCE_ONLY_SIGNED_COMPONENT_SPATIAL_KAPPA_PILOT',
        'source_zip_sha256':p10gz.OUTER_SHA,
        'status':'READ_ONLY_KAPPA_PILOT_ONLY_NOT_GMSH_FEM_OR_DWR',
        'P10HB_primary_adaptation_policy':'MECHANICAL_ONLY for current R EDV_VAR xi=0 B6 900s M0/M1 source pilot; thermal retained for QA and future re-assessment, NOT a universal PDE decoupling',
        'primary_kappa_column':'kappa25_mechanical_only',
        'thermal_total_intermesh_L1_over_mechanical_total':thermal_to_mech_ratio,
        'bins_thermal_signed_total_exceeds_mechanical_signed_total':int(thermal_exceeds_mech.sum()),
        'mechanical_signal_L1_share_in_those_bins':float(np.abs(mech_delta[thermal_exceeds_mech]).sum()/np.abs(mech_delta).sum()),
        'time_steps_compared_s':[36,25],
        'spatial_bins':1200,
        'components':list(COMPONENTS),
        'component_L1_normalization_m_inv':dict(zip(COMPONENTS,map(float,raw_norms))),
        'active_components':[x for x,a in zip(COMPONENTS,active) if a],
        'excluded_exact_or_nearly_zero_components':[x for x,a in zip(COMPONENTS,active) if not a],
        'score':'mean of active absolute intermesh component differences / each active component L1; components normalized to avoid mechanical sign cancellations',
        'time_robustness':'active component flags |deltaG25| > 5*|deltaG36-deltaG25|; robust score=score*(0.5+0.5*stable_fraction)',
        'time_bin_caveat':'retains full native signed 4D source; spatial score uses only exact sums of contributions over 900s; no assertion of 25s time-slice convergence',
        'smoothing':'normalized radial u=log(1+d_mm/0.05); direction cosines; C2 Wendland with radial band=.75, angular band=.60',
        'outer_shell':'[15mm,infinity) remains open; plotting representative placed at d=15mm boundary only, not physical centroid',
        'differentiability_caveat':'normalized RBF of cell-centre values is C2 in transformed coordinates; the exported bin lookup and physical placement are not themselves a continuous CAD-to-Gmsh field',
        'kappa_min_max_dt25':[float(k25.min()),float(k25.max())],
        'kappa_min_max_dt36':[float(k36.min()),float(k36.max())],
        'mechanical_only_kappa_min_max_dt25':[float(mk25.min()),float(mk25.max())],
        'mechanical_only_25_36_shared_smoothing_denominator':float(mden),
        'mechanical_only_mean_abs_kappa_dt36_dt25':float(np.mean(np.abs(mk36-mk25))),
        'mechanical_only_max_abs_kappa_dt36_dt25':float(np.max(np.abs(mk36-mk25))),
        'equal_normalized_all_active_vs_mechanical_only_mean_abs_kappa':float(np.mean(np.abs(k25-mk25))),
        'mean_abs_kappa_dt36_dt25':float(np.mean(np.abs(k36-k25))),
        'maximum_abs_kappa_dt36_dt25':float(np.max(np.abs(k36-k25))),
        'neighbor_count_min_median_max':[int(min(nneigh)),float(np.median(nneigh)),int(max(nneigh))],
        'time_component_stable_flags_percent':float(100*meaningful.mean()),
        'bins_without_mechanical_QP_support_in_any_mesh_dt':int(missing_support.sum()),
        'missing_support_bin_indices':list(map(int,np.flatnonzero(missing_support))),
        'dorfler_theta_0p5_full_vs_mechanical_only_jaccard':float(np.sum(full_sel25&mech_sel25)/np.sum(full_sel25|mech_sel25)),
        'ranking_warning':'large weighting sensitivity invalidates any automatic mesh launch based on either candidate; no scientifically frozen mechanical-vs-thermal weights',
        'polar_raw_score_mass_percent':float(100*robust[25][cap].sum()/robust[25].sum()),
        'near_wall_raw_score_mass_percent':float(100*robust[25][wall].sum()/robust[25].sum()),
        'polar_smooth_kappa_mass_percent':float(100*k25[cap].sum()/k25.sum()),
        'off_polar_bins':int((~cap).sum()),
        'dorfler':{str(th):{'selected_25':int(selected[str(th)].sum()),
                            'selected_36':int(dorfler(robust[36],th).sum()),
                            'jaccard':float(np.sum(selected[str(th)]&dorfler(robust[36],th))/
                                            np.sum(selected[str(th)]|dorfler(robust[36],th))),
                            'polar_selected':int(np.sum(selected[str(th)]&cap)),
                            'nonpolar_selected':int(np.sum(selected[str(th)]&~cap))}
                   for th in THETAS},
        'next_gate':'construct a true spatially continuous Gmsh evaluable source with CAD transform and verify 2D/3D mesh-only D-025 0.75..0.85 volume locally; no M2 GO now'
    }
    args.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for i,(ir,im,ip,d0,d1,theta,phi,opened) in enumerate(meta):
        row={'radial_bin':ir,'mu_bin':im,'phi_bin':ip,'d_lower_mm':d0,
             'd_upper_mm': '' if opened else d1,'theta_mid_rad':theta,
             'phi_mid_rad':phi,'score25':float(score[25][i]),
             'robust_score25':float(robust[25][i]),
             'robust_score36':float(robust[36][i]),
             'stable_component_fraction':float(reliability[i]),
             'kappa25_smooth':float(k25[i]),'kappa36_smooth':float(k36[i]),
             'kappa25_mechanical_only':float(mk25[i]),
             'kappa36_mechanical_only':float(mk36[i]),
             'kappa25_primary_for_M2_source_only':float(mk25[i]),
             'mechanical_robust_score25':float(mech_robust25[i]),
             'mechanical_robust_score36':float(mech_robust36[i]),
             'M0_mechanical_QP_dt25':int(support25['M0'][i]),
             'M1_mechanical_QP_dt25':int(support25['M1'][i]),
             'QP_support_missing_in_any_compared_run':int(missing_support[i]),
             'polar_cap':int(cap[i]),'near_wall_first_0p1mm':int(wall[i])}
        for k,field in enumerate(COMPONENTS):
            row['M1_minus_M0_dt25_'+field]=float(difference[25][i,k])
            row['temporal_change_dt36_minus25_'+field]=float(difference[36][i,k]-difference[25][i,k])
        for th in THETAS:row[f'dorfler_theta_{th}']=int(selected[str(th)][i])
        rows.append(row)
    with (args.output/'P10HA_SPATIAL_KAPPA_1200_BINS.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    (args.output/'P10HA_KAPPA_QA.json').write_text(json.dumps(diagnostics,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(diagnostics,indent=2,ensure_ascii=False))


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True,help='original P10GY_12_RUNS_EVIDENCE.zip')
    ap.add_argument('--output',type=Path,required=True,help='new derived output directory')
    main(ap.parse_args())
