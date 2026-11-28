#!/usr/bin/env python3
"""P10QR: honest independent L1 audit of projected P2 critical-s splits."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

TARGETS=(26,10,23,8,18,33)
PIN='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--part0',type=Path,required=True)
    p.add_argument('--part1',type=Path,required=True)
    p.add_argument('--p10qo-q128',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    parts=[json.loads(x.read_text()) for x in (a.part0,a.part1)]
    old=json.loads(a.p10qo_q128.read_text())
    if old['mesh_sha256']!=PIN or old['axis']!=2 or old['physical_4D_FEM_approved'] or \
       len(old['cells'])!=30:
        raise ValueError('P10QR_PRIOR_REAL_M8_MISMATCH')
    for i,x in enumerate(parts):
        if x['stage']!='P10QR' or x['mesh_sha256']!=PIN or x['part']!=i or \
           x['parts']!=2 or x['axis']!=2 or x['all_frozen_indices']!=list(TARGETS) or \
           x['physical_4D_FEM_approved'] or \
           x['two_active_P4_P2_not_processed'] is not True or \
           [z['index'] for z in x['cells']]!=list(TARGETS[i::2]) or \
           x['frozen_parameters']!=parts[0]['frozen_parameters'] or \
           x['frozen_parameters']['inner_s_budget']!=128 or \
           x['frozen_parameters']['outer_Gauss_orders']!=[128,256]:
            raise ValueError('P10QR_SOURCE_OR_LOCKED_INTEGRATOR_MISMATCH')
    prev={x['index']:x for x in old['cells']}
    cells={x['index']:x for part in parts for x in part['cells']}
    if set(cells)!=set(TARGETS):raise ValueError('P10QR_WRONG_TARGET_SET')
    dgrad=abs(old['hybrid_gradient_by_order_m3']['128'])
    dvol=old['root_physical_volume_m3']
    methods=('uniform_q128','critical_s_t128','critical_s_t256')
    data=[]
    for idx in TARGETS:
        x=cells[idx];reference=x['q256_reference']
        baseline=prev[idx]['order']['128']
        if x['baseline_q128']['cut_gradient_m3']!=baseline['cut_gradient_m3'] or \
           x['baseline_q128']['cut_volume_m3']!=baseline['cut_volume_m3'] or \
           x['active']!=[4] or x['group']!='one' or \
           max(x['full_gradient_relative_error'],x['full_volume_relative_error'])>1e-10:
            raise ValueError('P10QR_DIAGNOSTIC_AND_ANALYTIC_QA_WRONG')
        cand={'uniform_q128':baseline,'critical_s_t128':x['segmented']['128'],
              'critical_s_t256':x['segmented']['256']}
        if cand['critical_s_t128']['transverse_Gauss_points']!=16384 or \
           cand['critical_s_t256']['transverse_Gauss_points']!=32768:
            raise ValueError('P10QR_CUT_GAUSS_BUDGET_MISMATCH')
        row={'index':idx,'q256_reference_origin':x['reference_origin'],
             'full_polynomial_gradient_relative_error':x['full_gradient_relative_error'],
             'full_polynomial_volume_relative_error':x['full_volume_relative_error'],
             'critical_event_roots_by_kind_t128':x['segmented']['128']['total_critical_event_roots_by_kind'],
             'unresolved_topology_probe_intervals_t128':x['segmented']['128']['topology_probe_unresolved_intervals'],
             'unresolved_topology_probe_intervals_t256':x['segmented']['256']['topology_probe_unresolved_intervals'],
             'methods':{}}
        for method,v in cand.items():
            dg=v['cut_gradient_m3']-reference['cut_gradient_m3']
            dv=v['cut_volume_m3']-reference['cut_volume_m3']
            row['methods'][method]={'gradient_signed_m3':dg,'gradient_abs_m3':abs(dg),
                                    'volume_signed_m3':dv,'volume_abs_m3':abs(dv),
                                    'transverse_points':v['transverse_Gauss_points']}
        data.append(row)
    groups={'all_6':data,'previous_q256_4':[x for x in data if x['q256_reference_origin']=='PREVIOUS_Q256'],
            'new_q256_2':[x for x in data if x['q256_reference_origin']=='NEW_P10QR_Q256_HELDOUT_ORDER']}
    if len(groups['previous_q256_4'])!=4 or len(groups['new_q256_2'])!=2:
        raise ValueError('P10QR_NO_NEW_HELDOUT_Q256')
    metrics={}
    for group,rows in groups.items():
        results={}
        for m in methods:
            g=sum(x['methods'][m]['gradient_abs_m3'] for x in rows)
            v=sum(x['methods'][m]['volume_abs_m3'] for x in rows)
            signed=sum(x['methods'][m]['gradient_signed_m3'] for x in rows)
            results[m]={'L1_gradient_m3':g,'L1_gradient_relative_hybrid':g/dgrad,
                        'L1_volume_m3':v,'L1_volume_relative_full_child':v/dvol,
                        'signed_gradient_m3':signed,
                        'gradient_cancellation_ratio':g/max(abs(signed),1e-35),
                        'transverse_nodes_total':sum(x['methods'][m]['transverse_points'] for x in rows)}
        metrics[group]={'cell_count':len(rows),'methods':results,
                        'critical_t128_better_per_cell_count':sum(
                            x['methods']['critical_s_t128']['gradient_abs_m3']<x['methods']['uniform_q128']['gradient_abs_m3']
                            for x in rows),
                        'critical_t256_better_per_cell_count':sum(
                            x['methods']['critical_s_t256']['gradient_abs_m3']<x['methods']['uniform_q128']['gradient_abs_m3']
                            for x in rows),
                        'unresolved_topology_t128':sum(x['unresolved_topology_probe_intervals_t128'] for x in rows),
                        'unresolved_topology_t256':sum(x['unresolved_topology_probe_intervals_t256'] for x in rows)}
    out={'stage':'P10QR','scope':'single active P2 boundary, exact polynomial projection in inner s; empirical q256',
         'mesh_sha256':PIN,'source_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest()
            for k,p in (('part0',a.part0),('part1',a.part1),('baseline',a.p10qo_q128))},
         'frozen_indices':list(TARGETS),'frozen_parameters':parts[0]['frozen_parameters'],
         'metrics':metrics,'cells':data,
         'numerical_polynomial_roots_are_not_interval_certified':True,
         'one_boundary_quadratic_only':True,
         'cannot_claim_general_two_boundary_or_full_30_cell_convergence':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True}
    if any(not math.isfinite(x['L1_gradient_m3']) for group in metrics.values()
           for x in group['methods'].values()):
        raise ValueError('P10QR_NONFINITE_QA')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    for group,r in metrics.items():
        print('P10QR',group,'unresolved_t128',r['unresolved_topology_t128'])
        for m,x in r['methods'].items():
            print('P10QR',group,m,'L1_gradient',f'{x["L1_gradient_relative_hybrid"]:.6e}',
                  'L1_volume',f'{x["L1_volume_relative_full_child"]:.6e}',
                  'points',x['transverse_nodes_total'])
    print('P10QR_NO_GLOBAL_CERTIFICATION_NO_FEM')


if __name__=='__main__':main()
