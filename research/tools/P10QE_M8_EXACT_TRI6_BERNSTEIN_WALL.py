#!/usr/bin/env python3
"""P10QE: exact-rational Bernstein radius enclosure of genuine M8 pore Tri6.

All decimal coordinates in the ASCII M8.msh are read as exact rationals,
not rounded to binary floating point. Degree-4 Bernstein coefficients of
|F_Tri6-center|^2 are computed exactly, and subtriangle restriction uses
exact integer de Casteljau matrices. Successful output proves the bounds
for EVERY point of EVERY curved Tri6 face, not just for sampled points.

No CAD, mesh operation, FEM, optimization, or physics. Fail closed on caps.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
from functools import reduce
import hashlib
import itertools
import json
import math
from pathlib import Path

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as base

Q2=((2,0,0),(0,2,0),(0,0,2),(1,1,0),(0,1,1),(1,0,1))
Q4=tuple((a,b,4-a-b) for a in range(5) for b in range(5-a))
CHILD_VERTICES=(
    ((1,0,0),(Fraction(1,2),Fraction(1,2),0),(Fraction(1,2),0,Fraction(1,2))),
    ((Fraction(1,2),Fraction(1,2),0),(0,1,0),(0,Fraction(1,2),Fraction(1,2))),
    ((Fraction(1,2),0,Fraction(1,2)),(0,Fraction(1,2),Fraction(1,2)),(0,0,1)),
    ((Fraction(1,2),Fraction(1,2),0),(0,Fraction(1,2),Fraction(1,2)),(Fraction(1,2),0,Fraction(1,2))),
)
M2=[math.factorial(2)//math.prod(math.factorial(i) for i in a) for a in Q2]
M4=[math.factorial(4)//math.prod(math.factorial(i) for i in a) for a in Q4]


def child_matrices():
    """4 integer [15,15] blossom restriction matrices /16, exact."""
    index={tuple(a):i for i,a in enumerate(Q4)}
    out=[]
    for cverts in CHILD_VERTICES:
        rows=[]
        for beta in Q4:
            # Four independent blossom slots: beta_i copies of child vi.
            slot=([0]*beta[0]+[1]*beta[1]+[2]*beta[2])
            row=[0]*15
            for indices in itertools.product(range(3),repeat=4):
                old=tuple(indices.count(i) for i in range(3))
                prod=Fraction(1)
                for i,j in zip(indices,slot):
                    prod*=Fraction(cverts[j][i])
                value=16*prod
                if value.denominator!=1:
                    raise ValueError('Non-integral blossom subdivision entry')
                row[index[old]]+=int(value)
            if sum(row)!=16 or any(v<0 for v in row):
                raise ValueError('De Casteljau control rows must be convex')
            rows.append([(k,v) for k,v in enumerate(row) if v])
        out.append(rows)
    return out


def read_exact_pore_tri6(path):
    nodes={};walls=[];types=Counter();faces=Counter()
    with path.open(encoding='utf-8') as stream:
        for raw in stream:
            line=raw.strip()
            if line=='$MeshFormat' and next(stream).split()!=['2.2','0','8']:
                raise ValueError('Only Gmsh 2.2 ASCII accepted')
            if line=='$Nodes':
                for _ in range(int(next(stream))):
                    row=next(stream).split()
                    nodes[int(row[0])]=tuple(map(Fraction,row[1:]))
            if line=='$Elements':
                for _ in range(int(next(stream))):
                    row=list(map(int,next(stream).split()))
                    typ,n,phys=row[1:4]
                    types[typ]+=1
                    if typ==9:
                        faces[phys]+=1
                        if phys==8:
                            conn=row[3+n:]
                            if len(conn)!=6:
                                raise ValueError('Malformed Tri6 pore wall')
                            walls.append(tuple(nodes[j] for j in conn))
    if len(nodes)!=18331 or types[11]!=12546 or len(walls)!=648:
        raise ValueError('Actual accepted M8 geometry counts mismatch')
    return walls,types,faces


def polynomial_radius_squared(tri):
    center=(Fraction(0),Fraction(0),Fraction('0.03'))
    v=[tuple(pt[k]-center[k] for k in range(3)) for pt in tri]
    bez=v[:3]
    for a,b,k in ((0,1,3),(1,2,4),(2,0,5)):
        bez.append(tuple(2*v[k][j]-(v[a][j]+v[b][j])/2 for j in range(3)))
    lookup={a:k for k,a in enumerate(Q4)}
    coeff=[Fraction(0)]*15
    for i,a in enumerate(Q2):
        for j,b in enumerate(Q2):
            gamma=tuple(a[k]+b[k] for k in range(3))
            dot=sum(bez[i][k]*bez[j][k] for k in range(3))
            coeff[lookup[gamma]]+=Fraction(M2[i]*M2[j],M4[lookup[gamma]])*dot
    return coeff


def restrict_coeffs(matrix, coeff):
    return tuple(sum(coeff[k]*v for k,v in row) for row in matrix)


def certify_one(coeff, lower, upper, matrices, maxdepth, maxnodes):
    denom=math.lcm(*(c.denominator for c in coeff),lower.denominator,upper.denominator)
    num=tuple(int(c*denom) for c in coeff)
    lo=int(lower*denom);hi=int(upper*denom)
    unresolved=[(num,lo,hi,0)]
    visited=0;counts=Counter();deepest=0
    while unresolved:
        c,low,high,depth=unresolved.pop()
        visited+=1
        if visited>maxnodes:
            return {'pass':False,'stop':'MAX_NODES','visited':visited,'depth':depth}
        if min(c)>=low and max(c)<=high:
            counts[depth]+=1
            deepest=max(deepest,depth)
            continue
        if depth>=maxdepth:
            return {'pass':False,'stop':'MAX_DEPTH','visited':visited,'depth':depth,
                    'outward_excess_m2':float(Fraction(max(c)-high,denom*16**depth)),
                    'inward_excess_m2':float(Fraction(low-min(c),denom*16**depth))}
        unresolved.extend((restrict_coeffs(mat,c),low*16,high*16,depth+1)
                          for mat in matrices)
    return {'pass':True,'visited':visited,'depth':deepest,
            'certified_leaf_count':sum(counts.values()),
            'certified_leaf_depth_counts':dict(counts)}


def unit_test_subdivision(matrices):
    for mat in matrices:
        if any(sum(v for _,v in row)!=16 for row in mat):
            raise ValueError('Child polynomial partition-of-unity fails')
    # Constant polynomial exactness and child midpoint interpolation.
    const=(7,)*15
    for mat in matrices:
        if restrict_coeffs(mat,const)!=(112,)*15:
            raise ValueError('Constant preservation fails')
    # Geometry-specific coefficient construction: center and each vertex.
    tet=((Fraction('0.001'),Fraction(0),Fraction('0.03')),
         (Fraction(0),Fraction('0.001'),Fraction('0.03')),
         (Fraction(0),Fraction(0),Fraction('0.031')),
         (Fraction('0.0005'),Fraction('0.0005'),Fraction('0.03')),
         (Fraction(0),Fraction('0.0005'),Fraction('0.0305')),
         (Fraction('0.0005'),Fraction(0),Fraction('0.0305')))
    c=polynomial_radius_squared(tet)
    indices={a:i for i,a in enumerate(Q4)}
    for a in [(4,0,0),(0,4,0),(0,0,4)]:
        if c[indices[a]]!=Fraction('0.000001'):
            raise ValueError('Squared radius at vertices incorrect')
    def bern_eval(coeff,b):
        return sum(coeff[i]*M4[i]*math.prod(b[j]**a for j,a in enumerate(m))
                   for i,m in enumerate(Q4))
    test_b=(Fraction(1,6),Fraction(1,3),Fraction(1,2))
    # The midpoint basis is not linear: evaluate the full actual Tri6 map.
    aa,bb,cc=test_b
    shp=(aa*(2*aa-1),bb*(2*bb-1),cc*(2*cc-1),
         4*aa*bb,4*bb*cc,4*cc*aa)
    mapped=tuple(sum(shp[j]*tet[j][k] for j in range(6)) for k in range(3))
    if bern_eval(c,test_b)!=sum((mapped[k]-(Fraction('.03') if k==2 else 0))**2
                                    for k in range(3)):
        raise ValueError('Quartic Bernstein mapping fails an interior point')
    for mat,vertices in zip(matrices,CHILD_VERTICES):
        child=restrict_coeffs(mat,c)
        old_b=tuple(sum(vertices[j][i]*test_b[j] for j in range(3)) for i in range(3))
        if bern_eval(child,test_b)!=16*bern_eval(c,old_b):
            raise ValueError('Quartic De Casteljau restriction fails nonconstant exact test')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--outer-extra-m',default='0.000000001',
                   help='r_wall <= R+outer-extra-m (exact rational decimal)')
    p.add_argument('--inner-deficit-m',default='0.000001',
                   help='r_wall >= R-inner-deficit-m (exact rational decimal)')
    p.add_argument('--max-depth',type=int,default=13)
    p.add_argument('--max-nodes-per-face',type=int,default=200000)
    p.add_argument('--output',type=Path,default=Path('P10QE_M8_EXACT_TRI6_WALL_QA.json'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    if sha!=base.PINNED_M8_SHA256:
        raise ValueError('Not the accepted immutable M8')
    outer_extra=Fraction(args.outer_extra_m)
    inner_deficit=Fraction(args.inner_deficit_m)
    R=Fraction('0.001')
    if not 0<outer_extra<=Fraction('0.000001') or not 0<inner_deficit<=R:
        raise ValueError('Unsupported radius tolerance')
    lower=(R-inner_deficit)**2
    upper=(R+outer_extra)**2
    matrices=child_matrices()
    unit_test_subdivision(matrices)
    walls,types,faces=read_exact_pore_tri6(args.mesh)
    depths=Counter();visited=0;leaves=0;failed=[]
    for i,tri in enumerate(walls):
        coeff=polynomial_radius_squared(tri)
        a=certify_one(coeff,lower,upper,matrices,args.max_depth,args.max_nodes_per_face)
        visited+=a['visited']
        if a['pass']:
            depths[a['depth']]+=1
            leaves+=a['certified_leaf_count']
        else:
            failed.append({'face_index':i,'audit':a})
        if (i+1)%108==0:
            print(f'P10QE_EXACT_TRI6_PROGRESS {i+1}/648 '
                  f'certified={i+1-len(failed)} failed={len(failed)} '
                  f'total_subtriangles={visited}',flush=True)
    outcome={'stage':'P10QE','status':('PASS_EXACT_RATIONAL_ALL648_TRI6_WALL_RADIUS_ENCLOSURE'
                                     if not failed else 'STOP_UNCERTIFIED_TRI6_WALL'),
             'mesh_sha256':sha,'mesh_changed':False,'fem_started':False,
             'gmsh_generated':False,'HighOrderElastic_mesh_policy_preserved':True,
             'method':'exact rational decimal Gmsh coordinates; degree-4 triangular Bernstein coefficients; integer /16 De Casteljau subdivision',
             'pore_wall_tri6_count':len(walls),
             'target_radius_lower_m':str(R-inner_deficit),
             'target_radius_upper_m':str(R+outer_extra),
             'outer_extra_m':str(outer_extra),'inner_deficit_m':str(inner_deficit),
             'max_depth':args.max_depth,'max_nodes_per_face':args.max_nodes_per_face,
             'faces_certified':len(walls)-len(failed),
             'subtriangles_visited_total':visited,'certified_subtriangle_leaves':leaves,
             'maximum_depth_distribution_per_face':dict(sorted(depths.items())),
             'first_failed_faces':failed[:8],
             'scope':'Exact surface radius enclosure only: no topological proof of entire M8 ice-domain inclusion.',
             'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(outcome,indent=2)+'\n')
    if failed:
        raise SystemExit(f'P10QE_STOP_UNCERTIFIED_TRI6_COUNT={len(failed)} evidence={args.output}')
    print(outcome['status'],flush=True)


if __name__=='__main__':
    main()
