#!/usr/bin/env python3
"""P10NS: in-memory Gmsh Tet10 topology and curved Jacobian audit, no mesh output/FEM."""
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from p10nq_native_geometry_correspondence_windows import MESH, SHA, sample
from p10nr_coordinate_topology import boundary_index, match_by_position, classify

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "P10NS_VOLUME_TOPOLOGY_QUALITY_RESULT.json"
EDGES = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
DL = np.array([[-1., -1., -1.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
PORE_CENTER = np.array([0., 0., .03])


def quadrature_points(order):
    """Tensor Gauss points transformed to interior of reference tetrahedron."""
    x, _ = np.polynomial.legendre.leggauss(order)
    x = (x + 1) / 2
    a, b, c = np.meshgrid(x, x, x, indexing="ij")
    r = a.ravel()
    s = ((1-a)*b).ravel()
    t = ((1-a)*(1-b)*c).ravel()
    return np.column_stack((r, s, t))


def tet10_gradients(points):
    l = np.column_stack((1-points.sum(axis=1), points))
    g = np.empty((len(points), 10, 3), dtype=float)
    for i in range(4):
        g[:, i, :] = (4*l[:, i, None]-1)*DL[i]
    for k, (i, j) in enumerate(EDGES):
        g[:, 4+k, :] = 4*(l[:, i, None]*DL[j] + l[:, j, None]*DL[i])
    return g


def det_statistics(snap, order, batch=64):
    ids = sorted(snap["tets"])
    points = quadrature_points(order)
    grads = tet10_gradients(points)
    min_det = np.inf
    max_det = -np.inf
    bad_elements = 0
    nonpositive_qps = 0
    evaluated = 0
    t0 = time.monotonic()
    for start in range(0, len(ids), batch):
        part = ids[start:start+batch]
        xyz = np.array([[snap["nodes"][n] for n in snap["tets"][eid]] for eid in part])
        jac = np.einsum("enc,qnj->ecqj", xyz, grads, optimize=True)
        # jac dimensions: element, xyz-component, QP, reference-component
        jac = jac.transpose(0, 2, 1, 3)
        det = np.linalg.det(jac)
        min_det = min(min_det, float(det.min()))
        max_det = max(max_det, float(det.max()))
        bad_elements += int(np.count_nonzero(np.any(det <= 0, axis=1)))
        nonpositive_qps += int(np.count_nonzero(det <= 0))
        evaluated += det.size
        if time.monotonic()-t0 > 30 and start % (batch*30) == 0:
            print(f"P10NS_QUALITY order={order} elements={start+len(part)}/{len(ids)}", flush=True)
    return {"order_per_axis": order, "qps_per_element": len(points),
            "elements": len(ids), "evaluated_qps": evaluated,
            "min_detJ": min_det, "max_detJ": max_det,
            "nonpositive_qps": nonpositive_qps,
            "elements_with_nonpositive_detJ": bad_elements,
            "wall_s": time.monotonic()-t0}


def interior_topology(before, after):
    corners_b = {n for c in before["tets"].values() for n in c[:4]}
    corners_a = {n for c in after["tets"].values() for n in c[:4]}
    mapping = match_by_position(before, after, corners_b, corners_a)
    def index(snap, remap=None):
        out = {}
        duplicates = 0
        for e, conn in snap["tets"].items():
            verts = tuple(remap[n] for n in conn[:4]) if remap else conn[:4]
            key = tuple(sorted(verts))
            if key in out:
                duplicates += 1
            out[key] = (e, conn)
        if duplicates:
            raise ValueError(f"duplicate Tet10 vertex sets: {duplicates}")
        return out
    left, right = index(before, mapping), index(after)
    shared = left.keys() & right.keys()
    report = {"corner_nodes":len(mapping),
              "corner_tags_changed_after_coordinate_map":sum(a != b for a,b in mapping.items()),
              "tets_before":len(left), "tets_after":len(right),
              "matched_tet_vertex_sets":len(shared),
              "missing_tet_vertex_sets":len(left.keys()-right.keys()),
              "extra_tet_vertex_sets":len(right.keys()-left.keys()),
              "topology_preserved":len(shared)==len(left)==len(right)}
    changes=[]
    boundary_b=boundary_index(before)
    boundary_a=boundary_index(after)
    unchanged=0
    matched_edges=0
    boundary_moves=0
    for key in shared:
        _, old = left[key]
        _, new = right[key]
        old_edge = {tuple(sorted((mapping[old[i]], mapping[old[j]]))):old[4+k]
                    for k,(i,j) in enumerate(EDGES)}
        new_edge = {tuple(sorted((new[i],new[j]))):new[4+k]
                    for k,(i,j) in enumerate(EDGES)}
        if old_edge.keys()!=new_edge.keys():
            raise ValueError("edge mismatch on matched vertex tetrahedron")
        for edge in old_edge:
            o, n = old_edge[edge], new_edge[edge]
            dist = float(np.linalg.norm(before["nodes"][o]-after["nodes"][n]))
            changes.append(dist)
            matched_edges+=1
            unchanged+=dist<1e-12
            if o in boundary_b or n in boundary_a:
                boundary_moves+=dist>=1e-12
    report.update({"matched_mid_edge_occurrences":matched_edges,
                   "unchanged_mid_edge_occurrences_tol_1e_12_m":unchanged,
                   "boundary_mid_edge_occurrences_moved":boundary_moves,
                   "mid_edge_displacement_max_mm":max(changes,default=0)*1000,
                   "mid_edge_displacement_p95_mm":float(np.percentile(changes,95))*1000 if changes else None,
                   "mid_edge_displacement_median_mm":float(np.median(changes))*1000 if changes else None})
    return report


def selftest():
    p=quadrature_points(3)
    g=tet10_gradients(p)
    assert p.shape==(27,3) and g.shape==(27,10,3)
    assert np.allclose(g.sum(axis=1),0,atol=1e-13)
    corners=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],float)
    xyz=np.vstack((corners,[(corners[i]+corners[j])/2 for i,j in EDGES]))
    j=np.einsum('kc,qkj->qcj',xyz,g)
    assert np.allclose(np.linalg.det(j),1,atol=1e-12)
    first={"nodes":{i+1:xyz[i].copy() for i in range(10)},
           "tets":{11:tuple(range(1,11))},
           "by_phys":{8:{"node_ids":set(range(1,11))}}}
    second={"nodes":{i+101:xyz[i].copy() for i in range(10)},
            "tets":{12:tuple(range(101,111))},
            "by_phys":{8:{"node_ids":set(range(101,111))}}}
    assert interior_topology(first,second)["topology_preserved"]
    assert det_statistics(first,3)["min_detJ"]>0.999999999999
    xyz[4]+=[0,0,3]
    assert np.min(np.linalg.det(np.einsum('kc,qkj->qcj',xyz,g)))<0
    print('P10NS_SYNTHETIC_TET10_JACOBIAN_PASS',flush=True)


def main():
    selftest()
    if "--selftest" in sys.argv:
        return
    import gmsh
    if OUTPUT.exists():raise RuntimeError("P10NS_STOP: output exists; preserve it")
    if gmsh.__version__!="4.15.2":raise RuntimeError("Gmsh 4.15.2 required")
    if hashlib.sha256(MESH.read_bytes()).hexdigest()!=SHA:raise RuntimeError("source M13 R2 SHA mismatch")
    report={"protocol":"P10NS_VOLUME_TET10_TOPOLOGY_AND_CURVED_JACOBIANS",
            "source_sha256":SHA, "status":"STARTED", "FEM_attempts":0,
            "mesh_generation_attempts":0,"mesh_files_written":0,"marker_uses":0}
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal",1)
        gmsh.option.setNumber("Mesh.HighOrderFixBoundaryNodes",1)
        gmsh.option.setNumber("Mesh.HighOrderIterMax",50)
        gmsh.option.setNumber("Mesh.HighOrderPassMax",5)
        gmsh.option.setNumber("Mesh.HighOrderNumLayers",2)
        gmsh.open(str(MESH))
        before=sample(gmsh)
        report["before_quality"]={str(k):det_statistics(before,k) for k in (3,7,9)}
        t0=time.monotonic()
        print("P10NS_OPTIMIZER_START",flush=True)
        gmsh.model.mesh.optimize("HighOrderElastic",force=True)
        report["optimizer_s"]=time.monotonic()-t0
        after=sample(gmsh)
        report["boundary_tri6_preserved_recheck"]=classify(before,after)["all_boundary_tri6_preserved"]
        report["volume_topology"]=interior_topology(before,after)
        report["after_quality"]={str(k):det_statistics(after,k) for k in (3,7,9)}
        report["no_nonpositive_detJ_all_grids"]=all(
            v["nonpositive_qps"]==0 for v in report["after_quality"].values())
        report["status"]="AUDIT_COMPLETED_NO_R3_NO_FEM"
        report["acceptance"]="DIAGNOSTIC_ONLY_M13_NOT_ACCEPTED"
    except Exception as e:
        report["status"]="AUDIT_ERROR"
        report["error"]=repr(e)
        report["traceback"]=traceback.format_exc()[-4500:]
    finally:
        gmsh.finalize()
    with OUTPUT.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    print('P10NS_DONE',report['status'],flush=True)
    if report['status']!='AUDIT_COMPLETED_NO_R3_NO_FEM':raise RuntimeError("P10NS_AUDIT_ERROR: see JSON")


if __name__=='__main__':
    try:main()
    except Exception as e:
        print('P10NS_STOP',repr(e),flush=True)
        sys.exit(2)
