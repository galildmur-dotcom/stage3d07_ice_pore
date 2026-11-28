#!/usr/bin/env python3
"""P10QI: genuine curved-M8 Tet10 gradient polynomial and exact moments.

For each previously audited one-quartic curved child of M8, restrict the
*same parent* manufactured P2 FE field (never re-interpolate nodal z^3 on
child coordinates). Prove by independent random evaluations that
  det(J_child) * 0.0015 * dz f_h
is polynomial of total degree <=3, and calculate its exact reference-
simplex integral via monomial moments. Also verify degree-4 spherical
level-set pullbacks. Source-only; no FEM, Gmsh or mesh mutation.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10PZ_M8_DIRECT_BERNSTEIN_PREFILTER as pz

SCALE=.0015
MONOMIALS=tuple((i,j,k) for n in range(4) for i in range(n+1)
                for j in range(n-i+1) for k in [n-i-j])
REF_NODES=np.concatenate((py.REF_TET,.5*(py.REF_TET[py.EDGES[:,0]]+
                                         py.REF_TET[py.EDGES[:,1]])),axis=0)


def shape_at(points):
    l=np.concatenate((1-points.sum(axis=1,keepdims=True),points),axis=1)
    basis=np.empty((len(points),10));basis[:,:4]=l*(2*l-1)
    for i,(a,b) in enumerate(py.EDGES):
        basis[:,i+4]=4*l[:,a]*l[:,b]
    return basis


def mapped_and_numerator(child_nodes,child_field,u):
    shape,G=m8.tet10_shape(u)
    J=child_nodes.T@G
    a,b,c=J[:,0],J[:,1],J[:,2]
    cof=np.array([np.cross(b,c)[2],np.cross(c,a)[2],np.cross(a,b)[2]])
    det=float(np.linalg.det(J))
    grad=G.T@child_field
    numerator=float(SCALE*cof@grad)
    if not det>0:
        raise ValueError('P10QI_NEGATIVE_CURVED_CHILD_TET10_DET')
    physical=float(SCALE*np.linalg.solve(J.T,grad)[2])
    return shape@child_nodes,numerator,det,physical


def mono_matrix(points):
    return np.column_stack([np.prod(points**np.array(exp),axis=1) for exp in MONOMIALS])


def exact_monomial_integral(exp):
    return math.prod(math.factorial(n) for n in exp)/math.factorial(sum(exp)+3)


def exact_volume_via_duffy(child_nodes):
    u,w=np.polynomial.legendre.leggauss(4)
    u=(u+1)/2;w=w/2
    total=0.
    for a,wa in zip(u,w):
        for b,wb in zip(u,w):
            for c,wc in zip(u,w):
                uvw=np.array([a,(1-a)*b,(1-a)*(1-b)*c])
                _,_,det,_=mapped_and_numerator(child_nodes,np.zeros(10),uvw)
                total+=wa*wb*wc*(1-a)**2*(1-b)*det
    return total


def verify_quartic_pullback(child_nodes,rng):
    controls=child_nodes.copy()
    for k,(a,b) in enumerate(py.EDGES,start=4):
        controls[k]=2*child_nodes[k]-.5*(child_nodes[a]+child_nodes[b])
    radial,cone=pz.true_quartic_coefficients((controls-m8.CENTER)[None])
    bary=rng.dirichlet(np.ones(4),size=128)
    bernstein=np.stack([pz.multinomial(4,a)*np.prod(bary**a,axis=1)
                        for a in pz.ALPHA4],axis=1)
    p=shape_at(bary[:,1:])@child_nodes-m8.CENTER
    actual_r=np.einsum('ij,ij->i',p,p)
    actual_c=.36*p[:,2]**2-.64*(p[:,0]**2+p[:,1]**2)
    residual=max(float(np.max(abs(bernstein@radial[0]-actual_r))),
                 float(np.max(abs(bernstein@cone[0]-actual_c))))
    if residual>3e-17:
        raise ValueError('P10QI_QUARTIC_BERNSTEIN_IDENTITY_FAILED')
    return residual


def test_child(x_parent,case,rng):
    vertices=np.array(case['reference_vertices'],dtype=float)
    bary_nodes=np.column_stack((1-REF_NODES.sum(axis=1),REF_NODES))
    original_pts=bary_nodes@vertices
    child_nodes=shape_at(original_pts)@x_parent
    f_parent=((x_parent[:,2]-.03)/SCALE)**3
    child_field=shape_at(original_pts)@f_parent
    if np.max(abs(child_nodes-np.array(case['physical_child_nodes_10'])))>5e-16:
        raise ValueError('P10QI_CHILD_NOT_SAME_GENUINE_M8')
    grid=np.array([[i/3,j/3,k/3] for i in range(4)
                   for j in range(4-i) for k in range(4-i-j)])
    if grid.shape!=(20,3):
        raise AssertionError('Invalid polynomial identification grid')
    values=np.array([mapped_and_numerator(child_nodes,child_field,u)[1] for u in grid])
    coeff=np.linalg.solve(mono_matrix(grid),values)
    rng_points=rng.dirichlet(np.ones(4),size=256)[:,1:]
    direct=[mapped_and_numerator(child_nodes,child_field,u) for u in rng_points]
    poly=mono_matrix(rng_points)@coeff
    gap=float(np.max(abs(poly-np.array([r[1] for r in direct]))))
    physical_gap=max(abs(r[1]/r[2]-r[3]) for r in direct)
    if gap>2e-19 or physical_gap>1e-10:
        raise ValueError(f'P10QI_CUBIC_GRADIENT_NUMERATOR_IDENTITY_FAILED {gap} {physical_gap}')
    x_from_child=shape_at(rng_points)@child_nodes
    parent_u=(np.column_stack((1-rng_points.sum(axis=1),rng_points))@vertices)
    original_field=shape_at(parent_u)@f_parent
    restricted_field=shape_at(rng_points)@child_field
    err_field=float(np.max(abs(original_field-restricted_field)))
    err_map=float(np.max(abs(x_from_child-shape_at(parent_u)@x_parent)))
    if err_field>3e-12 or err_map>3e-16:
        raise ValueError('P10QI_NOT_ORIGINAL_FE_FIELD_RESTRICTION')
    exact_grad=float(coeff@np.array([exact_monomial_integral(a) for a in MONOMIALS]))
    vol=exact_volume_via_duffy(child_nodes)
    if not math.isfinite(exact_grad) or vol<=0:
        raise ValueError('P10QI_NONPOSITIVE_OR_NONFINITE_REAL_CHILD')
    qerr=verify_quartic_pullback(child_nodes,rng)
    return child_nodes,child_field,{
        'original_element_id':case['original_element_id'],
        'mesh_tet_index':case['mesh_tet_index'],
        'radial_bin':case['radial_bin'],'mu_bin':case['mu_bin'],
        'phi_bin':case['phi_bin'],'depth':case['depth'],
        'active_quartic':case['quartic_constraint'],
        'exact_full_gradient_m3':exact_grad,
        'independent_q4_exact_full_volume_m3':vol,
        'maximum_cubic_polynomial_reproduction_error_m3_per_ref_point':gap,
        'maximum_cofactor_vs_solved_physical_gradient_error':float(physical_gap),
        'maximum_true_FE_child_parent_trace_error':err_field,
        'maximum_true_quadratic_child_parent_map_error_m':err_map,
        'maximum_radial_cone_quartic_bernstein_error_m2':qerr,
        'child_polynomial_monomial_coefficients':coeff.tolist(),
        'monomial_exponents':list(MONOMIALS)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_QA.json'))
    p.add_argument('--worker-input',type=Path,default=Path('P10QI_M8_REFERENCE_GRADIENT_CHILDREN.txt'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    selected=json.loads(args.selection.read_text())
    if sha!=m8.PINNED_M8_SHA256 or selected['mesh_sha256']!=sha or len(selected['cases'])!=8:
        raise ValueError('P10QI_PINNED_M8_OR_CASE_SELECTION_MISMATCH')
    xyz,conn,ids,*_=m8.parse_msh(args.mesh)
    lookup={int(i):k for k,i in enumerate(ids)}
    rng=np.random.default_rng(20261128)
    lines=['P10QI_M8_TET10_GRADIENT_CHILD_V1',str(len(selected['cases']))]
    cases=[]
    for case in selected['cases']:
        k=lookup[case['original_element_id']]
        if k!=case['mesh_tet_index'] or sum(s==0 for s in case['constraints_status'])!=1:
            raise ValueError('P10QI_SELECTOR_NOT_SINGLE_TRUE_QUARTIC')
        X=xyz[conn[k]]
        child,f,rec=test_child(X,case,rng)
        cases.append(rec)
        lines.append(' '.join(str(case[key]) for key in ('original_element_id','radial_bin',
                        'mu_bin','phi_bin','depth','quartic_constraint')))
        lines.extend(' '.join(format(x,'.17g') for x in pt) for pt in child)
        lines.append(' '.join(format(x,'.17g') for x in f))
        lines.append(format(rec['exact_full_gradient_m3'],'.17g')+' '+
                     format(rec['independent_q4_exact_full_volume_m3'],'.17g'))
        print(f'P10QI_PREFLIGHT_CASE_{len(cases)}/8 elem={case["original_element_id"]} '
              f'cubic_gap={rec["maximum_cubic_polynomial_reproduction_error_m3_per_ref_point"]:.3g} '
              f'quartic_gap={rec["maximum_radial_cone_quartic_bernstein_error_m2"]:.3g}',flush=True)
    args.worker_input.write_text('\n'.join(lines)+'\n')
    out={'stage':'P10QI','status':'PASS_REAL_M8_TET10_CUBIC_GRADIENT_AND_QUARTIC_SECTOR_POLYNOMIALS',
         'mesh_sha256':sha,'mesh_changed':False,'Gmsh_generated':False,
         'physical_FEM_started':False,'real_child_count':len(cases),
         'input_format':'Original accepted M8 curvature and P2 parent FE field restricted exactly to real child Tet10',
         'gradient_numerator_degree_upper_bound':3,'squared_radius_and_polar_degree_upper_bound':4,
         'full_child_moments_exact_by_degree3_monomial_simplex_formula':True,
         'worker_input_sha256':hashlib.sha256(args.worker_input.read_bytes()).hexdigest(),
         'cases':cases,'absolute_cut_integration_error_certified':False,
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QI_REFERENCE_POLYNOMIAL_PREFLIGHT_PASS',flush=True)


if __name__=='__main__':
    main()
