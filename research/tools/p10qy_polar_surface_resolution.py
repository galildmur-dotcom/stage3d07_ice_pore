#!/usr/bin/env python3
"""P10QY: audit actual M20/M21 curved pore-surface resolution in fine polar caps.

Example:
  python research/tools/p10qy_polar_surface_resolution.py \
    --m20 P10PK_M20_COMPLETE_MESH_AND_AUDIT_EVIDENCE.zip \
    --m21 P10PO_M21_COMPLETE_MESH_AND_AUDIT_EVIDENCE.zip

Reads original accepted meshes in evidence ZIPs; never changes meshes or runs
Gmsh/FEM. Corner-to-corner Tri6 edges quantify *spatial FE resolution*, not
error in the physical derivative. Quadratic midside nodes are not counted as
independent elements. Results describe actual geometry, not 4D angular bins.
"""

import argparse
import hashlib
import json
import math
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path


DATA = {
    "M20": {
        "mesh_name": "P10PK_M20_HIGHORDERELASTIC_UNVERIFIED.msh",
        "sha256": "b568adac49d19f561f8ee6d4c420ff10df51ae32cb8d2e2c1ba46af28d78f8a5",
        "nodes": 61446,
        "pore_tri6": 5598,
    },
    "M21": {
        "mesh_name": "P10PO_M21_HIGHORDERELASTIC_UNVERIFIED.msh",
        "sha256": "0908d7f66e3db2e3880089f245872a854c22f67dc6bee3ec87924131e7039dee",
        "nodes": 65231,
        "pore_tri6": 6048,
    },
}
BANDS = [(0, 1), (1, 2), (0, 2), (2, 5), (5, 8), (0, 8),
         (8, 10), (0, 10), (10, 20), (20, 30), (30, 40)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def length(a):
    return math.sqrt(dot(a, a))


def fit_sphere(points):
    # Centered least-squares avoids poor conditioning for millimetre geometry.
    avg = tuple(math.fsum(p[i] for p in points) / len(points) for i in range(3))
    avg_r2 = math.fsum(dot(p, p) for p in points) / len(points)
    a = [[0.0] * 3 for _ in range(3)]
    rhs = [0.0] * 3
    for p in points:
        d = sub(p, avg)
        r2 = dot(p, p) - avg_r2
        for i in range(3):
            rhs[i] += 0.5 * d[i] * r2
            for j in range(3):
                a[i][j] += d[i] * d[j]
    mat = [a[i][:] + [rhs[i]] for i in range(3)]
    for j in range(3):
        k = max(range(j, 3), key=lambda i: abs(mat[i][j]))
        mat[k], mat[j] = mat[j], mat[k]
        if abs(mat[j][j]) < 1e-30:
            raise ValueError("Degenerate sphere least-squares fit")
        pivot = mat[j][j]
        for n in range(j, 4):
            mat[j][n] /= pivot
        for i in range(j + 1, 3):
            fac = mat[i][j]
            for n in range(j, 4):
                mat[i][n] -= fac * mat[j][n]
    center = [0.0] * 3
    for j in range(2, -1, -1):
        center[j] = mat[j][3] - sum(mat[j][i] * center[i] for i in range(j + 1, 3))
    center = tuple(center)
    radii = [length(sub(p, center)) for p in points]
    rad = statistics.mean(radii)
    residual = max(abs(v - rad) for v in radii)
    return center, rad, residual


def load_pore(zip_path, label):
    info = DATA[label]
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP CRC failure: " + str(zip_path))
        raw = z.read(info["mesh_name"])
        sha = hashlib.sha256(raw).hexdigest()
        if sha != info["sha256"]:
            raise ValueError(f"{label} accepted optimized mesh SHA mismatch: {sha}")
    lines = iter(raw.decode("utf-8").splitlines())
    nodes = {}
    tri = []
    for line in lines:
        if line == "$Nodes":
            count = int(next(lines))
            for _ in range(count):
                parts = next(lines).split()
                nodes[int(parts[0])] = tuple(map(float, parts[1:4]))
        if line == "$Elements":
            count = int(next(lines))
            for _ in range(count):
                parts = list(map(int, next(lines).split()))
                typ, tag_count = parts[1:3]
                tags = parts[3:3 + tag_count]
                if typ == 9 and tags and tags[0] == 8:
                    ids = tuple(parts[3 + tag_count:])
                    if len(ids) != 6:
                        raise ValueError("Malformed pore Tri6")
                    tri.append(ids)
    if len(nodes) != info["nodes"] or len(tri) != info["pore_tri6"]:
        raise ValueError(f"Unexpected {label} nodes or pore Tri6 counts")
    corners = sorted({nid for t in tri for nid in t[:3]})
    center, radius, residual = fit_sphere([nodes[nid] for nid in corners])
    if residual / radius > 5e-5:
        raise ValueError(f"Pore corner nodes not near a sphere: residual={residual}")
    return nodes, tri, center, radius, residual, sha, len(corners)


def audit(zip_path, label):
    nodes, tri, center, radius, residual, sha, corner_count = load_pore(zip_path, label)
    theta = {}
    hemisphere = {}
    for t in tri:
        for nid in t[:3]:
            if nid not in theta:
                d = sub(nodes[nid], center)
                cos_t = max(-1, min(1, d[2] / length(d)))
                theta[nid] = math.degrees(math.acos(abs(cos_t)))
                hemisphere[nid] = "north" if d[2] >= 0 else "south"
    edges = set()
    for t in tri:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            edges.add(tuple(sorted((a, b))))
    records = {}
    for pole in ("north", "south"):
        corner_set = {nid for nid in theta if hemisphere[nid] == pole}
        counts = {}
        for low, high in BANDS:
            nodes_band = [nid for nid in corner_set if low <= theta[nid] < high]
            lengths = []
            for a, b in edges:
                mid = tuple((nodes[a][i] + nodes[b][i]) * 0.5 for i in range(3))
                d = sub(mid, center)
                mid_t = math.degrees(math.acos(max(-1, min(1, abs(d[2]) / length(d)))))
                mid_pole = "north" if d[2] >= 0 else "south"
                if mid_pole == pole and low <= mid_t < high:
                    lengths.append(length(sub(nodes[a], nodes[b])))
            # Tri6 P2 centroid at barycentric (1/3,1/3,1/3).
            tris = 0
            for t in tri:
                centroid = tuple((-math.fsum(nodes[nid][i] for nid in t[:3])
                                  + 4 * math.fsum(nodes[nid][i] for nid in t[3:])) / 9
                                 for i in range(3))
                d = sub(centroid, center)
                angle = math.degrees(math.acos(max(-1, min(1, abs(d[2]) / length(d)))))
                h = "north" if d[2] >= 0 else "south"
                if h == pole and low <= angle < high:
                    tris += 1
            counts[f"{low}_{high}"] = {
                "corner_vertices": len(nodes_band),
                "tri6_centroids": tris,
                "unique_corner_edges_by_midpoint": len(lengths),
                "median_corner_edge_um": statistics.median(lengths) * 1e6 if lengths else None,
            }
        core_nodes = [nid for nid in corner_set if theta[nid] < 8]
        core_edges = [e for e in edges if e[0] in core_nodes and e[1] in core_nodes]
        med_core = statistics.median(length(sub(nodes[a], nodes[b])) for a, b in core_edges) if core_edges else None
        crossing = sum(1 for a, b in edges
                       if (a in corner_set and b in corner_set and
                           (theta[a] < 8) != (theta[b] < 8)))
        records[pole] = {
            "vertices_below_8deg": len(core_nodes),
            "whole_edges_below_8deg": len(core_edges),
            "crossing_edges_at_8deg": crossing,
            "median_whole_edge_below_8_um": med_core * 1e6 if med_core else None,
            "meridian_arc_0_to_8_um": radius * math.radians(8) * 1e6,
            "estimated_meridian_steps_to_8": radius * math.radians(8) / med_core if med_core else None,
            "bands": counts,
        }
    return {
        "mesh": label, "mesh_sha256": sha,
        "pore_radius_mm": radius * 1e3,
        "fitted_center_mm": [x * 1e3 for x in center],
        "max_sphere_fit_radial_residual_um": residual * 1e6,
        "pore_tri6": len(tri), "pore_corner_vertices": corner_count,
        "polar_resolution": records,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--m20", required=True, type=Path)
    p.add_argument("--m21", required=True, type=Path)
    args = p.parse_args()
    result = {"protocol": "P10QY_REAL_M20_M21_POLE_SURFACE_RESOLUTION_READ_ONLY",
              "status": "PASS_ACCEPTED_MESH_SHA_CRC_FINE_CAP_AUDIT",
              "note": "Corner edge median is a resolution indicator, not a FE truncation/error estimate.",
              "meshes": {"M20": audit(args.m20, "M20"), "M21": audit(args.m21, "M21")}}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
