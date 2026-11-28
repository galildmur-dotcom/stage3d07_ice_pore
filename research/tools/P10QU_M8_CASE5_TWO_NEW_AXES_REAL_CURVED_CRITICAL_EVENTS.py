#!/usr/bin/env python3
"""P10QU: independently rebuild critical-event ray quadrature on axes 0 and 1.

The physical M8 P4 radial and P2 azimuth interfaces are reconstructed from
the genuine curved Tet10 map, with per-slice verification.  P4->P2 and
P2->P1 in the ray coordinate are *checked*, not assumed for other meshes.
Candidate projected events: discriminant, endpoints, degree change, and
the radial/azimuth resultant.  Full cubic P2-FE ray primitive is unchanged.
An empirical double-precision diagnostic, NOT an interval certificate/FEM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QQ_M8_ROOT_TOPOLOGY_ADAPTIVE_TRANSVERSE import root_topology
from P10QR_M8_ONE_BOUNDARY_DISCRIMINANT_SEGMENTED import distribute_nodes,gauss
from P10QT_M8_RADIAL_AND_TWO_BOUNDARY_CRITICAL_INTEGRATOR import physically_guarded_event_roots

PIN='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
P=np.polynomial.polynomial
T_ORDERS=(128,256)
S_BUDGET=128


def ray_boundary_coefficients(c:RayChild,axis:int,s:float,t:float):
    other=[i for i in (0,1,2) if i!=axis]
    raymax=(1.-s)*(1.-t)
    ref=np.zeros((3,3))
    ref[:,other[0]]=s
    ref[:,other[1]]=(1.-s)*t
    ref[:,axis]=[0.,.5*raymax,raymax]
    phys=c.physical_poly(qi.shape_at(ref)@c.nodes)
    radial=np.pad(np.asarray(c.constraint(phys,0),dtype=float),(0,5))[:5]
    azimuth=np.pad(np.asarray(c.constraint(phys,4),dtype=float),(0,3))[:3]
    return radial,azimuth


def reconstruct(c:RayChild,axis:int,t:float):
    samples=np.array([0.,.1464466094067262,.5,.8535533905932737,1.])
    radial=np.stack([ray_boundary_coefficients(c,axis,float(s),t)[0] for s in samples])
    f=np.stack([P.polyfit(samples,radial[:,k],4) for k in range(5)])
    azsamples=np.array([0.,.5,1.])
    azimuth=np.stack([ray_boundary_coefficients(c,axis,float(s),t)[1] for s in azsamples])
    a=np.stack([P.polyfit(azsamples,azimuth[:,k],2) for k in range(3)])
    sf=max(float(np.max(np.abs(f))),1e-30)
    sa=max(float(np.max(np.abs(a))),1e-30)
    errf=0.;erra=0.
    for s in (.08,.26,.41,.67,.91):
        tr,ta=ray_boundary_coefficients(c,axis,s,t)
        errf=max(errf,float(np.max(np.abs(tr-[P.polyval(s,x) for x in f])))/sf)
        erra=max(erra,float(np.max(np.abs(ta-[P.polyval(s,x) for x in a])))/sa)
    # These limits are deliberately tighter than the 1e-6 L1 acceptance.
    if max(errf,erra)>1e-9:
        raise ValueError('P10QU_REAL_M8_P4_P2_TRANSVERSE_RECONSTRUCTION_FAILED')
    f=f/sf;a=a/sa
    high_rad=float(np.max(np.abs(f[3:])))
    high_az=float(np.max(np.abs(a[2])))
    if max(high_rad,high_az)>1e-9:
        raise ValueError('P10QU_GENERAL_QUARTIC_OR_QUADRATIC_RAY_NOT_SUPPORTED_FAIL_CLOSED')
    return f,a,{'radial_reconstruction_relative':errf,
                 'azimuth_reconstruction_relative':erra,
                 'radial_w3_w4_relative':high_rad,
                 'azimuth_w2_relative':high_az}


def events(c:RayChild,axis:int,t:float):
    f,a,diag=reconstruct(c,axis,t)
    active=c.active
    candidates={}
    if active in ([0],[0,4]):
        r0,r1,r2=f[:3]
        candidates.update({
            'radial_multiple_root':P.polysub(P.polymul(r1,r1),4*P.polymul(r2,r0)),
            'radial_origin':r0,
            'radial_endpoint':P.polyadd(P.polyadd(r0,r1),r2),
            'radial_degree_change':r2})
    if active in ([4],[0,4]):
        a0,a1=a[:2]
        candidates.update({'azimuth_origin':a0,
                           'azimuth_endpoint':P.polyadd(a0,a1),
                           'azimuth_degree_change':a1})
    if active==[0,4]:
        candidates['radial_azimuth_resultant']=P.polyadd(
            P.polysub(P.polymul(r2,P.polymul(a0,a0)),
                      P.polymul(r1,P.polymul(a1,a0))),
            P.polymul(r0,P.polymul(a1,a1)))
    if active not in ([0],[4],[0,4]):
        raise ValueError('P10QU_BAD_ACTUAL_CUT_INTERFACE_SET')
    roots=[];event_counts={};zeros={};trim_count=0;maxtrim=0.
    for kind,coeff in candidates.items():
        real,zero,trim,relative=physically_guarded_event_roots(coeff,kind)
        roots.extend(real)
        event_counts[kind]=len(real)
        if zero:zeros[kind]=1
        trim_count+=int(trim)
        maxtrim=max(maxtrim,relative)
    roots.sort();unique=[]
    for root in roots:
        if not unique or root-unique[-1]>2e-8:unique.append(root)
    breaks=[0.]+unique+[1.]
    if len(breaks)>17:raise ValueError('P10QU_TOO_MANY_CRITICAL_S_INTERVALS')
    missed=0
    for lo,hi in zip(breaks,breaks[1:]):
        # Probes are only empirical: near-tangencies may escape them.
        sig={root_topology(c,axis,lo+(hi-lo)*v,t) for v in (.125,.375,.5,.625,.875)}
        missed+=int(len(sig)>1)
    diag.update({'candidate_event_counts':event_counts,
                 'identically_zero_event_counts':zeros,
                 'azimuth_degree_numerical_trim_count':trim_count,
                 'max_trimmed_relative_coefficient':maxtrim,
                 'unresolved_topology_intervals':missed,
                 'number_of_s_intervals':len(breaks)-1})
    if missed:raise ValueError('P10QU_TOPOLOGY_CHANGES_INSIDE_PROJECTED_S_INTERVAL')
    return breaks,diag


def compute(c:RayChild,axis:int,order:int,cut=True):
    if axis not in (0,1) or order not in T_ORDERS:
        raise ValueError('P10QU_WRONG_AXIS_OR_ORDER')
    tn,tw=gauss(order)
    outg=0.;outv=0.;points=0;segments=0;trim=0
    maxr=0.;maxa=0.;maxhi_r=0.;maxhi_a=0.;maxtrim=0.
    events_total={};zero_total={}
    for t,wt in zip(tn,tw):
        br,info=events(c,axis,float(t))
        ns=distribute_nodes(br,S_BUDGET)
        if sum(ns)!=S_BUDGET:raise ValueError('P10QU_GAUSS_BUDGET_NOT_FIXED')
        gs=0.;vs=0.
        for (lo,hi),n in zip(zip(br,br[1:]),ns):
            sn,sw=gauss(n)
            for s,w in zip(sn,sw):
                g,v,_=c.moment_on_ray(axis,lo+(hi-lo)*float(s),float(t),cut=cut)
                gs+=(hi-lo)*float(w)*g
                vs+=(hi-lo)*float(w)*v
            points+=n
        outg+=float(wt)*gs;outv+=float(wt)*vs
        segments+=info['number_of_s_intervals']
        trim+=info['azimuth_degree_numerical_trim_count']
        maxtrim=max(maxtrim,info['max_trimmed_relative_coefficient'])
        maxr=max(maxr,info['radial_reconstruction_relative'])
        maxa=max(maxa,info['azimuth_reconstruction_relative'])
        maxhi_r=max(maxhi_r,info['radial_w3_w4_relative'])
        maxhi_a=max(maxhi_a,info['azimuth_w2_relative'])
        for k,v in info['candidate_event_counts'].items():events_total[k]=events_total.get(k,0)+v
        for k in info['identically_zero_event_counts']:zero_total[k]=zero_total.get(k,0)+1
    if points!=order*S_BUDGET:raise ValueError('P10QU_WRONG_TOTAL_POINT_COUNT')
    return {'cut_gradient_m3':outg,'cut_volume_m3':outv,'transverse_Gauss_points':points,
            'outer_Gauss_points':order,'inner_nodes_per_t':S_BUDGET,
            'critical_s_intervals_total':segments,'event_root_counts':events_total,
            'identically_zero_event_slices':zero_total,
            'numerical_azimuth_degree_trims':trim,
            'max_trimmed_relative_coefficient':maxtrim,
            'max_radial_reconstruction_relative':maxr,
            'max_azimuth_reconstruction_relative':maxa,
            'max_high_order_radial_ray_coefficient_relative':maxhi_r,
            'max_high_order_azimuth_ray_coefficient_relative':maxhi_a,
            'unresolved_topology_intervals':0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--axis-q128',type=Path,required=True)
    p.add_argument('--axis',type=int,choices=[0,1],required=True)
    p.add_argument('--part',type=int,choices=[0,1,2,3],required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    ch=json.loads(args.child_report.read_text())
    base=json.loads(args.axis_q128.read_text())
    if sha!=PIN or ch['mesh_sha256']!=PIN or base['mesh_sha256']!=PIN or \
       ch['source_cases']!=[5] or ch['h_depth_limit']!=8 or ch['min_h_one']!=8 or \
       base['axis']!=args.axis or len(base['cells'])!=30 or \
       ch['physical_4D_FEM_approved'] or base['physical_4D_FEM_approved']:
        raise ValueError('P10QU_WRONG_REAL_M8_MESH_OR_PREVIOUS_AXIS_BASELINE')
    terminals=ch['terminals']
    ids=[i for i,t in enumerate(terminals) if t['group'] in ('one','multi')]
    if len(ids)!=30 or sorted(ids)!=sorted(r['index'] for r in base['cells']):
        raise ValueError('P10QU_TRUE_THIRTY_CUT_SOURCE_CHANGED')
    baseline={r['index']:r['order']['128'] for r in base['cells']}
    selection=ids[args.part::4];rows=[]
    for pos,idx in enumerate(selection,1):
        c=RayChild(terminals[idx]);full=c.integrate(args.axis,8,cut=False)
        if abs(full['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)>1e-10:
            raise ValueError('P10QU_REAL_CUBIC_PRIMITIVE_FULL_MOMENT_FAILED')
        values={}
        for order in T_ORDERS:
            start=time.monotonic();r=compute(c,args.axis,order,cut=True)
            r['elapsed_s']=time.monotonic()-start
            if not math.isfinite(r['cut_gradient_m3']) or not 0<=r['cut_volume_m3']<=c.exact_full_volume*(1+1e-8):
                raise ValueError('P10QU_BAD_CURVED_CUT_INTEGRAL')
            values[str(order)]=r
        # Independent exact full-polynomial check for the new piecewise weights.
        fullsplit=compute(c,args.axis,128,cut=False)
        ef=abs(fullsplit['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)
        ev=abs(fullsplit['cut_volume_m3']-c.exact_full_volume)/c.exact_full_volume
        if max(ef,ev)>1e-10:raise ValueError('P10QU_SPLIT_FULL_POLYNOMIAL_QA_FAILED')
        rows.append({'index':idx,'group':terminals[idx]['group'],'active':c.active,
                     'uniform_axis_q128':baseline[idx],'critical':values,
                     'full_gradient_relative_error':ef,'full_volume_relative_error':ev})
        print(f'P10QU axis={args.axis} part={args.part} progress={pos}/{len(selection)} '
              f'index={idx} active={c.active} t128={values["128"]["elapsed_s"]:.1f}s '
              f't256={values["256"]["elapsed_s"]:.1f}s',flush=True)
    out={'stage':'P10QU','scope':'two independent new axes real M8 30 cuts; critical s from reduced P4/P2 geometry',
         'mesh_sha256':PIN,'source_case':5,'original_element_id':5865,'axis':args.axis,
         'part':args.part,'parts':4,'all_30_indices':ids,'selected_indices':selection,
         'numerical_reduction_P4_to_P2_and_P2_to_P1_rechecked_each_outer_slice':True,
         'fixed_s_budget':S_BUDGET,'fixed_outer_orders':list(T_ORDERS),
         'double_roots_and_topology_samples_not_interval_certified':True,
         'physical_4D_FEM_approved':False,'no_mesh_change_no_CAD_no_Gmsh_no_FEM':True,'cells':rows}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(f'P10QU_NEW_AXIS_{args.axis}_PART_{args.part}_COMPLETE_NO_FEM',flush=True)


if __name__=='__main__':main()
