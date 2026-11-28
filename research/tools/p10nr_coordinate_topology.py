#!/usr/bin/env python3
"""P10NR: compare optimized M13 boundary connectivity by *coordinates*, not IDs.

Run next to P10NQ's original M13 R2 .msh and p10nq_native...py.
No mesh output, no FEM, no marker use. Requires gmsh 4.15.2 and numpy.
"""
import collections
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from p10nq_native_geometry_correspondence_windows import MESH, SHA, sample

OUTPUT = Path(__file__).resolve().parent / "P10NR_COORDINATE_TOPOLOGY_RESULT.json"
TOL = 1e-12  # m; exact input/output point-clouds must already coincide


def boundary_index(snap):
    return {n for p in snap["by_phys"].values() for n in p["node_ids"]}


def match_by_position(before, after, ids_before, ids_after, tol=TOL):
    """Unique bijection with tolerance, rejecting duplicates and ambiguity."""
    ids_before, ids_after = sorted(ids_before), sorted(ids_after)
    if len(ids_before) != len(ids_after):
        raise ValueError("different node counts")
    # Rounded grid is merely a candidate index; verify true Euclidean distances.
    grid = collections.defaultdict(list)
    for tag in ids_after:
        key = tuple(np.rint(after["nodes"][tag] / tol).astype(np.int64))
        grid[key].append(tag)
    mapping = {}
    used = set()
    import itertools
    for tag in ids_before:
        p = before["nodes"][tag]
        key = tuple(np.rint(p / tol).astype(np.int64))
        nearby = []
        for offset in itertools.product((-1, 0, 1), repeat=3):
            nearby.extend(grid.get(tuple(key[i] + offset[i] for i in range(3)), []))
        matches = [n for n in nearby if np.linalg.norm(after["nodes"][n] - p) < tol]
        if len(matches) != 1:
            raise ValueError(f"nonunique coordinate match: old node {tag}, candidates {len(matches)}")
        if matches[0] in used:
            raise ValueError(f"noninjective coordinate map at {tag}")
        mapping[tag] = matches[0]
        used.add(matches[0])
    if len(used) != len(ids_after):
        raise ValueError("not surjective")
    return mapping


def face_signature(conn):
    """Tri6 geometry with three vertex+edge-midpoint associations.

    Gmsh Tri6 local nodes = corners 0,1,2; midsides 01,12,20.
    Orientation/order independent; changing curved edge pairing is detectable.
    """
    a, b, c, ab, bc, ca = conn
    return (tuple(sorted((a, b, c))), tuple(sorted((tuple(sorted((a, b))) + (ab,),
                                                    tuple(sorted((b, c))) + (bc,),
                                                    tuple(sorted((c, a))) + (ca,)))))


def multiset_faces(snap, phys, remap=None):
    result = collections.Counter()
    for conn in snap["by_phys"][phys]["elements"].values():
        c = tuple(remap[x] for x in conn) if remap is not None else conn
        result[face_signature(c)] += 1
    return result


def classify(before, after):
    if set(before["by_phys"]) != set(after["by_phys"]):
        raise ValueError("physical groups changed")
    before_ids, after_ids = boundary_index(before), boundary_index(after)
    mapping = match_by_position(before, after, before_ids, after_ids)
    report = {"boundary_nodes": len(mapping),
              "boundary_tags_changed_under_coordinate_map": sum(k != v for k, v in mapping.items()),
              "physical_groups": {}}
    for phys in sorted(before["by_phys"]):
        left = multiset_faces(before, phys, mapping)
        right = multiset_faces(after, phys)
        missing = sum((left - right).values())
        extra = sum((right - left).values())
        report["physical_groups"][str(phys)] = {
            "faces_before": sum(left.values()), "faces_after": sum(right.values()),
            "faces_missing_after_coordinate_remap": missing,
            "faces_extra_after_coordinate_remap": extra,
            "geometry_connectivity_preserved": missing == extra == 0}
    report["all_boundary_tri6_preserved"] = all(
        q["geometry_connectivity_preserved"] for q in report["physical_groups"].values())
    # Interior Tet10 midside nodes can move. Do not claim Tet10 invariance
    # from a boundary-only node bijection.
    report["interior_tet10_correspondence"] = "NOT_TESTED"
    return report


def selftest():
    def snap(nodes, faces):
        return {"nodes": {k: np.array(v, float) for k, v in nodes.items()},
                "by_phys": {8: {"node_ids": set(nodes), "elements": faces}}}
    coords = {1:(0,0,0),2:(1,0,0),3:(0,1,0),4:(.5,0,0),5:(.5,.5,0),6:(0,.5,0)}
    base = snap(coords, {10:(1,2,3,4,5,6)})
    relabel = {i:i+100 for i in coords}
    perm = snap({relabel[k]:v for k,v in coords.items()},
                {20:tuple(relabel[k] for k in (2,3,1,5,6,4))})
    assert classify(base, perm)["all_boundary_tri6_preserved"]
    bad = snap(perm["nodes"], {20:tuple(relabel[k] for k in (2,3,1,6,5,4))})
    assert not classify(base, bad)["all_boundary_tri6_preserved"]
    ambiguous = snap({**coords, 7:(0,0,0)}, {10:(1,2,3,4,5,6)})
    try:
        match_by_position(base, ambiguous, coords, ambiguous["nodes"])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate-coordinate gate did not fire")
    print("P10NR_SYNTHETIC_PASS", flush=True)


def main():
    selftest()
    if "--selftest" in sys.argv:
        return
    import gmsh
    if OUTPUT.exists():
        raise RuntimeError("P10NR_STOP: output already exists; no overwrite")
    if gmsh.__version__ != "4.15.2":
        raise RuntimeError("Gmsh 4.15.2 required")
    if hashlib.sha256(MESH.read_bytes()).hexdigest() != SHA:
        raise RuntimeError("M13 R2 source SHA mismatch")
    report = {"protocol": "P10NR_BOUNDARY_COORDINATE_TRI6_CORRESPONDENCE",
              "status": "STARTED", "source_sha256": SHA,
              "FEM_attempts": 0, "gmsh_generation_attempts": 0, "marker_uses": 0}
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Mesh.HighOrderFixBoundaryNodes", 1)
        gmsh.option.setNumber("Mesh.HighOrderIterMax", 50)
        gmsh.option.setNumber("Mesh.HighOrderPassMax", 5)
        gmsh.option.setNumber("Mesh.HighOrderNumLayers", 2)
        gmsh.open(str(MESH))
        before = sample(gmsh)
        t0 = time.monotonic()
        gmsh.model.mesh.optimize("HighOrderElastic", force=True)
        report["optimizer_s"] = time.monotonic() - t0
        after = sample(gmsh)
        report.update(classify(before, after))
        report["status"] = "AUDIT_COMPLETED_NO_R3_NO_FEM"
        report["acceptance"] = "DIAGNOSTIC_ONLY_NOT_M13_ACCEPTANCE"
    except Exception as e:
        report["status"] = "AUDIT_ERROR"
        report["error"] = repr(e)
        report["traceback"] = traceback.format_exc()[-4000:]
    finally:
        gmsh.finalize()
    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print("P10NR_DONE", report["status"], flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("P10NR_STOP", repr(e), flush=True)
        sys.exit(2)
