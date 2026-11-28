#!/usr/bin/env python3
"""Independent accounting and q32 holdout for P10QF face-aware FE pilot.

No numerical q-series can by itself certify absolute error on a piecewise
smooth field. This audit only checks arithmetic invariants, fair workloads,
replay against immutable q24 M8 data, and a separately evaluated q32 holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--face-aware',type=Path,required=True)
    p.add_argument('--width-only',type=Path,required=True)
    p.add_argument('--q24',type=Path,required=True)
    p.add_argument('--q32',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('P10QF_M8_FACE_AWARE_INDEPENDENT_QA.json'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    face=json.loads(args.face_aware.read_text())
    width=json.loads(args.width_only.read_text())
    high=json.loads(args.q24.read_text())
    holdout=json.loads(args.q32.read_text())
    if sha!=m8.PINNED_M8_SHA256 or any(v['mesh_sha256']!=sha for v in [face,width,high,holdout]):
        raise ValueError('P10QF pin mismatch: cannot audit other M8 geometry')
    if len(face['cases'])!=4 or len(holdout['bins'])!=4:
        raise ValueError('Exactly four real polar bins required')
    index=lambda seq:{(b['radial_bin'],b['mu_bin'],b['phi_bin']):b for b in seq}
    face_by=index(face['cases']);width_by=index(width['cases'])
    q24_by=index(high['bins']);q32_by=index(holdout['bins'])
    keys=set(face_by)
    if keys!=set(width_by) or keys!=set(q24_by) or keys!=set(q32_by):
        raise ValueError('Different polar bins between candidates/reference')
    fields=[]
    for key in sorted(keys):
        a=face_by[key];b=width_by[key]
        ref24=next(q['FE_nodal_cubic_moment_m3'] for q in q24_by[key]['q_records'] if q['q']==24)
        rows=q32_by[key]['q_records']
        if len(rows)!=1 or rows[0]['q']!=32:
            raise ValueError('q32 holdout must have one independent order-32 run')
        q32=rows[0]
        if q32['nodes']!=32768 or q32['not_located']!=0:
            raise ValueError('q32 curved Tet10 point evaluation incomplete')
        if abs(q32['relative_to_ideal']-1)>1e-12 or q32['FE_nodal_linear_vs_exact_rel']>1e-12:
            raise ValueError('q32 constant or FE-linear manufactured moment failed')
        if a['nodes_evaluated']!=72*(1+2*a['binary_splits']):
            raise ValueError('Adaptive face-aware q2/q4 work accounting mismatch')
        if a['terminal_leaf_count']!=1+a['binary_splits']:
            raise ValueError('Binary partition leaf mass bookkeeping mismatch')
        if a['face_transition_splits']+a['physical_width_fallback_splits']!=a['binary_splits']:
            raise ValueError('Inconsistent face-aware split type count')
        if sum(a['split_axes_radial_mu_phi'])!=a['binary_splits']:
            raise ValueError('Incorrect split-axis statistics')
        if a['nodes_evaluated']>a['max_nodes'] or b['spherical_point_evaluations']>b['node_cap']:
            raise ValueError('Exceeded user-safe local quadrature node cap')
        if a['met_empirical_indicator_target']!=(a['L1_local_q2_q4_indicator_relative_q24']<=a['target_indicator_relative']+3e-15):
            raise ValueError('False indicator pass flag')
        if abs(ref24-a['q24_reference_FE_cubic_m3'])>2e-20 or abs(ref24-b['reference_q24_manufactured_FE_moment_m3'])>2e-20:
            raise ValueError('Q24 comparison not pinned to same reference')
        if a['max_depth']!=b['maxdepth_cap'] or a['target_indicator_relative']!=b['target_relative_to_q24']:
            raise ValueError('Adaptive comparison changed scientific budget')
        if a['q24_reference_FE_cubic_m3']==0:
            raise ValueError('Invalid zero manufactured FE moment')
        fields.append({'radial_bin':key[0],'mu_bin':key[1],'phi_bin':key[2],
                       'q24_m3':ref24,'q32_holdout_m3':q32['FE_nodal_cubic_moment_m3'],
                       'q24_to_q32_relative':abs(q32['FE_nodal_cubic_moment_m3']-ref24)/abs(q32['FE_nodal_cubic_moment_m3']),
                       'face_aware_m3':a['adaptive_face_aware_FE_cubic_m3'],
                       'width_only_m3':b['adaptive_q4_moment_m3'],
                       'face_indicator_rel_q24':a['L1_local_q2_q4_indicator_relative_q24'],
                       'width_indicator_rel_q24':b['adaptive_L1_indicator_relative_q24'],
                       'face_points':a['nodes_evaluated'],
                       'width_points':b['spherical_point_evaluations'],
                       'face_vs_q32_rel':abs(a['adaptive_face_aware_FE_cubic_m3']-q32['FE_nodal_cubic_moment_m3'])/abs(q32['FE_nodal_cubic_moment_m3']),
                       'width_vs_q32_rel':abs(b['adaptive_q4_moment_m3']-q32['FE_nodal_cubic_moment_m3'])/abs(q32['FE_nodal_cubic_moment_m3'])})
    denom=sum(abs(c['q32_holdout_m3']) for c in fields)
    def l1(key):
        return sum(abs(c[key]-c['q32_holdout_m3']) for c in fields)/denom
    qdelta=np.array([c['q32_holdout_m3']-c['q24_m3'] for c in fields])
    out={'stage':'P10QF','status':'PASS_INDEPENDENT_FOUR_BIN_CURVED_TET10_FACE_AWARE_Q32_HOLDOUT_ONLY',
         'mesh_sha256':sha,'mesh_changed':False,'fem_started':False,'gmsh_generated':False,
         'high_q_holdout_is_exact_certificate':False,
         'L1_q24_vs_q32_relative':l1('q24_m3'),
         'signed_q24_to_q32_relative_to_L1_moment':float(abs(qdelta.sum())/denom),
         'q24_to_q32_positive_bin_changes':int((qdelta>0).sum()),
         'q24_to_q32_negative_bin_changes':int((qdelta<0).sum()),
         'L1_face_aware_vs_q32_relative':l1('face_aware_m3'),
         'L1_width_only_vs_q32_relative':l1('width_only_m3'),
         'face_aware_total_points':sum(c['face_points'] for c in fields),
         'width_only_total_points':sum(c['width_points'] for c in fields),
         'face_aware_indicator_targets_met':sum(c['face_indicator_rel_q24']<=1e-6 for c in fields),
         'width_only_indicator_targets_met':sum(c['width_indicator_rel_q24']<=1e-6 for c in fields),
         'q32_holdout_points':32768*4,'cases':fields,
         'warning':'q32 is a holdout quadrature, not known exact integral; local q2/q4 differences cannot certify error without additional regularity bounds.',
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'])
    print('L1_RELATIVE_TO_Q32 face=',out['L1_face_aware_vs_q32_relative'],
          'width=',out['L1_width_only_vs_q32_relative'],
          'q24=',out['L1_q24_vs_q32_relative'])


if __name__=='__main__':
    main()
