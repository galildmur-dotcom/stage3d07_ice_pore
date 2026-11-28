#!/usr/bin/env python3
"""Stage3D07 P10PY: certified h-refinement of accepted M8 curved Tet10.

Every split is an affine subdivision of the reference tetrahedron. The
restriction of its genuine degree-2 isoparametric map is evaluated exactly
as 10 quadratic Bezier control points. Their convex hull yields conservative
interval enclosures; hence OUTSIDE / INSIDE classifications are safe.

Pure geometry, source-only: no CAD, Gmsh optimization, mesh edits, FEM/EDV.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8

REF_TET = np.array([[0., 0., 0.], [1., 0., 0.],
                    [0., 1., 0.], [0., 0., 1.]], dtype=np.float64)
EDGES = np.array([(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])


def map_tet10_nodally(X: np.ndarray, uvw: np.ndarray) -> np.ndarray:
    """Evaluate exact parent Tet10 F at a batch of reference points.

    X = physical coordinates of 10 nodes, uvw=(m,10,3); return (m,10,3).
    """
    l = np.concatenate((1.-uvw.sum(axis=2, keepdims=True), uvw),axis=2)
    basis = np.empty((len(uvw), uvw.shape[1], 10),dtype=np.float64)
    basis[:,:,:4] = l*(2*l-1)
    for j,(a,b) in enumerate(EDGES):
        basis[:,:,4+j] = 4*l[:,:,a]*l[:,:,b]
    return np.einsum("msk,kd->msd",basis,X)


def subcell_envelopes(X: np.ndarray, vertices: np.ndarray):
    """Return a rigorous convex-hull AABB and exact physical vertices."""
    mid = .5*(vertices[:,EDGES[:,0]] + vertices[:,EDGES[:,1]])
    mapped = map_tet10_nodally(X,np.concatenate((vertices,mid),axis=1))
    control = mapped.copy()
    for k,(a,b) in enumerate(EDGES,start=4):
        control[:,k] = 2*mapped[:,k]-.5*(mapped[:,a]+mapped[:,b])
    return control.min(axis=1)-m8.CENTER,control.max(axis=1)-m8.CENTER,mapped[:,:4]


def bisect_longest_curved_edge(ref_vertices: np.ndarray,physical_vertices: np.ndarray):
    """Binary exact partition along each subcell's longest physical edge."""
    a=physical_vertices[:,EDGES[:,0],:]
    b=physical_vertices[:,EDGES[:,1],:]
    longest=np.argmax(np.sum((a-b)**2,axis=2),axis=1)
    ea,eb=EDGES[longest,0],EDGES[longest,1]
    index=np.arange(len(ref_vertices))
    midpoint=.5*(ref_vertices[index,ea]+ref_vertices[index,eb])
    left=ref_vertices.copy();right=ref_vertices.copy()
    left[index,ea]=midpoint
    right[index,eb]=midpoint
    return np.concatenate((left,right),axis=0)


def adaptive_one(X: np.ndarray,ir: int,im: int,ip: int,maximum: int):
    active=REF_TET[np.newaxis].copy()
    certified_inside=0.;certified_outside=0.
    results=[]
    for depth in range(maximum+1):
        if len(active):
            lo,hi,phys=subcell_envelopes(X,active)
            possible,inside,status=m8.candidate_masks(lo,hi,ir,im,ip)
            excluded=~possible
            unknown=possible&~inside
            weight=2.**(-depth)
            certified_inside+=float(inside.sum())*weight
            certified_outside+=float(excluded.sum())*weight
            quartic=(status[:,[0,1,3]]==0).sum(axis=1)
            unknown_quartic=quartic[unknown]
            ambiguous_multi=float((unknown_quartic>=2).sum())*weight
            ambiguous_one=float((unknown_quartic==1).sum())*weight
            ambiguous_zero=float((unknown_quartic==0).sum())*weight
            unknown_count=int(unknown.sum())
            if depth<maximum:
                active=bisect_longest_curved_edge(active[unknown],phys[unknown])
        else:
            unknown_count=0;ambiguous_multi=ambiguous_one=ambiguous_zero=0.
        undecided=unknown_count*2.**(-depth)
        if abs(certified_inside+certified_outside+undecided-1.)>1e-10:
            raise ValueError("reference tetra partition mass not conservative")
        if abs(undecided-ambiguous_multi-ambiguous_one-ambiguous_zero)>1e-12:
            raise ValueError("ambiguous quartic phase partition not conservative")
        results.append({
            "depth":depth,"certified_inside_fraction":certified_inside,
            "certified_outside_fraction":certified_outside,
            "uncertain_fraction":undecided,
            "multi_quartic_uncertain_fraction":ambiguous_multi,
            "one_quartic_uncertain_fraction":ambiguous_one,
            "zero_quartic_uncertain_fraction":ambiguous_zero,
            "uncertain_leaves":unknown_count,
            "still_ambiguous":bool(unknown_count),
            "still_multi_quartic":bool(ambiguous_multi)
        })
    return results


def test_exact_map_restriction(X: np.ndarray):
    """Check exact quadratic control net, including on a split subcell."""
    sub=REF_TET[np.newaxis].copy()
    for _ in range(3):
        _,_,physical=subcell_envelopes(X,sub)
        sub=bisect_longest_curved_edge(sub,physical)
        sub=sub[:1]
    low,high,_=subcell_envelopes(X,sub)
    bary=np.random.default_rng(20261128).dirichlet(np.ones(4),size=30)
    sample=bary@sub[0]
    pos=map_tet10_nodally(X,sample[:,np.newaxis,:])[:,0,:]
    if not (np.all(pos>=low[0]+m8.CENTER-1e-13)
            and np.all(pos<=high[0]+m8.CENTER+1e-13)):
        raise ValueError("Bezier convex hull does not enclose curved Tet10")
    # The actual restricted geometric function is still the same parent F.
    p=sample[0]
    n,_=m8.tet10_shape(p)
    if not np.allclose(pos[0],n@X,rtol=1e-12,atol=1e-15):
        raise ValueError("exact Tet10 map restriction does not commute")


def quadrature_volume(X: np.ndarray,subcell: np.ndarray) -> float:
    """Independent q4 Duffy quadrature of true Tet10 Jacobian on a subcell."""
    u,ww=np.polynomial.legendre.leggauss(4)
    u=.5*(u+1);ww=.5*ww
    a=subcell[1]-subcell[0]
    b=subcell[2]-subcell[0]
    c=subcell[3]-subcell[0]
    A=np.column_stack((a,b,c))
    result=0.
    for i,x in enumerate(u):
        for j,y in enumerate(u):
            for k,z in enumerate(u):
                p=np.array([x,(1-x)*y,(1-x)*(1-y)*z])
                parent_pt=subcell[0]+A@p
                _,G=m8.tet10_shape(parent_pt)
                J=X.T@G@A
                result+=ww[i]*ww[j]*ww[k]*(1-x)**2*(1-y)*np.linalg.det(J)
    return float(result)


def check_physical_volume_partition(X: np.ndarray) -> float:
    """Exact h-subcells must preserve the parent's *physical* Tet10 volume."""
    root_vol=quadrature_volume(X,REF_TET)
    if root_vol<=0:
        raise ValueError("nonpositive true physical volume")
    sub=REF_TET[np.newaxis].copy()
    for _ in range(4):
        _,_,physical=subcell_envelopes(X,sub)
        sub=bisect_longest_curved_edge(sub,physical)
    subtotal=sum(quadrature_volume(X,child) for child in sub)
    err=abs(subtotal-root_vol)/root_vol
    if err>1e-12:
        raise ValueError("physical Tet10 volume was not preserved by reference subdivision")
    return err


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mesh",type=Path,required=True)
    p.add_argument("--max-depth",type=int,default=8)
    p.add_argument("--all-azimuth",action="store_true",
                   help="audit all 12 phi bins instead of two adjacent-to-zero wedges")
    p.add_argument("--output",type=Path,default=Path("P10PY_M8_BEZIER_ADAPTIVE_QA.json"))
    args=p.parse_args()
    if not 0<=args.max_depth<=12:
        p.error("max-depth must be in 0..12")
    mesh_hash=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    if mesh_hash != m8.PINNED_M8_SHA256:
        raise SystemExit("P10PY_STOP_M8_SHA_NOT_ACCEPTED")
    xyz,conn,ids,types,faces=m8.parse_msh(args.mesh)
    X=xyz[conn]
    bezier=X.copy()
    for k,(a,b) in enumerate(EDGES,start=4):
        bezier[:,k]=2*X[:,k]-.5*(X[:,a]+X[:,b])
    root_lo=bezier.min(axis=1)-m8.CENTER
    root_hi=bezier.max(axis=1)-m8.CENTER
    phys_partition_error=0.
    for k in [0,len(X)//2,len(X)-1]:
        test_exact_map_restriction(X[k])
        phys_partition_error=max(phys_partition_error,check_physical_volume_partition(X[k]))

    bins_phi=range(12) if args.all_azimuth else [5,6]
    bin_list=[(ir,im,ip) for ir in [0,4] for im in [0,9] for ip in bins_phi]
    all_bins=[]
    for ir,im,ip in bin_list:
        possible,_,_=m8.candidate_masks(root_lo,root_hi,ir,im,ip)
        candidate=np.flatnonzero(possible)
        total=len(candidate)
        accum=[{"depth":d,"certified_inside_sum":0.,"certified_outside_sum":0.,
                "uncertain_sum":0.,"multi_quartic_sum":0.,"one_quartic_sum":0.,
                "zero_quartic_sum":0.,"uncertain_leaves":0,
                "ambiguous_elements":0,"multi_quartic_elements":0}
               for d in range(args.max_depth+1)]
        for idx in candidate:
            results=adaptive_one(X[idx],ir,im,ip,args.max_depth)
            for level,row in enumerate(results):
                a=accum[level]
                for f,t in [("certified_inside_fraction","certified_inside_sum"),
                            ("certified_outside_fraction","certified_outside_sum"),
                            ("uncertain_fraction","uncertain_sum"),
                            ("multi_quartic_uncertain_fraction","multi_quartic_sum"),
                            ("one_quartic_uncertain_fraction","one_quartic_sum"),
                            ("zero_quartic_uncertain_fraction","zero_quartic_sum"),
                            ("uncertain_leaves","uncertain_leaves")]:
                    a[t]+=row[f]
                a["ambiguous_elements"]+=int(row["still_ambiguous"])
                a["multi_quartic_elements"]+=int(row["still_multi_quartic"])
        for a in accum:
            a["unresolved_reference_volume_fraction_of_candidates"]=(
                a["uncertain_sum"]/total if total else 0)
            a["multi_quartic_reference_volume_fraction_of_candidates"]=(
                a["multi_quartic_sum"]/total if total else 0)
            if abs(a["certified_inside_sum"]+a["certified_outside_sum"]+
                   a["uncertain_sum"]-total)>1e-9:
                raise ValueError("aggregate tetra reference fractions do not close")
        all_bins.append({"radial_bin":ir,"mu_bin":im,"phi_bin":ip,
                         "original_possible_Tet10":total,"depth_records":accum})
        print("P10PY_BIN_DONE r="+str(ir)+" mu="+str(im)+" phi="+str(ip)+
              " root="+str(total)+" dmax_multi_frac="+
              f"{accum[-1]['multi_quartic_reference_volume_fraction_of_candidates']:.8g}"+
              " dmax_uncert_frac="+
              f"{accum[-1]['unresolved_reference_volume_fraction_of_candidates']:.8g}",flush=True)
    report={"stage":"P10PY","status":"PASS_ADAPTIVE_BEZIER_CURVED_TET10_SOURCE_ONLY",
            "mesh_sha256":mesh_hash,"mesh_changed":False,"fem_started":False,
            "gmsh_generated":False,"high_order_elastic_unchanged":True,
            "node_count":len(xyz),"tet10_count":len(X),
            "criterion":"Bezier convex-hull enclosure of exact quadratic Tet10 on each affine reference sub-tetra",
            "binary_split":"longest physical edge, midpoint in reference coordinates",
            "refinement_conservation_tolerance":1e-10,
            "independent_subcell_physical_volume_partition_rel":phys_partition_error,
            "maximum_depth":args.max_depth,
            "all_azimuth":args.all_azimuth,
            "metric_meaning":"unresolved reference-volume upper bound, not true cut-volume or FEM error",
            "bin_count":len(all_bins),"bins":all_bins}
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("P10PY_M8_CERTIFIED_H_REFINEMENT_PASS",flush=True)


if __name__=="__main__":
    main()
