#!/usr/bin/env python3
"""P10QO: independent three-axis L1 convergence audit on new real M8 case5.

Never equate a three-direction numerical agreement to a certified error bound.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--axis0', type=Path, required=True)
    p.add_argument('--axis1', type=Path, required=True)
    p.add_argument('--axis2', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    inputs = [a.axis0, a.axis1, a.axis2]
    data = [json.loads(path.read_text()) for path in inputs]
    first = data[0]
    root_grad = abs(first['root_exact_full_gradient_m3'])
    root_vol = first['root_physical_volume_m3']
    if root_grad <= 0 or root_vol <= 0:
        raise ValueError('P10QO_ZERO_DENOMINATOR')
    for axis, row in enumerate(data):
        if row['stage'] != 'P10QO' or row['source_case'] != 5 or row['axis'] != axis or \
           row['mesh_sha256'] != '40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d' or \
           row['physical_4D_FEM_approved'] or not row['no_Gmsh_no_CAD_no_FEM_no_mesh_change'] or \
           row['orders'] != [16, 32, 64, 128] or len(row['cells']) != 30 or \
           any(row[key] != first[key] for key in (
               'child_input_sha256', 'source_case', 'original_element_id', 'sector',
               'root_physical_volume_m3', 'root_exact_full_gradient_m3',
               'exact_inside_gradient_m3', 'exact_inside_volume_m3', 'group_counts')):
            raise ValueError(f'P10QO_SOURCE_OR_AXIS_MISMATCH_{axis}')
        if [(c['index'], c['group']) for c in row['cells']] != \
           [(c['index'], c['group']) for c in first['cells']]:
            raise ValueError('P10QO_CELL_ORDER_OR_GROUP_MISMATCH')
        if row['group_counts']['multi'] != 7 or row['group_counts']['one'] != 23:
            raise ValueError('P10QO_UNEXPECTED_REAL_M8_CASE5_TOPOLOGY')
        for c in row['cells']:
            if max(c['full_gradient_relative_error'], c['full_volume_relative_error']) > 1e-10:
                raise ValueError('P10QO_CURVED_FULL_MOMENT_NOT_VALIDATED')
        for n in row['orders']:
            hybrid_gradient = row['exact_inside_gradient_m3'] + sum(
                c['order'][str(n)]['cut_gradient_m3'] for c in row['cells'])
            hybrid_volume = row['exact_inside_volume_m3'] + sum(
                c['order'][str(n)]['cut_volume_m3'] for c in row['cells'])
            if not math.isclose(hybrid_gradient, row['hybrid_gradient_by_order_m3'][str(n)],
                                rel_tol=2e-14, abs_tol=1e-28) or \
               not math.isclose(hybrid_volume, row['hybrid_volume_by_order_m3'][str(n)],
                                rel_tol=2e-14, abs_tol=1e-28):
                raise ValueError('P10QO_RECOMPUTED_HYBRID_SUM_MISMATCH')
        last_l1 = sum(abs(c['order']['128']['cut_gradient_m3'] -
                          c['order']['64']['cut_gradient_m3']) for c in row['cells'])
        if not math.isclose(last_l1, row['q_last_pair_L1_gradient_m3'],
                            rel_tol=2e-14, abs_tol=1e-28):
            raise ValueError('P10QO_RECOMPUTED_NONCANCELLED_L1_MISMATCH')
    within = []
    per_order = []
    for n0, n1 in [(16, 32), (32, 64), (64, 128)]:
        for axis, row in enumerate(data):
            cells = row['cells']
            dif = [c['order'][str(n1)]['cut_gradient_m3'] - c['order'][str(n0)]['cut_gradient_m3'] for c in cells]
            vd = [c['order'][str(n1)]['cut_volume_m3'] - c['order'][str(n0)]['cut_volume_m3'] for c in cells]
            scale = abs(row['hybrid_gradient_by_order_m3'][str(n1)])
            r = {'axis': axis, 'q_low': n0, 'q_high': n1,
                 'signed_gradient_change_m3': sum(dif), 'L1_gradient_change_m3': sum(map(abs, dif)),
                 'L1_gradient_relative_hybrid': sum(map(abs, dif))/scale,
                 'L1_volume_change_m3': sum(map(abs, vd)),
                 'L1_volume_relative_original_full_child': sum(map(abs, vd))/root_vol,
                 'largest_cell_gradient_delta': [
                     {'index': cells[i]['index'], 'absolute_delta_m3': abs(dif[i]),
                      'group': cells[i]['group']} for i in sorted(range(len(cells)),key=lambda i:abs(dif[i]),reverse=True)[:5]]}
            within.append(r)
    for n in first['orders']:
        axis_pairs = []
        for ai, bi in itertools.combinations(range(3), 2):
            ra, rb = data[ai], data[bi]
            dif = [a1['order'][str(n)]['cut_gradient_m3'] - b1['order'][str(n)]['cut_gradient_m3']
                   for a1,b1 in zip(ra['cells'],rb['cells'])]
            vd = [a1['order'][str(n)]['cut_volume_m3'] - b1['order'][str(n)]['cut_volume_m3']
                  for a1,b1 in zip(ra['cells'],rb['cells'])]
            normal = max(abs(ra['hybrid_gradient_by_order_m3'][str(n)]),
                         abs(rb['hybrid_gradient_by_order_m3'][str(n)]))
            axis_pairs.append({'axes': [ai,bi], 'signed_gradient_difference_m3':sum(dif),
                               'L1_gradient_difference_m3':sum(map(abs,dif)),
                               'L1_gradient_relative_hybrid':sum(map(abs,dif))/normal,
                               'L1_volume_difference_m3':sum(map(abs,vd)),
                               'L1_volume_relative_original_full_child':sum(map(abs,vd))/root_vol,
                               'largest_cell_gradient_delta': [
                                   {'index':ra['cells'][i]['index'],'absolute_delta_m3':abs(dif[i]),
                                    'group':ra['cells'][i]['group']}
                                   for i in sorted(range(len(dif)),key=lambda i:abs(dif[i]),reverse=True)[:5]]})
        per_order.append({'order':n,'axis_pair_comparisons':axis_pairs})
    end = [x for x in within if x['q_low']==64]
    last=per_order[-1]['axis_pair_comparisons']
    tolerance=1e-6
    # Both fields must meet target; L1 prevents sign cancellation.
    passes={
        'q64_to_128_gradient_all_three_axes':all(x['L1_gradient_relative_hybrid']<=tolerance for x in end),
        'q64_to_128_volume_all_three_axes':all(x['L1_volume_relative_original_full_child']<=tolerance for x in end),
        'q128_gradient_all_three_axis_pairs':all(x['L1_gradient_relative_hybrid']<=tolerance for x in last),
        'q128_volume_all_three_axis_pairs':all(x['L1_volume_relative_original_full_child']<=tolerance for x in last),
    }
    maxima={'last_pair_gradient_L1_relative':max(x['L1_gradient_relative_hybrid'] for x in end),
            'last_pair_volume_L1_relative':max(x['L1_volume_relative_original_full_child'] for x in end),
            'cross_axis_gradient_L1_relative':max(x['L1_gradient_relative_hybrid'] for x in last),
            'cross_axis_volume_L1_relative':max(x['L1_volume_relative_original_full_child'] for x in last)}
    out={'stage':'P10QO','scope':'heldout true-curved M8 case5, 3 axes, no physical FEM',
         'mesh_sha256':first['mesh_sha256'],'source_case':5,
         'original_element_id':first['original_element_id'],
         'cell_count':len(first['cells']),'counts':first['group_counts'],
         'source_axis_sha256':{str(i):hashlib.sha256(f.read_bytes()).hexdigest() for i,f in enumerate(inputs)},
         'root_exact_full_gradient_m3':first['root_exact_full_gradient_m3'],
         'root_physical_volume_m3':root_vol,
         'uniform_quadrature_orders':first['orders'],
         'within_axis_order_refinement':within,
         'pairwise_cross_axis_comparisons':per_order,
         'empirical_relative_L1_target':tolerance,
         'four_independent_empirical_gate_results':passes,
         'empirical_joint_pass':all(passes.values()),
         'worst_relative_L1':maxima,
         'no_strict_error_enclosure':True,
         'physical_4D_FEM_approved':False,
         'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True}
    if not all(math.isfinite(x) for x in maxima.values()):
        raise ValueError('P10QO_NONFINITE_AUDIT_METRIC')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QO_HELDOUT_NEW_CASE5_EMPIRICAL_'+('PASS' if out['empirical_joint_pass'] else 'FAIL'))
    print(json.dumps({'checks':passes,'worst_relative_L1':maxima},indent=2))
    print('P10QO_NO_RIGOROUS_ERROR_BOUND_NO_FEM')


if __name__=='__main__':
    main()
