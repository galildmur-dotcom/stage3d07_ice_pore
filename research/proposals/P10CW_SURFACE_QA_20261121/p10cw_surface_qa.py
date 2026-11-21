#!/usr/bin/env python3
"""Read-only Gmsh MSH2 Tri6 pore-wall surface diagnostics, NO FEM."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import gmsh
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("msh", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--radius-mm", type=float, default=1.0)
    args = ap.parse_args()
    source_hash = hashlib.sha256(args.msh.read_bytes()).hexdigest()
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        runtime_version = gmsh.option.getString("General.Version")
        gmsh.open(str(args.msh))
        if (2, 8) not in gmsh.model.getPhysicalGroups():
            raise RuntimeError("STOP: PORE_WALL physical group 2:8 absent")
        wall_surfaces = gmsh.model.getEntitiesForPhysicalGroup(2, 8)
        if len(wall_surfaces) != 1:
            raise RuntimeError("STOP: expected exactly one pore-wall surface entity")
        types, tags, connectivity = gmsh.model.mesh.getElements(2, int(wall_surfaces[0]))
        if len(types) != 1 or int(types[0]) != 9:
            raise RuntimeError(f"STOP: pore elements not exclusively Tri6: {types}")
        tri = np.asarray(connectivity[0], dtype=np.int64).reshape(-1, 6)
        tag, xyz, _ = gmsh.model.mesh.getNodes()
        coordinates = np.asarray(xyz).reshape(-1, 3)
        lookup = {int(t): i for i, t in enumerate(tag)}
        pt = coordinates[np.fromiter((lookup[int(v)] for v in tri.ravel()), dtype=np.int64).reshape(-1, 6)]
        center = np.array([0.0, 0.0, 0.03])
        radius = args.radius_mm / 1000.0
        corner = pt[:, :3, :]
        vectors = corner - center
        mean = vectors.mean(axis=1)
        mu = np.clip(mean[:, 2] / np.linalg.norm(mean, axis=1), -1.0, 1.0)
        phi = np.mod(np.arctan2(mean[:, 1], mean[:, 0]), 2 * math.pi)
        edges = np.stack((corner[:, 0]-corner[:, 1], corner[:, 1]-corner[:, 2], corner[:, 2]-corner[:, 0]), axis=1)
        lengths = np.linalg.norm(edges, axis=2)
        hmax = np.max(lengths, axis=1)
        area = np.linalg.norm(np.cross(edges[:, 0], -edges[:, 2]), axis=1) / 2
        quality = 4 * math.sqrt(3) * area / np.maximum(np.sum(lengths**2, axis=1), 1e-300)
        radial_error = np.abs(np.linalg.norm(pt-center, axis=2) - radius)
        mu_index = np.minimum((10*((mu+1)/2)).astype(int), 9)
        phi_index = np.minimum((12*phi/(2*math.pi)).astype(int), 11)

        rows=[]
        for i in range(10):
            for j in range(12):
                sel = (mu_index == i) & (phi_index == j)
                count = int(np.count_nonzero(sel))
                rows.append({"mu_bin": i, "phi_bin": j, "count_tri6": count,
                             "chord_area_mm2": float(np.sum(area[sel])*1e6),
                             "hmax_p50_um": float(np.median(hmax[sel])*1e6) if count else None})
        polar = (mu_index==0) | (mu_index==9)
        middle = ~polar
        worst = int(np.argmin(quality))
        quality_low01 = (quality < 0.1)
        quality_low02 = (quality < 0.2)
        result = {
            "status": "P10CW_PORE_WALL_TRI6_SURFACE_QA_ONLY_NO_TET_NO_FEM",
            "gmsh_runtime": runtime_version,
            "mesh_sha256": source_hash,
            "physical_groups": [[int(d),int(t)] for d,t in gmsh.model.getPhysicalGroups()],
            "tri6_pore": int(tri.shape[0]),
            "pore_chord_area_mm2": float(np.sum(area)*1e6),
            "sphere_cad_area_mm2": float(4*math.pi*(args.radius_mm**2)),
            "area_relative_error": float((np.sum(area)-4*math.pi*radius**2)/(4*math.pi*radius**2)),
            "hmax_um_p5_p50_p95": [float(v*1e6) for v in np.percentile(hmax,[5,50,95])],
            "min_corner_quality": float(np.min(quality)),
            "corner_quality_p5_p50_p95": [float(v) for v in np.percentile(quality,[5,50,95])],
            "corner_quality_below_0p1": int(np.count_nonzero(quality_low01)),
            "corner_quality_below_0p2": int(np.count_nonzero(quality_low02)),
            "corner_quality_below_0p1_polar": int(np.count_nonzero(quality_low01 & polar)),
            "corner_quality_below_0p2_polar": int(np.count_nonzero(quality_low02 & polar)),
            "worst_corner_quality_mu_phi_bins": [int(mu_index[worst]),int(phi_index[worst])],
            "worst_corner_quality_hmax_um": float(hmax[worst]*1e6),
            "worst_corner_quality_edge_um": [float(v*1e6) for v in lengths[worst]],
            "worst_corner_quality_mu": float(mu[worst]),
            "worst_corner_quality_phi_deg": float(phi[worst]*180/math.pi),
            "worst_corner_quality_centroid_mm": [float(v*1e3) for v in corner[worst].mean(axis=0)],
            "nonpositive_corner_area": int(np.count_nonzero(area<=0)),
            "max_radial_node_deviation_um": float(np.max(radial_error)*1e6),
            "polar_tri6": int(np.count_nonzero(polar)),
            "polar_chord_area_fraction": float(np.sum(area[polar])/np.sum(area)),
            "polar_vs_mid_median_hmax_ratio": float(np.median(hmax[polar])/np.median(hmax[middle])),
            "mu_phi_bins": rows,
        }
        if sum(r["count_tri6"] for r in rows) != tri.shape[0]:
            raise RuntimeError("STOP: angular partition count closure")
        if np.any(area<=0) or not np.all(np.isfinite(hmax)):
            raise RuntimeError("STOP: nonpositive surface area or nonfinite edge")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
        print(result["status"],"tri6",result["tri6_pore"],"h50_um",result["hmax_um_p5_p50_p95"][1],
              "polar_ratio",result["polar_vs_mid_median_hmax_ratio"],"sha256",source_hash)
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    main()
