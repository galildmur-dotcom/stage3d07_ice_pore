#!/usr/bin/env python3
"""Conservative per-bin absolute physical-volume scheduling on accepted M8.

Replays the P10QB 48-bin hybrid stopped-subcell traversal, saving the exact
physical volume of each *ready one-boundary* child. Sort descending, then
compute the MINIMUM number of local calls that would leave at most each
specified absolute unintegrated-volume budget. Multi-boundary residual is an
unavoidable floor until handled separately. This is a geometrical workload
forecast, not actual q-error certification or full FEM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10PZ_M8_DIRECT_BERNSTEIN_PREFILTER as pz
import P10QA_M8_PHYSICAL_CUT_VOLUME_BRACKETS as phys


TARGETS=(.5,.2,.1,.05,.02,.01)


def one_element_ready_volumes(X,detcoeff,ir,im,ip,depth_max):
    active=py.REF_TET[None].copy()
    parent=float(detcoeff.mean()/6.)
    inside=outside=0.
    ready=[]
    count_multi=0
    for depth in range(depth_max+1):
        if not len(active):
            count_multi=0
            continue
        control,vertices=pz.restricted_control_net(X,active)
        lo,hi=control.min(axis=1)-m8.CENTER,control.max(axis=1)-m8.CENTER
        _,_,coarse=m8.candidate_masks(lo,hi,ir,im,ip)
        bound=pz.quartic_and_linear_status(control,ir,im,ip)
        if (((coarse==1)&(bound==-1))|((coarse==-1)&(bound==1))).any():
            raise ValueError('quartic Bernstein signs conflict with AABB')
        status=np.where(coarse==0,bound,coarse)
        excluded=(status==-1).any(axis=1)
        included=(status==1).all(axis=1)
        uncertain=~included&~excluded
        exactly_one=uncertain&((status==0).sum(axis=1)==1)
        one_quartic=exactly_one&((status[:,[0,1,3]]==0).sum(axis=1)==1)
        one_quadratic=exactly_one&~one_quartic
        multi=uncertain&~exactly_one
        resolved=included|excluded|one_quartic|one_quadratic
        if resolved.any():
            volumes=phys.physical_volume_of_subcells(detcoeff,active[resolved],depth)
            if np.any(volumes<=0):
                raise ValueError('negative true physical child volume')
            inside+=float(volumes[included[resolved]].sum())
            outside+=float(volumes[excluded[resolved]].sum())
            ready.extend((float(v),0) for v in volumes[one_quartic[resolved]])
            ready.extend((float(v),1) for v in volumes[one_quadratic[resolved]])
        count_multi=int(multi.sum())
        if depth<depth_max:
            active=py.bisect_longest_curved_edge(active[multi],vertices[multi])
    residual=parent-inside-outside-sum(v for v,t in ready)
    if residual < -2e-13*parent:
        raise ValueError('overfilled parent physical volume')
    return parent,max(0.,residual),count_multi,ready


def ideal_volume(ir):
    rlo=m8.PORE_R+m8.RADIAL_LOWER_MM[ir]/1000.
    rhi=m8.PORE_R+m8.RADIAL_LOWER_MM[ir+1]/1000.
    return (rhi**3-rlo**3)/3. * .2 * math.pi/6.


def cost_schedule(volumes,types,floor,target_abs,price4,price8):
    total=sum(volumes)
    if floor>=target_abs:
        return {'state':'BLOCKED_BY_MULTI_BOUNDARY_FLOOR',
                'ideal_absolute_budget_m3':target_abs,
                'multi_physical_floor_m3':floor,'needed_calls':None}
    budget_single=target_abs-floor
    v=np.array(volumes,dtype=np.float64)
    t=np.array(types,dtype=np.int8)
    order=np.argsort(-v,kind='stable')
    sorted_v=v[order]
    sorted_t=t[order]
    required=max(0.,total-budget_single)
    prefix=np.cumsum(sorted_v,dtype=np.float64)
    k=0 if required<=1e-14*max(total,1e-30) else int(np.searchsorted(prefix,required,side='left')+1)
    if k>len(volumes):
        raise ValueError('impossible physical ready-call budget')
    used=float(prefix[k-1]) if k else 0.
    callsq=int((sorted_t[:k]==0).sum())
    calls2=int(k-callsq)
    remaining=max(0.,total-used)
    if floor+remaining>target_abs+3e-12*target_abs:
        raise ValueError('selected call budget not actually satisfied')
    return {'state':'POSSIBLE_IF_SELECTED_CUT_INTEGRALS_ARE_EXACT',
            'ideal_absolute_budget_m3':target_abs,'multi_physical_floor_m3':floor,
            'ready_total_physical_m3':total,
            'estimated_unintegrated_upper_m3':floor+remaining,
            'needed_calls':k,'quartic_calls':callsq,'quadratic_calls':calls2,
            'skipped_calls':len(volumes)-k,
            'scenario_nodes_q4':callsq*price4[0]+calls2*price4[1],
            'scenario_nodes_q8':callsq*price8[0]+calls2*price8[1]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--hybrid',type=Path,required=True)
    p.add_argument('--quartic-pilot',type=Path,required=True)
    p.add_argument('--quadratic-pilot',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('P10QC_M8_ABSOLUTE_BUDGET_SCHEDULE_ALL48.json'))
    args=p.parse_args()
    digest=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    baseline=json.loads(args.baseline.read_text(encoding='utf-8'))
    hybrid=json.loads(args.hybrid.read_text(encoding='utf-8'))
    qua=json.loads(args.quartic_pilot.read_text(encoding='utf-8'))
    quad=json.loads(args.quadratic_pilot.read_text(encoding='utf-8'))
    if any(x['mesh_sha256']!=digest for x in (baseline,hybrid,qua,quad)) or digest!=m8.PINNED_M8_SHA256:
        raise SystemExit('P10QC_STOP_UNPINNED_M8_OR_INCOMPATIBLE_REPORT')
    if hybrid['bin_count']!=48 or baseline['bin_count']!=48:
        raise ValueError('not all 48 bins present')
    if qua['num_cases']!=8 or quad['num_cases']!=8:
        raise ValueError('actual Algoim pilots missing')
    def median_nodes(report,q):
        rows=sorted(next(r for r in c['q_records'] if r['q']==q)['points'] for c in report['cases'])
        return rows[len(rows)//2]
    med4=(median_nodes(qua,4),median_nodes(quad,4))
    med8=(median_nodes(qua,8),median_nodes(quad,8))
    xyz,conn,ids,types,faces=m8.parse_msh(args.mesh)
    X=xyz[conn]
    detc=phys.detj_bernstein_cubic_from_affine_jacobian(phys.jacobian_at_reference_vertices(X))
    if np.any(detc.min(axis=1)<=512*np.finfo(float).eps*np.max(np.abs(detc),axis=1)):
        raise ValueError('Jacobian sign uncertified')
    root=X.copy()
    for k,(a,b) in enumerate(py.EDGES,start=4):
        root[:,k]=2*X[:,k]-.5*(X[:,a]+X[:,b])
    lo,hi=root.min(axis=1)-m8.CENTER,root.max(axis=1)-m8.CENTER
    results=[]
    for no,(b,old) in enumerate(zip(baseline['bins'],hybrid['bins'])):
        ir,im,ip=(b[k] for k in ('radial_bin','mu_bin','phi_bin'))
        if (ir,im,ip)!=(old['radial_bin'],old['mu_bin'],old['phi_bin']):
            raise ValueError('hybrid/baseline bin identity mismatch')
        possible,_,_=m8.candidate_masks(lo,hi,ir,im,ip)
        candidates=np.flatnonzero(possible)
        ready=[];floor=0.;multi_leaves=0;total=0.
        for e in candidates:
            vol,left,count,subset=one_element_ready_volumes(X[e],detc[e],ir,im,ip,12)
            total+=vol;floor+=left;multi_leaves+=count;ready.extend(subset)
        prev=old['depth_records'][-1]
        typecounts=[sum(t==i for v,t in ready) for i in (0,1)]
        if typecounts!=[prev['one_quartic_calls'],prev['one_quadratic_calls']]:
            raise ValueError('replayed one-boundary call counts changed')
        if multi_leaves!=prev['multi_remaining_leaves'] or abs(floor-prev['multi_remaining_physical_m3'])>2e-11*total:
            raise ValueError('replayed physical multi-boundary remainder mismatch')
        vals=[v for v,t in ready];labels=[t for v,t in ready]
        target={str(100*f):cost_schedule(vals,labels,floor,ideal_volume(ir)*f,med4,med8)
                for f in TARGETS}
        results.append({'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
                        'original_candidate_count':len(candidates),
                        'ideal_spherical_sector_volume_m3':ideal_volume(ir),
                        'candidate_physical_volume_m3':total,
                        'single_quartic_calls':typecounts[0],
                        'single_quadratic_calls':typecounts[1],
                        'single_ready_physical_upper_m3':sum(vals),
                        'multi_remaining_physical_m3':floor,
                        'multi_remaining_leaves':multi_leaves,
                        'budgets_percent_ideal':target})
        print(f'P10QC_BUDGET_BIN_{no+1:02d}/48 r={ir} mu={im} phi={ip} '
              f'singleQ={typecounts[0]} single2={typecounts[1]} '
              f'multi_vs_ideal={floor/ideal_volume(ir):.4g} '
              f'budget_20pct={target["20.0"]["state"]}',flush=True)
    report={'stage':'P10QC','status':'PASS_ALL48_PHYSICAL_ABSOLUTE_VOLUME_BUDGET_WORKLOAD_ONLY',
            'mesh_sha256':digest,'mesh_changed':False,'fem_started':False,
            'gmsh_generated':False,'max_depth':12,'bin_count':len(results),
            'target_relative_to':'ideal spherical-sector volume used only as tolerance scale, not exact M8 cut volume',
            'semantic_warning':'Budgets bound unintegrated mass IF selected local integrals were exact; actual quadrature error is NOT certified.',
            'empirical_median_nodes_per_quartic_and_quadratic_q4':list(med4),
            'empirical_median_nodes_per_quartic_and_quadratic_q8':list(med8),
            'bins':results,'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('P10QC_ABSOLUTE_BUDGET_ALL48_GEOMETRY_QA_PASS',flush=True)


if __name__=='__main__':
    main()
