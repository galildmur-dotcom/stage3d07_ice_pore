#!/usr/bin/env python3
"""P10QG manufactured discontinuous-gradient polar-integral q-convergence.

An H1-conforming quadratic Tet10 interpolation of nodal z^3 is continuous,
but its physical gradient J^{-T} grad_ref f jumps across element faces.
Integrate normalized physical z derivative, resembling the regularity
problem of stress observables, without running any physical FEM.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QD_M8_SPHERICAL_TET10_POINT_LOCATION as qd
import P10QG_M8_CONSERVATIVE_CURVED_FACE_CLEARANCE as face


SCALE=.0015


def physical_z_gradient(X,uvw,nodal):
    N,G=m8.tet10_shape(uvw)
    J=X.T@G
    if np.linalg.det(J)<=0:
        raise ValueError('Actual curved Tet10 Jacobian not positive')
    grad=np.linalg.solve(J.T,G.T@nodal)
    return float(SCALE*grad[2]),float(N@nodal)


def face_gradient_jump_diagnostic(X,conn,*,samples=96):
    owners=defaultdict(list)
    for e,row in enumerate(conn):
        for vertices in face.FACES:
            key=tuple(sorted(int(row[j]) for j in vertices))
            owners[key].append((e,vertices))
    candidates=[]
    for key,parents in owners.items():
        if len(parents)!=2:
            continue
        a,b=parents
        p=np.array([X[a[0],j] for j in a[1]])
        center=np.mean(p,axis=0)
        rad=np.linalg.norm(center-m8.CENTER)
        if .00099<=rad<=.0016:
            candidates.append((key,parents))
    if len(candidates)<samples:
        raise ValueError('Not enough real curved shared Tet10 faces near pore')
    rng=np.random.default_rng(20261128)
    selected=rng.choice(len(candidates),size=samples,replace=False)
    jumps=[];field_discrepancy=[];position_discrepancy=[]
    for k in selected:
        key,parents=candidates[k]
        pts=[];vals=[];grad=[]
        for e,vertices in parents:
            b=np.zeros(4)
            for j in vertices:
                b[j]=1/3
            u=b[1:]
            N,_=m8.tet10_shape(u)
            pts.append(N@X[e])
            nodal=((X[e,:,2]-.03)/SCALE)**3
            g,v=physical_z_gradient(X[e],u,nodal)
            grad.append(g);vals.append(v)
        position_discrepancy.append(float(np.linalg.norm(pts[0]-pts[1])))
        field_discrepancy.append(abs(vals[0]-vals[1]))
        jumps.append(abs(grad[0]-grad[1]))
    if max(position_discrepancy)>1e-12 or max(field_discrepancy)>1e-10:
        raise ValueError('C0 quadratic continuity across M8 faces failed')
    return {'shared_internal_faces_in_near_pore_region':len(candidates),
            'faces_examined_independently':samples,
            'max_physical_face_position_gap_m':max(position_discrepancy),
            'max_FE_cubic_trace_jump':max(field_discrepancy),
            'mean_absolute_normalized_z_gradient_jump':float(np.mean(jumps)),
            'max_absolute_normalized_z_gradient_jump':float(np.max(jumps)),
            'median_absolute_normalized_z_gradient_jump':float(np.median(jumps)),
            'faces_with_nonzero_jump_above_1e_minus_10':sum(v>1e-10 for v in jumps)}


def exact_smooth_gradient_moment(ir,im,ip):
    r0=m8.PORE_R+m8.RADIAL_LOWER_MM[ir]*.001
    r1=m8.PORE_R+m8.RADIAL_LOWER_MM[ir+1]*.001
    mu0=-1+im*.2;mu1=mu0+.2
    return (r1**5-r0**5)/5*(mu1**3-mu0**3)/3*(math.pi/6)*3/SCALE**2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--q',type=int,nargs='+',default=[4,8,12,16,24])
    p.add_argument('--output',type=Path,default=Path('P10QG_M8_STRESSLIKE_TET10_GRADIENT_QA.json'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    if sha!=m8.PINNED_M8_SHA256:
        raise ValueError('P10QG_ONLY_ACCEPTED_M8')
    xyz,conn,*_=m8.parse_msh(args.mesh)
    X=xyz[conn]
    diag=face_gradient_jump_diagnostic(X,conn)
    locator=qd.CurvedTet10Locator(X)
    bins=[];total_nodes=0
    for ir in [0,4]:
        for im in [0,9]:
            ip=0
            records=[]
            for q in args.q:
                pts,ww,*_=qd.sphere_points(ir,im,ip,q)
                vals=np.empty(len(pts));lin=np.empty(len(pts))
                ids=[]
                for k,p in enumerate(pts):
                    e,u=locator.locate(p)
                    if e is None:
                        raise ValueError('P10QG_STOP_SPHERICAL_POINT_NOT_IN_REAL_M8')
                    z=(X[e,:,2]-.03)/SCALE
                    vals[k],_=physical_z_gradient(X[e],u,z**3)
                    lin[k],_=physical_z_gradient(X[e],u,z)
                    ids.append(e)
                v=float(ww@vals)
                linear=float(ww@lin)
                rlo=m8.PORE_R+m8.RADIAL_LOWER_MM[ir]*.001
                rhi=m8.PORE_R+m8.RADIAL_LOWER_MM[ir+1]*.001
                ideal=(rhi**3-rlo**3)/3*.2*math.pi/6
                error=abs(linear-ideal)/ideal
                if error>2e-10:
                    raise ValueError(f'Linear-gradient exactness violated {error}')
                records.append({'q':q,'nodes':len(pts),
                                'normalized_cubic_FE_z_gradient_moment_m3':v,
                                'linear_FE_gradient_moment_m3':linear,
                                'linear_relative_to_exact_ideal_sector_error':error,
                                'distinct_Tet10':len(set(ids))})
                total_nodes+=len(pts)
                print(f'P10QG_GRADIENT r={ir} mu={im} phi={ip} q={q} '
                      f'moment={v:.12g} linear_error={error:.3g}',flush=True)
            bins.append({'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
                         'analytic_smooth_cubic_derivative_moment_m3':exact_smooth_gradient_moment(ir,im,ip),
                         'q_records':records})
    def rel_changes(a,b):
        deltas=[];moment=[]
        for x in bins:
            r={j['q']:j['normalized_cubic_FE_z_gradient_moment_m3'] for j in x['q_records']}
            deltas.append(r[b]-r[a]);moment.append(r[b])
        deltas=np.array(deltas);moment=np.array(moment)
        return {'q_pair':[a,b],
                'L1_abs_bin_deltas_relative_to_L1_moment':float(abs(deltas).sum()/abs(moment).sum()),
                'signed_bin_deltas_relative_to_L1_moment':float(abs(deltas.sum())/abs(moment).sum()),
                'max_bin_relative_delta':float(np.max(abs(deltas)/abs(moment))),
                'positive_deltas':int((deltas>0).sum()),
                'negative_deltas':int((deltas<0).sum())}
    changes=[rel_changes(a,b) for a,b in zip(args.q[:-1],args.q[1:])]
    out={'stage':'P10QG','status':'PASS_TRUE_TET10_GRADIENT_JUMP_AND_SPHERICAL_Q_SERIES_MANUFACTURED_ONLY',
         'mesh_sha256':sha,'mesh_changed':False,'gmsh_generated':False,'fem_started':False,
         'q_levels':args.q,'four_bins':bins,'total_quadrature_points':total_nodes,
         'independently_evaluated_shared_face_gradient_jumps':diag,
         'sum_absolute_and_signed_q_changes':changes,
         'warning':'Manufactured FE physical z gradient, not stress or a physical FEM output. q comparisons do not certify absolute integration error.',
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'],flush=True)


if __name__=='__main__':
    main()
