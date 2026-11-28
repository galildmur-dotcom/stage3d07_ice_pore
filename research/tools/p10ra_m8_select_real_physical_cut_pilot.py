#!/usr/bin/env python3
"""P10RA: select actual M8 wall Tet10 for a selective physical Algoim A/B pilot.

Reads the immutable accepted-M8 *Windows source* ZIP and original *physical*
ZIP. It performs no PDE replay, Gmsh, quadrature or fabricated FE evaluation.
The signed4D CSV has bin totals, NOT per-element physical integrands: do not
attribute the bin totals to a specific selected Tet10.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path


M8_SHA = "40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
CENTER = (0.0, 0.0, 0.030)
RADIUS = 0.001


def load_m8(source_path):
    with zipfile.ZipFile(source_path) as z:
        if z.testzip() is not None:
            raise ValueError("M8 package ZIP CRC failure")
        raw = z.read("P10KV_WORK/M8.msh")
    if hashlib.sha256(raw).hexdigest() != M8_SHA:
        raise ValueError("Not the accepted physical M8 mesh")
    nodes, tets, pore_faces = {}, {}, {}
    lines = iter(raw.decode("utf-8").splitlines())
    for line in lines:
        if line == "$Nodes":
            for _ in range(int(next(lines))):
                p = next(lines).split()
                nodes[int(p[0])] = tuple(map(float, p[1:4]))
        elif line == "$Elements":
            for _ in range(int(next(lines))):
                p = list(map(int, next(lines).split()))
                element_id, kind, tag_count = p[:3]
                physical = p[3] if tag_count else -1
                ids = tuple(p[3 + tag_count:])
                if kind == 11 and physical == 1:
                    tets[element_id] = ids
                elif kind == 9 and physical == 8:
                    pore_faces[element_id] = ids
    if (len(nodes), len(tets), len(pore_faces)) != (18331, 12546, 648):
        raise ValueError("M8 Tet10/pore Tri6 topology mismatch")
    return nodes, tets, pore_faces


def polar_angle(x):
    d = tuple(x[i] - CENTER[i] for i in range(3))
    length = math.sqrt(sum(v * v for v in d))
    if length == 0:
        raise ValueError("Point at pore center")
    return math.degrees(math.acos(max(-1.0, min(1.0, abs(d[2]) / length))))


def polar_side(x):
    return "north" if x[2] >= CENTER[2] else "south"


def p2_center(coords):
    # Tri6 quadratic shape at L1=L2=L3=1/3: corners -1/9, edges +4/9.
    return tuple((4 * math.fsum(x[i] for x in coords[3:])
                  - math.fsum(x[i] for x in coords[:3])) / 9 for i in range(3))


def selected_wall_tets(nodes, tets, faces):
    ordinal = {tid: i for i, tid in enumerate(tets)}
    face_to_tet = defaultdict(list)
    for tid, ids in tets.items():
        if len(ids) != 10:
            raise ValueError(f"Tet10 {tid} has unexpected topology")
        a, b, c, d = ids[:4]
        for triplet in ((a, b, c), (a, b, d), (a, c, d), (b, c, d)):
            face_to_tet[tuple(sorted(triplet))].append(tid)
    if any(len(neighbours) > 2 for neighbours in face_to_tet.values()):
        raise ValueError("Nonmanifold Tet10 face adjacency")

    wall = defaultdict(list)
    for fid, ids in faces.items():
        if len(ids) != 6:
            raise ValueError(f"Malformed pore Tri6 {fid}")
        match = face_to_tet.get(tuple(sorted(ids[:3])), [])
        if len(match) != 1:
            raise ValueError(f"Pore face {fid} has {len(match)} adjacent Tet10")
        coords = [nodes[nid] for nid in ids]
        radius_deviation = max(abs(math.dist(x, CENTER) - RADIUS) for x in coords[:3])
        if radius_deviation > 5e-8:
            raise ValueError(f"Pore face {fid} off expected spherical wall")
        x = p2_center(coords)
        side = polar_side(x)
        angle = polar_angle(x)
        min_angle = min(polar_angle(y) for y in coords)
        azimuth = math.atan2(x[1] - CENTER[1], x[0] - CENTER[0])
        phi_bin = min(11, max(0, int((azimuth + math.pi) * 12 / (2 * math.pi))))
        wall[match[0]].append({
            "pore_face_gmsh_id": fid, "pole": side,
            "face_center_angle_deg": angle,
            "face_minimum_node_angle_deg": min_angle,
            "phi_bin_at_face_center": phi_bin,
        })
    if len(wall) < 250:
        raise ValueError("Unexpectedly few pore-adjacent tetrahedra")

    rows = []
    for tid, details in wall.items():
        for pole in ("north", "south"):
            own = [d for d in details if d["pole"] == pole]
            if not own:
                continue
            minimum = min(d["face_minimum_node_angle_deg"] for d in own)
            middle = min(d["face_center_angle_deg"] for d in own)
            if minimum < 8:
                zone = "core_0_8deg"
            elif minimum < 23:
                zone = "halo_8_23deg"
            else:
                continue
            rows.append({
                "tet10_gmsh_element_id": tid,
                "tet10_msh_volume_ordinal_zero_based": ordinal[tid],
                "pole": pole,
                "zone": zone,
                "minimum_pore_face_node_angle_deg": minimum,
                "nearest_pore_face_center_angle_deg": middle,
                "pore_faces": sorted(own, key=lambda d: d["pore_face_gmsh_id"]),
            })

    # Deterministic, geometrically selected control: two wall-adjacent Tet10
    # near 30 degrees at each pole, outside the expensive pilot caps.
    for pole in ("north", "south"):
        available = []
        for tid, details in wall.items():
            own = [d for d in details if d["pole"] == pole]
            if not own:
                continue
            angle = min(d["face_center_angle_deg"] for d in own)
            if angle >= 23:
                available.append((abs(angle - 30), tid, angle, own))
        for _, tid, angle, own in sorted(available)[:2]:
            rows.append({
                "tet10_gmsh_element_id": tid,
                "tet10_msh_volume_ordinal_zero_based": ordinal[tid],
                "pole": pole,
                "zone": "gauss_control_near_30deg", "minimum_pore_face_node_angle_deg": min(
                    d["face_minimum_node_angle_deg"] for d in own),
                "nearest_pore_face_center_angle_deg": angle,
                "pore_faces": sorted(own, key=lambda d: d["pore_face_gmsh_id"]),
            })
    return sorted(rows, key=lambda r: (r["zone"], r["pole"], r["tet10_gmsh_element_id"])), len(wall)


def physical_signed4d(original_zip):
    by_bin = defaultdict(list)
    total = 0.0
    count = 0
    with zipfile.ZipFile(original_zip) as z:
        if z.testzip() is not None:
            raise ValueError("M8 physical evidence ZIP CRC failure")
        m = json.loads(z.read("P10KV_MANIFEST.json"))
        if m.get("mesh_sha256") != M8_SHA or m.get("native_exit_code") != 0:
            raise ValueError("M8 physical run not accepted")
        with z.open("P10DD_SIGNED_R_THETA_PHI_T.csv") as raw:
            for row in csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline="")):
                val = float(row["total_per_m"])
                total += val
                count += 1
                if (row["region"] == "VOLUME" and int(row["radial_bin"]) == 0
                        and int(row["mu_bin"]) in (0, 9)):
                    key = (int(row["mu_bin"]), int(row["phi_bin"]))
                    by_bin[key].append({
                        "step": int(row["step"]),
                        "mechanical_per_m": float(row["mechanical_total_per_m"]),
                        "thermal_per_m": float(row["thermal_total_per_m"]),
                        "total_per_m": val,
                    })
    expected = m["independent_4d"]["jpeak_derivative_per_m"]
    if count != 43236 or abs(total - expected) > 1e-8 or len(by_bin) != 24:
        raise ValueError("Real M8 signed4D does not close")
    selected = []
    for (mu, phi), rows in sorted(by_bin.items()):
        if len(rows) != 36 or {x["step"] for x in rows} != set(range(1, 37)):
            raise ValueError("Incomplete physical time series")
        selected.append({
            "mu_bin": mu, "phi_bin": phi,
            "actual_mechanical_signed_per_m": math.fsum(x["mechanical_per_m"] for x in rows),
            "actual_thermal_signed_per_m": math.fsum(x["thermal_per_m"] for x in rows),
            "actual_total_signed_per_m": math.fsum(x["total_per_m"] for x in rows),
            "actual_total_abs_4d_L1_per_m": math.fsum(abs(x["total_per_m"]) for x in rows),
        })
    return total, selected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-package", required=True, type=Path)
    p.add_argument("--physical-evidence", required=True, type=Path)
    p.add_argument("--compact", action="store_true", help="Only element ids, polar angles, zone and compact physical bins")
    p.add_argument("--pilot-only", action="store_true", help="List only core and independent Gauss controls; retain halo count")
    args = p.parse_args()
    nodes, tets, faces = load_m8(args.source_package)
    selected, wall_tets = selected_wall_tets(nodes, tets, faces)
    total, polar_physics = physical_signed4d(args.physical_evidence)
    zone_counts = {zone: sum(x["zone"] == zone for x in selected)
                   for zone in ("core_0_8deg", "halo_8_23deg", "gauss_control_near_30deg")}
    if args.pilot_only:
        selected = [x for x in selected if x["zone"] != "halo_8_23deg"]
    if args.compact:
        selected = [{"tet10_gmsh_element_id": x["tet10_gmsh_element_id"],
                     "tet10_msh_volume_ordinal_zero_based": x["tet10_msh_volume_ordinal_zero_based"],
                     "pole": x["pole"], "zone": x["zone"],
                     "nearest_pore_face_center_angle_deg": x["nearest_pore_face_center_angle_deg"]}
                    for x in selected]
    print(json.dumps({
        "protocol": "P10RA_ACCEPTED_M8_REAL_PHYSICAL_SELECTIVE_ALGOIM_PILOT_READ_ONLY",
        "status": "PASS_M8_MESH_FACE_ADJACENCY_AND_PHYSICAL_CLOSURE_SELECTION_ONLY",
        "mesh_sha256": M8_SHA,
        "physical_global_D_R_jpeak_per_m": total,
        "mesh_tet10_count": len(tets),
        "mesh_pore_tri6_count": len(faces),
        "pore_adjacent_unique_tet10": wall_tets,
        "zone_counts": zone_counts,
        "listed_pilot_tet10": len(selected),
        "selected_tet10": selected,
        "r0_polar_real_4d_bin_contributions": polar_physics,
        "warning": "Bin totals are real physical results but CANNOT be assigned to individual selected Tet10. "
                   "The archived ZIP lacks physical QP integrand/state/adjoint values. "
                   "No Algoim evaluation, altered FEM quadrature, or A/B derivative is claimed.",
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
