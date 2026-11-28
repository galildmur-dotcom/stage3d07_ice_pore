#!/usr/bin/env python3
"""P10QH gradient discontinuity stress test of spherical FE quadrature.

Compare P10QF face-label-aware splits versus physical-width splits for the
*actual* piecewise curved Tet10 manufactured z derivative. The two policies
use identical q2/q4 local estimators and equal node budgets. Independent q32
holdout is not a certified exact integral. No physical FEM run.
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
import P10QD_M8_SPHERICAL_TET10_POINT_LOCATION as qd
import P10QE_M8_ADAPTIVE_SPHERICAL_FE_PILOT as qe
import P10QF_M8_FACE_AWARE_SPHERICAL_FE_PILOT as qf
import P10QG_M8_STRESSLIKE_TET10_GRADIENT_Q_SERIES as qg


def evaluate(locator,X,box,q):
    pts,weights=qe.sphere_box_points(box,q)
    values=np.empty(len(pts));ids=np.empty(len(pts),dtype=np.int32)
    for i,pt in enumerate(pts):
        k,u=locator.locate(pt)
        if k is None:
            raise ValueError('P10QH_GRADIENT_POINT_NOT_FOUND_IN_M8')
        zz=(X[k,:,2]-.03)/qg.SCALE
        values[i],_=qg.physical_z_gradient(X[k],u,zz**3)
        ids[i]=k
    return float(weights@values),ids


def cell(locator,X,box,depth,method):
    v2,_=evaluate(locator,X,box,2)
    v4,ids=evaluate(locator,X,box,4)
    labels=ids.reshape(4,4,4)
    crossing=[int(np.count_nonzero(labels[1:]!=labels[:-1])),
              int(np.count_nonzero(labels[:,1:]!=labels[:,:-1])),
              int(np.count_nonzero(labels[:,:,1:]!=labels[:,:,:-1]))]
    widths=qf.widths(box)
    if method=='face' and max(crossing)>0:
        axis=int(max(range(3),key=lambda k:(crossing[k],widths[k])))
        selected='observed_crossing'
    else:
        axis=int(np.argmax(widths));selected='physical_width'
    return {'box':box,'depth':depth,'v2':v2,'v4':v4,
            'indicator':abs(v4-v2),'axis':axis,'rule':selected,
            'face_crossings':crossing,'number_of_Tet10':len(set(ids))}


def adapt(locator,X,ir,im,reference,method,max_nodes,max_depth):
    begin=time.monotonic()
    top=cell(locator,X,qe.bin_box(ir,im,0),0,method)
    pq=[(-top['indicator'],0,top)];next_id=1;nodes=72
    moment=top['v4'];indicator=top['indicator'];splits=0
    axes=Counter();modes=Counter();capped=0
    while pq and nodes+144<=max_nodes:
        _,_,parent=heapq.heappop(pq)
        if parent['depth']>=max_depth:
            capped+=1
            continue
        children=[]
        for subbox in qf.bisect(parent['box'],parent['axis']):
            child=cell(locator,X,subbox,parent['depth']+1,method)
            children.append(child)
            heapq.heappush(pq,(-child['indicator'],next_id,child))
            next_id+=1
        nodes+=144;splits+=1
        modes[parent['rule']]+=1;axes[parent['axis']]+=1
        moment+=sum(x['v4'] for x in children)-parent['v4']
        indicator+=sum(x['indicator'] for x in children)-parent['indicator']
        if splits%100==0:
            print(f'P10QH_GRAD_HEARTBEAT {method} r={ir} mu={im} '
                  f'nodes={nodes} L1local={indicator/abs(reference):.6g}',flush=True)
    return {'radial_bin':ir,'mu_bin':im,'phi_bin':0,'policy':method,
            'q2_q4_node_evaluations':nodes,'node_cap':max_nodes,
            'binary_splits':splits,'max_depth':max_depth,
            'adaptive_gradient_moment_m3':moment,
            'L1_local_q2_q4_indicator_m3':indicator,
            'L1_local_indicator_relative_to_q32':indicator/abs(reference),
            'relative_difference_to_independent_q32':abs(moment-reference)/abs(reference),
            'face_crossing_driven_splits':modes['observed_crossing'],
            'width_driven_splits':modes['physical_width'],
            'split_axis_counts_radial_mu_phi':[axes[k] for k in range(3)],
            'capped_depth_priority_cells':capped,'elapsed_s':time.monotonic()-begin}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mesh',type=Path,required=True)
    ap.add_argument('--prior-gradient',type=Path,required=True)
    ap.add_argument('--max-nodes',type=int,default=24000)
    ap.add_argument('--max-depth',type=int,default=13)
    ap.add_argument('--q-holdout',type=int,default=32)
    ap.add_argument('--output',type=Path,default=Path('P10QH_M8_DISCONTINUOUS_GRADIENT_ADAPTIVE_QA.json'))
    args=ap.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    previous=json.loads(args.prior_gradient.read_text())
    if sha!=m8.PINNED_M8_SHA256 or previous['mesh_sha256']!=sha or args.max_nodes<216 or args.q_holdout<24:
        raise ValueError('P10QH_GRADIENT_INVALID_PIN_OR_SETTINGS')
    xyz,conn,*_=m8.parse_msh(args.mesh);X=xyz[conn]
    locator=qd.CurvedTet10Locator(X)
    result=[];holdouts=[]
    beginning=time.monotonic()
    for ir in (0,4):
        for im in (0,9):
            r=qe.bin_box(ir,im,0)
            reference,ids=evaluate(locator,X,r,args.q_holdout)
            prior=next(x for x in previous['four_bins'] if x['radial_bin']==ir and x['mu_bin']==im)
            q24=next(x['normalized_cubic_FE_z_gradient_moment_m3'] for x in prior['q_records'] if x['q']==24)
            holdouts.append({'radial_bin':ir,'mu_bin':im,'phi_bin':0,
                             'q_holdout':args.q_holdout,'q_holdout_evaluations':args.q_holdout**3,
                             'q32_gradient_moment_m3':reference,
                             'previous_q24_gradient_moment_m3':q24,
                             'q24_q32_relative_difference':abs(reference-q24)/abs(reference),
                             'distinct_real_Tet10_at_q32':len(set(ids))})
            print(f'P10QH_HOLDOUT r={ir} mu={im} '
                  f'q24_q32_rel={abs(reference-q24)/abs(reference):.8g}',flush=True)
            for method in ('width','face'):
                record=adapt(locator,X,ir,im,reference,method,args.max_nodes,args.max_depth)
                result.append(record)
                print(f'P10QH_GRADIENT_POLICY {method} r={ir} mu={im} '
                      f'vs_q32={record["relative_difference_to_independent_q32"]:.8g} '
                      f'indicator={record["L1_local_indicator_relative_to_q32"]:.8g}',flush=True)
    compare=[]
    for h in holdouts:
        ir,im=h['radial_bin'],h['mu_bin']
        width=next(x for x in result if x['radial_bin']==ir and x['mu_bin']==im and x['policy']=='width')
        face=next(x for x in result if x['radial_bin']==ir and x['mu_bin']==im and x['policy']=='face')
        if width['q2_q4_node_evaluations']!=face['q2_q4_node_evaluations']:
            raise ValueError('P10QH_UNEQUAL_NODE_BUDGET_COMPARISON')
        compare.append({'radial_bin':ir,'mu_bin':im,'equal_nodes':width['q2_q4_node_evaluations'],
                        'width_indicator_rel':width['L1_local_indicator_relative_to_q32'],
                        'face_indicator_rel':face['L1_local_indicator_relative_to_q32'],
                        'width_vs_q32_rel':width['relative_difference_to_independent_q32'],
                        'face_vs_q32_rel':face['relative_difference_to_independent_q32'],
                        'face_policy_has_lower_L1_indicator':face['L1_local_indicator_relative_to_q32']<width['L1_local_indicator_relative_to_q32'],
                        'face_policy_closer_to_q32':face['relative_difference_to_independent_q32']<width['relative_difference_to_independent_q32']})
    deltas=[];q32=[]
    for h in holdouts:
        a=next(x for x in result if x['policy']=='face' and x['radial_bin']==h['radial_bin'] and x['mu_bin']==h['mu_bin'])
        q32.append(h['q32_gradient_moment_m3'])
        deltas.append(a['adaptive_gradient_moment_m3']-h['q32_gradient_moment_m3'])
    out={'stage':'P10QH','status':'PASS_EQUAL_BUDGET_ACTUAL_TET10_GRADIENT_FACE_AWARE_VS_WIDTH_EMPIRICAL',
         'mesh_sha256':sha,'mesh_changed':False,'Gmsh_run':False,'physical_FEM_run':False,
         'field':'piecewise actual curved Tet10 physical z gradient of nodal interpolated cubic; not physical stress',
         'holdout_is_exact':False,'q2_q4_indicator_is_certified_bound':False,
         'q2_q4_local_indicator_can_miss_face_jumps':True,
         'holdouts':holdouts,'equal_work_cases':compare,'runs':result,
         'face_policy_L1_abs_signed_q32_discrepancy':{
             'L1_absolute_relative_to_q32_L1':float(np.sum(np.abs(deltas))/np.sum(np.abs(q32))),
             'signed_absolute_relative_to_q32_L1':float(abs(np.sum(deltas))/np.sum(np.abs(q32))),
             'positive_deltas':int(np.count_nonzero(np.array(deltas)>0)),
             'negative_deltas':int(np.count_nonzero(np.array(deltas)<0))},
         'runtime_seconds':time.monotonic()-beginning,
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QH_PASS_GRADIENT_EQUAL_BUDGET_PILOT',flush=True)


if __name__=='__main__':
    main()
