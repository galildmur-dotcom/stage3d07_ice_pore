#!/usr/bin/env python3
"""Independent 48-bin feasibility and monotone budget audit for P10QC.

The scheduling table is a *conditional* physical mass-bound workload plan:
selected local integrals are hypothetically exact, and unsolved multi cuts
retain [0,V] uncertainty. This is NOT a quadrature error bound or FEM pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8


TARGETS=[50.,20.,10.,5.,2.,1.]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--hybrid',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('P10QC_M8_ABSOLUTE_BUDGET_SUMMARY_QA.json'))
    p.add_argument('--csv',type=Path,default=Path('P10QC_M8_ABSOLUTE_BUDGET_QA.csv'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    sched=json.loads(args.schedule.read_text(encoding='utf-8'))
    hybrid=json.loads(args.hybrid.read_text(encoding='utf-8'))
    if sha!=m8.PINNED_M8_SHA256 or sched['mesh_sha256']!=sha or hybrid['mesh_sha256']!=sha:
        raise ValueError('not accepted M8 physical data')
    if sched['status']!='PASS_ALL48_PHYSICAL_ABSOLUTE_VOLUME_BUDGET_WORKLOAD_ONLY':
        raise ValueError('schedule not generated')
    if sched['bin_count']!=hybrid['bin_count']!=48 or sched['max_depth']!=hybrid['max_depth']!=12:
        raise ValueError('incomplete 48x13 coverage')
    result={str(t):{'target_percent_ideal':t,'feasible_bins':0,
                    'blocked_by_multi_floor_bins':0,'selected_calls':0,
                    'skipped_calls':0,'selected_quartic':0,'selected_quadratic':0,
                    'node_scenario_q4':0,'node_scenario_q8':0} for t in TARGETS}
    rows=['radial_bin,mu_bin,phi_bin,target_percent_ideal,state,selected_calls,selected_quartic,selected_quadratic,skipped_calls,remaining_upper_m3,multi_floor_m3']
    for b,old in zip(sched['bins'],hybrid['bins']):
        key=tuple(b[k] for k in ('radial_bin','mu_bin','phi_bin'))
        if key!=tuple(old[k] for k in ('radial_bin','mu_bin','phi_bin')):
            raise ValueError('bin identity changed')
        d=old['depth_records'][-1]
        total_calls=d['one_quartic_calls']+d['one_quadratic_calls']
        if total_calls!=b['single_quartic_calls']+b['single_quadratic_calls']:
            raise ValueError('selected call total changed')
        if abs(d['multi_remaining_physical_m3']-b['multi_remaining_physical_m3'])>2e-12*b['candidate_physical_volume_m3']:
            raise ValueError('multi physical floor mismatch')
        previous=0
        for t in TARGETS:
            key_t=str(t)
            data=b['budgets_percent_ideal'][key_t]
            r=result[key_t]
            target=t/100*b['ideal_spherical_sector_volume_m3']
            floor=b['multi_remaining_physical_m3']
            if abs(data['ideal_absolute_budget_m3']-target)>1e-12*target:
                raise ValueError('wrong per-bin absolute target')
            if floor>=target:
                if data['state']!='BLOCKED_BY_MULTI_BOUNDARY_FLOOR':
                    raise ValueError('multi-blocked bin improperly declared feasible')
                r['blocked_by_multi_floor_bins']+=1
                rows.append(','.join(str(x) for x in (*key,t,'BLOCKED',0,0,0,0,'',floor)))
                continue
            if data['state']!='POSSIBLE_IF_SELECTED_CUT_INTEGRALS_ARE_EXACT':
                raise ValueError('unnecessarily blocked feasible target')
            k=data['needed_calls']
            if not 0<=k<=total_calls or data['skipped_calls']+k!=total_calls:
                raise ValueError('invalid number of scheduled local Algoim calls')
            if k<previous:
                raise ValueError('stricter tolerance cannot require fewer local calls')
            previous=k
            if data['quartic_calls']+data['quadratic_calls']!=k:
                raise ValueError('missing split between quadratic and quartic calls')
            if data['estimated_unintegrated_upper_m3']>target*(1+4e-12):
                raise ValueError('scheduled absolute physical mass bound exceeded')
            r['feasible_bins']+=1
            for k1,k2 in [('selected_calls','needed_calls'),('skipped_calls','skipped_calls'),
                          ('selected_quartic','quartic_calls'),('selected_quadratic','quadratic_calls'),
                          ('node_scenario_q4','scenario_nodes_q4'),('node_scenario_q8','scenario_nodes_q8')]:
                r[k1]+=data[k2]
            rows.append(','.join(str(x) for x in (*key,t,'CONDITIONAL',k,
                       data['quartic_calls'],data['quadratic_calls'],data['skipped_calls'],
                       data['estimated_unintegrated_upper_m3'],floor)))
    for t,r in result.items():
        if r['feasible_bins']+r['blocked_by_multi_floor_bins']!=48:
            raise ValueError('missing full-bin budget outcomes')
    output={'stage':'P10QC','status':'PASS_INDEPENDENT_48_BIN_ABSOLUTE_BUDGET_FEASIBILITY_ONLY',
            'mesh_sha256':sha,'mesh_changed':False,'fem_started':False,
            'target_relative_to':'ideal spherical-sector volume, independent from exact discrete Tet10 region',
            'budgets':result,
            'warning':'Conditional if selected local cut integrals exact, q-error and multi-boundary remainder not yet solved; no physical FEM approval',
            'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    args.csv.write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print('P10QC_INDEPENDENT_ABSOLUTE_BUDGET_QA_PASS',json.dumps(result),flush=True)


if __name__=='__main__':
    main()
