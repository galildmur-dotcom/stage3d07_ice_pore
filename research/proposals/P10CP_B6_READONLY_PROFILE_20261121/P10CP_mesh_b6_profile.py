#!/usr/bin/env python3
"""P10CP R1. SHA-gated READ-ONLY B6 mesh-size/straight-corner-quality profile.

Only reads the three original Gmsh 2 ASCII Tet10 .msh sources. NO Gmsh,
mesh production, CMake, FE solves, physical fields, or source mesh writes.
All statistics use corner centroids and *straight* tetrahedral edges/volumes.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import secrets
import sys
import time
import traceback
import zipfile

VERSION = "P10CP_R1_B6_ORIGINAL_MESH_READONLY_SIZE_QUALITY_NO_FEM"
MESHES = (
    ("H4W4B2", "H4W4B2.msh", "3f6bf10717e566c5268e0b716e13c887365e0d3c61e46c156fdbe6ba1aa3d2c7", 367823, 261091, 18518, 29288, 192565, 20720),
    ("H4W4B20", "H4W4B20_P10AB.msh", "94ab3df693265dbb4e7e723eb3c54642f4c385a465d91a1db4436ab66adc6715", 449522, 323052, 18525, 29577, 254258, 20692),
    ("H4W5B2", "H4W5B2_P10AC.msh", "db50a10fc2a12870bf6e678e2ef0be496feba218b1010f9e65f8669f67d093a8", 393998, 275549, 26465, 35331, 192965, 20788),
)
CENTER = (0.0, 0.0, 0.03)  # m, from P10CI original geometry
R_M = 0.001
EDGE_PAIRS = ((0, 1), (1, 2), (2, 0), (0, 3), (2, 3), (1, 3))
RADIAL_SHELLS = 24
POLAR_BANDS = 10
PHI_SECTORS = 12
# Logarithmic radial resolution; B6 support = [0.1, 5.0] mm from wall.
RADIAL_EDGES_MM = tuple(0.1 * (50.0 ** (i / RADIAL_SHELLS)) for i in range(RADIAL_SHELLS + 1))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for piece in iter(lambda: src.read(4 * 1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def quantile(values: list[float], p: float):
    if not values:
        return ""
    a = sorted(values)
    k = p * (len(a) - 1)
    i = int(k)
    return a[i] + (a[min(i + 1, len(a) - 1)] - a[i]) * (k - i)


def xyz_to_d_mu_phi(point):
    xx = point[0] - CENTER[0]
    yy = point[1] - CENTER[1]
    zz = point[2] - CENTER[2]
    radius = math.sqrt(xx * xx + yy * yy + zz * zz)
    if radius <= 0 or not math.isfinite(radius):
        raise ValueError("zero or invalid pore-center radius")
    d_mm = (radius - R_M) * 1000.0
    mu = max(-1.0, min(1.0, zz / radius))
    rho_m = math.hypot(xx, yy)
    phi = math.atan2(yy, xx) % (2.0 * math.pi) if rho_m > 0 else 0.0
    return d_mm, mu, phi, rho_m


def radial_index(d_mm):
    if d_mm < 0.1 or d_mm > 5.0:
        return None
    return min(RADIAL_SHELLS - 1, bisect_right(RADIAL_EDGES_MM, d_mm) - 1)


def polar_index(mu):
    return min(POLAR_BANDS - 1, max(0, int((mu + 1.0) * POLAR_BANDS / 2)))


def phi_index(phi):
    return min(PHI_SECTORS - 1, int(phi * PHI_SECTORS / (2.0 * math.pi)))


def difference(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def length(v):
    return math.sqrt(sum(x * x for x in v))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def corner_geometry(p):
    a, b, c, d = p[:4]
    ab, ac, ad = difference(b, a), difference(c, a), difference(d, a)
    det = sum(x * y for x, y in zip(ab, cross(ac, ad)))
    sides = [length(difference(p[i], p[j])) for i, j in EDGE_PAIRS]
    if not all(math.isfinite(v) and v > 0 for v in sides):
        raise ValueError("invalid/nonpositive corner edge")
    vol = abs(det) / 6.0
    quality = 12.0 * (3.0 * vol) ** (2.0 / 3.0) / sum(v * v for v in sides) if vol > 0 else 0.0
    curve = 0.0
    for k, (i, j) in enumerate(EDGE_PAIRS):
        midpoint = tuple(0.5 * (p[i][u] + p[j][u]) for u in range(3))
        curve = max(curve, length(difference(p[k + 4], midpoint)) / sides[k])
    return {
        "signed_corner_det": det,
        "corner_vol_m3": vol,
        "quality": quality,
        "hmax_mm": max(sides) * 1000,
        "hmin_mm": min(sides) * 1000,
        "hvol_mm": (6.0 * vol) ** (1.0 / 3.0) * 1000,
        "edge_ratio": max(sides) / min(sides),
        "midside_dev_over_edge": curve,
    }


class Stats:
    __slots__ = ("count", "sum_volume", "hmax", "hvol", "qualities", "edge_ratios", "curves", "nonpositive", "low_quality", "cross_r", "cross_mu", "axis_ambiguous")

    def __init__(self):
        self.count = 0
        self.sum_volume = 0.0
        self.hmax = []
        self.hvol = []
        self.qualities = []
        self.edge_ratios = []
        self.curves = []
        self.nonpositive = 0
        self.low_quality = 0
        self.cross_r = 0
        self.cross_mu = 0
        self.axis_ambiguous = 0

    def add(self, geom, radial_cross: bool, mu_cross: bool, unresolved_phi: bool):
        self.count += 1
        self.sum_volume += geom["corner_vol_m3"]
        self.hmax.append(geom["hmax_mm"])
        self.hvol.append(geom["hvol_mm"])
        self.qualities.append(geom["quality"])
        self.edge_ratios.append(geom["edge_ratio"])
        self.curves.append(geom["midside_dev_over_edge"])
        self.nonpositive += geom["signed_corner_det"] <= 0
        self.low_quality += geom["quality"] < 0.1
        self.cross_r += radial_cross
        self.cross_mu += mu_cross
        self.axis_ambiguous += unresolved_phi


def output_stats(mesh, ri, mi, ph, st):
    lo, hi = RADIAL_EDGES_MM[ri:ri + 2]
    out = {
        "mesh": mesh,
        "radial_bin": ri,
        "d_lower_mm": f"{lo:.12g}",
        "d_upper_mm": f"{hi:.12g}",
        "polar_band": mi,
        "mu_lower": f"{-1.0 + 2.0 * mi / POLAR_BANDS:.12g}",
        "mu_upper": f"{-1.0 + 2.0 * (mi + 1) / POLAR_BANDS:.12g}",
        "phi_sector": "" if ph is None else ph,
        "phi_lower_deg": "" if ph is None else 360.0 * ph / PHI_SECTORS,
        "phi_upper_deg": "" if ph is None else 360.0 * (ph + 1) / PHI_SECTORS,
        "tet10_corner_centroids": st.count,
        "sum_corner_volume_m3": f"{st.sum_volume:.12g}",
        "hmax_corner_edge_p05_mm": quantile(st.hmax, 0.05),
        "hmax_corner_edge_p50_mm": quantile(st.hmax, 0.50),
        "hmax_corner_edge_p95_mm": quantile(st.hmax, 0.95),
        "hvol_corner_p50_mm": quantile(st.hvol, 0.5),
        "corner_quality_p05": quantile(st.qualities, 0.05),
        "corner_quality_p50": quantile(st.qualities, 0.5),
        "corner_edge_ratio_p95": quantile(st.edge_ratios, 0.95),
        "midside_deviation_over_edge_p95": quantile(st.curves, 0.95),
        "corner_nonpositive_count": st.nonpositive,
        "corner_quality_lt_0p1_count": st.low_quality,
        "corner_cross_radial_bin_count": st.cross_r,
        "corner_cross_polar_band_count": st.cross_mu,
        "centroid_phi_axis_ambiguous_count": st.axis_ambiguous,
    }
    return out


def skip_section(inp, label):
    end = "$End" + label[1:]
    while True:
        row = inp.readline()
        if not row:
            raise ValueError("unterminated section " + label)
        if row.strip() == end:
            return


def scan_stream(inp):
    """Parse original ASCII MSH2 and collect P10CP region; no writes, no meshing."""
    if inp.readline().strip() != "$MeshFormat":
        raise ValueError("no $MeshFormat marker")
    fmt = inp.readline().split()
    if len(fmt) < 3 or not fmt[0].startswith("2.") or fmt[1] != "0":
        raise ValueError("only Gmsh 2 ASCII supported")
    if inp.readline().strip() != "$EndMeshFormat":
        raise ValueError("bad $EndMeshFormat")
    nodes = None
    node_count = 0
    all_elements = 0
    n_tet10 = 0
    counts = {"0_20um": 0, "20_100um": 0, "100um_5mm": 0, "outside_B6": 0, "inside_pore": 0}
    binned = {}
    elements_seen = False
    while True:
        tag = inp.readline()
        if not tag:
            break
        label = tag.strip()
        if label == "$Nodes":
            if nodes is not None:
                raise ValueError("duplicate $Nodes")
            node_count = int(inp.readline())
            nodes = {}
            for _ in range(node_count):
                fields = inp.readline().split()
                if len(fields) != 4:
                    raise ValueError("bad node row")
                nid = int(fields[0])
                coords = tuple(float(s) for s in fields[1:])
                if nid in nodes or not all(math.isfinite(v) for v in coords):
                    raise ValueError("duplicate/nonfinite node coordinate")
                nodes[nid] = coords
            if inp.readline().strip() != "$EndNodes":
                raise ValueError("bad $EndNodes")
        elif label == "$Elements":
            if nodes is None or elements_seen:
                raise ValueError("nodes missing or duplicate elements section")
            elements_seen = True
            all_elements = int(inp.readline())
            for _ in range(all_elements):
                fields = inp.readline().split()
                if len(fields) < 4:
                    raise ValueError("truncated Gmsh element")
                if int(fields[1]) != 11:
                    continue
                ntags = int(fields[2])
                ids = list(map(int, fields[3 + ntags:]))
                if len(ids) != 10:
                    raise ValueError("expected exactly 10 nodes per Tet10")
                p = [nodes[n] for n in ids]
                n_tet10 += 1
                centroid = tuple(sum(p[k][u] for k in range(4)) / 4.0 for u in range(3))
                d_mm, mu, phi, rho = xyz_to_d_mu_phi(centroid)
                if d_mm < 0:
                    counts["inside_pore"] += 1
                elif d_mm < .02:
                    counts["0_20um"] += 1
                elif d_mm < .1:
                    counts["20_100um"] += 1
                elif d_mm > 5.0:
                    counts["outside_B6"] += 1
                else:
                    counts["100um_5mm"] += 1
                    ri = radial_index(d_mm)
                    if ri is None:
                        raise AssertionError("B6 radial index gap")
                    mi = polar_index(mu)
                    fi = phi_index(phi)
                    geom = corner_geometry(p)
                    corner_angles = [xyz_to_d_mu_phi(corner) for corner in p[:4]]
                    rcross = any(radial_index(c[0]) != ri for c in corner_angles)
                    mcross = any(polar_index(c[1]) != mi for c in corner_angles)
                    unresolved = rho < 1e-12  # m, φ not defined numerically on axis
                    cell_key = (ri, mi, fi)
                    st = binned.get(cell_key)
                    if st is None:
                        st = Stats()
                        binned[cell_key] = st
                    st.add(geom, rcross, mcross, unresolved)
            if inp.readline().strip() != "$EndElements":
                raise ValueError("bad $EndElements")
        elif label.startswith("$") and not label.startswith("$End"):
            skip_section(inp, label)
    if nodes is None or not elements_seen:
        raise ValueError("missing mesh nodes/elements")
    if sum(counts.values()) != n_tet10 or sum(s.count for s in binned.values()) != counts["100um_5mm"]:
        raise ValueError("nonconservative centroid partition")
    return node_count, n_tet10, all_elements, counts, binned


def profiles(mesh, binned):
    fine = []
    coarse = []
    n = 0
    for ri in range(RADIAL_SHELLS):
        for mi in range(POLAR_BANDS):
            sumst = Stats()
            for fi in range(PHI_SECTORS):
                st = binned.get((ri, mi, fi), Stats())
                n += st.count
                fine.append(output_stats(mesh, ri, mi, fi, st))
                sumst.count += st.count
                sumst.sum_volume += st.sum_volume
                sumst.hmax.extend(st.hmax)
                sumst.hvol.extend(st.hvol)
                sumst.qualities.extend(st.qualities)
                sumst.edge_ratios.extend(st.edge_ratios)
                sumst.curves.extend(st.curves)
                sumst.nonpositive += st.nonpositive
                sumst.low_quality += st.low_quality
                sumst.cross_r += st.cross_r
                sumst.cross_mu += st.cross_mu
                sumst.axis_ambiguous += st.axis_ambiguous
            coarse.append(output_stats(mesh, ri, mi, None, sumst))
    return fine, coarse, n


def write_csv(path, rows):
    if not rows:
        raise ValueError("cannot export empty CSV")
    with path.open("w", newline="", encoding="utf-8") as out:
        w = csv.DictWriter(out, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def selftest():
    # Regular Tet10 with exact edge midpoints: objective corner quality = 1.
    a = 0.001
    p = ((0, 0, 0), (a, 0, 0), (a / 2, a * math.sqrt(3) / 2, 0),
         (a / 2, a * math.sqrt(3) / 6, a * math.sqrt(2 / 3)))
    mids = tuple(tuple((p[i][u] + p[j][u]) / 2 for u in range(3)) for i, j in EDGE_PAIRS)
    g = corner_geometry(p + mids)
    assert g["signed_corner_det"] > 0 and abs(g["quality"] - 1) < 1e-12
    assert abs(g["hmax_mm"] - 1) < 1e-12 and g["midside_dev_over_edge"] == 0
    assert radial_index(.1) == 0 and radial_index(5.0) == RADIAL_SHELLS - 1
    assert radial_index(.099999) is None and radial_index(5.000001) is None
    assert polar_index(-1.) == 0 and polar_index(1.) == 9
    assert phi_index(2 * math.pi - 1e-14) == 11 and phi_index(0.) == 0
    # In-memory mini Gmsh2 fixture, never creates even a synthetic .msh file.
    xx = [(.00120, 0., .03), (.00124, 0., .03), (.00120, .00004, .03), (.00120, 0., .03004)]
    xmid = [tuple((xx[i][u] + xx[j][u]) / 2 for u in range(3)) for i, j in EDGE_PAIRS]
    text_mesh = "$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n10\n"
    text_mesh += "".join(str(i) + " " + " ".join(map(str, xyz)) + "\n" for i, xyz in enumerate(xx + xmid, 1))
    text_mesh += "$EndNodes\n$Elements\n1\n1 11 2 1 1 " + " ".join(str(i) for i in range(1, 11)) + "\n$EndElements\n"
    nn, nt, ne, counts, data = scan_stream(io.StringIO(text_mesh))
    assert (nn, nt, ne) == (10, 1, 1)
    assert counts["100um_5mm"] == 1 and sum(counts.values()) == 1
    fine, coarse, total = profiles("SYNTHETIC", data)
    assert total == 1 and len(fine) == 2880 and len(coarse) == 240
    assert sum(row["tet10_corner_centroids"] for row in fine) == total
    assert sum(row["tet10_corner_centroids"] for row in coarse) == total
    assert sum(row["corner_nonpositive_count"] for row in coarse) == 0
    assert quantile([1.0, 3.0], .5) == 2.0
    # A unit in the 20–100um shell must be excluded from the new region.
    altered = text_mesh.replace("0.00124", "0.00106").replace("0.0012", "0.00102")
    _, _, _, counts2, bins2 = scan_stream(io.StringIO(altered))
    assert counts2["20_100um"] == 1 and not bins2
    print("P10CP_UNIT_OK read_only=1 synthetic_mesh_in_memory=1 q_regular=1 bins=24x10x12 partition=PASS FEM=0")


def source_directory_safe(mesh_root, tool_root):
    # Prevent any output within the Windows Stage3D07 project or source meshes.
    parent = mesh_root.resolve().parent
    tool = tool_root.resolve()
    return (tool.drive.casefold() not in ("g:", "f:")
            and tool != parent and parent not in tool.parents)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--mesh-root", type=Path)
    opt = parser.parse_args()
    if opt.selftest:
        selftest()
        return 0
    if opt.mesh_root is None:
        parser.error("--mesh-root required for Windows source-mesh read-only audit")
    root = Path(__file__).resolve().parent
    source = opt.mesh_root.resolve()
    if not source_directory_safe(source, root):
        print("RESULT=P10CP_STOP_OUTPUT_INSIDE_SOURCE_PROJECT (no writes)", flush=True)
        return 2
    run_base = root / "P10CP_RUNS"
    if run_base.exists() and any(run_base.iterdir()):
        print("RESULT=P10CP_STOP_ALREADY_ATTEMPTED_IN_THIS_TOOL_DIRECTORY", flush=True)
        return 2
    run_base.mkdir(exist_ok=True)
    out = run_base / (datetime.now(timezone.utc).strftime("P10CP_%Y%m%d_%H%M%S_UTC_") + secrets.token_hex(3))
    out.mkdir(exist_ok=False)
    status = "P10CP_READONLY_STOP_NO_FEM"
    began = time.perf_counter()
    lines = ["TOOL_REVISION=" + VERSION, "SOURCE_MESH_WRITES=0", "GMSH_CALLS=0", "NEW_MSH_FILES=0", "FEM_RUNS=0", "EXPECTED_MESHES=3", "RADIAL=24_LOG_BINS_0.1_TO_5_MM", "POLAR=10_EQUAL_MU_BINS", "PHI=12_EQUAL_DEG_SECTORS", "CLASSIFICATION=CORNER_CENTROID_NOT_CURVED_TET10_QP"]
    try:
        if not source.is_dir():
            raise FileNotFoundError("expected source mesh directory absent")
        identity = []
        # SHA-gate ALL three meshes before expensive parsing; never use substitutes.
        for name, filename, expected, nnode, ntet, n0, n1, nb6, noutside in MESHES:
            path = source / filename
            if not path.is_file():
                raise FileNotFoundError("missing pinned original mesh " + filename)
            observed = sha256_file(path)
            if observed != expected:
                raise ValueError(name + " original mesh SHA-256 mismatch: STOP")
            identity.append({"mesh": name, "filename": filename, "sha256": observed, "expected_nodes": nnode, "expected_tet10": ntet})
        lines.append("PINNED_RAW_MESH_SHA256=PASS_3_OF_3")
        all_coarse = []
        all_fine = []
        summaries = []
        for name, filename, sha, nnode, ntet, n0, n1, nb6, noutside in MESHES:
            started = time.perf_counter()
            with (source / filename).open("r", encoding="utf-8", errors="strict") as inp:
                actual_nodes, actual_tets, nelem, counts, binned = scan_stream(inp)
            got_counts = [counts["0_20um"], counts["20_100um"], counts["100um_5mm"], counts["outside_B6"]]
            if (actual_nodes, actual_tets) != (nnode, ntet) or got_counts != [n0, n1, nb6, noutside] or counts["inside_pore"] != 0:
                raise ValueError(name + " original count/category mismatch: STOP; got " + str((actual_nodes, actual_tets, counts)))
            fine, coarse, coverage = profiles(name, binned)
            if coverage != nb6 or len(fine) != 2880 or len(coarse) != 240:
                raise AssertionError("nonconservative P10CP bins " + name)
            q_low = sum(r["corner_quality_lt_0p1_count"] for r in fine)
            nonpositive = sum(r["corner_nonpositive_count"] for r in fine)
            summaries.append({"mesh": name, "mesh_sha256": sha, "node_count": actual_nodes, "tet10_count": actual_tets, "all_element_records": nelem, "tet10_0_20um": n0, "tet10_20_100um": n1, "tet10_100um_5mm": coverage, "tet10_outside_B6": noutside, "corner_nonpositive_count_100um_5mm": nonpositive, "corner_quality_lt_0p1_count_100um_5mm": q_low, "seconds": round(time.perf_counter() - started, 3)})
            all_fine.extend(fine)
            all_coarse.extend(coarse)
            del binned, fine, coarse
            print(name + ": SHA/COUNTS_PASS, "+str(coverage)+" centroid Tet10 in 0.1–5mm, corner_nonpositive="+str(nonpositive), flush=True)
        write_csv(out / "P10CP_MESH_SUMMARY.csv", summaries)
        write_csv(out / "P10CP_MERIDIONAL_720CELL_PROFILE.csv", all_coarse)
        write_csv(out / "P10CP_3D_8640CELL_PROFILE.csv", all_fine)
        sha_table = {f.name: sha256_file(f) for f in sorted(out.glob("*.csv"))}
        manifest = {"revision": VERSION, "source": "3 raw pinned original meshes", "pore_radius_m": R_M, "pore_center_m": CENTER, "binning": {"radial_mm": list(RADIAL_EDGES_MM), "mu_bounds": [-1 + 0.2 * k for k in range(11)], "phi_sector_degrees": 30, "bounds": "0.1<=d<=5.0mm; centroid classification; lower/upper half-open except final radial upper inclusive"}, "metrics": "exact per-cell corner-edge/quality quantiles; straight-sided corner-Tet only; not Gmsh prescribed h0, not curved Tet10 QP", "input_hashes": identity, "csv_sha256": sha_table, "FEM_runs": 0, "gmsh_calls": 0}
        (out / "P10CP_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lines += ["NODE_TET10_CATEGORY_COUNTS=PASS_3_OF_3", "TET10_RADIAL_MU_PHI_PARTITION=PASS_3_OF_3", "SUMMARY_ROWS=3", "MERIDIONAL_ROWS=720", "SPHERICAL_3D_ROWS=8640", "CURVED_TET10_QP_POSITIVITY=NOT_TESTED", "H0_GMSH_SIZE_FIELD=NOT_RECONSTRUCTED", "FULL_4D_DERIVATIVE=NOT_AVAILABLE", "PHYSICAL_M1_MESH_GENERATED=NO", "M1_RESOURCE_FORECAST=NOT_CALIBRATED"]
        status = "P10CP_ORIGINAL_B6_MESH_PROFILE_OK_NO_FEM"
    except Exception as exc:
        lines += ["STOP_TYPE=" + type(exc).__name__, "STOP_REASON=" + str(exc)]
        (out / "P10CP_STOP_TRACE.txt").write_text(traceback.format_exc(), encoding="utf-8")
    lines += ["WALL_SECONDS=" + str(round(time.perf_counter() - began, 3)), "RESULT=" + status]
    (out / "P10CP_RESULT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with zipfile.ZipFile(out / "P10CP_EVIDENCE.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(out.iterdir()):
            if f.is_file() and f.name != "P10CP_EVIDENCE.zip":
                z.write(f, f.name)
    print("RESULT=" + status, flush=True)
    print("EVIDENCE=" + str(out / "P10CP_EVIDENCE.zip"), flush=True)
    return 0 if status == "P10CP_ORIGINAL_B6_MESH_PROFILE_OK_NO_FEM" else 2


if __name__ == "__main__":
    sys.exit(main())
