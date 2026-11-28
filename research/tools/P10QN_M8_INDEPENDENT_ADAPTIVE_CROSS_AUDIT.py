#!/usr/bin/env python3
"""P10QN: cross-audit initial negative and tightened adaptive policies.

Recompute the L1/signed selected integrals and sample-point costs from
raw real-M8 low and held-out high quadrature data.  Check the third-axis
result separately; never mistake empirical agreement for a certificate.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

M8='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
R1=Path('P10QN_M8_ADAPTIVE_ORDER_HELDOUT_QA.json')
R2=Path('P10QN_M8_ADAPTIVE_ORDER_MARGIN06_QA.json')
THIRD=Path('P10QN_M8_THIRD_AXIS_ADAPTIVE_VALIDATION_QA.json')
UNIFORM=Path('P10QN_M8_UNIFORM_Q128_THREE_AXIS_QA.json')
AXIS0=Path('P10QN_M8_FULL_H8_RAY_AXIS0_Q128_QA.json')
LOW={1:Path('P10QN_M8_FULL_H8_RAY_AXIS1_LOW_QA.json'),
     2:Path('P10QL_M8_FULL_H8_RAY_AXIS2_QA.json')}
HIGH={1:Path('P10QM_M8_FULL_H8_RAY_AXIS1_Q256_QA.json'),
      2:Path('P10QM_M8_FULL_H8_RAY_AXIS2_Q256_QA.json')}


def read(f):
    x=json.loads(f.read_text())
    if x['mesh_sha256']!=M8 or x.get('physical_4D_FEM_approved',False):
        raise ValueError('P10QN_CROSS_AUDIT_WRONG_M8_OR_ILLEGAL_FEM')
    return x


def validate_policy(p,low,high):
    assigned=p['locked_schedule']['orders_in_source_order']
    if len(assigned)!=27 or any(n not in (64,128) for n in assigned):
        raise ValueError('P10QN_CROSS_AUDIT_BAD_ADAPTIVE_SCHEDULE')
    out=[]
    for axis in (1,2):
        grad_delta=[];volume_delta=[]
        for i,order in enumerate(assigned):
            selected=(low[axis] if order==64 else high[axis])['cells'][i]['orders'][str(order)]
            ref=high[axis]['cells'][i]['orders']['256']
            grad_delta.append(selected['cut_gradient_m3']-ref['cut_gradient_m3'])
            volume_delta.append(selected['cut_volume_m3']-ref['cut_volume_m3'])
        stage=p['heldout_axis_validation'][axis-1]
        gL1=sum(abs(d) for d in grad_delta)
        vL1=sum(abs(d) for d in volume_delta)
        if not math.isclose(gL1,stage['adaptive_vs_q256_L1_absolute_m3'],
                            rel_tol=2e-12,abs_tol=1e-27) or \
           not math.isclose(sum(grad_delta),stage['adaptive_vs_q256_signed_m3'],
                            rel_tol=2e-12,abs_tol=1e-27) or \
           not math.isclose(vL1,stage['cut_volume_L1_error_m3'],
                            rel_tol=2e-12,abs_tol=1e-27):
            raise ValueError('P10QN_CROSS_AUDIT_SIGNED_OR_L1_NOT_REPRODUCIBLE')
        out.append({'axis':axis,'gradient_L1_m3':gL1,'volume_L1_m3':vL1})
    cost=27*(16**2+32**2+64**2)+assigned.count(128)*128**2
    if cost!=p['transverse_sample_points_adaptive_including_preflight']:
        raise ValueError('P10QN_CROSS_AUDIT_ADAPTIVE_COST_MISREPORTED')
    # Recompute cross-axis selected values, not just q256-corrected errors.
    diff_g=[];diff_v=[]
    for i,order in enumerate(assigned):
        data=[]
        for axis in (1,2):
            data.append((low[axis] if order==64 else high[axis])['cells'][i]['orders'][str(order)])
        diff_g.append(data[0]['cut_gradient_m3']-data[1]['cut_gradient_m3'])
        diff_v.append(data[0]['cut_volume_m3']-data[1]['cut_volume_m3'])
    if not math.isclose(sum(abs(d) for d in diff_g),p['selected_gradient_cross_axis_L1_m3'],
                        rel_tol=2e-12,abs_tol=1e-27) or \
       not math.isclose(sum(abs(d) for d in diff_v),p['selected_cut_volume_cross_axis_L1_m3'],
                        rel_tol=2e-12,abs_tol=1e-27):
        raise ValueError('P10QN_CROSS_AUDIT_CROSS_AXIS_L1_NOT_REPRODUCIBLE')
    return {'margin':p['locked_schedule']['design_fraction_of_target'],
            'q128_cells':assigned.count(128),'q64_cells':assigned.count(64),
            'total_actual_sample_points':cost,
            'cost_saving_factor_vs_q256':(27*256**2)/cost,
            'per_axis':out,
            'cross_axis_gradient_L1_m3':sum(abs(d) for d in diff_g),
            'cross_axis_volume_L1_m3':sum(abs(d) for d in diff_v),
            'passes_gradient_full_child_volume_cross_axis_1e_minus_6':
              p['selected_cross_axis_grad_and_volume_pass_global_1e_minus_6']}


def main():
    initial=read(R1);tightened=read(R2);third=read(THIRD);uniform=read(UNIFORM)
    axis0=read(AXIS0)
    low={a:read(p) for a,p in LOW.items()}
    high={a:read(p) for a,p in HIGH.items()}
    if initial['locked_schedule']['design_fraction_of_target']!=.75 or \
       tightened['locked_schedule']['design_fraction_of_target']!=.6 or \
       initial['selected_cross_axis_grad_and_volume_pass_global_1e_minus_6'] or \
       not tightened['selected_cross_axis_grad_and_volume_pass_global_1e_minus_6']:
        raise ValueError('P10QN_CROSS_AUDIT_INITIAL_FAIL_OR_TIGHTENED_PASS_MISSING')
    if third['locked_schedule_reference']!=R2.name or \
       [r['selected_n'] for r in third['cells_axis0']]!= \
       tightened['locked_schedule']['orders_in_source_order'] or \
       third['physical_4D_FEM_approved']:
        raise ValueError('P10QN_CROSS_AUDIT_THIRD_AXIS_NOT_SAME_LOCKED_SCHEDULE')
    models=[validate_policy(p,low,high) for p in (initial,tightened)]
    for v in third['independent_cross_validation']:
        if v['reference_axis'] not in (1,2) or not math.isfinite(v['axis0_adaptive_vs_axis_q256_gradient_L1_relative']):
            raise ValueError('P10QN_CROSS_AUDIT_THIRD_AXIS_INVALID')
    if third['status']!='THIRD_AXIS_STRICT_EMPIRICAL_L1_FAIL' or \
       uniform['status']!='UNIFORM_Q128_THREE_AXIS_GLOBAL_EMPIRICAL_PASS' or \
       not uniform['both_gradient_and_full_child_volume_global_1e_minus_6_pass']:
        raise ValueError('P10QN_MISSING_NEGATIVE_ADAPTIVE_OR_POSITIVE_UNIFORM_EVIDENCE')
    raw={0:axis0,1:high[1],2:high[2]}
    checked=[]
    for pair in ((0,1),(0,2),(1,2)):
        a,b=(raw[i]['cells'] for i in pair)
        grad=sum(abs(x['orders']['128']['cut_gradient_m3']-
                     y['orders']['128']['cut_gradient_m3']) for x,y in zip(a,b))
        vol=sum(abs(x['orders']['128']['cut_volume_m3']-
                    y['orders']['128']['cut_volume_m3']) for x,y in zip(a,b))
        reported=next((r for r in uniform['cross_axis_q128_L1'] if r['axes']==list(pair)),None)
        if reported is None or not math.isclose(grad,reported['gradient_L1_m3'],
                                               rel_tol=2e-12,abs_tol=1e-27) or \
           not math.isclose(vol,reported['volume_L1_m3'],rel_tol=2e-12,abs_tol=1e-27):
            raise ValueError('P10QN_UNIFORM_THREE_AXIS_L1_NOT_REPRODUCIBLE')
        checked.append({'axes':pair,'gradient_L1_m3':grad,
                        'volume_L1_m3':vol})
    result={'stage':'P10QN','date_utc':'2026-11-28','mesh_sha256':M8,
            'status':'NEGATIVE_ADAPTIVE_THIRD_AXIS_AND_POSITIVE_UNIFORM_Q128_PILOT_QA',
            'initial_margin_075_outcome':models[0],
            'tightened_margin_06_outcome':models[1],
            'third_axis_status':third['status'],
            'third_axis_heldout':third['independent_cross_validation'],
            'uniform_q128_3axis_status':uniform['status'],
            'uniform_q128_recalculated_cross_axis_L1':checked,
            'recommended_interim_P10QN_pilot_quadrature':'uniform q128 across all 27 M8 cut cells; no physics authority',
            'uniform_q128_transverse_points_per_axis':27*128**2,
            'uniform_q256_transverse_points_per_axis':27*256**2,
            'third_axis_heldout_data_was_not_used_for_order_selection':True,
            'cut_volume_relative_to_cut_volume_remains_stricter_than_full_element_budget':True,
            'contraction_model_is_empirical_not_rigorous_error_certification':True,
            'all_48_spherical_bins_verified':False,
            'physical_4D_FEM_approved':False,'mesh_Gmsh_CAD_FEM_executed':False,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    Path('P10QN_M8_INDEPENDENT_ADAPTIVE_FINAL_CROSS_AUDIT_QA.json').write_text(
        json.dumps(result,indent=2)+'\n')
    print('P10QN_INDEPENDENT_ADAPTIVE_AUDIT_PASS_PHYSICS_FAIL_CLOSED',flush=True)


if __name__=='__main__':main()
