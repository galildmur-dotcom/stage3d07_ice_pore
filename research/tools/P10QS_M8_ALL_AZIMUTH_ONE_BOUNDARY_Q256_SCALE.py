#!/usr/bin/env python3
"""P10QS: extend P10QR explicit P2 critical-s splitting to ALL 22 az-one cuts.

Six previous P10QR cells are immutable. Run the other 16 across four disjoint
parts; eight real q256 references are new. No mesh generation, Gmsh, FEM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QR_M8_ONE_BOUNDARY_DISCRIMINANT_SEGMENTED import (
    PIN, AXIS, S_BUDGET, T_ORDERS, integrate)

ALL_AZ=(5,6,7,8,9,10,11,12,15,17,18,23,24,25,26,28,29,32,33,34,35,36)
PREVIOUS_QR=(26,10,23,8,18,33)
WORKLIST=(5,7,9,15,24,29,35,36,6,11,12,17,25,28,32,34)
NEW_REFERENCE_EXPECTED={5,7,9,15,24,29,35,36}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--axis2-q128',type=Path,required=True)
    p.add_argument('--p10qp-part0',type=Path,required=True)
    p.add_argument('--p10qp-part1',type=Path,required=True)
    p.add_argument('--p10qp-posthoc',type=Path,required=True)
    p.add_argument('--p10qq-part0',type=Path,required=True)
    p.add_argument('--p10qq-part1',type=Path,required=True)
    p.add_argument('--p10qr-part0',type=Path,required=True)
    p.add_argument('--p10qr-part1',type=Path,required=True)
    p.add_argument('--part',type=int,choices=[0,1,2,3],required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    mesh_sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    child=json.loads(a.child_report.read_text())
    baseline=json.loads(a.axis2_q128.read_text())
    oldp=[json.loads(f.read_text()) for f in (a.p10qp_part0,a.p10qp_part1,a.p10qp_posthoc)]
    oldq=[json.loads(f.read_text()) for f in (a.p10qq_part0,a.p10qq_part1)]
    oldr=[json.loads(f.read_text()) for f in (a.p10qr_part0,a.p10qr_part1)]
    if mesh_sha!=PIN or child['mesh_sha256']!=PIN or child['source_cases']!=[5] or \
       child['h_depth_limit']!=8 or child['min_h_one']!=8 or \
       baseline['mesh_sha256']!=PIN or baseline['axis']!=AXIS or \
       len(baseline['cells'])!=30 or \
       any(x['mesh_sha256']!=PIN or x['physical_4D_FEM_approved'] for x in
           [child,baseline,*oldp,*oldq,*oldr]):
        raise ValueError('P10QS_PINNED_REAL_M8_OR_REFERENCE_GUARD')
    actual=tuple(i for i,t in enumerate(child['terminals']) if t['group']=='one' and
                 [j for j,v in enumerate(t['status']) if v==0]==[4])
    if actual!=ALL_AZ or set(WORKLIST)!=set(ALL_AZ)-set(PREVIOUS_QR):
        raise ValueError('P10QS_ALL_22_SOURCE_REAL_CELL_SET_CHANGED')
    prev={c['index']:c['order']['128'] for c in baseline['cells']}
    refs={c['index']:c['new_methods']['uniform_q256'] for src in oldp for c in src['cells']}
    refs.update({c['index']:c['uniform_q256_reference'] for src in oldq for c in src['cells']})
    refs.update({c['index']:c['q256_reference'] for src in oldr for c in src['cells']})
    if set(ALL_AZ)-set(refs)!=NEW_REFERENCE_EXPECTED:
        raise ValueError('P10QS_Q256_NEW_REFERENCE_FROZEN_SET_CHANGED')
    rows=[];selected=WORKLIST[a.part::4]
    for count,idx in enumerate(selected,1):
        t=child['terminals'][idx]
        c=RayChild(t)
        if t['group']!='one' or c.active!=[4]:
            raise ValueError('P10QS_NON_AZ_ONE_BOUNDARY')
        full=c.integrate(AXIS,8,cut=False)
        if abs(full['cut_gradient_m3']-c.exact_full_gradient)>1e-10*max(abs(c.exact_full_gradient),1e-25):
            raise ValueError('P10QS_ANALYTIC_FULL_MOMENT_PRECHECK')
        results={}
        for order in T_ORDERS:
            start=time.monotonic();result=integrate(c,order,cut=True)
            result['elapsed_s']=time.monotonic()-start
            if not math.isfinite(result['cut_gradient_m3']) or \
               not 0<=result['cut_volume_m3']<=c.exact_full_volume*(1+1e-8):
                raise ValueError('P10QS_NONPHYSICAL_S_SEGMENTED_CUT')
            results[str(order)]=result
        full_segmented=integrate(c,128,cut=False)
        full_grad_error=abs(full_segmented['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)
        full_vol_error=abs(full_segmented['cut_volume_m3']-c.exact_full_volume)/c.exact_full_volume
        if max(full_grad_error,full_vol_error)>1e-10:
            raise ValueError('P10QS_SEGMENTED_FULL_CUBIC_QA_FAILED')
        if idx in refs:
            ref=refs[idx];origin='PRIOR_Q256'
        else:
            start=time.monotonic();ref=c.integrate(AXIS,256)
            ref['elapsed_s']=time.monotonic()-start
            origin='P10QS_NEW_Q256_HELDOUT_ORDER'
        rows.append({'index':idx,'group':t['group'],'active':c.active,
                     'prior_uniform_q128':prev[idx],
                     'q256_reference':ref,'q256_origin':origin,
                     'segmented':results,
                     'full_gradient_relative_error':full_grad_error,
                     'full_volume_relative_error':full_vol_error})
        print(f'P10QS_M8_AZ_ONE part={a.part} progress={count}/{len(selected)} '
              f'cell={idx} new_q256={origin.startswith("P10QS")} '
              f'q128_abs={abs(prev[idx]["cut_gradient_m3"]-ref["cut_gradient_m3"]):.4e} '
              f'seg128_abs={abs(results["128"]["cut_gradient_m3"]-ref["cut_gradient_m3"]):.4e}',flush=True)
    inputs={'child':a.child_report,'uniform128':a.axis2_q128,
            'p10qp_part0':a.p10qp_part0,'p10qp_part1':a.p10qp_part1,
            'p10qp_posthoc':a.p10qp_posthoc,'p10qq_part0':a.p10qq_part0,
            'p10qq_part1':a.p10qq_part1,'p10qr_part0':a.p10qr_part0,
            'p10qr_part1':a.p10qr_part1}
    out={'stage':'P10QS','mesh_sha256':PIN,'source_case':5,'original_element_id':5865,
         'axis':AXIS,'all_22_az_one_indices':list(ALL_AZ),
         'prior_p10qr_6_indices':list(PREVIOUS_QR),'frozen_remaining_16_worklist':list(WORKLIST),
         'all_8_new_q256_expected':sorted(NEW_REFERENCE_EXPECTED),
         'part':a.part,'parts':4,'selected_indices':list(selected),
         'frozen_parameters':{'inner_s_budget':S_BUDGET,'outer_t_orders':list(T_ORDERS)},
         'input_sha256':{k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in inputs.items()},
         'physical_4D_FEM_approved':False,
         'numerical_projected_roots_not_interval_certified':True,
         'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
         'cells':rows}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(f'P10QS_PART_{a.part}_ALL_AZ_ONE_SCALE_COMPLETE_NO_FEM',flush=True)


if __name__=='__main__':main()
