#!/usr/bin/env python3
"""P10QJ real-M8 curved child h-subdivision after multi-cut q failure.

Repeated exact affine subdivision of the *reference* curved child. For
each h depth, Bernstein-enclose ALL six bin conditions, classify outside,
inside, exactly one uncertain, or still >=2 uncertain. Measure *actual*
positive curved-Tet10 physical volumes via polynomial-exact q4 Duffy.
This is a conservative geometry budget, NOT integrated FE-gradient proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10PZ_M8_DIRECT_BERNSTEIN_PREFILTER as pz
import P10QB_M8_SELECT_SINGLE_QUARTIC_CHILDREN as qb


def analyze_one(case,max_depth):
    X=np.array(case['physical_child_nodes_10'],dtype=float)
    ir,im,ip=[case[k] for k in ('radial_bin','mu_bin','phi_bin')]
    root_volume=py.quadrature_volume(X,py.REF_TET)
    if root_volume<=0:
        raise ValueError('P10QJ_CHILD_VOLUME_NOT_POSITIVE')
    active=py.REF_TET[None].copy()
    classified=np.zeros(3)  # outside, inside, exactly one cut
    cumulative_counts=np.zeros(3,dtype=int)
    rows=[]
    for depth in range(max_depth+1):
        ctrl,vertices=pz.restricted_control_net(X,active)
        sign=qb.hybrid_status(ctrl,ir,im,ip)
        neg=np.any(sign==-1,axis=1)
        pos=np.all(sign==1,axis=1)
        unresolved=~(neg|pos)
        one=unresolved&(np.sum(sign==0,axis=1)==1)
        multi=unresolved&~one
        volume=np.array([py.quadrature_volume(X,v) for v in active])
        if not np.all(volume>0):
            raise ValueError('P10QJ_NONPOSITIVE_PHYSICAL_H_CHILD_VOLUME')
        category_masks=(neg,pos,one)
        for k,mask in enumerate(category_masks):
            classified[k]+=float(np.sum(volume[mask]))
            cumulative_counts[k]+=int(np.count_nonzero(mask))
        multi_volume=float(np.sum(volume[multi]))
        balance=abs(classified.sum()+multi_volume-root_volume)/root_volume
        if balance>3e-10:
            raise ValueError(f'P10QJ_UNCONSERVATIVE_H_PARTITION depth={depth} gap={balance}')
        rows.append({'h_level':depth,
                     'cumulative_outside_volume_fraction':classified[0]/root_volume,
                     'cumulative_fully_inside_volume_fraction':classified[1]/root_volume,
                     'cumulative_one_boundary_volume_fraction':classified[2]/root_volume,
                     'unresolved_at_least_two_boundary_volume_fraction':multi_volume/root_volume,
                     'still_multi_boundary_subtet_count':int(multi.sum()),
                     'cumulative_one_boundary_subtets':int(cumulative_counts[2]),
                     'total_active_subtets_checked_at_level':len(active),
                     'physical_volume_partition_closure_relative':balance})
        if not np.any(multi):
            break
        if depth<max_depth:
            active=py.bisect_longest_curved_edge(active[multi],vertices[multi])
    return {'element_id':case['original_element_id'],
            'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
            'initial_child_reference_depth':case['depth'],
            'original_child_volume_m3':root_volume,
            'level_records':rows}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mesh',type=Path,required=True)
    ap.add_argument('--selection',type=Path,required=True)
    ap.add_argument('--algoim',type=Path,required=True)
    ap.add_argument('--max-depth',type=int,default=8)
    ap.add_argument('--output',type=Path,default=Path('P10QJ_M8_TWO_BOUNDARY_H_SUBDIVISION_QA.json'))
    args=ap.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    sel=json.loads(args.selection.read_text());algoim=json.loads(args.algoim.read_text())
    if sha!=m8.PINNED_M8_SHA256 or any(x['mesh_sha256']!=sha for x in (sel,algoim)):
        raise ValueError('P10QJ_H_DIVISION_M8_SHA_MISMATCH')
    if not(0<=args.max_depth<=10) or len(sel['cases'])!=8:
        raise ValueError('P10QJ_BAD_H_PARAMETER_OR_CASES')
    output=[]
    for case in sel['cases']:
        a=analyze_one(case,args.max_depth)
        rec=a['level_records'][-1]
        print(f'P10QJ_H_DIAGNOSTIC elem={case["original_element_id"]} '
              f'r={case["radial_bin"]} mu={case["mu_bin"]} '
              f'multi_h{rec["h_level"]}={rec["unresolved_at_least_two_boundary_volume_fraction"]:.8g} '
              f'one_h{rec["h_level"]}={rec["cumulative_one_boundary_volume_fraction"]:.8g} '
              f'unresolved_cells={rec["still_multi_boundary_subtet_count"]}',flush=True)
        output.append(a)
    status='PASS_CONSERVATIVE_TRUE_M8_H_BUDGET_DIAGNOSTIC_NOT_CUT_INTEGRATION'
    out={'stage':'P10QJ','status':status,'mesh_sha256':sha,
         'mesh_changed':False,'Gmsh_run':False,'physical_FEM_run':False,
         'max_h_level':args.max_depth,'case_count':len(output),'cases':output,
         'volume_weights':'true positive curved M8 Tet10 detJ integrated by exact degree-three Duffy q4',
         'remaining_multi_bound_fraction_bounded_not_integrated':True,
         'full_48_bin_quadrature_converged':False,
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QJ_REAL_CURVED_H_SUBDIVISION_BUDGET_PASS',flush=True)


if __name__=='__main__':
    main()
