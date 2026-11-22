#!/usr/bin/env python3
"""P10EE: source-only/raw-mesh surface-vs-volume adaptation diagnostic.

Read original M1/M2 only; no native Gmsh, no physical FEM, no markers.
Pore Tri6 curvilinear area and spatial QP-effective element area in two caps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import zipfile

import numpy as np

import p10ed_verify_original_m1_m2_raw_spatial as raw

SOURCE_SHA="8b1650ae7808b117f5778ca726b2542c9cbc59365a09913128a322713b254009"
CAP_MU=.8
RADIUS=.001
NEAR_SIZE=.00042855883184652975
TARGET_VOL=.8
TARGET_H=TARGET_VOL**(1/3)
TARGET_AREA=TARGET_H**2
EDGE=((0,1),(1,2),(2,0))


def check_field(package: Path) -> dict:
    raw.ensure(raw.digest(package)==SOURCE_SHA,"exact P10EA R1 source ZIP SHA")
    with zipfile.ZipFile(package) as z:
        geo=z.read("P10DV_M2_INLINE_FIELD20.geo").decode("utf-8")
        cad=z.read("sphere_pore_B6_refined.geo").decode("utf-8")
    raw.ensure("Field[6] = MathEval;" in geo and
               "Background Field=6;" in geo and
               "Include \"sphere_pore_B6_refined.geo\";" in geo and
               geo.count("Field[6].F = ")==1 and
               "F2*exp(log(1-0.2*" in geo and
               "Field[1].SurfacesList={pore()};" in cad and
               "Field[2] = Threshold;" in cad and
               "Field[2].SizeMin=nearSize;" in cad and
               "Field[2].DistMin=0.0015;" in cad and
               "Mesh.MeshSizeFromPoints=0;" in cad and
               "Mesh.MeshSizeFromCurvature=0;" in cad and
               "Mesh.MeshSizeExtendFromBoundary=0;" in cad and
               "Mesh.Algorithm3D=10;" in cad,
               "exact field/background/CAD configuration mismatch")
    return {"source_archive_sha256":SOURCE_SHA,
       "background_field_final":"Field[6] MathEval(F2 * (1-0.20*kappa)^(1/3))",
       "scope":"one Background Field=6 for entire meshing request, no separate 3D-only field",
       "F2_distance_source":"CAD Physical pore surface, Distance + Threshold, nearSize within 1.5mm",
       "F2_near_size_mm":NEAR_SIZE*1e3,
       "F6_polar_surface_target_size_mm":NEAR_SIZE*TARGET_H*1e3,
       "target_volume_ratio_polar":TARGET_VOL,
       "target_surface_edge_ratio_polar":TARGET_H,
       "target_surface_element_area_ratio_polar":TARGET_AREA,
       "mesh_size_from_points":False,"mesh_size_from_curvature":False,
       "extend_sizes_from_boundary":False,"algorithm_3d":10}


def tri_basis(order: int):
    gp, gw=np.polynomial.legendre.leggauss(order)
    x=(gp+1)/2
    w=gw/2
    dl=np.array([[-1.,-1.],[1.,0.],[0.,1.]])
    ns, ds, ws=[],[],[]
    for a,wa in zip(x,w):
        for b,wb in zip(x,w):
            u=a; v=(1-a)*b
            l=np.array([1-u-v,u,v])
            n=list(l*(2*l-1))
            d=list((4*l[:,None]-1)*dl)
            for i,j in EDGE:
                n.append(4*l[i]*l[j])
                d.append(4*(l[i]*dl[j]+l[j]*dl[i]))
            ns.append(n);ds.append(d);ws.append(wa*wb*(1-a))
    ns=np.array(ns);ds=np.array(ds);ws=np.array(ws)
    raw.ensure(abs(ws.sum()-.5)<2e-15 and
       np.max(abs(ns.sum(axis=1)-1))<2e-14 and
       np.max(abs(ds.sum(axis=1)))<2e-14,
       "Tri6 Lagrange/Duffy surface quadrature selftest")
    return ns,ds,ws


def surface_areas(p: np.ndarray, ns: np.ndarray, ds: np.ndarray, ws: np.ndarray):
    J=np.einsum("nic,qij->nqcj",p,ds,optimize=True)
    # Shape [tri, q, physical_xyz, local_param(2)].
    area_j=np.linalg.norm(np.cross(J[:,:,:,0], J[:,:,:,1]),axis=2)
    xyz=np.einsum("qi,nic->nqc",ns,p,optimize=True)
    return area_j@ws, area_j, xyz


def surface_stats(mesh: dict, order: int) -> dict:
    pore=mesh["nodes"][mesh["pore_tri6"]]
    n,d,w=tri_basis(order)
    area, jac, qp=surface_areas(pore,n,d,w)
    raw.ensure(np.all(jac>0) and np.all(area>0),"surface Jacobian")
    z=(qp-raw.CENTRE)
    rho=np.linalg.norm(z,axis=-1)
    mu=z[:,:,2]/rho
    weights=jac*w[None,:]
    am=np.broadcast_to(area[:,None], weights.shape)
    zones={}
    for key,sel in (("north",mu>=CAP_MU),("south",mu<=-CAP_MU),
                    ("both_poles",abs(mu)>=CAP_MU),
                    ("nonpolar",abs(mu)<CAP_MU)):
        qarea=float(weights[sel].sum())
        partial=float((weights[sel]/am[sel]).sum())
        zones[key]={"curved_qp_area_m2":qarea,"fractional_surface_tri6":partial,
            "effective_curved_Tri6_area_m2":qarea/partial,
            "area_analytic_m2":(4*math.pi*RADIUS**2*(1-CAP_MU) *
                                  (0.5 if key in ("north","south") else 1)
                                  if key!="nonpolar" else 4*math.pi*RADIUS**2*CAP_MU)}
    vertices=pore[:,:3,:]
    cent=vertices.mean(axis=1)
    cmu=(cent[:,2]-.03)/np.linalg.norm(cent-raw.CENTRE,axis=-1)
    edges=np.stack([np.linalg.norm(pore[:,i]-pore[:,j],axis=1) for i,j in EDGE],axis=1)
    node_cloud=np.unique(mesh["pore_tri6"].ravel())
    nodes=mesh["nodes"][node_cloud]
    locations={}
    for name,sign in (("north",1),("south",-1)):
        pole=raw.CENTRE+np.array([0,0,sign*RADIUS])
        locations[name]={"nearest_surface_node_distance_mm":float(np.min(np.linalg.norm(nodes-pole,axis=1))*1000),
                         "tri6_by_corner_centroid":int(np.count_nonzero(cmu*sign>=CAP_MU)),
                         "median_surface_corner_edge_length_mm":float(np.median(edges[cmu*sign>=CAP_MU])*1000)}
    return {"tri6":len(pore),"surface_quadrature_order":order,
       "curved_full_pore_area_m2":float(area.sum()),
       "analytical_full_pore_area_m2":4*math.pi*RADIUS**2,
       "curved_full_vs_analytic_rel_error":float(area.sum()/(4*math.pi*RADIUS**2)-1),
       "max_quadratic_surface_interior_radial_deviation_m":float(np.max(abs(rho-RADIUS))),
       "zones":zones,"poles":locations}


def selftest() -> None:
    n,d,w=tri_basis(3)
    v=np.array([[0.,0.,0.],[.001,0.,0.],[0.,.001,0.]])
    p=np.concatenate([v,np.array([(v[i]+v[j])/2 for i,j in EDGE])])
    area,j,x=surface_areas(p[None],n,d,w)
    raw.ensure(abs(area[0]-5e-7)<1e-21 and
       np.max(abs(j-1e-6))<1e-19 and x.shape==(1,9,3),
       "affine Tri6 unit surface area")
    print("P10EE_TRI6_SURFACE_SELFTEST_PASS affine=PASS curved_area=PASS no_Gmsh=1 FEM=0")


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m1",type=Path)
    ap.add_argument("--m2",type=Path)
    ap.add_argument("--source-release",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args()
    selftest()
    if args.selftest:return 0
    raw.ensure(all((args.m1,args.m2,args.source_release,args.out)),"all input paths and output required")
    source=check_field(args.source_release)
    a=raw.parse_msh2(args.m1,raw.M1_SHA)
    b=raw.parse_msh2(args.m2,raw.M2_SHA)
    result={"protocol":"P10EE_PORE_TRI6_SURFACE_VS_VOLUME_SOURCE_ONLY",
        "source":source,"m1_sha256":raw.M1_SHA,"m2_sha256":raw.M2_SHA,
        "no_gmsh_no_fem_no_marker":True,
        "mesh_field_source_scope":"Global Background Field=6 used by regular Gmsh 1D, 2D and 3D generation; source has no explicit surface-only stage",
        "surface_spatial_qp_quadrature_sensitivity":{}}
    for order in (3,5,9,15):
        m1=surface_stats(a,order)
        m2=surface_stats(b,order)
        pairs={}
        for key in m1["zones"]:
            x=m1["zones"][key]
            y=m2["zones"][key]
            pairs[key]={"m2_over_m1_surface_effective_curved_tri6_area":
                         y["effective_curved_Tri6_area_m2"]/x["effective_curved_Tri6_area_m2"],
                        "m2_over_m1_qp_region_area":y["curved_qp_area_m2"]/x["curved_qp_area_m2"],
                        "m1_qp_vs_analytic_area":x["curved_qp_area_m2"]/x["area_analytic_m2"]-1,
                        "m2_qp_vs_analytic_area":y["curved_qp_area_m2"]/y["area_analytic_m2"]-1}
        result["surface_spatial_qp_quadrature_sensitivity"][str(order)]={"M1":m1,"M2":m2,"comparison":pairs}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"P10EE_PORE_TRI6_SURFACE_FIELD_DIAGNOSTIC.json").write_text(
         json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    v=result["surface_spatial_qp_quadrature_sensitivity"]["15"]["comparison"]
    print("P10EE_ORIGINAL_M1_M2_PORE_TRI6_SURFACE_AUDIT_OK",
       "target_area_ratio",format(TARGET_AREA,".8g"),
       "north_observed_area_ratio",format(v["north"]["m2_over_m1_surface_effective_curved_tri6_area"],".8g"),
       "south",format(v["south"]["m2_over_m1_surface_effective_curved_tri6_area"],".8g"),
       "Gmsh=0 FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
