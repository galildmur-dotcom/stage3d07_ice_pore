#!/usr/bin/env python3
"""P10QM: independent two-axis n128/n256 L1 and signed audit on real M8 h8.

Reads two independently executed ray-integration files, the earlier n128
study and the original Algoim Q8 benchmark.  Every check fails closed:
even positive empirical h/q/axis convergence is NOT an error certificate.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

M8='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
FILES={
  1:Path('P10QM_M8_FULL_H8_RAY_AXIS1_Q256_QA.json'),
  2:Path('P10QM_M8_FULL_H8_RAY_AXIS2_Q256_QA.json')}
SOURCE=Path('P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE.py')
PRIOR=Path('P10QL_M8_FULL_H8_RAY_AXIS2_Q128_QA.json')
REFERENCE=Path('P10QK_M8_HYBRID_H_AND_Q_ALWAYS_GL_QA.json')


def data(file):
    a=json.loads(file.read_text())
    if a['stage'] not in ('P10QL','P10QM') or a['mesh_sha256']!=M8 or \
       a.get('cut_full_4D_FEM_ready',False) or a.get('physical_4D_FEM_approved',False):
        raise ValueError('P10QM_BAD_PIN_OR_ILLEGAL_PHYSICAL_AUTHORITY')
    return a


def weight_moments(x):
    n=x['transverse_Gauss_orders'];assert n==[128,256]
    prev=[];now=[];algo=[];vol_prev=[];vol_now=[];groups={'one':0,'multi':0}
    for cell in x['cells']:
        groups[cell['group']]+=1
        prev.append(cell['orders']['128']['cut_gradient_m3'])
        now.append(cell['orders']['256']['cut_gradient_m3'])
        algo.append(cell['algoim_gl_q8_gradient_m3'])
        vol_prev.append(cell['orders']['128']['cut_volume_m3'])
        vol_now.append(cell['orders']['256']['cut_volume_m3'])
    if len(now)!=27 or groups!={'one':22,'multi':5}:
        raise ValueError('P10QM_WRONG_H8_ACTIVE_PARTITION')
    delta=[b-a for a,b in zip(prev,now)]
    contrast=[b-a for a,b in zip(algo,now)]
    vol_delta=[b-a for a,b in zip(vol_prev,vol_now)]
    qtotal=x['ray_hybrid_gradient_m3_by_order']['256']
    sum_l1=sum(abs(d) for d in delta)
    if not math.isclose(sum_l1,x['ray_q_previous_to_last_L1_m3'],rel_tol=2e-12,abs_tol=1e-28) or \
       not math.isclose(sum(delta),x['ray_q_previous_to_last_signed_m3'],rel_tol=2e-12,abs_tol=1e-28):
        raise ValueError('P10QM_REPORTED_SIGNED_L1_NOT_REPRODUCIBLE')
    if not math.isclose(sum(abs(d) for d in contrast),x['ray_last_order_vs_gl_q8_L1_m3'],
                        rel_tol=2e-12,abs_tol=1e-28):
        raise ValueError('P10QM_REPORTED_ALGOIM_DELTA_NOT_REPRODUCIBLE')
    by_group={}
    for group in ('one','multi'):
        items=[(abs(delta[j]),abs(now[j]),x['cells'][j]['index'])
               for j in range(len(now)) if x['cells'][j]['group']==group]
        by_group[group]={'cell_count':len(items),
                         'q128_q256_L1_gradient_m3':sum(v[0] for v in items),
                         'top_cells_by_absolute_delta':[
                            {'index':i,'absolute_delta_m3':d,'absolute_integral_m3':g}
                             for d,g,i in sorted(items,reverse=True)[:7]]}
    return {'axis':x['axis'],'q256_total_m3':qtotal,
            'q128_to_q256_L1_m3':sum_l1,
            'q128_to_q256_L1_relative_to_hybrid':sum_l1/max(abs(qtotal),1e-25),
            'q128_to_q256_signed_m3':sum(delta),
            'q256_vs_algoim_q8_L1_m3':sum(abs(d) for d in contrast),
            'q256_vs_algoim_q8_L1_relative_to_hybrid':sum(abs(d) for d in contrast)/max(abs(qtotal),1e-25),
            'q256_vs_algoim_q8_signed_m3':sum(contrast),
            'q128_to_q256_volume_L1_m3':sum(abs(d) for d in vol_delta),
            'q128_to_q256_volume_L1_relative_to_cut_volume':sum(abs(d) for d in vol_delta)/max(sum(abs(v) for v in vol_now),1e-25),
            'by_group':by_group,
            'full_physical_ray_points':sum(c['orders']['256']['transverse_Gauss_points'] for c in x['cells'])}


def main():
    sources={axis:data(file) for axis,file in FILES.items()}
    previous=data(PRIOR)
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    for axis,x in sources.items():
        if x['axis']!=axis or x['ray_source_sha256']!=sha or \
           x['transverse_Gauss_orders']!=[128,256]:
            raise ValueError('P10QM_WRONG_AXIS_OR_RAY_SOURCE_REVISION')
        if len(x['cells'])!=27:raise ValueError('P10QM_MISSING_H8_TERMINALS')
    if previous['ray_source_sha256']!=sha or previous['axis']!=2:
        raise ValueError('P10QM_PRIOR_RAY_SOURCE_MISMATCH')
    gl=json.loads(REFERENCE.read_text())
    if gl['mesh_sha256']!=M8 or gl['quadrature_strategy']!='gl':
        raise ValueError('P10QM_PRIOR_ALGOIM_BENCHMARK_MISMATCH')
    reference=[p for p in gl['partitions'] if p['min_h_one']==8]
    if len(reference)!=1:raise ValueError('P10QM_NO_H8_BENCHMARK')
    raw1=sources[1]['cells'];raw2=sources[2]['cells'];raw128=previous['cells']
    axis_diff=[];axis_volume_diff=[];local_delta=[]
    for i,(a,b,c) in enumerate(zip(raw1,raw2,raw128)):
        if a['index']!=b['index'] or b['index']!=c['index'] or \
           a['group']!=b['group'] or a['h_depth']!=b['h_depth']:
            raise ValueError('P10QM_NOT_THE_SAME_TRUE_CURVED_SUBTET10')
        if not math.isclose(b['orders']['128']['cut_gradient_m3'],
                            c['orders']['128']['cut_gradient_m3'],
                            rel_tol=1e-13,abs_tol=1e-27):
            raise ValueError('P10QM_Q128_NOT_DETERMINISTIC_BETWEEN_INDEPENDENT_RUNS')
        va=a['orders']['256']['cut_gradient_m3']
        vb=b['orders']['256']['cut_gradient_m3']
        axis_diff.append(vb-va)
        axis_volume_diff.append(b['orders']['256']['cut_volume_m3']-
                                a['orders']['256']['cut_volume_m3'])
        local_delta.append({'index':a['index'],'group':a['group'],
             'axis1_q128_to_q256_relative':abs(va-a['orders']['128']['cut_gradient_m3'])/max(abs(va),1e-18),
             'axis2_q128_to_q256_relative':abs(vb-b['orders']['128']['cut_gradient_m3'])/max(abs(vb),1e-18),
             'axis_q256_relative_disagreement':abs(vb-va)/max(abs(vb),1e-18),
             'absolute_axis_difference_m3':abs(vb-va),
             'absolute_axis_volume_difference_m3':abs(axis_volume_diff[-1]),
             'abs_q256_gradient_m3':abs(vb)})
    result_axes=[weight_moments(sources[1]),weight_moments(sources[2])]
    full=max(abs(x['q256_total_m3']) for x in result_axes)
    largest=sorted(local_delta,key=lambda r:r['absolute_axis_difference_m3'],reverse=True)
    outcome={'stage':'P10QM','date_utc':'2026-11-28',
             'mesh_sha256':M8,'source_sha256':sha,
             'scope':'real M8 element 6008 source-case4, one h8 decomposition, all 27 true cut cells',
             'status':'INDEPENDENT_TWO_AXIS_N256_EMPIRICAL_CONVERGENCE_QA_NOT_PHYSICS_CERTIFICATION',
             'axis_metrics':result_axes,
             'q256_two_axis_L1_difference_m3':sum(abs(d) for d in axis_diff),
             'q256_two_axis_L1_relative_to_hybrid':sum(abs(d) for d in axis_diff)/full,
             'q256_two_axis_signed_difference_m3':sum(axis_diff),
             'q256_two_axis_volume_L1_difference_m3':sum(abs(d) for d in axis_volume_diff),
             'worst_axis_differences':largest[:12],
             'all_cut_cells':local_delta,
             'min_required_global_relative_q_L1':1e-6,
             'gl_q8_hybrid_original_m3':reference[0]['q_total_gradient_m3_by_order']['8'],
             'geometric_two_boundary_bernstein_enclosure_m3':reference[0]['residual_multi_bernstein_enclosure_m3'],
             'numeric_double_roots_not_certified_by_interval_arithmetic':True,
             'q_differences_and_axis_spread_are_NOT_rigorous_error_bounds':True,
             'physical_4D_FEM_approved':False,
             'Gmsh_or_CAD_or_FEM_executed':False}
    Path('P10QM_M8_TWO_AXIS_Q256_FINAL_CROSS_AUDIT_QA.json').write_text(json.dumps(outcome,indent=2)+'\n')
    print('P10QM_TWO_AXIS_N256_INDEPENDENT_CROSS_AUDIT_PASS_PHYSICS_FAIL_CLOSED',flush=True)


if __name__=='__main__':main()
