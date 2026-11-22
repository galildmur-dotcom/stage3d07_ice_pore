#!/usr/bin/env python3
"""Independent dense curved-Tet10 geometry audit of an observed P10FP M0.

Read-only, Linux diagnostic, no Gmsh or FEM. Requires NumPy; uses the
reviewed P10CK Gmsh node ordering and 7^3/9^3 Duffy Gauss-Legendre points.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/proposals/P10FP_FROM_M0_WINDOWS_20261122"))
from P10CK_curved_qp_audit import shape  # noqa: E402


def load_mesh(path):
    nodes = {}
    tets = []
    boundary = {k: set() for k in range(2, 10)}
    tri_count = {k: 0 for k in range(2, 10)}
    with path.open(encoding="utf-8") as f:
        if f.readline().strip() != "$MeshFormat":
            raise ValueError("not Gmsh 2.2 ASCII")
        fmt = f.readline().split()
        if fmt[:2] != ["2.2", "0"] or f.readline().strip() != "$EndMeshFormat":
            raise ValueError("unexpected MSH2 header")
        for line in f:
            if line.strip() == "$Nodes":
                for _ in range(int(f.readline())):
                    q = f.readline().split()
                    if len(q) != 4 or int(q[0]) in nodes:
                        raise ValueError("invalid node")
                    nodes[int(q[0])] = tuple(float(x) for x in q[1:])
            if line.strip() == "$Elements":
                for _ in range(int(f.readline())):
                    q = list(map(int, f.readline().split()))
                    kind, ntag = q[1:3]
                    physical = q[3] if ntag else 0
                    ids = q[3+ntag:]
                    if kind == 11:
                        if physical != 1 or len(ids) != 10:
                            raise ValueError("unexpected Tet10/physical volume")
                        tets.append(ids)
                    elif kind == 9:
                        if physical not in boundary or len(ids) != 6:
                            raise ValueError("unexpected Tri6/physical boundary")
                        boundary[physical].update(ids)
                        tri_count[physical] += 1
                    elif kind in (2, 4):
                        raise ValueError("first-order elements forbidden")
    if len(nodes) < 1000 or len(tets) < 1000 or not all(tri_count.values()):
        raise ValueError("mesh not complete or physical tags absent")
    node_ids = sorted(nodes)
    indexed = {x: k for k, x in enumerate(node_ids)}
    xyz = np.asarray([nodes[k] for k in node_ids], dtype=float)
    tet_ids = np.asarray([[indexed[i] for i in ids] for ids in tets], dtype=np.int64)
    pore = xyz[[indexed[i] for i in sorted(boundary[8])]]
    rp = np.linalg.norm(pore - [0., 0., .03], axis=1)
    max_pore_radius_error = float(np.max(np.abs(rp-.001)))
    if not np.isfinite(xyz).all() or max_pore_radius_error > 2.e-7:
        raise ValueError("nonfinite geometry or pore-surface sphere mismatch")
    return xyz, tet_ids, tri_count, max_pore_radius_error


def quad(order):
    g, gw = np.polynomial.legendre.leggauss(order)
    g = (g+1.)/2.
    gw = gw/2.
    D = []
    weights = []
    for i, a in enumerate(g):
        for j, b in enumerate(g):
            for k, c in enumerate(g):
                r = a
                s = (1-r)*b
                t = (1-r)*(1-b)*c
                D.append(shape(r, s, t)[1])
                weights.append(gw[i]*gw[j]*gw[k]*(1-r)**2*(1-b))
    gradient = np.asarray(D, dtype=float)
    weight = np.asarray(weights)
    if abs(weight.sum()-1./6.) > 3.e-15:
        raise ValueError("quadrature normalization failed")
    return gradient, weight


def evaluate(xyz, tet_ids, order):
    gradient, weights = quad(order)
    minimum, maximum = math.inf, -math.inf
    nonpositive = 0
    total_volume = 0.
    max_internal_ratio = 0.
    n = len(tet_ids)
    for i in range(0, n, 32):
        p = xyz[tet_ids[i:i+32]]
        # J[b,q,coordinate,reference] = sum_node x[b,node,coordinate]*D[q,node,reference]
        J = np.einsum("bnc,qnr->bqcr", p, gradient, optimize=True)
        det = np.linalg.det(J)
        minimum = min(minimum, float(det.min()))
        maximum = max(maximum, float(det.max()))
        nonpositive += int(np.count_nonzero(~np.isfinite(det) | (det <= 0.)))
        total_volume += float(np.sum(det @ weights))
        lo, hi = det.min(axis=1), det.max(axis=1)
        if (lo > 0).all():
            max_internal_ratio = max(max_internal_ratio, float(np.max(hi/lo)))
    if nonpositive or minimum <= 0:
        raise ValueError(f"nonpositive/nonfinite detJ: {nonpositive} / {n*order**3}")
    return {"order": order, "total_curved_qp": n*order**3,
            "nonpositive": nonpositive, "minimum_detj": minimum,
            "maximum_detj": maximum, "integrated_volume_m3": total_volume,
            "max_element_detj_ratio": max_internal_ratio}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--msh", required=True, type=Path)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    digest = hashlib.sha256(a.msh.read_bytes()).hexdigest()
    if digest != a.expected_sha256:
        raise RuntimeError("M0 SHA mismatch before 729QP sampling")
    xyz, tet_ids, tri_count, pore_error = load_mesh(a.msh)
    report = {"protocol":"P10FQ_FRESH_M0_INDEPENDENT_343_729QP", "mesh":"M0",
              "mesh_sha256": digest, "nodes":len(xyz), "tet10": len(tet_ids),
              "tri6_tags":tri_count, "max_pore_surface_radius_error_m":pore_error,
              "qp343": evaluate(xyz,tet_ids,7),
              "qp729": evaluate(xyz,tet_ids,9),
              "gate":"PASS_DENSE_SAMPLED_GEOMETRY_NO_FEM"}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
