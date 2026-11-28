#!/usr/bin/env python3
"""P10CX: independent stdlib-only MSH2 Tri6 pore surface check. NO FEM."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

VERSION = "P10CX_R1_WINDOWS_2D_PORE_SURFACE_ONLY"
CENTER = (0., 0., .03)
R = .001


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def xyz_spherical(point):
    dx, dy, dz = (point[i] - CENTER[i] for i in range(3))
    rr = math.sqrt(dx*dx + dy*dy + dz*dz)
    if rr <= 0:
        raise ValueError("zero radius")
    mu = max(-1., min(1., dz/rr))
    phi = (math.atan2(dy, dx) % (2*math.pi)) if (dx or dy) else 0.
    return (min(9, int((mu+1)*5)), min(11, int(phi*6/math.pi)), mu, phi)


def triangle(corners):
    a, b, c = corners
    ab = tuple(a[i]-b[i] for i in range(3))
    bc = tuple(b[i]-c[i] for i in range(3))
    ca = tuple(c[i]-a[i] for i in range(3))
    edges = [math.sqrt(sum(x*x for x in vec)) for vec in (ab, bc, ca)]
    cross = (ab[1]*ca[2]-ab[2]*ca[1], ab[2]*ca[0]-ab[0]*ca[2], ab[0]*ca[1]-ab[1]*ca[0])
    area = .5*math.sqrt(sum(x*x for x in cross))
    q = 4*math.sqrt(3)*area/sum(e*e for e in edges) if sum(e*e for e in edges) else 0.
    return edges, area, q


def percentile(values, fraction):
    s = sorted(values)
    pos = fraction*(len(s)-1)
    lo = int(pos)
    hi = min(lo+1, len(s)-1)
    return s[lo] + (s[hi]-s[lo])*(pos-lo)


def parse_msh(stream):
    if stream.readline().strip() != "$MeshFormat":
        raise ValueError("MSH2 header missing")
    fmt = stream.readline().split()
    if len(fmt) != 3 or fmt[0] != "2.2" or fmt[1] != "0":
        raise ValueError("MSH2.2 ASCII required")
    if stream.readline().strip() != "$EndMeshFormat":
        raise ValueError("MSH2 header not closed")
    nodes, physicals, wall, n_all = {}, {}, [], 0
    seen = set()
    for line in stream:
        token = line.strip()
        if token == "$PhysicalNames":
            if "physical" in seen:
                raise ValueError("duplicate PhysicalNames")
            seen.add("physical")
            n = int(stream.readline())
            for _ in range(n):
                row = stream.readline().split(maxsplit=2)
                if len(row) != 3:
                    raise ValueError("bad PhysicalNames row")
                physicals[(int(row[0]), int(row[1]))] = row[2].strip().strip('"')
            if stream.readline().strip() != "$EndPhysicalNames":
                raise ValueError("PhysicalNames unclosed")
        elif token == "$Nodes":
            if "nodes" in seen:
                raise ValueError("duplicate Nodes")
            seen.add("nodes")
            n = int(stream.readline())
            for _ in range(n):
                row = stream.readline().split()
                if len(row) != 4:
                    raise ValueError("bad Node row")
                key = int(row[0])
                p = tuple(float(v) for v in row[1:])
                if key in nodes or not all(map(math.isfinite, p)):
                    raise ValueError("duplicated/nonfinite Node")
                nodes[key] = p
            if stream.readline().strip() != "$EndNodes":
                raise ValueError("Nodes unclosed")
        elif token == "$Elements":
            if "elements" in seen:
                raise ValueError("duplicate Elements")
            seen.add("elements")
            n_all = int(stream.readline())
            for _ in range(n_all):
                row = [int(v) for v in stream.readline().split()]
                if len(row) < 4:
                    raise ValueError("short Element row")
                kind, ntags = row[1], row[2]
                if len(row) < 3+ntags:
                    raise ValueError("Element tags truncated")
                physical = row[3] if ntags else None
                if physical == 8:
                    if kind != 9 or len(row) != 3+ntags+6:
                        raise ValueError("PORE_WALL not Tri6")
                    wall.append(row[3+ntags:])
            if stream.readline().strip() != "$EndElements":
                raise ValueError("Elements unclosed")
        elif token.startswith("$") and not token.startswith("$End"):
            end = "$End" + token[1:]
            for item in stream:
                if item.strip() == end:
                    break
            else:
                raise ValueError("unclosed section " + token)
    if physicals.get((2, 8)) != "PORE_WALL":
        raise ValueError("physical PORE_WALL missing")
    if not nodes or not wall or not n_all:
        raise ValueError("no Nodes/Elements/Tri6 pore")
    return nodes, wall, n_all, physicals


def analyze(nodes, wall, n_all, physicals, mesh_sha):
    sizes, qualities, polar_sizes, middle_sizes = [], [], [], []
    bins = {(i, j): {"count": 0, "area": 0.0, "sizes": []} for i in range(10) for j in range(12)}
    area_total, polar_area, nonpositive, rad_max = 0., 0., 0, 0.
    worst = None
    for number, node_ids in enumerate(wall):
        pt = [nodes[i] for i in node_ids]
        edges, area, q = triangle(pt[:3])
        if area <= 0:
            nonpositive += 1
        mean = tuple(sum(p[i] for p in pt[:3])/3 for i in range(3))
        mi, pi, mu, phi = xyz_spherical(mean)
        h = max(edges)
        sizes.append(h)
        qualities.append(q)
        entry = bins[(mi, pi)]
        entry["count"] += 1
        entry["area"] += area
        entry["sizes"].append(h)
        area_total += area
        if mi in (0, 9):
            polar_sizes.append(h)
            polar_area += area
        else:
            middle_sizes.append(h)
        for p in pt:
            rad_max = max(rad_max, abs(math.dist(p, CENTER)-R))
        if worst is None or q < worst["corner_quality"]:
            worst = {"tri6_element_sequence": number, "corner_quality": q,
                     "mu_bin": mi, "phi_bin": pi, "mu": mu, "phi_deg": phi*180/math.pi,
                     "corner_edge_um": [e*1e6 for e in edges],
                     "corner_centroid_mm": [v*1e3 for v in mean]}
    rows = []
    for (i, j), v in sorted(bins.items()):
        rows.append({"mu_bin": i, "phi_bin": j, "tri6_count": v["count"],
                     "chord_area_mm2": v["area"]*1e6,
                     "hmax_p50_um": percentile(v["sizes"], .5)*1e6 if v["count"] else None})
    result = {"tool_revision": VERSION, "result": "P10CX_SURFACE_QA_COMPLETE_NO_3D_NO_FEM",
              "input_msh_sha256": mesh_sha, "nodes": len(nodes), "all_elements": n_all,
              "pore_tri6": len(wall), "all_angular_bins_occupied": all(r["tri6_count"] for r in rows),
              "pore_chord_area_mm2": area_total*1e6,
              "area_rel_to_cad_sphere": (area_total - 4*math.pi*R**2)/(4*math.pi*R**2),
              "hmax_um_p5_p50_p95": [percentile(sizes,x)*1e6 for x in (.05,.5,.95)],
              "quality_p5_p50_p95": [percentile(qualities,x) for x in (.05,.5,.95)],
              "min_corner_quality": min(qualities),
              "below_q0p1": sum(q<.1 for q in qualities),
              "below_q0p2": sum(q<.2 for q in qualities),
              "nonpositive_area": nonpositive,
              "max_radial_node_error_um": rad_max*1e6,
              "polar_area_fraction": polar_area/area_total,
              "polar_vs_mid_hmedian_ratio": percentile(polar_sizes,.5)/percentile(middle_sizes,.5),
              "worst_tri6": worst, "angular_rows": rows}
    if sum(x["tri6_count"] for x in rows) != len(wall) or nonpositive or not all(r["tri6_count"] for r in rows):
        raise ValueError("failed partition/area/coverage checks")
    return result


def selftest():
    a,b,c = (0,0,0),(1,0,0),(.5,math.sqrt(3)/2,0)
    _, area, q = triangle([a,b,c])
    assert abs(area-math.sqrt(3)/4)<1e-14 and abs(q-1)<1e-14
    assert xyz_spherical((0,0,.029))[0] == 0
    assert xyz_spherical((0,0,.031))[0] == 9
    assert abs(percentile([0,10],.5)-5)<1e-14
    print("P10CX_SYNTHETIC_UNIT_OK")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--mesh", type=Path)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    if args.mesh is None or args.out_dir is None:
        parser.error("--mesh and --out-dir required")
    with args.mesh.open("r", encoding="ascii") as stream:
        nodes, wall, n_all, physicals = parse_msh(stream)
    result = analyze(nodes, wall, n_all, physicals, sha(args.mesh))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir/"P10CX_SURFACE_QA.json").write_text(json.dumps(result, indent=2)+"\n",encoding="utf-8")
    with (args.out_dir/"P10CX_ANGULAR_120.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=["mu_bin","phi_bin","tri6_count","chord_area_mm2","hmax_p50_um"])
        writer.writeheader()
        writer.writerows(result["angular_rows"])
    print(f"P10CX_SURFACE_QA_OK pore_tri6={result['pore_tri6']} qmin={result['min_corner_quality']:.9g} "
          f"bad_q0p1={result['below_q0p1']} polar_h_ratio={result['polar_vs_mid_hmedian_ratio']:.9g}")


if __name__ == "__main__":
    main()
