#!/usr/bin/env python3
"""P10QN: genuinely held-out third reference-axis test of locked adaptive q.

Run only the orders assigned by the q16/32/64 training on axis 2; do not
retune anything using these new axis-0 cut results.  Compare all 27 true
curved M8 cuts with independent q256 benchmarks from axes 1 and 2, plus
their already computed adaptive values.  No CAD, Gmsh, FEM, mesh changes.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import time

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild

SCHEDULE=Path('P10QN_M8_ADAPTIVE_ORDER_MARGIN06_QA.json')
CHILD=Path('P10QK_M8_HYBRID_CHILDREN_CASE4_H8_ONE8_QA.json')
M8=Path('P10PO_M21_NARROW_POLES_HIGHORDERELASTIC_ALL_QA_20261128/M8.msh')
LOW={1:Path('P10QN_M8_FULL_H8_RAY_AXIS1_LOW_QA.json'),
     2:Path('P10QL_M8_FULL_H8_RAY_AXIS2_QA.json')}
HIGH={1:Path('P10QM_M8_FULL_H8_RAY_AXIS1_Q256_QA.json'),
      2:Path('P10QM_M8_FULL_H8_RAY_AXIS2_Q256_QA.json')}
OUT=Path('P10QN_M8_THIRD_AXIS_ADAPTIVE_VALIDATION_QA.json')
ROOT_VOLUME=6.22294002408442e-14


def check_pin():
    digest=hashlib.sha256(M8.read_bytes()).hexdigest()
    if digest!=m8.PINNED_M8_SHA256:
        raise ValueError('P10QN_UNAPPROVED_M8')
    return digest


def main():
    mesh=check_pin()
    q=json.loads(SCHEDULE.read_text())
    rep=json.loads(CHILD.read_text())
    if q['mesh_sha256']!=mesh or rep['mesh_sha256']!=mesh or \
       q['locked_schedule']['design_fraction_of_target']!=.6 or \
       q['physical_4D_FEM_approved'] or rep['physical_4D_FEM_approved']:
        raise ValueError('P10QN_THIRD_AXIS_SCHEDULE_OR_MESH_NOT_LOCKED')
    orders=q['locked_schedule']['orders_in_source_order']
    if len(orders)!=27 or not all(n in (64,128) for n in orders):
        raise ValueError('P10QN_THIRD_AXIS_ILLEGAL_ORDER')
    term_pairs=[(i,t) for i,t in enumerate(rep['terminals']) if t['group'] in ('one','multi')]
    terms=[t for _,t in term_pairs]
    if len(terms)!=27:raise ValueError('P10QN_THIRD_AXIS_WRONG_TRUE_H8_PARTITION')
    # First compute the new, independently held-out axis=0 numbers without
    # loading either previous axis's quadrature moments.
    axis0=[];results=[]
    for i,(order,term) in enumerate(zip(orders,terms)):
        c=RayChild(term)
        full=c.integrate(0,8,cut=False)
        fg=abs(full['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)
        fv=abs(full['cut_volume_m3']-c.exact_full_volume)/c.exact_full_volume
        if max(fg,fv)>1e-10:
            raise ValueError('P10QN_THIRD_AXIS_ANALYTIC_FULL_TET10_FAILED')
        t0=time.monotonic()
        val=c.integrate(0,order)
        val['wall_seconds']=time.monotonic()-t0
        axis0.append(val)
        results.append({'index':term_pairs[i][0],
                        'group':term['group'],'selected_n':order,
                        'cut_gradient_m3':val['cut_gradient_m3'],
                        'cut_volume_m3':val['cut_volume_m3'],
                        'full_moment_grad_relative':fg,
                        'full_moment_volume_relative':fv,
                        'wall_seconds':val['wall_seconds']})
        if (i+1)%5==0 or i==len(terms)-1:
            print('P10QN_THIRD_AXIS_PROGRESS=',i+1,'/',len(terms),flush=True,sep='')

    # Only after the axis-0 program has finished is the held-out comparator
    # loaded. No selection changes are permitted at this point.
    low={a:json.loads(f.read_text()) for a,f in LOW.items()}
    high={a:json.loads(f.read_text()) for a,f in HIGH.items()}
    cross=[]
    for a in (1,2):
        for item in (low[a],high[a]):
            if item['mesh_sha256']!=mesh or len(item['cells'])!=27:
                raise ValueError('P10QN_THIRD_AXIS_COMPARATOR_PARTITION_MISMATCH')
        ref=[];adaptive=[]
        for i,n in enumerate(orders):
            original=high[a]['cells'][i]['orders']['256']
            selected=(low[a] if n==64 else high[a])['cells'][i]['orders'][str(n)]
            ref.append(original);adaptive.append(selected)
        axis0_diff=[axis0[i]['cut_gradient_m3']-ref[i]['cut_gradient_m3'] for i in range(27)]
        selected_diff=[axis0[i]['cut_gradient_m3']-adaptive[i]['cut_gradient_m3'] for i in range(27)]
        volume_ref=[axis0[i]['cut_volume_m3']-ref[i]['cut_volume_m3'] for i in range(27)]
        volume_selected=[axis0[i]['cut_volume_m3']-adaptive[i]['cut_volume_m3'] for i in range(27)]
        total=abs(high[a]['ray_hybrid_gradient_m3_by_order']['256'])
        cross.append({'reference_axis':a,
                      'axis0_adaptive_vs_axis_q256_gradient_L1_m3':sum(abs(x) for x in axis0_diff),
                      'axis0_adaptive_vs_axis_q256_gradient_L1_relative':sum(abs(x) for x in axis0_diff)/total,
                      'axis0_adaptive_vs_axis_adaptive_gradient_L1_m3':sum(abs(x) for x in selected_diff),
                      'axis0_adaptive_vs_axis_adaptive_gradient_L1_relative':sum(abs(x) for x in selected_diff)/total,
                      'axis0_adaptive_vs_axis_q256_volume_L1_relative_to_full_child':
                          sum(abs(x) for x in volume_ref)/ROOT_VOLUME,
                      'axis0_adaptive_vs_axis_adaptive_volume_L1_relative_to_full_child':
                          sum(abs(x) for x in volume_selected)/ROOT_VOLUME,
                      'signed_axis0_gradient_minus_reference_m3':sum(axis0_diff)})
    passed=all(row['axis0_adaptive_vs_axis_q256_gradient_L1_relative']<1e-6 and
               row['axis0_adaptive_vs_axis_adaptive_gradient_L1_relative']<1e-6 and
               row['axis0_adaptive_vs_axis_q256_volume_L1_relative_to_full_child']<1e-6 and
               row['axis0_adaptive_vs_axis_adaptive_volume_L1_relative_to_full_child']<1e-6
               for row in cross)
    out={'stage':'P10QN','mesh_sha256':mesh,'date_utc':'2026-11-28',
         'status':'THIRD_AXIS_STRICT_EMPIRICAL_L1_PASS' if passed else 'THIRD_AXIS_STRICT_EMPIRICAL_L1_FAIL',
         'method':'locked axis2 training schedule, independently evaluated reference axis0',
         'locked_schedule_reference':SCHEDULE.name,
         'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'total_transverse_points_axis0':sum(n*n for n in orders),
         'selected_n_counts':{'64':orders.count(64),'128':orders.count(128)},
         'independent_cross_validation':cross,
         'third_axis_pass_both_gradient_and_full_reference_volume_global_1e_minus_6':passed,
         'no_mathematically_certified_error_bound':True,
         'physical_4D_FEM_approved':False,'Gmsh_CAD_FEM_executed':False,
         'cells_axis0':results}
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QN_THIRD_AXIS_VALIDATION_COMPLETE',out['status'],flush=True)


if __name__=='__main__':main()
