#!/usr/bin/env python3
"""P10DE: read-only geometric M0=H0/M1 comparison; no solver, no remeshing.

Uses the historical P10CT MSH2 parser and independent P10CK 27-point curved
Tet10 geometry (Gmsh node order). Never interprets mesh differences as
adjoint derivatives or error indicators.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import sys
import tempfile

from P10CT_u0_mesh_audit import parse, sha256, selftest as p10ct_selftest
from P10CK_curved_qp_audit import QUAD, eval_tet
from P10CP_mesh_b6_profile import corner_geometry

H0_SHA = "e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8"
EXACT_VOLUME = .06 * .06 * .05 - 4. * math.pi * (.001**3) / 3.
EDGES_MM = (0., .02, .1, .5, 1.5, 5., 18., math.inf)
RADIAL_LABELS = ("0_20um", "20_100um", "100_500um", "0p5_1p5mm",
                 "1p5_5mm", "5_18mm", "18mm_plus")
CONTRACT = "P10DE_R1_M0_H0_M1_GRADED_NO_INDICATORS_NO_FEM"


def require(condition: bool, msg: str) -> None:
    if not condition:
        raise ValueError("P10DE_QA_STOP: " + msg)


def radial_index(mm: float) -> int:
    require(mm > -1e-7, "Tet10 centroid inside pore")
    for i in range(len(EDGES_MM) - 1):
        if mm < EDGES_MM[i + 1]:
            return i
    raise ValueError("unreachable radial index")


def quantile(xs: list[float], f: float) -> float | None:
    if not xs:
        return None
    x = sorted(xs)
    r = (len(x) - 1) * f
    a = int(r)
    return x[a] * (1 - (r - a)) + x[min(a + 1, len(x) - 1)] * (r - a)


def read_all_curved(mesh: Path) -> dict:
    """ALL 27 Tet10 curved quadrature samples, exact ASCII MSH2, strict tags."""
    coords = None
    radial = defaultdict(lambda: defaultdict(list))
    overall = defaultdict(list)
    qp_negative = 0
    corner_negative = 0
    qp_min = math.inf
    total_volume = 0.
    count_tet = count_pore_tri = 0
    wall_radial_error = 0.
    with mesh.open("r", encoding="ascii", errors="strict") as f:
        for line in f:
            if line.strip() == "$Nodes":
                require(coords is None, "duplicate node section")
                n = int(next(f))
                coords = {}
                for _ in range(n):
                    cols = next(f).split()
                    require(len(cols) == 4, "node record columns")
                    xyz = tuple(float(x) for x in cols[1:])
                    require(all(math.isfinite(v) for v in xyz), "nonfinite node")
                    coords[int(cols[0])] = xyz
                require(next(f).strip() == "$EndNodes", "node section end")
            if line.strip() == "$Elements":
                require(coords is not None, "nodes before elements")
                n_elem = int(next(f))
                for _ in range(n_elem):
                    col = next(f).split()
                    typ, ntag = int(col[1]), int(col[2])
                    tag = int(col[3])
                    ids = [int(x) for x in col[3 + ntag:]]
                    if typ == 9 and tag == 8:
                        require(len(ids) == 6, "pore Tri6 node count")
                        count_pore_tri += 1
                        for nid in ids:
                            x, y, z = coords[nid]
                            err = abs(math.sqrt(x*x + y*y + (z-.03)**2) - .001)
                            wall_radial_error = max(wall_radial_error, err)
                    if typ != 11:
                        continue
                    require(tag == 1 and len(ids) == 10, "Tet10 type/tag/size")
                    p = [coords[nid] for nid in ids]
                    count_tet += 1
                    g = corner_geometry(p)
                    corner_negative += g["signed_corner_det"] <= 0.
                    cx, cy, cz = (sum(p[k][j] for k in range(4)) / 4. for j in range(3))
                    rr = math.sqrt(cx*cx + cy*cy + (cz-.03)**2)
                    mm = (rr - .001)*1000.
                    i = radial_index(mm)
                    mu = min(9, max(0, int(5. * (1. + (cz-.03)/rr))))
                    acc = radial[(i, mu)]
                    for name, v in (("corner_volume", g["corner_vol_m3"]),
                                    ("hmax_mm", g["hmax_mm"]),
                                    ("quality", g["quality"])):
                        acc[name].append(v)
                        overall[name].append(v)
                    volume = 0.
                    for N, D, weight in QUAD:
                        _x, jac = eval_tet(p, N, D)
                        require(math.isfinite(jac), "nonfinite curved detJ")
                        qp_min = min(qp_min, jac)
                        qp_negative += jac <= 0.
                        volume += weight * jac
                    total_volume += volume
                require(next(f).strip() == "$EndElements", "element section end")
                break
    require(count_tet > 0 and count_pore_tri > 0, "no Tet10/pore Tri6")
    rows = []
    for i, label in enumerate(RADIAL_LABELS):
        for mu in range(10):
            d = radial.get((i, mu), {})
            vs = d.get("corner_volume", [])
            es = d.get("hmax_mm", [])
            qs = d.get("quality", [])
            rows.append({
                "radial_band": label, "mu_bin": mu, "tet10": len(vs),
                "median_corner_volume_m3": quantile(vs, .5),
                "median_hmax_mm": quantile(es, .5),
                "min_corner_quality": min(qs) if qs else None,
                "p05_corner_quality": quantile(qs, .05),
            })
    return {
        "mesh_sha256": sha256(mesh), "tet10": count_tet,
        "pore_tri6": count_pore_tri,
        "wall_node_max_radial_deviation_m": wall_radial_error,
        "corner_negative": corner_negative,
        "curved_qp_count": 27 * count_tet,
        "curved_qp_negative": qp_negative,
        "curved_qp_det_min": qp_min,
        "curved_volume_sum_m3": total_volume,
        "curved_volume_relative_CAD_error": (total_volume/EXACT_VOLUME)-1.,
        "global_median_corner_volume_m3": quantile(overall["corner_volume"], .5),
        "global_median_corner_hmax_mm": quantile(overall["hmax_mm"], .5),
        "global_min_corner_quality": min(overall["quality"]),
        "rows": rows,
    }


def check_one(mesh: Path, *, is_h0: bool) -> dict:
    require(mesh.is_file(), "missing MSH2 input: " + str(mesh))
    digest = sha256(mesh)
    if is_h0:
        require(digest == H0_SHA, "historic H0 SHA mismatch; stop before comparison")
    with mesh.open("r", encoding="ascii", errors="strict") as f:
        original, coarse_rows = parse(f)
    full = read_all_curved(mesh)
    require(original["tet10"] == full["tet10"] and
            original["physical_group_counts"]["2:8"] == full["pore_tri6"],
            "independent old/new parser count disagreement")
    if is_h0:
        require(original["mesh_nodes"] == 10845 and original["tet10"] == 7388 and
                full["pore_tri6"] == 136, "H0 historic structural counts mismatch")
    issues = []
    if original["missing_or_misnamed_groups"]:
        issues.append("physical tags or names missing/mismatched")
    if original["corner_det_nonpositive_count"] or full["corner_negative"]:
        issues.append("nonpositive corner Jacobian")
    if full["curved_qp_negative"]:
        issues.append("nonpositive 27QP curved Jacobian")
    if full["global_min_corner_quality"] <= .02:
        issues.append("min corner quality <= 0.02")
    if full["wall_node_max_radial_deviation_m"] >= 1e-8:
        issues.append("pore Tri6 not lying on exact sphere")
    if abs(full["curved_volume_relative_CAD_error"]) > .005:
        issues.append("curved volume differs from CAD by >0.5%")
    return {"structural": original, "full_curved": full, "issues": issues,
            "p10ct_480_bins_coverage": len(coarse_rows)}


def audit(h0: Path, m1: Path) -> tuple[dict, list[dict]]:
    require(h0.resolve() != m1.resolve(), "H0 and M1 must be separate files")
    a, b = check_one(h0, is_h0=True), check_one(m1, is_h0=False)
    ar, br = a["full_curved"], b["full_curved"]
    require(ar["mesh_sha256"] != br["mesh_sha256"], "M1 is byte-identical to H0")
    vol_ratio = br["global_median_corner_volume_m3"] / ar["global_median_corner_volume_m3"]
    h_ratio = br["global_median_corner_hmax_mm"] / ar["global_median_corner_hmax_mm"]
    m1_more = br["tet10"] > ar["tet10"]
    near_target = .65 <= vol_ratio <= .95
    design_issues = []
    if not m1_more:
        design_issues.append("M1 has no more Tet10 than H0")
    if not near_target:
        design_issues.append("global unpaired median Tet10 volume ratio outside 0.65-0.95")
    all_clean = not a["issues"] and not b["issues"] and not design_issues
    summary = {
        "protocol": CONTRACT, "status": "GEOMETRY_QA_PASS" if all_clean else "GEOMETRY_QA_STOP",
        "h0_sha256": ar["mesh_sha256"], "m1_sha256": br["mesh_sha256"],
        "h0": {k: v for k, v in ar.items() if k != "rows"},
        "m1": {k: v for k, v in br.items() if k != "rows"},
        "h0_issues": a["issues"], "m1_issues": b["issues"],
        "mesh_target_issues": design_issues,
        "element_ratio_M1_over_H0": br["tet10"] / ar["tet10"],
        "median_corner_volume_ratio_M1_over_H0": vol_ratio,
        "median_hmax_ratio_M1_over_H0": h_ratio,
        "target_volume_ratio": .8,
        "target_h_ratio": .8**(1./3.),
        "new_tet10_count_exceeds_h0": m1_more,
        "mesh_refinement_observed": bool(m1_more and vol_ratio < 1.),
        "mesh_refinement_target_about_20pct_broad_gate": near_target,
        "comparison_rule": "Unpaired medians of distinct meshes; no element-by-element 20% guarantee",
        "binning_rule": "Corner-centroid radial and mu only, NOT physical 4D derivative",
        "jacobian_rule": "27 curved Tet10 QPs for ALL tetrahedra; positivity at these points is not positivity everywhere",
        "FEM_runs": 0,
    }
    profiles = []
    for sample, obj in (("H0", ar), ("M1", br)):
        for r in obj["rows"]:
            profiles.append({"mesh": sample, **r})
    return summary, profiles


def selftest() -> None:
    p10ct_selftest()
    require(len(RADIAL_LABELS) == 7 and radial_index(.0) == 0 and
            radial_index(.02) == 1 and radial_index(.1) == 2 and
            radial_index(24.) == 6, "radial bins")
    require(abs(sum(w for _, _, w in QUAD) - 1./6.) < 1e-15, "tetra quadrature")
    require(quantile([1., 2., 3.], .5) == 2., "quantile")
    for bad in (-.01, -1.):
        try:
            radial_index(bad)
        except ValueError:
            pass
        else:
            raise ValueError("negative test failed to reject pore interior")
    # Exercise OUR second MSH2 parser and all-27-QP loop on a straight Tet10.
    p4 = ((.0012, 0., .03), (.00124, 0., .03),
          (.0012, .00004, .03), (.0012, 0., .03004))
    edges = ((0, 1), (1, 2), (2, 0), (0, 3), (2, 3), (1, 3))
    p10 = p4 + tuple(tuple((p4[i][j] + p4[k][j]) / 2 for j in range(3))
                     for i, k in edges)
    names = ["ICE_VOLUME", "TOP_ROBIN", "BOTTOM_INSULATED",
             "X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS",
             "PORE_WALL", "B6_INTERFACE"]
    lines = ["$MeshFormat", "2.2 0 8", "$EndMeshFormat", "$PhysicalNames", "9"]
    lines += [f'{3 if i == 1 else 2} {i} "{name}"'
              for i, name in enumerate(names, 1)]
    lines += ["$EndPhysicalNames", "$Nodes", "10"]
    lines += [str(i) + " " + " ".join(str(v) for v in p)
              for i, p in enumerate(p10, 1)]
    lines += ["$EndNodes", "$Elements", "9"]
    lines += [f"{i-1} 9 2 {i} {i} 1 2 3 5 6 7" for i in range(2, 10)]
    lines += ["9 11 2 1 1 " + " ".join(map(str, range(1, 11))), "$EndElements"]
    with tempfile.TemporaryDirectory(prefix="p10de_qa_selftest_") as td:
        path = Path(td) / "fixture.msh"
        path.write_text("\n".join(lines) + "\n", encoding="ascii")
        sample = read_all_curved(path)
        folded = list(p10)
        folded[4] = (p4[0][0] - 4e-6, p4[0][1] + 2e-5, p4[0][2])
        original_row = "5 " + " ".join(str(v) for v in p10[4])
        folded_row = "5 " + " ".join(str(v) for v in folded[4])
        text = path.read_text(encoding="ascii")
        require(original_row in text, "synthetic fold fixture")
        path.write_text(text.replace(original_row, folded_row, 1), encoding="ascii")
        invalid = read_all_curved(path)
    require(sample["tet10"] == 1 and sample["pore_tri6"] == 1 and
            sample["curved_qp_count"] == 27 and
            sample["curved_qp_negative"] == 0 and
            abs(sample["curved_volume_sum_m3"] - (4e-5)**3/6.) < 1e-20,
            "independent full 27QP real-parser fixture")
    require(invalid["curved_qp_negative"] > 0 and
            invalid["corner_negative"] == 0,
            "folded curved Tet10 negative fixture was not detected")
    print("P10DE_M1_MESH_QA_SYNTHETIC_OK curved27=PASS parser=PASS folded_negative=DETECTED FEM=0")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--h0", type=Path)
    ap.add_argument("--m1", type=Path)
    ap.add_argument("--out", type=Path)
    opts = ap.parse_args()
    if opts.selftest:
        selftest()
        return 0
    if not opts.h0 or not opts.m1 or not opts.out:
        ap.error("--h0 --m1 --out required")
    summary, profiles = audit(opts.h0, opts.m1)
    opts.out.mkdir(parents=True, exist_ok=True)
    (opts.out / "P10DE_M0_M1_MESH_QA.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (opts.out / "P10DE_M0_M1_RADIAL_MU_BINS.csv").open(
            "w", newline="", encoding="utf-8") as f:
        fields = list(profiles[0])
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(profiles)
    print("P10DE_M1_QA_PASS_NO_FEM" if summary["status"] == "GEOMETRY_QA_PASS"
          else "P10DE_M1_QA_STOP_NO_FEM",
          "H0_TET10=", summary["h0"]["tet10"],
          "M1_TET10=", summary["m1"]["tet10"],
          "MEDIAN_CORNER_VOLUME_RATIO=", summary["median_corner_volume_ratio_M1_over_H0"])
    return 0 if summary["status"] == "GEOMETRY_QA_PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
