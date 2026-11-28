#!/usr/bin/env python3
"""Choose real M8 curved Tet10 children with exactly one quadratic boundary.

The hemisphere and azimuthal halfplanes become *quadratic* in reference
coordinates after exact curved Tet10 pullback. Other bin boundaries must
be certified inside through P10PZ hybrid Bernstein signs.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10QB_M8_SELECT_SINGLE_QUARTIC_CHILDREN as select_q4


def true_quadratic_sign(X,points,im,ip,k):
    mapped=py.map_tet10_nodally(X,points[:,None,:])[:,0,:]-m8.CENTER
    if k==2:
        return (1 if im==9 else -1)*mapped[:,2]
    angle=-math.pi+2*math.pi*ip/12 + (math.pi/6 if k==5 else 0.)
    value=-math.sin(angle)*mapped[:,0]+math.cos(angle)*mapped[:,1]
    return -value if k==5 else value


def search_one(X,ir,im,ip,min_depth=2,max_depth=9):
    active=py.REF_TET[None].copy()
    lattice=np.array([v for v in itertools.product(range(5),repeat=4) if sum(v)==4],dtype=float)/4.
    for depth in range(max_depth+1):
        control,phys=select_q4.pz.restricted_control_net(X,active)
        status=select_q4.hybrid_status(control,ir,im,ip)
        outside=(status==-1).any(axis=1)
        inside=(status==1).all(axis=1)
        unknown=~outside&~inside
        simple=unknown&((status==0).sum(axis=1)==1)
        quad= ((status[:,[2,4,5]]==0).sum(axis=1)==1)
        if depth>=min_depth:
            for j in np.flatnonzero(simple&quad):
                boundary=int([2,4,5][np.flatnonzero(status[j,[2,4,5]]==0)[0]])
                ref=active[j]
                sample=lattice@ref
                values=true_quadratic_sign(X,sample,im,ip,boundary)
                # Avoid tangential/rare-event cases in the first single-quadratic pilot.
                pos=int((values>0).sum())
                if 6<=pos<=29:
                    return depth,ref,boundary,status[j].tolist(),pos
        if depth<max_depth:
            active=py.bisect_longest_curved_edge(active[unknown],phys[unknown])
            if not len(active):
                break
    return None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('P10QC_M8_QUADRATIC_PILOT_INPUT.txt'))
    p.add_argument('--json',type=Path,default=Path('P10QC_M8_QUADRATIC_SELECTION_QA.json'))
    args=p.parse_args()
    digest=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    baseline=json.loads(args.baseline.read_text(encoding='utf-8'))
    if digest!=m8.PINNED_M8_SHA256 or baseline['mesh_sha256']!=digest or baseline['bin_count']!=48:
        raise SystemExit('P10QC_STOP_M8_NOT_ACCEPTED')
    xyz,conn,ids,types,faces=m8.parse_msh(args.mesh)
    X=xyz[conn]
    root=X.copy()
    for k,(a,b) in enumerate(py.EDGES,start=4):
        root[:,k]=2*X[:,k]-.5*(X[:,a]+X[:,b])
    lo,hi=root.min(axis=1)-m8.CENTER,root.max(axis=1)-m8.CENTER
    cases=[]
    options=[(0,0,0),(0,9,0),(4,0,0),(4,9,0),(0,0,6),(0,9,6),(4,0,6),(4,9,6),
             (4,0,5),(4,9,5),(0,0,5),(0,9,5)]
    for ir,im,ip in options:
        possible,_,_=m8.candidate_masks(lo,hi,ir,im,ip)
        for e in np.flatnonzero(possible):
            got=search_one(X[e],ir,im,ip)
            if got is None:
                continue
            depth,ref,boundary,status,pos=got
            mids=.5*(ref[py.EDGES[:,0]]+ref[py.EDGES[:,1]])
            nodes=py.map_tet10_nodally(X[e],np.concatenate((ref,mids))[None])[0]
            cases.append({'original_element_id':int(ids[e]),'mesh_tet_index':int(e),
                          'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
                          'depth':depth,'quadratic_constraint':boundary,
                          'constraints_status':status,'positive_lattice_points':pos,
                          'reference_vertices':ref.tolist(),
                          'physical_child_nodes_10':nodes.tolist()})
            print(f'P10QC_QUADRATIC_SELECTED {len(cases)} '
                  f'eid={int(ids[e])} r={ir} mu={im} phi={ip} '
                  f'depth={depth} active={boundary} lattice_pos={pos}',flush=True)
            break
        if len(cases)>=8:
            break
    if len(cases)<6 or {c['radial_bin'] for c in cases}!={0,4} or {c['mu_bin'] for c in cases}!={0,9}:
        raise SystemExit(f'P10QC_STOP_NOT_ENOUGH_SAFE_QUADRATIC_SAMPLES: {len(cases)}')
    lines=['P10QB_M8_CURVED_CHILD_TET10_V1',str(len(cases))]
    for c in cases:
        lines.append(' '.join(str(c[k]) for k in
                     ('original_element_id','radial_bin','mu_bin','phi_bin','depth','quadratic_constraint')))
        lines += [' '.join(f'{u:.17g}' for u in pt) for pt in c['reference_vertices']]
        lines += [' '.join(f'{u:.17g}' for u in pt) for pt in c['physical_child_nodes_10']]
    args.output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    report={'stage':'P10QC','status':'PASS_REAL_M8_SINGLE_QUADRATIC_SELECTION',
            'mesh_sha256':digest,'mesh_changed':False,'gmsh_generated':False,
            'fem_started':False,'num_cases':len(cases),'cases':cases}
    args.json.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('P10QC_M8_QUADRATIC_SELECTION_PASS',flush=True)


if __name__=='__main__':
    main()
