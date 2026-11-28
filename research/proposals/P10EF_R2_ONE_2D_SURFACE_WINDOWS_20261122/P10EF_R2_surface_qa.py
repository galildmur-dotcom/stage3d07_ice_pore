#!/usr/bin/env python3
"""Read-only curved Tri6 pore surface QA; stdlib only, no native Gmsh/FEM."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
M2_SHA = "ba1f1a0553a568c1b399acadd52bce1c1dc32e8d1c6b3ab1ce6759c547e5dee5"
CENTRE = (0.0, 0.0, .03)
R = .001
CAP_MU = .8
EDGES = ((0, 1), (1, 2), (2, 0))


def check(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError("P10EF_R2_SURFACE_QA_STOP: " + reason)


def digest(file: Path) -> str:
    h = hashlib.sha256()
    with file.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_msh2(file: Path, *, expected: str | None = None) -> dict:
    check(file.is_file(), "missing MSH " + str(file))
    actual = digest(file)
    if expected is not None:
        check(actual == expected, "original raw mesh SHA differs")
    with file.open("r", encoding="ascii", errors="strict") as src:
        check(next(src).strip() == "$MeshFormat" and
              next(src).strip() == "2.2 0 8" and
              next(src).strip() == "$EndMeshFormat", "MSH2 ASCII format")
        physical = {}
        for line in src:
            if line.strip() == "$PhysicalNames":
                for _ in range(int(next(src))):
                    dim, tag, name = next(src).strip().split(maxsplit=2)
                    physical[(int(dim), int(tag))] = name.strip('"')
                check(next(src).strip() == "$EndPhysicalNames", "physical closing")
            if line.strip() == "$Nodes":
                break
        else:
            check(False, "no nodes")
        nodes = {}
        for _ in range(int(next(src))):
            a = next(src).split()
            check(len(a) == 4, "node line width")
            idx = int(a[0]); check(idx not in nodes, "duplicate node")
            nodes[idx] = tuple(map(float, a[1:]))
        check(next(src).strip() == "$EndNodes", "nodes closing")
        check(next(src).strip() == "$Elements", "no elements after nodes")
        by_type = Counter(); tri = []; physical_tet = 0
        for _ in range(int(next(src))):
            parts = list(map(int, next(src).split()))
            check(len(parts) >= 5, "element width")
            typ, tags = parts[1:3]
            check(tags >= 2 and len(parts) >= 3 + tags, "element tags")
            by_type[typ] += 1
            phys = parts[3]; ids = parts[3+tags:]
            if typ == 9 and phys == 8:
                check(len(ids) == 6, "Tri6 connectivity")
                tri.append(tuple(ids))
            if typ == 11 and phys == 1:
                physical_tet += 1
        check(next(src).strip() == "$EndElements", "element closing")
        check(not src.read().strip(), "trailing MSH blocks")
    check(physical.get((2, 8)) == "PORE_WALL", "PORE_WALL tag 8")
    check(len(tri) > 0, "no pore curved Tri6")
    check(all(all(i in nodes for i in t) for t in tri), "dangling nodes")
    check(all(math.isfinite(c) for p in nodes.values() for c in p), "nonfinite nodes")
    return {"path": str(file), "sha256": actual, "nodes": nodes,
            "tri": tri, "types": dict(sorted(by_type.items())),
            "physical_tet10": physical_tet}


def gauss(n: int) -> tuple[list[float], list[float]]:
    x, w = [], []
    for i in range(1, n+1):
        z = math.cos(math.pi*(i-.25)/(n+.5))
        for _ in range(40):
            a, b = 1., z
            for k in range(2, n+1):
                a, b = b, ((2*k-1)*z*b-(k-1)*a)/k
            dp = n*(z*b-a)/(z*z-1)
            dz = b/dp; z -= dz
            if abs(dz) < 1e-15:
                break
        check(abs(z) <= 1, "Gauss root")
        x.append((z+1)/2)
        w.append(1/((1-z*z)*dp*dp))
    check(abs(sum(w)-1)<1e-13,"Gauss weights")
    return x, w


def cross_length(a: list[float], b: list[float]) -> float:
    v = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    return math.sqrt(sum(c*c for c in v))


def surface(mesh: dict, nqp: int = 15) -> dict:
    x, w = gauss(nqp)
    qrule = []
    dl = ((-1., -1.), (1., 0.), (0., 1.))
    for a, wa in zip(x, w):
        for b, wb in zip(x, w):
            u, v = a, (1-a)*b
            l = (1-u-v, u, v)
            ns = [t*(2*t-1) for t in l]
            ds = [[(4*l[i]-1)*dl[i][j] for j in (0,1)] for i in range(3)]
            for i,j in EDGES:
                ns.append(4*l[i]*l[j])
                ds.append([4*(l[i]*dl[j][k]+l[j]*dl[i][k]) for k in (0,1)])
            qrule.append((ns, ds, wa*wb*(1-a)))
    check(abs(sum(q[2] for q in qrule)-.5)<1e-13, "Tri6 quadrature weights")
    zones = {z:{"area":0., "frac":0.} for z in ("north","south","both_poles","nonpolar")}
    area_total = 0.; max_deviation = 0.; smallest_jac = float("inf")
    by_centroid = {"north":[], "south":[]}
    nearest = {"north":float("inf"), "south":float("inf")}
    used = set()
    for ids in mesh["tri"]:
        pp = [mesh["nodes"][k] for k in ids]
        used.update(ids)
        qdata = []; elem_area = 0.
        for ns, ds, qw in qrule:
            xyz = [sum(ns[i]*pp[i][c] for i in range(6)) for c in range(3)]
            du = [sum(ds[i][0]*pp[i][c] for i in range(6)) for c in range(3)]
            dv = [sum(ds[i][1]*pp[i][c] for i in range(6)) for c in range(3)]
            jac = cross_length(du, dv)
            smallest_jac = min(smallest_jac,jac)
            rho = math.sqrt(sum((xyz[c]-CENTRE[c])**2 for c in range(3)))
            check(rho>0, "QP zero radius")
            max_deviation = max(max_deviation,abs(rho-R))
            mu = (xyz[2]-CENTRE[2])/rho
            da = jac*qw
            qdata.append((mu, da))
            elem_area += da
        check(elem_area>0, "Tri6 non-positive area")
        area_total += elem_area
        for mu, da in qdata:
            zone_list = ("north", "both_poles") if mu>=CAP_MU else (
                ("south","both_poles") if mu<=-CAP_MU else ("nonpolar",))
            for z in zone_list:
                zones[z]["area"] += da
                zones[z]["frac"] += da/elem_area
        pcent = [sum(p[c] for p in pp[:3])/3 for c in range(3)]
        cr = math.sqrt(sum((pcent[c]-CENTRE[c])**2 for c in range(3)))
        for z, sign in (("north",1),("south",-1)):
            if sign*(pcent[2]-CENTRE[2])/cr >= CAP_MU:
                by_centroid[z].extend(math.dist(pp[i],pp[j])*1000 for i,j in EDGES)
    for i in used:
        for z, sign in (("north",1),("south",-1)):
            nearest[z] = min(nearest[z], math.dist(mesh["nodes"][i],
                (0.,0.,.03+sign*R))*1000)
    check(smallest_jac>1e-16,"degenerate Tri6 Jacobian")
    check(max_deviation < 5e-6, "surface QP far from 1mm spherical pore")
    check(abs(area_total/(4*math.pi*R*R)-1)<.06,
          "full curved pore area differs >6% from analytic")
    for z in zones:
        area = zones[z]["area"]
        fraction = zones[z]["frac"]
        check(fraction>0, "no surface QPs in zone "+z)
        zones[z] = {"curved_qp_area_m2":area,
            "fractional_surface_tri6":fraction,
            "effective_curved_Tri6_area_m2":area/fraction}
    return {"pore_tri6":len(mesh["tri"]), "node_count":len(mesh["nodes"]),
        "element_types":mesh["types"],"physical_tet10":mesh["physical_tet10"],
        "surface_qp_order":nqp,"curved_pore_area_m2":area_total,
        "analytic_pore_area_m2":4*math.pi*R*R,
        "relative_area_error":area_total/(4*math.pi*R*R)-1,
        "max_qp_radial_deviation_m":max_deviation,"min_jacobian":smallest_jac,
        "zones":zones,"nearest_pole_node_mm":nearest,
        "corner_edge_samples_mm":{k:len(v) for k,v in by_centroid.items()}}


def audit(m1: Path, old_m2: Path, candidate: Path, out: Path) -> dict:
    original = parse_msh2(m1,expected=M1_SHA)
    previous = parse_msh2(old_m2,expected=M2_SHA)
    new = parse_msh2(candidate)
    check(new["physical_tet10"]==0 and new["types"].get(11,0)==0,
          "new experiment is 2D ONLY, no Tet10 allowed")
    reference, historical, test = (surface(x) for x in (original,previous,new))
    target = .8**(2/3)
    ratios = {z:{"candidate_over_m1":test["zones"][z]["effective_curved_Tri6_area_m2"] /
              reference["zones"][z]["effective_curved_Tri6_area_m2"],
              "historical_m2_over_m1":historical["zones"][z]["effective_curved_Tri6_area_m2"] /
              reference["zones"][z]["effective_curved_Tri6_area_m2"],
              "target_at_kappa_1":target}
              for z in ("north","south","both_poles","nonpolar")}
    data = {"status":"P10EF_R2_GEOMETRY_QA_OK_ADAPTATION_UNDECIDED_NO_FEM",
        "m1_sha256":original["sha256"],"historical_m2_sha256":previous["sha256"],
        "candidate_2d_sha256":new["sha256"],"original_m1":reference,
        "historical_m2":historical,"candidate_2d":test,
        "effective_curved_tri6_area_ratios":ratios,
        "interpretation":"compare measured area ratios against 0.8^(2/3), not a guaranteed acceptance",
        "native_3d_attempts":0,"physical_fem_attempts":0}
    out.mkdir(parents=True,exist_ok=True)
    (out/"P10EF_R2_SURFACE_QP_AUDIT.json").write_text(
         json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return data


def selftest() -> None:
    a,w = gauss(15)
    check(len(a)==15 and abs(sum(w)-1)<1e-13,"Gauss15")
    temp = {"nodes": {1:(0.,0.,0.),2:(.001,0.,0.),3:(0.,.001,0.),
            4:(.0005,0.,0.),5:(.0005,.0005,0.),6:(0.,.0005,0.)},
            "tri":[(1,2,3,4,5,6)]}
    # Flat Tri6 selftest evaluates the same basis without spherical-pore check.
    dl = ((-1.,-1.),(1.,0.),(0.,1.)); pts = [temp["nodes"][i] for i in temp["tri"][0]]
    u,v = .23,.37; l = (1-u-v,u,v)
    n = [t*(2*t-1) for t in l]+[4*l[i]*l[j] for i,j in EDGES]
    check(abs(sum(n)-1)<1e-14 and abs(sum(n[i]*pts[i][0] for i in range(6))-.001*u)<1e-15,
          "flat quadratic Tri6 basis")
    print("P10EF_R2_QA_SELFTEST_PASS GL15 Tri6 partition affine=PASS native=0 FEM=0")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest",action="store_true")
    parser.add_argument("--m1",type=Path)
    parser.add_argument("--old-m2",type=Path)
    parser.add_argument("--candidate",type=Path)
    parser.add_argument("--out",type=Path)
    args = parser.parse_args()
    selftest()
    if not args.selftest:
        check(all((args.m1,args.old_m2,args.candidate,args.out)),"all input paths required")
        result = audit(args.m1,args.old_m2,args.candidate,args.out)
        print(result["status"], "north",result["effective_curved_tri6_area_ratios"]["north"]["candidate_over_m1"],
              "south",result["effective_curved_tri6_area_ratios"]["south"]["candidate_over_m1"])
