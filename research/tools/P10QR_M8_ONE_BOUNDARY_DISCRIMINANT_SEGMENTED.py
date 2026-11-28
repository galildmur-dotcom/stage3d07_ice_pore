#!/usr/bin/env python3
"""P10QR: project exact P2 ray-boundary discriminant onto inner s on M8.

For a fixed outer t and one active quadratic boundary, reconstruct p(s,w)
from the REAL curved Tet10 map. Split s at roots of disc_w(p), p(s,0),
p(s,1), and the leading coefficient. On every interval use Gauss; the
physical cubic numerator is integrated exactly along w by P10QL.RayChild.
Numerical real-root solving is NOT interval-certified, and the outer t
direction remains unsplit. No Gmsh/CAD/mesh modification/FEM.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QQ_M8_ROOT_TOPOLOGY_ADAPTIVE_TRANSVERSE import root_topology

PIN='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
TARGETS=(26,10,23,8,18,33)
AXIS=2
S_BUDGET=128
T_ORDERS=(128,256)


def azimuth_ray_coeffs(c:RayChild,s:float,t:float):
    other=[i for i in range(3) if i!=AXIS]
    f0=s;f1=(1-s)*t;wmax=(1-s)*(1-t)
    refs=np.zeros((3,3))
    refs[:,other[0]]=f0;refs[:,other[1]]=f1
    refs[:,AXIS]=[0.,.5*wmax,wmax]
    xyz=qi.shape_at(refs)@c.nodes
    p=c.constraint(c.physical_poly(xyz),4)
    return np.pad(np.asarray(p,dtype=float),(0,max(0,3-len(p))))[:3]


def fitted_boundary(c:RayChild,t:float):
    # Each physical component is quadratic in (s,w) at fixed t because the
    # true Tet10 map is P2 in reference coordinates. The azimuth constraint
    # is linear in physical XYZ, hence p(s,w) has bi-degree <= (2,2).
    f0=azimuth_ray_coeffs(c,0.,t)
    fm=azimuth_ray_coeffs(c,.5,t)
    f1=azimuth_ray_coeffs(c,1.,t)
    c0=f0;c2=2*(f1-2*fm+f0);c1=f1-f0-c2
    # Array indexed by powers of w, each entry is powers of s (0,1,2).
    coeff=np.stack((c0,c1,c2),axis=1)
    scale=float(np.max(np.abs(coeff)))
    if scale<1e-13:
        raise ValueError('P10QR_AZIMUTH_BOUNDARY_DEGENERATE_ON_ENTIRE_SLICE')
    # Verify actual physical polynomial coefficient interpolation away from
    # the three interpolation nodes. The constraint is not approximated by
    # a linear mesh or a plane in parameter space.
    err=0.
    for s in (.125,.375,.625,.875):
        actual=azimuth_ray_coeffs(c,s,t)
        fitted=coeff[:,0]+s*coeff[:,1]+s*s*coeff[:,2]
        err=max(err,float(np.max(abs(fitted-actual)))/scale)
    if err>1e-10:
        raise ValueError('P10QR_P2_RAY_BOUNDARY_INTERPOLATION_NOT_EXACT')
    return coeff/scale,err


def real_event_roots(coeff,kind):
    p=np.asarray(coeff,dtype=float)
    scale=float(np.max(np.abs(p)))
    if scale<=1e-13:
        return [],True
    # Degree trimming relative to coefficient norm avoids creating roots
    # from nearly vanishing high-order cancellation terms.
    while len(p)>1 and abs(p[-1])<5e-13*scale:
        p=p[:-1]
    if len(p)<=1:return [],False
    roots=np.polynomial.polynomial.polyroots(p/scale)
    found=[]
    for r in roots:
        if abs(r.imag)<=2e-7 and 1e-9<r.real<1-1e-9:
            s=float(r.real)
            residual=abs(np.polynomial.polynomial.polyval(s,p))/scale
            if residual>5e-6:
                raise ValueError('P10QR_CRITICAL_ROOT_NUMERIC_RESIDUAL_FAIL_'+kind)
            found.append(s)
    return found,False


def projected_critical_s(c:RayChild,t:float):
    coeff,interpolation_err=fitted_boundary(c,t)
    a,b,z=coeff[2],coeff[1],coeff[0]
    P=np.polynomial.polynomial
    discriminant=P.polysub(P.polymul(b,b),4*P.polymul(a,z))
    polynomials={
        'multiple_ray_root':discriminant,
        'ray_origin':z,
        'ray_endpoint':P.polyadd(P.polyadd(a,b),z),
        'degree_change':a}
    roots=[];degenerate=[];by_kind={}
    for kind,p in polynomials.items():
        rr,identically_zero=real_event_roots(p,kind)
        if identically_zero:degenerate.append(kind)
        by_kind[kind]=len(rr)
        roots.extend(rr)
    roots.sort()
    unique=[]
    for s in roots:
        if not unique or s-unique[-1]>2e-8:unique.append(s)
    if len(unique)>16:
        raise ValueError('P10QR_UNBOUNDED_EVENT_COUNT')
    breaks=[0.]+unique+[1.]
    # Check the supposed topologically smooth intervals with THREE independent
    # points, in addition to the algebraic root-event construction.
    missed=0
    for lo,hi in zip(breaks,breaks[1:]):
        sigs={root_topology(c,AXIS,lo+(hi-lo)*s,t) for s in (.125,.5,.875)}
        if len(sigs)>1:missed+=1
    return breaks,{'event_counts_by_kind':by_kind,
                   'identically_zero_event_polynomials':degenerate,
                   'interpolation_relative_error':interpolation_err,
                   'unresolved_probe_intervals':missed,
                   'number_of_s_intervals':len(breaks)-1}


def distribute_nodes(breaks,budget=S_BUDGET):
    lengths=np.diff(breaks)
    n=len(lengths)
    if n<1 or n>budget//8:
        raise ValueError('P10QR_INVALID_NUMBER_OF_S_INTERVALS')
    # Allocate the fixed 128-node inner budget proportionally by length,
    # with a small minimum per interval. This is frozen and never tuned on
    # q256 data. Exact budget is filled by deterministic largest residuals.
    out=[max(8,int(budget*float(v))) for v in lengths]
    while sum(out)>budget:
        candidates=[i for i,v in enumerate(out) if v>8]
        if not candidates:raise ValueError('P10QR_S_BUDGET_TOO_SMALL')
        j=max(candidates,key=lambda k:(out[k]-budget*lengths[k],out[k],-k))
        out[j]-=1
    while sum(out)<budget:
        j=max(range(n),key=lambda k:(budget*lengths[k]-out[k],lengths[k],-k))
        out[j]+=1
    return out


@lru_cache(maxsize=160)
def gauss(n):
    x,w=np.polynomial.legendre.leggauss(n)
    return (x+1)*.5,w*.5


def integrate(c:RayChild,t_order:int,cut=True):
    tnodes,tweights=gauss(t_order)
    result_g=0.;result_v=0.;used_points=0
    event_sums={k:0 for k in ('multiple_ray_root','ray_origin','ray_endpoint','degree_change')}
    unresolved=0;degeneracies={};nintervals=0;max_interp=0.
    for t,wt in zip(tnodes,tweights):
        t=float(t)
        breaks,meta=projected_critical_s(c,t)
        count=distribute_nodes(breaks)
        if sum(count)!=S_BUDGET:raise ValueError('P10QR_INNER_NODE_BUDGET')
        local_g=0.;local_v=0.
        for (lo,hi),n in zip(zip(breaks,breaks[1:]),count):
            snodes,sweights=gauss(n)
            for u,sw in zip(snodes,sweights):
                s=lo+(hi-lo)*float(u)
                g,v,_=c.moment_on_ray(AXIS,s,t,cut=cut)
                local_g+=(hi-lo)*float(sw)*g
                local_v+=(hi-lo)*float(sw)*v
            used_points+=n
        result_g+=float(wt)*local_g;result_v+=float(wt)*local_v
        unresolved+=meta['unresolved_probe_intervals']
        nintervals+=meta['number_of_s_intervals']
        max_interp=max(max_interp,meta['interpolation_relative_error'])
        for k,v in meta['event_counts_by_kind'].items():event_sums[k]+=v
        for k in meta['identically_zero_event_polynomials']:
            degeneracies[k]=degeneracies.get(k,0)+1
    if used_points!=t_order*S_BUDGET:
        raise ValueError('P10QR_TOTAL_TRANSVERSE_NODES_WRONG')
    return {'cut_gradient_m3':result_g,'cut_volume_m3':result_v,
            'transverse_Gauss_points':used_points,'outer_Gauss_points':t_order,
            'inner_nodes_per_outer_slice':S_BUDGET,
            'total_critical_event_roots_by_kind':event_sums,
            'total_s_smooth_intervals':nintervals,
            'topology_probe_unresolved_intervals':unresolved,
            'identically_zero_event_slice_counts':degeneracies,
            'max_P2_interpolation_relative_error':max_interp}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--axis2-q128',type=Path,required=True)
    p.add_argument('--p10qp-part0',type=Path,required=True)
    p.add_argument('--p10qp-part1',type=Path,required=True)
    p.add_argument('--p10qp-posthoc',type=Path,required=True)
    p.add_argument('--p10qq-part0',type=Path,required=True)
    p.add_argument('--p10qq-part1',type=Path,required=True)
    p.add_argument('--part',type=int,choices=[0,1],required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    child=json.loads(a.child_report.read_text())
    base=json.loads(a.axis2_q128.read_text())
    old=[json.loads(x.read_text()) for x in (a.p10qp_part0,a.p10qp_part1,a.p10qp_posthoc)]
    latest=[json.loads(x.read_text()) for x in (a.p10qq_part0,a.p10qq_part1)]
    if sha!=PIN or sha!=m8.PINNED_M8_SHA256 or child['mesh_sha256']!=sha or \
       child['source_cases']!=[5] or child['h_depth_limit']!=8 or child['min_h_one']!=8 or \
       base['mesh_sha256']!=sha or base['axis']!=2 or base['orders']!=[16,32,64,128] or \
       any(x['mesh_sha256']!=sha or x['physical_4D_FEM_approved'] for x in [child,base,*old,*latest]):
        raise ValueError('P10QR_PINNED_M8_AND_SOURCE_GUARD')
    previous={x['index']:x['order']['128'] for x in base['cells']}
    refs={r['index']:r['new_methods']['uniform_q256'] for j in old for r in j['cells']}
    refs.update({r['index']:r['uniform_q256_reference'] for j in latest for r in j['cells']})
    new_ref_indices=[i for i in TARGETS if i not in refs]
    if new_ref_indices!=[18,33]:
        raise ValueError('P10QR_Q256_HELDOUT_TARGET_SET_CHANGED')
    rows=[]
    for pos,idx in enumerate(TARGETS[a.part::2],1):
        term=child['terminals'][idx]
        c=RayChild(term)
        if term['group']!='one' or c.active!=[4]:
            raise ValueError('P10QR_DEGREE_TWO_SINGLE_ACTIVE_AZ_BOUNDARY_REQUIRED')
        full=c.integrate(AXIS,8,cut=False)
        if abs(full['cut_gradient_m3']-c.exact_full_gradient)>1e-10*max(abs(c.exact_full_gradient),1e-25):
            raise ValueError('P10QR_REFERENCE_CUBIC_MOMENT_FAIL')
        methods={}
        for n in T_ORDERS:
            tic=time.monotonic();x=integrate(c,n,cut=True)
            x['elapsed_s']=time.monotonic()-tic
            if not math.isfinite(x['cut_gradient_m3']) or not 0<=x['cut_volume_m3']<=c.exact_full_volume*(1+1e-8):
                raise ValueError('P10QR_INVALID_CURVED_CUT_MOMENT')
            methods[str(n)]=x
        # Full polynomial with the same projected event boundaries/weights.
        smooth=integrate(c,128,cut=False)
        e_g=abs(smooth['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)
        e_v=abs(smooth['cut_volume_m3']-c.exact_full_volume)/c.exact_full_volume
        if max(e_g,e_v)>1e-10:
            raise ValueError('P10QR_S_SEGMENTS_FULL_EXACT_POLYNOMIAL_MOMENT_FAILED')
        if idx in refs:
            reference=refs[idx];origin='PREVIOUS_Q256'
        else:
            tic=time.monotonic();reference=c.integrate(AXIS,256)
            reference['elapsed_s']=time.monotonic()-tic
            origin='NEW_P10QR_Q256_HELDOUT_ORDER'
        rows.append({'index':idx,'group':term['group'],'active':c.active,
                     'baseline_q128':previous[idx],
                     'q256_reference':reference,'reference_origin':origin,
                     'segmented':methods,
                     'full_gradient_relative_error':e_g,
                     'full_volume_relative_error':e_v})
        print(f'P10QR_REAL_M8 part={a.part} progress={pos}/{len(TARGETS[a.part::2])} '
              f'cell={idx} q128_abs={abs(previous[idx]["cut_gradient_m3"]-reference["cut_gradient_m3"]):.4e} '
              f'split128_abs={abs(methods["128"]["cut_gradient_m3"]-reference["cut_gradient_m3"]):.4e} '
              f'split256_abs={abs(methods["256"]["cut_gradient_m3"]-reference["cut_gradient_m3"]):.4e}',flush=True)
    out={'stage':'P10QR','scope':'single active true quadratic azimuth P2 boundary, explicit discriminant/endpoint projection',
         'mesh_sha256':sha,'original_element_id':5865,'source_case':5,'axis':AXIS,
         'all_frozen_indices':list(TARGETS),'part':a.part,'parts':2,
         'frozen_parameters':{'inner_s_budget':S_BUDGET,'outer_Gauss_orders':list(T_ORDERS),
                              'critical_events':['multiple_ray_root','ray_origin','ray_endpoint','degree_change'],
                              'real_event_root_residual_tolerance':5e-6,
                              'minimum_per_s_smooth_interval':8},
         'new_q256_indices':[i for i in TARGETS[a.part::2] if i not in refs],
         'physical_4D_FEM_approved':False,'numerical_projected_roots_not_interval_certified':True,
         'two_active_P4_P2_not_processed':True,
         'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
         'cells':rows}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(f'P10QR_PART{a.part}_PROJECTED_CRITICAL_EVENTS_COMPLETED_NOT_FEM',flush=True)


if __name__=='__main__':main()
