#!/usr/bin/env python3
"""Independent P10QG geometry/gradient scientific audit, fail-closed.

It validates a deep conservative Bezier face separation against a depth-11
AABB-only ablation and independent points on actual curved Tet10 faces.
It also checks the linear manufactured gradient identity and the true C0
trace / discontinuous-gradient phenomenon on genuine shared M8 Tet10 faces.

No geometry/FEM writes or physical 4D approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QG_M8_CONSERVATIVE_CURVED_FACE_CLEARANCE as geom


def actual_spatial_point(box,uvw):
    a,b,c=uvw
    r0,r1,m0,m1,p0,p1=box
    r=r0+a*(r1-r0);mu=m0+b*(m1-m0);phi=p0+c*(p1-p0)
    d=r*math.sqrt(max(0.,1-mu*mu))
    return np.array([d*math.cos(phi),d*math.sin(phi),r*mu])


def check_spherical_enclosures(deep):
    rng=np.random.default_rng(20261128)
    boxes=[x['box'] for b in deep['cases'] for x in b['first_pure_cases']]
    if not boxes:
        raise ValueError('No actual certified-pure spherical boxes to audit')
    n=0;min_clearance=math.inf
    for box in boxes:
        low,hi=geom.spherical_box_aabb(box)
        for u in rng.uniform(0,1,size=(128,3)):
            p=actual_spatial_point(box,u)
            if (p<low-1e-16).any() or (p>hi+1e-16).any():
                raise ValueError('Spherical analytic physical enclosure missed a direct point')
            min_clearance=min(min_clearance,float(np.min(np.r_[p-low,hi-p])))
            n+=1
    return {'independent_uniform_spherical_box_points':n,
            'minimum_observed_spherical_box_to_AABB_face_clearance_m':min_clearance}


def check_true_face_bernstein_projection(X,conn):
    flo,fhi,normals,pmin,pmax,inc=geom.true_unique_tri6_faces(X,conn)
    rng=np.random.default_rng(20261128)
    # Reconstruct the documented iteration order of first-insertion faces
    # independently from volume connectivity; this avoids trusting plotted
    # triangle samples or P10QG's per-face output.
    keys=[];owners={}
    for e,row in enumerate(conn):
        for vertices in geom.FACES:
            key=tuple(sorted(int(row[j]) for j in vertices))
            if key not in owners:
                keys.append(key);owners[key]=(e,vertices)
    if len(keys)!=len(flo) or len(inc)!=25911:
        raise ValueError('Invalid face registry consistency')
    chosen=rng.choice(len(keys),size=128,replace=False)
    tested=0
    for idx in chosen:
        e,vertices=owners[keys[idx]]
        for bary in rng.dirichlet([2,2,2],size=8):
            l=np.zeros(4)
            for j,w in zip(vertices,bary):
                l[j]=w
            N,G=m8.tet10_shape(l[1:])
            p=N@X[e]-m8.CENTER
            proj=float(normals[idx]@p)
            if (p<flo[idx]-1e-13).any() or (p>fhi[idx]+1e-13).any():
                raise ValueError('Bezier face AABB missed actual physical point')
            if not (pmin[idx]-1e-13<=proj<=pmax[idx]+1e-13):
                raise ValueError('Bezier normal projection interval not enclosing curved face')
            tested+=1
    return {'true_curved_Tet10_faces_checked':len(chosen),
            'independent_face_surface_points_checked':tested,
            'all_Bezier_3D_and_normal_projection_enclosures_pass':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--normal-depth11',type=Path,required=True)
    p.add_argument('--normal-deep',type=Path,required=True)
    p.add_argument('--bbox-depth11',type=Path,required=True)
    p.add_argument('--gradient',type=Path,required=True)
    p.add_argument('--topology',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('P10QG_M8_INDEPENDENT_FACE_AND_GRADIENT_QA.json'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    reports=[json.loads(path.read_text()) for path in [args.normal_depth11,args.normal_deep,args.bbox_depth11,args.gradient,args.topology]]
    small,deep,bbox,grad,top=reports
    if sha!=m8.PINNED_M8_SHA256 or any(x['mesh_sha256']!=sha for x in reports):
        raise ValueError('Not all P10QG source-only evidence uses accepted real M8')
    if small['max_depth']!=11 or bbox['max_depth']!=11 or deep['max_depth']<15:
        raise ValueError('AABB/normal ablation or deeper h study missing')
    if not small['face_normal_separation_enabled'] or not deep['face_normal_separation_enabled'] or bbox['face_normal_separation_enabled']:
        raise ValueError('Expected Bezier-normal vs AABB-only ablation not run')
    index=lambda rows:{(x['radial_bin'],x['mu_bin'],x['phi_bin']):x for x in rows}
    s=index(small['cases']);d=index(deep['cases']);b=index(bbox['cases'])
    expected={(r,m,0) for r in (0,4) for m in (0,9)}
    if set(s)!=expected or set(d)!=expected or set(b)!=expected:
        raise ValueError('Four polar bins incomplete')
    bybin=[]
    for key in sorted(expected):
        a,c,z=s[key],d[key],b[key]
        if z['pure_face_clearance_boxes']!=0 or z['certified_pure_volume_fraction_of_ideal']>1e-13:
            raise ValueError('Expected negative AABB-only control changed; re-review science')
        if not (0<a['certified_pure_volume_fraction_of_ideal']<=c['certified_pure_volume_fraction_of_ideal']<=1):
            raise ValueError('Face-normal continuous clearance did not improve with h')
        for row in [a,c,z]:
            if abs(row['pure_volume_m3']+row['ambiguous_volume_upper_m3']-row['ideal_sector_volume_m3'])>1e-11*row['ideal_sector_volume_m3']:
                raise ValueError('Spherical partition physical mass not conserved')
            if row['ambiguous_volume_upper_m3']<0:
                raise ValueError('Negative unresolved upper-bound physical mass')
        bybin.append({'radial_bin':key[0],'mu_bin':key[1],
                      'AABB_only_d11_pure_fraction':z['certified_pure_volume_fraction_of_ideal'],
                      'Bezier_normal_d11_pure_fraction':a['certified_pure_volume_fraction_of_ideal'],
                      'Bezier_normal_deep_pure_fraction':c['certified_pure_volume_fraction_of_ideal'],
                      'deep_visited_subboxes':c['subboxes_visited'],
                      'deep_pure_subboxes':c['pure_face_clearance_boxes']})
    if len(grad['four_bins'])!=4 or grad['independently_evaluated_shared_face_gradient_jumps']['faces_examined_independently']!=96:
        raise ValueError('Required independent discontinuous-gradient pilot missing')
    gj=grad['independently_evaluated_shared_face_gradient_jumps']
    if gj['max_physical_face_position_gap_m']>1e-12 or gj['max_FE_cubic_trace_jump']>1e-10:
        raise ValueError('Curved Tet10 C0 consistency failed')
    if gj['faces_with_nonzero_jump_above_1e_minus_10']<=0:
        raise ValueError('No true FE gradient jump was demonstrated')
    for case in grad['four_bins']:
        for q in case['q_records']:
            if q['nodes']!=q['q']**3 or q['linear_relative_to_exact_ideal_sector_error']>2e-10:
                raise ValueError('Physical Tet10 gradient chain rule failed manufactured linear test')
    for row in grad['sum_absolute_and_signed_q_changes']:
        if row['signed_bin_deltas_relative_to_L1_moment']>row['L1_abs_bin_deltas_relative_to_L1_moment']+1e-14:
            raise ValueError('Impossible signed changes larger than absolute changes')
    xyz,conn,*_=m8.parse_msh(args.mesh)
    X=xyz[conn]
    enclosure=check_spherical_enclosures(deep)
    surface=check_true_face_bernstein_projection(X,conn)
    out={'stage':'P10QG','status':'PASS_INDEPENDENT_CURVED_FACE_CLEARANCE_AND_DISCONTINUOUS_TET10_GRADIENT_PILOT_ONLY',
         'mesh_sha256':sha,'mesh_changed':False,'fem_started':False,'gmsh_generated':False,
         'face_box_numeric_margin_m':deep['coordinate_margin_m'],
         'not_formal_directed_rounding':True,
         'exact_P10QE_wall_certificate_unchanged':top['pore_wall_full_surface_certified'],
         'face_AABB_vs_normal_projection_by_bin':bybin,
         'random_spherical_box_checks':enclosure,
         'random_true_curved_Tet10_face_checks':surface,
         'continuous_FE_traces_and_discontinuous_FE_gradient':gj,
         'gradient_quadrature_L1_q_changes':grad['sum_absolute_and_signed_q_changes'],
         'warning':'Numerical convex hull plus physical margin is conservative broad phase, NOT formal directed-rounded proof. Q series are empirical, not certified physical integration errors.',
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'],flush=True)
    for b in bybin:
        print('GEOMETRIC_CLEARANCE',b['radial_bin'],b['mu_bin'],
              b['Bezier_normal_d11_pure_fraction'],b['Bezier_normal_deep_pure_fraction'],flush=True)


if __name__=='__main__':
    main()
