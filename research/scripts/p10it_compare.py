#!/usr/bin/env python3
"""Source-only M2/M3 signed 4D comparison, no Gmsh/FEM."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

PARTS = ('mech_explicit_per_m', 'mech_equilibrium_per_m', 'mech_history_per_m',
         'thermal_mass_per_m', 'thermal_diffusion_per_m')
KEY = ('radial_bin', 'mu_bin', 'phi_bin')
BOUNDS = ('r_lower_mm', 'r_upper_mm', 'theta_lower_rad', 'theta_upper_rad',
          'phi_lower_rad', 'phi_upper_rad')


def read(path, mesh):
    result = {}
    bounds = {}
    supports = {}
    robin = []
    with path.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            assert row['mesh'] == mesh and row['mode'] == 'R' and row['functional'] == 'jpeak'
            n = int(row['step'])
            assert 1 <= n <= 36 and int(row['time_start_s']) == 25 * (n-1)
            assert int(row['time_end_s']) == 25*n
            if row['region'] == 'TOP_ROBIN':
                robin.append(row)
                continue
            assert row['region'] == 'VOLUME'
            key = tuple(int(row[x]) for x in KEY)
            assert all(0 <= v < lim for v, lim in zip(key, (10, 10, 12)))
            b = tuple(float(row[x]) if row[x] else None for x in BOUNDS)
            assert key not in bounds or bounds[key] == b
            bounds[key] = b
            kn = key + (n,)
            assert kn not in result, f'duplicate bin {kn}'
            arr = np.array([float(row[x]) for x in PARTS], float)
            assert np.all(np.isfinite(arr))
            assert abs(float(row['total_per_m']) - arr.sum()) < 1e-8
            result[kn] = arr
            supports[kn] = int(row['mechanical_qp'])
    assert len(result) == 43200 and len(bounds) == 1200 and len(robin) == 36
    return result, bounds, supports


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def dorfler(s):
    order = np.argsort(-s, kind='stable')
    count = int(np.searchsorted(np.cumsum(s[order]), .5 * s.sum()) + 1)
    return set(order[:count].tolist())


def smooth(xyz, u, raw):
    out = np.empty(len(raw))
    for i in range(len(raw)):
        rho = np.sqrt(((u-u[i])/.75)**2 + ((xyz-xyz[i])**2).sum(axis=1)/.60**2)
        w = np.maximum(1-rho, 0)**4 * (4*np.maximum(rho, 0)+1)
        w[rho >= 1] = 0
        out[i] = np.dot(w, raw)/w.sum()
    return out/out.max()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--m2', type=Path, required=True)
    ap.add_argument('--m3', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--prior', type=Path)
    a = ap.parse_args()
    m2, b2, qp2 = read(a.m2, 'M2')
    m3, b3, qp3 = read(a.m3, 'M3')
    assert m2.keys() == m3.keys() and b2 == b3
    keys = sorted(b2)
    delta = np.array([[m3[k+(n,)] - m2[k+(n,)] for n in range(1,37)] for k in keys])
    summed = delta.sum(axis=(0,1))
    global_shift = float(summed.sum())
    assert abs(global_shift - (2.473214870917888-2.5598510250834945)) < 1e-9
    assert np.all(np.array([[qp2[k+(n,)] > 0 and qp3[k+(n,)] > 0 for n in range(1,37)] for k in keys]))
    a_parts = np.abs(delta).sum(axis=1)
    denom = a_parts.sum(axis=0)
    assert np.all(denom > 0)
    normalized = a_parts / denom
    mech = normalized[:,:3].mean(axis=1)
    thermal = normalized[:,3:].mean(axis=1)
    # Angular centers from exact shared physical bin bounds.
    th = np.array([.5*(b2[k][2]+b2[k][3]) for k in keys])
    ph = np.array([.5*(b2[k][4]+b2[k][5]) for k in keys])
    xyz = np.column_stack((np.sin(th)*np.cos(ph),np.sin(th)*np.sin(ph),np.cos(th)))
    d = np.array([.5*(b2[k][0] + b2[k][1]) if b2[k][1] is not None else 15 for k in keys])
    u = np.log1p(d/.05)
    beta_scores = {str(b): (1-b)*mech + b*thermal for b in (0,.1,.25)}
    beta_smoothed = {b: smooth(xyz,u,s) for b,s in beta_scores.items()}
    region = {'north':np.array([k[0]<=4 and k[1]==9 for k in keys]),
              'south':np.array([k[0]<=4 and k[1]==0 for k in keys])}
    region['polar'] = region['north'] | region['south']
    all_step_delta = delta.sum(axis=2)
    spatial_signed = delta.sum(axis=(1,2))
    l1_4d = float(np.abs(all_step_delta).sum())
    beta_qa={}
    for b,s in beta_scores.items():
        selected = dorfler(s)
        beta_qa[b]={'dorfler_theta_0p5_bins':len(selected),
                    'dorfler_supported_polar_bins':sum(bool(region['polar'][i]) for i in selected),
                    'supported_polar_score_fraction':float(s[region['polar']].sum()/s.sum()),
                    'max_kappa':float(beta_smoothed[b].max()),
                    'top_10_bins':[list(keys[i]) for i in np.argsort(-beta_smoothed[b])[:10]]}
    if a.prior:
        with a.prior.open(newline='',encoding='utf-8-sig') as f:
            prior={tuple(int(r[x]) for x in KEY):r for r in csv.DictReader(f)}
        assert set(prior)==set(keys)
        old_score=np.array([float(prior[k]['beta_0p1_score']) for k in keys])
        old_kappa=np.array([float(prior[k]['beta_0p1_kappa_smoothed']) for k in keys])
        old_sel=dorfler(old_score);new_sel=dorfler(beta_scores['0.1'])
        summary_old={'source_sha256':sha(a.prior),
            'dorfler_jaccard_beta_0p1':len(old_sel&new_sel)/len(old_sel|new_sel),
            'kappa_MAE_centers_beta_0p1':float(np.abs(beta_smoothed['0.1']-old_kappa).mean()),
            'old_polar_score_fraction':float(old_score[region['polar']].sum()/old_score.sum())}
    else:
        summary_old=None
    summary={'protocol':'P10IT_INDEPENDENT_M2_M3_SOURCE_ONLY',
             'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_FEM',
             'inputs_sha256':{'M2_4D_CSV':sha(a.m2),'M3_4D_CSV':sha(a.m3)},
             'spatial_bins':len(keys),'time_steps':36,'volume_4d_rows_each':len(m2),
             'global_signed_delta':global_shift,
             'component_signed_delta':dict(zip(PARTS,map(float,summed))),
             'sum_abs_component_4d_delta':float(np.abs(delta).sum()),
             'sum_abs_total_4d_delta':l1_4d,
             'cancellation_factor_total_4d':l1_4d/abs(global_shift),
             'regions':{},'beta_hypotheses':beta_qa}
    summary['comparison_to_M3_source_P10IM']=summary_old
    for name,mask in region.items():
        dd=delta[mask]
        summary['regions'][name]={'bins':int(mask.sum()),
            'signed_delta':float(dd.sum()),
            'signed_component_delta':dict(zip(PARTS,map(float,dd.sum(axis=(0,1))))),
            'l1_4d_total_delta':float(np.abs(dd.sum(axis=2)).sum()),
            'l1_4d_component_delta':float(np.abs(dd).sum()),
            'M2_QP':sum(qp2[k+(n,)] for k,ok in zip(keys,mask) if ok for n in range(1,37)),
            'M3_QP':sum(qp3[k+(n,)] for k,ok in zip(keys,mask) if ok for n in range(1,37))}
    a.out.mkdir(parents=True,exist_ok=True)
    with (a.out/'P10IT_M2_M3_1200_BINS.csv').open('w',newline='') as f:
        fields=list(KEY)+['M2_QP','M3_QP','signed_delta','abs_4d_total_delta','abs_4d_components_delta','first12_signed_delta','last12_signed_delta']
        fields += ['signed_delta_'+p for p in PARTS] + ['abs_4d_'+p for p in PARTS]
        fields += ['mech_score','thermal_score']
        for b in beta_scores:fields += ['beta_'+b+'_score','beta_'+b+'_kappa']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for i,k in enumerate(keys):
            row=dict(zip(KEY,k))
            row.update(M2_QP=sum(qp2[k+(n,)] for n in range(1,37)),M3_QP=sum(qp3[k+(n,)] for n in range(1,37)),
                       signed_delta=spatial_signed[i],abs_4d_total_delta=np.abs(all_step_delta[i]).sum(),
                       abs_4d_components_delta=np.abs(delta[i]).sum(),
                       first12_signed_delta=delta[i,:12,:].sum(),last12_signed_delta=delta[i,24:,:].sum(),
                       mech_score=mech[i],thermal_score=thermal[i])
            for j,p in enumerate(PARTS):
                row['signed_delta_'+p]=delta[i,:,j].sum()
                row['abs_4d_'+p]=a_parts[i,j]
            for b,s in beta_scores.items():
                row['beta_'+b+'_score']=s[i]
                row['beta_'+b+'_kappa']=beta_smoothed[b][i]
            w.writerow(row)
    (a.out/'P10IT_QA.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
