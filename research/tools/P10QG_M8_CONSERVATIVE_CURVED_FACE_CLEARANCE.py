#!/usr/bin/env python3
"""P10QG source-only curved Tet10 face clearance for spherical subboxes.

For every unique genuine quadratic Tet10 face, take the complete degree-2
Bezier convex-hull AABB. For any spherical (r,mu,phi) subbox, compute a
conservative physical AABB. If they do NOT overlap, the spherical subbox
cannot cross that Tet10 face. With one valid interior point and conforming
mesh topology, it lies in one Tet10, conditionally on global embedding.

Trigonometric bounds use a protective 5-picometre physical-coordinate
margin (NOT a directed-rounding formal interval certificate). This is a
conservative floating-point broad phase, not exact rational proof.

Does not build/modify meshes or run FEM, EDV, Gmsh, adjoint or physics.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QE_M8_ADAPTIVE_SPHERICAL_FE_PILOT as qe
import P10QF_M8_FACE_AWARE_SPHERICAL_FE_PILOT as qf
from P10QD_M8_SPHERICAL_TET10_POINT_LOCATION import CurvedTet10Locator


FACES=((0,1,2),(0,1,3),(0,2,3),(1,2,3))
EDGE_MID={tuple(sorted((a,b))):k for k,(a,b) in enumerate(m8.EDGE,start=4)}
MARGIN_M=5e-12


def true_unique_tri6_faces(X,conn):
    """All mesh faces including interior faces; fail on P2 nonconformity."""
    registry={};incidence=Counter()
    for e,row in enumerate(conn):
        corners=row[:4]
        for face in FACES:
            key=tuple(sorted(int(corners[k]) for k in face))
            mids=[];mid_local=[]
            for k in range(3):
                edge=tuple(sorted((face[k],face[(k+1)%3])))
                mid_local.append(EDGE_MID[edge])
                mids.append(int(row[mid_local[-1]]))
            mids=tuple(mids)
            # Edge midpoint identity must agree across volume neighbours.
            by_edge={tuple(sorted((int(corners[face[k]]),int(corners[face[(k+1)%3]])))):mids[k]
                     for k in range(3)}
            if key in registry:
                prior=registry[key][0]
                if prior!=by_edge:
                    raise ValueError('Nonconforming real quadratic Tet10 shared face nodes')
            else:
                xyz=np.vstack((X[e,list(face)],X[e,mid_local]))
                be=np.copy(xyz)
                for j,(a,b) in enumerate(((0,1),(1,2),(2,0)),start=3):
                    be[j]=2*xyz[j]-.5*(xyz[a]+xyz[b])
                normal=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0])
                norm=float(np.linalg.norm(normal))
                if norm<=1e-23:
                    raise ValueError('Degenerate physical M8 Tri6 face normal')
                normal/=norm
                projection=(be-m8.CENTER)@normal
                registry[key]=(by_edge,be.min(axis=0)-m8.CENTER,
                               be.max(axis=0)-m8.CENTER,normal,
                               float(projection.min()),float(projection.max()))
            incidence[key]+=1
    if len(registry)!=25911 or any(v not in [1,2] for v in incidence.values()):
        raise ValueError('Actual curved M8 face counts/topology changed')
    lo=np.array([v[1] for v in registry.values()]);hi=np.array([v[2] for v in registry.values()])
    normal=np.array([v[3] for v in registry.values()])
    plane_min=np.array([v[4] for v in registry.values()])
    plane_max=np.array([v[5] for v in registry.values()])
    return lo,hi,normal,plane_min,plane_max,incidence


def extrema_of_trig(func,a,b):
    values=[func(a),func(b)]
    # All sin/cos stationary points occur on the pi/2 lattice; this
    # intentionally includes redundant candidates for both functions.
    for k in range(-8,9):
        angle=k*math.pi/2
        if a<=angle<=b:
            values.append(func(angle))
    return min(values),max(values)


def bound_product(a,b,c,d):
    vals=(a*c,a*d,b*c,b*d)
    return min(vals),max(vals)


def spherical_box_aabb(box):
    """Include whole spherical box in a physical Cartesian AABB.

    The computed analytic extrema are widened by MARGIN_M, >> typical
    binary sin/sqrt rounding at 1.5 mm radius. This numerical protection
    is not a mathematically directed-rounded guarantee.
    """
    r0,r1,mu0,mu1,phi0,phi1=box
    if not (0<r0<=r1 and -1<=mu0<=mu1<=1 and phi0<=phi1):
        raise ValueError('Invalid 4D polar-sector subbox')
    amin=min(abs(mu0),abs(mu1))
    if mu0<=0<=mu1:
        amin=0.
    amax=max(abs(mu0),abs(mu1))
    s0=math.sqrt(max(0.,1-amax*amax))
    s1=math.sqrt(max(0.,1-amin*amin))
    q0,q1=r0*s0,r1*s1
    c0,c1=extrema_of_trig(math.cos,phi0,phi1)
    t0,t1=extrema_of_trig(math.sin,phi0,phi1)
    xx=bound_product(q0,q1,c0,c1)
    yy=bound_product(q0,q1,t0,t1)
    zz=bound_product(r0,r1,mu0,mu1)
    low=np.array([xx[0],yy[0],zz[0]])-MARGIN_M
    high=np.array([xx[1],yy[1],zz[1]])+MARGIN_M
    if (low>high).any():
        raise ValueError('Invalid spherical Cartesian enclosure')
    return low,high


def size_volume(box):
    r0,r1,m0,m1,p0,p1=box
    return (r1**3-r0**3)/3*(m1-m0)*(p1-p0)


def pass_samples_in_pure_box(locator,box,element,rng):
    """Independent *sample* falsification test, not the geometric proof."""
    # Check all corner combinations away from exactly degenerate pole endpoints
    # and random interior points without reusing the center.
    coords=[]
    for a in [0.1,0.9]:
        for b in [0.1,0.9]:
            for c in [0.1,0.9]:
                coords.append((a,b,c))
    coords.extend(rng.uniform(.05,.95,(4,3)))
    r0,r1,m0,m1,p0,p1=box
    for a,b,c in coords:
        r=r0+a*(r1-r0);mu=m0+b*(m1-m0);phi=p0+c*(p1-p0)
        xy=r*math.sqrt(max(0.,1-mu*mu))
        pt=np.array([xy*math.cos(phi),xy*math.sin(phi),.03+r*mu])
        found,_=locator.locate(pt)
        if found!=element:
            raise ValueError('False single-Tet10 face-clearance classification')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--P10QE-topology',type=Path,required=True)
    p.add_argument('--max-depth',type=int,default=11)
    p.add_argument('--case',action='append',default=None,
                   help='optional radial_bin,mu_bin,phi_bin (repeatable); default four pole pilot bins')
    p.add_argument('--sample-pure-per-bin',type=int,default=32)
    p.add_argument('--bbox-only',action='store_true',
                   help='negative control: disable Bezier convex hull face-normal separation')
    p.add_argument('--max-cells-per-bin',type=int,default=25000)
    p.add_argument('--output',type=Path,default=Path('P10QG_M8_CONSERVATIVE_FACE_CLEARANCE_QA.json'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    topology=json.loads(args.P10QE_topology.read_text())
    if sha!=m8.PINNED_M8_SHA256 or topology['mesh_sha256']!=sha:
        raise ValueError('Accepted real M8 pin or topology missing')
    if not topology['domain_topology_and_outer_boundary']['all_exposed_faces_tagged_exactly_once']:
        raise ValueError('Nonconforming M8 physical boundary')
    xyz,conn,*_=m8.parse_msh(args.mesh)
    X=xyz[conn]
    flo,fhi,normal,plane_min,plane_max,inc=true_unique_tri6_faces(X,conn)
    limit=.001600000001
    region=((fhi>=-limit)&(flo<=limit)).all(axis=1)
    flo=flo[region];fhi=fhi[region]
    normal=normal[region];plane_min=plane_min[region];plane_max=plane_max[region]
    locator=CurvedTet10Locator(X)
    bins=[];rng=np.random.default_rng(20261128)
    cases=[(ir,im,0) for ir in [0,4] for im in [0,9]]
    if args.case is not None:
        cases=[tuple(map(int,arg.split(','))) for arg in args.case]
        if len(set(cases))!=len(cases) or any((r not in [0,4] or m not in [0,9] or ip!=0)
                                            for r,m,ip in cases):
            raise ValueError('Only four pinned polar sectors supported')
    for ir,im,ip in cases:
            root=qe.bin_box(ir,im,ip)
            ideal=size_volume(root)
            # Child physical AABB is contained in its parent's (allowing
            # protective margin). Reuse parent face candidates, eliminating
            # O(number_of_all_faces) queries for every deep leaf.
            active=[(root,0,np.arange(len(flo),dtype=np.int32))]
            visited=0;pure=0;pure_vol=0.;ambiguous=0.;uncertain_vol=0.
            pure_cases=[];sampled=0;minhit=1e9;maxhit=0
            count_at_level=Counter();pure_at_level=Counter()
            while active:
                box,depth,candidate=active.pop()
                visited+=1;count_at_level[depth]+=1
                if visited>args.max_cells_per_bin:
                    raise ValueError('P10QG_GEOMETRY_NODE_CAP: fail closed')
                lo,hi=spherical_box_aabb(box)
                overlap=((flo[candidate]<=hi)&(fhi[candidate]>=lo)).all(axis=1)
                possible=candidate[overlap]
                if not args.bbox_only and len(possible):
                    n=normal[possible]
                    # If projections of the whole spherical AABB and the
                    # full curved-face Bezier convex hull onto the face's
                    # vertex-plane normal are disjoint, actual intersection
                    # is impossible. This also rejects slanted faces whose
                    # axis-aligned boxes engulf interior tetra points.
                    qmin=np.sum(np.where(n>=0,lo[None,:],hi[None,:])*n,axis=1)
                    qmax=np.sum(np.where(n>=0,hi[None,:],lo[None,:])*n,axis=1)
                    keep=(qmax>=plane_min[possible]-MARGIN_M)&(qmin<=plane_max[possible]+MARGIN_M)
                    possible=possible[keep]
                count=len(possible)
                minhit=min(minhit,count);maxhit=max(maxhit,count)
                if not count:
                    r0,r1,m0,m1,p0,p1=box
                    r=.5*(r0+r1);mu=.5*(m0+m1);phi=.5*(p0+p1)
                    xy=r*math.sqrt(max(0.,1-mu*mu))
                    pt=np.array([xy*math.cos(phi),xy*math.sin(phi),.03+r*mu])
                    tet,uvw=locator.locate(pt)
                    if tet is None:
                        raise ValueError('Face-clear subbox has no containing curved M8 Tet10')
                    pure+=1;pure_vol+=size_volume(box);pure_at_level[depth]+=1
                    if len(pure_cases)<args.sample_pure_per_bin:
                        pass_samples_in_pure_box(locator,box,tet,rng)
                        sampled+=12
                        pure_cases.append({'depth':depth,'tet10_index':int(tet),
                                           'box':box,'fraction_of_ideal':size_volume(box)/ideal})
                    continue
                if depth>=args.max_depth:
                    ambiguous+=1;uncertain_vol+=size_volume(box)
                else:
                    # Deliberately geometry-only physical-width splitting.
                    # Face *non-overlap* is conservative; label sampling is not
                    # required to decide whether a box is single-element.
                    dim=int(np.argmax(qf.widths(box)))
                    a,b=qf.bisect(box,dim)
                    active.append((a,depth+1,possible))
                    active.append((b,depth+1,possible))
                if visited%4000==0:
                    print(f'P10QG_FACE_CLEARANCE_HEARTBEAT r={ir} mu={im} '
                          f'visited={visited} pure={pure} unresolved={len(active)}',flush=True)
            closure=abs(pure_vol+uncertain_vol-ideal)/ideal
            if closure>1e-11:
                raise ValueError('Spherical subboxes do not physically partition ideal bin')
            result={'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
                    'ideal_sector_volume_m3':ideal,'subboxes_visited':visited,
                    'pure_face_clearance_boxes':pure,'ambiguous_terminal_boxes':ambiguous,
                    'pure_volume_m3':pure_vol,'ambiguous_volume_upper_m3':uncertain_vol,
                    'certified_pure_volume_fraction_of_ideal':pure_vol/ideal,
                    'unresolved_volume_fraction_of_ideal':uncertain_vol/ideal,
                    'volume_partition_closure_relative':closure,
                    'min_face_box_candidate_count':minhit,'max_face_box_candidate_count':maxhit,
                    'subboxes_visited_by_depth':dict(sorted(count_at_level.items())),
                    'pure_subboxes_by_depth':dict(sorted(pure_at_level.items())),
                    'reprojection_falsification_points':sampled,
                    'first_pure_cases':pure_cases[:4]}
            bins.append(result)
            print(f'P10QG_FACE_CLEAR_BIN_{len(bins)}/{len(cases)} r={ir} mu={im} '
                  f'pure_fraction={pure_vol/ideal:.7g} '
                  f'ambiguous_fraction={uncertain_vol/ideal:.7g} '
                  f'boxes={visited} pure={pure}',flush=True)
    out={'stage':'P10QG','status':'PASS_CONSERVATIVE_FLOATING_BERNSTEIN_FACE_CLEARANCE_GEOMETRY_ONLY',
         'mesh_sha256':sha,'mesh_changed':False,'fem_started':False,'gmsh_generated':False,
         'unique_total_curved_faces':len(inc),'region_filtered_faces':len(flo),
         'M8_quadratic_face_conformity_checked':True,
         'face_normal_separation_enabled':not args.bbox_only,
         'coordinate_margin_m':MARGIN_M,
         'numeric_limit':'Trig functions bounded analytically then expanded by 5e-12 m; NOT formally directed-rounded or exact rational certificate.',
         'conditional_topological_assumption':'Face-clearance proves a single Tet10 inside a globally embedded, non-self-intersecting conforming M8 mesh.',
         'max_depth':args.max_depth,'case_count':len(bins),'cases':bins,
         'max_unresolved_mass_fraction':max(c['unresolved_volume_fraction_of_ideal'] for c in bins),
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'],flush=True)


if __name__=='__main__':
    main()
