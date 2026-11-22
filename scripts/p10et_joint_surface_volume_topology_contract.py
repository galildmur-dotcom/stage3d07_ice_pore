#!/usr/bin/env python3
"""P10ET: pinned original Tri6 + prior fixed 3D Tet10 QP, joint gate design.

No new mesh, Gmsh parse, FEM or Windows one-shot marker. Surface 5..35QP
are newly integrated from exact private original raw MSH2; volumetric
9^3-QP caps are read from the independently verified P10ER derived CSV.
The draft size-field parameters are a *source-only hypothesis* and are
NOT a Gmsh .geo or evidence of realized adaptivity.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from p10ed_verify_original_m1_m2_raw_spatial import CENTRE, M1_SHA, digest, kappa, parse_msh2
from p10ee_audit_pore_surface_sizing_source_only import selftest as tri_selftest, surface_stats
from p10er_three_raw_msh_local_topology_forensics import SHA as RAW_SHA, coordinates
from p10es_m1_measured_smooth_sizing_calibration import (
    S, angular_basis, field2, smooth_field2, field_selftest,
)

P10ER_CSV_SHA = "b37c530d69d298aa57d17a15ca9e4546eac0f7f3ee433e768098e0e3d986bd92"
P10ES_JSON_SHA = "3d8bad11c769399061409c735ccc1e9f4fa1085573554d93ca38cab7dadb5054"
SURFACE_ORDERS = (5, 9, 15, 25, 35)
VOLUME_BAND = (.75, .85)
MAX_LOG_BETA=.018
LAYER_TAPER_M=.0004  # order of measured M1 pore corner edge length
ALPHA_N=.23
LAMBDA_N=.012
LAMBDA_N_CORE=.004


def ensure(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("P10ET_STOP: " + message)


def read_verified_previous(csv_path: Path, json_path: Path):
    ensure(digest(csv_path)==P10ER_CSV_SHA and digest(json_path)==P10ES_JSON_SHA,
           "exact independently verified P10ER/P10ES derived source SHA")
    with csv_path.open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream))
    raw=json.loads(json_path.read_text(encoding="utf-8"))
    ensure(raw["source_M1_SHA256"]==M1_SHA and len(rows)==44,
           "prior 3D fixed-domain/M1 identity")
    caps={}
    for hemi in ("north", "south"):
        a=[r for r in rows if r["region"]==hemi+"_polar_0_100um" and
           int(r["order"])==9]
        ensure(len(a)==1,"matched 9^3 physical polar cap")
        r=a[0]
        caps[hemi]={"m1_N_eff":float(r["M1_fractional_tets"]),
                    "P10EK_N_eff":float(r["P10EK_fractional_tets"]),
                    "P10EN_N_eff":float(r["P10EN_fractional_tets"]),
                    "P10EK_volume_Q":float(r["P10EK_over_M1"]),
                    "P10EN_volume_Q":float(r["P10EN_over_M1"]),
                    "m1_physical_cap_volume_m3":float(r["M1_region_vol_m3"]),
                    "P10EK_cap_volume_over_M1":
                      float(r["P10EK_region_vol_m3"])/float(r["M1_region_vol_m3"]),
                    "P10EN_cap_volume_over_M1":
                      float(r["P10EN_region_vol_m3"])/float(r["M1_region_vol_m3"]),
                    "future_nominal_N_eff_bounds_for_equal_cap_volume":
                      [float(r["M1_fractional_tets"])/VOLUME_BAND[1],
                       float(r["M1_fractional_tets"])/VOLUME_BAND[0]]}
    prior_coeff=np.asarray(raw["surface_and_volume_regression"]
                         ["coefficients_log_bounded_N_S_Ncore"],dtype=float)
    ensure(prior_coeff.shape==(3,) and abs(prior_coeff[0]-.018)<1e-12 and
           np.linalg.norm(prior_coeff)<.1,"pinned safe source coefficient")
    return caps,prior_coeff


def surface(mesh: dict, orders: tuple[int,...]) -> dict:
    result={}
    for order in orders:
        s=surface_stats(mesh,order)
        # A curved quadratic Tri6 sphere is an approximation to CAD sphere;
        # its area has a stable O(1e-4) geometry bias, distinct from QP error.
        ensure(abs(s["curved_full_vs_analytic_rel_error"])<1e-3 and
               s["tri6"] in (178,194,192),"curved sphere surface geometry")
        result[str(order)]={
            "full_pore_area_rel_error":s["curved_full_vs_analytic_rel_error"],
            "north":s["zones"]["north"],
            "south":s["zones"]["south"],
            "both_poles":s["zones"]["both_poles"],
        }
    return result


def pairs_surface(surfaces: dict) -> tuple[list[dict],dict]:
    rows=[]
    for order in SURFACE_ORDERS:
        key=str(order)
        for hemi in ("north","south"):
            base=surfaces["M1"][key][hemi]
            for label in ("P10EK_M2","P10EN_M2"):
                b=surfaces[label][key][hemi]
                q=b["effective_curved_Tri6_area_m2"]/base["effective_curved_Tri6_area_m2"]
                rows.append({"order":order,"hemisphere":hemi,"candidate":label,
                             "surface_effective_area_Q":q,
                             "M1_surface_N_eff":base["fractional_surface_tri6"],
                             "M2_surface_N_eff":b["fractional_surface_tri6"],
                             "M1_surface_cap_area_m2":base["curved_qp_area_m2"],
                             "M2_surface_cap_area_m2":b["curved_qp_area_m2"],
                             "physical_cap_area_ratio":b["curved_qp_area_m2"]/base["curved_qp_area_m2"]})
    order25={(x["hemisphere"],x["candidate"]):x for x in rows if x["order"]==25}
    order35={(x["hemisphere"],x["candidate"]):x for x in rows if x["order"]==35}
    d={key:abs(order35[key]["surface_effective_area_Q"]-
               order25[key]["surface_effective_area_Q"]) for key in order35}
    ensure(max(d.values())<.001,"surface cap 25x25->35x35 indicator instability")
    return rows,{"max_surface_Q_change_25_to_35":max(d.values()),
                 "per_cap_changes":{str(k):v for k,v in d.items()}}


def smooth_draft_params(coeff: np.ndarray) -> dict:
    # At south kappa=1, choose alpha to offset bounded M1 beta and keep the
    # same nominal h^3 ratio 0.80 against original F2 as P10EK south.
    alpha_s=1.-.80*math.exp(-3*float(coeff[1]))
    ensure(.15<alpha_s<.25 and .15<ALPHA_N<.25,"nominal alpha budgets")
    return {"alpha_base":.20,"alpha_north":ALPHA_N,
            "alpha_south_compensated":alpha_s,
            "north_wall_taper_lambda":LAMBDA_N,
            "north_axis_extra_lambda":LAMBDA_N_CORE,
            "wall_normal_taper_m":LAYER_TAPER_M,
            "M1_bounded_coefficients":coeff.tolist(),
            "field_is_executable_geo":False,
            "formula":"h_trial=h_Field2_C1*exp(beta_M1)*(1-alpha(mu)*kappa)^(1/3)*exp(kappa*wN*(lambdaN+lambdaCore*wCore)*(1-S(d/layer_width)))",
            "limitation":"This candidate is an algebraic nominal contract, not observed Gmsh response"}


def calc_draft(x: np.ndarray, coeff: np.ndarray, params: dict) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    d,mu,_phi=coordinates(x)
    kp=kappa(x)
    wn=S((mu-.6)/.2)
    ws=S((-mu-.6)/.2)
    wc=S((mu-.8)/.1)
    alpha=.20+(params["alpha_north"]-.20)*wn+(
        params["alpha_south_compensated"]-.20)*ws
    lam=kp*wn*(params["north_wall_taper_lambda"]+
               params["north_axis_extra_lambda"]*wc)*(
               1-S(d/params["wall_normal_taper_m"]))
    href=smooth_field2(d)*np.exp(angular_basis(x)@coeff)
    trial=href*np.cbrt(1-alpha*kp)*np.exp(lam)
    ensure(np.all(trial>0) and np.all(np.isfinite(trial)),"positive draft h")
    return trial,href,lam


def c1_seam_audit(coeff: np.ndarray, params: dict) -> dict:
    """Numerical C1 source-field seam check, not a meshing smoothness test."""
    def evaluate(radial_d: float, mu: float) -> float:
        direction=np.array([math.sqrt(max(0.,1-mu*mu)),0.,mu])
        point=CENTRE+(.001+radial_d)*direction
        return float(calc_draft(point[None,:],coeff,params)[0][0])
    # Compare left and right first derivatives at every analytic join.
    radial_joins=(0.,.0001,.0004,.0005,.00145,.00155,.01795,.01805)
    angular_joins=(-.8,-.6,.6,.8,.9)
    eps_d=1e-9
    eps_mu=1e-6
    rd={}
    for seam in radial_joins:
        left=(evaluate(seam,.85)-evaluate(seam-eps_d,.85))/eps_d
        right=(evaluate(seam+eps_d,.85)-evaluate(seam,.85))/eps_d
        rd[str(seam)]={"left":left,"right":right,"difference":abs(left-right)}
    ad={}
    for seam in angular_joins:
        left=(evaluate(.00005,seam)-evaluate(.00005,seam-eps_mu))/eps_mu
        right=(evaluate(.00005,seam+eps_mu)-evaluate(.00005,seam))/eps_mu
        ad[str(seam)]={"left":left,"right":right,"difference":abs(left-right)}
    max_rd=max(x["difference"] for x in rd.values())
    max_ad=max(x["difference"] for x in ad.values())
    ensure(max_rd<.001 and max_ad<2e-7,"C1 seam derivative numeric sanity")
    return {"radial_derivative_jump_max":max_rd,
            "angular_derivative_jump_max_m":max_ad,
            "radial_epsilon_m":eps_d,"angular_mu_epsilon":eps_mu,
            "radial_seams":rd,"angular_seams":ad,
            "scope":"nominal source-only finite-difference seam sanity; no guarantee on realized Tet10"}


def virtual_field_contract(coeff: np.ndarray) -> dict:
    params=smooth_draft_params(coeff)
    ds=np.concatenate([np.linspace(0,1e-4,17),np.linspace(1e-4,.0005,17),
                       np.asarray([.0015,.018])])
    mus=np.linspace(-1,1,121)
    phis=np.linspace(0,2*math.pi,12,endpoint=False)
    points=np.asarray([CENTRE+(.001+d)*np.array([
        math.sqrt(max(0.,1-m*m))*math.cos(p),
        math.sqrt(max(0.,1-m*m))*math.sin(p),m])
        for d in ds for m in mus for p in phis])
    h,href,_=calc_draft(points,coeff,params)
    d,mu,_=coordinates(points)
    kp=kappa(points)
    full=(kp>1.-1e-12)
    k0=kp==0
    qsource=(h/field2(d))**3
    qcal=(h/href)**3
    ensure(k0.any() and full.any() and np.all(h>0),"source field samples")
    ensure(np.max(abs(qsource[full]-np.clip(qsource[full],*VOLUME_BAND)))<1e-12,
           "nominal source Field2 volume budget violated at full kappa1")
    ensure(np.max(abs(qcal[full]-np.clip(qcal[full],*VOLUME_BAND)))<1e-12,
           "nominal calibrated M1 volume budget violated at full kappa1")
    # Preserve kappa0 except proven tiny legacy Threshold corner regularization.
    k0_dev=np.max(abs(h[k0]/field2(d[k0])-1))
    ensure(k0_dev<.012,"kappa0 source size preservation budget")
    # Sanity original-vertex shape-gradation samples on M1 shared faces.
    f={}
    for hemi,mask in (("north",full&(mu>=.8)),("north_axis",full&(mu>=.9)),
                      ("south",full&(mu<=-.8))):
        ensure(mask.any(),"empty full priority field samples")
        f[hemi]={"trial_cube_relative_original_Field2":
                  [float(np.min(qsource[mask])),float(np.max(qsource[mask]))],
                 "trial_cube_relative_M1_calibrated":
                  [float(np.min(qcal[mask])),float(np.max(qcal[mask]))]}
    params["all_grid_full_kappa_source_volume_Q"]=[float(np.min(qsource[full])),
                                                    float(np.max(qsource[full]))]
    params["all_grid_full_kappa_calibrated_volume_Q"]=[float(np.min(qcal[full])),
                                                        float(np.max(qcal[full]))]
    params["kappa0_max_h_over_original_Field2_minus1"]=float(k0_dev)
    params["priority_hemispheres"]=f
    params["C1_seam_numeric_audit"]=c1_seam_audit(coeff,params)
    return params


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m1",type=Path)
    parser.add_argument("--p10ek",type=Path)
    parser.add_argument("--p10en",type=Path)
    parser.add_argument("--p10er-csv",type=Path)
    parser.add_argument("--p10es-json",type=Path)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--selftest",action="store_true")
    args=parser.parse_args()
    field_selftest()
    tri_selftest()
    if args.selftest:
        print("P10ET_SURFACE_VOLUME_C1_SYNTHETIC_OK no_Gmsh=1 FEM=0")
        return 0
    ensure(all(v is not None for v in (args.m1,args.p10ek,args.p10en,
                                      args.p10er_csv,args.p10es_json,args.out)),
           "all exact private MSH and prior derived sources required")
    inputs={"M1":args.m1,"P10EK_M2":args.p10ek,"P10EN_M2":args.p10en}
    for name,path in inputs.items():
        ensure(path.is_file() and digest(path)==RAW_SHA[name],"raw SHA pin "+name)
    volumes,coeff=read_verified_previous(args.p10er_csv,args.p10es_json)
    meshes={name:parse_msh2(path,RAW_SHA[name]) for name,path in inputs.items()}
    sizes={"M1":(9736,178),"P10EK_M2":(9988,194),"P10EN_M2":(10020,192)}
    for name,mesh in meshes.items():
        ensure((len(mesh["tet10"]),len(mesh["pore_tri6"]))==sizes[name],
               "original Tet10/Tri6 inventory "+name)
    surfaces={name:surface(m,SURFACE_ORDERS) for name,m in meshes.items()}
    rows,stability=pairs_surface(surfaces)
    joined=[]
    for hemi in ("north","south"):
        z=volumes[hemi]
        for name in ("P10EK_M2","P10EN_M2"):
            area=next(r for r in rows if r["order"]==35 and
                      r["hemisphere"]==hemi and r["candidate"]==name)
            qv=z["P10EK_volume_Q"] if name=="P10EK_M2" else z["P10EN_volume_Q"]
            qa=area["surface_effective_area_Q"]
            joined.append({"hemisphere":hemi,"candidate":name,
                           "Tet10_volume_Q_729QP":qv,
                           "Tri6_surface_area_Q_35x35QP":qa,
                           "geometric_scale_coupling_ratio_Qv_over_Qa_pow_3over2":qv/qa**1.5,
                           "D025_volume_gate": "PASS" if .75<=qv<=.85 else "STOP",
                           "surface_is_an_independent_D025_gate":False})
    source_only=virtual_field_contract(coeff)
    output={"protocol":"P10ET_ORIGINAL_SURFACE_VOLUME_QP_TOPOLOGY_CONTRACT",
       "status":"JOINT_SOURCE_ONLY_PRE_REGISTRATION_NO_GMSH_NO_FEM",
       "private_raw_mesh_sha256":RAW_SHA,
       "pinned_previous_source_sha256":{"P10ER_3D_caps_csv":P10ER_CSV_SHA,
                                        "P10ES_bounded_field_json":P10ES_JSON_SHA},
       "no_new_native_gmsh_no_FEM_no_markers":True,
       "volume_fixed_physical_caps_order":729,
       "surface_QP_orders_per_axis":list(SURFACE_ORDERS),
       "surface_quad_stability":stability,
       "M1_3D_volume_Neff_window":volumes,
       "surface_full_meshes":surfaces,
       "joint_observed_surface_volume":joined,
       "surface_area_ratio_if_isotropic_volume_0p75_to_0p85_ONLY_DIAGNOSTIC":
           [VOLUME_BAND[0]**(2/3),VOLUME_BAND[1]**(2/3)],
       "source_only_c1_wall_normal_field":source_only,
       "pre_registered_future_mesh_review":{
           "hard_D025_gate":"0.75 <= effective Tet10 volume M2/M1 <=0.85 separately north and south, 729QP stable vs 343QP",
           "geometry":"all curved Tet10 27QP Jacobians positive, exact CAD groups, sphere pore and volume, new raw SHA",
           "surface":"Tri6 area in fixed north/south caps with 15,25,35 QP and pore sphere Jacobian; DIAGNOSTIC, not hard volume gate",
           "kappa0":"preserve realized size as nearly as possible; report local Q, no arbitrary new numerical hard band",
           "neighbour_smoothness":"audit M1 and M2 adjacent Tet10 volume-root ratios including p50,p95,p99,max; no new unapproved hard threshold",
           "topology":"report pore Tri6 counts, vertex/face churn and polar N_eff, not require phi uniformity",
           "resources":"new isolated guarded Gmsh -3 with single fresh one-shot marker only after investigator authorization",
           "physics":"FEM forbidden without independent geometry+D025 GO; direct/adjoint on same accepted M2 only"},
       "caution":["Surface area Q can be below isotropic interval even when 3D volume Q is accepted (P10EK south)",
           "An algebraic C1 field cannot guarantee a realized surface triangulation or Tet10 neighbour smoothness",
           "C1 proposed source is not executable Gmsh .geo and no new one-shot permission was requested",
           "P10ER cap boundary QP indicator numerical convergence remains necessary"]}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"P10ET_SURFACE_VOLUME_TOPOLOGY_CONTRACT.json").write_text(
        json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    with (args.out/"P10ET_ORIGINAL_SURFACE_VOLUME_CAP_RATIOS.csv").open(
            "w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(joined[0]),lineterminator="\n")
        writer.writeheader();writer.writerows(joined)
    print("P10ET_EXACT_THREE_MESH_SURFACE_VOLUME_CONTRACT_OK",
          "caps",len(joined),"35x35_QP","native_Gmsh=0","FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
