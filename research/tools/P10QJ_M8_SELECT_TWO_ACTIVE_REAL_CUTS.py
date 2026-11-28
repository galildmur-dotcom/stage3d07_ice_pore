#!/usr/bin/env python3
"""P10QJ: select real M8 curved Tet10 children with 1 quartic+1 quadratic.

Five of six bin inequalities are NOT assumed to be absent: exactly four
must be proven *inside* by conservative actual P2/P4 Bernstein bounds,
and one quartic plus one quadratic may cross. Independent lattice points
must see all four signed intersections, ruling out disjoint surfaces.
No Gmsh, mesh edits, FEM or physics.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10PZ_M8_DIRECT_BERNSTEIN_PREFILTER as pz
import P10QB_M8_SELECT_SINGLE_QUARTIC_CHILDREN as qb
import P10QC_M8_SELECT_SINGLE_QUADRATIC_CHILDREN as qc
import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi

QUARTIC=(0,1,3)
QUADRATIC=(2,4,5)
BARY=np.array([v for v in itertools.product(range(7),repeat=4) if sum(v)==6],dtype=float)/6.


def find_one(X,ir,im,ip,min_depth=2,max_depth=9):
    active=py.REF_TET[None].copy()
    visited=0
    for depth in range(max_depth+1):
        if len(active)==0:
            break
        ctrl,vertices=pz.restricted_control_net(X,active)
        status=qb.hybrid_status(ctrl,ir,im,ip)
        excluded=np.any(status==-1,axis=1)
        inside=np.all(status==1,axis=1)
        unresolved=~excluded&~inside
        visited+=len(active)
        if depth>=min_depth:
            two=(np.sum(status==0,axis=1)==2)&(
                np.sum(status[:,QUARTIC]==0,axis=1)==1)&(
                np.sum(status[:,QUADRATIC]==0,axis=1)==1)&unresolved
            for k in np.flatnonzero(two):
                quartic=QUARTIC[int(np.flatnonzero(status[k,list(QUARTIC)]==0)[0])]
                quadratic=QUADRATIC[int(np.flatnonzero(status[k,list(QUADRATIC)]==0)[0])]
                sample=BARY@active[k]
                a=qb.physical_quartic(X,sample,ir,quartic)
                b=qc.true_quadratic_sign(X,sample,im,ip,quadratic)
                if not(a.min()<-1e-20 and a.max()>1e-20 and
                       b.min()<-1e-12 and b.max()>1e-12):
                    continue
                combo=np.array([np.sum(((a>0)==qa)&((b>0)==qb_sign))
                                for qa in (False,True) for qb_sign in (False,True)])
                # Separate positive/negative phases of both surfaces must be
                # visible physically; avoid tangential false multi-cuts.
                if min(combo)>=2:
                    return {'depth':depth,'reference_vertices':active[k],
                            'quartic_constraint':int(quartic),
                            'quadratic_constraint':int(quadratic),
                            'constraints_status':status[k].tolist(),
                            'lattice_sign_phase_counts':combo.tolist(),
                            'lattice_quartic_sign_range':list(map(float,[a.min(),a.max()])),
                            'lattice_quadratic_sign_range':list(map(float,[b.min(),b.max()])),
                            'search_reference_cells_visited':visited}
        if depth<max_depth:
            active=py.bisect_longest_curved_edge(active[unresolved],vertices[unresolved])
    return None


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mesh',type=Path,required=True)
    ap.add_argument('--max-elements-per-sector',type=int,default=300)
    ap.add_argument('--max-depth',type=int,default=9)
    ap.add_argument('--output',type=Path,default=Path('P10QJ_M8_TWO_ACTIVE_CURVED_SELECTION_QA.json'))
    ap.add_argument('--worker-input',type=Path,default=Path('P10QJ_M8_TWO_ACTIVE_TET10_GRADIENT_CHILDREN.txt'))
    args=ap.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    if sha!=m8.PINNED_M8_SHA256 or args.max_depth>10:
        raise ValueError('P10QJ_INVALID_M8_OR_DEPTH')
    xyz,conn,ids,*_=m8.parse_msh(args.mesh)
    X=xyz[conn]
    raw=X.copy()
    for k,(a,b) in enumerate(py.EDGES,start=4):
        raw[:,k]=2*X[:,k]-.5*(X[:,a]+X[:,b])
    lo=raw.min(axis=1)-m8.CENTER;hi=raw.max(axis=1)-m8.CENTER
    rng=np.random.default_rng(20261128)
    results=[];work=0
    choices=[(r,m,p) for r in (0,4) for m in (0,9) for p in (0,6)]
    for ir,im,ip in choices:
        possible,*_=m8.candidate_masks(lo,hi,ir,im,ip)
        for e in np.flatnonzero(possible)[:args.max_elements_per_sector]:
            sel=find_one(X[e],ir,im,ip,max_depth=args.max_depth)
            if sel is None:
                continue
            work+=sel['search_reference_cells_visited']
            ref=sel.pop('reference_vertices')
            mid=.5*(ref[py.EDGES[:,0]]+ref[py.EDGES[:,1]])
            nodes=py.map_tet10_nodally(X[e],np.concatenate((ref,mid))[None])[0]
            case={'original_element_id':int(ids[e]),'mesh_tet_index':int(e),
                  'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
                  'reference_vertices':ref.tolist(),
                  'physical_child_nodes_10':nodes.tolist(),**sel}
            _,field,poly=qi.test_child(X[e],case,rng)
            case['restricted_parent_FE_P2_nodal_values']=field.tolist()
            case['exact_full_gradient_m3']=poly['exact_full_gradient_m3']
            case['exact_full_volume_m3']=poly['independent_q4_exact_full_volume_m3']
            case['polynomial_numerator_QA']={key:poly[key] for key in (
                'maximum_cubic_polynomial_reproduction_error_m3_per_ref_point',
                'maximum_cofactor_vs_solved_physical_gradient_error',
                'maximum_true_FE_child_parent_trace_error',
                'maximum_radial_cone_quartic_bernstein_error_m2')}
            results.append(case)
            print(f'P10QJ_REAL_DOUBLE_CUT_SELECT case={len(results)} '
                  f'element={case["original_element_id"]} r={ir} mu={im} phi={ip} '
                  f'depth={case["depth"]} boundaries={case["quartic_constraint"]},{case["quadratic_constraint"]} '
                  f'four_phases={case["lattice_sign_phase_counts"]}',flush=True)
            break
    if len(results)<4 or {x['radial_bin'] for x in results}!={0,4} or {x['mu_bin'] for x in results}!={0,9}:
        raise ValueError(f'P10QJ_NOT_ENOUGH_REAL_DOUBLE_CUTS {len(results)}')
    lines=['P10QJ_M8_TRUE_TWO_ACTIVE_GRADIENT_CHILD_V1',str(len(results))]
    for c in results:
        lines.append(' '.join(str(c[key]) for key in (
            'original_element_id','radial_bin','mu_bin','phi_bin','depth',
            'quartic_constraint','quadratic_constraint')))
        lines.extend(' '.join(format(x,'.17g') for x in pt) for pt in c['physical_child_nodes_10'])
        lines.append(' '.join(format(x,'.17g') for x in c['restricted_parent_FE_P2_nodal_values']))
        lines.append(format(c['exact_full_gradient_m3'],'.17g')+' '+
                     format(c['exact_full_volume_m3'],'.17g'))
    args.worker_input.write_text('\n'.join(lines)+'\n')
    report={'stage':'P10QJ','status':'PASS_REAL_M8_TWO_ACTIVE_QUARTIC_QUADRATIC_BERNSTEIN_SELECTION',
            'mesh_sha256':sha,'mesh_changed':False,'Gmsh_run':False,'physical_FEM_run':False,
            'real_curved_child_count':len(results),'sector_count':len(choices),
            'constraints_status':'exactly two active; all other four Bernstein-positive across each whole curved child',
            'all_four_sign_phases_seen_on_independent_84_point_reference_lattice':True,
            'true_parent_FE_field_restriction_checked':True,
            'worker_input_sha256':hashlib.sha256(args.worker_input.read_bytes()).hexdigest(),
            'cases':results,'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('P10QJ_TWO_ACTIVE_REAL_M8_SELECTION_PASS',flush=True)


if __name__=='__main__':
    main()
