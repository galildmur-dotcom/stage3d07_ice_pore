#!/usr/bin/env python3
"""P10QN: select per-cell transverse q64/q128 using only axis2 q16/q32/q64.

Quarantine the *previously calculated* q256 along both axes until the
selection is fixed.  Calibrate empirical geometric-order decay from q16/32/64,
use a factor-2 protective multiplier, and solve the absolute L1 budget by
deterministically promoting largest indicators.  Audit against two held-out
q256 integrations after the schedule has been locked, never as a selector.

Not a directed-rounded error certificate; no CAD/Gmsh/mesh/FEM work.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import argparse

M8='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
TRAIN=Path('P10QL_M8_FULL_H8_RAY_AXIS2_QA.json')
HELD_LOW=Path('P10QN_M8_FULL_H8_RAY_AXIS1_LOW_QA.json')
HOLD={1:Path('P10QM_M8_FULL_H8_RAY_AXIS1_Q256_QA.json'),
      2:Path('P10QM_M8_FULL_H8_RAY_AXIS2_Q256_QA.json')}
DEFAULT_OUTPUT=Path('P10QN_M8_ADAPTIVE_ORDER_HELDOUT_QA.json')

TARGET_REL=1e-6
DESIGN_MARGIN=.75
SAFETY_MULTIPLIER=2.


def read(file):
    j=json.loads(file.read_text())
    if j['mesh_sha256']!=M8 or j['stage'] not in ('P10QL','P10QM') or \
       j.get('physical_4D_FEM_approved',False) or j.get('cut_full_4D_FEM_ready',False):
        raise ValueError('P10QN_BAD_M8_PIN_OR_PHYSICS_AUTHORITY')
    if j['axis'] not in (1,2) or len(j['cells'])!=27 or \
       j['ray_source_sha256']!=hashlib.sha256(Path('P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE.py').read_bytes()).hexdigest():
        raise ValueError('P10QN_INCOMPLETE_DIFFERENT_OR_UNCHECKED_RAY_SOURCE')
    return j


def series_for(rows,q):
    return [c['orders'][str(q)]['cut_gradient_m3'] for c in rows]


def make_schedule(training,design_margin):
    if training['axis']!=2 or training['transverse_Gauss_orders']!=[16,32,64]:
        raise ValueError('P10QN_TRAINING_MUST_CONTAIN_ONLY_Q16_Q32_Q64')
    rows=training['cells']
    low16,low32,low64=(series_for(rows,q) for q in (16,32,64))
    d16=[abs(b-a) for a,b in zip(low16,low32)]
    d32=[abs(b-a) for a,b in zip(low32,low64)]
    ratio=sum(d32)/max(sum(d16),1e-30)
    # A global empirical contraction factor: cap from below and above so that
    # a vanishing initial difference never implies a zero future error.
    ratio=max(.05,min(.5,ratio))
    c64=SAFETY_MULTIPLIER*ratio/(1-ratio)
    c128=SAFETY_MULTIPLIER*ratio*ratio/(1-ratio)
    total=training['ray_hybrid_gradient_m3_by_order']['64']
    budget=TARGET_REL*design_margin*abs(total)
    ranking=sorted(range(27),key=lambda i:(-d32[i],rows[i]['index']))
    assigned=[64]*27

    def predicted():
        return sum(d32[i]*(c64 if assigned[i]==64 else c128) for i in range(27))

    if predicted()>budget:
        for j in ranking:
            assigned[j]=128
            if predicted()<=budget:break
    if predicted()>budget:
        raise ValueError('P10QN_Q128_CANNOT_MEET_PREDECLARED_PREDICTED_BUDGET')
    return {'training_axis':2,
            'model':'global contraction L1(q32,q64)/L1(q16,q32), safety factor 2',
            'raw_empirical_contraction_ratio':sum(d32)/sum(d16),
            'bounded_contraction_ratio':ratio,
            'prediction_multiplier_64':c64,
            'prediction_multiplier_128':c128,
            'target_relative_global_L1':TARGET_REL,
            'design_fraction_of_target':design_margin,
            'fixed_budget_m3':budget,
            'predicted_L1_remainder_m3':predicted(),
            'predicted_relative_L1':predicted()/abs(total),
            'selected_indices_q128':[rows[i]['index'] for i in range(27) if assigned[i]==128],
            'selected_indices_q64':[rows[i]['index'] for i in range(27) if assigned[i]==64],
            'orders_in_source_order':assigned,
            'training_d16_L1_m3':sum(d16),
            'training_d32_L1_m3':sum(d32),
            'training_cell_indicators_m3':[{'index':rows[i]['index'],
                                          'd16_32':d16[i],
                                          'd32_64':d32[i]} for i in range(27)]}


def validate_schedule(schedule,low,high):
    if low['axis']!=high['axis'] or low['axis'] not in (1,2) or \
       low['transverse_Gauss_orders']!=[16,32,64] or \
       high['transverse_Gauss_orders']!=[128,256]:
        raise ValueError('P10QN_INVALID_HELDOUT_RESOLUTIONS')
    selections=[];ref=[];valselected=[];vol_ref=[];errors=[];volume_errors=[]
    assigned=schedule['orders_in_source_order']
    inside=high['fully_inside_exact_gradient_m3']
    for i,(a,b) in enumerate(zip(low['cells'],high['cells'])):
        if a['index']!=b['index'] or a['group']!=b['group'] or \
           a['h_depth']!=b['h_depth']:
            raise ValueError('P10QN_HELDOUT_SOURCE_H8_PARTITION_MISMATCH')
        order=assigned[i]
        val=(a if order==64 else b)['orders'][str(order)]
        true=b['orders']['256']
        selections.append(val['cut_gradient_m3'])
        ref.append(true['cut_gradient_m3'])
        valselected.append(val['cut_volume_m3'])
        vol_ref.append(true['cut_volume_m3'])
        errors.append(val['cut_gradient_m3']-true['cut_gradient_m3'])
        volume_errors.append(val['cut_volume_m3']-true['cut_volume_m3'])
    hybrid=inside+sum(selections)
    q256=inside+sum(ref)
    if not math.isclose(q256,high['ray_hybrid_gradient_m3_by_order']['256'],
                        rel_tol=3e-12,abs_tol=1e-26):
        raise ValueError('P10QN_Q256_REFERENCE_TOTAL_NOT_REPRODUCED')
    l1=sum(abs(x) for x in errors)
    total_target=max(abs(q256),1e-25)
    return {'heldout_axis':high['axis'],
            'adaptive_gradient_m3':hybrid,'uniform_q256_gradient_m3':q256,
            'adaptive_vs_q256_L1_absolute_m3':l1,
            'adaptive_vs_q256_L1_relative':l1/total_target,
            'adaptive_vs_q256_signed_m3':sum(errors),
            'cut_volume_L1_error_m3':sum(abs(x) for x in volume_errors),
            'cut_volume_L1_relative':sum(abs(x) for x in volume_errors)/
                                     max(sum(abs(x) for x in vol_ref),1e-25),
            'empirical_L1_target_pass':l1/total_target<=TARGET_REL,
            'per_cell_actual_vs_q256_m3':[
                {'index':c['index'],'group':c['group'],'selected_n':assigned[i],
                 'absolute_gradient_delta_m3':abs(errors[i]),
                 'signed_gradient_delta_m3':errors[i],
                 'absolute_volume_delta_m3':abs(volume_errors[i])}
                 for i,c in enumerate(low['cells'])]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--design-margin',type=float,default=DESIGN_MARGIN)
    p.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    args=p.parse_args()
    if not .1<=args.design_margin<=.95:
        raise ValueError('P10QN_INVALID_APRIORI_DESIGN_MARGIN')
    # Phase A: train using ONLY q16/32/64 on axis 2. Lock schedule before
    # fetching *any* q128/256 or axis-1 values.
    train=read(TRAIN)
    schedule=make_schedule(train,args.design_margin)
    print('P10QN_ADAPTIVE_SCHEDULE_LOCKED',
          'q128=',len(schedule['selected_indices_q128']),
          'q64=',len(schedule['selected_indices_q64']),
          'predicted_rel=',format(schedule['predicted_relative_L1'],'.5g'),flush=True)

    # Phase B: strictly held-out q256 for both axes; axis1 q16/32/64 was
    # never loaded during training or allocation.
    low={1:read(HELD_LOW),2:train}
    high={axis:read(path) for axis,path in HOLD.items()}
    results=[validate_schedule(schedule,low[a],high[a]) for a in (1,2)]
    assigned=schedule['orders_in_source_order']
    # Real per-cell integration work includes preflight q16/32/64 for all;
    # then q128 is computed only for cells assigned that order.
    preflight=len(assigned)*(16**2+32**2+64**2)
    selective=assigned.count(128)*128**2
    adaptive_points=preflight+selective
    reference_points=len(assigned)*256**2
    q128_points=len(assigned)*128**2
    cross_l1=sum(abs(a['signed_gradient_delta_m3']-b['signed_gradient_delta_m3'])
                 for a,b in zip(results[0]['per_cell_actual_vs_q256_m3'],
                                results[1]['per_cell_actual_vs_q256_m3']))
    def selected_cell(a,i):
        order=assigned[i]
        source=low[a] if order==64 else high[a]
        return source['cells'][i]['orders'][str(order)]
    selected_axis_L1=sum(abs(selected_cell(1,i)['cut_gradient_m3']-
                             selected_cell(2,i)['cut_gradient_m3']) for i in range(27))
    selected_volume_axis_L1=sum(abs(selected_cell(1,i)['cut_volume_m3']-
                                    selected_cell(2,i)['cut_volume_m3']) for i in range(27))
    source_root_volume=6.22294002408442e-14
    q256_full_gradient=max(abs(r['uniform_q256_gradient_m3']) for r in results)
    qa={'stage':'P10QN','mesh_sha256':M8,'date_utc':'2026-11-28',
        'scope':'exact same h8 true curved M8 case4 27 cut cells',
        'algorithm':'heldout independent two-axis adaptive q64/128 selection, training only axis2 16/32/64',
        'locked_schedule':schedule,
        'heldout_axis_validation':results,
        'cross_axis_selected_minus_q256_L1_difference_m3':cross_l1,
        'selected_gradient_cross_axis_L1_m3':selected_axis_L1,
        'selected_gradient_cross_axis_L1_relative_to_hybrid':selected_axis_L1/q256_full_gradient,
        'selected_cut_volume_cross_axis_L1_m3':selected_volume_axis_L1,
        'selected_cut_volume_cross_axis_L1_relative_to_original_child_volume':
            selected_volume_axis_L1/source_root_volume,
        'selected_cut_volume_L1_relative_to_original_child_volume_by_axis':[
            r['cut_volume_L1_error_m3']/source_root_volume for r in results],
        'transverse_sample_points_adaptive_including_preflight':adaptive_points,
        'transverse_sample_points_uniform_q128':q128_points,
        'transverse_sample_points_uniform_q256':reference_points,
        'uniform_q256_to_adaptive_cost_factor':reference_points/adaptive_points,
        'uniform_q128_to_adaptive_cost_factor':q128_points/adaptive_points,
        'both_heldout_axes_pass_empirical_global_L1_1e_minus_6':all(
            v['empirical_L1_target_pass'] for v in results),
        'selected_cross_axis_grad_and_volume_pass_global_1e_minus_6':
            selected_axis_L1/q256_full_gradient<=TARGET_REL and
            selected_volume_axis_L1/source_root_volume<=TARGET_REL,
        'selected_orders_are_empirical_not_directed_rounding':True,
        'no_global_4D_physical_integral_certification':True,
        'FEM_or_Gmsh_or_CAD_executed':False,'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(qa,indent=2)+'\n')
    print('P10QN_HELDOUT_ADAPTIVE_QA_COMPLETE_PHYSICS_NOT_CERTIFIED',flush=True)


if __name__=='__main__':main()
