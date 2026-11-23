#!/usr/bin/env python3
"""Independent P10GH real MSH2/Tri6 audit, offline and read-only.

Does not import P10GH_surface_compare. No Gmsh, no 3D, no FEM.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

R = 0.001
B6 = 0.006
CENTRE = (0., 0., 0.03)


def ensure(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sub(a, b):
    return tuple(x-y for x, y in zip(a,b))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def norm(a):
    return math.sqrt(dot(a,a))


def quantile(seq, p):
    x=sorted(seq); z=p*(len(x)-1); lo=math.floor(z); hi=math.ceil(z)
    return x[lo]*(hi-z)+x[hi]*(z-lo) if lo!=hi else x[lo]


def jac7(t, r, s):
    # Independent quadratic Lagrange shape derivative in (r,s) coordinates.
    a=1-r-s
    dr=(1-4*a, 4*r-1, 0, 4*(a-r), 4*s, -4*s)
    ds=(1-4*a, 0, 4*s-1, -4*r, 4*r, 4*(a-s))
    xr=tuple(sum(dr[i]*t[i][k] for i in range(6)) for k in range(3))
    xs=tuple(sum(ds[i]*t[i][k] for i in range(6)) for k in range(3))
    return norm(cross(xr,xs))


# Degree-5 Dunavant 7-point quadrature; reference area is 1/2.
QUAD=[(1/3,1/3,.1125)]
for a,b,w in ((.059715871789770,.470142064105115,.066197076394253),
               (.797426985353087,.101286507323456,.062969590272414)):
    QUAD.extend(((a,b,w),(b,a,w),(b,b,w)))


def parse_msh2(data):
    ensure(len(data)<=12*1024**2, "oversized MSH")
    f=io.StringIO(data.decode("ascii")); nodes={}; surfaces=defaultdict(list)
    kinds=Counter(); version=False
    for raw in f:
        line=raw.strip()
        if line=="$MeshFormat":
            ensure(next(f).strip()=="2.2 0 8", "not ASCII MSH2.2")
            version=True
        elif line=="$Nodes":
            count=int(next(f)); ensure(0<count<500000,"node limit")
            for _ in range(count):
                parts=next(f).split()
                ensure(len(parts)==4,"malformed node")
                node=int(parts[0]);ensure(node not in nodes,"duplicate node")
                nodes[node]=tuple(map(float,parts[1:]))
        elif line=="$Elements":
            count=int(next(f));ensure(0<count<500000,"element limit")
            for _ in range(count):
                parts=list(map(int,next(f).split()))
                ensure(len(parts)>=4,"malformed element")
                kind,ntags=parts[1:3]; kinds[kind]+=1
                ensure(kind==9,"unexpected non-Tri6 element type "+str(kind))
                ensure(ntags>=1 and len(parts)==3+ntags+6,"malformed Tri6")
                physical=parts[3];ensure(physical in range(2,10),"bad physical tag")
                ids=parts[3+ntags:];ensure(len(set(ids))==6,"duplicate Tri6 node")
                ensure(all(v in nodes for v in ids),"missing node")
                surfaces[physical].append(ids)
    ensure(version and set(surfaces)==set(range(2,10)),"missing format/physical groups")
    ensure(sum(len(v) for v in surfaces.values())==sum(kinds.values()),"counts")
    return nodes,surfaces,kinds


def audit(data):
    nodes,surfaces,kinds=parse_msh2(data)
    result={"nodes":len(nodes),"Tri6":sum(kinds.values()),
            "physical_counts":{str(k):len(v) for k,v in sorted(surfaces.items())}}
    for physical,rad in ((8,R),(9,B6)):
        qualities=[]; area=0.; jacmin=float("inf"); rmax=0.;
        signs=[]; mids={}; edges=Counter(); cornerids=set(); pole={"N":[],"S":[]}
        worst=(float("inf"),None,None)
        for ids in surfaces[physical]:
            pts=[nodes[i] for i in ids]
            x,y,z=pts[:3]
            vec=cross(sub(y,x),sub(z,x))
            lengths=(norm(sub(y,x))**2,norm(sub(z,y))**2,norm(sub(x,z))**2)
            q=2*math.sqrt(3)*norm(vec)/sum(lengths)
            ensure(math.isfinite(q) and q>.001,"bad corner quality")
            qualities.append(q)
            centroid=tuple((x[k]+y[k]+z[k])/3 for k in range(3))
            mu=(centroid[2]-.03)/norm(sub(centroid,CENTRE))
            if mu>=.8:pole["N"].append(q)
            if mu<=-.8:pole["S"].append(q)
            if q<worst[0]:worst=(q,centroid,mu)
            signs.append(dot(vec,sub(centroid,CENTRE)))
            cornerids.update(ids[:3])
            for a,b,m in ((ids[0],ids[1],ids[3]),
                          (ids[1],ids[2],ids[4]),
                          (ids[2],ids[0],ids[5])):
                edge=tuple(sorted((a,b)));edges[edge]+=1
                if edge in mids:ensure(mids[edge]==m,"midpoint mismatch")
                mids[edge]=m
            for pt in pts:
                rmax=max(rmax,abs(norm(sub(pt,CENTRE))-rad))
            for rr,ss,w in QUAD:
                j=jac7(pts,rr,ss);ensure(j>0 and math.isfinite(j),"curved Jacobian")
                jacmin=min(jacmin,j);area+=w*j
        ensure(len(pole["N"]) and len(pole["S"]),"polar coverage")
        ensure(all(v==2 for v in edges.values()),"non-closed physical sphere")
        ensure(len(cornerids)-len(edges)+len(surfaces[physical])==2,
               "sphere Euler characteristic not two")
        ensure(rmax<1e-8,"CAD radius mismatch")
        ensure(all(v<0 for v in signs) or all(v>0 for v in signs),
               "inconsistent surface orientation")
        result[str(physical)]={
            "min_q":min(qualities),"p05_q":quantile(qualities,.05),
            "median_q":statistics.median(qualities),
            "north_count":len(pole["N"]),"south_count":len(pole["S"]),
            "north_qmin":min(pole["N"]),"south_qmin":min(pole["S"]),
            "worst_xyz_m":worst[1],"worst_mu":worst[2],
            "curved_area_7pt_m2":area,"area_ratio_exact":area/(4*math.pi*rad**2),
            "min_jacobian_7pt":jacmin,"max_radius_error_m":rmax,
            "corner_vertices":len(cornerids),"unique_corner_edges":len(edges),
            "euler_characteristic":len(cornerids)-len(edges)+len(surfaces[physical]),
            "every_edge_twice":True,"shared_midside_nodes":True,
            "normal_sign":1 if signs[0]>0 else -1,
        }
    return result


def main(zip_path):
    blob=Path(zip_path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names=z.namelist();ensure(len(names)==12 and len(set(names))==12,
                                  "unexpected evidence entries")
        ensure(all("/" not in n and "\\" not in n for n in names),"unsafe names")
        ensure(z.testzip() is None,"corrupted ZIP")
        report=json.loads(z.read("P10GH_CAD_POLE_METRICS.json"))
        ensure(report["status"]=="P10GH_SURFACE_ONLY_PASS_NO_3D_NO_FEM",
               "native status")
        ensure(report["native_2d_attempts"]==2 and report["native_3d_attempts"]==0
               and report["FEM_attempts"]==0,"unexpected attempts")
        ensure(report["installed"]["gmsh_version"].strip()=="4.15.2",
               "unexpected native Gmsh version")
        ensure(report["installed"]["M0_sha256"]==
               "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6",
               "unrecognized canonical M0")
        ensure(sha(z.read("P10GH_SOURCE_SHA256.json"))==
               report["installed"]["source_pin_sha256"],"source pin changed")
        for name, expected in report["generated_sha256"].items():
            ensure(sha(z.read(name))==expected,"generated GEO SHA mismatch: "+name)
        ensure(report["generated_sha256"]["M0.geo"]==
               "ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa",
               "canonical M0 geo changed")
        ensure(report["generated_sha256"]["sphere_pore_B6_refined.geo"]==
               "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0",
               "canonical CAD changed")
        o=z.read("sphere_pore_B6_refined.geo").decode("utf-8")
        rr=z.read("sphere_pore_B6_refined_rotated.geo").decode("utf-8")
        anchor="Sphere(3) = {poreCX,poreCY,poreCZ,r0};"
        rotate="Rotate { {1,0,0}, {poreCX,poreCY,poreCZ}, Pi/2 } { Volume{3}; }"
        ensure(rr.replace(anchor+"\n"+rotate,anchor)==o,
               "CAD variant is not a pure rotation")
        out={"evidence_zip_sha256":sha(blob),"results":{}}
        for label in ("ORIGINAL","ROTATED"):
            msh=z.read(f"P10GH_{label}_2D.msh")
            log=z.read(f"P10GH_{label}_2D.log")
            r=report["results"][label]
            ensure(sha(msh)==r["native"]["msh_sha256"] and
                   sha(log)==r["native"]["log_sha256"],"native hash mismatch")
            ensure(r["native"]["exit_code"]==0 and not r["native"]["stop_reason"],
                   "native STOP")
            txt=log.decode("utf-8-sig",errors="replace")
            ensure("Done meshing 2D" in txt and "-3" not in txt and
                   "Error   :" not in txt,"invalid native log")
            result=audit(msh)
            qa=r["surface"]
            ensure(result["nodes"]==qa["nodes"] and result["Tri6"]==qa["total_tri6"],
                   "mesh count mismatch")
            for key,mkey in (("min_q","q_corner_min"),("p05_q","q_corner_p05"),
                             ("median_q","q_corner_median"),
                             ("north_qmin","north_polar_qmin"),
                             ("south_qmin","south_polar_qmin")):
                ensure(abs(result["8"][key]-qa[mkey])<1e-12,
                       "independent corner quality mismatch: "+key)
            out["results"][label]=result
        a=out["results"]["ORIGINAL"]["8"]
        b=out["results"]["ROTATED"]["8"]
        out["comparison"]={
            "pore_min_q_absolute_gain":b["min_q"]-a["min_q"],
            "pore_min_q_relative_gain":b["min_q"]/a["min_q"]-1,
            "p05_q_delta":b["p05_q"]-a["p05_q"],
            "north_qmin_delta":b["north_qmin"]-a["north_qmin"],
            "south_qmin_delta":b["south_qmin"]-a["south_qmin"],
        }
        out["status"]="P10GI_INDEPENDENT_READ_ONLY_2D_AUDIT_PASS"
    print(json.dumps(out,indent=2,ensure_ascii=False))


if __name__=="__main__":
    ensure(len(sys.argv)==2,"usage: script.py evidence.zip")
    main(sys.argv[1])
