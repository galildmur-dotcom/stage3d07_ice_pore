#!/usr/bin/env python3
"""P10PZ: exact polynomial Bernstein-sign prefilter on accepted curved Tet10 M8.

All geometry stays on the original M8. A quadratic isoparametric map is
restricted to reference sub-tetrahedra and degree-two Bezier coefficients are
multiplied analytically to produce *degree-four Bernstein coefficients* of
the radial and polar bin level sets. No collocation inversion is used.

Mathematical sign enclosure follows from Bernstein convex-hull property.
Floating-point evaluations employ explicit guards, not directed interval
arithmetic; they are not machine-verification certificates.
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
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as p10py


def multi_index(degree: int):
    return [tuple(i) for i in itertools.product(range(degree + 1), repeat=4)
            if sum(i) == degree]


ALPHA2 = [(2, 0, 0, 0), (0, 2, 0, 0), (0, 0, 2, 0), (0, 0, 0, 2)] + [
    tuple(int(k == a) + int(k == b) for k in range(4)) for a, b in p10py.EDGES]
ALPHA4 = multi_index(4)
MULT4_POS = {alpha: i for i, alpha in enumerate(ALPHA4)}


def multinomial(n: int, alpha: tuple[int, ...]):
    return math.factorial(n) // math.prod(math.factorial(x) for x in alpha)


def make_product_groups():
    """B^2_alpha * B^2_beta = [C(2,a)C(2,b)/C(4,a+b)] B^4_(a+b)."""
    groups = [[] for _ in ALPHA4]
    for i, a in enumerate(ALPHA2):
        for j, b in enumerate(ALPHA2):
            c = tuple(x + y for x, y in zip(a, b))
            groups[MULT4_POS[c]].append((i, j, multinomial(2, a) *
                                         multinomial(2, b) / multinomial(4, c)))
    return [(np.array([q[0] for q in g], dtype=np.intp),
             np.array([q[1] for q in g], dtype=np.intp),
             np.array([q[2] for q in g], dtype=np.float64)) for g in groups]


PRODUCT_GROUPS = make_product_groups()
EPS = np.finfo(np.float64).eps


def true_quartic_coefficients(controls: np.ndarray):
    """Return degree-4 Bezier coefficients for r² and the polar cone.

    controls: (n,10,3) of curved physical mapping relative to pore centre.
    cone = 0.36*z² - 0.64*(x²+y²) (positive within either cap).
    """
    x, y, z = (controls[:, :, k] for k in range(3))
    xx = x[:, :, None] * x[:, None, :]
    yy = y[:, :, None] * y[:, None, :]
    zz = z[:, :, None] * z[:, None, :]
    pair_r = xx + yy + zz
    pair_cone = .36 * zz - .64 * (xx + yy)
    r = np.empty((len(controls), len(ALPHA4)), dtype=np.float64)
    cone = np.empty_like(r)
    for k, (i, j, w) in enumerate(PRODUCT_GROUPS):
        r[:, k] = (pair_r[:, i, j] * w).sum(axis=1)
        cone[:, k] = (pair_cone[:, i, j] * w).sum(axis=1)
    return r, cone


def guarded_sign(coefficients: np.ndarray, guard: np.ndarray):
    low = coefficients.min(axis=1)
    high = coefficients.max(axis=1)
    return np.where(high < -guard, -1, np.where(low > guard, 1, 0)).astype(np.int8)


def quartic_and_linear_status(controls: np.ndarray, ir: int, im: int, ip: int):
    """Sign of six defining inequalities, using actual polynomial controls."""
    relative = controls - m8.CENTER
    r, cone = true_quartic_coefficients(relative)
    maxcoord = np.max(np.abs(relative), axis=(1, 2))
    rho_lo = m8.PORE_R + m8.RADIAL_LOWER_MM[ir] / 1000.
    rho_hi = m8.PORE_R + m8.RADIAL_LOWER_MM[ir + 1] / 1000.
    # Scale-aware backward-error cushion for polynomial products in double.
    guard4 = 512 * EPS * (maxcoord**2 + rho_hi**2)
    status = [guarded_sign(r - rho_lo**2, guard4),
              guarded_sign(rho_hi**2 - r, guard4)]
    guard2 = 128 * EPS * np.maximum(maxcoord, m8.PORE_R)
    sign = 1 if im == 9 else -1
    status.append(guarded_sign(sign * relative[:, :, 2], guard2))
    status.append(guarded_sign(cone, guard4))
    angle = -math.pi + 2 * math.pi * ip / 12
    for k, direction in enumerate([angle, angle + math.pi / 6]):
        value = -math.sin(direction) * relative[:, :, 0] + math.cos(direction) * relative[:, :, 1]
        if k:
            value = -value
        status.append(guarded_sign(value, guard2))
    return np.stack(status, axis=1)


def restricted_control_net(X: np.ndarray, ref_vertices: np.ndarray):
    mid = .5 * (ref_vertices[:, p10py.EDGES[:, 0]] + ref_vertices[:, p10py.EDGES[:, 1]])
    mapped = p10py.map_tet10_nodally(X, np.concatenate((ref_vertices, mid), axis=1))
    controls = mapped.copy()
    for k, (a, b) in enumerate(p10py.EDGES, start=4):
        controls[:, k] = 2 * mapped[:, k] - .5 * (mapped[:, a] + mapped[:, b])
    return controls, mapped[:, :4]


def adaptive_one(X: np.ndarray, ir: int, im: int, ip: int, maximum: int):
    active = p10py.REF_TET[np.newaxis].copy()
    inside_mass = 0.
    outside_mass = 0.
    records = []
    aabb_conflicts = 0
    for depth in range(maximum + 1):
        if len(active):
            controls, vertices = restricted_control_net(X, active)
            lo, hi = controls.min(axis=1) - m8.CENTER, controls.max(axis=1) - m8.CENTER
            _, _, box_status = m8.candidate_masks(lo, hi, ir, im, ip)
            polynomial_status = quartic_and_linear_status(controls, ir, im, ip)
            conflict = ((box_status == 1) & (polynomial_status == -1)) | (
                (box_status == -1) & (polynomial_status == 1))
            aabb_conflicts += int(conflict.sum())
            if conflict.any():
                raise ValueError("Bernstein/AABB exclusion signs contradict")
            # Retain already-conclusive AABB exclusions, tightening only zeros.
            status = np.where(box_status == 0, polynomial_status, box_status)
            excluded = (status == -1).any(axis=1)
            included = (status == 1).all(axis=1)
            unknown = ~excluded & ~included
            weight = 2. ** (-depth)
            inside_mass += float(included.sum()) * weight
            outside_mass += float(excluded.sum()) * weight
            multi = (status[:, [0, 1, 3]] == 0).sum(axis=1)
            ambiguous_multi = float(((multi >= 2) & unknown).sum()) * weight
            ambiguous_one = float(((multi == 1) & unknown).sum()) * weight
            ambiguous_zero = float(((multi == 0) & unknown).sum()) * weight
            unknown_count = int(unknown.sum())
            if depth < maximum:
                active = p10py.bisect_longest_curved_edge(active[unknown], vertices[unknown])
        else:
            unknown_count = 0
            ambiguous_multi = ambiguous_one = ambiguous_zero = 0.
        undecided = unknown_count * 2. ** (-depth)
        if abs(inside_mass + outside_mass + undecided - 1) > 1e-10:
            raise ValueError("nonconservative h-partition")
        if abs(undecided - ambiguous_multi - ambiguous_one - ambiguous_zero) > 1e-12:
            raise ValueError("nonconservative active-polynomial partition")
        records.append({"depth": depth, "certified_inside_fraction": inside_mass,
                        "certified_outside_fraction": outside_mass,
                        "uncertain_fraction": undecided,
                        "multi_quartic_uncertain_fraction": ambiguous_multi,
                        "one_quartic_uncertain_fraction": ambiguous_one,
                        "zero_quartic_uncertain_fraction": ambiguous_zero,
                        "uncertain_leaves": unknown_count,
                        "still_ambiguous": bool(unknown_count),
                        "still_multi_quartic": bool(ambiguous_multi)})
    return records, aabb_conflicts


def direct_polynomial_identity_test(X: np.ndarray):
    """Check product algebra against exact curved-Tet10 point evaluation."""
    base = p10py.REF_TET[np.newaxis].copy()
    for _ in range(4):
        controls, vertices = restricted_control_net(X, base)
        base = p10py.bisect_longest_curved_edge(base, vertices)
    controls, _ = restricted_control_net(X, base)
    r, cone = true_quartic_coefficients(controls - m8.CENTER)
    rng = np.random.default_rng(20261128)
    bary = rng.dirichlet(np.ones(4), size=32)
    alpha4 = np.array(ALPHA4)
    basis = np.array([multinomial(4,tuple(a)) * np.prod(t**a) for t in bary for a in alpha4])
    basis = basis.reshape(len(bary), len(ALPHA4))
    for k, sub in enumerate(base):
        coords = p10py.map_tet10_nodally(X, (bary @ sub)[:, None, :])[:, 0, :] - m8.CENTER
        expected_r = np.einsum('nd,nd->n', coords, coords)
        expected_cone = .36 * coords[:, 2]**2 - .64 * (coords[:, 0]**2 + coords[:, 1]**2)
        if np.max(np.abs(basis @ r[k] - expected_r)) > 1e-13 * max(expected_r.max(), 1e-6):
            raise ValueError("radial quartic Bernstein reproduction failed")
        if np.max(np.abs(basis @ cone[k] - expected_cone)) > 1e-13 * max(expected_r.max(), 1e-6):
            raise ValueError("polar quartic Bernstein reproduction failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("P10PZ_M8_BERNSTEIN_QA.json"))
    args = parser.parse_args()
    if not 0 <= args.max_depth <= 12:
        parser.error("depth must be in 0..12")
    digest = hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    if digest != m8.PINNED_M8_SHA256 or baseline["mesh_sha256"] != digest or baseline["bin_count"] != 48:
        raise SystemExit("P10PZ_STOP_UNACCEPTED_M8_OR_BASELINE")
    if args.max_depth > baseline["maximum_depth"]:
        raise SystemExit("P10PZ_STOP_BASELINE_TOO_SHALLOW")
    xyz, conn, ids, types, faces = m8.parse_msh(args.mesh)
    X = xyz[conn]
    for e in [0, len(X) // 2, len(X) - 1]:
        direct_polynomial_identity_test(X[e])
    root_control = X.copy()
    for k, (a, b) in enumerate(p10py.EDGES, start=4):
        root_control[:, k] = 2 * X[:, k] - .5 * (X[:, a] + X[:, b])
    root_lo, root_hi = root_control.min(axis=1) - m8.CENTER, root_control.max(axis=1) - m8.CENTER
    bins = []
    conflicts = 0
    for index, base_bin in enumerate(baseline["bins"]):
        ir, im, ip = (base_bin[key] for key in ("radial_bin", "mu_bin", "phi_bin"))
        possible, _, _ = m8.candidate_masks(root_lo, root_hi, ir, im, ip)
        candidates = np.flatnonzero(possible)
        if len(candidates) != base_bin["original_possible_Tet10"]:
            raise ValueError("baseline candidate count changed")
        total = len(candidates)
        accum = [{"depth": d, "certified_inside_sum": 0., "certified_outside_sum": 0.,
                  "uncertain_sum": 0., "multi_quartic_sum": 0., "one_quartic_sum": 0.,
                  "zero_quartic_sum": 0., "uncertain_leaves": 0,
                  "ambiguous_elements": 0, "multi_quartic_elements": 0}
                 for d in range(args.max_depth + 1)]
        for e in candidates:
            records, cf = adaptive_one(X[e], ir, im, ip, args.max_depth)
            conflicts += cf
            for a, row in zip(accum, records):
                for source, target in [
                    ("certified_inside_fraction", "certified_inside_sum"),
                    ("certified_outside_fraction", "certified_outside_sum"),
                    ("uncertain_fraction", "uncertain_sum"),
                    ("multi_quartic_uncertain_fraction", "multi_quartic_sum"),
                    ("one_quartic_uncertain_fraction", "one_quartic_sum"),
                    ("zero_quartic_uncertain_fraction", "zero_quartic_sum"),
                    ("uncertain_leaves", "uncertain_leaves")]:
                    a[target] += row[source]
                a["ambiguous_elements"] += int(row["still_ambiguous"])
                a["multi_quartic_elements"] += int(row["still_multi_quartic"])
        for a, base in zip(accum, base_bin["depth_records"]):
            a["unresolved_reference_volume_fraction_of_candidates"] = a["uncertain_sum"] / total
            a["multi_quartic_reference_volume_fraction_of_candidates"] = a["multi_quartic_sum"] / total
            if abs(a["certified_inside_sum"] + a["certified_outside_sum"] + a["uncertain_sum"] - total) > 1e-9:
                raise ValueError("aggregate mass not conserved")
            for field in ["unresolved_reference_volume_fraction_of_candidates",
                          "multi_quartic_reference_volume_fraction_of_candidates"]:
                if a[field] > base[field] + 1e-10:
                    raise ValueError("direct Bernstein method worse than P10PY")
        bins.append({"radial_bin": ir, "mu_bin": im, "phi_bin": ip,
                     "original_possible_Tet10": total, "depth_records": accum})
        a = accum[-1]
        print(f"P10PZ_BIN_{index+1:02d}/48 r={ir} mu={im} phi={ip} "
              f"d{args.max_depth}_multi={a['multi_quartic_reference_volume_fraction_of_candidates']:.7g} "
              f"d{args.max_depth}_uncertain={a['unresolved_reference_volume_fraction_of_candidates']:.7g}",
              flush=True)
    out = {"stage": "P10PZ", "status": "PASS_DIRECT_BERNSTEIN_ALL_48_POLES_GEOMETRY_ONLY",
           "mesh_sha256": digest, "mesh_changed": False, "fem_started": False,
           "gmsh_generated": False, "node_count": len(xyz), "tet10_count": len(X),
           "method": "direct quadratic-Bezier polynomial products into quartic Bernstein level-set controls",
           "floating_point": "guarded IEEE float64, not directed interval arithmetic",
           "baseline": "P10PY all 48 azimuthal polar bins, same original Tet10 candidate pairs",
           "bernstein_vs_aabb_contradictions": conflicts, "maximum_depth": args.max_depth,
           "bin_count": len(bins), "bins": bins}
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("P10PZ_DIRECT_BERNSTEIN_48_BINS_PASS", flush=True)


if __name__ == "__main__":
    main()
