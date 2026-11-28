#!/usr/bin/env python3
"""P10ES: exact-private-M1, source-only empirical C1 sizing calibration.

Jointly fits first-order Tet10 *corner edges* and pore-wall Tri6 corner
edges against the pinned M1 Threshold Field2. Curved Tet10 volumes provide
an independent equivalent-regular-tetra length diagnostic, NOT an edge.
No Gmsh, mesh emission, simulation or one-shot marker. Numeric fit is an
empirical geometry proxy, not a reproduction of Gmsh nor D-025 acceptance.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

import numpy as np

from p10ed_verify_original_m1_m2_raw_spatial import (
    CENTRE, EDGES, M1_SHA, curved, digest, kappa, parse_msh2, rule27, selftest,
)
from p10er_three_raw_msh_local_topology_forensics import coordinates

NEAR, FAR = .00042855883184652975, .0070524788853066865
DIST_MIN, DIST_MAX = .0015, .018
CORNER_ROUND_RADIUS = .00005  # 0.05 mm, source-only C1 regularization proposal
RIDGE = 1.0
MAX_LOG_OFFSET = .018  # near-wall bounded fitting correction, not a D-025 guarantee
P10EN_ZIP_SHA="4cccb95b22ea2575452a2b7b684c8e311a8d9628272775a8a633d3297b70b4bc"
M1_FIELD_GEO_SHA="c6ec88a3fe91db0f3c369391a91aefbd1bc83f1d3033b38a985c3033c605ddd8"
CAD_GEO_SHA="8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0"


def require(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError("P10ES_STOP: " + why)


def source_provenance(path: Path) -> dict:
    require(path.is_file() and digest(path)==P10EN_ZIP_SHA,"exact P10EN archive SHA")
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None,"original P10EN archive CRC")
        a=z.read("GEO/A_ORIGINAL_M1_FIELD2.geo")
        cad=z.read("GEO/sphere_pore_B6_refined.geo")
        manifest=json.loads(z.read("P10EA_RUN_MANIFEST.json"))
    require(hashlib.sha256(a).hexdigest()==M1_FIELD_GEO_SHA and
            hashlib.sha256(cad).hexdigest()==CAD_GEO_SHA and
            manifest.get("m1_sha256")==M1_SHA and
            manifest.get("original_m1_sha256")==M1_SHA,
            "exact M1 CAD/field source provenance")
    source=a.decode("ascii")
    geo=cad.decode("ascii")
    for label,number in (("nearSize",NEAR),("farSize",FAR)):
        match=re.search(r"(?m)^"+label+r"\s*=\s*([\d.eE+-]+)\s*;",source)
        require(match is not None and math.isclose(float(match.group(1)),number,rel_tol=1e-14),
                "source value "+label)
    for needle in ("Field[2] = Threshold;", "Field[2].InField=1;",
                   "Field[2].SizeMin=nearSize;", "Field[2].SizeMax=farSize;",
                   "Field[2].DistMin=0.0015;", "Field[2].DistMax=0.018;",
                   "Mesh.MeshSizeExtendFromBoundary=0;",
                   "Mesh.MeshSizeFromPoints=0;", "Mesh.MeshSizeFromCurvature=0;"):
        require(needle in geo,"M1 source Threshold/source mesh field invariant: "+needle)
    require('Background Field=2;' in source and
            'Include "sphere_pore_B6_refined.geo";' in source,
            "original M1 background field identity")
    return {"P10EN_evidence_sha256":P10EN_ZIP_SHA,
            "M1_background_Field2_GEO_sha256":M1_FIELD_GEO_SHA,
            "original_CAD_Threshold_GEO_sha256":CAD_GEO_SHA,
            "M1_mesh_sha256_from_windows_manifest":M1_SHA}


def S(x: np.ndarray) -> np.ndarray:
    t = np.clip(x, 0., 1.)
    return t*t*(3.-2.*t)


def field2(d: np.ndarray) -> np.ndarray:
    x = np.clip((d-DIST_MIN)/(DIST_MAX-DIST_MIN), 0., 1.)
    return NEAR + (FAR-NEAR)*x


def smooth_field2(d: np.ndarray) -> np.ndarray:
    """Exact original linear Threshold except within 2*epsilon at each kink.

    A quadratic Hermite join preserves value and first derivative at both
    ends; it cannot reproduce the original non-C1 kink everywhere.
    """
    d=np.asarray(d, dtype=float)
    eps=CORNER_ROUND_RADIUS
    slope=(FAR-NEAR)/(DIST_MAX-DIST_MIN)
    out=np.asarray(field2(d)).copy()
    a=(d>=DIST_MIN-eps)&(d<DIST_MIN+eps)
    b=(d>DIST_MAX-eps)&(d<=DIST_MAX+eps)
    u=(d[a]-(DIST_MIN-eps))/(2*eps)
    v=(d[b]-(DIST_MAX-eps))/(2*eps)
    out[a]=NEAR+slope*eps*u*u
    out[b]=FAR-slope*eps*(1-v)*(1-v)
    return out


def angular_basis(xyz: np.ndarray) -> np.ndarray:
    _d, mu, _phi=coordinates(xyz)
    kn=kappa(xyz)
    wn=S((mu-.6)/.2)
    ws=S((-mu-.6)/.2)
    core=S((mu-.8)/.1)
    return np.stack([kn*wn, kn*ws, kn*wn*core],axis=-1)


def proxy_data(mesh: dict, N: np.ndarray, D: np.ndarray, W: np.ndarray) -> dict:
    p=mesh["nodes"][mesh["tet10"]]
    vol,jac,xyz=curved(p,N,D,W)
    require(np.all(vol>0) and np.all(jac>0), "curved Tet10 Jacobian")
    corner=p[:,:4,:]
    edge=np.stack([np.linalg.norm(corner[:,a]-corner[:,b],axis=1)
                   for a,b in EDGES],axis=1)
    h_edge=np.median(edge,axis=1)
    h_equiv=np.cbrt(6*math.sqrt(2)*vol)
    centres=corner.mean(axis=1)
    d,mu,phi=coordinates(centres)
    tri=mesh["nodes"][mesh["pore_tri6"][:, :3]]
    t_edge=np.stack([np.linalg.norm(tri[:,a]-tri[:,b],axis=1)
                     for a,b in EDGES[:3]],axis=1)
    tri_mid=tri.mean(axis=1)-CENTRE
    tri_unit=tri_mid/np.linalg.norm(tri_mid,axis=1)[:,None]
    tri_xyz=CENTRE + .001*tri_unit  # project chord centroids to physical sphere
    return {"tet_centres":centres,"tet_edge_m":h_edge,"tet_edge_min_m":edge.min(axis=1),
            "tet_edge_max_m":edge.max(axis=1),"tet_regular_eq_m":h_equiv,
            "tet_curved_vol_m3":vol,"tet_d_m":d,"tet_mu":mu,"tet_phi":phi,
            "tri_centres":tri_xyz,"tri_edge_m":np.median(t_edge,axis=1),
            "tri_d_m":np.zeros(len(tri_xyz)),
            "tri_mu":coordinates(tri_xyz)[1],"tri_phi":coordinates(tri_xyz)[2]}


def median_stats(v: np.ndarray) -> dict:
    require(v.size>0 and np.all(np.isfinite(v)),"empty/invalid source sample")
    return {"n":int(v.size),"median":float(np.median(v)),
            "p10":float(np.quantile(v,.1)),"p90":float(np.quantile(v,.9))}


def sampling_report(data: dict) -> list[dict]:
    rows=[]
    for kind in ("Tet10", "pore_Tri6"):
        if kind=="Tet10":
            d=data["tet_d_m"];mu=data["tet_mu"];e=data["tet_edge_m"]
            eq=data["tet_regular_eq_m"]
        else:
            d=data["tri_d_m"];mu=data["tri_mu"];e=data["tri_edge_m"]
            eq=None
        for rad, lo, hi in (("0_100um",0,1e-4), ("100_500um",1e-4,5e-4),
                            ("500_1500um",5e-4,1.5e-3),
                            ("1p5_6mm",1.5e-3,6e-3),
                            ("6_18mm",6e-3,18e-3),
                            ("18mm_plus",18e-3,1)):
            for pol, ang in (("north",mu>=.8),("south",mu<=-.8),
                             ("off",np.abs(mu)<=.6)):
                m=(d>=lo)&(d<hi)&ang
                if m.sum()==0:
                    continue
                f=field2(d[m])
                rows.append({"element":kind,"radial":rad,"zone":pol,"count":int(m.sum()),
                     "median_corner_edge_mm":float(np.median(e[m])*1000),
                     "median_edge_over_original_Field2":float(np.median(e[m]/f)),
                     "p10_edge_over_Field2":float(np.quantile(e[m]/f,.1)),
                     "p90_edge_over_Field2":float(np.quantile(e[m]/f,.9)),
                     "median_regular_equivalent_edge_mm":
                         float(np.median(eq[m])*1000) if eq is not None else "",
                     "median_regular_equivalent_over_Field2":
                         float(np.median(eq[m]/f)) if eq is not None else ""})
    require(any(r["element"]=="pore_Tri6" for r in rows),"pore source samples")
    return rows


def fit_weighted(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    require(X.shape==(len(y),3) and len(w)==len(y),"regression shapes")
    xx=X.T@(w[:,None]*X)
    yy=X.T@(w*y)
    return np.linalg.solve(xx+RIDGE*np.eye(3),yy)


def regression(data: dict) -> tuple[dict,np.ndarray]:
    tet=data["tet_centres"]
    tri=data["tri_centres"]
    # Different geometrical proxies are NOT equal to Gmsh h: estimate a
    # separate response factor for each kind from the existing M1 near-wall,
    # off-polar kappa=0 reference region. This enforces no spatial uniformity;
    # it calibrates observation operators, not the actual mesh.
    tet_off=((data["tet_d_m"]>=0)&(data["tet_d_m"]<1e-4)&
             (abs(data["tet_mu"])<=.6))
    tri_off=abs(data["tri_mu"])<=.6
    require(tet_off.sum()>50 and tri_off.sum()>50,"reference sample sizes")
    c_edge=float(np.median(data["tet_edge_m"][tet_off]/field2(data["tet_d_m"][tet_off])))
    c_equiv=float(np.median(data["tet_regular_eq_m"][tet_off]/field2(data["tet_d_m"][tet_off])))
    c_surface=float(np.median(data["tri_edge_m"][tri_off]/field2(data["tri_d_m"][tri_off])))
    for c in (c_edge,c_equiv,c_surface):
        require(.5<c<1.5,"reference proxy factor")
    points=np.concatenate([tet,tet,tri])
    edges=np.concatenate([data["tet_edge_m"],data["tet_regular_eq_m"],
                           data["tri_edge_m"]])
    scale=np.concatenate([np.full(len(tet),c_edge),np.full(len(tet),c_equiv),
                          np.full(len(tri),c_surface)])
    d=np.concatenate([data["tet_d_m"],data["tet_d_m"],data["tri_d_m"]])
    phi=np.concatenate([data["tet_phi"],data["tet_phi"],data["tri_phi"]])
    b=angular_basis(points)
    mask=(np.linalg.norm(b,axis=1)>0.04)
    n_tet=len(tet)
    weights=np.concatenate([np.full(n_tet,.5),np.full(n_tet,.5),
                             np.full(len(tri),.5)])[mask]
    X=b[mask];y=np.log(edges[mask]/(scale[mask]*field2(d[mask])));f=phi[mask]
    coeff=fit_weighted(X,y,weights)
    fitted=X@coeff
    rms=lambda e,w:float(np.sqrt(np.average(e*e,weights=w)))
    folds=[]
    for sector in range(4):
        held=(np.floor(f/(math.pi/2)).astype(int)%4)==sector
        require(held.sum()>5 and (~held).sum()>30,"too few azimuthal heldout samples")
        beta=fit_weighted(X[~held],y[~held],weights[~held])
        folds.append({"phi_quarter":sector,"heldout_samples":int(held.sum()),
                      "unfitted_log_RMSE":rms(y[held],weights[held]),
                      "fitted_log_RMSE":rms(y[held]-X[held]@beta,weights[held])})
    # Pure source-only global bound: rescale coefficients without hard clipping,
    # so the final field remains C1 at all coefficient transitions.
    grid_d=np.linspace(0,.0005,37)
    grid_mu=np.linspace(-1,1,181)
    sample=np.asarray([CENTRE+(.001+di)*np.array([
        math.sqrt(max(0,1-mu*mu)),0.,mu]) for di in grid_d for mu in grid_mu])
    bb=angular_basis(sample)
    magnitude=float(np.max(np.abs(bb@coeff)))
    scale=min(1.,MAX_LOG_OFFSET/magnitude) if magnitude else 1.
    safe=coeff*scale
    require(float(np.max(np.abs(bb@safe))) <= MAX_LOG_OFFSET+1e-12,"bounded C1 field")
    return {"objective":"ridge jointly debiased log-proxies against observed off-polar kappa0 reference",
            "data_included":"Tet10 centre edge median, curved volume regular-tetra edge and pore Tri6 projected-centroid edge median",
            "reference_kappa0_off_nearwall_count_Tet10":int(tet_off.sum()),
            "reference_kappa0_off_pore_Tri6":int(tri_off.sum()),
            "reference_proxy_ratios_over_Field2_Tet_corner_edge_regular_equivalent_pore_edge":
                 [c_edge,c_equiv,c_surface],
            "tet_samples":int(np.count_nonzero(mask[:n_tet])),
            "tet_equivalent_samples":int(np.count_nonzero(mask[n_tet:2*n_tet])),
            "pore_samples":int(np.count_nonzero(mask[2*n_tet:])),
            "source_observation_log_RMSE":rms(y,weights),
            "fitted_observation_log_RMSE":rms(y-fitted,weights),
            "bounded_observation_log_RMSE":rms(y-X@safe,weights),
            "leave_one_phi_quarter_out_CV":folds,
            "coefficients_log_raw_N_S_Ncore":coeff.tolist(),
            "coefficients_log_bounded_N_S_Ncore":safe.tolist(),
            "maximum_abs_beta_raw":magnitude,
            "coefficient_scale_to_bound":float(scale),
            "maximum_abs_beta_bounded":float(np.max(np.abs(bb@safe))),
            "bound_abs_beta":MAX_LOG_OFFSET,
            "note":"A fit to realized edge proxies is NOT an inverse Gmsh generator; CV may reject use"}, safe


def audit_field(data: dict, safe_coeff: np.ndarray) -> dict:
    phi=np.linspace(0,2*math.pi,32,endpoint=False)
    d=np.concatenate([np.linspace(0,5e-4,21),np.linspace(1.0e-3,2e-3,51),
                      np.linspace(17e-3,19e-3,51)])
    mu=np.linspace(-1,1,81)
    points=np.asarray([CENTRE+(1e-3+di)*np.array([
        math.sqrt(max(0.,1.-u*u))*math.cos(ph),
        math.sqrt(max(0.,1.-u*u))*math.sin(ph),u])
        for di in d for u in mu for ph in phi],dtype=float)
    dd, mm, _pp=coordinates(points)
    source=field2(dd); hs=smooth_field2(dd)
    beta=angular_basis(points)@safe_coeff
    hcal=hs*np.exp(beta)
    require(np.all(hcal>0) and np.all(np.isfinite(hcal)),"field positivity")
    mask0=kappa(points)==0
    priority=kappa(points)>1-1e-12
    require(np.max(np.abs(beta[mask0]))<1e-14,"kappa0 exact correction zero")
    source_rel=np.abs(hs/source-1)
    # Exact smoothness proof of quadratic joins: slopes from the left/right
    # must agree, independent of the numerical grid sampling above.
    slope=(FAR-NEAR)/(DIST_MAX-DIST_MIN)
    eps=CORNER_ROUND_RADIUS
    for u,expected in ((DIST_MIN-eps,0.),(DIST_MIN+eps,slope),
                       (DIST_MAX-eps,slope),(DIST_MAX+eps,0.)):
        h=1e-10
        dl=(smooth_field2(np.asarray([u]))-smooth_field2(np.asarray([u-h])))[0]/h
        dr=(smooth_field2(np.asarray([u+h]))-smooth_field2(np.asarray([u])))[0]/h
        require(abs(dl-expected)<1e-4 and abs(dr-expected)<1e-4,
                "piecewise quadratic C1 join derivative")
    # Nominal target contraction relative to *calibrated reference*, rather
    # than claiming any realized M2/Tet10 volume acceptance.
    alpha=.20
    htrial=hcal*np.cbrt(1-alpha*kappa(points))
    rel_ref=(htrial/hcal)**3
    rel_original=(htrial/source)**3
    require(abs(float(np.max(rel_ref[priority]))-.8)<1e-12 and
            abs(float(np.min(rel_ref[priority]))-.8)<1e-12,
            "nominal calibrated-reference kappa1 volume target")
    return {"C1_corner_transition":"analytic quadratic Hermite, numeric one-sided derivative PASS",
            "field2_smoothing_corner_radius_m":eps,
            "max_abs_source_Field2_perturbation_whole_grid":float(source_rel.max()),
            "max_abs_source_Field2_perturbation_kappa0_grid":float(source_rel[mask0].max()),
            "kappa0_exact_calibration_factor":1.,
            "kappa0_median_m2_trial_over_original_Field2_h":
                 float(np.median((htrial/source)[mask0])),
            "kappa0_max_abs_m2_trial_over_Field2_h_minus1":
                 float(np.max(abs(htrial[mask0]/source[mask0]-1))),
            "at_full_kappa1_nominal_M2_over_calibrated_M1_volume":
                 [float(rel_ref[priority].min()),float(rel_ref[priority].max())],
            "at_full_kappa1_nominal_M2_over_original_Field2_size_cubed":
                 [float(rel_original[priority].min()),float(rel_original[priority].max())],
            "max_beta_grid":float(np.max(beta)),"min_beta_grid":float(np.min(beta)),
            "min_hcal_m":float(np.min(hcal)),"max_hcal_m":float(np.max(hcal)),
            "not_native_gmsh_and_not_realized_volume":True}


def original_neighbour_field_gradation(mesh: dict, data: dict,
                                       coeff: np.ndarray) -> dict:
    """Compare prescribed scalar h at ORIGINAL M1 centroids sharing a face.

    This does not predict neighbour ratios after remeshing a new 3D M2.
    """
    face_map=defaultdict(list)
    for i,verts in enumerate(mesh["tet10"][:,:4]):
        for loc in ((0,1,2),(0,1,3),(0,2,3),(1,2,3)):
            face_map[tuple(sorted(int(verts[j]) for j in loc))].append(i)
    require(all(len(v) in (1,2) for v in face_map.values()),"corner-face manifold")
    edges=np.asarray([v for v in face_map.values() if len(v)==2],dtype=int)
    x=data["tet_centres"];d=data["tet_d_m"];mu=data["tet_mu"]
    f=field2(d)
    cal=smooth_field2(d)*np.exp(angular_basis(x)@coeff)
    trial=cal*np.cbrt(1.-.20*kappa(x))
    near=((np.maximum(d[edges[:,0]],d[edges[:,1]])<.0005)&
          (np.minimum(abs(mu[edges[:,0]]),abs(mu[edges[:,1]]))>=.6))
    require(near.sum()>100,"near-polar face neighbour count")
    result={"neighbour_count_near_polar":int(near.sum())}
    for name,h in (("M1_original_Field2",f),("M1_C1_empirical_bounded",cal),
                   ("M2_nominal_C1_trial",trial)):
        ratio=np.exp(abs(np.log(h[edges[:,0]]/h[edges[:,1]])))
        q=ratio[near]
        result[name]={"median":float(np.median(q)),
                      "p95":float(np.quantile(q,.95)),
                      "p99":float(np.quantile(q,.99)),
                      "maximum":float(np.max(q))}
    result["warning"]="These are smooth *prescribed field samples* on old M1, not actual new M2 Tet10 gradation"
    return result


def field_selftest() -> None:
    x=np.linspace(0,1,101)
    require(abs(S(np.asarray([0.]))[0])<1e-15 and
            abs(S(np.asarray([1.]))[0]-1)<1e-15 and
            np.all(np.diff(S(x))>=0),"smoothstep")
    mm=np.asarray([CENTRE+np.array([0,0,.00105]),
                   CENTRE+np.array([.00105,0,0]),
                   CENTRE+np.array([0,0,-.00105])])
    B=angular_basis(mm)
    require(abs(B[0,0]-1)<1e-14 and abs(B[0,2]-1)<1e-14 and
            abs(B[1]).max()<1e-14 and abs(B[2,1]-1)<1e-14,
            "polar/off exact anchors")
    d=np.asarray([0.,DIST_MIN-CORNER_ROUND_RADIUS, DIST_MIN+CORNER_ROUND_RADIUS,
                  DIST_MAX-CORNER_ROUND_RADIUS,DIST_MAX+CORNER_ROUND_RADIUS,.04])
    v=smooth_field2(d)
    require(np.all(v>=NEAR-1e-13) and np.all(v<=FAR+1e-13) and
            abs(v[0]-NEAR)<1e-14 and abs(v[-1]-FAR)<1e-14,"C1 threshold range")


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m1",type=Path)
    ap.add_argument("--evidence",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args()
    field_selftest()
    N,D,W=rule27(); selftest(N,D,W)
    if args.selftest:
        print("P10ES_C1_GEOMETRY_SYNTHETIC_OK SHA_PIN_ACTIVE FEM=0 Gmsh=0")
        return 0
    require(args.m1 is not None and args.out is not None and args.evidence is not None,
            "--m1 --evidence --out required")
    source=source_provenance(args.evidence)
    require(args.m1.name=="P10DG_M1_CANDIDATE.msh" and digest(args.m1)==M1_SHA,
            "must use exact original M1 SHA")
    mesh=parse_msh2(args.m1,M1_SHA)
    require(len(mesh["tet10"])==9736 and len(mesh["pore_tri6"])==178,
            "original M1 inventory")
    data=proxy_data(mesh,N,D,W)
    rows=sampling_report(data)
    fit,coeff=regression(data)
    field=audit_field(data,coeff)
    neighbour=original_neighbour_field_gradation(mesh,data,coeff)
    out={"protocol":"P10ES_M1_RAW_MEASURED_JOINT_SURFACE_VOLUME_C1_FIELD_CALIBRATION",
         "status":"SOURCE_ONLY_EMPIRICAL_CALIBRATION_NO_M2_RUNNER_NO_GMSH_NO_FEM",
         "source_M1_SHA256":M1_SHA,"original_source_provenance":source,
         "pore_wall_radius_m":.001,
         "original_M1_Field2":{"near_m":NEAR,"far_m":FAR,
                               "dist_min_m":DIST_MIN,"dist_max_m":DIST_MAX,
                               "C1":False},
         "original_M1_curved_tet10_volume_total_m3":float(data["tet_curved_vol_m3"].sum()),
         "surface_and_volume_regression":fit,"C1_field_source_only_audit":field,
         "source_field_neighbour_gradation":neighbour,
         "field_formula":{
             "mu":"(z-0.03)/sqrt(x*x+y*y+(z-0.03)^2)",
             "smoothstep":"S(t)=u^2*(3-2*u), u=clip(t,0,1)",
             "angular_weight_north":"wN=S((mu-0.6)/0.2)",
             "angular_weight_south":"wS=S((-mu-0.6)/0.2)",
             "north_core":"wC=S((mu-0.8)/0.1)",
             "beta":"kappa*(coefN*wN+coefS*wS+coefCore*wN*wC)",
             "h_M1_cal":"C1_smooth_original_Field2*exp(beta)",
             "h_M2_trial":"h_M1_cal*(1-0.20*kappa)^(1/3)",
             "numeric_source_coefficients_NOT_NATIVE_GEO":coeff.tolist()},
         "limitations":[
             "No original M1 regeneration with h_M1_cal; an empirical fit is NOT Gmsh inverse",
             "M1 surface edge median and regular-tetra volume-equivalent edge are different proxies",
             "Original Gmsh Threshold2 field is C0 with derivative kinks at 1.5/18mm; C1 smoothing perturbs it locally",
             "A target ratio relative to reconstructed h_M1_cal is NOT a measured M2/M1 Tet10 volume ratio",
             "One native Gmsh -3 could still rebuild all polar Tri6 and violate D025",
             "Only actual same-region 729QP and independent neighbor/geometry QA may authorize FEM",
             "No per-phi uniformity or global Tet10-count cap is imposed"]}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"P10ES_M1_JOINT_CALIBRATION_AND_C1_FIELD_AUDIT.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (args.out/"P10ES_M1_SURFACE_VOLUME_EDGE_PROXIES.csv").open(
            "w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader();writer.writerows(rows)
    print("P10ES_M1_JOINT_C1_SOURCE_CALIBRATION_OK",
          f"M1={len(mesh['tet10'])}",f"fit_beta_max={fit['maximum_abs_beta_raw']:.5f}",
          f"bound={MAX_LOG_OFFSET:.3f}","FEM=0 Gmsh=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
