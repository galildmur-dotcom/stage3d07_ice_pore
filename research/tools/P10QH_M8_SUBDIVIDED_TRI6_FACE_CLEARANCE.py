#!/usr/bin/env python3
"""P10QH: subdivide actual curved M8 Tet10 faces before spherical-cell QA.

Each child is an exact degree-two polynomial restriction in real arithmetic.
Floating interval enclosures have a protective margin; this is *not* a
formally directed-rounded certificate. No mesh modification or physics.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QE_M8_ADAPTIVE_SPHERICAL_FE_PILOT as qe
import P10QF_M8_FACE_AWARE_SPHERICAL_FE_PILOT as qf
import P10QG_M8_CONSERVATIVE_CURVED_FACE_CLEARANCE as qg
from P10QD_M8_SPHERICAL_TET10_POINT_LOCATION import CurvedTet10Locator

EDGES=((0,1),(1,2),(2,0))
CHILD_VERTICES=np.array([
    [[1,0,0],[.5,.5,0],[.5,0,.5]],
    [[.5,.5,0],[0,1,0],[0,.5,.5]],
    [[.5,0,.5],[0,.5,.5],[0,0,1]],
    [[.5,.5,0],[0,.5,.5],[.5,0,.5]],
],dtype=float)
MARGIN=qg.MARGIN_M


def tri_shape(b):
    a,c,d=np.moveaxis(np.asarray(b),-1,0)
    return np.stack((a*(2*a-1),c*(2*c-1),d*(2*d-1),
                     4*a*c,4*c*d,4*d*a),axis=-1)


def child_reference_nodes(vertices):
    return np.vstack((vertices,[(vertices[a]+vertices[b])/2 for a,b in EDGES]))


CHILD_MATRICES=np.stack([tri_shape(child_reference_nodes(v)) for v in CHILD_VERTICES])


def real_m8_unique_faces(X,conn):
    """Recover physical six-node faces and independently detect P2 conformity."""
    registry={};inc=Counter()
    for e,row in enumerate(conn):
        corners=row[:4]
        for face in qg.FACES:
            key=tuple(sorted(int(corners[k]) for k in face))
            pairs=[tuple(sorted((face[k],face[(k+1)%3]))) for k in range(3)]
            midloc=[qg.EDGE_MID[t] for t in pairs]
            mids={tuple(sorted((int(corners[a]),int(corners[b])))):int(row[qg.EDGE_MID[a,b]])
                  for a,b in pairs}
            if key not in registry:
                registry[key]=(mids,np.vstack((X[e,list(face)],X[e,midloc])))
            elif registry[key][0]!=mids:
                raise ValueError('P10QH_NONCONFORMING_SHARED_TRI6')
            inc[key]+=1
    if len(registry)!=25911 or any(n not in (1,2) for n in inc.values()):
        raise ValueError('P10QH_M8_TOPOLOGY_MISMATCH')
    return np.array([v[1] for v in registry.values()]),inc


def subdivide_faces(faces,levels):
    """Shape (faces,4**levels,6,3), with barycentric patch vertices."""
    out=faces[:,None,:,:]
    vertices=np.eye(3)[None,:,:]
    for _ in range(levels):
        out=np.einsum('cij,fpjk->fpcik',CHILD_MATRICES,out).reshape(len(faces),-1,6,3)
        vertices=np.einsum('cij,pjk->pcik',CHILD_VERTICES,vertices).reshape(-1,3,3)
    return out,vertices


def curved_patch_bounds(patches):
    bez=patches.copy()
    for k,(a,b) in enumerate(EDGES,start=3):
        bez[:,:,k,:]=2*patches[:,:,k,:]-.5*(patches[:,:,a,:]+patches[:,:,b,:])
    normal=np.cross(patches[:,:,1,:]-patches[:,:,0,:],
                    patches[:,:,2,:]-patches[:,:,0,:])
    scale=np.linalg.norm(normal,axis=-1)
    if not np.all(np.isfinite(scale)) or np.any(scale<1e-28):
        raise ValueError('P10QH_DEGENERATE_SUBPATCH_NORMAL')
    normal/=scale[...,None]
    rel=bez-m8.CENTER
    projection=np.einsum('fpvc,fpc->fpv',rel,normal)
    return (rel.min(axis=2),rel.max(axis=2),normal,
            projection.min(axis=2),projection.max(axis=2))


def patch_possible(indices,box_lo,box_hi,bounds):
    """Return original face IDs which *might* touch the spherical cell."""
    low,high,normal,pmin,pmax=bounds
    if len(indices)==0:
        return indices
    overlap=np.all((low[indices]<=box_hi+MARGIN)&
                   (high[indices]>=box_lo-MARGIN),axis=-1)
    candidates=indices[np.any(overlap,axis=1)]
    if len(candidates)==0:
        return candidates
    n=normal[candidates]
    qmin=np.sum(np.where(n>=0,box_lo,box_hi)*n,axis=-1)
    qmax=np.sum(np.where(n>=0,box_hi,box_lo)*n,axis=-1)
    feasible=(qmax>=pmin[candidates]-MARGIN)&(qmin<=pmax[candidates]+MARGIN)
    return candidates[np.any(feasible&overlap[np.any(overlap,axis=1)],axis=1)]


def check_restriction_and_enclosure(faces,patches,vertices,bounds):
    """Independent interior point checks for actual face-polynomial restrictions."""
    rng=np.random.default_rng(20261128)
    indices=rng.choice(len(faces),min(200,len(faces)),replace=False)
    max_gap=0.;max_violation=0.;num=0
    lo,hi,n,pmin,pmax=bounds
    for i in indices:
        for j,tri in enumerate(vertices):
            for _ in range(3):
                w=rng.dirichlet((1.7,1.4,1.3))
                parent_b=w@tri
                expected=tri_shape(parent_b)@faces[i]
                actual=tri_shape(w)@patches[i,j]
                max_gap=max(max_gap,float(np.max(abs(expected-actual))))
                relative=actual-m8.CENTER
                max_violation=max(max_violation,float(np.max(lo[i,j]-relative)),
                                  float(np.max(relative-hi[i,j])),
                                  float(pmin[i,j]-relative@n[i,j]),
                                  float(relative@n[i,j]-pmax[i,j]))
                num+=1
    if max_gap>5e-14 or max_violation>2e-14:
        raise ValueError(f'P10QH_PATCH_RESTRICTION_ENCLOSURE_FAILED {max_gap} {max_violation}')
    return {'random_real_face_subpatch_interior_points':num,
            'maximum_parent_vs_subpatch_coordinate_gap_m':max_gap,
            'maximum_bezier_enclosure_violation_m':max_violation}


def run_case(locator,bounds,ir,im,level,max_depth,max_cells,rng):
    root=qe.bin_box(ir,im,0);vol=qg.size_volume(root)
    stack=[(root,0,np.arange(len(bounds[0]),dtype=np.int32))]
    visited=pure=unresolved=sampled=0
    pure_vol=unresolved_vol=0.;min_face=math.inf;max_face=0
    while stack:
        box,depth,ids=stack.pop()
        visited+=1
        if visited>max_cells:
            raise ValueError('P10QH_NODE_CAP_REACHED_FAIL_CLOSED')
        lo,hi=qg.spherical_box_aabb(box)
        possibilities=patch_possible(ids,lo,hi,bounds)
        cnt=len(possibilities);min_face=min(min_face,cnt);max_face=max(max_face,cnt)
        if not cnt:
            r0,r1,m0,m1,p0,p1=box
            r=.5*(r0+r1);mu=.5*(m0+m1);phi=.5*(p0+p1)
            xy=r*math.sqrt(max(0.,1-mu*mu))
            point=np.array([xy*math.cos(phi),xy*math.sin(phi),.03+r*mu])
            elem,_=locator.locate(point)
            if elem is None:
                raise ValueError('P10QH_PURE_BOX_WITHOUT_TET10')
            pure+=1;pure_vol+=qg.size_volume(box)
            if sampled<480:
                qg.pass_samples_in_pure_box(locator,box,elem,rng)
                sampled+=12
        elif depth==max_depth:
            unresolved+=1;unresolved_vol+=qg.size_volume(box)
        else:
            a,b=qf.bisect(box,int(np.argmax(qf.widths(box))))
            stack.append((a,depth+1,possibilities))
            stack.append((b,depth+1,possibilities))
        if visited%10000==0:
            print(f'P10QH_HEARTBEAT level={level} r={ir} mu={im} '
                  f'visited={visited} pure={pure}',flush=True)
    closure=abs(pure_vol+unresolved_vol-vol)/vol
    if closure>1e-11:
        raise ValueError('P10QH_VOLUME_PARTITION_FAILURE')
    return {'radial_bin':ir,'mu_bin':im,'phi_bin':0,'bezier_subdivision_levels':level,
            'spherical_depth_limit':max_depth,'spherical_boxes_visited':visited,
            'pure_boxes':pure,'unresolved_terminal_boxes':unresolved,
            'pure_volume_fraction':pure_vol/vol,'unresolved_volume_fraction':unresolved_vol/vol,
            'volume_partition_relative_error':closure,'min_faces_possible':min_face,
            'max_faces_possible':max_face,'independent_pure_box_locator_checks':sampled}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh',type=Path,required=True)
    parser.add_argument('--P10QE-topology',type=Path,required=True)
    parser.add_argument('--levels',nargs='+',type=int,default=[0,1,2])
    parser.add_argument('--max-depth',type=int,default=11)
    parser.add_argument('--max-cells-per-bin',type=int,default=140000)
    parser.add_argument('--output',type=Path,default=Path('P10QH_M8_SUBDIVIDED_TRI6_FACE_CLEARANCE_QA.json'))
    args=parser.parse_args()
    if any(level not in (0,1,2) for level in args.levels) or len(set(args.levels))!=len(args.levels):
        raise ValueError('Unsupported or duplicate subpatch subdivision levels')
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    topo=json.loads(args.P10QE_topology.read_text())
    if sha!=m8.PINNED_M8_SHA256 or topo['mesh_sha256']!=sha or not topo['domain_topology_and_outer_boundary']['all_exposed_faces_tagged_exactly_once']:
        raise ValueError('P10QH_M8_PIN_TOPOLOGY_MISMATCH')
    xyz,conn,*_=m8.parse_msh(args.mesh);X=xyz[conn]
    faces,inc=real_m8_unique_faces(X,conn)
    limit=.001600000001
    # Use parent *Bezier* hull for the region prefilter; a bulging Tri6
    # face may extend past the hull of its six Lagrange nodes.
    parent_bounds=curved_patch_bounds(faces[:,None,:,:])
    region=np.all(parent_bounds[0][:,0]<=limit,axis=1)&np.all(parent_bounds[1][:,0]>=-limit,axis=1)
    faces=faces[region]
    locator=CurvedTet10Locator(X);rng=np.random.default_rng(20261128)
    results=[];validations=[];runstart=time.monotonic()
    for lev in args.levels:
        start=time.monotonic()
        patches,vertices=subdivide_faces(faces,lev)
        bounds=curved_patch_bounds(patches)
        validation=check_restriction_and_enclosure(faces,patches,vertices,bounds)
        validation['level']=lev;validation['number_of_subpatches']=len(faces)*4**lev
        validation['build_and_validation_seconds']=time.monotonic()-start
        validations.append(validation)
        for ir in (0,4):
            for im in (0,9):
                c=run_case(locator,bounds,ir,im,lev,args.max_depth,args.max_cells_per_bin,rng)
                results.append(c)
                print(f'P10QH_CASE level={lev} r={ir} mu={im} pure={c["pure_volume_fraction"]:.7g} '
                      f'cells={c["spherical_boxes_visited"]}',flush=True)
    comparison=[]
    by={(x['bezier_subdivision_levels'],x['radial_bin'],x['mu_bin']):x for x in results}
    for ir in (0,4):
        for im in (0,9):
            row={'radial_bin':ir,'mu_bin':im}
            for lev in args.levels:
                v=by[lev,ir,im]
                row[f'level_{lev}_pure_volume_fraction']=v['pure_volume_fraction']
                row[f'level_{lev}_boxes']=v['spherical_boxes_visited']
            if 0 in args.levels:
                for lev in args.levels:
                    if lev:
                        gain=by[lev,ir,im]['pure_volume_fraction']-by[0,ir,im]['pure_volume_fraction']
                        if gain<-2e-10:
                            raise ValueError('P10QH_REFINEMENT_WORSENED_CONSERVATIVE_CLASSIFICATION')
                        row[f'level_{lev}_absolute_pure_volume_gain']=gain
            comparison.append(row)
    report={'stage':'P10QH','status':'PASS_CONSERVATIVE_FLOAT_SUBDIVIDED_REAL_TRI6_FACES_NOT_FORMAL_CERTIFICATE',
            'mesh_sha256':sha,'mesh_modified':False,'Gmsh_run':False,'physical_FEM_run':False,
            'unique_real_curved_faces':len(inc),'near_pore_candidate_faces':len(faces),
            'levels':args.levels,'max_spherical_depth':args.max_depth,
            'floating_protective_margin_m':MARGIN,
            'limitations':'Face-subpatch Bezier enclosures use floating coordinates and protective slack; not interval-directed rounding or proof of global M8 embedding. Pure volumes conditional on embedded conforming Tet10 mesh.',
            'independent_restriction_and_hull_checks':validations,
            'comparison':comparison,'cases':results,'elapsed_s':time.monotonic()-runstart,
            'absolute_integration_error_certified':False,'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('P10QH_PASS_SUBDIVIDED_FACE_CLEARANCE',flush=True)


if __name__=='__main__':
    main()
