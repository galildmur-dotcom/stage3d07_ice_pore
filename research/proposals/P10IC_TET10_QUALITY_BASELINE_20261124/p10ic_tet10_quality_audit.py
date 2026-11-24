#!/usr/bin/env python3
"""P10IC read-only Tet10 quality baseline and independent quadrature QA.

Usage: python p10ic_tet10_quality_audit.py PATH_TO_MSH
No mesh generation or FEM. Numerical candidate acceptance thresholds are NOT set.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import gmsh
import numpy as np
import p10hv_independent_scan as exact

PINNED_M1_SHA256 = "47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7"


def distribution(values):
    vals = np.asarray(values, dtype=np.float64)
    if not len(vals) or not np.all(np.isfinite(vals)):
        raise ValueError("Empty or nonfinite element quality data")
    return {
        "min": float(vals.min()), "p01": float(np.percentile(vals, 1)),
        "p05": float(np.percentile(vals, 5)), "median": float(np.median(vals)),
        "p95": float(np.percentile(vals, 95)), "max": float(vals.max()),
        "nonpositive_count": int(np.count_nonzero(vals <= 0)),
    }


def audit(path):
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    xyz, tet, faces = exact.read_msh(data)
    result = {
        "protocol": "P10IC_READONLY_TET10_QUALITY_AUDIT_V1",
        "file_sha256": sha,
        "matches_pinned_original_M1": sha == PINNED_M1_SHA256,
        "tet10_count": int(len(tet)),
        "pore_Tri6_count": int(faces[8]),
        "physical_surface_tags": sorted(int(k) for k in faces),
        "FEM_attempts": 0, "mesh_generation_attempts": 0,
        "candidate_geometry_accepted": False,
        "candidate_physics_converged": False,
    }
    if len(tet) == 0:
        raise ValueError("No Tet10")
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(path))
        tags, _ = gmsh.model.mesh.getElementsByType(11)
        if len(tags) != len(tet):
            raise ValueError("Gmsh and independent parser disagree on Tet10 count")
        result["gmsh_version"] = gmsh.__version__
        result["gmsh_curved_element_qualities"] = {
            kind: distribution(gmsh.model.mesh.getElementQualities(tags, qualityName=kind))
            for kind in ("minSICN", "minSJ", "minDetJac", "gamma")
        }
    finally:
        gmsh.finalize()
    base = exact.evaluate(xyz, tet, 3, None)
    q343 = exact.evaluate(xyz, tet, 7, base["volume"])
    q729 = exact.evaluate(xyz, tet, 9, base["volume"])
    g343, g729 = exact.groups(q343), exact.groups(q729)
    rels = [abs(g343[key]["Veff"] / g729[key]["Veff"] - 1)
            for key in g729 if g729[key]["Neff"] > 0]
    result["independent_curved_Tet10_quadrature"] = {
        "min_detJ_27_343_729": [float(base["minj"]), float(q343["minj"]), float(q729["minj"])],
        "positive_at_all_sampled_QP": min(base["minj"], q343["minj"], q729["minj"]) > 0,
        "CAD_volume_closure_rel_729": float(q729["volume"].sum() / exact.CAD_VOL - 1),
        "max_relative_Veff_343_729_over_supported_regions": float(max(rels)),
        "mean_Tet10_curved_volume_m3": float(q729["volume"].mean()),
        "north_high_kappa_near_Veff_m3": float(g729["near_p0_N"]["Veff"]),
        "south_high_kappa_near_Veff_m3": float(g729["near_p0_S"]["Veff"]),
        "north_high_kappa_near_Neff": float(g729["near_p0_N"]["Neff"]),
        "south_high_kappa_near_Neff": float(g729["near_p0_S"]["Neff"]),
    }
    result["neighbour_volume_ratio_DIAGNOSTIC_NOT_GATE"] = exact.neighbour_quality(
        xyz, tet, q729["volume"])
    result["gate_note"] = (
        "This is evidence, not an automatic geometric GO: all curved Tet10 must be good; "
        "numerical acceptability thresholds must be preregistered before the next M2. "
        "Neighbour ratios are not a hard rejection criterion under D-030."
    )
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python p10ic_tet10_quality_audit.py MESH.msh")
    print(json.dumps(audit(Path(sys.argv[1]).resolve()), ensure_ascii=False, indent=2))
