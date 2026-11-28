#!/usr/bin/env python3
"""P10QN: independent full 3-axis q128 fallback when adaptive gate fails.

This is a scientific benchmark for all 27 real M8 h8 cut cells, not a
claim of rigorous quadrature error bounds or physical FEM permission.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

M8='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
ROOT_VOL=6.22294002408442e-14
SOURCES={0:Path('P10QN_M8_FULL_H8_RAY_AXIS0_Q128_QA.json'),
         1:Path('P10QM_M8_FULL_H8_RAY_AXIS1_Q256_QA.json'),
         2:Path('P10QM_M8_FULL_H8_RAY_AXIS2_Q256_QA.json')}


def read(p,axis):
    v=json.loads(p.read_text())
    if v['stage'] not in ('P10QL','P10QM') or v['axis']!=axis or \
       v['mesh_sha256']!=M8 or len(v['cells'])!=27:
        raise ValueError('P10QN_UNIFORM_THREE_AXIS_M8_SOURCE_INVALID')
    return v


def abs_l1(left,right,field):
    return sum(abs(a['orders']['128'][field]-b['orders']['128'][field]) for a,b in zip(left,right))


def main():
    a={ax:read(f,ax) for ax,f in SOURCES.items()}
    for x in a.values():
        if '128' not in {str(t) for t in x['transverse_Gauss_orders']}:
            raise ValueError('P10QN_UNIFORM_Q128_NOT_IN_SOURCE')
    ref_gradient=max(abs(x['ray_hybrid_gradient_m3_by_order']['128']) for x in a.values())
    all_pair=[]
    for ax1,ax2 in ((0,1),(0,2),(1,2)):
        g=abs_l1(a[ax1]['cells'],a[ax2]['cells'],'cut_gradient_m3')
        v=abs_l1(a[ax1]['cells'],a[ax2]['cells'],'cut_volume_m3')
        all_pair.append({'axes':[ax1,ax2],
                         'gradient_L1_m3':g,'gradient_L1_relative_to_hybrid':g/ref_gradient,
                         'volume_L1_m3':v,'volume_L1_relative_to_full_child':v/ROOT_VOL})
    reference=[]
    for axis in (1,2):
        base=a[axis]
        v2=[base['cells'][i]['orders']['256']['cut_gradient_m3'] for i in range(27)]
        vol2=[base['cells'][i]['orders']['256']['cut_volume_m3'] for i in range(27)]
        for trial_axis in (0,1,2):
            test=a[trial_axis]['cells']
            g=sum(abs(test[i]['orders']['128']['cut_gradient_m3']-v2[i]) for i in range(27))
            v=sum(abs(test[i]['orders']['128']['cut_volume_m3']-vol2[i]) for i in range(27))
            reference.append({'trial_axis_q128':trial_axis,'reference_axis_q256':axis,
                              'gradient_L1_relative_to_hybrid':g/ref_gradient,
                              'volume_L1_relative_to_full_child':v/ROOT_VOL})
    passed=all(v['gradient_L1_relative_to_hybrid']<=1e-6 and
               v['volume_L1_relative_to_full_child']<=1e-6 for v in all_pair+reference)
    out={'stage':'P10QN','date_utc':'2026-11-28','mesh_sha256':M8,
         'status':'UNIFORM_Q128_THREE_AXIS_GLOBAL_EMPIRICAL_PASS' if passed else
                  'UNIFORM_Q128_THREE_AXIS_GLOBAL_EMPIRICAL_FAIL',
         'scope':'27 curved M8 h8 cuts, three reference-coordinate axes, 128x128 all',
         'cross_axis_q128_L1':all_pair,
         'q128_three_axes_against_independent_q256_reference':reference,
         'uniform_q128_point_count_per_axis':27*128*128,
         'uniform_q256_point_count_per_axis':27*256*256,
         'all_relative_to_full_element_gradient_or_volume':True,
         'stricter_cut_volume_relative_to_cut_volume_not_claimed':True,
         'both_gradient_and_full_child_volume_global_1e_minus_6_pass':passed,
         'q_differences_are_not_rigorous_upper_error_bounds':True,
         'physical_4D_FEM_approved':False,'mesh_CAD_Gmsh_FEM_executed':False}
    Path('P10QN_M8_UNIFORM_Q128_THREE_AXIS_QA.json').write_text(json.dumps(out,indent=2)+'\n')
    print('P10QN_UNIFORM_Q128_THREE_AXIS_AUDIT_COMPLETE',out['status'],flush=True)


if __name__=='__main__':main()
