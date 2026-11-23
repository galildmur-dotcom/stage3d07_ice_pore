#!/usr/bin/env python3
"""Independently verify native P10GD 2D meshes and quantify polar triangle quality.

Read-only Gmsh-independent audit; raw MSH stays inside user's private ZIP.
qcorner = 4 sqrt(3) A / sum(edge^2); 1 for equilateral triangles.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from zipfile import ZipFile


def need(ok, why):
    if not ok:
        raise RuntimeError("P10GE_SURFACE_INDEPENDENT_STOP: " + why)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def parse_surface(payload):
    lines = payload.decode("ascii").splitlines()
    n = lines.index("$Nodes")
    count = int(lines[n + 1]); nodes = {}
    for row in lines[n + 2:n + 2 + count]:
        data = row.split()
        need(len(data) == 4, "bad MSH2 node row")
        nodes[int(data[0])] = tuple(map(float, data[1:]))
    i = lines.index("$Elements"); count = int(lines[i + 1])
    triangles = []
    for row in lines[i + 2:i + 2 + count]:
        a = list(map(int, row.split()))
        if a[1] == 9 and a[2] >= 1 and a[3] == 8:
            need(len(a[3+a[2]:]) == 6, "bad pore Tri6")
            triangles.append(a[3+a[2]:])
    need(len(triangles) > 100, "not a pore surface mesh")
    bins = defaultdict(list); radius_error = 0.; worst = None
    for ids in triangles:
        pts = [nodes[j] for j in ids[:3]]
        for j in ids:
            x, y, z = nodes[j]
            radius_error = max(radius_error, abs(math.sqrt(x*x+y*y+(z-.03)**2)-.001))
        u = [pts[1][j]-pts[0][j] for j in range(3)]
        v = [pts[2][j]-pts[0][j] for j in range(3)]
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2],
                 u[0]*v[1]-u[1]*v[0])
        area = .5 * math.sqrt(sum(x*x for x in cross))
        edge = [math.dist(pts[k], pts[(k+1)%3]) for k in range(3)]
        q = 4*math.sqrt(3)*area/sum(s*s for s in edge)
        centroid = tuple(sum(p[j] for p in pts)/3 for j in range(3))
        x, y, z = centroid; r = math.sqrt(x*x+y*y+(z-.03)**2)
        mu = (z-.03)/r
        signed = ("N_" if mu>=0 else "S_") + (
            "polar" if abs(mu)>=.8 else "taper" if abs(mu)>.6 else "off")
        bins[signed].append(q)
        if worst is None or q < worst["qcorner"]:
            worst = {"qcorner":q, "mu":mu, "centroid_m":centroid}
    need(radius_error < 2e-13, "not exact spherical pore")
    summaries = {k: {"tri6":len(v), "min_qcorner":min(v),
                     "median_qcorner":statistics.median(v)}
                 for k,v in bins.items()}
    need(len(summaries) == 6, "missing signed surface sector")
    return {"pore_tri6":len(triangles),"max_pore_node_radius_error_m":radius_error,
            "min_qcorner":worst["qcorner"],
            "median_qcorner":statistics.median(q for v in bins.values() for q in v),
            "worst_triangle":worst,"signed_surface_quality":summaries}


def analyze(path):
    with ZipFile(path) as z:
        need(z.testzip() is None,"broken ZIP CRC")
        manifest=json.loads(z.read("P10GD_SURFACE_SWEEP_METRICS.json"))
        need(manifest.get("status") == "P10GD_SURFACE_ONLY_PASS_NO_3D_NO_FEM" and
             len(manifest["results"]) == 9 and
             manifest.get("native_3d_attempts") == 0 and
             manifest.get("FEM_attempts") == 0,
             "evidence is not successful 2D-only sweep")
        out=[]
        for item in manifest["results"]:
            theta=item["theta"]; code=f"{int(round(theta*1000)):04d}"
            name=f"P10GD_SURFACE_T{code}"
            geo=z.read(name+".geo")
            mesh=z.read(name+"_2D.msh")
            need(sha_bytes(geo)==item["GEO_sha256"] and
                 sha_bytes(mesh)==item["native_2d_sha256"],
                 "changed source or raw 2D probe: "+name)
            need(b"Error" not in z.read(name+"_2D.log") and
                 b"Done meshing 2D" in z.read(name+"_2D.log"),
                 "native Gmsh 2D error")
            measured=parse_surface(mesh)
            need(measured["pore_tri6"]==item["surface"]["pore_tri6"],
                 "independent pore count mismatch")
            for key, row in measured["signed_surface_quality"].items():
                need(row["tri6"]==item["surface"]["signed_surface_bins"][key]["tri6"],
                     "independent signed zone count mismatch: "+key)
            out.append({"theta":theta, "source_geo_sha256":item["GEO_sha256"],
                        "raw_msh2_sha256":item["native_2d_sha256"], **measured})
    return {"protocol":"P10GE_INDEPENDENT_P10GD_NATIVE_2D_POLE_CORNER_QUALITY",
            "evidence_zip_sha256":sha_bytes(path.read_bytes()),
            "not_3d_and_not_FEM":True,
            "raw_surface_meshes_remain_private":True,
            "qcorner_definition":"4*sqrt(3)*corner_triangle_area/sum(corner_edge_length_squared)",
            "results":out}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    result=analyze(a.evidence)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("x",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
        f.write("\n")
    print("P10GE_2D_AUDIT_PASS",len(result["results"]),"fields",flush=True)
