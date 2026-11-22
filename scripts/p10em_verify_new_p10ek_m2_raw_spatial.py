#!/usr/bin/env python3
"""P10EM: inspect the *new* P10EK original M2 against pinned original M1.

Independent read-only MSH2 Tet10 integration in matching spatial regions.
No Gmsh, no physical FEM, no user Windows markers, no raw mesh publication.
Does NOT automatically authorize physical FEM.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from p10ed_verify_original_m1_m2_raw_spatial import (
    CAD_VOL, M1_SHA, RAD, POL, audit_mesh, compare, digest, ensure,
    parse_msh2, rule27, selftest, spatial_rule,
)

P10EK_M2_SHA = "f7183efdaff22b0ed7c281104ee00e18499c0d53f087100e08959a7d4a43250b"
P10EK_TET10 = 9988
P10EK_PORE_TRI6 = 194


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m1", type=Path)
    ap.add_argument("--m2", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    N, D, W = rule27()
    selftest(N, D, W)
    if args.selftest:
        print("P10EM_TET10_RAW_SPATIAL_SYNTHETIC_OK affine=PASS inverted=STOP FEM=0")
        return 0

    ensure(all(x is not None for x in (args.m1, args.m2, args.out)),
           "--m1 --m2 --out required")
    ensure(args.m1.resolve() != args.m2.resolve(), "same M1 and M2 source")
    ensure(args.m1.name == "P10DG_M1_CANDIDATE.msh" and
           args.m2.name == "P10EA_M2_CANDIDATE.msh", "wrong mesh filename")
    ensure(digest(args.m1) == M1_SHA and digest(args.m2) == P10EK_M2_SHA,
           "original P10EK raw MSH2 SHA mismatch; never substitute historical M2")

    a = parse_msh2(args.m1, M1_SHA)
    b = parse_msh2(args.m2, P10EK_M2_SHA)
    ensure(len(a["tet10"]) == 9736 and len(a["pore_tri6"]) == 178 and
           len(b["tet10"]) == P10EK_TET10 and len(b["pore_tri6"]) == P10EK_PORE_TRI6,
           "raw M1/M2 Tet10 and pore Tri6 inventory mismatch")

    sa, rowsa, auxa = audit_mesh(a, "M1", N, D, W)
    sb, rowsb, auxb = audit_mesh(b, "P10EK_M2", N, D, W)
    ensure(all(abs(s["curved_CAD_rel_error"]) < .005 for s in (sa, sb)),
           "curved volume inconsistent with CAD")
    comparison = compare(rowsa, rowsb, auxa, auxb)

    refinements = {}
    for order in (3, 5, 7, 9):
        ra = spatial_rule(a, auxa["vol"], order)
        rb = spatial_rule(b, auxb["vol"], order)
        zone_ratio = [vb/va for va, vb in zip(ra["qp_effective_tet_volume_m3"],
                                               rb["qp_effective_tet_volume_m3"])]
        ns_ratio = [vb/va for va, vb in zip(ra["qp_north_south_effective_tet_volume_m3"],
                                             rb["qp_north_south_effective_tet_volume_m3"])]
        refinements[str(order)] = {
            "qp_per_tet": order**3,
            "zone_effective_volume_ratio_M2_over_M1": zone_ratio,
            "north_south_effective_volume_ratio_M2_over_M1": ns_ratio,
            "zone_geometric_volume_ratio_M2_over_M1": [
                vb/va for va, vb in zip(ra["qp_spatial_volumes_m3"], rb["qp_spatial_volumes_m3"])],
            "m1_region_volume_m3": ra["qp_spatial_volumes_m3"],
            "m2_region_volume_m3": rb["qp_spatial_volumes_m3"],
        }

    hot = (RAD[0], POL[0])
    ensure((comparison[0]["radial_zone"], comparison[0]["polar_zone"]) == hot,
           "first QP region must be full kappa=1 near-pore polar cap")
    q3, q5, q7, q9 = (refinements[str(o)]["zone_effective_volume_ratio_M2_over_M1"][0]
                        for o in (3, 5, 7, 9))
    output = {
        "protocol": "P10EM_ORIGINAL_P10EK_M2_INDEPENDENT_FIXED_3D_QP_SPATIAL",
        "raw_mesh_sha256": {"M1": M1_SHA, "P10EK_M2": P10EK_M2_SHA},
        "raw_meshes_not_published": True,
        "no_Gmsh_no_FEM_no_markers": True,
        "status": "INDEPENDENT_SPATIAL_DIAGNOSTIC_NOT_AUTOMATIC_D023_GO",
        "cad_volume_m3": CAD_VOL,
        "M1": sa,
        "P10EK_M2": sb,
        "zone_definitions": {"radial": RAD, "polar": POL},
        "formula": "zone_effective_volume = integral_zone(dV) / integral_zone(dV/full_curved_Tet10_volume)",
        "refinement_orders_per_axis": [3, 5, 7, 9],
        "fixed_3d_spatial_domain_quadrature": refinements,
        "priority_full_kappa_one_zone": {
            "radial_zone": hot[0], "polar_zone": hot[1],
            "hard_minimum_accepted_characteristic_volume_ratio_at_kappa_1": .8,
            "orders_3_5_7_9_ratio": [q3, q5, q7, q9],
            "largest_last_order_change": abs(q9-q7),
            "order9_below_0p8_warning": q9 < .8,
        },
        "interpretation_limits": [
            "fixed physical zones compare effective volumes, not identical Tet10 elements",
            "boundary QP indicator has quadrature error; inspect 3/5/7/9 trend",
            "nearest-centroid comparison is descriptive only",
            "D-023A allows azimuthal nonuniformity but requires spatial smoothness",
            "M2 forward and adjoint FEM require separate sign-off; no automatic run",
        ],
        "physical_fem_allowed": False,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out/"P10EM_INDEPENDENT_P10EK_M2_SPATIAL_QP.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    csv_path = args.out/"P10EM_INDEPENDENT_P10EK_M2_9_ZONE_COMPARE.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(comparison[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(comparison)
    print("P10EM_NEW_RAW_M2_FIXED_SPATIAL_DIAGNOSTIC_OK FEM=0",
          "kappa_one_orders", *(f"{v:.6f}" for v in (q3,q5,q7,q9)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
