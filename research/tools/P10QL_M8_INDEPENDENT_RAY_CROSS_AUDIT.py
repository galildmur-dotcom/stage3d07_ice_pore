#!/usr/bin/env python3
"""P10QL: re-audit two h8 ray resolutions and 3 orthogonal physical cuts.

Diagnostic confidence is empirical (h/q/axis), not a validated interval
error bound. Never confuse a small signed difference with L1 convergence.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

PIN='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'


def get(filename):
    x=json.loads(Path(filename).read_text())
    if x['stage']!='P10QL' or x['mesh_sha256']!=PIN or \
       x.get('physical_4D_FEM_approved',False) or x.get('cut_full_4D_FEM_ready',False):
        raise ValueError('P10QL_WRONG_STAGE_OR_M8_PIN')
    return x


def cross_ray_details(filename,selected):
    x=get(filename)
    result=[]
    for item in x['results']:
        i=item['index']
        if i not in selected:raise ValueError('P10QL_UNEXPECTED_PILOT_INDEX')
        n=x['n_values'][-1];prev=x['n_values'][-2]
        cut=[d[str(n)]['cut_gradient_m3'] for d in item['ray_axes'].values()]
        dif=[abs(d[str(n)]['cut_gradient_m3']-d[str(prev)]['cut_gradient_m3'])
             for d in item['ray_axes'].values()]
        ref=sum(cut)/len(cut)
        spread=(max(cut)-min(cut))/abs(ref)
        delta=max(dif)/abs(ref)
        for audit in item['axis_full_analytic_relative'].values():
            if max(audit.values())>1e-10:
                raise ValueError('P10QL_FULL_POLYNOMIAL_IDENTITY_FAILED')
        result.append({'original_child':i,'n':n,'axes':list(item['ray_axes']),
                       'mean_ray_gradient_m3':ref,
                       'axis_Linf_relative_spread':spread,
                       'last_n_increase_max_relative':delta,
                       'algoim_gl_q8_gradient_m3':item['algoim_gl_q8_cut_gradient_m3'],
                       'algoim_vs_ray_relative':abs(ref-item['algoim_gl_q8_cut_gradient_m3'])/abs(ref),
                       'empirical_local_n_convergence_pass_1e_minus_6':delta<1e-6 and spread<1e-6})
    if sorted(v['original_child'] for v in result)!=sorted(selected):
        raise ValueError('P10QL_PILOT_CELLS_MISSING')
    return result


def analyze_sum(x):
    assert x['axis']==2 and len(x['cells'])==27
    if x['geometric_multi_uncertainty_bernstein_m3'][1]>2.41e-15:
        raise ValueError('P10QL_MULTI_BOUND_WIDENED')
    terms=x['cells']
    orders=x['transverse_Gauss_orders'];prev,last=orders[-2:]
    dif=[r['orders'][str(last)]['cut_gradient_m3']-
         r['orders'][str(prev)]['cut_gradient_m3'] for r in terms]
    l1=sum(abs(v) for v in dif);sg=sum(dif)
    total=x['ray_hybrid_gradient_m3_by_order'][str(last)]
    if not math.isclose(l1,x['ray_q_previous_to_last_L1_m3'],rel_tol=2e-12,abs_tol=1e-28) or \
       not math.isclose(sg,x['ray_q_previous_to_last_signed_m3'],rel_tol=2e-12,abs_tol=1e-28):
        raise ValueError('P10QL_RAY_L1_SIGNED_MISAGGREGATED')
    dgl=[r['orders'][str(last)]['cut_gradient_m3']-r['algoim_gl_q8_gradient_m3'] for r in terms]
    if not math.isclose(sum(abs(v) for v in dgl),x['ray_last_order_vs_gl_q8_L1_m3'],
                        rel_tol=2e-12,abs_tol=1e-28):
        raise ValueError('P10QL_ALGOIM_CROSS_L1_MISAGGREGATED')
    return {'n_pair':[prev,last], 'cut_cell_count':len(terms),
            'ray_total_gradient_m3':total,'algoim_gl_q8_total_gradient_m3':x['algoim_gl_q8_hybrid_gradient_m3'],
            'ray_q_change_L1_m3':l1,'ray_q_change_L1_relative_to_hybrid':l1/abs(total),
            'ray_q_change_signed_m3':sg,
            'ray_vs_algoim_L1_m3':sum(abs(v) for v in dgl),
            'ray_vs_algoim_L1_relative_to_hybrid':sum(abs(v) for v in dgl)/abs(total),
            'ray_vs_algoim_signed_m3':sum(dgl)}


def main():
    radial=cross_ray_details('P10QL_M8_RAY_PILOT_CASE4_H0_I0_HIGH_QA.json',[0])
    other=cross_ray_details('P10QL_M8_RAY_PILOT_CASE4_H0_ANGULAR_DOUBLE_HIGH_QA.json',[4,9])
    pilot=radial+other
    low=get('P10QL_M8_FULL_H8_RAY_AXIS2_QA.json')
    high=get('P10QL_M8_FULL_H8_RAY_AXIS2_Q128_QA.json')
    if low['ray_source_sha256']!=high['ray_source_sha256'] or \
       low['ray_source_sha256']!=hashlib.sha256(Path('P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE.py').read_bytes()).hexdigest():
        raise ValueError('P10QL_RAY_PROGRAM_SHA_CHANGED_BETWEEN_RUNS')
    if [v['index'] for v in low['cells']]!=[v['index'] for v in high['cells']]:
        raise ValueError('P10QL_H8_PARTITION_CHANGED_BETWEEN_Q_RUNS')
    for a,b in zip(low['cells'],high['cells']):
        q64a=a['orders']['64']['cut_gradient_m3']
        q64b=b['orders']['64']['cut_gradient_m3']
        if not math.isclose(q64a,q64b,rel_tol=1e-13,abs_tol=1e-27):
            raise ValueError('P10QL_SAME_INPUT_Q64_NOT_DETERMINISTIC')
    summaries=[analyze_sum(low),analyze_sum(high)]
    if not all(v['empirical_local_n_convergence_pass_1e_minus_6']
               for v in pilot if v['original_child'] in (0,4)):
        raise ValueError('P10QL_RADIAL_AND_AZIMUTHAL_LOCAL_Q256_DID_NOT_CONVERGE')
    if any(v['empirical_local_n_convergence_pass_1e_minus_6'] for v in pilot if v['original_child']==9):
        raise ValueError('P10QL_DOUBLE_CUT_Q256_NOT_TRULY_CONVERGED')
    output={'stage':'P10QL','date_utc':'2026-11-28','mesh_sha256':PIN,
            'scientific_status':'INDEPENDENT_RAY_SLICED_CUT_MOMENTS_WITH_POSITIVE_LOCAL_PILOTS_BUT_NO_GLOBAL_CERTIFICATE',
            'source_ray_sha256':low['ray_source_sha256'],
            'three_physical_pilots':pilot,
            'complete_real_h8_one_axis_q_series':summaries,
            'q_changes_and_axes_agreement_are_empirical_not_proven_error_bounds':True,
            'real_multi_boundary_residual_not_certified':True,
            'no_CAD_no_Gmsh_no_FEM':True,
            'physical_4D_FEM_approved':False}
    Path('P10QL_M8_INDEPENDENT_RAY_FINAL_CROSS_AUDIT_QA.json').write_text(json.dumps(output,indent=2)+'\n')
    print('P10QL_INDEPENDENT_RAY_CROSS_AUDIT_PASS_NOT_PHYSICS_CERTIFICATION',flush=True)


if __name__=='__main__':main()
