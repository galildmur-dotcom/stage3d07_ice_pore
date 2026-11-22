"""Read-only native Gmsh 2.2 ASCII geometry QA for any Stage3D07 Tet10 mesh.

The 27 curved QPs duplicate the independently audited P10CK implementation.
Positive 27 samples do NOT guarantee continuous Jacobian positivity.
"""
import hashlib
import math
from pathlib import Path

from P10CK_curved_qp_audit import QUAD, eval_tet, corner_det


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def audit(path, *, expensive=True):
    """No mutation. Fails closed on malformed elements or nonpositive sampled detJ."""
    mesh = Path(path)
    nodes = {}
    n_tet = n_pore = n_top = 0
    n_bad = 0
    min_det = math.inf
    min_corner = math.inf
    integral_volume = 0.
    max_qp_ratio = 0.
    tags = set()
    volumes = []
    centroids = []
    faces = {}
    adjacency = []
    with mesh.open("r", encoding="utf-8") as stream:
        if stream.readline().strip() != "$MeshFormat":
            raise ValueError("not Gmsh MSH2")
        parts = stream.readline().split()
        if len(parts) < 3 or not parts[0].startswith("2.") or parts[1] != "0":
            raise ValueError("only ASCII MSH2 is supported")
        if stream.readline().strip() != "$EndMeshFormat":
            raise ValueError("MSH2 header not terminated")
        while True:
            section = stream.readline()
            if not section:
                break
            if section.strip() == "$Nodes":
                if nodes:
                    raise ValueError("duplicate $Nodes")
                count = int(stream.readline())
                for _ in range(count):
                    parts = stream.readline().split()
                    if len(parts) != 4:
                        raise ValueError("invalid node row")
                    idx = int(parts[0])
                    xyz = tuple(float(z) for z in parts[1:])
                    if idx in nodes or not all(map(math.isfinite, xyz)):
                        raise ValueError("duplicate/nonfinite node")
                    nodes[idx] = xyz
                if stream.readline().strip() != "$EndNodes":
                    raise ValueError("invalid $Nodes end")
            elif section.strip() == "$Elements":
                if not nodes:
                    raise ValueError("missing node block")
                count = int(stream.readline())
                for _ in range(count):
                    parts = [int(z) for z in stream.readline().split()]
                    if len(parts) < 4 or len(parts) < 3 + parts[2]:
                        raise ValueError("invalid element row")
                    kind, ntags = parts[1], parts[2]
                    tag = parts[3] if ntags else 0
                    ids = parts[3 + ntags:]
                    if kind == 9:
                        if len(ids) != 6:
                            raise ValueError("non-Tri6 second-order face")
                        tags.add(tag)
                        n_pore += tag == 8
                        n_top += tag == 2
                    elif kind == 11:
                        if len(ids) != 10 or tag != 1:
                            raise ValueError("Tet10 missing canonical physical volume tag 1")
                        n_tet += 1
                        if not expensive:
                            continue
                        if n_tet > 1000000:
                            raise ValueError("more than 1,000,000 Tet10: Python diagnostic resource cap")
                        points = [nodes[k] for k in ids]
                        corner = corner_det(points)
                        min_corner = min(min_corner, corner)
                        if corner <= 0:
                            n_bad += 1
                        local_min, local_max = math.inf, -math.inf
                        v = 0.
                        center_sum = [0.,0.,0.]
                        for N, D, w in QUAD:
                            x, det = eval_tet(points, N, D)
                            local_min = min(local_min, det)
                            local_max = max(local_max, det)
                            integral_volume += w * det
                            v += w*det
                            for dim in range(3):
                                center_sum[dim] += w*det*x[dim]
                            if det <= 0 or not math.isfinite(det):
                                n_bad += 1
                        min_det = min(min_det, local_min)
                        if local_min > 0:
                            max_qp_ratio = max(max_qp_ratio, local_max / local_min)
                        volumes.append(v)
                        centroids.append(tuple(z/v for z in center_sum) if v > 0 else (0.,0.,0.))
                        for face in ((0,1,2),(0,1,3),(0,2,3),(1,2,3)):
                            k = tuple(sorted(ids[i] for i in face))
                            if k in faces:
                                prev = faces.pop(k)
                                adjacency.append((prev,n_tet-1))
                            else:
                                faces[k] = n_tet-1
                    elif kind in (4, 2):
                        raise ValueError("linear Tet4/Tri3 forbidden; only Tet10/Tri6")
                if stream.readline().strip() != "$EndElements":
                    raise ValueError("invalid $Elements end")
    if not n_tet or n_pore < 10 or n_top < 10 or not {2,3,4,5,6,7,8,9} <= tags:
        raise ValueError(f"missing canonical physical tags or elements: tet={n_tet}, pore={n_pore}, tags={sorted(tags)}")
    if expensive and (n_bad or min_det <= 0):
        raise ValueError(f"nonpositive curved Jacobian/corner: count={n_bad}, min={min_det}")
    ratios = []
    near_ratios = []
    if expensive:
        position = []
        for x,y,z in centroids:
            dx,dy,dz = x,y,z-.03
            radius = math.sqrt(dx*dx+dy*dy+dz*dz)
            position.append((radius-.001, dz/radius if radius > 0 else 0.))
        for i,j in adjacency:
            q = (max(volumes[i],volumes[j])/min(volumes[i],volumes[j]))**(1/3)
            ratios.append(q)
            if max(position[i][0],position[j][0]) < .0005 and min(abs(position[i][1]),abs(position[j][1])) >= .6:
                near_ratios.append(q)
    def stats(values):
        if not values:
            return {"count":0}
        v = sorted(values)
        def quantile(q):
            a = q*(len(v)-1)
            lo = int(a)
            return v[lo] + (v[min(lo+1,len(v)-1)]-v[lo])*(a-lo)
        return {"count":len(v),"median":quantile(.5),"p95":quantile(.95),
                "p99":quantile(.99),"maximum":v[-1],
                "q_gt_1p25":sum(q>1.25 for q in v)}
    return {"mesh_sha256": sha256(mesh), "nodes": len(nodes), "tet10": n_tet,
            "pore_tri6": n_pore, "top_tri6": n_top,
            "physical_surface_tags": sorted(tags), "curved_qp": n_tet * 27 if expensive else None,
            "nonpositive_samples": n_bad if expensive else None,
            "minimum_curved_detj": min_det if expensive else None,
            "minimum_corner_detj": min_corner if expensive else None,
            "max_element_qp_detj_ratio": max_qp_ratio if expensive else None,
            "qp_integrated_volume_m3": integral_volume if expensive else None,
            "adjacent_face_size_jump_all": stats(ratios) if expensive else None,
            "adjacent_face_size_jump_near_polar": stats(near_ratios) if expensive else None,
            "geometry_gate": "PASS_27QP_DIAGNOSTIC" if expensive else "NOT_EVALUATED"}
