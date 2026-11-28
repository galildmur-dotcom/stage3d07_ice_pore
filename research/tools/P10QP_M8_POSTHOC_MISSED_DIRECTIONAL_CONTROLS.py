#!/usr/bin/env python3
"""P10QP exploratory follow-up, explicitly POST-HOC after the frozen pilot.

Sample the four largest axis-2 q64->q128 changes EXCLUDED by the frozen
axis0/1 selection. Fresh q256 is not a certified exact answer.
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
from P10QP_M8_HELDOUT_Q256_PANEL_COMPARISON import panel_integrate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--axis2-q128',type=Path,required=True)
    p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    report=json.loads(a.child_report.read_text())
    prev=json.loads(a.axis2_q128.read_text())
    sched=json.loads(a.schedule.read_text())
    if sha!=m8.PINNED_M8_SHA256 or report['mesh_sha256']!=sha or \
       report['source_cases']!=[5] or report['min_h_one']!=8 or \
       report['h_depth_limit']!=8 or prev['axis']!=2 or prev['source_case']!=5 or \
       sched['training_only_axes']!=[0,1] or \
       len(sched['selected_indices_ranked'])!=12 or \
       any(x['physical_4D_FEM_approved'] for x in (report,prev,sched)):
        raise ValueError('P10QP_POSTHOC_SOURCE_GUARD_FAIL')
    excluded=[c for c in prev['cells'] if c['index'] not in sched['selected_indices_ranked']]
    excluded.sort(key=lambda c:(-abs(c['order']['128']['cut_gradient_m3']-
                                   c['order']['64']['cut_gradient_m3']),c['index']))
    indices=[c['index'] for c in excluded[:4]]
    if indices!=[23,31,21,25]:
        raise ValueError('P10QP_POSTHOC_RANKING_CHANGED')
    out=[]
    for i,idx in enumerate(indices,1):
        term=report['terminals'][idx]
        c=RayChild(term)
        full=c.integrate(2,8,cut=False)
        if abs(full['cut_gradient_m3']-c.exact_full_gradient)>1e-10*max(abs(c.exact_full_gradient),1e-25):
            raise ValueError('P10QP_POSTHOC_FULL_MOMENT_FAIL')
        methods={}
        for name,action in (
            ('uniform_q256',lambda:c.integrate(2,256)),
            ('panel2_q64',lambda:panel_integrate(c,2,2,64)),
            ('panel4_q32',lambda:panel_integrate(c,2,4,32))):
            tic=time.monotonic();m=action();m['elapsed_s']=time.monotonic()-tic
            if not math.isfinite(m['cut_gradient_m3']) or not 0<=m['cut_volume_m3']<=c.exact_full_volume*(1+1e-8):
                raise ValueError('P10QP_POSTHOC_NONPHYSICAL_RESULT')
            methods[name]=m
        out.append({'index':idx,'group':term['group'],
                    'previous_axis2_q64_gradient_m3':prev['cells'][next(j for j,x in enumerate(prev['cells']) if x['index']==idx)]['order']['64']['cut_gradient_m3'],
                    'uniform_q128_from_previous_run':next(x for x in prev['cells'] if x['index']==idx)['order']['128'],
                    'new_methods':methods})
        print(f'P10QP_POSTHOC_PROGRESS={i}/4 index={idx} '
              f'q128_to_q256={methods["uniform_q256"]["cut_gradient_m3"]-out[-1]["uniform_q128_from_previous_run"]["cut_gradient_m3"]:.4e}',flush=True)
    a.output.write_text(json.dumps({'stage':'P10QP','scope':'EXPLORATORY_POSTHOC_NOT_FROZEN_PILOT',
        'mesh_sha256':sha,'control_indices':[r['index'] for r in out],
        'ranked_by':'previously SEEN axis2 q64->q128 nonselected deviations',
        'results_do_NOT_constitute_heldout_target_selection':True,
        'schedule_sha256':hashlib.sha256(a.schedule.read_bytes()).hexdigest(),
        'axis2_q128_sha256':hashlib.sha256(a.axis2_q128.read_bytes()).hexdigest(),
        'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
        'cells':out},indent=2)+'\n')
    print('P10QP_POSTHOC_DIRECTIONAL_CONTROL_COMPLETE_NOT_CERTIFIED_NO_FEM',flush=True)


if __name__=='__main__':main()
