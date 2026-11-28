#!/usr/bin/env python3
"""Independent P10PZ audit: quartic-collocation identity and full P10PY dominance.

Reconstructs degree-four Bezier coefficients independently by solving a
Vandermonde system from physical evaluations of the original M8 Tet10.
Also verifies every one of 48 azimuth/pole bin traces and conservations.
No mesh modifications, FEM, CAD or Gmsh operations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as p10py
import P10PZ_M8_DIRECT_BERNSTEIN_PREFILTER as p10pz


def collocation_identity_audit(xyz, conn):
    """Independent 35×35 evaluation/interpolation vs product-algebra proof."""
    multi = np.array(p10pz.ALPHA4, dtype=np.int64)
    bary = multi / 4.
    vandermonde = np.array([
        [math.factorial(4) / math.prod(math.factorial(int(a)) for a in alpha)
         * np.prod(point ** alpha) for alpha in multi] for point in bary])
    if np.linalg.cond(vandermonde) > 1e5:
        raise ValueError("unexpected quartic interpolation conditioning")
    indices = [0, len(conn) // 7, len(conn) // 3, len(conn) // 2, len(conn)-1]
    maximum_relative_error = 0.
    num_tests = 0
    for index in indices:
        X = xyz[conn[index]]
        cells = p10py.REF_TET[np.newaxis].copy()
        for depth in range(4):
            controls, physical_vertices = p10pz.restricted_control_net(X, cells)
            coeff_r, coeff_cone = p10pz.true_quartic_coefficients(controls - m8.CENTER)
            for k, child in enumerate(cells):
                physical = np.array([m8.tet10_shape(tuple(pt))[0] @ X - m8.CENTER
                                     for pt in bary @ child])
                true_r = (physical**2).sum(axis=1)
                true_cone = .36*physical[:, 2]**2 - .64*(physical[:, 0]**2+physical[:, 1]**2)
                reconstructed_r = np.linalg.solve(vandermonde, true_r)
                reconstructed_cone = np.linalg.solve(vandermonde, true_cone)
                scale = max(1e-8, np.max(np.abs(true_r)))
                maximum_relative_error = max(maximum_relative_error,
                    np.max(np.abs(reconstructed_r - coeff_r[k])) / scale,
                    np.max(np.abs(reconstructed_cone - coeff_cone[k])) / scale)
                num_tests += 1
            if depth < 3:
                cells = p10py.bisect_longest_curved_edge(cells, physical_vertices)
    if maximum_relative_error >= 1e-10:
        raise ValueError(f"independent Bernstein interpolation differs: {maximum_relative_error}")
    return {"test_count": num_tests, "max_rel_error_vs_nodal_collocation": float(maximum_relative_error),
            "collocation_condition_number": float(np.linalg.cond(vandermonde))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("P10PZ_M8_BERNSTEIN_SUMMARY_QA.json"))
    parser.add_argument("--csv", type=Path, default=Path("P10PZ_M8_BERNSTEIN_CONVERGENCE.csv"))
    args = parser.parse_args()
    m8_digest = hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    if m8_digest != m8.PINNED_M8_SHA256:
        raise SystemExit("P10PZ_QA_STOP_UNPINNED_M8")
    old = json.loads(args.baseline.read_text(encoding="utf-8"))
    new = json.loads(args.candidate.read_text(encoding="utf-8"))
    if old["mesh_sha256"] != new["mesh_sha256"] or new["mesh_sha256"] != m8_digest:
        raise ValueError("mesh hash mismatch")
    if new["status"] != "PASS_DIRECT_BERNSTEIN_ALL_48_POLES_GEOMETRY_ONLY":
        raise ValueError("candidate did not finish")
    if new["mesh_changed"] or new["fem_started"] or new["gmsh_generated"]:
        raise ValueError("unexpected physical operation")
    if new["bernstein_vs_aabb_contradictions"] != 0:
        raise ValueError("contradictory geometric signs")
    if old["bin_count"] != 48 or new["bin_count"] != 48 or new["maximum_depth"] != 12:
        raise ValueError("incomplete 48-bin depth-12 audit")
    xyz, conn, ids, types, faces = m8.parse_msh(args.mesh)
    if new["node_count"] != len(xyz) or new["tet10_count"] != len(conn):
        raise ValueError("M8 geometry count mismatch")
    interpolation = collocation_identity_audit(xyz, conn)
    names = ["near_south", "near_north", "far_south", "far_north"]
    summary = {name: {"radial_bin": ir, "mu_bin": im, "candidate_pairs": 0,
                      "depth": []} for name,(ir,im) in zip(names,[(0,0),(0,9),(4,0),(4,9)])}
    for ob, nb in zip(old["bins"], new["bins"]):
        key = (ob["radial_bin"], ob["mu_bin"], ob["phi_bin"])
        if key != (nb["radial_bin"], nb["mu_bin"], nb["phi_bin"]):
            raise ValueError("different bin order")
        n = ob["original_possible_Tet10"]
        if n != nb["original_possible_Tet10"] or n <= 0:
            raise ValueError("different original candidate count")
        group_name = names[[(0,0),(0,9),(4,0),(4,9)].index(key[:2])]
        group = summary[group_name]
        group["candidate_pairs"] += n
        prev_unknown, prev_multi = 1.0, 1.0
        for depth,(a,b) in enumerate(zip(ob["depth_records"], nb["depth_records"])):
            if a["depth"] != depth or b["depth"] != depth:
                raise ValueError("missing or misordered depth")
            if depth >= len(group["depth"]):
                group["depth"].append({"level": depth, "old_uncertain_sum": 0.,
                                       "new_uncertain_sum": 0., "old_multi_sum": 0.,
                                       "new_multi_sum": 0., "old_leaves": 0,
                                       "new_leaves": 0})
            g = group["depth"][depth]
            for source,target in [("uncertain_sum", "uncertain_sum"),
                                  ("multi_quartic_sum", "multi_sum"),
                                  ("uncertain_leaves", "leaves")]:
                g["old_"+target] += a[source]
                g["new_"+target] += b[source]
            for field in ("uncertain_sum","multi_quartic_sum"):
                if b[field] > a[field] + 1e-9:
                    raise ValueError("P10PZ sign prefilter regressed from P10PY")
            if abs(b["certified_inside_sum"] + b["certified_outside_sum"] + b["uncertain_sum"] - n) > 1e-9:
                raise ValueError("missing reference mass")
            if abs(b["multi_quartic_sum"] + b["one_quartic_sum"] + b["zero_quartic_sum"] - b["uncertain_sum"]) > 1e-9:
                raise ValueError("missing quartic-status mass")
            uncertain, multi = b["uncertain_sum"]/n, b["multi_quartic_sum"]/n
            if uncertain > prev_unknown + 1e-11 or multi > prev_multi + 1e-11:
                raise ValueError("new classifier not monotone")
            prev_unknown, prev_multi = uncertain, multi
        if len(nb["depth_records"]) != 13:
            raise ValueError("required depth records missing")
    lines = ["radial_bin,mu_bin,depth,P10PY_uncertain_pct,P10PZ_uncertain_pct,"
             "P10PY_multi_quartic_pct,P10PZ_multi_quartic_pct,old_uncertain_leaves,new_uncertain_leaves"]
    for group in summary.values():
        n = group["candidate_pairs"]
        for d in group["depth"]:
            d["old_uncertain_pct"] = 100*d["old_uncertain_sum"]/n
            d["new_uncertain_pct"] = 100*d["new_uncertain_sum"]/n
            d["old_multi_pct"] = 100*d["old_multi_sum"]/n
            d["new_multi_pct"] = 100*d["new_multi_sum"]/n
            lines.append(f"{group['radial_bin']},{group['mu_bin']},{d['level']},"
                         f"{d['old_uncertain_pct']:.9f},{d['new_uncertain_pct']:.9f},"
                         f"{d['old_multi_pct']:.9f},{d['new_multi_pct']:.9f},"
                         f"{d['old_leaves']},{d['new_leaves']}")
    totals = {"old_uncertain_leaves_d12": 0, "new_uncertain_leaves_d12": 0,
              "old_multi_reference_mass_d12": 0., "new_multi_reference_mass_d12": 0.}
    for g in summary.values():
        d=g["depth"][-1]
        totals["old_uncertain_leaves_d12"] += d["old_leaves"]
        totals["new_uncertain_leaves_d12"] += d["new_leaves"]
        totals["old_multi_reference_mass_d12"] += d["old_multi_sum"]
        totals["new_multi_reference_mass_d12"] += d["new_multi_sum"]
    totals["leaf_reduction_pct"] = 100*(1-totals["new_uncertain_leaves_d12"]/totals["old_uncertain_leaves_d12"])
    totals["multi_mass_reduction_pct"] = 100*(1-totals["new_multi_reference_mass_d12"]/totals["old_multi_reference_mass_d12"])
    if totals["leaf_reduction_pct"] < 10 or totals["multi_mass_reduction_pct"] < 5:
        raise ValueError("sign bound improvement too small for P10PZ acceptance")
    report = {"stage": "P10PZ", "status": "PASS_INDEPENDENT_DIRECT_BERNSTEIN_M8_ALL48",
              "mesh_sha256": m8_digest, "mesh_changed": False, "fem_started": False,
              "gmsh_generated": False, "group_summary": summary, "global_totals": totals,
              "independent_polynomial_collocation": interpolation,
              "metric_warning": "candidate reference-volume uncertainty, not physical cut-volume or FEM convergence"}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    args.csv.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print("P10PZ_INDEPENDENT_AUDIT_PASS", json.dumps(totals), flush=True)


if __name__ == "__main__":
    main()
