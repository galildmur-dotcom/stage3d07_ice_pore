#!/usr/bin/env python3
"""Select genuine single-active-quartic curved M8 Tet10 child cells.

Produces compact read-only text records for true LAPACKE/Algoim C++20
pilot, with exact 10-node pullbacks of the original accepted M8 map.
No CAD, new mesh, FEM or Gmsh.
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


def hybrid_status(control, ir, im, ip):
    lo, hi = control.min(axis=1) - m8.CENTER, control.max(axis=1) - m8.CENTER
    _, _, coarse = m8.candidate_masks(lo, hi, ir, im, ip)
    tight = pz.quartic_and_linear_status(control, ir, im, ip)
    if (((coarse==1)&(tight==-1))|((coarse==-1)&(tight==1))).any():
        raise ValueError('contradictory conservative signs')
    return np.where(coarse==0, tight, coarse)


def physical_quartic(X, pt, ir, quartic_id):
    mapped = py.map_tet10_nodally(X,pt[:,None,:])[:,0,:]-m8.CENTER
    rho_lo=m8.PORE_R + m8.RADIAL_LOWER_MM[ir] / 1000.
    rho_hi=m8.PORE_R + m8.RADIAL_LOWER_MM[ir+1] / 1000.
    rr=(mapped**2).sum(axis=1)
    if quartic_id==0:
        return rr-rho_lo**2
    if quartic_id==1:
        return rho_hi**2-rr
    if quartic_id==3:
        return .36*mapped[:,2]**2-.64*(mapped[:,0]**2+mapped[:,1]**2)
    raise ValueError('invalid quartic constraint')


def search_element(X, ir, im, ip, earliest, latest):
    cells=py.REF_TET[None].copy()
    for depth in range(latest+1):
        control, physical_vertices=pz.restricted_control_net(X,cells)
        status=hybrid_status(control,ir,im,ip)
        excluded=(status==-1).any(axis=1)
        included=(status==1).all(axis=1)
        unresolved=~excluded & ~included
        if depth>=earliest:
            exactly_one=((status[:,[0,1,3]]==0).sum(axis=1)==1)
            fully_decided_other=((status!=0).sum(axis=1)==5)
            selected=np.flatnonzero(unresolved & exactly_one & fully_decided_other)
            for k in selected:
                quartic=[0,1,3][np.flatnonzero(status[k,[0,1,3]]==0)[0]]
                # A true crossing, not merely a loose Bernstein bound.
                mid_ref=np.vstack([cells[k], cells[k].mean(axis=0)])
                values=physical_quartic(X,mid_ref,ir,quartic)
                if values.min()<-1e-22 and values.max()>1e-22:
                    return depth,cells[k],int(quartic),status[k].tolist(),values.tolist()
        if depth<latest:
            cells=py.bisect_longest_curved_edge(cells[unresolved],physical_vertices[unresolved])
            if not len(cells):
                break
    return None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('P10QB_M8_SINGLE_QUARTIC_PILOT_INPUT.txt'))
    p.add_argument('--json',type=Path,default=Path('P10QB_M8_SINGLE_QUARTIC_SELECTION_QA.json'))
    args=p.parse_args()
    digest=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    base=json.loads(args.baseline.read_text(encoding='utf-8'))
    if digest!=m8.PINNED_M8_SHA256 or base['mesh_sha256']!=digest or base['bin_count']!=48:
        raise SystemExit('P10QB_STOP_UNACCEPTED_M8_OR_BASELINE')
    xyz,conn,ids,types,faces=m8.parse_msh(args.mesh)
    X=xyz[conn]
    raw=X.copy()
    for k,(a,b) in enumerate(py.EDGES,start=4):
        raw[:,k]=2*X[:,k]-.5*(X[:,a]+X[:,b])
    root_lo,root_hi=raw.min(axis=1)-m8.CENTER,raw.max(axis=1)-m8.CENTER
    cases=[]
    # Prefer near/outer wall, both poles and distinct azimuth sectors.
    choices=[(0,0,6),(0,9,6),(4,0,6),(4,9,6),(0,0,0),(0,9,0),(4,0,0),(4,9,0),
             (4,0,5),(4,9,5),(0,0,5),(0,9,5)]
    for ir,im,ip in choices:
        possible,_,_=m8.candidate_masks(root_lo,root_hi,ir,im,ip)
        for e in np.flatnonzero(possible):
            result=search_element(X[e],ir,im,ip,earliest=3,latest=9)
            if result is None:
                continue
            depth,ref,quartic,status,values=result
            points=np.vstack([ref, .5*(ref[py.EDGES[:,0]]+ref[py.EDGES[:,1]])])
            child_x=py.map_tet10_nodally(X[e],points[None])[0]
            cases.append({'original_element_id':int(ids[e]),
                          'mesh_tet_index':int(e),'radial_bin':ir,'mu_bin':im,
                          'phi_bin':ip,'depth':depth,'quartic_constraint':quartic,
                          'constraints_status':status,
                          'reference_vertices':ref.tolist(),
                          'physical_child_nodes_10':child_x.tolist(),
                          'true_boundary_vertex_and_center_values':values})
            print(f'P10QB_SELECTED case={len(cases)} elem={int(ids[e])} '
                  f'r={ir} mu={im} phi={ip} depth={depth} quartic={quartic}',flush=True)
            break
        if len(cases)>=8:
            break
    if len(cases)<4 or {c['radial_bin'] for c in cases}!={0,4} or {c['mu_bin'] for c in cases}!={0,9}:
        raise SystemExit(f'P10QB_STOP_NOT_ENOUGH_GENUINE_SINGLE_QUARTIC_CASES found={len(cases)}')
    lines=['P10QB_M8_CURVED_CHILD_TET10_V1',str(len(cases))]
    for c in cases:
        lines.append(' '.join(str(c[k]) for k in
                     ['original_element_id','radial_bin','mu_bin','phi_bin','depth','quartic_constraint']))
        lines += [' '.join(format(x,'.17g') for x in pt) for pt in c['reference_vertices']]
        lines += [' '.join(format(x,'.17g') for x in pt) for pt in c['physical_child_nodes_10']]
    args.output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    report={'stage':'P10QB','status':'PASS_REAL_M8_SINGLE_QUARTIC_SELECTION',
            'mesh_sha256':digest,'mesh_changed':False,'fem_started':False,
            'gmsh_generated':False,'num_cases':len(cases),
            'coordinate_system':'true curved child Tet10, physical metres; constraints certified by Bernstein signs',
            'cases':cases}
    args.json.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('P10QB_SOURCE_ONLY_SELECTION_PASS',flush=True)


if __name__=='__main__':
    main()
