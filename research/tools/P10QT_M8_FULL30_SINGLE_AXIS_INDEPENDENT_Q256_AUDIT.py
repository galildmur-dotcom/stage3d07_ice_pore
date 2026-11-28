#!/usr/bin/env python3
"""P10QT: independent source-locked L1 on ALL 30 real h8 cut cells of case5.

Combines previous 22 one-az (P10QS) and 8 new radial/multi (P10QT).
Even an empirical one-axis PASS is NOT a three-axis or rigorous FEM gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from P10QT_M8_RADIAL_AND_TWO_BOUNDARY_CRITICAL_INTEGRATOR import (
    PIN,ALL,WORKLIST,NEW_Q256)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for i in range(4):p.add_argument(f'--part{i}',type=Path,required=True)
    p.add_argument('--p10qs-22-audit',type=Path,required=True)
    p.add_argument('--p10qo-q128',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    partpaths=[getattr(a,f'part{i}') for i in range(4)]
    parts=[json.loads(f.read_text()) for f in partpaths]
    qs=json.loads(a.p10qs_22_audit.read_text())
    base=json.loads(a.p10qo_q128.read_text())
    if qs['stage']!='P10QS' or qs['mesh_sha256']!=PIN or \
       len(qs['cells'])!=22 or qs['physical_4D_FEM_approved'] or \
       base['stage']!='P10QO' or base['mesh_sha256']!=PIN or \
       base['axis']!=2 or base['source_case']!=5 or len(base['cells'])!=30 or \
       base['physical_4D_FEM_approved']:
        raise ValueError('P10QT_OLD_22_OR_30_SOURCE_WRONG')
    for i,part in enumerate(parts):
        if part['stage']!='P10QT' or part['mesh_sha256']!=PIN or \
           part['axis']!=2 or part['part']!=i or part['parts']!=4 or \
           part['frozen_remaining_eight_indices']!=list(ALL) or \
           part['worklist']!=list(WORKLIST) or \
           part['new_q256_indices']!=sorted(NEW_Q256) or \
           part['physical_4D_FEM_approved'] or \
           [r['index'] for r in part['cells']]!=list(WORKLIST[i::4]):
            raise ValueError('P10QT_PART_WRONG_OR_NOT_FROZEN')
    prior={x['index']:x for x in base['cells']}
    one={x['index']:x for x in qs['cells']}
    eight={x['index']:x for part in parts for x in part['cells']}
    if set(eight)!=set(ALL) or len(one)!=22 or len(set(prior)-set(one)-set(eight))!=0:
        raise ValueError('P10QT_FULL30_COVERAGE_NOT_EXACT')
    dgrad=abs(base['hybrid_gradient_by_order_m3']['128'])
    dvol=base['root_physical_volume_m3']
    methods=('uniform_q128','critical_s_t128','critical_s_t256')
    rows=[]
    for idx in sorted(prior):
        source=prior[idx]
        if idx in one:
            d=one[idx]
            if d['methods']['uniform_q128']['point_count']!=16384:
                raise ValueError('P10QT_OLD_AZ_Q128_COST_WRONG')
            row={'index':idx,'source_group':'one_azimuth','active':[4],
                 'reference_origin':'P10QP_P10QQ_P10QR_P10QS_PRIOR_Q256',
                 'unresolved_t128':d['unresolved_topology_t128'],
                 'unresolved_t256':d['unresolved_topology_t256'],
                 'full_relative_error':max(d['relative_full_moment_gradient_error'],
                                           d['relative_full_moment_volume_error']),
                 'methods':{m:{'absolute_gradient_m3':d['methods'][m]['absolute_gradient_m3'],
                               'signed_gradient_m3':d['methods'][m]['signed_gradient_m3'],
                               'absolute_volume_m3':d['methods'][m]['absolute_volume_m3'],
                               'point_count':d['methods'][m]['point_count']}
                            for m in methods}}
        else:
            d=eight[idx]
            if d['prior_uniform_q128']['cut_gradient_m3']!=source['order']['128']['cut_gradient_m3'] or \
               d['prior_uniform_q128']['cut_volume_m3']!=source['order']['128']['cut_volume_m3'] or \
               d['active_constraints'] not in ([0],[0,4]) or \
               max(d['full_gradient_relative_error'],d['full_volume_relative_error'])>1e-10:
                raise ValueError('P10QT_NEW_EIGHT_NOT_REAL_OR_NOT_ANALYTIC')
            ref=d['q256_reference']
            cands={'uniform_q128':d['prior_uniform_q128'],
                   'critical_s_t128':d['segmented']['128'],
                   'critical_s_t256':d['segmented']['256']}
            row={'index':idx,'source_group':d['group'],'active':d['active_constraints'],
                 'reference_origin':d['q256_origin'],
                 'unresolved_t128':d['segmented']['128']['unresolved_topology_probe_intervals'],
                 'unresolved_t256':d['segmented']['256']['unresolved_topology_probe_intervals'],
                 'full_relative_error':max(d['full_gradient_relative_error'],d['full_volume_relative_error']),
                 'methods':{}}
            for m,v in cands.items():
                dg=v['cut_gradient_m3']-ref['cut_gradient_m3']
                dv=v['cut_volume_m3']-ref['cut_volume_m3']
                row['methods'][m]={'absolute_gradient_m3':abs(dg),'signed_gradient_m3':dg,
                                   'absolute_volume_m3':abs(dv),
                                   'point_count':v['transverse_Gauss_points']}
            if row['methods']['critical_s_t128']['point_count']!=16384 or \
               row['methods']['critical_s_t256']['point_count']!=32768:
                raise ValueError('P10QT_NEW_SEGMENTED_NODE_BUDGET_BROKEN')
        rows.append(row)
    groups={'all_30':rows,'azimuth_one_22':[x for x in rows if x['source_group']=='one_azimuth'],
            'radial_and_multi_8':[x for x in rows if x['source_group']!='one_azimuth']}
    if any(len(groups[k])!=v for k,v in (('all_30',30),('azimuth_one_22',22),('radial_and_multi_8',8))):
        raise ValueError('P10QT_L1_GROUP_CARDINALITY_WRONG')
    results={}
    for group,values in groups.items():
        metrics={}
        for m in methods:
            ag=sum(x['methods'][m]['absolute_gradient_m3'] for x in values)
            av=sum(x['methods'][m]['absolute_volume_m3'] for x in values)
            signed=sum(x['methods'][m]['signed_gradient_m3'] for x in values)
            metrics[m]={'L1_gradient_m3':ag,'L1_gradient_relative_hybrid':ag/dgrad,
                        'L1_volume_m3':av,'L1_volume_relative_full_child':av/dvol,
                        'signed_gradient_m3':signed,
                        'gradient_cancellation_ratio':ag/max(abs(signed),1e-35),
                        'total_Gauss_points':sum(x['methods'][m]['point_count'] for x in values),
                        'empirical_L1_gradient_pass_1e_minus_6':ag/dgrad<=1e-6}
        results[group]={'cell_count':len(values),'methods':metrics,
                        'critical_t128_improved_count':sum(
                            x['methods']['critical_s_t128']['absolute_gradient_m3']<
                            x['methods']['uniform_q128']['absolute_gradient_m3'] for x in values),
                        'critical_t256_improved_count':sum(
                            x['methods']['critical_s_t256']['absolute_gradient_m3']<
                            x['methods']['uniform_q128']['absolute_gradient_m3'] for x in values),
                        'unresolved_topology_t128':sum(x['unresolved_t128'] for x in values),
                        'unresolved_topology_t256':sum(x['unresolved_t256'] for x in values)}
    out={'stage':'P10QT','mesh_sha256':PIN,'source_case':5,
         'scope':'ALL 30 real h8 M8 cut cells, axis2 q256 comparator only, not full 4D',
         'source_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in
           [(f'part{i}',x) for i,x in enumerate(partpaths)]+
           [('P10QS22',a.p10qs_22_audit),('QOq128',a.p10qo_q128)]},
         'group_results':results,'full_30_cell_indices':[x['index'] for x in rows],
         'cells':rows,
         'root_events_built_only_on_axis2_where_radial_P4_reduces_to_P2':True,
         'q256_numerical_reference_is_not_exact_error_certificate':True,
         'no_three_axis_or_interval_error_certification':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True}
    if any(not math.isfinite(x['L1_gradient_relative_hybrid']) for g in results.values()
           for x in g['methods'].values()):
        raise ValueError('P10QT_NONFINITE_COMBINED_AUDIT')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    for group,g in results.items():
        print('P10QT',group,'n',g['cell_count'],'improved128',g['critical_t128_improved_count'],
              'unresolved128',g['unresolved_topology_t128'])
        for method,v in g['methods'].items():
            print('P10QT',group,method,'L1_gradient',f'{v["L1_gradient_relative_hybrid"]:.7e}',
                  'L1_volume',f'{v["L1_volume_relative_full_child"]:.7e}',
                  'points',v['total_Gauss_points'],
                  'empirical_pass',v['empirical_L1_gradient_pass_1e_minus_6'])
    print('P10QT_FULL30_AXIS2_ONLY_NOT_CERTIFIED_FEM_FORBIDDEN')


if __name__=='__main__':main()
