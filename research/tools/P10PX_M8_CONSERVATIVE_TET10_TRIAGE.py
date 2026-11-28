#!/usr/bin/env python3
"""Stage3D07 P10PX: read-only M8.msh curved-Tet10 geometry and bin prefilter.

No CAD, Gmsh operation, mesh mutation, FEM, or adjoint. Strict Gmsh 2.2/Tet10.
Uses convex-hull bounds of the *quadratic Bezier form* of each Tet10 mapping,
therefore every rejected element is guaranteed not to touch the target bin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

PINNED_M8_SHA256 = "40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
CENTER = np.array([0., 0., .03], dtype=np.float64)
PORE_R = .001
RADIAL_LOWER_MM = [0., .02, .05, .1, .25, .5, 1., 2., 5., 15.]
EDGE = np.array([(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
# Gmsh type-11 raw: 01,12,20,03,32,13. Our canonical: 01,02,03,12,13,23.
CANONICAL = np.array([0, 1, 2, 3, 4, 6, 7, 5, 9, 8])


def parse_msh(path: Path):
    nodes: dict[int, list[float]] = {}
    tets = []
    tet_ids = []
    face_tags: dict[int, int] = {}
    types: dict[int, int] = {}
    with path.open(encoding="utf-8") as f:
        for raw in f:
            s = raw.strip()
            if s == "$MeshFormat":
                fmt = next(f).split()
                if fmt != ["2.2", "0", "8"]:
                    raise ValueError("expected ASCII Gmsh 2.2 with 8-byte reals")
            elif s == "$Nodes":
                n = int(next(f))
                for _ in range(n):
                    z = next(f).split()
                    tag = int(z[0])
                    if tag in nodes or len(z) != 4:
                        raise ValueError("duplicate node tag or malformed node")
                    nodes[tag] = [float(z[1]), float(z[2]), float(z[3])]
            elif s == "$Elements":
                n = int(next(f))
                for _ in range(n):
                    z = list(map(int, next(f).split()))
                    tag, typ, nt = z[:3]
                    phys = z[3]
                    conn = z[3+nt:]
                    types[typ] = types.get(typ, 0) + 1
                    if typ == 11:
                        if phys != 1 or len(conn) != 10:
                            raise ValueError("non-ice or non-Tet10 volume element")
                        tet_ids.append(tag)
                        tets.append(conn)
                    elif typ == 9:
                        if len(conn) != 6 or phys not in range(2, 10):
                            raise ValueError("bad Tri6 face")
                        face_tags[phys] = face_tags.get(phys, 0) + 1
                    else:
                        raise ValueError(f"unexpected element type {typ}")
    if not tets or len(face_tags) != 8:
        raise ValueError("missing Tet10 or boundary physical groups")
    keys = sorted(nodes)
    lookup = {key: i for i, key in enumerate(keys)}
    xyz = np.array([nodes[k] for k in keys], dtype=np.float64)
    ids = np.array(tet_ids, dtype=np.int64)
    conn = np.array([[lookup[k] for k in c] for c in tets], dtype=np.int32)
    return xyz, conn[:, CANONICAL], ids, types, face_tags


def tet10_shape(uvw):
    l = np.array([1. - sum(uvw), *uvw])
    d = np.array([[-1., -1., -1.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    N = np.empty(10)
    G = np.empty((10, 3))
    for i in range(4):
        N[i] = l[i] * (2*l[i] - 1)
        G[i] = (4*l[i] - 1) * d[i]
    for i, (a, b) in enumerate(EDGE, start=4):
        N[i] = 4*l[a]*l[b]
        G[i] = 4*(l[a]*d[b] + l[b]*d[a])
    return N, G


def signed_interval(lo, hi, ax, ay):
    low = np.minimum(ax*lo[:, 0], ax*hi[:, 0]) + np.minimum(ay*lo[:, 1], ay*hi[:, 1])
    high = np.maximum(ax*lo[:, 0], ax*hi[:, 0]) + np.maximum(ay*lo[:, 1], ay*hi[:, 1])
    return low, high


def squares(lo, hi):
    mn = np.where((lo <= 0) & (hi >= 0), 0., np.minimum(lo**2, hi**2))
    mx = np.maximum(lo**2, hi**2)
    return mn, mx


def halfspace_gte(lo, hi):
    return np.where(hi < 0, -1, np.where(lo >= 0, 1, 0)).astype(np.int8)


def halfspace_lte(lo, hi):
    return np.where(lo > 0, -1, np.where(hi <= 0, 1, 0)).astype(np.int8)


def candidate_masks(lo, hi, ir, im, ip):
    n = len(lo)
    rho_lo = PORE_R + RADIAL_LOWER_MM[ir]/1000.
    rho_hi = PORE_R + RADIAL_LOWER_MM[ir+1]/1000.
    sqmin, sqmax = squares(lo, hi)
    rmin = sqmin.sum(axis=1)
    rmax = sqmax.sum(axis=1)
    cond = [halfspace_gte(rmin-rho_lo**2, rmax-rho_lo**2),
            halfspace_lte(rmin-rho_hi**2, rmax-rho_hi**2)]
    # Only the two true endcap bins: mu∈[-1,-0.8] or [0.8,1].
    if im not in [0, 9]:
        raise ValueError("this source-only audit is limited to pole endcaps")
    sign = 1 if im == 9 else -1
    cond.append(halfspace_gte(sign*lo[:, 2] if sign == 1 else -hi[:, 2],
                              sign*hi[:, 2] if sign == 1 else -lo[:, 2]))
    mu0=.8
    g_lo=mu0**2*(sqmin[:, 0]+sqmin[:, 1])-(1-mu0**2)*sqmax[:, 2]
    g_hi=mu0**2*(sqmax[:, 0]+sqmax[:, 1])-(1-mu0**2)*sqmin[:, 2]
    cond.append(halfspace_lte(g_lo,g_hi))
    # Target 30-degree azimuth wedges adjacent to phi=0 (bins 5 and 6).
    if ip not in [5, 6]:
        raise ValueError("this source-only audit is limited to azimuth bins 5/6")
    lower=-math.pi+2*math.pi*ip/12
    upper=lower+math.pi/6
    gl,gh=signed_interval(lo,hi,-math.sin(lower),math.cos(lower))
    cond.append(halfspace_gte(gl,gh))
    gl,gh=signed_interval(lo,hi,-math.sin(upper),math.cos(upper))
    cond.append(halfspace_lte(gl,gh))
    status=np.stack(cond,axis=1)
    excluded=(status==-1).any(axis=1)
    inside=(status==1).all(axis=1)
    possible=~excluded
    return possible,inside,status


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mesh",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path("P10PX_M8_READ_ONLY_TRIAGE_QA.json"))
    p.add_argument("--samples",type=Path,default=Path("P10PX_M8_TET10_SAMPLE_NODES.txt"))
    args=p.parse_args()
    digest=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    if digest!=PINNED_M8_SHA256:
        raise SystemExit(f"P10PX_STOP_M8_PIN_MISMATCH found={digest}")
    xyz,conn,ids,types,faces=parse_msh(args.mesh)
    X=xyz[conn]  # [elements, 10, physical coordinate]
    if not np.isfinite(X).all():
        raise SystemExit("P10PX_STOP_NONFINITE_M8_COORDINATES")
    # Exact conversion to quadratic Bezier simplex controls. This gives
    # *rigorous* physical AABBs enclosing the entire curved reference Tet10.
    bezier=X.copy()
    for idx,(a,b) in enumerate(EDGE,start=4):
        bezier[:,idx,:]=2*X[:,idx,:]-.5*(X[:,a,:]+X[:,b,:])
    lo=bezier.min(axis=1)-CENTER
    hi=bezier.max(axis=1)-CENTER

    # Full Tet10 Jacobian audit at 27 Duffy/Gauss locations.
    gl=np.array([.1127016653792583,.5,.8872983346207417])
    gw=np.array([5/18,8/18,5/18])
    pts=[]; ws=[]; shape=[]; grad=[]
    for ia,a in enumerate(gl):
        for ib,b in enumerate(gl):
            for ic,c in enumerate(gl):
                u,v,w=a,(1-a)*b,(1-a)*(1-b)*c
                n,g=tet10_shape((u,v,w))
                pts.append((u,v,w));shape.append(n);grad.append(g)
                ws.append(gw[ia]*gw[ib]*gw[ic]*(1-a)**2*(1-b))
    N=np.array(shape);G=np.array(grad);W=np.array(ws)
    det_min=math.inf;det_max=-math.inf;nonpos=0
    volumes=np.zeros(len(conn));sample_pos=np.empty((len(conn),len(pts),3))
    for start in range(0,len(conn),512):
        stop=min(start+512,len(conn));x=X[start:stop]
        J=np.einsum("eki,qkj->eqij",x,G)
        det=np.linalg.det(J)
        det_min=min(det_min,float(det.min()));det_max=max(det_max,float(det.max()))
        nonpos+=int((det<=0).sum())
        volumes[start:stop]=det@W
        sample_pos[start:stop]=np.einsum("qk,eki->eqi",N,x)
    if nonpos or (volumes<=0).any():
        raise SystemExit("P10PX_STOP_NONPOSITIVE_TET10_JACOBIAN")

    bin_details=[];samples=[]
    rad_bins=[0,1,3,4,5,6]  # Near-wall and middle radial shells from signed-4D SOP
    for ir in rad_bins:
        for im in [0,9]:
            for ip in [5,6]:
                possible,inside,status=candidate_masks(lo,hi,ir,im,ip)
                candidates=np.flatnonzero(possible)
                uncertain=np.flatnonzero(possible&~inside)
                quartic_uncertain=(status[:,[0,1,3]]==0).sum(axis=1)
                bin_details.append({"radial_bin":ir,"mu_bin":im,"phi_bin":ip,
                                    "excluded_proven":int((~possible).sum()),
                                    "fully_inside_proven":int(inside.sum()),
                                    "cut_or_ambiguous_conservative":len(uncertain),
                                    "possible":len(candidates),
                                    "possible_at_most_one_quartic_cut":int((possible&(quartic_uncertain<=1)).sum()),
                                    "possible_two_or_three_quartic_cuts":int((possible&(quartic_uncertain>=2)).sum()),
                                    "uncertain_multi_constraints":int(((status==0).sum(axis=1)[uncertain]>=2).sum())})
                # Do not select enormous broad-phase false positives for Algoim.
                # Rank deterministically by sample QPs falling near the target
                # physical sector, then by smallest element ID.
                if ir!=4 or im not in [0,9] or ip!=6:
                    continue
                r=np.linalg.norm(sample_pos[candidates]-CENTER,axis=2)
                mu=(sample_pos[candidates,:,2]-CENTER[2])/np.maximum(r,1e-30)
                az=np.arctan2(sample_pos[candidates,:,1],sample_pos[candidates,:,0])
                bound_lo=PORE_R+RADIAL_LOWER_MM[ir]/1000
                bound_hi=PORE_R+RADIAL_LOWER_MM[ir+1]/1000
                zsign=1 if im==9 else -1
                hit=(r>=bound_lo)&(r<=bound_hi)&(zsign*mu>=.8)&(az>=0)&(az<=math.pi/6)
                count=hit.sum(axis=1)
                tests=[r-bound_lo, r-bound_hi, zsign*mu-.8,
                       az, math.pi/6-az]
                crossings=sum((v.min(axis=1)<0)&(v.max(axis=1)>0) for v in tests)
                # Actual physical bin crossing at the 27 geometric audit
                # samples, ideally where two or more interfaces interact.
                order=sorted(range(len(candidates)),key=lambda k:(
                    not (0<int(count[k])<27),
                    -int(crossings[k]),
                    abs(float(count[k])-13.5),
                    int(ids[candidates[k]])))
                for k in order[:3]:
                    e=int(candidates[k]);nd=X[e]
                    samples.append({"element_id":int(ids[e]),"region":"north" if im==9 else "south",
                                    "radial_bin":ir,"mu_bin":im,"phi_bin":ip,
                                    "interior_gauss_hits":int(count[k]),
                                    "sampled_crossing_constraints":int(crossings[k]),
                                    "conservative_constraint_status":status[e].tolist(),
                                    "relative_element_volume":float(volumes[e]),
                                    "physical_nodes_10":nd.tolist()})

    # The sample format allows a small pure-C++ program to run on the exact
    # accepted M8 Tet10 coordinates without a general-purpose JSON dependency.
    lines=["P10PX_M8_TET10_SAMPLE_V1",str(len(samples))]
    for record in samples:
        lines.append(str(record["element_id"])+" "+record["region"]+" "+
                     " ".join(str(x) for x in record["conservative_constraint_status"]))
        lines += [" ".join(f"{x:.17g}" for x in row) for row in record["physical_nodes_10"]]
    args.samples.write_text("\n".join(lines)+"\n",encoding="utf-8")
    report={"stage":"P10PX","status":"PASS_READ_ONLY_M8_GEOMETRY_TRIAGE",
            "mesh_sha256":digest,"mesh":args.mesh.name,"mesh_generated":False,"fem_started":False,
            "gmsh_optimization_started":False,"high_order_elastic_preserved":True,
            "node_count":len(xyz),"element_counts_by_gmsh_type":types,
            "physical_tri6_face_counts":faces,"tet10_count":len(conn),
            "tet10_jacobian_quadrature_samples":len(conn)*len(pts),
            "minimum_det_j":det_min,"maximum_det_j":det_max,
            "nonpositive_detj_count":nonpos,"volume_sum_m3":float(volumes.sum()),
            "bezier_convex_hull_bounds":True,"conservative_prefilter_certification":
              "No element removed unless an interval inequality holds on all Bezier controls",
            "binning_source":"P10DD: radial[0,.02,.05,.1,.25,.5,1,2,5,15] mm; mu10; phi12",
            "bin_triage":bin_details,"sample_count":len(samples),"samples":samples}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P10PX_M8_TRIAGE_PASS nodes="+str(len(xyz))+" tet10="+str(len(conn))+
          " det_min="+format(det_min,".8g")+" volume="+format(float(volumes.sum()),".10g")+
          " samples="+str(len(samples)))
    for b in bin_details:
        if b["radial_bin"] in [0,4] and b["phi_bin"]==6:
            print("P10PX_BIN r="+str(b["radial_bin"])+" mu="+str(b["mu_bin"])+
                  " possible="+str(b["possible"])+" proven_inside="+
                  str(b["fully_inside_proven"]))


if __name__=="__main__":
    main()
