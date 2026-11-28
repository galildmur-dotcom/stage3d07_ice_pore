#!/usr/bin/env python3
"""P10QT: projected critical events for real radial P2 + azimuth P1 rays.

On selected axis=2 true curved M8 Tet10 makes radial physical P4 reduce to
quadratic along w, and azimuth P2 to linear along w (checked at every t).
Use radial discriminant/endpoints, azimuth endpoints/degree and Res_w(R2,A1)
to split inner s. Exact P2-FE cubic ray primitive, outer Gauss 128/256.
No root interval certification and NO Gmsh/CAD/FEM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QQ_M8_ROOT_TOPOLOGY_ADAPTIVE_TRANSVERSE import root_topology
from P10QR_M8_ONE_BOUNDARY_DISCRIMINANT_SEGMENTED import (
    PIN,AXIS,S_BUDGET,T_ORDERS,distribute_nodes,gauss,real_event_roots)
from P10QS_M8_TWO_BOUNDARY_RESULTANT_PREFLIGHT import reconstruct

P=np.polynomial.polynomial
ALL=(13,14,20,21,31,37,38,30)
WORKLIST=(37,30,13,14,20,21,31,38)
NEW_Q256={37,30}


def physically_guarded_event_roots(poly,kind):
    """Remove only demonstrably sub-roundoff high-degree interpolation noise.

    At this true M8/axis the azimuth coefficient of w has observed degree 1
    in s. A degree-2 coefficient around 1e-12 relative makes the generic
    polynomial companion matrix singularly ill-conditioned and fabricates
    a 1e12 external root. Independently measured P2 reconstruction residuals
    are much smaller than the 1e-10 trimming guard. We retain a QA count.
    """
    p=np.asarray(poly,dtype=float)
    discarded=0.;trimmed=False
    if kind=='azimuth_degree_change' and len(p)==3:
        scale=float(max(abs(p)))
        if scale>0 and abs(p[2])<=1e-10*scale:
            discarded=float(abs(p[2])/scale)
            p=p[:2]
            trimmed=True
    roots,iszero=real_event_roots(p,kind)
    return roots,iszero,trimmed,discarded


def projected_events(c:RayChild,t:float):
    f,g,ef,eg=reconstruct(c,t)
    # P4 physical radial polynomial reduces to degree <=2 *in ray w* on
    # this exact M8 geometry/axis. This is rechecked at every Gauss t.
    higher=float(np.max(abs(f[3:])))
    if higher>1e-9 or float(np.max(abs(g[2])))>1e-9:
        raise ValueError('P10QT_P4_OR_P2_NOT_REDUCED_IN_SELECTED_RAY_DIRECTION')
    r0,r1,r2=f[0],f[1],f[2]
    az0,az1=g[0],g[1]
    polynomials={
        'radial_double_ray_root':P.polysub(P.polymul(r1,r1),4*P.polymul(r2,r0)),
        'radial_ray_origin':r0,
        'radial_ray_endpoint':P.polyadd(P.polyadd(r0,r1),r2),
        'radial_degree_change':r2}
    if c.active==[0,4]:
        polynomials.update({
            'azimuth_ray_origin':az0,
            'azimuth_ray_endpoint':P.polyadd(az0,az1),
            'azimuth_degree_change':az1,
            'radial_azimuth_resultant':P.polyadd(
                P.polysub(P.polymul(r2,P.polymul(az0,az0)),
                          P.polymul(r1,P.polymul(az1,az0))),
                P.polymul(r0,P.polymul(az1,az1)))})
    elif c.active!=[0]:
        raise ValueError('P10QT_NOT_REAL_RADIAL_OR_TWO_ACTIVE_CUT')
    allroots=[];rawcounts={};degenerate=[];degree_trim=0;max_trim_relative=0.
    for kind,polynomial in polynomials.items():
        rr,iszero,trimmed,discarded=physically_guarded_event_roots(polynomial,kind)
        degree_trim+=int(trimmed)
        max_trim_relative=max(max_trim_relative,discarded)
        rawcounts[kind]=len(rr)
        if iszero:degenerate.append(kind)
        allroots.extend(rr)
    allroots.sort();unique=[]
    for s in allroots:
        if not unique or s-unique[-1]>2e-8:unique.append(s)
    breaks=[0.]+unique+[1.]
    if len(breaks)>17:
        raise ValueError('P10QT_CRITICAL_EVENTS_EXCEED_FIXED_INNER_NODE_BUDGET')
    missed=0
    for lo,hi in zip(breaks,breaks[1:]):
        signatures={root_topology(c,AXIS,lo+(hi-lo)*v,t) for v in (.125,.5,.875)}
        if len(signatures)>1:missed+=1
    return breaks,{'interpolation_error_radial_P4':ef,
                   'interpolation_error_azimuth_P2':eg,
                   'max_higher_w_coeff_radial':higher,
                   'unresolved_probe_intervals':missed,
                   'candidate_roots_by_event':rawcounts,
                   'identically_zero_event_polynomials':degenerate,
                   'numerical_azimuth_degree_denoising_applied':degree_trim,
                   'max_dropped_relative_azimuth_degree_coefficient':max_trim_relative,
                   'n_s_intervals':len(breaks)-1}


def integrate(c:RayChild,t_order:int,cut=True):
    if c.active not in ([0],[0,4]) or t_order not in T_ORDERS:
        raise ValueError('P10QT_WRONG_Q_OR_REAL_SOURCE_CONSTRAINT')
    tn,tw=gauss(t_order)
    grad=0.;vol=0.;points=0;nintervals=0;unresolved=0
    rawcounts={};degenerate={};maxrad=0.;maxaz=0.;maxhigher=0.
    degree_denoising_slices=0;max_dropped_degree_relative=0.
    for t,weight in zip(tn,tw):
        t=float(t)
        breaks,info=projected_events(c,t)
        allocations=distribute_nodes(breaks,S_BUDGET)
        if sum(allocations)!=S_BUDGET:
            raise ValueError('P10QT_INNER_BUDGET_ALLOCATION_FAILED')
        lg=0.;lv=0.
        for (left,right),n in zip(zip(breaks,breaks[1:]),allocations):
            nodes,weights=gauss(n)
            for s,sw in zip(nodes,weights):
                x=left+(right-left)*float(s)
                a,b,_=c.moment_on_ray(AXIS,x,t,cut=cut)
                wt=(right-left)*float(sw)
                lg+=wt*a;lv+=wt*b
            points+=n
        grad+=float(weight)*lg;vol+=float(weight)*lv
        nintervals+=info['n_s_intervals']
        unresolved+=info['unresolved_probe_intervals']
        maxrad=max(maxrad,info['interpolation_error_radial_P4'])
        maxaz=max(maxaz,info['interpolation_error_azimuth_P2'])
        maxhigher=max(maxhigher,info['max_higher_w_coeff_radial'])
        degree_denoising_slices+=info['numerical_azimuth_degree_denoising_applied']
        max_dropped_degree_relative=max(max_dropped_degree_relative,
                                        info['max_dropped_relative_azimuth_degree_coefficient'])
        for k,v in info['candidate_roots_by_event'].items():rawcounts[k]=rawcounts.get(k,0)+v
        for k in info['identically_zero_event_polynomials']:
            degenerate[k]=degenerate.get(k,0)+1
    if points!=t_order*S_BUDGET:
        raise ValueError('P10QT_TOTAL_GAUSS_NODES_NOT_FIXED')
    return {'cut_gradient_m3':grad,'cut_volume_m3':vol,
            'transverse_Gauss_points':points,'outer_Gauss_points':t_order,
            'inner_nodes_per_t_slice':S_BUDGET,
            'total_s_segments':nintervals,'unresolved_topology_probe_intervals':unresolved,
            'critical_event_root_candidate_counts':rawcounts,
            'identically_zero_event_slice_counts':degenerate,
            'max_radial_P4_interpolation_relative_error':maxrad,
            'max_azimuth_P2_interpolation_relative_error':maxaz,
            'max_radial_higher_ray_coeff_relative':maxhigher,
            'azimuth_degree_numerical_denoising_slice_count':degree_denoising_slices,
            'max_discarded_relative_azimuth_degree_coefficient':max_dropped_degree_relative}


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
    p.add_argument('--part',type=int,choices=[0,1,2,3],required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    child=json.loads(a.child_report.read_text())
    prev=json.loads(a.axis2_q128.read_text())
    qp=[json.loads(f.read_text()) for f in (a.p10qp_part0,a.p10qp_part1,a.p10qp_posthoc)]
    qq=[json.loads(f.read_text()) for f in (a.p10qq_part0,a.p10qq_part1)]
    if sha!=PIN or child['mesh_sha256']!=PIN or child['source_cases']!=[5] or \
       child['h_depth_limit']!=8 or child['min_h_one']!=8 or \
       prev['mesh_sha256']!=PIN or len(prev['cells'])!=30 or prev['axis']!=AXIS or \
       any(x['mesh_sha256']!=PIN or x['physical_4D_FEM_approved'] for x in [child,prev,*qp,*qq]):
        raise ValueError('P10QT_M8_SHA_AND_SOURCE_NOT_PINNED')
    real=tuple(i for i,t in enumerate(child['terminals']) if t['group']=='multi' or
               (t['group']=='one' and [k for k,v in enumerate(t['status']) if v==0]==[0]))
    if set(real)!=set(ALL):raise ValueError('P10QT_8_REMAINING_REAL_CUT_CELLS_CHANGED')
    oldrefs={x['index']:x['new_methods']['uniform_q256'] for r in qp for x in r['cells']}
    oldrefs.update({x['index']:x['uniform_q256_reference'] for r in qq for x in r['cells']})
    if set(ALL)-set(oldrefs)!=NEW_Q256:
        raise ValueError('P10QT_FROZEN_NEW_Q256_SET_CHANGED')
    base={x['index']:x['order']['128'] for x in prev['cells']}
    rows=[];indices=WORKLIST[a.part::4]
    for pos,idx in enumerate(indices,1):
        term=child['terminals'][idx]
        c=RayChild(term)
        if c.active not in ([0],[0,4]):
            raise ValueError('P10QT_NOT_REAL_RADIAL_OR_MULTI')
        full=c.integrate(AXIS,8,cut=False)
        if abs(full['cut_gradient_m3']-c.exact_full_gradient)>1e-10*max(abs(c.exact_full_gradient),1e-25):
            raise ValueError('P10QT_ANALYTIC_FULL_CUBIC_PRECHECK')
        methods={}
        for order in T_ORDERS:
            tic=time.monotonic();x=integrate(c,order,cut=True)
            x['elapsed_s']=time.monotonic()-tic
            if not math.isfinite(x['cut_gradient_m3']) or \
               not 0<=x['cut_volume_m3']<=c.exact_full_volume*(1+1e-8):
                raise ValueError('P10QT_INVALID_CUT_PHYSICAL_INTEGRAL')
            methods[str(order)]=x
        smooth=integrate(c,128,cut=False)
        eg=abs(smooth['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)
        ev=abs(smooth['cut_volume_m3']-c.exact_full_volume)/c.exact_full_volume
        if max(eg,ev)>1e-10:
            raise ValueError('P10QT_SPLIT_FULL_CUBIC_EXACT_MOMENT_FAIL')
        if idx in oldrefs:
            reference=oldrefs[idx];origin='PRIOR_Q256'
        else:
            tic=time.monotonic();reference=c.integrate(AXIS,256)
            reference['elapsed_s']=time.monotonic()-tic
            origin='NEW_P10QT_Q256_HELDOUT_ORDER'
        rows.append({'index':idx,'group':term['group'],'active_constraints':c.active,
                     'prior_uniform_q128':base[idx],
                     'q256_reference':reference,'q256_origin':origin,
                     'segmented':methods,
                     'full_gradient_relative_error':eg,
                     'full_volume_relative_error':ev})
        print(f'P10QT_REAL_P4_P2 part={a.part} progress={pos}/{len(indices)} '
              f'cell={idx} act={c.active} new_q256={origin.startswith("NEW")} '
              f'uniform128_abs={abs(base[idx]["cut_gradient_m3"]-reference["cut_gradient_m3"]):.4e} '
              f'critical128_abs={abs(methods["128"]["cut_gradient_m3"]-reference["cut_gradient_m3"]):.4e} '
              f'unresolved={methods["128"]["unresolved_topology_probe_intervals"]}',flush=True)
    out={'stage':'P10QT','scope':'exact ray reduced P4->P2 radial + azimuth P1; 8 true M8 cuts',
         'mesh_sha256':PIN,'source_case':5,'original_element_id':5865,'axis':AXIS,
         'frozen_remaining_eight_indices':list(ALL),'worklist':list(WORKLIST),
         'new_q256_indices':sorted(NEW_Q256),
         'part':a.part,'parts':4,'selected_indices':list(indices),
         'frozen_parameters':{'inner_s_budget':S_BUDGET,'outer_t_orders':list(T_ORDERS),
                              'actual_radial_ray_degree_max':2,'actual_azimuth_ray_degree_max':1,
                              'include_joint_resultant':True},
         'physical_4D_FEM_approved':False,
         'normal_high_degree_P4_case_NOT_certified':True,
         'double_real_roots_not_interval_certified':True,
         'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
         'cells':rows}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(f'P10QT_PART_{a.part}_RADIAL_MULTI_INTEGRALS_COMPLETE_NO_FEM',flush=True)


if __name__=='__main__':main()
