#!/usr/bin/env python3
"""Stage3D07 P10QF: curved-Tet10 face-aware spherical FE integration pilot.

Local q2/q4 mismatch remains an *empirical* error indicator, NOT a
certified error upper bound. Unlike P10QE's physical-width-only splitting,
we choose the spherical subdivision axis using crossings of actual curved
Tet10 element IDs at q4 quadrature nodes, with physical width fallback.

True M8 Tet10 inverse mapping at EVERY node. No Gmsh, no mesh edits,
no 4D physical FEM/EDV/adjoint. All 4 polar test bins are pinned to M8.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import heapq
import json
import math
from pathlib import Path
import time

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QE_M8_ADAPTIVE_SPHERICAL_FE_PILOT as qe
from P10QD_M8_SPHERICAL_TET10_POINT_LOCATION import CurvedTet10Locator


def widths(box):
    r0,r1,m0,m1,p0,p1=box
    r=.5*(r0+r1)
    mu=.5*(m0+m1)
    transversal=math.sqrt(max(0.,1-mu*mu))
    return (r1-r0,r*(m1-m0)/max(transversal,1e-5),
            r*transversal*(p1-p0))


def bisect(box,dim):
    l=list(box)
    a=2*dim
    mid=.5*(l[a]+l[a+1])
    lo=l.copy();hi=l.copy()
    lo[a+1]=mid;hi[a]=mid
    return tuple(lo),tuple(hi)


def local_integral(locator,X,box,q):
    pts,w=qe.sphere_box_points(box,q)
    values=np.empty(len(pts),dtype=float)
    ids=np.empty(len(pts),dtype=np.int32)
    for i,p in enumerate(pts):
        k,uvw=locator.locate(p)
        if k is None:
            raise ValueError(f'QF_STOP_UNLOCATED_REAL_M8_TET10_POINT {p}')
        n,g=m8.tet10_shape(uvw)
        values[i]=float(n@(((X[k,:,2]-.03)/.0015)**3))
        ids[i]=k
    return float(w@values),ids


def cell_integrate(locator,X,box,depth):
    q2,id2=local_integral(locator,X,box,2)
    q4,id4=local_integral(locator,X,box,4)
    elem=id4.reshape((4,4,4))
    transitions=[int(np.count_nonzero(elem[1:]!=elem[:-1])),
                 int(np.count_nonzero(elem[:,1:]!=elem[:,:-1])),
                 int(np.count_nonzero(elem[:,:,1:]!=elem[:,:,:-1]))]
    count=int(len(np.unique(id4)))
    physical=widths(box)
    if max(transitions)>0:
        # Lexicographic rule: actual face transitions before physical
        # dimension. Normalize by the maximum physical width on ties.
        choice=int(max(range(3),key=lambda i:(transitions[i],physical[i])))
        mode='FACE_TRANSITION_OBSERVED'
    else:
        choice=int(np.argmax(physical))
        mode='PHYSICAL_WIDTH_FALLBACK'
    return {'box':box,'depth':depth,'v2':q2,'v4':q4,
            'indicator_abs_m3':abs(q4-q2),
            'face_transition_counts':transitions,
            'distinct_elements_at_q4':count,
            'split_axis':choice,'split_rule':mode,
            'points':len(id2)+len(id4)}


def adaptive_one(locator,X,ir,im,ip,reference,target,max_depth,max_nodes):
    begin=time.monotonic()
    c=cell_integrate(locator,X,qe.bin_box(ir,im,ip),0)
    pq=[(-c['indicator_abs_m3'],0,c)]
    idserial=1;nodes=c['points'];splits=0;leaves=1
    integ=c['v4'];l1=c['indicator_abs_m3'];maxdeep=0
    modes=Counter();axes=Counter();distinctmax=c['distinct_elements_at_q4']
    facecrosses=0;discarded_deep=0;progress=[]
    while (l1>target*abs(reference) and
           nodes+2*72<=max_nodes and pq):
        _,_,c=heapq.heappop(pq)
        if c['depth']>=max_depth:
            discarded_deep+=1
            continue
        mode=c['split_rule'];axis=c['split_axis']
        child=[]
        for part in bisect(c['box'],axis):
            v=cell_integrate(locator,X,part,c['depth']+1)
            child.append(v)
            heapq.heappush(pq,(-v['indicator_abs_m3'],idserial,v))
            idserial+=1;nodes+=v['points']
            distinctmax=max(distinctmax,v['distinct_elements_at_q4'])
        modes[mode]+=1;axes[axis]+=1
        facecrosses+=sum(c['face_transition_counts'])
        integ+=sum(v['v4'] for v in child)-c['v4']
        l1+=sum(v['indicator_abs_m3'] for v in child)-c['indicator_abs_m3']
        splits+=1;leaves+=1
        maxdeep=max(maxdeep,max(v['depth'] for v in child))
        if splits%100==0 or time.monotonic()-begin>15*(len(progress)+1):
            row={'splits':splits,'nodes':nodes,
                 'L1_local_indicator_rel':l1/abs(reference),
                 'vs_q24_relative':abs(integ-reference)/abs(reference)}
            progress.append(row)
            print(f'P10QF_HEARTBEAT r={ir} mu={im} phi={ip} '
                  f'nodes={nodes} indicator={row["L1_local_indicator_rel"]:.6g} '
                  f'delta_q24={row["vs_q24_relative"]:.6g}',flush=True)
    met=l1<=target*abs(reference)
    return {'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
            'q24_reference_FE_cubic_m3':reference,
            'adaptive_face_aware_FE_cubic_m3':integ,
            'L1_local_q2_q4_indicator_m3':l1,
            'L1_local_q2_q4_indicator_relative_q24':l1/abs(reference),
            'adaptive_vs_q24_relative':abs(integ-reference)/abs(reference),
            'target_indicator_relative':target,'met_empirical_indicator_target':met,
            'nodes_evaluated':nodes,'max_nodes':max_nodes,'max_depth':max_depth,
            'max_depth_observed':maxdeep,'binary_splits':splits,
            'terminal_leaf_count':leaves,
            'face_transition_splits':modes['FACE_TRANSITION_OBSERVED'],
            'physical_width_fallback_splits':modes['PHYSICAL_WIDTH_FALLBACK'],
            'split_axes_radial_mu_phi':[axes[i] for i in range(3)],
            'max_distinct_Tet10_at_one_q4_subbox':distinctmax,
            'observed_adjacent_q4_node_face_crossings_in_split_cells':facecrosses,
            'capped_depth_leaves':discarded_deep,
            'elapsed_s':time.monotonic()-begin,'progress':progress,
            'limitations':'Transitions are observed only at quadrature nodes, not guaranteed to reveal all curved face crossings; q2-q4 is not an error bound; q24 is not exact.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--high-q',type=Path,required=True)
    p.add_argument('--p10qe-baseline',type=Path,required=True)
    p.add_argument('--target',type=float,default=1e-6)
    p.add_argument('--max-depth',type=int,default=12)
    p.add_argument('--max-nodes',type=int,default=60000)
    p.add_argument('--output',type=Path,default=Path('P10QF_M8_FACE_AWARE_SPHERICAL_FE_QA.json'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    high=json.loads(args.high_q.read_text())
    old=json.loads(args.p10qe_baseline.read_text())
    if sha!=m8.PINNED_M8_SHA256 or high['mesh_sha256']!=sha or old['mesh_sha256']!=sha:
        raise ValueError('P10QF_M8_PIN_OR_PRIOR_REPORT_MISMATCH')
    if old['cases'][0]['target_relative_to_q24']!=args.target or old['cases'][0]['node_cap']!=args.max_nodes:
        raise ValueError('Different work budgets: not a fair P10QE comparison')
    xyz,conn,*_=m8.parse_msh(args.mesh)
    X=xyz[conn]
    locator=CurvedTet10Locator(X)
    old_cases={(a['radial_bin'],a['mu_bin'],a['phi_bin']):a for a in old['cases']}
    results=[]
    for b in high['bins']:
        ir,im,ip=[b[k] for k in ('radial_bin','mu_bin','phi_bin')]
        reference=next(r['FE_nodal_cubic_moment_m3'] for r in b['q_records'] if r['q']==24)
        prev=old_cases[ir,im,ip]
        current=adaptive_one(locator,X,ir,im,ip,reference,args.target,args.max_depth,args.max_nodes)
        current['P10QE_width_only_nodes']=prev['spherical_point_evaluations']
        current['P10QE_width_only_indicator_rel']=prev['adaptive_L1_indicator_relative_q24']
        current['P10QE_width_only_vs_q24_rel']=prev['adaptive_vs_independent_q24_relative']
        current['P10QE_width_only_target_met']=prev['met_indicator_target']
        results.append(current)
        print(f'P10QF_CASE_{len(results)}/4 '
              f'face_nodes={current["nodes_evaluated"]} '
              f'face_indicator={current["L1_local_q2_q4_indicator_relative_q24"]:.6g} '
              f'face_target_met={current["met_empirical_indicator_target"]} '
              f'vs_q24={current["adaptive_vs_q24_relative"]:.6g}',flush=True)
    out={'stage':'P10QF','status':'PASS_FACE_TRANSITION_AWARE_FE_QUADRATURE_PILOT_NOT_PHYSICS',
         'mesh_sha256':sha,'mesh_changed':False,'fem_started':False,'gmsh_generated':False,
         'q2_q4_indicator_is_error_certificate':False,
         'face_transition_detection_is_continuous_proof':False,
         'q24_reference_is_exact':False,
         'cases':results,'case_count':len(results),
         'face_aware_total_nodes':sum(x['nodes_evaluated'] for x in results),
         'P10QE_width_only_total_nodes':sum(x['P10QE_width_only_nodes'] for x in results),
         'face_aware_indicator_targets_met':sum(x['met_empirical_indicator_target'] for x in results),
         'P10QE_indicator_targets_met':sum(x['P10QE_width_only_target_met'] for x in results),
         'face_aware_max_vs_q24_rel':max(x['adaptive_vs_q24_relative'] for x in results),
         'P10QE_max_vs_q24_rel':max(x['P10QE_width_only_vs_q24_rel'] for x in results),
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'],flush=True)


if __name__=='__main__':
    main()
