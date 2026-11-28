#!/usr/bin/env python3
"""48-bin M8 hybrid workload: stop h-refinement at one active boundary.

Counts actual curved physical mass and call count ready for local one-surface
Algoim vs still-multiple-boundary cells. The proposed Algoim calculation is
NOT executed for all 48 bins in this geometric readiness test. Source-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10PZ_M8_DIRECT_BERNSTEIN_PREFILTER as pz
import P10QA_M8_PHYSICAL_CUT_VOLUME_BRACKETS as phys


def one_child_audit(X,det_coeff,ir,im,ip,maxdepth):
    active=py.REF_TET[None].copy()
    full=float(det_coeff.mean()/6.)
    masses={k:0. for k in ('inside','outside','one_quartic','one_quadratic')}
    counts={'one_quartic':0,'one_quadratic':0}
    trace=[]
    for depth in range(maxdepth+1):
        if len(active):
            control,vertices=pz.restricted_control_net(X,active)
            lo,hi=control.min(axis=1)-m8.CENTER,control.max(axis=1)-m8.CENTER
            _,_,coarse=m8.candidate_masks(lo,hi,ir,im,ip)
            tight=pz.quartic_and_linear_status(control,ir,im,ip)
            if (((coarse==1)&(tight==-1))|((coarse==-1)&(tight==1))).any():
                raise ValueError('hybrid Bernstein signs contradict AABB')
            status=np.where(coarse==0,tight,coarse)
            outside=(status==-1).any(axis=1)
            inside=(status==1).all(axis=1)
            unknown=~outside & ~inside
            simple=unknown & ((status==0).sum(axis=1)==1)
            oneq=simple & ((status[:,[0,1,3]]==0).sum(axis=1)==1)
            one2=simple & ~oneq
            multi=unknown & ~simple
            labels={'inside':inside,'outside':outside,
                    'one_quartic':oneq,'one_quadratic':one2}
            resolved=inside|outside|oneq|one2
            if resolved.any():
                vols=phys.physical_volume_of_subcells(det_coeff,active[resolved],depth)
                if np.any(vols<=0):
                    raise ValueError('bad positive subcell mass')
                for label,mask in labels.items():
                    masses[label]+=float(vols[mask[resolved]].sum())
            counts['one_quartic']+=int(oneq.sum())
            counts['one_quadratic']+=int(one2.sum())
            still=int(multi.sum())
            if depth<maxdepth:
                active=py.bisect_longest_curved_edge(active[multi],vertices[multi])
        else:
            still=0
        remaining=full-sum(masses.values())
        if remaining<-1e-13*full:
            raise ValueError('unresolved physical volume negative')
        trace.append({'depth':depth,**{k+'_physical_m3':v for k,v in masses.items()},
                      'multi_remaining_physical_m3':max(0.,remaining),
                      'one_quartic_calls':counts['one_quartic'],
                      'one_quadratic_calls':counts['one_quadratic'],
                      'multi_remaining_leaves':still})
    return full,trace


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--max-depth',type=int,default=12)
    p.add_argument('--output',type=Path,default=Path('P10QB_M8_HYBRID_READINESS_ALL48.json'))
    args=p.parse_args()
    if args.max_depth<0 or args.max_depth>12:
        p.error('depth must be 0..12')
    digest=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    baseline=json.loads(args.baseline.read_text(encoding='utf-8'))
    if digest!=m8.PINNED_M8_SHA256 or baseline['mesh_sha256']!=digest or baseline['bin_count']!=48:
        raise SystemExit('P10QB_STOP_UNACCEPTED_M8_OR_BASELINE')
    xyz,conn,ids,types,faces=m8.parse_msh(args.mesh)
    X=xyz[conn]
    detc=phys.detj_bernstein_cubic_from_affine_jacobian(phys.jacobian_at_reference_vertices(X))
    if np.any(detc.min(axis=1)<=512*np.finfo(float).eps*np.max(np.abs(detc),axis=1)):
        raise SystemExit('P10QB_STOP_NOT_GLOBALLY_POSITIVE_JACOBIAN')
    root_control=X.copy()
    for k,(a,b) in enumerate(py.EDGES,start=4):
        root_control[:,k]=2*X[:,k]-.5*(X[:,a]+X[:,b])
    rootlo,roothi=root_control.min(axis=1)-m8.CENTER,root_control.max(axis=1)-m8.CENTER
    bins=[]
    for no,b in enumerate(baseline['bins']):
        ir,im,ip=(b[k] for k in ('radial_bin','mu_bin','phi_bin'))
        possible,_,_=m8.candidate_masks(rootlo,roothi,ir,im,ip)
        candidates=np.flatnonzero(possible)
        if len(candidates)!=b['original_possible_Tet10']:
            raise ValueError('P10PZ candidate set changed')
        physical_total=float((detc[candidates].mean(axis=1)/6.).sum())
        rows=[{'depth':d,'inside_physical_m3':0.,'outside_physical_m3':0.,
               'one_quartic_physical_m3':0.,'one_quadratic_physical_m3':0.,
               'multi_remaining_physical_m3':0.,'one_quartic_calls':0,
               'one_quadratic_calls':0,'multi_remaining_leaves':0}
              for d in range(args.max_depth+1)]
        for e in candidates:
            full,history=one_child_audit(X[e],detc[e],ir,im,ip,args.max_depth)
            for row,h in zip(rows,history):
                for key in ('inside_physical_m3','outside_physical_m3',
                            'one_quartic_physical_m3','one_quadratic_physical_m3',
                            'multi_remaining_physical_m3','one_quartic_calls',
                            'one_quadratic_calls','multi_remaining_leaves'):
                    row[key]+=h[key]
        for row in rows:
            subtotal=sum(row[k+'_physical_m3'] for k in
                         ('inside','outside','one_quartic','one_quadratic'))+row['multi_remaining_physical_m3']
            if abs(subtotal-physical_total)>2e-11*physical_total:
                raise ValueError('hybrid physical mass not conservative')
            row['multi_remaining_fraction_candidate_mass']=row['multi_remaining_physical_m3']/physical_total
        bins.append({'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
                     'candidate_count':len(candidates),'candidate_physical_m3':physical_total,
                     'depth_records':rows})
        last=rows[-1]
        print(f'P10QB_HYBRID_BIN_{no+1:02d}/48 r={ir} mu={im} phi={ip} '
              f'oneQ={last["one_quartic_calls"]} one2={last["one_quadratic_calls"]} '
              f'multi={last["multi_remaining_leaves"]} '
              f'multi_phys_frac={last["multi_remaining_fraction_candidate_mass"]:.7g}',flush=True)
    report={'stage':'P10QB','status':'PASS_HYBRID_M8_48_BIN_GEOMETRIC_READINESS_NOT_FULL_ALGOIM',
            'mesh_sha256':digest,'mesh_changed':False,'fem_started':False,'gmsh_generated':False,
            'method':'Stop true M8 physical h-subtet when exactly one constraint remains, recurse only multi-active',
            'metric_warning':'one_quartic_calls are potential Algoim integrations, NOT yet executed for all48',
            'max_depth':args.max_depth,'bin_count':len(bins),'bins':bins}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('P10QB_HYBRID_READINESS_ALL48_PASS',flush=True)


if __name__=='__main__':
    main()
