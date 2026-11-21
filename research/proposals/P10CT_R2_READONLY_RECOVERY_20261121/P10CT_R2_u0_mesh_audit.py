#!/usr/bin/env python3
"""P10CT R2: read-only recovery of original R1 U0 mesh, zero Gmsh/FEM.

All spatial bins are element corner-centroid proxies, NOT physical 4D QP fields.
Curved Tet10 positivity is checked at all 27 quadrature samples of EVERY Tet10.
This is still a sampled check, not a mathematical guarantee on the whole element.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sys

from P10CK_curved_qp_audit import QUAD, eval_tet, corner_det, selftest as curved_selftest
from P10CP_mesh_b6_profile import corner_geometry, quantile, selftest as corner_selftest

VERSION = "P10CT_R2_READONLY_FULL_27QP_RECOVERY_NO_GMSH_NO_FEM"
CENTER = (0.0, 0.0, 0.03)
RADIUS_M = 0.001
BOX_VOLUME_M3 = 0.06 * 0.06 * 0.05
EXACT_SOLID_M3 = BOX_VOLUME_M3 - 4.0 * math.pi * RADIUS_M**3 / 3.0
ZONES = ("corner_centroid_inside_pore", "0_20um", "20_100um", "100um_5mm", "outside_B6")
NEARWALL_ZONES = ("corner_centroid_inside_pore", "0_20um", "20_100um")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def zone_of(d_mm: float) -> str:
    if d_mm < 0:
        return ZONES[0]
    if d_mm < 0.02:
        return ZONES[1]
    if d_mm < 0.1:
        return ZONES[2]
    if d_mm <= 5.0:
        return ZONES[3]
    return ZONES[4]


def spherical(p):
    dx, dy, dz = p[0] - CENTER[0], p[1] - CENTER[1], p[2] - CENTER[2]
    radius = math.sqrt(dx * dx + dy * dy + dz * dz)
    if radius <= 0 or not math.isfinite(radius):
        raise ValueError("invalid radius about pore centre")
    mu = max(-1.0, min(1.0, dz / radius))
    phi = math.atan2(dy, dx) % (2 * math.pi) if math.hypot(dx, dy) else 0.0
    return (radius - RADIUS_M) * 1000.0, min(9, int((mu + 1.0) * 5)), min(11, int(phi * 6 / math.pi))


def skip_section(inp, name):
    end = "$End" + name[1:]
    for row in inp:
        if row.strip() == end:
            return
    raise ValueError("unterminated section " + name)


def parse(inp):
    """Read ASCII MSH2; retain nodes and diagnostic statistics, never modify input."""
    if inp.readline().strip() != "$MeshFormat":
        raise ValueError("Gmsh MSH2 header missing")
    fields = inp.readline().split()
    if len(fields) != 3 or fields[0] != "2.2" or fields[1] != "0":
        raise ValueError("expected Gmsh MSH2.2 ASCII")
    if inp.readline().strip() != "$EndMeshFormat":
        raise ValueError("malformed Gmsh MSH2 header")

    nodes, counts, physical_names = None, defaultdict(int), {}
    records = defaultdict(list)
    zone_count, volume_corner, qp_counter = defaultdict(int), 0.0, defaultdict(int)
    q_sample_min, negative_corner, negative_qp = float("inf"), 0, 0
    n_all = n_tet = n_tri = n_qp_tets = 0
    bad_curved_tet_count = 0
    bad_curved_by_zone = defaultdict(int)
    worst_curved_tets = []
    while True:
        raw = inp.readline()
        if not raw:
            break
        label = raw.strip()
        if label == "$PhysicalNames":
            n = int(inp.readline())
            for _ in range(n):
                row = inp.readline().split(maxsplit=2)
                if len(row) != 3:
                    raise ValueError("malformed physical name")
                dim, tag = int(row[0]), int(row[1])
                physical_names[(dim, tag)] = row[2].strip().strip('"')
            if inp.readline().strip() != "$EndPhysicalNames":
                raise ValueError("unclosed $PhysicalNames")
        elif label == "$Nodes":
            if nodes is not None:
                raise ValueError("duplicate $Nodes")
            n = int(inp.readline())
            if n <= 0:
                raise ValueError("empty mesh")
            nodes = {}
            for _ in range(n):
                row = inp.readline().split()
                if len(row) != 4:
                    raise ValueError("invalid node")
                nid = int(row[0])
                if nid in nodes:
                    raise ValueError("duplicate node id")
                xyz = tuple(float(x) for x in row[1:])
                if not all(math.isfinite(x) for x in xyz):
                    raise ValueError("nonfinite coordinate")
                nodes[nid] = xyz
            if inp.readline().strip() != "$EndNodes":
                raise ValueError("unclosed $Nodes")
        elif label == "$Elements":
            if nodes is None:
                raise ValueError("elements before nodes")
            n_all = int(inp.readline())
            for _ in range(n_all):
                row = inp.readline().split()
                if len(row) < 4:
                    raise ValueError("incomplete element")
                typ, ntags = int(row[1]), int(row[2])
                if ntags < 2:
                    raise ValueError("missing physical/geometric tags")
                tag = int(row[3])
                ids = tuple(int(x) for x in row[3 + ntags:])
                if typ == 9:  # Tri6
                    if len(ids) != 6:
                        raise ValueError("Tri6 has incorrect number of nodes")
                    n_tri += 1
                    counts[(2, tag)] += 1
                    if tag == 8:  # all pore-wall nodes lie on exact CAD sphere
                        for nid in ids:
                            d, _, _ = spherical(nodes[nid])
                            records[("wall_node_radius_error_mm", 0, 0)].append(abs(d))
                elif typ == 11:  # Tet10
                    if len(ids) != 10:
                        raise ValueError("Tet10 has incorrect number of nodes")
                    n_tet += 1
                    counts[(3, tag)] += 1
                    if tag != 1:
                        raise ValueError("unexpected Tet10 physical volume tag")
                    p = [nodes[n] for n in ids]
                    c = tuple(sum(p[i][k] for i in range(4)) / 4.0 for k in range(3))
                    d, mu, phi = spherical(c)
                    z = zone_of(d)
                    zone_count[z] += 1
                    # Coarse curved Tet10 may have a straight-corner centroid
                    # geometrically inside the sphere. Record it separately;
                    # do not turn a corner-centroid proxy into a parser STOP.
                    g = corner_geometry(p)
                    negative_corner += g["signed_corner_det"] <= 0.0
                    volume_corner += g["corner_vol_m3"]
                    records[(z, mu, phi)].append((g["hmax_mm"], g["quality"], g["edge_ratio"], g["midside_dev_over_edge"]))
                    # This read-only recovery checks ALL 27QP on ALL Tet10.
                    n_qp_tets += 1
                    qp_counter[z] += 1
                    this_min = float("inf")
                    this_bad = 0
                    for N, D, _weight in QUAD:
                        det = eval_tet(p, N, D)[1]
                        this_min = min(this_min, det)
                        this_bad += det <= 0.0 or not math.isfinite(det)
                    q_sample_min = min(q_sample_min, this_min)
                    negative_qp += this_bad
                    if this_bad:
                        bad_curved_tet_count += 1
                        bad_curved_by_zone[z] += 1
                        item = {"gmsh_element_id": int(row[0]), "zone": z,
                                "d_centroid_mm": d, "mu_bin": mu, "phi_sector": phi,
                                "min_detJ_27qp": this_min, "negative_qp_count": this_bad,
                                "signed_corner_det": g["signed_corner_det"],
                                "corner_quality": g["quality"], "hmax_mm": g["hmax_mm"]}
                        worst_curved_tets.append(item)
                        worst_curved_tets.sort(key=lambda q: q["min_detJ_27qp"])
                        if len(worst_curved_tets) > 30:
                            worst_curved_tets.pop()
                # Other Gmsh elements are counted but never accepted as substitutes.
            if inp.readline().strip() != "$EndElements":
                raise ValueError("unclosed $Elements")
        elif label.startswith("$") and not label.startswith("$End"):
            skip_section(inp, label)
    if nodes is None or not n_tet or not n_tri:
        raise ValueError("missing nodes/Tet10/Tri6")

    # A mesh with all nine canonical physical groups is required; labels are
    # checked as well as tags, to catch accidental remapping of boundaries.
    expected = {(3, 1): "ICE_VOLUME", (2, 2): "TOP_ROBIN", (2, 3): "BOTTOM_INSULATED",
                (2, 4): "X_MINUS", (2, 5): "X_PLUS", (2, 6): "Y_MINUS",
                (2, 7): "Y_PLUS", (2, 8): "PORE_WALL", (2, 9): "B6_INTERFACE"}
    absent = [f"{dim}:{tag}" for (dim, tag), name in expected.items()
              if counts[(dim, tag)] == 0 or physical_names.get((dim, tag)) != name]
    total = sum(zone_count.values())
    assert total == n_tet == sum(counts[(3, i)] for i in range(1, 2))
    rows = []
    for z in ZONES:
        for mu in range(10):
            for phi in range(12):
                a = records.get((z, mu, phi), [])
                rows.append({"zone": z, "polar_mu_bin": mu, "phi_sector": phi,
                             "tet10_centroids": len(a),
                             "hmax_p05_mm": quantile([q[0] for q in a], .05),
                             "hmax_p50_mm": quantile([q[0] for q in a], .5),
                             "hmax_p95_mm": quantile([q[0] for q in a], .95),
                             "corner_quality_p05": quantile([q[1] for q in a], .05),
                             "corner_edge_ratio_p95": quantile([q[2] for q in a], .95)})
    band_summary = {}
    for z in ZONES:
        a = [g for (zz, mu, phi), xs in records.items() if zz == z and isinstance(mu, int) for g in xs]
        p = [g for (zz, mu, phi), xs in records.items() if zz == z and mu in (0, 9) for g in xs]
        band_summary[z] = {"tet10": zone_count[z], "hmax_p05_mm": quantile([x[0] for x in a], .05),
                           "hmax_p50_mm": quantile([x[0] for x in a], .5),
                           "hmax_p95_mm": quantile([x[0] for x in a], .95),
                           "corner_quality_p05": quantile([x[1] for x in a], .05),
                           "polar_tet10": len(p), "polar_hmax_p50_mm": quantile([x[0] for x in p], .5),
                           "mid_hmax_p50_mm": quantile([x[0] for (zz, mu, _), xs in records.items()
                                                       if zz == z and isinstance(mu, int) and mu not in (0, 9)
                                                       for x in xs], .5),
                           "curved_qp_sampled_tet10": qp_counter[z]}
    wall_dev = records.get(("wall_node_radius_error_mm", 0, 0), [])
    all_corner_quality = [g[1] for (z, _, _), xs in records.items() if z in ZONES for g in xs]
    result = {
        "revision": VERSION, "mesh_nodes": len(nodes), "mesh_elements": n_all,
        "tet10": n_tet, "tri6": n_tri, "physical_group_counts": {f"{dim}:{tag}": counts[(dim, tag)] for dim, tag in expected},
        "physical_names": {f"{dim}:{tag}": physical_names.get((dim, tag)) for dim, tag in expected},
        "missing_or_misnamed_groups": absent, "zone_profile": band_summary,
        "tet10_corner_volume_total_m3": volume_corner, "CAD_exact_ice_volume_m3": EXACT_SOLID_M3,
        "corner_volume_relative_difference": (volume_corner / EXACT_SOLID_M3) - 1.0,
        "corner_det_nonpositive_count": negative_corner, "sampled_curved_tet10": n_qp_tets,
        "curved_27qp_samples": 27 * n_qp_tets, "curved_qp_nonpositive_count": negative_qp,
        "curved_tet10_with_nonpositive_27qp_count": bad_curved_tet_count,
        "bad_curved_tet10_by_zone": dict(bad_curved_by_zone),
        "worst_30_curved_tet10": worst_curved_tets,
        "curved_qp_det_min": q_sample_min, "pore_wall_max_radial_node_error_mm": max(wall_dev) if wall_dev else None,
        "corner_quality_lt_0p1_count": sum(x < .1 for x in all_corner_quality),
        "corner_quality_min": min(all_corner_quality),
        "phi_binning_method": "corner_centroid_not_physical_QP_partition",
        "true_4D_mechanical_thermal_fields": "ABSENT", "physical_FEM_runs": 0,
        "uniformity_status": "MEASURED_CORNER_PROXY_NOT_A_PROOF_OF_PHYSICAL_CONVERGENCE",
        "physical_readiness": "NOT_ASSESSED_NO_FEM_AUTHORIZATION",
    }
    return result, rows


def selftest():
    curved_selftest()
    corner_selftest()
    # Exercise basic region/axis indexing and geometry sign without writing a file.
    assert zone_of(.0199) == "0_20um"
    assert zone_of(.0200) == "20_100um"
    assert zone_of(.1000) == "100um_5mm"
    assert zone_of(5.001) == "outside_B6"
    assert spherical((0.0, 0.0, 0.0312))[1] == 9
    assert spherical((0.0, 0.0, 0.0288))[1] == 0
    assert spherical((0.0012, 0.0, 0.03))[2] == 0
    assert len(QUAD) == 27
    # A full in-memory MSH2.2 fixture tests our *own* parser and tag gate.
    # Repeated synthetic Tri6 records test the contract, not physical geometry.
    p4 = [(0.0012, 0.0, 0.03), (0.00124, 0.0, 0.03),
          (0.0012, 0.00004, 0.03), (0.0012, 0.0, 0.03004)]
    edges = ((0, 1), (1, 2), (2, 0), (0, 3), (2, 3), (1, 3))
    coords = p4 + [tuple((p4[i][k] + p4[j][k]) / 2 for k in range(3)) for i, j in edges]
    names = [(3, 1, "ICE_VOLUME"), (2, 2, "TOP_ROBIN"),
             (2, 3, "BOTTOM_INSULATED"), (2, 4, "X_MINUS"),
             (2, 5, "X_PLUS"), (2, 6, "Y_MINUS"), (2, 7, "Y_PLUS"),
             (2, 8, "PORE_WALL"), (2, 9, "B6_INTERFACE")]
    lines = ["$MeshFormat", "2.2 0 8", "$EndMeshFormat", "$PhysicalNames", "9"]
    lines += [f'{d} {tag} "{name}"' for d, tag, name in names]
    lines += ["$EndPhysicalNames", "$Nodes", "10"]
    lines += [f"{i} " + " ".join(str(v) for v in p) for i, p in enumerate(coords, 1)]
    lines += ["$EndNodes", "$Elements", "9"]
    lines += [f"{i-1} 9 2 {i} {i} 1 2 3 5 6 7" for i in range(2, 10)]
    lines += ["9 11 2 1 1 " + " ".join(map(str, range(1, 11))), "$EndElements"]
    summary, rows = parse(io.StringIO("\n".join(lines) + "\n"))
    assert summary["tet10"] == 1 and summary["tri6"] == 8
    assert not summary["missing_or_misnamed_groups"]
    assert summary["zone_profile"]["100um_5mm"]["tet10"] == 1
    assert summary["curved_qp_nonpositive_count"] == 0
    assert len(rows) == 5 * 10 * 12
    altered = "\n".join(lines).replace('2 9 "B6_INTERFACE"', '2 9 "WRONG_B6"') + "\n"
    wrong, _ = parse(io.StringIO(altered))
    assert "2:9" in wrong["missing_or_misnamed_groups"]
    assert zone_of(-.001) == "corner_centroid_inside_pore"
    print("P10CT_R2_U0_SYNTHETIC_UNIT_OK parser=PASS physical_groups=9 full_curved_QP=27 bins=600 FEM=0 GMSH=0")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--mesh", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--target-size-mm", type=float, default=2.0)
    opt = ap.parse_args()
    if opt.selftest:
        selftest()
        return 0
    if not opt.mesh or not opt.out_dir or not opt.mesh.is_file():
        ap.error("existing --mesh and --out-dir required")
    if not math.isfinite(opt.target_size_mm) or opt.target_size_mm <= 0:
        ap.error("positive target-size-mm required")
    if opt.out_dir.resolve() == opt.mesh.parent.resolve():
        ap.error("audit output directory must differ from mesh directory")
    opt.out_dir.mkdir(parents=True, exist_ok=True)
    with opt.mesh.open("r", encoding="ascii", errors="strict") as inp:
        summary, rows = parse(inp)
    summary["mesh_sha256"] = sha256(opt.mesh)
    summary["target_h_mm"] = opt.target_size_mm
    summary["geometry_only_acceptance"] = bool(not summary["missing_or_misnamed_groups"]
        and summary["corner_det_nonpositive_count"] == 0
        and summary["curved_qp_nonpositive_count"] == 0
        and summary["corner_quality_min"] > 0.02
        and summary["pore_wall_max_radial_node_error_mm"] is not None
        and summary["pore_wall_max_radial_node_error_mm"] < 1e-5)
    summary["flags"] = {
        "nearwall_0_20um_has_tet_centroids": summary["zone_profile"]["0_20um"]["tet10"] > 0,
        "nearwall_20_100um_has_tet_centroids": summary["zone_profile"]["20_100um"]["tet10"] > 0,
        "polar_0_100um_has_tet_centroids": sum(summary["zone_profile"][z]["polar_tet10"] for z in ZONES[:2]) > 0,
    }
    (opt.out_dir / "P10CT_U0_SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (opt.out_dir / "P10CT_U0_3D_SIZE_BINS.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("P10CT_R2_QA_COMPLETE_GEOMETRY_ACCEPTED" if summary["geometry_only_acceptance"] else "P10CT_R2_QA_COMPLETE_GEOMETRY_REJECTED")
    print("U0_TET10=", summary["tet10"], "U0_TRI6=", summary["tri6"],
          "NEGATIVE_CORNER=", summary["corner_det_nonpositive_count"],
          "NEGATIVE_CURVED_SAMPLED=", summary["curved_qp_nonpositive_count"],
          "PHYSICAL_FEM=0")
    return 0  # A completed negative QC is scientific evidence, not a tool failure.


if __name__ == "__main__":
    sys.exit(main())
