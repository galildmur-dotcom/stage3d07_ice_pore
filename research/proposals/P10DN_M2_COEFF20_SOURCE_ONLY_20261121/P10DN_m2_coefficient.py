#!/usr/bin/env python3
"""Continuous spatial M2 coefficient: 0<=kappa<=1, Vtarget/V_M1=1-0.2*kappa.

SOURCE-ONLY: --selftest or --label-m1 (read-only M1.msh + small CSV/JSON).
Never starts Gmsh, never solves physical FEM, never creates a one-shot marker.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
M1_SHA = "ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f"
M1_NAME = "P10DG_M1_CANDIDATE.msh"
M1_DEFAULT = Path(r"G:\Downloads\P10DG_R1_M1_EMPIRICAL_H0_MESH_ONLY_WINDOWS_20261121\P10DG_RUNS\P10DG_M1_20261121_120324_362583\P10DG_M1_CANDIDATE.msh")
PIN = HERE / "P10DN_SOURCE_SHA256SUMS.txt"

# Geometry: metres. Sphere radius 1mm, center (0,0,30mm).
PORE_R = 0.001
PORE_CX = 0.0
PORE_CY = 0.0
PORE_CZ = 0.03
R_FULL = 0.0001       # 100 µm: full radial priority, derived from P10DM
R_ZERO = 0.0005       # smoothly reach zero by 500 µm
MU_ZERO = 0.6         # below |cos(theta)|=.6 no new refinement
MU_FULL = 0.8         # complete polar outer bin |mu|>=.8 full priority
MAX_VOLUME_REDUCTION = 0.20


def require(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError("P10DN_SOURCE_STOP: " + why)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_source() -> int:
    require(PIN.is_file(), "source inventory absent; extract the whole ZIP")
    lines = PIN.read_text(encoding="utf-8").splitlines()
    require(len(lines) >= 5, "incomplete source-only package")
    seen = set()
    for line in lines:
        require(len(line) > 66 and line[64:66] == "  ", "malformed SHA inventory")
        digest, name = line[:64], line[66:]
        require(name not in seen and all(c in "0123456789abcdef" for c in digest),
                "duplicate or malformed source SHA")
        seen.add(name)
        src = HERE / name
        require(src.is_file() and sha256(src) == digest,
                "pinned source changed: " + name)
    require({"P10DN_m2_coefficient.py", "P10DN_M2_FIELD20.geo",
             "sphere_pore_B6_refined.geo", "01_P10DN_LABEL_M1_ONLY.cmd",
             "README_RU.md"} <= seen, "missing field/CAD/source code")
    return len(lines)


def smoothstep(u: float) -> float:
    v = min(1.0, max(0.0, u))
    return v * v * (3.0 - 2.0 * v)


def spherical(x: float, y: float, z: float) -> tuple[float, float]:
    dx, dy, dz = x-PORE_CX, y-PORE_CY, z-PORE_CZ
    rho = math.sqrt(dx*dx + dy*dy + dz*dz)
    # The point rho=0 is inside the excluded void. Define a harmless value.
    return rho-PORE_R, dz/rho if rho else 0.0


def kappa_xyz(x: float, y: float, z: float) -> float:
    d, mu = spherical(x, y, z)
    ur = (d-R_FULL)/(R_ZERO-R_FULL)
    ua = (mu*mu-MU_ZERO**2)/(MU_FULL**2-MU_ZERO**2)
    k = (1.0-smoothstep(ur))*smoothstep(ua)
    require(-1e-14 <= k <= 1+1e-14, "coefficient out of [0,1]")
    return min(1.0, max(0.0, k))


def volume_ratio(kappa: float) -> float:
    return 1.0-MAX_VOLUME_REDUCTION*kappa


def size_ratio(kappa: float) -> float:
    return volume_ratio(kappa)**(1.0/3.0)


def selftest() -> None:
    c=PORE_CZ
    for z in (c+PORE_R+R_FULL*.5, c-PORE_R-R_FULL*.5):
        require(kappa_xyz(0,0,z) == 1.0, "polar full coefficient is not 1")
        require(math.isclose(volume_ratio(kappa_xyz(0,0,z)), .8, abs_tol=1e-15),
                "polar target volume must be exactly 80%")
    require(kappa_xyz(PORE_R+R_FULL*.5, 0, c) == 0.0,
            "equatorial region must be zero new refinement")
    require(kappa_xyz(0,0,c+PORE_R+R_ZERO) == 0.0,
            "far from pore new refinement must vanish exactly")
    require(math.isclose(size_ratio(1), .8**(1/3), rel_tol=1e-15),
            "cubic size-to-volume scaling wrong")
    intermediate = kappa_xyz((PORE_R+.0003)*math.sqrt(.5), 0,
                             c+(PORE_R+.0003)*math.sqrt(.5))
    require(0 < intermediate < 1, "transition coefficient must be strictly intermediate")
    # Explicit Cartesian pole test: no phi dependence, no theta/phi singularity.
    for d in (0.0, .00005, .0002, .0004, .001, .01):
        for mu in (-1., -.9, -.7, -.6, 0., .6, .7, .9, 1.):
            for phi in (0., .2, .9, 1.7, 3.14, 5.6):
                rad = PORE_R+d
                xy = rad*math.sqrt(max(0.,1.-mu*mu))
                k = kappa_xyz(xy*math.cos(phi), xy*math.sin(phi), c+rad*mu)
                require(0 <= k <= 1 and .8 <= volume_ratio(k) <= 1.0,
                        "field bounds violated")
                require(math.isclose(k,kappa_xyz(xy,0,c+rad*mu),abs_tol=2e-13),
                        "unwanted phi dependence near the pole")
    # Finite slope and continuous first derivative at both taper junctions.
    for radius in (R_FULL, R_ZERO):
        eps=1e-8
        k0=kappa_xyz(0,0,c+PORE_R+radius)
        before=kappa_xyz(0,0,c+PORE_R+radius-eps)
        after=kappa_xyz(0,0,c+PORE_R+radius+eps)
        require(abs(after+before-2*k0)<1e-6, "non-smooth radial junction")
    for mu in (MU_ZERO,MU_FULL):
        eps=1e-6
        rad=PORE_R+.00005
        def k_at(m):
            return kappa_xyz(rad*math.sqrt(1-m*m),0,c+rad*m)
        require(abs(k_at(mu+eps)+k_at(mu-eps)-2*k_at(mu))<1e-6,
                "non-smooth angular junction")
    print("P10DN_M2_20PCT_FIELD_SELFTEST_OK kappa=[0,1] "
          "V_ratio=[0.8,1] h_ratio_min=" + format(size_ratio(1), ".15g") +
          " smooth=C1 azimuth_axisymmetric=1 mesh=NOT_BUILT FEM=0")


def parse_msh2(path: Path) -> tuple[dict[int, tuple[float,float,float]], list[tuple[int,list[int]]], int]:
    require(path.is_file() and path.name == M1_NAME,
            "only the original accepted M1 .msh is allowed")
    require(sha256(path) == M1_SHA,
            "exact D-019 M1 file SHA mismatch; H0/other M1 forbidden")
    lines = path.read_text(encoding="ascii", errors="strict").splitlines()
    require(len(lines)>100 and lines[0]=="$MeshFormat" and
            lines[1].split()[:2] == ["2.2", "0"],
            "expected ASCII Gmsh MSH2 v2.2")
    ix = lines.index("$Nodes")
    nodes_count = int(lines[ix+1])
    require(nodes_count == 14145, "M1 node count changed")
    nodes={}
    for line in lines[ix+2:ix+2+nodes_count]:
        parts=line.split()
        require(len(parts)==4,"malformed MSH2 node")
        node_id=int(parts[0])
        require(node_id not in nodes,"duplicate MSH2 node id")
        coords=tuple(map(float,parts[1:]))
        require(all(math.isfinite(c) for c in coords), "invalid coordinate")
        nodes[node_id]=coords
    ix=lines.index("$Elements")
    num_elements=int(lines[ix+1])
    tets=[]
    pore_count=0
    for line in lines[ix+2:ix+2+num_elements]:
        parts=list(map(int,line.split()))
        require(len(parts)>=4,"incomplete MSH2 element")
        eid,typ,ntags=parts[:3]
        require(ntags>=2 and len(parts)>=3+ntags,"malformed element tags")
        physical=parts[3]
        connectivity=parts[3+ntags:]
        if typ==11:  # MSH2 quadratic tetrahedron
            require(len(connectivity)==10 and physical==1,"Tet10 physical group/connectivity")
            tets.append((eid,connectivity))
        elif typ==9 and physical==8:  # quadratic triangle on pore wall
            require(len(connectivity)==6,"Tri6 wall connectivity")
            pore_count+=1
    require(len(tets)==9736 and pore_count==178,
            "accepted M1 Tet10/pore Tri6 counts changed")
    return nodes,tets,pore_count


def label_m1(path: Path, output_root: Path) -> Path:
    nodes,tets,pore_count=parse_msh2(path)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    target=output_root/("P10DN_M1_COEFF_ONLY_"+stamp)
    target.mkdir(parents=True,exist_ok=False)
    csvpath=target/"P10DN_M1_TET10_COEFFICIENTS.csv"
    counts={"zero":0,"one":0,"intermediate":0}
    sum_k=0.
    with csvpath.open("x",encoding="utf-8",newline="") as f:
        writer=csv.writer(f,lineterminator="\n")
        writer.writerow(["tet10_id","centroid_x_m","centroid_y_m","centroid_z_m",
                         "radial_distance_mm","mu","kappa_center","kappa_min_nodes",
                         "kappa_max_nodes","target_volume_over_M1","target_size_over_M1"])
        for element_id,connectivity in tets:
            verts=[nodes[i] for i in connectivity[:4]]
            cx,cy,cz=(sum(p[j] for p in verts)/4 for j in range(3))
            k=kappa_xyz(cx,cy,cz)
            kvals=[kappa_xyz(*nodes[i]) for i in connectivity]
            d,mu=spherical(cx,cy,cz)
            writer.writerow([element_id,cx,cy,cz,d*1000,mu,k,min(kvals),max(kvals),
                             volume_ratio(k),size_ratio(k)])
            if k==0:counts["zero"]+=1
            elif k==1:counts["one"]+=1
            else:counts["intermediate"]+=1
            sum_k+=k
    require(sum(counts.values())==9736,"some elements were not labelled")
    summary={
        "protocol":"P10DN_M1_CONTINUOUS_KAPPA20_SOURCE_ONLY",
        "m1_sha256":M1_SHA,"nodes":len(nodes),"tet10":len(tets),
        "pore_tri6":pore_count,"label_counts":counts,
        "mean_kappa_at_linear_centroid":sum_k/len(tets),
        "target_relative_volume_min":.8,"target_relative_volume_max":1.,
        "target_relative_size_min":size_ratio(1),
        "field":"C1 compact radial 0.1-to-0.5mm times mu² angular 0.6-to-0.8",
        "angular_azimuth":"phi-independent to avoid fitting sparse P10DN sectors",
        "note":"centroid is linear 4-corner centroid, not curved27QP volume average; no M2 mesh or FEM",
    }
    (target/"P10DN_M1_COEFFICIENT_SUMMARY.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P10DN_M1_TET10_COEFFICIENTS_OK tet10=9736 zero="+str(counts["zero"])+
          " intermediate="+str(counts["intermediate"])+" one="+str(counts["one"])+
          " no_Gmsh=1 physical_FEM=0")
    print("SOURCE_ONLY_OUTPUT:",target)
    return target


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--selftest",action="store_true")
    p.add_argument("--label-m1",action="store_true")
    p.add_argument("--mesh",type=Path)
    args=p.parse_args()
    if args.selftest:
        require(not args.label_m1 and args.mesh is None, "selftest must be isolated")
        selftest()
        return 0
    require(args.label_m1,"only --selftest or --label-m1 allowed; NO Gmsh/FEM")
    count=check_source()
    print("P10DN_SOURCE_PIN_OK",count,"files no_Gmsh=1 physical_FEM=0")
    mesh=args.mesh
    if mesh is None:
        entered=input("Exact original M1.msh path (Enter=historical P10DG folder): ").strip().strip('"').strip("'")
        mesh=Path(entered) if entered else M1_DEFAULT
    label_m1(mesh,HERE/"P10DN_OUTPUT")
    return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (ValueError,RuntimeError,OSError) as exc:
        print("P10DN_STOP:",exc,file=sys.stderr)
        raise SystemExit(2)
