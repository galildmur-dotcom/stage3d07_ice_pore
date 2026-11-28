#!/usr/bin/env python3
"""P10QE: adaptive spherical q2/q4 quadrature of a true Tet10 FE field.

Empirical local q discrepancy controls a GLOBAL sum of absolute error
indicators; no signed cancellation is used. Refinement bisects the largest
physical width of a spherical subbox. This is a scientific read-only pilot,
NOT a certified a posteriori error bound and NOT a FEM run.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
from pathlib import Path
import time

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as mesh
from P10QD_M8_SPHERICAL_TET10_POINT_LOCATION import CurvedTet10Locator


def bin_box(ir,im,ip):
    return (mesh.PORE_R+mesh.RADIAL_LOWER_MM[ir]*.001,
            mesh.PORE_R+mesh.RADIAL_LOWER_MM[ir+1]*.001,
            -1+im*.2,-.8+im*.2,
            -math.pi+ip*math.pi/6,-math.pi+(ip+1)*math.pi/6)


def sphere_box_points(box,q):
    r0,r1,m0,m1,p0,p1=box
    t,w=np.polynomial.legendre.leggauss(q)
    r=(r0+r1)/2+(r1-r0)/2*t
    m=(m0+m1)/2+(m1-m0)/2*t
    phi=(p0+p1)/2+(p1-p0)/2*t
    vr,vm,vp=np.meshgrid(r,m,phi,indexing='ij')
    weights=(w[:,None,None]*w[None,:,None]*w[None,None,:])
    weights=weights*(r1-r0)*(m1-m0)*(p1-p0)/8*vr**2
    xy=vr*np.sqrt(np.maximum(0.,1-vm**2))
    point=np.stack((xy*np.cos(vp),xy*np.sin(vp),.03+vr*vm),axis=-1)
    return point.reshape(-1,3),weights.ravel()


def evaluate(locator,X,box,q):
    pts,w=sphere_box_points(box,q)
    values=np.empty(len(pts))
    elements=[]
    for i,p in enumerate(pts):
        j,v=locator.locate(p)
        if j is None:
            raise ValueError(f'Curved Tet10 point location failed at {p}')
        l=np.r_[1.-v.sum(),v]
        n=np.empty(10)
        n[:4]=l*(2*l-1)
        for k,(a,b) in enumerate(mesh.EDGE,start=4):
            n[k]=4*l[a]*l[b]
        f=((X[j,:,2]-.03)/.0015)**3
        values[i]=n@f
        elements.append(j)
    return float(w@values),len(pts),len(set(elements))


def split_box(box):
    r0,r1,m0,m1,p0,p1=box
    r=(r0+r1)/2
    m=(m0+m1)/2
    # Genuine spatial widths, including near-pole azimuthal shrinking.
    radial=r1-r0
    theta=r*(m1-m0)/max(1e-5,math.sqrt(max(0.,1-m*m)))
    phi=r*math.sqrt(max(0.,1-m*m))*(p1-p0)
    dim=int(np.argmax([radial,theta,phi]))
    if dim==0:
        return (r0,r,m0,m1,p0,p1),(r,r1,m0,m1,p0,p1)
    if dim==1:
        return (r0,r1,m0,m,p0,p1),(r0,r1,m,m1,p0,p1)
    p=(p0+p1)/2
    return (r0,r1,m0,m1,p0,p),(r0,r1,m0,m1,p,p1)


def integrate_cell(locator,X,box,depth):
    v2,n2,_=evaluate(locator,X,box,2)
    v4,n4,ne=evaluate(locator,X,box,4)
    return {'box':box,'depth':depth,'v2':v2,'v4':v4,
            'local_indicator_abs_m3':abs(v4-v2),
            'points':n2+n4,'distinct_elements_q4':ne}


def adaptive_one(locator,X,ir,im,ip,ref,*,target,max_depth,max_nodes):
    start=time.monotonic()
    root=integrate_cell(locator,X,bin_box(ir,im,ip),0)
    heap=[(-root['local_indicator_abs_m3'],0,root)]
    count=1;nodes=root['points'];leaves=1
    estimate=root['v4'];error=root['local_indicator_abs_m3']
    depth_max=0
    log=[];counter=0
    while error>target*abs(ref) and nodes+2*72<=max_nodes and heap:
        _,_,cell=heapq.heappop(heap)
        if cell['depth']>=max_depth:
            # This is a *capped* leaf, not an erroneously resolved cell.
            continue
        children=[]
        for box in split_box(cell['box']):
            child=integrate_cell(locator,X,box,cell['depth']+1)
            children.append(child)
            heapq.heappush(heap,(-child['local_indicator_abs_m3'],count,child))
            count+=1
            nodes+=child['points']
        estimate+=sum(c['v4'] for c in children)-cell['v4']
        error+=sum(c['local_indicator_abs_m3'] for c in children)-cell['local_indicator_abs_m3']
        leaves+=1
        depth_max=max(depth_max,max(c['depth'] for c in children))
        counter+=1
        if counter%100==0 or time.monotonic()-start>15*(len(log)+1):
            snap={'splits':counter,'leaves':leaves,'nodes':nodes,
                  'estimated_L1_error_relative_to_q24':error/abs(ref),
                  'actual_delta_relative_to_q24':abs(estimate-ref)/abs(ref)}
            log.append(snap)
            print(f'P10QE_ADAPTIVE_HEARTBEAT r={ir} mu={im} phi={ip} '
                  f'nodes={nodes} L1_Est={snap["estimated_L1_error_relative_to_q24"]:.4g} '
                  f'delta_q24={snap["actual_delta_relative_to_q24"]:.4g}',flush=True)
    capped=(error>target*abs(ref))
    return {'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
            'reference_q24_manufactured_FE_moment_m3':ref,
            'adaptive_q4_moment_m3':estimate,'adaptive_L1_indicator_abs_m3':error,
            'adaptive_L1_indicator_relative_q24':error/abs(ref),
            'adaptive_vs_independent_q24_relative':abs(estimate-ref)/abs(ref),
            'target_relative_to_q24':target,'met_indicator_target':not capped,
            'max_depth_reached':depth_max,'maxdepth_cap':max_depth,
            'node_cap':max_nodes,'spherical_point_evaluations':nodes,
            'binary_splits':counter,'terminal_leaves':leaves,
            'elapsed_s':time.monotonic()-start,'progress':log,
            'important_limit':'q4-q2 local indicator is not a guaranteed upper bound on error. q24 reference also not exact.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--high-q',type=Path,required=True)
    p.add_argument('--target',type=float,default=5e-7)
    p.add_argument('--max-depth',type=int,default=10)
    p.add_argument('--max-nodes',type=int,default=50000)
    p.add_argument('--output',type=Path,default=Path('P10QE_M8_ADAPTIVE_SPHERICAL_FE_PILOT_QA.json'))
    args=p.parse_args()
    if args.target<=0 or args.max_nodes<144:
        raise ValueError('Invalid adaptive settings')
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    high=json.loads(args.high_q.read_text())
    if sha!=mesh.PINNED_M8_SHA256 or high['mesh_sha256']!=sha:
        raise ValueError('M8 or q24 reference SHA mismatch')
    xyz,conn,*_=mesh.parse_msh(args.mesh)
    X=xyz[conn]
    locator=CurvedTet10Locator(X)
    cases=[]
    for b in high['bins']:
        q={x['q']:x for x in b['q_records']}
        ref=q[24]['FE_nodal_cubic_moment_m3']
        a=adaptive_one(locator,X,b['radial_bin'],b['mu_bin'],b['phi_bin'],ref,
                       target=args.target,max_depth=args.max_depth,max_nodes=args.max_nodes)
        cases.append(a)
        print(f'P10QE_ADAPTIVE_CASE_{len(cases)}/4 '
              f'nodes={a["spherical_point_evaluations"]} '
              f'indicator_rel={a["adaptive_L1_indicator_relative_q24"]:.7g} '
              f'vs_q24={a["adaptive_vs_independent_q24_relative"]:.7g} '
              f'met={a["met_indicator_target"]}',flush=True)
    report={'stage':'P10QE','status':'PASS_ADAPTIVE_TET10_MANUFACTURED_FIELD_PILOT_NOT_CERTIFIED',
            'mesh_sha256':sha,'mesh_changed':False,'fem_started':False,
            'gmsh_generated':False,'cases':cases,
            'total_adaptive_points':sum(c['spherical_point_evaluations'] for c in cases),
            'max_indicator_relative':max(c['adaptive_L1_indicator_relative_q24'] for c in cases),
            'max_vs_q24_relative':max(c['adaptive_vs_independent_q24_relative'] for c in cases),
            'conditional_method':'physical-width binary splitting, priority by q2/q4 local difference, summed absolute indicators',
            'scientific_warning':'This is an empirical estimator, NOT an error certificate. No physics permitted.',
            'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],flush=True)


if __name__=='__main__':
    main()
