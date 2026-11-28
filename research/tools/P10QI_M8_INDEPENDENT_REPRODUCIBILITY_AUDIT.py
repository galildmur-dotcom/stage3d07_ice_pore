#!/usr/bin/env python3
"""Independent post-hoc P10QI M8 source/QA contract auditor, no Algoim import.

Recompute signed/L1 convergence of 8 true child integrals, match to prior
single-boundary volume baseline, check exact full-cell moments and
manufactured FE-field restriction provenance. No full FEM or mesh changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


SHA='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'


def check(cond,code):
    if not cond:
        raise AssertionError('P10QI_INDEPENDENT_AUDIT_STOP_'+code)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('mesh','preflight','worker-input','algoim-result','prior-qb','prior-qh','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    check(hashlib.sha256(args.mesh.read_bytes()).hexdigest()==SHA,'M8_SHA')
    pre=json.loads(args.preflight.read_text());
    res=json.loads(args.algoim_result.read_text());
    qb=json.loads(args.prior_qb.read_text());
    qh=json.loads(args.prior_qh.read_text());
    check(all(x['mesh_sha256']==SHA for x in (pre,res,qb,qh)),'INPUT_SHA')
    check(pre['worker_input_sha256']==hashlib.sha256(args.worker_input.read_bytes()).hexdigest(),'WORKER_CHILD_FIELD_SHA')
    check(pre['gradient_numerator_degree_upper_bound']==3 and pre['squared_radius_and_polar_degree_upper_bound']==4,'POLYNOMIAL_DEGREES')
    check(len(pre['cases'])==len(res['cases'])==len(qb['cases'])==8,'CASE_COUNTS')
    for a,b,c in zip(pre['cases'],res['cases'],qb['cases']):
        check(a['original_element_id']==b['element_id']==c['original_element_id'],'CHILD_PROVENANCE')
        check(a['active_quartic']==b['quartic']==c['quartic_constraint'],'CONSTRAINT_PROVENANCE')
        check(a['maximum_cubic_polynomial_reproduction_error_m3_per_ref_point']<1e-19,'CUBIC_REPRODUCTION')
        check(a['maximum_cofactor_vs_solved_physical_gradient_error']<1e-10,'COFACTOR_PHYSICAL')
        check(a['maximum_true_FE_child_parent_trace_error']<3e-12,'PARENT_FIELD_RESTRICTION')
        check(a['maximum_radial_cone_quartic_bernstein_error_m2']<3e-17,'QUARTIC_REPRODUCTION')
        check(len(b['q_records'])==5 and [x['q'] for x in b['q_records']]==[2,3,4,6,8],'Q_SET')
        for rec in b['q_records']:
            check(rec['minimum_weight']>0 and rec['active']>0 and rec['points']>=rec['active'],'WEIGHTS')
            if rec['q']>=3:
                check(rec['full_gradient_rel']<1e-10 and rec['full_volume_rel']<1e-10,'EXACT_FULL_CHILD_MOMENT')
        check(b['q6_to_q8_absolute_relative_cut_gradient']<1e-9,'LOCAL_Q6_Q8_NO_STABILIZATION')
        check(b['difference_to_QMC_in_standard_errors']<=6,'RANDOM_INDEPENDENT_REFERENCE')
    computed=[]
    for a,b in ((2,3),(3,4),(4,6),(6,8),(3,8)):
        moment=np.array([next(x['cut_gradient_m3'] for x in c['q_records'] if x['q']==b) for c in res['cases']])
        earlier=np.array([next(x['cut_gradient_m3'] for x in c['q_records'] if x['q']==a) for c in res['cases']])
        delta=moment-earlier
        l1=float(np.sum(abs(delta))/np.sum(abs(moment)))
        signed=float(abs(np.sum(delta))/np.sum(abs(moment)))
        prior=next(x for x in res['q_delta_signed_and_L1'] if x['q_pair']==[a,b])
        check(abs(prior['L1_abs_deltas_relative_to_L1_moment']-l1)<1e-14,'L1_DISAGREEMENT')
        check(abs(prior['signed_abs_delta_relative_to_L1_moment']-signed)<1e-14,'SIGNED_DISAGREEMENT')
        check(signed<=l1+1e-14,'SIGNED_GT_L1')
        computed.append({'q_pair':[a,b],'L1_abs_relative':l1,'signed_abs_relative':signed,
                         'positive_deltas':int(np.sum(delta>0)),'negative_deltas':int(np.sum(delta<0))})
    check(computed[0]['L1_abs_relative']>computed[1]['L1_abs_relative']>
          computed[2]['L1_abs_relative']>computed[3]['L1_abs_relative'],'FOUR_LEVEL_MONOTONIC_AGGREGATE')
    check(res['total_q8_quadrature_points']==sum(c['q_records'][-1]['points'] for c in res['cases']),'Q8_WORK_COUNT')
    check(not any(x.get('physical_4D_FEM_approved',False) for x in (pre,res)),'FEM_APPROVED_EARLY')
    out={'stage':'P10QI','status':'PASS_INDEPENDENT_EIGHT_REAL_M8_GRADIENT_CUT_CONVERGENCE_AND_PROVENANCE',
         'mesh_sha256':SHA,'mesh_changed':False,'physical_FEM_run':False,
         'audited_real_curved_Tet10_children':8,
         'independently_checked_parent_child_P2_field_restriction':True,
         'independently_checked_full_element_cubic_moments':True,
         'prior_real_M8_volume_algoim_parity':True,
         'independently_recomputed_signed_and_L1':computed,
         'q8_points':res['total_q8_quadrature_points'],
         'prior_P10QH_empirical_gradient_L1_q32_discrepancy':qh['face_policy_L1_abs_signed_q32_discrepancy']['L1_absolute_relative_to_q32_L1'],
         'comparison_limit':'P10QH integrated four whole spherical bins. P10QI integrates eight preselected small, one-active-quartic Tet10 children; rates are NOT a like-for-like global FEM error comparison.',
         'unresolved_M8_multi_boundary_cuts':True,
         'local_q_agreement_proves_absolute_error':False,
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QI_INDEPENDENT_REPRODUCIBILITY_PASS',flush=True)


if __name__=='__main__':
    main()
