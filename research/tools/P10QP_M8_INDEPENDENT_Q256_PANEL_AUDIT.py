#!/usr/bin/env python3
"""P10QP: independently compare two frozen same-budget composite rules to q256.

This is a 12/30 selected-cell pilot, not a q256 certificate or FEM gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--axis2-q128',type=Path,required=True)
    p.add_argument('--part0',type=Path,required=True)
    p.add_argument('--part1',type=Path,required=True)
    p.add_argument('--posthoc',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sched=json.loads(a.schedule.read_text())
    prev=json.loads(a.axis2_q128.read_text())
    parts=[json.loads(path.read_text()) for path in (a.part0,a.part1)]
    selected=sched['selected_indices_ranked']
    if len(selected)!=12 or sched['training_only_axes']!=[0,1] or \
       sched['unseen_order_to_predict']!=256 or prev['axis']!=2 or \
       len(prev['cells'])!=30 or \
       any(p['part']!=i or p['parts']!=2 or
           p['mesh_sha256']!=sched['mesh_sha256'] or
           p['schedule_sha256']!=hashlib.sha256(a.schedule.read_bytes()).hexdigest() or
           p['axis2_baseline_sha256']!=hashlib.sha256(a.axis2_q128.read_bytes()).hexdigest() or
           p['selected_indices_all']!=selected or
           p['selected_indices_this_part']!=selected[i::2] or
           p['physical_4D_FEM_approved'] or not p['no_Gmsh_no_CAD_no_FEM_no_mesh_change']
           for i,p in enumerate(parts)):
        raise ValueError('P10QP_AUDIT_SOURCE_MISMATCH')
    cells={c['index']:c for p in parts for c in p['cells']}
    prev_cells={c['index']:c for c in prev['cells']}
    if set(cells)!=set(selected) or len(prev_cells)!=30:
        raise ValueError('P10QP_UNEXPECTED_TARGET_CARDINALITY')
    methods=['uniform_q128','panel2_q64','panel4_q32']
    den_g=abs(prev['hybrid_gradient_by_order_m3']['128'])
    den_v=prev['root_physical_volume_m3']
    if den_g<=0 or den_v<=0:
        raise ValueError('P10QP_NONPOSITIVE_DENOMINATOR')
    totals={m:{'gradient_L1_m3':0.,'volume_L1_m3':0.,'gradient_signed_m3':0.,
               'volume_signed_m3':0.,'better_than_uniform_count_gradient':0,
               'better_than_uniform_count_volume':0,'total_transverse_points':0,
               'observed_elapsed_s':0.} for m in methods}
    rows=[]
    for idx in selected:
        row=cells[idx];prev_row=prev_cells[idx]
        uniform=row['uniform_q128_from_previous_independent_run']
        prev_value=prev_row['order']['128']
        for key in ('cut_gradient_m3','cut_volume_m3'):
            if uniform[key]!=prev_value[key]:
                raise ValueError('P10QP_BASELINE_NOT_THE_FROZEN_Q128')
        reference=row['new_methods']['uniform_q256']
        candidate={
            'uniform_q128':uniform,
            'panel2_q64':row['new_methods']['panel2_q64'],
            'panel4_q32':row['new_methods']['panel4_q32']}
        deltas={}
        for m,v in candidate.items():
            if v['transverse_Gauss_points']!=16384:
                raise ValueError('P10QP_UNEQUAL_NODE_BUDGET')
            dg=v['cut_gradient_m3']-reference['cut_gradient_m3']
            dv=v['cut_volume_m3']-reference['cut_volume_m3']
            d={'gradient_signed_vs_q256_m3':dg,'gradient_abs_vs_q256_m3':abs(dg),
               'volume_signed_vs_q256_m3':dv,'volume_abs_vs_q256_m3':abs(dv)}
            deltas[m]=d
            totals[m]['gradient_L1_m3']+=abs(dg)
            totals[m]['volume_L1_m3']+=abs(dv)
            totals[m]['gradient_signed_m3']+=dg
            totals[m]['volume_signed_m3']+=dv
            totals[m]['total_transverse_points']+=16384
            if m!='uniform_q128':
                totals[m]['observed_elapsed_s']+=v['elapsed_s']
                totals[m]['better_than_uniform_count_gradient']+=int(abs(dg)<abs(deltas['uniform_q128']['gradient_signed_vs_q256_m3']))
                totals[m]['better_than_uniform_count_volume']+=int(abs(dv)<abs(deltas['uniform_q128']['volume_signed_vs_q256_m3']))
        rows.append({'index':idx,'group':row['group'],'methods_vs_new_q256':deltas,
                     'reference_q256_gradient_m3':reference['cut_gradient_m3'],
                     'reference_q256_volume_m3':reference['cut_volume_m3'],
                     'reference_q256_elapsed_s':reference['elapsed_s']})
    for m,x in totals.items():
        x['gradient_L1_relative_full_hybrid']=x['gradient_L1_m3']/den_g
        x['volume_L1_relative_original_full_child']=x['volume_L1_m3']/den_v
        x['gradient_abs_signed_relative_full_hybrid']=abs(x['gradient_signed_m3'])/den_g
        x['gradient_cancellation_ratio']=x['gradient_L1_m3']/max(abs(x['gradient_signed_m3']),1e-35)
    best_g=min(methods,key=lambda m:totals[m]['gradient_L1_m3'])
    best_v=min(methods,key=lambda m:totals[m]['volume_L1_m3'])
    unselected=[c for c in prev['cells'] if c['index'] not in selected]
    unselected_64_128=sum(abs(c['order']['128']['cut_gradient_m3']-
                             c['order']['64']['cut_gradient_m3']) for c in unselected)
    selected_64_128=sum(abs(c['order']['128']['cut_gradient_m3']-
                           c['order']['64']['cut_gradient_m3']) for c in prev['cells'] if c['index'] in selected)
    out={'stage':'P10QP','mesh_sha256':prev['mesh_sha256'],'source_case':5,
         'scope':'new independent q256 axis2 on top 12 of 30 real h8 cut cells only',
         'selection_trained_only_axes':[0,1],'new_reference_order':256,
         'uniform_q256_error_bound_certified':False,'equal_cost_nodes_per_candidate_per_cell':16384,
         'source_sha256':{key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in (
             ('schedule',a.schedule),('prior_axis2',a.axis2_q128),('part0',a.part0),('part1',a.part1))},
         'selected_count':len(selected),'unselected_count':len(unselected),
         'training_selected_L1_score_coverage':sched['selected_score_coverage_fraction'],
         'axis2_selected_fraction_of_q64_to_q128_L1':selected_64_128/(unselected_64_128+selected_64_128),
         'axis2_unselected_q64_to_q128_L1_m3':unselected_64_128,
         'full_q128_hybrid_gradient_m3':den_g,'original_child_volume_m3':den_v,
         'metrics':totals,'best_gradient_method_on_selected_vs_q256':best_g,
         'best_volume_method_on_selected_vs_q256':best_v,
         'empirical_1e_minus_6_selected_L1_gradient_pass':{
             m:totals[m]['gradient_L1_relative_full_hybrid']<=1e-6 for m in methods},
         'selected_cells':rows,
         'cannot_claim_full_30_cell_convergence':True,
         'cannot_claim_three_axis_q256_agreement':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True}
    if a.posthoc is not None:
        post=json.loads(a.posthoc.read_text())
        if post['stage']!='P10QP' or post['scope']!='EXPLORATORY_POSTHOC_NOT_FROZEN_PILOT' or \
           post['control_indices']!=[23,31,21,25] or \
           post['schedule_sha256']!=hashlib.sha256(a.schedule.read_bytes()).hexdigest() or \
           post['axis2_q128_sha256']!=hashlib.sha256(a.axis2_q128.read_bytes()).hexdigest() or \
           post['physical_4D_FEM_approved'] or \
           len(post['cells'])!=4 or \
           any(row['index'] in selected for row in post['cells']):
            raise ValueError('P10QP_POSTHOC_NOT_DISTINCT_OR_NOT_LABELED')
        sums={m:{'gradient_L1_m3':0.,'volume_L1_m3':0.,
                 'better_than_uniform_count_gradient':0} for m in methods}
        post_rows=[]
        for row in post['cells']:
            idx=row['index']
            baseline=prev_cells[idx]['order']['128']
            if any(baseline[k]!=row['uniform_q128_from_previous_run'][k]
                   for k in ('cut_gradient_m3','cut_volume_m3')):
                raise ValueError('P10QP_POSTHOC_BASELINE_MISMATCH')
            ref=row['new_methods']['uniform_q256']
            vals={'uniform_q128':baseline,
                  'panel2_q64':row['new_methods']['panel2_q64'],
                  'panel4_q32':row['new_methods']['panel4_q32']}
            delta={m:abs(x['cut_gradient_m3']-ref['cut_gradient_m3'])
                   for m,x in vals.items()}
            for m,v in vals.items():
                if v['transverse_Gauss_points']!=16384:
                    raise ValueError('P10QP_POSTHOC_UNEQUAL_NODE_BUDGET')
                sums[m]['gradient_L1_m3']+=delta[m]
                sums[m]['volume_L1_m3']+=abs(v['cut_volume_m3']-ref['cut_volume_m3'])
                if m!='uniform_q128':
                    sums[m]['better_than_uniform_count_gradient']+=int(delta[m]<delta['uniform_q128'])
            post_rows.append({'index':idx,'gradient_absolute_vs_q256_m3':delta})
        for x in sums.values():
            x['gradient_L1_relative_full_hybrid']=x['gradient_L1_m3']/den_g
            x['volume_L1_relative_original_full_child']=x['volume_L1_m3']/den_v
        out['posthoc_exploratory_control_not_a_validated_policy']={
            'control_indices':[23,31,21,25],
            'control_selection_uses_seen_axis2_q64_q128':True,
            'source_sha256':hashlib.sha256(a.posthoc.read_bytes()).hexdigest(),
            'metrics':sums,'cells':post_rows}
        # All remaining per-cell absolute deviations from q256 are
        # nonnegative. A 16-cell subtotal > 1e-6 *already excludes* a
        # full 30-cell q256-comparator gate without running the last 14.
        lower={m:{
            'tested_cut_cells':16,'uncomputed_cut_cells':14,
            'gradient_L1_lower_bound_vs_q256_m3':totals[m]['gradient_L1_m3']+sums[m]['gradient_L1_m3'],
            'gradient_L1_relative_lower_bound_vs_q256':(
                totals[m]['gradient_L1_m3']+sums[m]['gradient_L1_m3'])/den_g,
            'empirical_full_30_q256_comparator_gate_mathematically_impossible':(
                totals[m]['gradient_L1_m3']+sums[m]['gradient_L1_m3'])/den_g>1e-6
            } for m in methods}
        out['sixteen_cell_L1_lower_bound_for_full_thirty_vs_empirical_q256']=lower
        if not all(x['empirical_full_30_q256_comparator_gate_mathematically_impossible']
                   for x in lower.values()):
            raise ValueError('P10QP_EXPECTED_NEGATIVE_TRANSFER_NOT_REPRODUCED')
    if any(not math.isfinite(x['gradient_L1_m3']) or not math.isfinite(x['volume_L1_m3'])
           for x in totals.values()):
        raise ValueError('P10QP_NONFINITE_QA')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QP_TARGETED_Q256_NEW_REFERENCE_NOT_CERTIFIED')
    for m,x in totals.items():
        print(m,'L1_gradient_norm',f'{x["gradient_L1_relative_full_hybrid"]:.6e}',
              'L1_volume_norm',f'{x["volume_L1_relative_original_full_child"]:.6e}',
              'nodes',x['total_transverse_points'])
    print('P10QP_BEST_METHODS',best_g,best_v)
    if a.posthoc is not None:
        for m,x in out['posthoc_exploratory_control_not_a_validated_policy']['metrics'].items():
            print('P10QP_POSTHOC',m,'L1_gradient_norm',f'{x["gradient_L1_relative_full_hybrid"]:.6e}')
        for m,x in out['sixteen_cell_L1_lower_bound_for_full_thirty_vs_empirical_q256'].items():
            print('P10QP_16_OF_30_LOWER_BOUND',m,
                  f'{x["gradient_L1_relative_lower_bound_vs_q256"]:.6e}',
                  'FULL_30_CANNOT_PASS')
    print('P10QP_FULL_30_CELLS_NOT_CERTIFIED_NO_FEM')


if __name__=='__main__':main()
