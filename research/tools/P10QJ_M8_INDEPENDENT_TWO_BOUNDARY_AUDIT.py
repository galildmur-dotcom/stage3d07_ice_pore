#!/usr/bin/env python3
"""Independent P10QJ negative-result plus h-refinement evidence audit.

Deliberately recomputes aggregate signed and L1 q changes, checks q8 exact
full-Tet10 moment FAIL classifications and monotone conservative 3D h mass.
No new geometry algorithms, no physical FEM, no Gmsh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

SHA='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'


def require(cond,why):
    if not cond:
        raise AssertionError('P10QJ_INDEPENDENT_AUDIT_STOP_'+why)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for x in ('mesh','selection','worker-input','algoim','h-budget','prior-qi','output'):
        ap.add_argument('--'+x,required=True,type=Path)
    a=vars(ap.parse_args())
    s=json.loads(a['selection'].read_text())
    v=json.loads(a['algoim'].read_text())
    h=json.loads(a['h_budget'].read_text())
    qi=json.loads(a['prior_qi'].read_text())
    require(hashlib.sha256(a['mesh'].read_bytes()).hexdigest()==SHA,'M8_SHA')
    require(all(x['mesh_sha256']==SHA for x in (s,v,h,qi)),'REPORT_PIN')
    require(s['worker_input_sha256']==hashlib.sha256(a['worker_input'].read_bytes()).hexdigest(),'REAL_WORKER_INPUT')
    require(len(s['cases'])==len(v['cases'])==len(h['cases'])==8,'EIGHT_CASES')
    require(len(qi['cases'])==8,'PRIOR_ONE_BOUNDARY_CASES')
    require(s['status']=='PASS_REAL_M8_TWO_ACTIVE_QUARTIC_QUADRATIC_BERNSTEIN_SELECTION','SELECTOR')
    require(v['status']=='FAIL_Q8_FULL_TET10_MOMENT_CONVERGENCE_ON_REAL_TWO_BOUNDARY_CELLS','EXPECTED_NEGATIVE')
    failures=[];comparisons=[]
    for original,calc,sub in zip(s['cases'],v['cases'],h['cases']):
        require(original['original_element_id']==calc['element_id']==sub['element_id'],'ORIGINAL_REAL_M8')
        active=[i for i,q in enumerate(original['constraints_status']) if q==0]
        require(sorted(active)==sorted([original['quartic_constraint'],original['quadratic_constraint']]),'EXACTLY_TWO_UNCERTAIN')
        require(all(x==1 for k,x in enumerate(original['constraints_status']) if k not in active),'OTHER_FOUR_NOT_CERTIFIED')
        require(min(original['lattice_sign_phase_counts'])>=2,'NOT_REAL_FOUR_PHASE_CROSSING')
        rec=calc['q_records']
        require([x['q'] for x in rec]==[2,3,4,6,8],'Q_LEVELS')
        require(all(0<x['min_weight'] and 0<x['active_points']<=x['total_points']<=2_000_000 for x in rec),'WEIGHTS_CAP')
        require(calc['QMC_difference_in_standard_errors']<8,'INDEPENDENT_QMC_DISAGREES')
        failed=max(rec[-1]['full_gradient_relative'],rec[-1]['full_volume_relative'])>1e-10
        require(failed!=calc['q8_exact_full_moment_test_pass_1e_minus_10'],'PASS_FLAG_INCONSISTENT')
        if failed:failures.append(original['original_element_id'])
        rows=sub['level_records'];require(len(rows)>2,'H_LEVELS')
        last=1.
        for row in rows:
            frac=row['unresolved_at_least_two_boundary_volume_fraction']
            require(frac<=last+1e-11 and frac>=-1e-14,'MULTI_MASS_NOT_MONOTONE')
            last=frac
            total=(frac+row['cumulative_outside_volume_fraction']+
                  row['cumulative_fully_inside_volume_fraction']+
                  row['cumulative_one_boundary_volume_fraction'])
            require(abs(total-1)<3e-10,'PHYSICAL_MASS_NOT_CONSERVED')
        require(rows[-1]['h_level']==8,'EXPECTED_DEPTH8')
        comparisons.append({'element_id':calc['element_id'],'radial_bin':calc['radial_bin'],
              'q8_full_gradient_moment_relative_error':rec[-1]['full_gradient_relative'],
              'q8_nodes':rec[-1]['total_points'],
              'q8_full_moment_pass':not failed,
              'h8_multi_boundary_volume_fraction':rows[-1]['unresolved_at_least_two_boundary_volume_fraction'],
              'h8_resolved_or_one_boundary_volume_fraction':
                    1-rows[-1]['unresolved_at_least_two_boundary_volume_fraction']})
    require(len(failures)==4,'FOUR_NEGATIVE_CASES')
    require(all(x['radial_bin']==4 for x in comparisons if not x['q8_full_moment_pass']),'NEGATIVES_NOT_OUTER_SHELL')
    require(all(x['radial_bin']==0 for x in comparisons if x['q8_full_moment_pass']),'POSITIVES_NOT_INNER_SHELL')
    sums=[]
    for q0,q1 in ((2,3),(3,4),(4,6),(6,8)):
        start=np.array([next(x['cut_gradient_m3'] for x in c['q_records'] if x['q']==q0) for c in v['cases']])
        end=np.array([next(x['cut_gradient_m3'] for x in c['q_records'] if x['q']==q1) for c in v['cases']])
        d=end-start
        l1=float(abs(d).sum()/abs(end).sum());signed=float(abs(d.sum())/abs(end).sum())
        orig=next(x for x in v['q_convergence_signed_and_L1'] if x['q_pair']==[q0,q1])
        require(abs(orig['L1_abs_relative']-l1)<1e-14 and abs(orig['signed_abs_relative']-signed)<1e-14,'Q_CONVERGENCE_MISMATCH')
        require(signed<=l1+1e-14,'SIGNED_NOT_L1')
        sums.append({'q_pair':[q0,q1],'L1_relative':l1,'signed_relative':signed})
    out={'stage':'P10QJ','status':'PASS_INDEPENDENT_NEGATIVE_TWO_SURFACE_Q8_AND_H_REMEDIATION_AUDIT',
         'mesh_sha256':SHA,'mesh_unchanged':True,'physical_FEM_performed':False,
         'q8_failed_full_analytical_moment_cases':len(failures),
         'q8_passed_full_analytical_moment_cases':len(v['cases'])-len(failures),
         'failed_element_ids':failures,'q8_true_gradients_cannot_be_certified':True,
         'crosscheck_cases':comparisons,'recomputed_q_changes_signed_and_L1':sums,
         'h_mass_partition_is_conservative':True,'h_reference_refinement_does_not_modify_M8':True,
         'remaining_multi_boundary_mass_is_not_integrated':True,
         'allow_full_48_bin_fem':False,'physical_4D_FEM_approved':False}
    a['output'].write_text(json.dumps(out,indent=2)+'\n')
    print('P10QJ_INDEPENDENT_NEGATIVE_AND_H_AUDIT_PASS',flush=True)


if __name__=='__main__':
    main()
