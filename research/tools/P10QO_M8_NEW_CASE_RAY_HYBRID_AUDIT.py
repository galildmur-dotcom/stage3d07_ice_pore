#!/usr/bin/env python3
"""P10QO: independent true-curved M8 cut-ray integration on NEW P10QJ cases.

Work without Algoim or previously selected q-values: find actual P4/P2
physical boundary roots along each ray, exactly integrate true cubic P2-FE
numerator, and use only 2D Gauss-Legendre outside the analytic direction.
Supports source cases 5,6,7 but explicitly caps cut-cell count for safety.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--worker-input',type=Path,required=True)
    p.add_argument('--case',type=int,choices=[5,6,7],required=True)
    p.add_argument('--axis',type=int,choices=[0,1,2],required=True)
    p.add_argument('--orders',type=int,nargs='+',default=[16,32,64,128])
    p.add_argument('--max-cuts',type=int,default=40)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    report=json.loads(a.child_report.read_text())
    select=json.loads(a.selection.read_text())
    if sha!=m8.PINNED_M8_SHA256 or report['mesh_sha256']!=sha or select['mesh_sha256']!=sha or \
       report['source_cases']!=[a.case] or report['min_h_one']!=8 or \
       report['h_depth_limit']!=8 or report['worker_input_sha256']!=hashlib.sha256(a.worker_input.read_bytes()).hexdigest() or \
       a.orders!=sorted(set(a.orders)) or any(n<8 or n>256 for n in a.orders) or \
       len(a.orders)<2 or report['physical_4D_FEM_approved']:
        raise ValueError('P10QO_REAL_M8_SHA_OR_SCOPE_OR_Q_INVALID')
    original=select['cases'][a.case]
    case=report['cases'][0]
    if case['original_element_id']!=original['original_element_id'] or \
       list(case['sector'])!=[original[k] for k in ('radial_bin','mu_bin','phi_bin')]:
        raise ValueError('P10QO_WRONG_REAL_SOURCE_ELEMENT_OR_SECTOR')
    terms=report['terminals']
    cut=[(i,t) for i,t in enumerate(terms) if t['group'] in ('one','multi')]
    counts=case['group_counts']
    if len(cut)!=counts['one']+counts['multi'] or len(cut)>a.max_cuts or \
       sum(case['group_physical_volume_fraction'].values())<1-3e-10 or \
       case['full_mass_partition_closure']>3e-10:
        raise ValueError('P10QO_UNCONTROLLED_CUT_COUNT_OR_VOLUME_PARTITION')
    exact_inside=sum(t['exact_full_gradient_m3'] for t in terms if t['group']=='inside')
    exact_inside_volume=sum(t['exact_full_volume_m3'] for t in terms if t['group']=='inside')
    sums={n:0. for n in a.orders};vol_sums={n:0. for n in a.orders}
    rows=[]
    for count,(i,t) in enumerate(cut,1):
        child=RayChild(t)
        full=child.integrate(a.axis,8,cut=False)
        grad_err=abs(full['cut_gradient_m3']-child.exact_full_gradient)/max(abs(child.exact_full_gradient),1e-25)
        vol_err=abs(full['cut_volume_m3']-child.exact_full_volume)/child.exact_full_volume
        if max(grad_err,vol_err)>1e-10:
            raise ValueError('P10QO_REAL_CURVED_FULL_POLYNOMIAL_MOMENT_WRONG')
        item={'index':i,'h_depth':t['h_depth'],'group':t['group'],
              'active_constraints':child.active,
              'exact_full_gradient_m3':child.exact_full_gradient,
              'exact_full_volume_m3':child.exact_full_volume,
              'full_gradient_relative_error':grad_err,
              'full_volume_relative_error':vol_err,
              'order':{}}
        for n in a.orders:
            tic=time.monotonic()
            value=child.integrate(a.axis,n)
            value['elapsed_s']=time.monotonic()-tic
            if not math.isfinite(value['cut_gradient_m3']) or \
               value['cut_volume_m3']<0 or \
               value['cut_volume_m3']>1.00000001*child.exact_full_volume:
                raise ValueError('P10QO_NONPHYSICAL_CURVED_CUT_VOLUME_OR_MOMENT')
            item['order'][str(n)]=value
            sums[n]+=value['cut_gradient_m3']
            vol_sums[n]+=value['cut_volume_m3']
        rows.append(item)
        if count%5==0 or count==len(cut):
            print(f'P10QO_CASE={a.case}_AXIS={a.axis}_PROGRESS={count}/{len(cut)}',flush=True)
    dif=[];vdif=[]
    n0,n1=a.orders[-2:]
    for t in rows:
        dif.append(t['order'][str(n1)]['cut_gradient_m3']-t['order'][str(n0)]['cut_gradient_m3'])
        vdif.append(t['order'][str(n1)]['cut_volume_m3']-t['order'][str(n0)]['cut_volume_m3'])
    total=exact_inside+sums[n1]
    result={'stage':'P10QO','scope':'new real curved M8 case, NOT case4 training geometry',
            'mesh_sha256':sha,'source_case':a.case,
            'original_element_id':case['original_element_id'],
            'sector':case['sector'],'axis':a.axis,'orders':a.orders,
            'child_input_sha256':report['worker_input_sha256'],
            'ray_worker_source_sha256':hashlib.sha256(Path('P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE.py').read_bytes()).hexdigest(),
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'group_counts':counts,'root_physical_volume_m3':case['root_volume_m3'],
            'root_exact_full_gradient_m3':original['exact_full_gradient_m3'],
            'group_volume_fractions':case['group_physical_volume_fraction'],
            'multi_boundary_bernstein_enclosure_m3':case['residual_multi_gradient_enclosure_m3'],
            'exact_inside_gradient_m3':exact_inside,
            'exact_inside_volume_m3':exact_inside_volume,
            'hybrid_gradient_by_order_m3':{str(n):exact_inside+sums[n] for n in a.orders},
            'hybrid_volume_by_order_m3':{str(n):exact_inside_volume+vol_sums[n] for n in a.orders},
            'q_last_pair_L1_gradient_m3':sum(abs(d) for d in dif),
            'q_last_pair_signed_gradient_m3':sum(dif),
            'q_last_pair_L1_relative_to_full_hybrid':sum(abs(d) for d in dif)/max(abs(total),1e-25),
            'q_last_pair_L1_volume_m3':sum(abs(d) for d in vdif),
            'q_last_pair_L1_volume_relative_to_original_full_child':
                sum(abs(d) for d in vdif)/case['root_volume_m3'],
            'no_error_bound_certified':True,'physical_4D_FEM_approved':False,
            'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
            'cells':rows}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(f'P10QO_CASE{a.case}_AXIS{a.axis}_INDEPENDENT_RAY_COMPLETE_NOT_FEM',flush=True)


if __name__=='__main__':main()
