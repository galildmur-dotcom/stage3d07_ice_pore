#!/usr/bin/env python3
"""P10QQ experimental 2D topology-probed Gauss panels on real curved M8.

Use only P4/P2 ray-root topology probes to choose a deterministic quadtree;
then exactly integrate the true cubic FE numerator along each ray and apply
area-allocated Gauss-Legendre across the resulting transverse rectangles.
NOT certified: finite probes can miss a topology-changing curve.
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
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild, roots_in_segment

PIN='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
PROBE=(.05,.5,.95)
MAX_DEPTH=4
NODE_BUDGET=128*128
MIN_N=8
RISK_WEIGHT=4.
TEST_INDICES=(26,20,31,21,23,10,8,38)


def root_topology(c:RayChild,axis:int,s:float,t:float):
    others=[i for i in (0,1,2) if i!=axis]
    fixed=(s,(1-s)*t)
    wmax=(1-s)*(1-t)
    if wmax<=0:return (-1,)
    refs=np.zeros((3,3))
    refs[:,others[0]]=fixed[0]
    refs[:,others[1]]=fixed[1]
    refs[:,axis]=[0.,.5*wmax,wmax]
    phys=c.physical_poly(qi.shape_at(refs)@c.nodes)
    polynomials=[c.constraint(phys,j) for j in c.active]
    r_by_constraint=[roots_in_segment(poly) for poly in polynomials]
    roots=sorted(set([0.,1.]+[v for rr in r_by_constraint for v in rr]))
    accepted=0
    for left,right in zip(roots,roots[1:]):
        if right-left<2e-12:continue
        mid=(left+right)*.5
        if all(np.polynomial.polynomial.polyval(mid,p)<=0 for p in polynomials):
            accepted+=1
    # Also retain per-boundary root multiplicities: number of accepted segments
    # alone is insufficient at a two-constraint crossing.
    return tuple([len(rr) for rr in r_by_constraint]+[accepted])


def topology_quadtree(c:RayChild,axis:int=2):
    rows=[];nprobes=0
    def visit(s0,s1,t0,t1,depth):
        nonlocal nprobes
        sigs=set()
        for fs in PROBE:
            for ft in PROBE:
                sigs.add(root_topology(c,axis,s0+(s1-s0)*fs,t0+(t1-t0)*ft))
                nprobes+=1
        changing=len(sigs)>1
        if changing and depth<MAX_DEPTH:
            sm=(s0+s1)*.5;tm=(t0+t1)*.5
            for sub in ((s0,sm,t0,tm),(sm,s1,t0,tm),
                        (s0,sm,tm,t1),(sm,s1,tm,t1)):
                visit(*sub,depth+1)
        else:
            rows.append({'s0':s0,'s1':s1,'t0':t0,'t1':t1,
                         'depth':depth,'probe_signature_count':len(sigs),
                         'still_changes_at_max_depth':changing})
    visit(0.,1.,0.,1.,0)
    if len(rows)>4**MAX_DEPTH:
        raise ValueError('P10QQ_QUADTREE_SIZE_UNCONTROLLED')
    return rows,nprobes


def assign_orders(leaves):
    weights=[]
    for v in leaves:
        area=(v['s1']-v['s0'])*(v['t1']-v['t0'])
        weights.append(area*(RISK_WEIGHT if v['still_changes_at_max_depth'] else 1.))
    scale=sum(weights)
    orders=[max(MIN_N,min(128,int(math.sqrt(NODE_BUDGET*w/scale)))) for w in weights]
    # The 8-node minimum is always possible: at most 4^4=256 leaves.
    # Remove extra nodes deterministically if the minimum floor pushes over
    # the 16,384-point cap.
    while sum(n*n for n in orders)>NODE_BUDGET:
        eligible=[i for i,n in enumerate(orders) if n>MIN_N]
        if not eligible:raise ValueError('P10QQ_NODE_BUDGET_IMPOSSIBLE')
        i=max(eligible,key=lambda k:(orders[k]/max(weights[k],1e-30),orders[k],-k))
        orders[i]-=1
    for v,n in zip(leaves,orders):v['gauss_order']=n
    return sum(n*n for n in orders)


@lru_cache(maxsize=128)
def gauss(n):
    a,w=np.polynomial.legendre.leggauss(n)
    return (a+1)*.5,w*.5


def integrate_panels(c:RayChild,axis:int,leaves,cut=True):
    grad=0.;vol=0.;segs=0
    for v in leaves:
        nodes,weights=gauss(v['gauss_order'])
        ds=v['s1']-v['s0'];dt=v['t1']-v['t0']
        for s,sw in zip(nodes,weights):
            rs=v['s0']+ds*float(s)
            for t,tw in zip(nodes,weights):
                rt=v['t0']+dt*float(t)
                g,m,nseg=c.moment_on_ray(axis,rs,rt,cut=cut)
                wt=ds*dt*float(sw*tw)
                grad+=wt*g;vol+=wt*m;segs+=nseg
    return {'cut_gradient_m3':grad,'cut_volume_m3':vol,
            'transverse_Gauss_points':sum(x['gauss_order']**2 for x in leaves),
            'accepted_ray_segments':segs}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--axis2-q128',type=Path,required=True)
    p.add_argument('--p10qp-part0',type=Path,required=True)
    p.add_argument('--p10qp-part1',type=Path,required=True)
    p.add_argument('--p10qp-posthoc',type=Path,required=True)
    p.add_argument('--part',type=int,choices=[0,1],required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    child=json.loads(a.child_report.read_text())
    base=json.loads(a.axis2_q128.read_text())
    old=[json.loads(x.read_text()) for x in (a.p10qp_part0,a.p10qp_part1,a.p10qp_posthoc)]
    if sha!=PIN or sha!=m8.PINNED_M8_SHA256 or \
       child['mesh_sha256']!=sha or child['source_cases']!=[5] or \
       child['min_h_one']!=8 or child['h_depth_limit']!=8 or \
       base['mesh_sha256']!=sha or base['axis']!=2 or base['orders']!=[16,32,64,128] or \
       base['source_case']!=5 or len(base['cells'])!=30 or \
       any(x['mesh_sha256']!=sha or x['physical_4D_FEM_approved'] for x in [child,base,*old]) or \
       any(x['stage']!='P10QP' for x in old):
        raise ValueError('P10QQ_WRONG_PINNED_M8_OR_Q256_REFERENCE')
    oldref={row['index']:row['new_methods']['uniform_q256']
            for source in old for row in source['cells']}
    if set(oldref)!={26,10,20,12,13,11,6,34,14,32,28,17,23,31,21,25}:
        raise ValueError('P10QQ_OLD_Q256_SET_NOT_AS_EXPECTED')
    prev={row['index']:row for row in base['cells']}
    rows=[]
    for pos,idx in enumerate(TEST_INDICES[a.part::2],1):
        term=child['terminals'][idx]
        if term['group'] not in ('one','multi') or idx not in prev:
            raise ValueError('P10QQ_TEST_TARGET_NOT_CUT')
        c=RayChild(term)
        full=c.integrate(2,8,cut=False)
        if abs(full['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)>1e-10:
            raise ValueError('P10QQ_FULL_CUBIC_CHECK_FAILED')
        tic=time.monotonic()
        leaves,nprobes=topology_quadtree(c)
        cost=assign_orders(leaves)
        topo_s=time.monotonic()-tic
        tic=time.monotonic()
        value=integrate_panels(c,2,leaves,cut=True)
        value['elapsed_s']=time.monotonic()-tic
        if cost!=value['transverse_Gauss_points'] or cost>NODE_BUDGET or \
           not math.isfinite(value['cut_gradient_m3']) or \
           not 0<=value['cut_volume_m3']<=c.exact_full_volume*(1+1e-8):
            raise ValueError('P10QQ_UNCONTROLLED_ADAPTIVE_RULE')
        # Same geometrically-selected leaves, but smooth full cubics: this
        # verifies all panel weights/Jacobians regardless of topology.
        check=integrate_panels(c,2,leaves,cut=False)
        full_g=abs(check['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)
        full_v=abs(check['cut_volume_m3']-c.exact_full_volume)/c.exact_full_volume
        if max(full_g,full_v)>1e-10:
            raise ValueError('P10QQ_GEOMETRY_PANEL_FULL_CUBIC_MOMENT_FAILED')
        if idx in oldref:
            reference=oldref[idx]
            origin='P10QP_PREVIOUS_Q256_REFERENCE'
            q256_elapsed=0.
        else:
            tic=time.monotonic();reference=c.integrate(2,256)
            q256_elapsed=time.monotonic()-tic
            origin='P10QQ_NEW_Q256_HELDOUT_ORDER'
        baseline=prev[idx]['order']['128']
        rows.append({'index':idx,'group':term['group'],'q256_reference_origin':origin,
                     'uniform_q128_from_P10QO':baseline,
                     'uniform_q256_reference':reference,
                     'new_q256_elapsed_s':q256_elapsed,
                     'topology_probe_count':nprobes,'topology_build_elapsed_s':topo_s,
                     'leaf_count':len(leaves),'max_depth_reached':max(v['depth'] for v in leaves),
                     'unresolved_max_depth_topology_count':sum(v['still_changes_at_max_depth'] for v in leaves),
                     'number_of_risk_weighted_panels':sum(v['still_changes_at_max_depth'] for v in leaves),
                     'adaptive_full_gradient_relative_error':full_g,
                     'adaptive_full_volume_relative_error':full_v,
                     'adaptive_cut':value,'leaves':leaves})
        print(f'P10QQ_REAL_M8 part={a.part} progress={pos}/{len(TEST_INDICES[a.part::2])} '
              f'cell={idx} leaves={len(leaves)} nodes={cost} '
              f'uniform_abs={abs(baseline["cut_gradient_m3"]-reference["cut_gradient_m3"]):.4e} '
              f'geometric_abs={abs(value["cut_gradient_m3"]-reference["cut_gradient_m3"]):.4e}',flush=True)
    out={'stage':'P10QQ','scope':'one frozen root-topology-probe quadtree, not certified',
         'mesh_sha256':sha,'source_case':5,'original_element_id':5865,'axis':2,
         'all_frozen_test_indices':list(TEST_INDICES),'part':a.part,'parts':2,
         'frozen_parameters':{'probe_fraction':list(PROBE),'max_depth':MAX_DEPTH,
                              'node_budget':NODE_BUDGET,'min_leaf_order':MIN_N,
                              'risk_weight_at_unresolved_max_depth':RISK_WEIGHT,
                              'topology_signature':'per-active-constraint interior roots + accepted ray intervals'},
         'prior_q256_reused_and_new_q256_indices':[i for i in TEST_INDICES[a.part::2] if i not in oldref],
         'input_sha256':{k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in (
             ('child',a.child_report),('axis2',a.axis2_q128),
             ('old_part0',a.p10qp_part0),('old_part1',a.p10qp_part1),('old_posthoc',a.p10qp_posthoc))},
         'finite_probes_may_miss_isolated_tangencies':True,
         'new_q256_is_not_exact_error_certificate':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
         'cells':rows}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(f'P10QQ_PART{a.part}_GEOMETRIC_TOPOLOGY_PILOT_DONE_NO_FEM',flush=True)


if __name__=='__main__':main()
