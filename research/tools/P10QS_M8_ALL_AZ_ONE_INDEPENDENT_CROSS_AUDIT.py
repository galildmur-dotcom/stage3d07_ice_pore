#!/usr/bin/env python3
"""P10QS: independent 22/22 single azimuth boundary non-cancelling L1 audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from P10QS_M8_ALL_AZIMUTH_ONE_BOUNDARY_Q256_SCALE import (
    PIN, ALL_AZ, PREVIOUS_QR, WORKLIST, NEW_REFERENCE_EXPECTED)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in range(4):p.add_argument(f'--part{k}',type=Path,required=True)
    p.add_argument('--p10qr-part0',type=Path,required=True)
    p.add_argument('--p10qr-part1',type=Path,required=True)
    p.add_argument('--axis2-q128',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    paths=[getattr(a,f'part{k}') for k in range(4)]
    parts=[json.loads(f.read_text()) for f in paths]
    qrs=[json.loads(f.read_text()) for f in (a.p10qr_part0,a.p10qr_part1)]
    prior=json.loads(a.axis2_q128.read_text())
    if prior['mesh_sha256']!=PIN or len(prior['cells'])!=30 or \
       prior['axis']!=2 or prior['physical_4D_FEM_approved']:
        raise ValueError('P10QS_PRIOR_30_CELL_SOURCE_WRONG')
    for i,pdata in enumerate(parts):
        if pdata['stage']!='P10QS' or pdata['mesh_sha256']!=PIN or \
           pdata['part']!=i or pdata['parts']!=4 or pdata['axis']!=2 or \
           pdata['all_22_az_one_indices']!=list(ALL_AZ) or \
           pdata['prior_p10qr_6_indices']!=list(PREVIOUS_QR) or \
           pdata['frozen_remaining_16_worklist']!=list(WORKLIST) or \
           pdata['all_8_new_q256_expected']!=sorted(NEW_REFERENCE_EXPECTED) or \
           [x['index'] for x in pdata['cells']]!=list(WORKLIST[i::4]) or \
           pdata['frozen_parameters']!={'inner_s_budget':128,'outer_t_orders':[128,256]} or \
           pdata['physical_4D_FEM_approved']:
            raise ValueError('P10QS_NOT_FROZEN_REAL_SOURCE_OR_PART')
    for i,pdata in enumerate(qrs):
        if pdata['stage']!='P10QR' or pdata['mesh_sha256']!=PIN or \
           [x['index'] for x in pdata['cells']]!=list(PREVIOUS_QR[i::2]) or \
           pdata['physical_4D_FEM_approved']:
            raise ValueError('P10QS_PRIOR_P10QR_SIX_NOT_IDENTICAL')
    rows={x['index']:x for part in [*parts,*qrs] for x in part['cells']}
    if set(rows)!=set(ALL_AZ):
        raise ValueError('P10QS_22_AZ_CELL_SET_NOT_COMPLETE')
    prev={x['index']:x for x in prior['cells']}
    dgrad=abs(prior['hybrid_gradient_by_order_m3']['128'])
    dvol=prior['root_physical_volume_m3']
    methods=('uniform_q128','critical_s_t128','critical_s_t256')
    details=[]
    for idx in ALL_AZ:
        row=rows[idx]
        old_baseline=(row['prior_uniform_q128'] if idx not in PREVIOUS_QR
                      else row['baseline_q128'])
        reference=row['q256_reference']
        reference_origin=(row['q256_origin'] if idx not in PREVIOUS_QR
                          else row['reference_origin'])
        if old_baseline['cut_gradient_m3']!=prev[idx]['order']['128']['cut_gradient_m3'] or \
           old_baseline['cut_volume_m3']!=prev[idx]['order']['128']['cut_volume_m3'] or \
           row['group']!='one' or row['active']!=[4] or \
           max(row['full_gradient_relative_error'],row['full_volume_relative_error'])>1e-10:
            raise ValueError('P10QS_SOURCE_ID_OR_CUBIC_MOMENT_WRONG')
        cand={'uniform_q128':old_baseline,
              'critical_s_t128':row['segmented']['128'],
              'critical_s_t256':row['segmented']['256']}
        if cand['critical_s_t128']['transverse_Gauss_points']!=16384 or \
           cand['critical_s_t256']['transverse_Gauss_points']!=32768:
            raise ValueError('P10QS_NONFROZEN_GAUSS_COST')
        info={'index':idx,'q256_origin':reference_origin,
              'unresolved_topology_t128':row['segmented']['128']['topology_probe_unresolved_intervals'],
              'unresolved_topology_t256':row['segmented']['256']['topology_probe_unresolved_intervals'],
              'event_counts_t128':row['segmented']['128']['total_critical_event_roots_by_kind'],
              'relative_full_moment_gradient_error':row['full_gradient_relative_error'],
              'relative_full_moment_volume_error':row['full_volume_relative_error'],
              'methods':{}}
        for m,v in cand.items():
            dg=v['cut_gradient_m3']-reference['cut_gradient_m3']
            dv=v['cut_volume_m3']-reference['cut_volume_m3']
            info['methods'][m]={'signed_gradient_m3':dg,'absolute_gradient_m3':abs(dg),
                                'signed_volume_m3':dv,'absolute_volume_m3':abs(dv),
                                'point_count':v['transverse_Gauss_points']}
        details.append(info)
    groups={'all_22':details,
            'original_P10QR_6':[x for x in details if x['index'] in PREVIOUS_QR],
            'additional_16':[x for x in details if x['index'] not in PREVIOUS_QR],
            'new_q256_8':[x for x in details if x['index'] in NEW_REFERENCE_EXPECTED],
            'prior_q256_14':[x for x in details if x['index'] not in NEW_REFERENCE_EXPECTED]}
    if len(groups['new_q256_8'])!=8 or len(groups['prior_q256_14'])!=14:
        raise ValueError('P10QS_NEW_Q256_COUNT_NOT_EIGHT')
    metrics={}
    for group,these in groups.items():
        values={}
        for m in methods:
            l1g=sum(x['methods'][m]['absolute_gradient_m3'] for x in these)
            l1v=sum(x['methods'][m]['absolute_volume_m3'] for x in these)
            signed=sum(x['methods'][m]['signed_gradient_m3'] for x in these)
            values[m]={'L1_gradient_m3':l1g,'L1_gradient_relative_hybrid':l1g/dgrad,
                       'L1_volume_m3':l1v,'L1_volume_relative_full_child':l1v/dvol,
                       'signed_gradient_m3':signed,
                       'gradient_signed_cancellation_ratio':l1g/max(abs(signed),1e-35),
                       'total_transverse_Gauss_points':sum(x['methods'][m]['point_count'] for x in these)}
        metrics[group]={'cell_count':len(these),'methods':values,
                        'critical_t128_cellwise_improvement_count':sum(
                            x['methods']['critical_s_t128']['absolute_gradient_m3']<
                            x['methods']['uniform_q128']['absolute_gradient_m3'] for x in these),
                        'critical_t256_cellwise_improvement_count':sum(
                            x['methods']['critical_s_t256']['absolute_gradient_m3']<
                            x['methods']['uniform_q128']['absolute_gradient_m3'] for x in these),
                        'unresolved_topology_t128':sum(x['unresolved_topology_t128'] for x in these),
                        'unresolved_topology_t256':sum(x['unresolved_topology_t256'] for x in these)}
    out={'stage':'P10QS','scope':'22 of 22 genuine one-azimuth curved M8 cuts, 8 newly q256, not full 30',
         'mesh_sha256':PIN,'source_sha256':{key:hashlib.sha256(path.read_bytes()).hexdigest()
             for key,path in [(f'part{i}',f) for i,f in enumerate(paths)]+
                            [('qr0',a.p10qr_part0),('qr1',a.p10qr_part1),('baseline',a.axis2_q128)]},
         'all_22_az_one_indices':list(ALL_AZ),'new_q256_indices':sorted(NEW_REFERENCE_EXPECTED),
         'remaining_unchecked_8_cut_cells':'7 two-boundary P4/P2 + 1 one-boundary radial P4',
         'metrics':metrics,'cells':details,
         'empirical_1e_minus_6_q256_comparator_pass_on_22_only':{
            m:metrics['all_22']['methods'][m]['L1_gradient_relative_hybrid']<=1e-6
            for m in methods},
         'cannot_claim_full_30_or_three_axis_or_interval_certification':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True}
    if any(not math.isfinite(x['L1_gradient_relative_hybrid']) for row in metrics.values()
           for x in row['methods'].values()):
        raise ValueError('P10QS_NONFINITE_AGGREGATE')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    for group,x in metrics.items():
        print('P10QS',group,'n',x['cell_count'],'improved_t128',x['critical_t128_cellwise_improvement_count'])
        for m,v in x['methods'].items():
            print('P10QS',group,m,'L1_grad',f'{v["L1_gradient_relative_hybrid"]:.7e}',
                  'L1_volume',f'{v["L1_volume_relative_full_child"]:.7e}',
                  'points',v['total_transverse_Gauss_points'])
    print('P10QS_NO_RIGOROUS_OR_FULL30_CERTIFICATION_NO_FEM')


if __name__=='__main__':main()
