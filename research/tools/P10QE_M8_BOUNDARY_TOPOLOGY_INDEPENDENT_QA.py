#!/usr/bin/env python3
"""Independent topology, outer-boundary and direct Tri6 checks for P10QE.

Checks geometry manifest without reusing the quartic Bernstein algorithm.
Direct rational checks are verification examples; the separate exact
Bernstein subdivision result is the continuous wall-radius certificate.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as base


def surfaces_and_incidence(path):
    coords={};surfaces=defaultdict(list);vol=[]
    with path.open(encoding='utf-8') as f:
        for raw in f:
            if raw.strip()=='$Nodes':
                for _ in range(int(next(f))):
                    row=next(f).split()
                    coords[int(row[0])]=row[1:]
            if raw.strip()=='$Elements':
                for _ in range(int(next(f))):
                    row=list(map(int,next(f).split()))
                    typ,n,physical=row[1:4]
                    conn=row[3+n:]
                    if typ==9:
                        surfaces[physical].append(tuple(conn))
                    elif typ==11:
                        vol.append(tuple(conn[:4]))
    counts=Counter()
    for tet in vol:
        for group in ((0,1,2),(0,1,3),(0,2,3),(1,2,3)):
            counts[tuple(sorted(tet[k] for k in group))]+=1
    if any(v not in (1,2) for v in counts.values()):
        raise ValueError('Nonmanifold Tet10 corner-face incidence')
    surf_counts={}
    marked=Counter()
    for physical,faces in surfaces.items():
        counts_for_group=Counter()
        for f in faces:
            face=tuple(sorted(f[:3]))
            if face not in counts:
                raise ValueError('Tri6 physical face not found in Tet10 mesh')
            counts_for_group[counts[face]]+=1
            if counts[face]==1:
                marked[face]+=1
        surf_counts[str(physical)]={'face_count':len(faces),
                                   'one_adjacent_Tet10':counts_for_group[1],
                                   'two_adjacent_Tet10':counts_for_group[2]}
    unmarked=[face for face,c in counts.items() if c==1 and marked[face]!=1]
    if unmarked:
        raise ValueError(f'Exposed Tet10 faces unmarked or multiply tagged: {len(unmarked)}')
    # Rigorous quadratic-Bezier convex-hull AABB for all non-pore outer faces.
    external=[]
    for group,faces in surfaces.items():
        if group==8:
            continue
        for face in faces:
            if counts[tuple(sorted(face[:3]))]!=1:
                continue
            X=np.array([[float(x) for x in coords[k]] for k in face])
            ctrl=X.copy()
            for idx,(a,b,k) in enumerate(((0,1,3),(1,2,4),(2,0,5)),start=3):
                ctrl[idx]=2*X[k]-(X[a]+X[b])/2
            lo=ctrl.min(axis=0)-base.CENTER
            hi=ctrl.max(axis=0)-base.CENTER
            mind=np.where((lo<=0)&(hi>=0),0,np.minimum(lo*lo,hi*hi))
            external.append((group,float(math.sqrt(mind.sum()))))
    if not external:
        raise ValueError('External boundary surfaces were not found')
    dmin=min(v for _,v in external)
    if dmin<=.0015:
        raise ValueError('Other mesh physical boundary intersects 1.50mm sphere AABB')
    return {'tet10_corner_face_manifold':True,'unique_topological_faces':len(counts),
            'exposed_tet10_faces':sum(v==1 for v in counts.values()),
            'internal_tet10_faces':sum(v==2 for v in counts.values()),
            'all_exposed_faces_tagged_exactly_once':True,
            'physical_Tri6_face_adjacency':surf_counts,
            'min_non_pore_exposed_surface_radius_certified_by_bezier_AABB_m':dmin}


def direct_tri6_checks(path,lower,upper):
    nodes={};tri=[]
    with path.open(encoding='utf-8') as f:
        for raw in f:
            if raw.strip()=='$Nodes':
                for _ in range(int(next(f))):
                    t=next(f).split();nodes[int(t[0])]=tuple(map(Fraction,t[1:]))
            if raw.strip()=='$Elements':
                for _ in range(int(next(f))):
                    row=list(map(int,next(f).split()))
                    if row[1]==9 and row[3]==8:
                        tri.append(tuple(nodes[k] for k in row[3+row[2]:]))
    if len(tri)!=648:
        raise ValueError('Tri6 wall count mismatch')
    samples=[(Fraction(1,3),Fraction(1,3),Fraction(1,3)),
             (Fraction(1,7),Fraction(2,7),Fraction(4,7)),
             (Fraction(3,11),Fraction(4,11),Fraction(4,11))]
    minr=math.inf;maxr=0.;n=0
    for face in tri:
        for bary in samples:
            a,b,c=bary
            shape=(a*(2*a-1),b*(2*b-1),c*(2*c-1),
                   4*a*b,4*b*c,4*c*a)
            position=tuple(sum(shape[k]*face[k][d] for k in range(6)) for d in range(3))
            rr=sum((position[d]-(Fraction('0.03') if d==2 else 0))**2
                   for d in range(3))
            if not lower**2<=rr<=upper**2:
                raise ValueError('Direct exact rational wall sample outside certificate')
            rad=math.sqrt(float(rr));minr=min(minr,rad);maxr=max(maxr,rad);n+=1
    # Curved face 560 controls the discovered inward extremum; multi-start
    # floating optimization is a diagnostic only, not the certificate.
    x=np.array(tri[560],dtype=float)-base.CENTER
    def square_rad(ab):
        a,b=ab;c=1-a-b
        N=np.array([c*(2*c-1),a*(2*a-1),b*(2*b-1),4*c*a,4*a*b,4*b*c])
        v=N@x
        return v@v
    candidates=[]
    for seed in ((.333,.333),(.25,.5),(.5,.25)):
        r=minimize(lambda u:1e6*square_rad(u),seed,method='SLSQP',
                   bounds=((0,1),(0,1)),
                   constraints=({'type':'ineq','fun':lambda u:1-sum(u)},),
                   options={'ftol':1e-13,'maxiter':200})
        if r.success:
            candidates.append((float(r.fun),[float(v) for v in r.x]))
    if not candidates:
        raise ValueError('Independent wall minimization diagnostic failed')
    best=min(candidates)
    return {'independent_direct_exact_rational_samples':n,
            'min_sampled_radius_m':minr,'max_sampled_radius_m':maxr,
            'face_560_local_minimum_radius_m':math.sqrt(best[0]*1e-6),
            'face_560_local_minimum_barycentric_uv':best[1],
            'face_560_local_inward_deviation_um':(base.PORE_R-math.sqrt(best[0]*1e-6))*1e6,
            'optimization_warning':'Floating constrained minimization is diagnostic, not proof of global minimum.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--wall',type=Path,required=True)
    p.add_argument('--adaptive',type=Path,required=True)
    p.add_argument('--high-q',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('P10QE_M8_INDEPENDENT_QA.json'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    wall=json.loads(args.wall.read_text())
    adapt=json.loads(args.adaptive.read_text())
    high=json.loads(args.high_q.read_text())
    if sha!=base.PINNED_M8_SHA256 or any(x['mesh_sha256']!=sha for x in [wall,adapt,high]):
        raise ValueError('Unpinned or incompatible Stage3D07 evidence')
    if wall['faces_certified']!=648 or wall['first_failed_faces'] or wall['status']!='PASS_EXACT_RATIONAL_ALL648_TRI6_WALL_RADIUS_ENCLOSURE':
        raise ValueError('Exact wall certification absent')
    lower=Fraction(wall['target_radius_lower_m'])
    upper=Fraction(wall['target_radius_upper_m'])
    if (upper-Fraction('0.001'))>Fraction('0.00000000000001'):
        raise ValueError('Not enough upper-wall precision')
    if (Fraction('0.001')-lower)>Fraction('0.000000772'):
        raise ValueError('Inner wall bracket worse than 0.772um')
    topo=surfaces_and_incidence(args.mesh)
    direct=direct_tri6_checks(args.mesh,lower,upper)
    highref={(b['radial_bin'],b['mu_bin'],b['phi_bin']):next(r['FE_nodal_cubic_moment_m3'] for r in b['q_records'] if r['q']==24)
             for b in high['bins']}
    if len(adapt['cases'])!=4:
        raise ValueError('Adaptive field pilot missing cases')
    for case in adapt['cases']:
        key=(case['radial_bin'],case['mu_bin'],case['phi_bin'])
        if key not in highref:
            raise ValueError('Not a high-q pole bin')
        ref=highref[key]
        if abs(ref-case['reference_q24_manufactured_FE_moment_m3'])>1e-20:
            raise ValueError('Independent q24 field benchmark mismatch')
        if not 0<=case['adaptive_L1_indicator_relative_q24']<.01:
            raise ValueError('Invalid adaptive absolute indicator')
        if case['spherical_point_evaluations']>case['node_cap']:
            raise ValueError('Adaptive point budget violation')
        if not case['spherical_point_evaluations']==72*(1+2*case['binary_splits']):
            raise ValueError('Incorrect adaptive work accounting')
    r0=Fraction('0.001')
    r1=Fraction('0.00102')
    max_missing_m3=float(((upper**3-r0**3)/3)*Fraction(1,5))*(math.pi/6)
    ideal_m3=float((r1**3-r0**3)/3*Fraction(1,5))*(math.pi/6)
    result={'stage':'P10QE','status':'PASS_INDEPENDENT_EXACT_WALL_AND_ADAPTIVE_FE_READ_ONLY_QA',
            'mesh_sha256':sha,'fem_started':False,'mesh_changed':False,
            'pore_wall_full_surface_certified':True,
            'wall_radius_lower_m':float(lower),'wall_radius_upper_m':float(upper),
            'domain_topology_and_outer_boundary':topo,
            'independent_wall_sample_and_local_optimization':direct,
            'conditional_missing_sphere_volume_upper_per_nearwall_sector_m3':max_missing_m3,
            'conditional_missing_sphere_volume_upper_relative_to_ideal_nearwall_sector':max_missing_m3/ideal_m3,
            'conditional_volume_warning':'Volume bound assumes sphere-sector membership is controlled only by the pore wall; other exposed faces are proven outside 1.5mm, but this does not certify arbitrary mesh global nonselfintersection.',
            'adaptive_field_four_case_node_count':sum(x['spherical_point_evaluations'] for x in adapt['cases']),
            'adaptive_indicator_is_not_error_bound':True,
            'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'])
    print('CERTIFIED_WALL_RADIUS_INTERVAL',lower,upper)
    print('EXTERNAL_BOUNDARY_MIN_DISTANCE_M',topo['min_non_pore_exposed_surface_radius_certified_by_bezier_AABB_m'])


if __name__=='__main__':
    main()
