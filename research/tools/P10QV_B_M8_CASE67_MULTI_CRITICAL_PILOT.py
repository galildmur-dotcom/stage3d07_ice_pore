#!/usr/bin/env python3
"""P10QV-B: real curved M8 case6/7 pilot of critical-event cut integration.

Generalizes P10QU from radial [0] to [1] while retaining the exact P2-FE
cubic ray moment of P10QL. For now it fails closed if a genuine radial P4
or azimuth P2 ray term is seen. Numerical degree reduction is empirical,
NOT a global interval certificate; no physical FEM or mesh modification.
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

P=np.polynomial.polynomial
PIN="40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
CASE_INPUT_SHA={
    6:"11b9a8ab4bbbc3e121308921ce96c95489e0832ce82a3a0204fc9fecea5e3e0e",
    7:"1400a4b06d4d9c03b13828f51875741d4db1c5a63b7e6ef48c173644f4815df5"}
# Independent first multi cut in each archive, fixed BEFORE integrations.
PILOTS={6:19,7:10}
S_BUDGET=128
MAX_COEFF_HIGH=1e-9
MAX_RECONSTRUCTION=1e-9


def physical_ray_coeffs(c:RayChild,axis:int,s:float,t:float,which:int):
    other=[k for k in (0,1,2) if k!=axis]
    wmax=(1.-s)*(1.-t)
    ref=np.zeros((3,3))
    ref[:,other[0]]=s
    ref[:,other[1]]=(1.-s)*t
    ref[:,axis]=[0.,.5*wmax,wmax]
    xyz=qi.shape_at(ref)@c.nodes
    phys=c.physical_poly(xyz)
    coeff=np.asarray(c.constraint(phys,which),dtype=float)
    n=5 if which in (0,1) else 3
    return np.pad(coeff,(0,max(0,n-len(coeff))))[:n]


def reconstruct(c:RayChild,axis:int,t:float):
    active=c.active
    if active not in ([0,4],[1,4]):
        raise ValueError("P10QV_B_REQUIRES_REAL_TWO_BOUNDARY_PILOT")
    radial=active[0]
    samples=np.array([0.,.1464466094067262,.5,.8535533905932737,1.])
    r=np.stack([physical_ray_coeffs(c,axis,float(s),t,radial) for s in samples])
    rf=np.stack([P.polyfit(samples,r[:,k],4) for k in range(5)])
    asamples=np.array([0.,.5,1.])
    a=np.stack([physical_ray_coeffs(c,axis,float(s),t,4) for s in asamples])
    af=np.stack([P.polyfit(asamples,a[:,k],2) for k in range(3)])
    sr=max(float(np.max(abs(rf))),1e-30)
    sa=max(float(np.max(abs(af))),1e-30)
    er=0.;ea=0.
    for s in (.08,.26,.41,.67,.91):
        rt=physical_ray_coeffs(c,axis,s,t,radial)
        at=physical_ray_coeffs(c,axis,s,t,4)
        er=max(er,float(np.max(abs(rt-[P.polyval(s,x) for x in rf])))/sr)
        ea=max(ea,float(np.max(abs(at-[P.polyval(s,x) for x in af])))/sa)
    f=rf/sr;g=af/sa
    high_rad=float(np.max(abs(f[3:])))
    high_az=float(np.max(abs(g[2])))
    if max(er,ea)>MAX_RECONSTRUCTION:
        raise ValueError(f"P10QV_B_INDEPENDENT_P4_P2_RECONSTRUCTION_STOP {er} {ea}")
    if max(high_rad,high_az)>MAX_COEFF_HIGH:
        raise ValueError(f"P10QV_B_GENUINE_P4_OR_P2_RAY_REQUIRES_GENERAL_RESULTANT_STOP {high_rad} {high_az}")
    return f,g,{"max_recon_radial":er,"max_recon_azimuth":ea,
                "max_radial_w3w4":high_rad,"max_azimuth_w2":high_az}


def projected_events(c:RayChild,axis:int,t:float):
    f,a,diagnostics=reconstruct(c,axis,t)
    r0,r1,r2=f[:3]
    a0,a1=a[:2]
    polynomials={
        "radial_double_root":P.polysub(P.polymul(r1,r1),4*P.polymul(r2,r0)),
        "radial_origin":r0,
        "radial_endpoint":P.polyadd(P.polyadd(r0,r1),r2),
        "radial_degree_change":r2,
        "azimuth_origin":a0,
        "azimuth_endpoint":P.polyadd(a0,a1),
        "azimuth_degree_change":a1,
        "radial_azimuth_resultant":P.polyadd(
            P.polysub(P.polymul(r2,P.polymul(a0,a0)),
                      P.polymul(r1,P.polymul(a1,a0))),
            P.polymul(r0,P.polymul(a1,a1)))}
    roots=[];trim_count=0;maxtrim=0.;by_kind={};zeros={}
    for name,p in polynomials.items():
        rr,zero,trim,relative=physically_guarded_event_roots(p,name)
        roots.extend(rr);by_kind[name]=len(rr)
        if zero:zeros[name]=1
        trim_count+=int(trim)
        maxtrim=max(maxtrim,relative)
    unique=[]
    for s in sorted(roots):
        if not unique or s-unique[-1]>2e-8:unique.append(s)
    breaks=[0.]+unique+[1.]
    if len(breaks)>17:
        raise ValueError("P10QV_B_CRITICAL_INTERVAL_COUNT_EXCEEDS_GUARDED_BUDGET")
    missed=0
    for lo,hi in zip(breaks,breaks[1:]):
        signatures={root_topology(c,axis,lo+(hi-lo)*v,t)
                    for v in (.125,.375,.5,.625,.875)}
        missed+=int(len(signatures)>1)
    if missed:
        raise ValueError(f"P10QV_B_UNRESOLVED_TOPOLOGY_NEAR_TANGENCY_STOP count={missed}")
    diagnostics.update({"intervals":len(breaks)-1,"event_roots":by_kind,
                        "zero_polynomials":zeros,"numerical_degree_trims":trim_count,
                        "max_relative_trim":maxtrim})
    return breaks,diagnostics


def integrate(c:RayChild,axis:int,order:int,cut:bool=True):
    if axis not in (0,1,2) or order not in (64,128,256):
        raise ValueError("P10QV_B_BAD_ORDER_OR_AXIS")
    tn,tw=gauss(order)
    total_g=0.;total_v=0.;points=0;intervals=0;trims=0
    maximum={k:0. for k in ("max_recon_radial","max_recon_azimuth",
                            "max_radial_w3w4","max_azimuth_w2","max_relative_trim")}
    event_counts={}
    for count,(t,wt) in enumerate(zip(tn,tw),1):
        breaks,diag=projected_events(c,axis,float(t))
        allocation=distribute_nodes(breaks,S_BUDGET)
        if sum(allocation)!=S_BUDGET:
            raise ValueError("P10QV_B_INNER_GAUSS_BUDGET_BROKEN")
        g=0.;v=0.
        for (lo,hi),n in zip(zip(breaks,breaks[1:]),allocation):
            sn,sw=gauss(n)
            for s,weight in zip(sn,sw):
                ray_g,ray_v,_=c.moment_on_ray(axis,lo+(hi-lo)*float(s),float(t),cut=cut)
                g+=(hi-lo)*float(weight)*ray_g
                v+=(hi-lo)*float(weight)*ray_v
            points+=n
        total_g+=float(wt)*g;total_v+=float(wt)*v
        intervals+=diag["intervals"]
        trims+=diag["numerical_degree_trims"]
        for name in maximum:maximum[name]=max(maximum[name],diag[name])
        for name,val in diag["event_roots"].items():event_counts[name]=event_counts.get(name,0)+val
        if count%32==0 or count==order:
            print(f"P10QV_B_PROGRESS axis={axis} order={order} cut={int(cut)} t={count}/{order}",
                  flush=True)
    if points!=order*S_BUDGET:
        raise ValueError("P10QV_B_WRONG_NUMBER_OF_TRANSVERSE_POINTS")
    return {"cut_gradient_m3":total_g,"cut_volume_m3":total_v,
            "transverse_points":points,"critical_s_intervals_total":intervals,
            "azimuth_numerical_degree_trims":trims,
            "event_roots":event_counts,**maximum}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--case",type=int,choices=[6,7],required=True)
    p.add_argument("--orders",nargs=2,type=int,default=(64,128))
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    orders=list(a.orders)
    if orders not in ([64,128],[128,256]):
        raise ValueError("P10QV_B_ONLY_FROZEN_64_128_OR_128_256_COST")
    source=a.input_dir/f"P10QO_M8_REAL_CASE{a.case}_H8_CHILDREN_QA.json"
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    data=json.loads(source.read_text())
    index=PILOTS[a.case];term=data["terminals"][index]
    radial=0 if a.case==6 else 1
    if digest!=CASE_INPUT_SHA[a.case] or data["mesh_sha256"]!=PIN or \
       data["source_cases"]!=[a.case] or data["physical_4D_FEM_approved"] or \
       term["group"]!="multi":
        raise ValueError("P10QV_B_REAL_M8_INPUT_AND_PILOT_SHA_GUARD_STOP")
    child=RayChild(term)
    if child.active!=[radial,4]:
        raise ValueError("P10QV_B_WRONG_CASE_RADIAL_BOUNDARY")
    values={}
    for axis in (0,1,2):
        preflight=child.integrate(axis,8,cut=False)
        eg=abs(preflight["cut_gradient_m3"]-child.exact_full_gradient)/max(
            abs(child.exact_full_gradient),1e-25)
        ev=abs(preflight["cut_volume_m3"]-child.exact_full_volume)/child.exact_full_volume
        if max(eg,ev)>1e-10:raise ValueError("P10QV_B_FULL_CUBIC_RAY_PRIMITIVE_STOP")
        critical={}
        for order in orders:
            t0=time.monotonic()
            out=integrate(child,axis,order)
            out["elapsed_s"]=time.monotonic()-t0
            if not math.isfinite(out["cut_gradient_m3"]) or \
               not 0<=out["cut_volume_m3"]<=child.exact_full_volume*(1+1e-8):
                raise ValueError("P10QV_B_NONPHYSICAL_CURVED_CUT_INTEGRAL")
            critical[str(order)]=out
        # Completeness of cut-free moment after the SAME event partition.
        full=integrate(child,axis,64,cut=False)
        fg=abs(full["cut_gradient_m3"]-child.exact_full_gradient)/max(
            abs(child.exact_full_gradient),1e-25)
        fv=abs(full["cut_volume_m3"]-child.exact_full_volume)/child.exact_full_volume
        if max(fg,fv)>1e-10:
            raise ValueError("P10QV_B_SEGMENTED_FULL_FE_MOMENT_CLOSURE_STOP")
        values[str(axis)]={"critical":critical,"full_primitive_rel_error":eg,
                           "full_primitive_vol_rel_error":ev,
                           "segmented_full_moment_relative":fg,
                           "segmented_full_volume_relative":fv}
    pairwise={}
    normalizer=max(abs(child.exact_full_gradient),1e-25)
    for axis1,axis2 in ((0,1),(0,2),(1,2)):
        lhs=values[str(axis1)]["critical"][str(orders[-1])]
        rhs=values[str(axis2)]["critical"][str(orders[-1])]
        pairwise[f"{axis1}_{axis2}"]={
            "gradient_abs_m3":abs(lhs["cut_gradient_m3"]-rhs["cut_gradient_m3"]),
            "gradient_rel_to_full_original_child":abs(
                lhs["cut_gradient_m3"]-rhs["cut_gradient_m3"])/normalizer,
            "volume_abs_m3":abs(lhs["cut_volume_m3"]-rhs["cut_volume_m3"])}
    out={"stage":"P10QV_B_PILOT","case":a.case,"original_element":5751 if a.case==6 else 5847,
         "child_index":index,"active_constraints":child.active,
         "archive_source_sha256":digest,"mesh_sha256_from_archived_provenance":PIN,
         "actual_mesh_bytes_not_available":True,"outer_orders":orders,
         "inner_budget_per_t":S_BUDGET,
         "max_higher_ray_degree_guard":MAX_COEFF_HIGH,
         "numerical_root_cancellation_not_interval_certified":True,
         "not_entire_90_or_88_cut":True,"no_Gmsh_no_mesh_change_no_FEM":True,
         "exact_full_child_gradient_m3":child.exact_full_gradient,
         "exact_full_child_volume_m3":child.exact_full_volume,
         "axes":values,"pairwise":pairwise}
    # Runtime is informational, not part of a deterministic numerical QA.
    for axis in out["axes"].values():
        for item in axis["critical"].values():item.pop("elapsed_s",None)
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(f"P10QV_B_CASE{a.case}_MULTI_CRITICAL_PILOT_COMPLETE_NOT_FEM",flush=True)


if __name__=="__main__":main()
