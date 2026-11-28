#!/usr/bin/env python3
"""P10QK: read-only h-hybrid genuine M8 curved Tet10 cut decomposition.

Derive exact restricted *parent* P2 field for every terminal sub-Tet10,
classify all six pole-sector constraints conservatively via existing P10PZ,
and calculate exact cubic full-gradient integral and degree-three Bernstein
enclosure of unknown cut contribution. No Gmsh, CAD, FEM or mesh changes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10PZ_M8_DIRECT_BERNSTEIN_PREFILTER as pz
import P10QB_M8_SELECT_SINGLE_QUARTIC_CHILDREN as qb
import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi

REF=py.REF_TET
BETA3=tuple(v for v in itertools.product(range(4),repeat=4) if sum(v)==3)
BARY_NODES=np.array(BETA3,dtype=float)/3.
BASIS3=np.array([[math.factorial(3)/math.prod(math.factorial(x) for x in beta)*
                  np.prod((bary**beta)) for beta in BETA3] for bary in BARY_NODES])
GRID=BARY_NODES[:,1:]
MOMENTS=np.array([qi.exact_monomial_integral(a) for a in qi.MONOMIALS])


def child_polynomial(parentX,parentF,local_ref):
    bary=np.column_stack((1-qi.REF_NODES.sum(axis=1),qi.REF_NODES))
    parentcoords=bary@local_ref
    nodes=qi.shape_at(parentcoords)@parentX
    f=qi.shape_at(parentcoords)@parentF
    values=np.array([qi.mapped_and_numerator(nodes,f,u)[1] for u in GRID])
    coefs=np.linalg.solve(qi.mono_matrix(GRID),values)
    moments=float(coefs@MOMENTS)
    bcontrols=np.linalg.solve(BASIS3,values)
    # Explicit floating error cushion, NOT a directed-rounded certificate.
    guard=1+1e-9
    lo=min(0.,float(np.min(bcontrols)))/6*guard
    hi=max(0.,float(np.max(bcontrols)))/6*guard
    if not(lo<=hi and math.isfinite(moments)):
        raise ValueError('P10QK_INVALID_GRADIENT_BERNSTEIN_BOUNDS')
    # Constant sum over the simplex integrates each degree-3 Bernstein basis
    # to exactly 1/(6*20), equivalent to monomial formula.
    bernstein_exact=float(np.sum(bcontrols)/(6*20))
    if abs(bernstein_exact-moments)>3e-15*max(abs(moments),1e-19):
        raise ValueError('P10QK_EXACT_MONOMIAL_AND_BERNSTEIN_MOMENT_DISAGREE')
    return nodes,f,moments,lo,hi


def process_case(case,maximum,min_h_one):
    parentX=np.array(case['physical_child_nodes_10'])
    parentF=np.array(case['restricted_parent_FE_P2_nodal_values'])
    sector=tuple(case[k] for k in ('radial_bin','mu_bin','phi_bin'))
    origin=int(case['original_element_id'])
    rootvol=py.quadrature_volume(parentX,REF)
    active=REF[None].copy()
    summary=Counter();volume_by_group=Counter();terminal=[]
    for depth in range(maximum+1):
        if not len(active):break
        control,phys=pz.restricted_control_net(parentX,active)
        status=qb.hybrid_status(control,*sector)
        for k,ref in enumerate(active):
            code=status[k]
            if np.any(code==-1):group='outside'
            elif np.all(code==1):group='inside'
            elif int(np.count_nonzero(code==0))==1:group='one'
            else:group='multi'
            if depth<maximum and (group=='multi' or (group=='one' and depth<min_h_one)):
                continue
            nodes,field,integral,cutlo,cuthi=child_polynomial(parentX,parentF,ref)
            vol=py.quadrature_volume(nodes,REF)
            summary[group]+=1;volume_by_group[group]+=vol
            if group=='outside':continue
            if group=='inside' and not(cutlo-1e-20<=integral<=cuthi+1e-20):
                raise ValueError('P10QK_FULL_INTEGRAL_OUT_OF_BERNSTEIN_BOUND')
            entries={'source_case':case['source_case'],
                     'original_element_id':origin,'radial_bin':sector[0],
                     'mu_bin':sector[1],'phi_bin':sector[2],
                     'h_depth':depth,'status':code.tolist(),
                     'group':group,'nodes':nodes.tolist(),
                     'field':field.tolist(),'exact_full_gradient_m3':integral,
                     'exact_full_volume_m3':vol,
                     'unknown_cut_gradient_lower_m3':cutlo,
                     'unknown_cut_gradient_upper_m3':cuthi}
            terminal.append(entries)
        if depth<maximum:
            live=((status!=-1).all(axis=1)&(status!=1).any(axis=1))
            mask=(live & (((status==0).sum(axis=1)>=2) |
                          (((status==0).sum(axis=1)==1)&(depth<min_h_one))))
            active=py.bisect_longest_curved_edge(active[mask],phys[mask])
    closure=abs(sum(volume_by_group.values())-rootvol)/rootvol
    if closure>3e-10:
        raise ValueError('P10QK_H_SPLITTING_MASS_PARTITION_BROKEN')
    return terminal,{'source_case':case['source_case'],'original_element_id':origin,
                     'sector':sector,'root_volume_m3':rootvol,
                     'group_counts':dict(summary),
                     'group_physical_volume_fraction':{k:v/rootvol for k,v in volume_by_group.items()},
                     'full_mass_partition_closure':closure,
                     'residual_multi_gradient_enclosure_m3':[
                        sum(t['unknown_cut_gradient_lower_m3'] for t in terminal if t['group']=='multi'),
                        sum(t['unknown_cut_gradient_upper_m3'] for t in terminal if t['group']=='multi')]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--case',nargs='+',type=int,default=[4])
    p.add_argument('--h',type=int,default=8)
    p.add_argument('--min-h-one',type=int,default=0,
                   help='Subdivide one-boundary curved subtetra to at least this depth.')
    p.add_argument('--output',type=Path,default=Path('P10QK_M8_HYBRID_CHILDREN_QA.json'))
    p.add_argument('--worker-input',type=Path,default=Path('P10QK_M8_HYBRID_GRADIENT_CHILDREN.txt'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    select=json.loads(args.selection.read_text())
    if sha!=m8.PINNED_M8_SHA256 or select['mesh_sha256']!=sha or not(0<=args.min_h_one<=args.h<=12):
        raise ValueError('P10QK_M8_PIN_OR_H_LEVEL_INVALID')
    if not args.case or len(set(args.case))!=len(args.case) or any(k<0 or k>=8 for k in args.case):
        raise ValueError('P10QK_SOURCE_CHILD_SELECTION_INVALID')
    results=[];cases=[]
    for k in args.case:
        source={**select['cases'][k],'source_case':k}
        parts,audit=process_case(source,args.h,args.min_h_one)
        cases.append(audit)
        results+=parts
        print(f'P10QK_H_PREPARE source={k} h={args.h} groups={audit["group_counts"]} '
              f'multi_enclosure={audit["residual_multi_gradient_enclosure_m3"]}',flush=True)
    if not results:
        raise ValueError('P10QK_NO_TERMINAL_HYBRID_CHILDREN')
    lines=['P10QK_M8_HYBRID_GRADIENT_CHILD_V1',str(len(results))]
    for t in results:
        lines.append(' '.join(str(t[k]) for k in
                     ('source_case','original_element_id','radial_bin','mu_bin','phi_bin','h_depth'))+
                     ' '+' '.join(str(i) for i in t['status']))
        lines.extend(' '.join(format(float(v),'.17g') for v in pt) for pt in t['nodes'])
        lines.append(' '.join(format(float(v),'.17g') for v in t['field']))
        lines.append(format(t['exact_full_gradient_m3'],'.17g')+' '+
                     format(t['exact_full_volume_m3'],'.17g'))
    args.worker_input.write_text('\n'.join(lines)+'\n')
    out={'stage':'P10QK','status':'PASS_REAL_M8_HYBRID_SUBTET10_EXACT_FIELD_POLYNOMIAL_AND_BERNSTEIN_BOUNDS',
         'mesh_sha256':sha,'mesh_changed':False,'Gmsh_run':False,'physical_FEM_run':False,
         'h_depth_limit':args.h,'min_h_one':args.min_h_one,'source_cases':args.case,
         'terminal_noncandidate_count':len(results),'cases':cases,
         'terminals':results,
         'uncertain_cut_integral_bounds_use_float_protective_margin_not_directed_rounding':True,
         'worker_input_sha256':hashlib.sha256(args.worker_input.read_bytes()).hexdigest(),
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QK_REAL_M8_HYBRID_GRADIENT_PREPARATION_PASS',flush=True)


if __name__=='__main__':
    main()
