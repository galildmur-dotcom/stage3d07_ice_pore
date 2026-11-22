#!/usr/bin/env python3
"""P10ED: independent, read-only, direct raw MSH2 Tet10 spatial audit.

No Gmsh, physics, cache, markers or published raw meshes. Spatial quadrature
integrals define an effective fractional element count, not a same-tet pairing.
Requires numpy and scipy; all output is small derived text/CSV only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

import numpy as np
from scipy.spatial import cKDTree

M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
M2_SHA = "ba1f1a0553a568c1b399acadd52bce1c1dc32e8d1c6b3ab1ce6759c547e5dee5"
CAD_VOL = .06 * .06 * .05 - (4.0 / 3.0) * math.pi * .001**3
CENTRE = np.array([0., 0., .03])
EDGES = [(0, 1), (1, 2), (2, 0), (0, 3), (2, 3), (1, 3)]
RAD = ["0_100um", "100_500um", "500um_plus"]
POL = ["polar_abs_mu_ge_0p8", "taper_abs_mu_0p6_0p8", "off_abs_mu_le_0p6"]


def ensure(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError("P10ED_STOP: " + why)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_msh2(path: Path, expected_sha: str) -> dict:
    ensure(path.is_file() and path.name in ("P10DG_M1_CANDIDATE.msh", "P10EA_M2_CANDIDATE.msh"),
           "wrong MSH filename or missing source")
    ensure(digest(path) == expected_sha, "exact raw MSH SHA mismatch")
    with path.open("r", encoding="ascii", errors="strict") as f:
        ensure(next(f).strip() == "$MeshFormat", "mesh header")
        ensure(next(f).strip() == "2.2 0 8", "ASCII MSH2.2 only")
        ensure(next(f).strip() == "$EndMeshFormat", "mesh header close")
        physical = {}
        for line in f:
            if line.strip() == "$PhysicalNames":
                n = int(next(f))
                for _ in range(n):
                    parts = next(f).strip().split(maxsplit=2)
                    ensure(len(parts) == 3, "physical names")
                    physical[(int(parts[0]), int(parts[1]))] = parts[2].strip('"')
                ensure(next(f).strip() == "$EndPhysicalNames", "physical close")
            elif line.strip() == "$Nodes":
                break
        else:
            ensure(False, "nodes absent")
        n = int(next(f))
        points = {}
        for _ in range(n):
            line = next(f).split()
            ensure(len(line) == 4, "node width")
            nid = int(line[0])
            ensure(nid not in points, "duplicate node")
            points[nid] = tuple(float(x) for x in line[1:])
        ensure(next(f).strip() == "$EndNodes", "node close")
        ensure(next(f).strip() == "$Elements", "elements follow nodes")
        count = int(next(f))
        tets, tris, other = [], [], {}
        for _ in range(count):
            raw = [int(v) for v in next(f).split()]
            ensure(len(raw) >= 5, "element width")
            eid, typ, ntag = raw[:3]
            ensure(ntag >= 2 and len(raw) >= 3 + ntag, "element tag count")
            tag = raw[3]
            ids = raw[3 + ntag:]
            if typ == 11:
                ensure(tag == 1 and len(ids) == 10, "volume Tet10 physical tag")
                tets.append(ids)
            elif typ == 9 and tag == 8:
                ensure(len(ids) == 6, "pore Tri6 connectivity")
                tris.append(ids)
            else:
                other[str(typ)] = other.get(str(typ), 0) + 1
        ensure(next(f).strip() == "$EndElements", "element close")
        ensure(not f.read().strip(), "trailing unexpected MSH sections")
    ensure(set(physical.items()) >= {((3, 1), "ICE_VOLUME"), ((2, 8), "PORE_WALL")},
           "wrong physical groups")
    ensure(set(x for a in tets + tris for x in a).issubset(points), "unknown node id")
    ensure(all(math.isfinite(v) for p in points.values() for v in p), "nonfinite node")
    xyz = np.zeros((max(points) + 1, 3), dtype=np.float64)
    for nid, p in points.items():
        xyz[nid] = p
    return {"nodes": xyz, "node_count": n, "tet10": np.asarray(tets, dtype=np.int64),
            "pore_tri6": np.asarray(tris, dtype=np.int64), "other": other}


def duffy_rule(order: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Derive Tet10 basis and gradients from barycentric Lagrange polynomials."""
    gp, gweight = np.polynomial.legendre.leggauss(order)
    gauss = (gp+1)/2
    gw = gweight/2
    dl = np.array([[-1., -1., -1.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    N, D, W = [], [], []
    for a, wa in zip(gauss, gw):
        for b, wb in zip(gauss, gw):
            for c, wc in zip(gauss, gw):
                r, s, t = a, (1-a)*b, (1-a)*(1-b)*c
                l = np.array([1-r-s-t, r, s, t])
                nb = list(l * (2*l-1))
                db = list((4*l[:, None]-1)*dl)
                for i, j in EDGES:
                    nb.append(4*l[i]*l[j])
                    db.append(4*(l[i]*dl[j]+l[j]*dl[i]))
                N.append(nb)
                D.append(db)
                W.append(wa*wb*wc*(1-a)**2*(1-b))
    N, D, W = np.asarray(N), np.asarray(D), np.asarray(W)
    ensure(abs(W.sum()-1/6) < 5e-16 and np.max(abs(N.sum(axis=1)-1)) < 1e-14 and
           np.max(abs(D.sum(axis=1))) < 1e-14, "basis/27 quadrature invariant")
    return N, D, W


def rule27() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return duffy_rule(3)


def curved(p: np.ndarray, N: np.ndarray, D: np.ndarray, W: np.ndarray):
    # p: [elements, 10, xyz], D: [quadrature, node, reference-coordinate]
    J = np.einsum("nic,qij->nqcj", p, D, optimize=True)
    det = np.linalg.det(J)
    vol = det @ W
    xyz = np.einsum("qi,nic->nqc", N, p, optimize=True)
    return vol, det, xyz


def spatial(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    relative = xyz - CENTRE
    rho = np.linalg.norm(relative, axis=-1)
    ensure(np.all(rho > 0), "point at excluded pore centre")
    d = rho - .001
    mu = relative[..., 2] / rho
    rad = np.where(d < .0001, 0, np.where(d < .0005, 1, 2))
    pol = np.where(np.abs(mu) >= .8, 0, np.where(np.abs(mu) > .6, 1, 2))
    return rad, pol, mu


def kappa(xyz: np.ndarray) -> np.ndarray:
    delta = xyz - CENTRE
    rho = np.linalg.norm(delta, axis=-1)
    mu2 = (delta[..., 2]/rho)**2
    ur = np.clip((rho-.001-.0001)/.0004, 0, 1)
    ua = np.clip((mu2-.6**2)/(.8**2-.6**2), 0, 1)
    return (1-(ur*ur*(3-2*ur)))*(ua*ua*(3-2*ua))


def quantile_weighted(x: np.ndarray, weight: np.ndarray, q: float) -> float:
    ix = np.argsort(x)
    xs, ws = x[ix], weight[ix]
    return float(xs[min(len(xs)-1, int(np.searchsorted(np.cumsum(ws), q*ws.sum(), side="left")))])


def audit_mesh(mesh: dict, label: str, N: np.ndarray, D: np.ndarray, W: np.ndarray):
    p = mesh["nodes"][mesh["tet10"]]
    vol, det, sample_xyz = curved(p, N, D, W)
    corner = np.linalg.det(p[:, 1:4, :]-p[:, :1, :])/6
    ensure(np.all(corner > 0), "nonpositive corner Jacobian")
    ensure(np.all(det > 0) and np.all(vol > 0), "nonpositive curved 27QP Jacobian")
    centre = p[:, :4, :].mean(axis=1)
    crad, cpol, cmu = spatial(centre)
    qrad, qpol, qmu = spatial(sample_xyz)
    qweight = det * W[None, :]
    w = np.broadcast_to(vol[:, None], qweight.shape)
    rows = []
    for r in range(3):
        for pol in range(3):
            cm = (crad == r) & (cpol == pol)
            qm = (qrad == r) & (qpol == pol)
            sample_vol, cells = qweight[qm], w[qm]
            ensure(cm.any() and qm.any(), "empty spatial zone")
            regvol = math.fsum(float(v) for v in sample_vol)
            fractional_count = math.fsum(float(v) for v in (sample_vol/cells))
            rows.append({"mesh": label, "radial_zone": RAD[r], "polar_zone": POL[pol],
                "tet_centroid_count": int(cm.sum()), "centroid_median_tet_volume_m3": float(np.median(vol[cm])),
                "qp_count": int(qm.sum()), "qp_region_volume_m3": regvol,
                "qp_fractional_cell_count": fractional_count,
                "qp_effective_tet_volume_m3": regvol/fractional_count,
                "qp_volume_weighted_median_tet_volume_m3": quantile_weighted(cells, sample_vol, .5),
                "qp_mean_kappa": float(np.dot(qweight[qm], kappa(sample_xyz)[qm])/regvol)})
    pore = mesh["nodes"][mesh["pore_tri6"]]
    xyz = pore[:, :3, :].mean(axis=1)
    _, pband, pmu = spatial(xyz)
    edges = np.stack([np.linalg.norm(pore[:, i]-pore[:, j], axis=1) for i, j in EDGES[:3]], axis=1)
    pore_stats = {}
    for name, mask in (("both_poles", pband==0), ("north", (pband==0)&(pmu>=0)),
                       ("south", (pband==0)&(pmu<0)), ("taper", pband==1), ("off", pband==2)):
        pore_stats[name] = {"tri6": int(mask.sum()),
            "median_corner_edge_mm": float(np.median(edges[mask])*1000) if mask.any() else None}
    wall_error = float(np.max(np.abs(np.linalg.norm(pore-CENTRE, axis=2)-.001)))
    stats = {"mesh": label, "nodes": mesh["node_count"], "tet10": int(len(p)),
             "pore_tri6": int(len(pore)), "curved_27qp": int(det.size),
             "corner_nonpositive": int(np.count_nonzero(corner<=0)),
             "curved_nonpositive": int(np.count_nonzero(det<=0)),
             "curved_min_det_m3": float(det.min()),
             "curved_volume_sum_m3": float(math.fsum(float(v) for v in vol)),
             "curved_CAD_rel_error": float(math.fsum(float(v) for v in vol)/CAD_VOL-1),
             "max_pore_spherical_node_abs_radial_error_m": wall_error,
             "pore_cap_surface_corner_edges": pore_stats,
             "centroid_positive_kappa_tet10": int(np.count_nonzero(kappa(centre)>0)),
             "centroid_full_kappa_tet10": int(np.count_nonzero(kappa(centre)==1))}
    return stats, rows, {"centroid": centre, "vol": vol, "crad": crad, "cpol": cpol,
                          "qweight": qweight, "qp_rad": qrad, "qp_pol": qpol, "qp_mu": qmu}


def compare(a: list[dict], b: list[dict], aa: dict, bb: dict) -> list[dict]:
    result=[]
    for x, y in zip(a, b):
        ensure((x["radial_zone"],x["polar_zone"]) == (y["radial_zone"],y["polar_zone"]),
               "9-zone alignment")
        k = x["qp_mean_kappa"]
        target = 1-.2*k
        record = {"radial_zone": x["radial_zone"], "polar_zone": x["polar_zone"],
                  "m1_centroid_tet": x["tet_centroid_count"], "m2_centroid_tet": y["tet_centroid_count"],
                  "m1_qp_region_volume_m3": x["qp_region_volume_m3"],
                  "m2_qp_region_volume_m3": y["qp_region_volume_m3"],
                  "m2_over_m1_qp_region_volume": y["qp_region_volume_m3"]/x["qp_region_volume_m3"],
                  "m1_fractional_tets": x["qp_fractional_cell_count"],
                  "m2_fractional_tets": y["qp_fractional_cell_count"],
                  "m2_over_m1_fractional_tet_density": (y["qp_fractional_cell_count"]/y["qp_region_volume_m3"])/
                        (x["qp_fractional_cell_count"]/x["qp_region_volume_m3"]),
                  "model_target_volume_ratio_m1_qp_mean": target,
                  "m2_over_m1_effective_tet_volume": y["qp_effective_tet_volume_m3"]/x["qp_effective_tet_volume_m3"],
                  "m2_over_m1_centroid_median_tet_volume": y["centroid_median_tet_volume_m3"]/x["centroid_median_tet_volume_m3"],
                  "m2_over_m1_qp_weighted_median_tet_volume": y["qp_volume_weighted_median_tet_volume_m3"]/x["qp_volume_weighted_median_tet_volume_m3"]}
        # Directional nearest-centroid mapping is a diagnostic of remeshing,
        # not identical Tet10 correspondence or exact location interpolation.
        r = RAD.index(x["radial_zone"]); pol = POL.index(x["polar_zone"])
        am = (aa["crad"]==r)&(aa["cpol"]==pol)
        bm = (bb["crad"]==r)&(bb["cpol"]==pol)
        avec = aa["centroid"][am]; bvec = bb["centroid"][bm]
        avol = aa["vol"][am]; bvol = bb["vol"][bm]
        d_ab, idx_ab = cKDTree(bvec).query(avec)
        d_ba, idx_ba = cKDTree(avec).query(bvec)
        record.update({"nearest_m1_to_m2_median_centroid_distance_mm": float(np.median(d_ab)*1000),
                       "nearest_m2_to_m1_median_centroid_distance_mm": float(np.median(d_ba)*1000),
                       "nearest_m1_to_m2_median_volume_ratio": float(np.median(bvol[idx_ab]/avol)),
                       "nearest_m2_to_m1_median_volume_ratio": float(np.median(bvol/avol[idx_ba]))})
        result.append(record)
    return result


def spatial_rule(mesh: dict, full_volume: np.ndarray, order: int) -> dict:
    """Integrate spatial *indicator* at a finer QP rule (not just tet volume)."""
    N,D,W=duffy_rule(order)
    tets=mesh["tet10"]
    volume=np.zeros(9,dtype=np.float64)
    fractional=np.zeros(9,dtype=np.float64)
    hemisphere_volume=np.zeros(18,dtype=np.float64)
    hemisphere_fractional=np.zeros(18,dtype=np.float64)
    min_jac=math.inf
    for start in range(0,len(tets),256):
        stop=min(start+256,len(tets))
        p=mesh["nodes"][tets[start:stop]]
        _,jac,xyz=curved(p,N,D,W)
        ensure(np.all(jac>0),f"nonpositive {order}^3-QP Jacobian")
        min_jac=min(min_jac,float(jac.min()))
        rr,pp,mu=spatial(xyz)
        weights=jac*W[None,:]
        code=(rr*3+pp).ravel()
        volume+=np.bincount(code,weights=weights.ravel(),minlength=9)
        fractional+=np.bincount(code,weights=(weights/full_volume[start:stop,None]).ravel(),minlength=9)
        code18=(2*code + (mu.ravel()<0).astype(int))
        hemisphere_volume+=np.bincount(code18,weights=weights.ravel(),minlength=18)
        hemisphere_fractional+=np.bincount(code18,weights=(weights/full_volume[start:stop,None]).ravel(),minlength=18)
    ensure(np.all(volume>0) and np.all(fractional>0),"zero QP spatial region")
    return {"order_per_axis":order,"qp_per_tet":order**3,
            "min_curved_Jacobian_m3":min_jac,
            "total_curved_volume_m3":float(volume.sum()),
            "qp_spatial_volumes_m3":volume.tolist(),
            "qp_fractional_tets":fractional.tolist(),
            "qp_effective_tet_volume_m3":(volume/fractional).tolist(),
            "qp_north_south_effective_tet_volume_m3":(hemisphere_volume/hemisphere_fractional).tolist(),
            "qp_north_south_region_volume_m3":hemisphere_volume.tolist()}


def selftest(N: np.ndarray, D: np.ndarray, W: np.ndarray) -> None:
    vertices=np.array([[0.,0.,0.],[.001,0.,0.],[0.,.001,0.],[0.,0.,.001]])
    p=np.concatenate([vertices, np.array([(vertices[i]+vertices[j])/2 for i,j in EDGES])])
    v, det, xyz = curved(p[None, :, :], N, D, W)
    ensure(abs(v[0]-(.001**3/6))<1e-24 and np.max(abs(det-1e-9))<1e-19 and
           xyz.shape==(1,27,3), "affine synthetic curved integral")
    inv=vertices.copy(); inv[[1,2]]=inv[[2,1]]
    pi=np.concatenate([inv,np.array([(inv[i]+inv[j])/2 for i,j in EDGES])])
    ensure(np.all(curved(pi[None,:,:], N,D,W)[1]<0), "inverted Tet10 negative test")
    ensure(np.max(abs(kappa(np.array([[0.,0.,.03105],[.00105,0.,.03]]))-
                      np.array([1.,0.])))<1e-14, "polar/equator source coefficient")


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m1",type=Path)
    ap.add_argument("--m2",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--selftest", action="store_true")
    args=ap.parse_args()
    N,D,W=rule27()
    selftest(N,D,W)
    if args.selftest:
        print("P10ED_RAW_TET10_SYNTHETIC_OK affine=PASS inverted=STOP geometry_only=1")
        return 0
    ensure(args.m1 is not None and args.m2 is not None and args.out is not None,
           "--m1 --m2 --out required")
    ensure(args.m1.resolve()!=args.m2.resolve(), "M1/M2 paths must differ")
    ensure(args.m1.name=="P10DG_M1_CANDIDATE.msh" and
           args.m2.name=="P10EA_M2_CANDIDATE.msh", "wrong original mesh basename")
    m1=parse_msh2(args.m1,M1_SHA)
    m2=parse_msh2(args.m2,M2_SHA)
    ensure(len(m1["tet10"])==9736 and len(m2["tet10"])==9750 and
           len(m1["pore_tri6"])==178 and len(m2["pore_tri6"])==170,
           "raw expected node/element counts")
    s1, rows1, aux1=audit_mesh(m1,"M1",N,D,W)
    s2, rows2, aux2=audit_mesh(m2,"M2",N,D,W)
    comparable=compare(rows1,rows2,aux1,aux2)
    # The exact cell-volume integral uses 27QP. Spatial zone clipping uses
    # discontinuous indicators: assess its quadrature sensitivity separately.
    spatial_refinements={}
    for order in (3,5,7,9):
        a=spatial_rule(m1,aux1["vol"],order)
        b=spatial_rule(m2,aux2["vol"],order)
        spatial_refinements[str(order)]={"M1":a,"M2":b,
            "m2_over_m1_zone_effective_tet_volume":
              [yb/xa for xa,yb in zip(a["qp_effective_tet_volume_m3"],
                                      b["qp_effective_tet_volume_m3"])],
            "m2_over_m1_zone_geometric_volume":
              [yb/xa for xa,yb in zip(a["qp_spatial_volumes_m3"],
                                      b["qp_spatial_volumes_m3"])],
            "m2_over_m1_north_south_effective_tet_volume":
              [yb/xa for xa,yb in zip(a["qp_north_south_effective_tet_volume_m3"],
                                      b["qp_north_south_effective_tet_volume_m3"])]}
    ensure(all(abs(s["curved_CAD_rel_error"])<.005 for s in (s1,s2)),
           "direct mesh curved volume/CAD mismatch")
    ensure(abs(sum(x["qp_region_volume_m3"] for x in rows1)-s1["curved_volume_sum_m3"])<1e-16 and
           abs(sum(x["qp_region_volume_m3"] for x in rows2)-s2["curved_volume_sum_m3"])<1e-16,
           "QP spatial global volume closure")
    summary={"protocol":"P10ED_R1_INDEPENDENT_RAW_MSH2_CURVED27QP_QP_SPATIAL_DENSITY",
      "raw_meshes_not_published":True,"no_Gmsh_no_FEM_no_markers":True,
      "quadrature":"3x3x3 Duffy Gauss, independent vectorized Tet10 Lagrange",
      "polar_analytical_volume_m3":{"0_100um_both_poles":.2*(4*math.pi/3)*(.0011**3-.001**3),
                                    "100_500um_both_poles":.2*(4*math.pi/3)*(.0015**3-.0011**3)},
      "mesh_sha256":{"M1":M1_SHA,"M2":M2_SHA},"cad_volume_m3":CAD_VOL,
      "raw_M1":s1,"raw_M2":s2,"qp_spatial_partition":"9 fixed radial x abs(mu) zones; piecewise assigned at each curved QP",
      "spatial_indicator_quadrature_refinement":spatial_refinements,
      "effective_tet_count":"N_eff(zone)=sum(QP_volume_in_zone / full_curved_tet_volume)",
      "effective_local_cell_volume":"QP_region_volume / fractional_N_eff; spatially matched domain not identical tets",
      "comparison_limit":"27QP step-zone membership is coarse near boundaries; nearest centroids are not paired elements",
      "target_not_guaranteed_by_gmsh":True,"physical_FEM":0}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/"P10ED_RAW_M1_M2_DIRECT_AUDIT.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for name,records in (("P10ED_RAW_M1_M2_9_ZONE_QP_SPATIAL.csv", rows1+rows2),
                         ("P10ED_RAW_M1_M2_9_ZONE_COMPARISON.csv",comparable)):
        with (args.out/name).open("w",encoding="utf-8",newline="") as stream:
            w=csv.DictWriter(stream,fieldnames=list(records[0]),lineterminator="\n")
            w.writeheader();w.writerows(records)
    print("P10ED_RAW_M1_M2_DIRECT_27QP_PASS", "M1",s1["tet10"],
          "M2",s2["tet10"],"QP",s2["curved_27qp"],
          "hotspot_qp_effective_ratio",format(comparable[0]["m2_over_m1_effective_tet_volume"],".8g"),
          "FEM=0")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
