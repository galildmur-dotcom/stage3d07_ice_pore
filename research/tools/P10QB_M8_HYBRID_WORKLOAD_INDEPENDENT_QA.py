#!/usr/bin/env python3
"""Independent mass-closure and computational scaling audit of P10QB hybrid."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh',type=Path,required=True)
    parser.add_argument('--hybrid',type=Path,required=True)
    parser.add_argument('--physical',type=Path,required=True)
    parser.add_argument('--pilot',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('P10QB_M8_HYBRID_WORKLOAD_SUMMARY_QA.json'))
    parser.add_argument('--csv',type=Path,default=Path('P10QB_M8_HYBRID_WORKLOAD_CONVERGENCE.csv'))
    args=parser.parse_args()
    digest=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    hybrid=json.loads(args.hybrid.read_text(encoding='utf-8'))
    volume=json.loads(args.physical.read_text(encoding='utf-8'))
    pilot=json.loads(args.pilot.read_text(encoding='utf-8'))
    if digest!=m8.PINNED_M8_SHA256 or any(x['mesh_sha256']!=digest for x in (hybrid,volume,pilot)):
        raise ValueError('cannot compare nonaccepted M8 inputs')
    if hybrid['status']!='PASS_HYBRID_M8_48_BIN_GEOMETRIC_READINESS_NOT_FULL_ALGOIM':
        raise ValueError('hybrid workload not finished')
    if pilot['status']!='PASS_REAL_ALGOIM_LAPACKE_EIGHT_M8_SINGLE_QUARTIC_PILOTS':
        raise ValueError('actual Algoim pilot is not qualified')
    if hybrid['bin_count']!=volume['bin_count']!=48 or hybrid['max_depth']!=volume['max_depth']!=12:
        raise ValueError('not a complete 48-bin comparison')
    groups={}
    rows=['radial_bin,mu_bin,phi_bin,depth,one_quartic_calls,one_quadratic_calls,remaining_multi_leaves,remaining_multi_physical_m3,remaining_multi_fraction_candidates']
    total={'one_quartic_calls':0,'one_quadratic_calls':0,'multi_remaining_leaves':0,
           'multi_remaining_physical_m3':0.,'candidate_total_physical_m3':0.}
    for b,base in zip(hybrid['bins'],volume['bins']):
        key=(b['radial_bin'],b['mu_bin'],b['phi_bin'])
        if key!=(base['radial_bin'],base['mu_bin'],base['phi_bin']):
            raise ValueError('different azimuth/radial/polar bin identities')
        root=b['candidate_physical_m3']
        if b['candidate_count']!=base['candidate_count'] or abs(root-base['candidate_total_physical_m3'])>2e-12*root:
            raise ValueError('candidate geometry not reproduced')
        previous_calls=(0,0)
        previous_multi_mass=root
        for depth,(d,old) in enumerate(zip(b['depth_records'],base['depth_records'])):
            if d['depth']!=depth or old['depth']!=depth:
                raise ValueError('depth labels wrong')
            mass=sum(d[k+'_physical_m3'] for k in
                     ('inside','outside','one_quartic','one_quadratic','multi_remaining'))
            if abs(mass-root)>2e-11*root:
                raise ValueError('physical mass conservation failed')
            if d['one_quartic_calls']<previous_calls[0] or d['one_quadratic_calls']<previous_calls[1]:
                raise ValueError('simple-case count not monotone')
            if d['multi_remaining_physical_m3']>previous_multi_mass+1e-12*root:
                raise ValueError('multi-active domain cannot grow on refinement')
            if d['multi_remaining_leaves']>old['unresolved_leaves']:
                raise ValueError('multi-active residual larger than no-stop baseline')
            previous_calls=d['one_quartic_calls'],d['one_quadratic_calls']
            previous_multi_mass=d['multi_remaining_physical_m3']
            rows.append(f'{key[0]},{key[1]},{key[2]},{depth},'
                        f'{d["one_quartic_calls"]},{d["one_quadratic_calls"]},'
                        f'{d["multi_remaining_leaves"]},'
                        f'{d["multi_remaining_physical_m3"]:.17g},'
                        f'{d["multi_remaining_fraction_candidate_mass"]:.17g}')
        if len(b['depth_records'])!=13:
            raise ValueError('missing depth records')
        fin=b['depth_records'][-1]
        grp=groups.setdefault(f'r{key[0]}_mu{key[1]}',
            {'bin_count':0,'one_quartic_calls':0,'one_quadratic_calls':0,
             'remaining_multi_leaves':0,'remaining_multi_physical_m3':0.,
             'candidate_physical_m3':0.})
        grp['bin_count']+=1
        for name in ('one_quartic_calls','one_quadratic_calls'):
            grp[name]+=fin[name]
            total[name]+=fin[name]
        grp['remaining_multi_leaves']+=fin['multi_remaining_leaves']
        grp['remaining_multi_physical_m3']+=fin['multi_remaining_physical_m3']
        grp['candidate_physical_m3']+=root
        total['multi_remaining_leaves']+=fin['multi_remaining_leaves']
        total['multi_remaining_physical_m3']+=fin['multi_remaining_physical_m3']
        total['candidate_total_physical_m3']+=root
    for key,grp in groups.items():
        if grp['bin_count']!=12:
            raise ValueError('incomplete azimuth coverage')
        grp['multi_mass_fraction_candidates']=grp['remaining_multi_physical_m3']/grp['candidate_physical_m3']
    total['multi_mass_fraction_candidates']=total['multi_remaining_physical_m3']/total['candidate_total_physical_m3']
    points=[c['q8']['points'] for c in pilot['cases']]
    total['pilot_q8_points_min']=min(points)
    total['pilot_q8_points_max']=max(points)
    total['pilot_q8_points_median']=sorted(points)[len(points)//2]
    # This extrapolation is explicitly a *scenario*, not a performance promise.
    total['naive_q8_node_scenario_min']=total['one_quartic_calls']*min(points)
    total['naive_q8_node_scenario_max']=total['one_quartic_calls']*max(points)
    report={'stage':'P10QB','status':'PASS_INDEPENDENT_48_BIN_HYBRID_WORKLOAD_NOT_FULL_QUADRATURE',
            'mesh_sha256':digest,'mesh_changed':False,'fem_started':False,
            'full_local_algoim_calls_executed':len(pilot['cases']),
            'groups':groups,'all48_totals':total,
            'interpretation':'All candidate calls are potential workload; only eight actual pilot Algoim integrations executed. Multi-active residual is still unintegrated.',
            'not_ready_for_4D_FEM':True}
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    args.csv.write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print('P10QB_HYBRID_48_BIN_INDEPENDENT_QA_PASS',json.dumps(total),flush=True)


if __name__=='__main__':
    main()
