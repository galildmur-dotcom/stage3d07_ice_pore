#!/usr/bin/env python3
"""Read-only localize two P10QV-E STOPs with physical s-root scans.

An UNGUARDED event partition is built here solely to explain which s
interval violates the frozen P10QV-B guard; it is never integrated or
accepted. A dense finite s scan also cannot prove a continuous theorem.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QQ_M8_ROOT_TOPOLOGY_ADAPTIVE_TRANSVERSE import root_topology
from P10QT_M8_RADIAL_AND_TWO_BOUNDARY_CRITICAL_INTEGRATOR import physically_guarded_event_roots
from P10QV_B_M8_CASE67_MULTI_CRITICAL_PILOT import (
    PILOTS,PIN,CASE_INPUT_SHA,reconstruct,projected_events)

P=np.polynomial.polynomial
FROZEN_PREFLIGHT_SHA={
    6:"78c189cfb90b4c93031e1ec4ca425e4278fa1f9629fe4566bb0a2887c383b54f",
    7:"d85c4bd12f62435720b858f534eec03396fb0dc260a6b9d4a57d7e9cc54fbbdd"}
SCAN_S=513


def diagnostic_unguarded_s_intervals(child:RayChild,axis:int,t:float):
    f,a,diag=reconstruct(child,axis,t)
    r0,r1,r2=f[:3];a0,a1=a[:2]
    poly={"radial_double_root":P.polysub(P.polymul(r1,r1),4*P.polymul(r2,r0)),
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
    roots=[];counts={}
    for name,v in poly.items():
        rr,_,_,_=physically_guarded_event_roots(v,name)
        counts[name]=len(rr)
        roots.extend(rr)
    unique=[]
    for s in sorted(roots):
        if not unique or s-unique[-1]>2e-8:unique.append(s)
    breaks=[0.]+unique+[1.]
    bad=[];sequence=[]
    for lo,hi in zip(breaks,breaks[1:]):
        sigs=[root_topology(child,axis,lo+(hi-lo)*f,t)
              for f in (.125,.375,.5,.625,.875)]
        if len(set(sigs))>1:
            bad.append({"s_low":lo,"s_high":hi,"probe_signatures":sigs})
        sig=sigs[2]
        if not sequence or sequence[-1]!=sig:sequence.append(sig)
    return {"unguarded_event_interval_count":len(breaks)-1,
            "unguarded_event_root_count_by_kind":counts,
            "unguarded_event_strips_root_signature_word":sequence,
            "missed_topology_in_event_s_intervals":bad,
            "unguarded_partition_is_diagnostic_only_not_approved":True,
            "maximum_reconstruction_relative":max(diag["max_recon_radial"],
                                                  diag["max_recon_azimuth"])}


def inspect(child:RayChild,axis:int,t:float):
    samples=[(i+.5)/SCAN_S for i in range(SCAN_S)]
    words=[root_topology(child,axis,s,t) for s in samples]
    transitions=[[samples[i-1],samples[i]] for i in range(1,SCAN_S)
                 if words[i]!=words[i-1]]
    payload={"physical_t":t,"physical_s_scan_points":SCAN_S,
             "physical_s_scan_unique_topologies":len(set(words)),
             "physical_s_scan_transitions":transitions,
             "finite_s_scan_not_interval_certificate":True}
    try:
        breaks,diag=projected_events(child,axis,t)
        payload["frozen_projected_event_status"]="PASS"
        payload["frozen_projected_s_intervals"]=len(breaks)-1
        payload["frozen_projected_numerical_degree_trims"]=diag["numerical_degree_trims"]
    except ValueError as exc:
        payload["frozen_projected_event_status"]="STOP"
        payload["frozen_projected_stop_reason"]=str(exc)
    payload["unguarded_explanation_only"]=diagnostic_unguarded_s_intervals(child,axis,t)
    return payload


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    rows=[]
    for case,axis in ((6,1),(7,2)):
        source=a.input_dir/f"P10QO_M8_REAL_CASE{case}_H8_CHILDREN_QA.json"
        pf=a.input_dir/f"P10QV_E_M8_CASE{case}_EVENT_STRIP_BRACKET_STOP_PREFLIGHT_QA.json"
        if hashlib.sha256(source.read_bytes()).hexdigest()!=CASE_INPUT_SHA[case] or \
           hashlib.sha256(pf.read_bytes()).hexdigest()!=FROZEN_PREFLIGHT_SHA[case]:
            raise ValueError("P10QV_E_STOP_LOCAL_UNFROZEN_INPUT_REJECTED")
        raw=json.loads(source.read_text());diag=json.loads(pf.read_text())
        if raw["mesh_sha256"]!=PIN or raw["physical_4D_FEM_approved"] or \
           diag["axes"][str(axis)]["status"]!="NUMERICAL_TOPOLOGY_STOP" or \
           diag["axes_with_geometry_stop"]!=[axis]:
            raise ValueError("P10QV_E_STOP_LOCAL_WRONG_CASE")
        msg=diag["axes"][str(axis)]["stop_reason"]
        bracket=re.search(r"interval=\[([^,]+),([^\]]+)\] probe_t=([^ ]+)",msg)
        if bracket is None:
            raise ValueError("P10QV_E_STOP_BRACKET_NOT_PARSEABLE")
        tlo,thi,tmid=(float(x) for x in bracket.groups())
        if not tlo<tmid<thi or thi-tlo>=1/257:
            raise ValueError("P10QV_E_STOP_BRACKET_INVALID")
        c=RayChild(raw["terminals"][PILOTS[case]])
        if c.active!=([0,4] if case==6 else [1,4]):
            raise ValueError("P10QV_E_STOP_WRONG_ACTIVE_CONSTRAINTS")
        rows.append({"case":case,"axis":axis,"preflight_stop_reason":msg,
                     "bracket":[tlo,thi],"t_probe_at_STOP":tmid,
                     "test_slices":[inspect(c,axis,t) for t in (tlo,tmid,thi)]})
        print(f"P10QV_E_STOP_LOCAL case={case} axis={axis} t={tmid:.12g}",flush=True)
    result={"stage":"P10QV_E_LOCAL_PHYSICAL_ROOT_TOPOLOGY_STOP_EXPLANATION",
            "mesh_sha256_from_archived_provenance":PIN,
            "preflight_sha256":FROZEN_PREFLIGHT_SHA,
            "unguarded_s_partitions_never_used_for_integration":True,
            "physical_s_scans_finite_not_certified":True,
            "no_Gmsh_no_mesh_change_no_FEM":True,
            "physical_4D_FEM_approved":False,"rows":rows}
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("P10QV_E_LOCAL_STOP_EXPLANATION_COMPLETE_NOT_FEM",flush=True)


if __name__=="__main__":main()
