#!/usr/bin/env python3
"""P10QQ: independent L1/volume/node-cost audit for the geometry-only pilot."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

TEST=(26,20,31,21,23,10,8,38)
PIN='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--part0',type=Path,required=True)
    p.add_argument('--part1',type=Path,required=True)
    p.add_argument('--previous-q128',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    parts=[json.loads(path.read_text()) for path in (a.part0,a.part1)]
    q=json.loads(a.previous_q128.read_text())
    baseline={row['index']:row for row in q['cells']}
    if q['mesh_sha256']!=PIN or q['axis']!=2 or len(baseline)!=30 or \
       q['physical_4D_FEM_approved'] or \
       any(row['stage']!='P10QQ' or row['mesh_sha256']!=PIN or row['axis']!=2 or \
           row['part']!=i or row['parts']!=2 or row['all_frozen_test_indices']!=list(TEST) or \
           row['physical_4D_FEM_approved'] or len(row['cells'])!=4 or \
           [x['index'] for x in row['cells']]!=list(TEST[i::2]) or \
           row['frozen_parameters']!=parts[0]['frozen_parameters']
           for i,row in enumerate(parts)):
        raise ValueError('P10QQ_AUDIT_INVALID_FROZEN_REAL_M8_SCOPE')
    rows={row['index']:row for part in parts for row in part['cells']}
    if set(rows)!=set(TEST):raise ValueError('P10QQ_WRONG_OR_DUPLICATE_TEST_CELLS')
    den_g=abs(q['hybrid_gradient_by_order_m3']['128'])
    den_v=q['root_physical_volume_m3']
    result_rows=[]
    for idx in TEST:
        r=rows[idx]
        prev=baseline[idx]['order']['128']
        if r['uniform_q128_from_P10QO']['cut_gradient_m3']!=prev['cut_gradient_m3'] or \
           r['uniform_q128_from_P10QO']['cut_volume_m3']!=prev['cut_volume_m3'] or \
           r['adaptive_cut']['transverse_Gauss_points']>16384 or \
           not 0<r['leaf_count']<=256 or \
           r['adaptive_full_gradient_relative_error']>1e-10 or \
           r['adaptive_full_volume_relative_error']>1e-10:
            raise ValueError('P10QQ_ADAPTIVE_FULL_MOMENT_OR_BUDGET_WRONG')
        u=r['uniform_q128_from_P10QO'];g=r['adaptive_cut'];ref=r['uniform_q256_reference']
        result_rows.append({'index':idx,'q256_origin':r['q256_reference_origin'],
            'leaf_count':r['leaf_count'],'unresolved_topology_count':r['unresolved_max_depth_topology_count'],
            'topology_probes':r['topology_probe_count'],
            'topology_build_elapsed_s':r['topology_build_elapsed_s'],
            'adaptive_cut_elapsed_s':g['elapsed_s'],
            'adaptive_transverse_points':g['transverse_Gauss_points'],
            'uniform_abs_gradient_vs_q256_m3':abs(u['cut_gradient_m3']-ref['cut_gradient_m3']),
            'adaptive_abs_gradient_vs_q256_m3':abs(g['cut_gradient_m3']-ref['cut_gradient_m3']),
            'uniform_abs_volume_vs_q256_m3':abs(u['cut_volume_m3']-ref['cut_volume_m3']),
            'adaptive_abs_volume_vs_q256_m3':abs(g['cut_volume_m3']-ref['cut_volume_m3']),
            'improved_gradient':abs(g['cut_gradient_m3']-ref['cut_gradient_m3'])<abs(u['cut_gradient_m3']-ref['cut_gradient_m3'])})
    groups={'all_8':result_rows,
            'old_q256_6':[x for x in result_rows if x['q256_origin']=='P10QP_PREVIOUS_Q256_REFERENCE'],
            'fresh_q256_2':[x for x in result_rows if x['q256_origin']=='P10QQ_NEW_Q256_HELDOUT_ORDER']}
    if len(groups['old_q256_6'])!=6 or len(groups['fresh_q256_2'])!=2:
        raise ValueError('P10QQ_HELDOUT_REFERENCE_COUNT_MISMATCH')
    metrics={}
    for key,cells in groups.items():
        au=sum(x['adaptive_abs_gradient_vs_q256_m3'] for x in cells)
        un=sum(x['uniform_abs_gradient_vs_q256_m3'] for x in cells)
        metrics[key]={'cell_count':len(cells),'uniform_gradient_L1_relative_hybrid':un/den_g,
                      'adaptive_gradient_L1_relative_hybrid':au/den_g,
                      'uniform_volume_L1_relative_full_child':sum(x['uniform_abs_volume_vs_q256_m3'] for x in cells)/den_v,
                      'adaptive_volume_L1_relative_full_child':sum(x['adaptive_abs_volume_vs_q256_m3'] for x in cells)/den_v,
                      'adaptive_to_uniform_gradient_L1_ratio':au/max(un,1e-40),
                      'gradient_improved_count':sum(x['improved_gradient'] for x in cells),
                      'uniform_transverse_points':len(cells)*16384,
                      'adaptive_transverse_points':sum(x['adaptive_transverse_points'] for x in cells),
                      'topology_probe_evaluations_not_in_Gauss_point_count':sum(x['topology_probes'] for x in cells),
                      'observed_topology_build_elapsed_s':sum(x['topology_build_elapsed_s'] for x in cells),
                      'observed_adaptive_cut_elapsed_s':sum(x['adaptive_cut_elapsed_s'] for x in cells),
                      'leaf_count_total':sum(x['leaf_count'] for x in cells),
                      'unresolved_topology_panel_count':sum(x['unresolved_topology_count'] for x in cells)}
    out={'stage':'P10QQ','scope':'one frozen topology probe rule; empirical q256 comparison NOT root cert',
         'mesh_sha256':PIN,'original_element_id':5865,'axis':2,
         'source_sha256':{k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in (
             ('part0',a.part0),('part1',a.part1),('baseline',a.previous_q128))},
         'frozen_test_indices':list(TEST),
         'frozen_geometry_parameters':parts[0]['frozen_parameters'],
         'metrics':metrics,'cells':result_rows,
         'pilot_8_gradient_q256_comparator_target_1e_minus_6_pass':(
             metrics['all_8']['adaptive_gradient_L1_relative_hybrid']<=1e-6),
         'pilot_8_total_transverse_points_within_uniform_q128_budget':(
             metrics['all_8']['adaptive_transverse_points']<=metrics['all_8']['uniform_transverse_points']),
         'finite_topology_probes_do_not_exclude_hidden_tangencies':True,
         'q256_is_numerical_comparator_not_proven_truth':True,
         'cannot_claim_all_30_cut_cells_or_three_axis_convergence':True,
         'no_global_error_bound_certified':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True}
    if any(not math.isfinite(x['adaptive_gradient_L1_relative_hybrid']) for x in metrics.values()):
        raise ValueError('P10QQ_NONFINITE_AUDIT_RESULT')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    for key,r in metrics.items():
        print('P10QQ',key,'q128_L1=',f'{r["uniform_gradient_L1_relative_hybrid"]:.6e}',
              'topology_L1=',f'{r["adaptive_gradient_L1_relative_hybrid"]:.6e}',
              'ratio=',f'{r["adaptive_to_uniform_gradient_L1_ratio"]:.4f}',
              'points=',r['adaptive_transverse_points'],'/',r['uniform_transverse_points'],
              'leaves=',r['leaf_count_total'],'unresolved=',r['unresolved_topology_panel_count'])
    print('P10QQ_PILOT_COMPLETE_NO_RIGOROUS_CERTIFICATE_NO_FEM')


if __name__=='__main__':main()
