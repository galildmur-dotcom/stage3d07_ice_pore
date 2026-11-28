#!/usr/bin/env python3
"""P10QP: genuine heldout q256 and same-node-budget composite transverse Gauss.

Actual curved Tet10/P4/P2 roots per ray, exact 1D cubic FE primitive.
Only 12 previously frozen targets, split into two disjoint worker parts.
No Gmsh, CAD, mesh change, physical FEM, EDV or shape adjoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild


def panel_integrate(c:RayChild,axis:int,panels:int,n:int):
    if (panels,n) not in ((2,64),(4,32)):
        raise ValueError('P10QP_UNFROZEN_PANEL_CONFIGURATION')
    ab,ww=np.polynomial.legendre.leggauss(n)
    ab=(ab+1)*0.5;ww=ww*0.5
    # The original RayChild maps (s,t)∈[0,1]² to the Duffy tetrahedron.
    # Apply the exact affine panel Jacobian 1/(panels^2).
    total_g=0.;total_v=0.;ac=0
    for panel_s in range(panels):
        for panel_t in range(panels):
            for s,sw in zip(ab,ww):
                ss=(panel_s+float(s))/panels
                for t,tw in zip(ab,ww):
                    tt=(panel_t+float(t))/panels
                    g,v,nseg=c.moment_on_ray(axis,ss,tt)
                    weight=float(sw*tw)/(panels*panels)
                    total_g+=weight*g;total_v+=weight*v;ac+=nseg
    return {'cut_gradient_m3':total_g,'cut_volume_m3':total_v,
            'transverse_Gauss_points':panels*panels*n*n,
            'accepted_ray_segments':ac}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--axis2-q128',type=Path,required=True)
    p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--part',type=int,choices=[0,1],required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    if sha!=m8.PINNED_M8_SHA256:
        raise ValueError('P10QP_WRONG_M8')
    schedule=json.loads(a.schedule.read_text())
    qa=json.loads(a.child_report.read_text())
    prev=json.loads(a.axis2_q128.read_text())
    selected=schedule['selected_indices_ranked']
    if schedule['stage']!='P10QP' or schedule['mesh_sha256']!=sha or \
       not schedule['never_used_axis2_or_q256_for_selection'] or \
       schedule['training_only_axes']!=[0,1] or schedule['unseen_order_to_predict']!=256 or \
       len(selected)!=12 or len(set(selected))!=12 or \
       schedule['uniform_comparators']!=[128,256] or \
       schedule['locked_panel_candidates']!=[
           {'panel_s':2,'panel_t':2,'nodes_per_panel_direction':64,'total_transverse_points':16384},
           {'panel_s':4,'panel_t':4,'nodes_per_panel_direction':32,'total_transverse_points':16384}] or \
       qa['mesh_sha256']!=sha or qa['source_cases']!=[5] or qa['h_depth_limit']!=8 or \
       qa['min_h_one']!=8 or qa['physical_4D_FEM_approved'] or \
       prev['stage']!='P10QO' or prev['mesh_sha256']!=sha or prev['axis']!=2 or \
       prev['source_case']!=5 or prev['orders']!=[16,32,64,128] or \
       prev['child_input_sha256']!=qa['worker_input_sha256'] or \
       prev['physical_4D_FEM_approved']:
        raise ValueError('P10QP_UNFROZEN_EXPERIMENT_OR_INVALID_SOURCE')
    prev_by_index={x['index']:x for x in prev['cells']}
    rows=[];my_indices=selected[a.part::2]
    for pos,idx in enumerate(my_indices,1):
        t=qa['terminals'][idx]
        if t['group'] not in ('one','multi') or idx not in prev_by_index or \
           prev_by_index[idx]['group']!=t['group']:
            raise ValueError('P10QP_TARGET_NOT_REAL_CUT_CELL')
        c=RayChild(t)
        full=c.integrate(2,8,cut=False)
        if abs(full['cut_gradient_m3']-c.exact_full_gradient)>1e-10*max(abs(c.exact_full_gradient),1e-25) or \
           abs(full['cut_volume_m3']-c.exact_full_volume)>1e-10*c.exact_full_volume:
            raise ValueError('P10QP_EXACT_FULL_MOMENT_FAILED')
        baseline=prev_by_index[idx]['order']['128']
        methods={}
        for name,method in (
            ('uniform_q256',lambda:c.integrate(2,256)),
            ('panel2_q64',lambda:panel_integrate(c,2,2,64)),
            ('panel4_q32',lambda:panel_integrate(c,2,4,32))):
            tic=time.monotonic();value=method();value['elapsed_s']=time.monotonic()-tic
            if not math.isfinite(value['cut_gradient_m3']) or not math.isfinite(value['cut_volume_m3']) or \
               value['cut_volume_m3']<0 or value['cut_volume_m3']>c.exact_full_volume*(1+1e-8):
                raise ValueError('P10QP_INVALID_PHYSICAL_CUT_MOMENT')
            methods[name]=value
        rows.append({'index':idx,'group':t['group'],'h_depth':t['h_depth'],
                     'active_boundary_indices':c.active,
                     'exact_full_gradient_m3':c.exact_full_gradient,
                     'exact_full_volume_m3':c.exact_full_volume,
                     'uniform_q128_from_previous_independent_run':{
                         'cut_gradient_m3':baseline['cut_gradient_m3'],
                         'cut_volume_m3':baseline['cut_volume_m3'],
                         'transverse_Gauss_points':16384},
                     'new_methods':methods})
        print(f'P10QP_REAL_M8_HELDOUT_Q256 part={a.part} progress={pos}/{len(my_indices)} '
              f'cell={idx} q128_to_q256_grad={methods["uniform_q256"]["cut_gradient_m3"]-baseline["cut_gradient_m3"]:.4e}',flush=True)
    out={'stage':'P10QP','scope':'FROZEN selection axes 0,1; new axis2 q256 reference, two equal-cost panels',
         'mesh_sha256':sha,'source_case':5,'original_element_id':5865,'part':a.part,'parts':2,
         'selected_indices_all':selected,'selected_indices_this_part':my_indices,
         'schedule_sha256':hashlib.sha256(a.schedule.read_bytes()).hexdigest(),
         'child_report_sha256':hashlib.sha256(a.child_report.read_bytes()).hexdigest(),
         'axis2_baseline_sha256':hashlib.sha256(a.axis2_q128.read_bytes()).hexdigest(),
         'uniform_reference_q256_is_empirical_not_certified':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
         'cells':rows}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(f'P10QP_PART_{a.part}_DONE_Q256_EMPIRICAL_ONLY_NO_FEM',flush=True)


if __name__=='__main__':main()
