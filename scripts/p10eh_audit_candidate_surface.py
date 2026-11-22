#!/usr/bin/env python3
"""P10EH: independent read-only curved Tri6 audit of P10EF R2 ZIP.

No Gmsh, FEM, original M1/M2 raw mesh, or one-shot markers are touched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p10ee_audit_pore_surface_sizing_source_only import tri_basis, surface_areas

EXPECTED_MSH = "96f5c9a5d88811ef6b68cc46acabe094dbdd8f4b7441025ee39864bcbab4d1c7"
MESH_NAME = "P10EF_R2_SURFACE_2D_CANDIDATE.msh"
CENTRE = np.array([0.0, 0.0, .03])


def parse_pore(data):
    lines = iter(data.decode("ascii").splitlines())
    assert next(lines) == "$MeshFormat"
    assert next(lines) == "2.2 0 8"
    assert next(lines) == "$EndMeshFormat"
    for s in lines:
        if s == "$Nodes":
            break
    else:
        raise ValueError("No nodes")
    nodes = {}
    for _ in range(int(next(lines))):
        a = next(lines).split()
        nodes[int(a[0])] = [float(v) for v in a[1:]]
    assert next(lines) == "$EndNodes"
    assert next(lines) == "$Elements"
    tris = []
    types = {}
    for _ in range(int(next(lines))):
        a = [int(v) for v in next(lines).split()]
        typ, ntags = a[1:3]
        types[typ] = types.get(typ, 0) + 1
        if typ == 9 and a[3] == 8:
            assert len(a[3+ntags:]) == 6
            tris.append([nodes[v] for v in a[3+ntags:]])
    assert next(lines) == "$EndElements"
    assert len(tris) == 194 and types.get(11, 0) == 0
    return np.asarray(tris), len(nodes), types


def kappa(qp):
    delta = qp - CENTRE
    radius = np.linalg.norm(delta, axis=-1)
    d = np.clip((radius - .0011) / .0004, 0.0, 1.0)
    smooth_radial = d*d*(3-2*d)
    mu2 = delta[..., 2]**2 / (np.sum(delta**2, axis=-1) + 1.e-24)
    p = np.clip((mu2-.36)/.28, 0.0, 1.0)
    return (1-smooth_radial)*p*p*(3-2*p)


def analyze(mesh, order):
    N, D, W = tri_basis(order)
    area, jac, qp = surface_areas(mesh, N, D, W)
    assert np.all(jac > 0)
    wt = jac * W[None, :]
    kap = kappa(qp)
    mu = (qp[..., 2]-.03)/np.linalg.norm(qp-CENTRE, axis=-1)
    area_per_q = np.broadcast_to(area[:, None], wt.shape)
    result = {"order": order, "total_pore_area_m2": float(area.sum()),
              "area_relative_to_sphere": float(area.sum()/(4*np.pi*1e-6)-1),
              "minimum_surface_jacobian": float(jac.min()),
              "kappa_range": [float(kap.min()), float(kap.max())], "bins": {}}
    categories = {
        "north_mu_ge_08": mu >= .8,
        "south_mu_le_minus08": mu <= -.8,
        "nonpolar_abs_mu_lt_08": np.abs(mu) < .8,
        "kappa_zero": kap < 1.e-12,
        "kappa_0_to_025": (kap >= 1.e-12) & (kap < .25),
        "kappa_025_to_05": (kap >= .25) & (kap < .5),
        "kappa_05_to_075": (kap >= .5) & (kap < .75),
        "kappa_075_to_099": (kap >= .75) & (kap < .99),
        "kappa_099_to_1": kap >= .99,
    }
    for name, selection in categories.items():
        if not np.any(selection):
            continue
        total = float(wt[selection].sum())
        effective_count = float((wt[selection]/area_per_q[selection]).sum())
        kp = float(np.sum(wt[selection]*kap[selection])/total)
        target = float(np.sum(wt[selection]*(1-.2*kap[selection])**(2/3))/total)
        result["bins"][name] = {"area_m2": total,
           "area_fraction": total/float(area.sum()),
           "effective_tri6_count": effective_count,
           "effective_tri6_area_m2": total/effective_count,
           "area_weighted_kappa": kp,
           "area_weighted_nominal_target_ratio": target}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with zipfile.ZipFile(args.evidence) as z:
        assert z.testzip() is None
        raw = z.read(MESH_NAME)
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_MSH
        recorded = json.loads(z.read("QA/P10EF_R2_SURFACE_QP_AUDIT.json"))
    mesh, node_count, types = parse_pore(raw)
    out = {"protocol": "P10EH_READ_ONLY_INDEPENDENT_P10EF_R2_SURFACE",
           "candidate_sha256": EXPECTED_MSH, "node_count": node_count,
           "pore_tri6": len(mesh), "element_types": types,
           "gmsh_invocations": 0, "fem_invocations": 0,
           "quadrature": {str(n): analyze(mesh, n) for n in (3,5,9,15)},
           "comparison_to_recorded": {}}
    latest = out["quadrature"]["15"]
    out["comparison_to_recorded"]["full_area_absolute_m2"] = abs(
       latest["total_pore_area_m2"]-recorded["candidate_2d"]["curved_pore_area_m2"])
    for label, key in (("north_mu_ge_08", "north"), ("south_mu_le_minus08", "south"),
                        ("nonpolar_abs_mu_lt_08", "nonpolar")):
        actual = latest["bins"][label]["effective_tri6_area_m2"]
        expected = recorded["candidate_2d"]["zones"][key]["effective_curved_Tri6_area_m2"]
        out["comparison_to_recorded"][key+"_effective_area_relative"] = actual/expected-1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("P10EH_INDEPENDENT_TRI6_QP_OK", json.dumps(out["comparison_to_recorded"]))


if __name__ == "__main__":
    main()
