#!/usr/bin/env python3
"""P10ER: read-only forensics of original M1, P10EK M2 and P10EN M2.

All input raw MSH2 are SHA-pinned and private. Only small derived JSON/CSV
are written. Curved full Tet10 volumes use audited 27QP P10ED integration;
subregion intersections use independent higher-order physical QP indicators.
The result is a *diagnostic*, not a D-025 pass or a one-shot Gmsh permit.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from p10ed_verify_original_m1_m2_raw_spatial import (
    CENTRE, EDGES, M1_SHA, audit_mesh, curved, digest, duffy_rule,
    ensure, parse_msh2, rule27, selftest,
)

SHA = {
    "M1": M1_SHA,
    "P10EK_M2": "f7183efdaff22b0ed7c281104ee00e18499c0d53f087100e08959a7d4a43250b",
    "P10EN_M2": "04a5a16111ebfa1219cd628355b83eb2b5e7bf0d3238c08a3fff118377bfc8f0",
}
NEAR_SIZE = 0.00042855883184652975  # original M1 Field[2].SizeMin
FACES = ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3))


def summary(x: np.ndarray) -> dict:
    ensure(bool(x.size) and np.all(np.isfinite(x)), "empty or invalid diagnostic sample")
    return {"count": int(x.size), "median": float(np.median(x)),
            "p10": float(np.quantile(x, .1)), "p90": float(np.quantile(x, .9)),
            "p95": float(np.quantile(x, .95)), "p99": float(np.quantile(x, .99)),
            "maximum": float(np.max(x))}


def coordinates(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    r = xyz - CENTRE
    rho = np.linalg.norm(r, axis=-1)
    ensure(np.all(rho > 0), "sphere centre in mesh")
    return rho - .001, r[..., 2] / rho, np.mod(np.arctan2(r[..., 1], r[..., 0]), 2*math.pi)


def zones() -> list[dict]:
    out = []
    for hemi in ("north", "south"):
        for name, da, db, ma, mb in (
            ("polar_0_100um", 0, 100, .8, 1),
            ("polar_0_50um", 0, 50, .8, 1),
            ("polar_50_100um", 50, 100, .8, 1),
            ("polar_mu_0p8_0p9", 0, 100, .8, .9),
            ("polar_mu_0p9_1", 0, 100, .9, 1),
            ("taper_0_100um", 0, 100, .6, .8),
            ("off_0_100um", 0, 100, 0, .6),
        ):
            out.append({"name": hemi+"_"+name, "hemisphere": hemi,
                        "d_m": [da*1e-6, db*1e-6], "abs_mu": [ma, mb],
                        "phi_rad": [0, 2*math.pi]})
        for sector in range(4):
            out.append({"name": hemi+f"_polar_phi_{sector}", "hemisphere": hemi,
                        "d_m": [0, 1e-4], "abs_mu": [.8, 1],
                        "phi_rad": [sector*math.pi/2, (sector+1)*math.pi/2]})
    return out


def region_sample(mesh: dict, full_vol: np.ndarray, order: int, defs: list[dict]) -> list[dict]:
    basis, deriv, quad_w = duffy_rule(order)
    zone_v = np.zeros(len(defs))
    zone_n = np.zeros(len(defs))
    hit = np.zeros(len(defs), dtype=np.int64)
    for start in range(0, len(full_vol), 192):
        p = mesh["nodes"][mesh["tet10"][start:start+192]]
        _, jac, xyz = curved(p, basis, deriv, quad_w)
        ensure(np.all(jac > 0), f"nonpositive curved Jacobian at order {order}")
        weights = jac * quad_w[None, :]
        d, mu, phi = coordinates(xyz)
        mu_abs = np.abs(mu)
        for i, reg in enumerate(defs):
            lo, hi = reg["d_m"]
            mlo, mhi = reg["abs_mu"]
            plo, phi_hi = reg["phi_rad"]
            mask = ((d >= lo) & (d < hi) & (mu_abs >= mlo) &
                    (mu_abs < mhi) & (phi >= plo) & (phi < phi_hi) &
                    ((mu >= 0) if reg["hemisphere"] == "north" else (mu < 0)))
            w = weights[mask]
            zone_v[i] += float(np.sum(w))
            zone_n[i] += float(np.sum((weights / full_vol[start:start+len(p), None])[mask]))
            hit[i] += int(np.count_nonzero(mask))
    ensure(np.all(zone_n > 0) and np.all(hit > 0), f"empty {order}QP spatial diagnostic bin")
    return [{"region": reg["name"], "order_per_axis": order,
             "region_volume_m3": float(zone_v[i]), "fractional_tet_count": float(zone_n[i]),
             "effective_cell_volume_m3": float(zone_v[i]/zone_n[i]),
             "qp_hits": int(hit[i])} for i, reg in enumerate(defs)]


def face_adjacency(mesh: dict, vol: np.ndarray, d: np.ndarray, mu: np.ndarray) -> dict:
    face_map: dict[tuple, list[int]] = defaultdict(list)
    for ei, v in enumerate(mesh["tet10"][:, :4]):
        for face in FACES:
            face_map[tuple(sorted(int(v[i]) for i in face))].append(ei)
    ensure(all(len(v) in (1, 2) for v in face_map.values()), "nonmanifold corner face")
    links = np.asarray([v for v in face_map.values() if len(v) == 2], dtype=np.int64)
    h_ratio = np.exp(np.abs(np.log(vol[links[:, 0]] / vol[links[:, 1]]))/3)
    near = ((np.maximum(d[links[:, 0]], d[links[:, 1]]) < .0005) &
            (np.minimum(np.abs(mu[links[:, 0]]), np.abs(mu[links[:, 1]])) >= .6))
    return {"internal_corner_faces": int(len(links)),
            "boundary_corner_faces": int(sum(len(v) == 1 for v in face_map.values())),
            "h_jump_ratio_all_adjacent": summary(h_ratio),
            "h_jump_ratio_near_polar_adjacent": summary(h_ratio[near]),
            "near_polar_count_h_jump_gt_1p25": int(np.count_nonzero(h_ratio[near] > 1.25)),
            "note": "cube root of curved-volume ratio of face neighbours, not imposed field C1 test"}


def topo_signature(mesh: dict) -> dict:
    # 1e-11 m bins: diagnostic only, not an exact mesh equivalence assertion.
    nodes = mesh["nodes"]
    point_key = lambda v: tuple(int(z) for z in np.rint(v/1e-11))
    vol_vertices = mesh["tet10"][:, :4]
    pore_vertices = mesh["pore_tri6"][:, :3]
    all_corners = {point_key(nodes[int(i)]) for i in np.unique(vol_vertices)}
    pore_corners = {point_key(nodes[int(i)]) for i in np.unique(pore_vertices)}
    pore_triangles = {tuple(sorted(point_key(nodes[int(i)]) for i in v)) for v in pore_vertices}
    return {"all_corner_points": all_corners, "pore_corner_points": pore_corners,
            "pore_triangles": pore_triangles}


def mesh_diagnostics(mesh: dict, label: str, N: np.ndarray, D: np.ndarray, W: np.ndarray,
                     defs: list[dict]):
    original, _, aux = audit_mesh(mesh, label, N, D, W)
    vol = aux["vol"]
    d, mu, phi = coordinates(aux["centroid"])
    caps = {}
    for name, mask in (
        ("north_polar_centroids", (d >= 0) & (d < 1e-4) & (mu >= .8)),
        ("south_polar_centroids", (d >= 0) & (d < 1e-4) & (mu <= -.8)),
        ("north_polar_0_500um", (d >= 0) & (d < 5e-4) & (mu >= .8)),
        ("south_polar_0_500um", (d >= 0) & (d < 5e-4) & (mu <= -.8)),
        ("off_0_100um", (d >= 0) & (d < 1e-4) & (np.abs(mu) <= .6)),
    ):
        caps[name] = {"centroid_tet_count": int(np.count_nonzero(mask)),
                      "cell_volume_m3": summary(vol[mask]) if mask.any() else None,
                      "h_cube_root_volume_mm": summary(np.cbrt(vol[mask])*1000) if mask.any() else None}
    tri_corner = mesh["nodes"][mesh["pore_tri6"][:, :3]]
    tri_mid = tri_corner.mean(axis=1)
    _, tri_mu, _ = coordinates(tri_mid)
    tri_edges = np.stack([np.linalg.norm(tri_corner[:, a]-tri_corner[:, b], axis=1)
                          for a,b in EDGES[:3]], axis=1)
    pore = {}
    for key, mask in (("north_mu_ge_0p8", tri_mu >= .8),
                      ("south_mu_le_m0p8", tri_mu <= -.8),
                      ("off_abs_mu_le_0p6", np.abs(tri_mu) <= .6)):
        pore[key] = {"tri6_count": int(mask.sum()),
                     "corner_edge_mm": summary(tri_edges[mask].ravel()*1000)}
    return ({"mesh": label, "original_geometry": original,
             "M1_field2_near_target_h_mm": NEAR_SIZE*1000,
             "centroid_local_geometry": caps,
             "pore_surface_tri6": pore,
             "face_smoothness_diagnostics": face_adjacency(mesh, vol, d, mu)},
            {order: region_sample(mesh, vol, order, defs) for order in (7, 9)},
            topo_signature(mesh),
            {"centroid": aux["centroid"], "vol": vol, "d": d, "mu": mu})


def test_smooth_field() -> dict:
    # Proposed functional family; alpha_N/S are deliberately not fixed here.
    def S(t):
        u = np.clip(t, 0., 1.)
        return u*u*(3-2*u)
    mu = np.linspace(-1, 1, 10001)
    north = S((mu-.6)/.2)
    south = S((-mu-.6)/.2)
    ensure(np.all(north >= 0) and np.all(south >= 0) and
           np.max(north+south) <= 1+1e-12 and
           north[-1] == 1 and south[0] == 1 and
           north[0] == 0 and south[-1] == 0,
           "smooth polar weights bounds/ends")
    # Derivative of S exactly vanishes at both joins; numerical continuity check.
    for u in (-.8, -.6, .6, .8):
        i = int(np.argmin(abs(mu-u)))
        ensure(abs(north[i+1]-north[i]) < 1e-5 and
               abs(south[i+1]-south[i]) < 1e-5, "C1 transition near join")
    return {"polar_weight_smoothstep_C1_test": "PASS",
            "alpha_values_calibrated": False,
            "field_family": "h(x)=Field2(x)*(1-kappa(x)*(alpha_N*w_N(mu)+alpha_S*w_S(mu)))**(1/3)",
            "north_weight": "w_N(mu)=S((mu-0.6)/0.2)",
            "south_weight": "w_S(mu)=S((-mu-0.6)/0.2)",
            "smoothstep": "S(t)=clip(t,0,1)^2*(3-2*clip(t,0,1))",
            "constraint": "0<=alpha_N,alpha_S<1, calibrated from raw realized data; no new mesh issued"}


def assert_partition_closure(regional: dict, defs: list[dict]) -> None:
    names = [x["name"] for x in defs]
    for name, by_order in regional.items():
        for order, rows in by_order.items():
            m = dict(zip(names, rows))
            for hemi in ("north", "south"):
                base = m[hemi+"_polar_0_100um"]
                children = (
                    [hemi+"_polar_0_50um", hemi+"_polar_50_100um"],
                    [hemi+"_polar_mu_0p8_0p9", hemi+"_polar_mu_0p9_1"],
                    [hemi+f"_polar_phi_{i}" for i in range(4)],
                )
                for members in children:
                    for k in ("region_volume_m3", "fractional_tet_count", "qp_hits"):
                        total = sum(m[q][k] for q in members)
                        ensure(abs(total/base[k]-1) < 1e-10,
                               f"QP spatial partition closure {name} order{order} {hemi} {k}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m1", type=Path)
    ap.add_argument("--p10ek", type=Path)
    ap.add_argument("--p10en", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    N, D, W = rule27()
    selftest(N, D, W)
    model = test_smooth_field()
    if args.selftest:
        print("P10ER_TET10_FIELD_SYNTHETIC_OK affine=PASS inverted=STOP C1=PASS FEM=0")
        return 0
    ensure(all(x is not None for x in (args.m1, args.p10ek, args.p10en, args.out)),
           "all three pinned raw paths and output required")
    paths = {"M1": args.m1, "P10EK_M2": args.p10ek, "P10EN_M2": args.p10en}
    ensure(len({p.resolve() for p in paths.values()}) == 3, "distinct raw meshes required")
    for name, path in paths.items():
        ensure(path.is_file() and digest(path) == SHA[name], f"SHA mismatch: {name}")
    original = {name:parse_msh2(path, SHA[name]) for name,path in paths.items()}
    ensure([len(original[z]["tet10"]) for z in paths] == [9736,9988,10020],
           "wrong audited raw Tet10 inventories")
    defs = zones()
    audits, regional, signatures, auxiliary = {}, {}, {}, {}
    for label, mesh in original.items():
        audits[label], regional[label], signatures[label], auxiliary[label] = mesh_diagnostics(
            mesh, label, N, D, W, defs)
    assert_partition_closure(regional, defs)
    contrasts = []
    for order in (7, 9):
        for i, z in enumerate(defs):
            a = regional["M1"][order][i]
            b = regional["P10EK_M2"][order][i]
            c = regional["P10EN_M2"][order][i]
            contrasts.append({"region": z["name"], "order": order,
                              "M1_v_eff_m3": a["effective_cell_volume_m3"],
                              "P10EK_over_M1": b["effective_cell_volume_m3"]/a["effective_cell_volume_m3"],
                              "P10EN_over_M1": c["effective_cell_volume_m3"]/a["effective_cell_volume_m3"],
                              "P10EN_over_P10EK": c["effective_cell_volume_m3"]/b["effective_cell_volume_m3"],
                              "M1_region_vol_m3": a["region_volume_m3"],
                              "P10EK_region_vol_m3": b["region_volume_m3"],
                              "P10EN_region_vol_m3": c["region_volume_m3"],
                              "M1_fractional_tets": a["fractional_tet_count"],
                              "P10EK_fractional_tets": b["fractional_tet_count"],
                              "P10EN_fractional_tets": c["fractional_tet_count"],
                              "min_qp_hits": min(a["qp_hits"],b["qp_hits"],c["qp_hits"])})
    q9 = {x["region"]:x for x in contrasts if x["order"] == 9}
    for region, ek, en in (("north_polar_0_100um", .7242307903, .7201707321),
                           ("south_polar_0_100um", .8031802142, .8864601881)):
        ensure(abs(q9[region]["P10EK_over_M1"]-ek) < 2e-4 and
               abs(q9[region]["P10EN_over_M1"]-en) < 2e-4,
               "independent QP priority cap contrast must reproduce P10EM/P10EP")
    transitions = {}
    old = signatures["M1"]
    for name in ("P10EK_M2", "P10EN_M2"):
        new = signatures[name]
        transitions[name] = {
            f"common_{key}": len(old[key] & new[key]) for key in old}
        transitions[name].update({
            f"M1_{key}": len(old[key]) for key in old})
        transitions[name].update({
            f"M2_{key}": len(new[key]) for key in old})
        xyz1 = auxiliary["M1"]["centroid"]
        xyz2 = auxiliary[name]["centroid"]
        near_m1 = ((auxiliary["M1"]["d"] < 5e-4) &
                   (np.abs(auxiliary["M1"]["mu"]) >= .8))
        near_m2 = ((auxiliary[name]["d"] < 5e-4) &
                   (np.abs(auxiliary[name]["mu"]) >= .8))
        if near_m1.any() and near_m2.any():
            dst, _ = cKDTree(xyz1[near_m1]).query(xyz2[near_m2])
            transitions[name]["nearest_polar_centroid_distance_mm"] = summary(dst*1000)
    output = {
        "protocol": "P10ER_THREE_EXACT_RAW_MSH2_LOCAL_VOLUME_FACE_TOPOLOGY_SOURCE_ONLY",
        "status": "SOURCE_ONLY_LOCAL_FORENSICS_NOT_D025_GO_NO_FEM",
        "original_raw_sha256_private": SHA,
        "raw_meshes_not_published": True,
        "new_native_Gmsh_attempts": 0,
        "new_forward_adjoint_FEM_attempts": 0,
        "geometric_full_volume_rule": "P10ED direct curved Tet10 27QP",
        "fixed_region_indicator_rule": "Gauss-Duffy 7^3/9^3 QP; descriptive subzones, not independent pass bands",
        "region_definitions": defs,
        "mesh_diagnostics": audits,
        "topological_diagnostics_M1_to_M2": transitions,
        "proposed_smooth_local_field_family_only": model,
        "interpretation_limits": [
            "subzone quadrature and rare-tet statistics are descriptive and require convergence review",
            "corner-face neighbour jump is a quality diagnostic; no accepted quantitative smoothness threshold",
            "coordinate-point 1e-11m coincidences are indicative, not an exact topology match",
            "M1/M2 centroid nearest-neighbour positions do not pair tetrahedra",
            "two alpha trials cannot uniquely separate size-field response from remeshing topology",
            "a source C1 smooth field does not guarantee local realized volume or FEM accuracy"],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/"P10ER_THREE_MESH_LOCAL_TOPOLOGY_AUDIT.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    with (args.out/"P10ER_FIXED_POLAR_SUBREGION_7_9QP.csv").open(
            "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(contrasts[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(contrasts)
    print("P10ER_THREE_ORIGINAL_MSH_FORENSICS_OK", "regions", len(defs),
          "contrasts", len(contrasts), "FEM=0", "Gmsh=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
