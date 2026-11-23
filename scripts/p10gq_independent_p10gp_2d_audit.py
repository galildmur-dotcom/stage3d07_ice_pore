#!/usr/bin/env python3
"""Independent read-only checks of primary P10GP Windows surface evidence."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

EXPECTED_SHA = "875497809d59b08920aeb951cb690a7272b31722b1daedd2a824dd61c8f36cf2"
CASES = ("A_ORIGINAL_F3", "B_SELF_CONTAINED_C1_SOUTH")


def sha(x): return hashlib.sha256(x).hexdigest()


def quantile(a, p):
    a = sorted(a)
    x = (len(a)-1)*p
    i = int(x)
    return a[i] + (a[min(i+1,len(a)-1)]-a[i])*(x-i)


def parse_msh(raw):
    rows = iter(raw.decode("ascii").splitlines())
    nodes, triangles, types = {}, [], {}
    for row in rows:
        if row == "$Nodes":
            for _ in range(int(next(rows))):
                b = next(rows).split()
                nodes[int(b[0])] = tuple(map(float,b[1:]))
        if row == "$Elements":
            for _ in range(int(next(rows))):
                b = list(map(int,next(rows).split()))
                _,typ,n = b[:3]
                types[typ] = types.get(typ,0)+1
                assert typ == 9 and n >= 1
                triangles.append((b[3],b[3+n:]))
    assert len(nodes)>0 and len(triangles)>0 and set(types)=={9}
    return nodes,triangles,types


def evaluate(nodes,triangles):
    zones={"north":[],"south":[],"equator":[],"all_pore":[]}
    factors={"north":[],"south":[],"equator":[],"all_pore":[]}
    edge_to_cells={}
    tags={}
    for physical, ids in triangles:
        tags[physical]=tags.get(physical,0)+1
        assert len(ids)==6 and all(i in nodes for i in ids)
        if physical != 8: continue
        x=[nodes[i] for i in ids[:3]]
        c=tuple(sum(p[k] for p in x)/3 for k in range(3))
        d=math.dist(c,(0,0,.03))
        mu=(c[2]-.03)/d
        lengths=[math.dist(x[a],x[b]) for a,b in ((0,1),(1,2),(2,0))]
        character=statistics.median(lengths)
        group="north" if mu>=.8 else "south" if mu<=-.8 else "equator" if abs(mu)<=.2 else "intermediate"
        zones["all_pore"].extend(lengths)
        factors["all_pore"].append(character)
        if group in zones:
            zones[group].extend(lengths)
            factors[group].append(character)
        for a,b in ((0,1),(1,2),(2,0)):
            edge_to_cells.setdefault(tuple(sorted((ids[a],ids[b]))),[]).append((character,group))
    assert set(tags)==set(range(2,10))
    assert all(zones.values())
    jumps={"north":[],"south":[],"all_pore":[]}
    for cells in edge_to_cells.values():
        assert len(cells)==2, "pore Tri6 manifold edge incidence"
        v=max(cells[0][0],cells[1][0])/min(cells[0][0],cells[1][0])
        jumps["all_pore"].append(v)
        for pole in ("north","south"):
            if any(c[1]==pole for c in cells): jumps[pole].append(v)
    return {"tags":tags,"sizes":{name:{"n_edges":len(v),"median_mm":1000*statistics.median(v),"p05_mm":1000*quantile(v,.05),"p95_mm":1000*quantile(v,.95)} for name,v in zones.items()},
            "adjacent_characteristic_ratio":{name:{"n_pairs":len(v),"median":statistics.median(v),"p95":quantile(v,.95),"max":max(v)} for name,v in jumps.items()}}


def main(path):
    data=Path(path).read_bytes()
    assert sha(data)==EXPECTED_SHA, "original ZIP SHA mismatch"
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None and len(z.namelist())==13
        m=json.loads(z.read("P10GP_MANIFEST.json"))
        assert m["status"]=="BOTH_2D_DONE_PENDING_INDEPENDENT_AUDIT"
        assert (m["native_2d_attempts"],m["native_3d_attempts"],m["FEM_attempts"])==(2,0,0)
        out={"zip_sha256":EXPECTED_SHA,"cases":{}}
        for case in CASES:
            record=m["cases"][case]
            mesh=z.read(case+"/P10GP_SURFACE.msh")
            log=z.read(case+"/P10GP_GMSH_2D.log")
            geo=z.read(case+"/P10GP_SURFACE.geo")
            cmd=record["native"]["command"]
            assert cmd.count("-2")==1 and "-3" not in cmd and "-save_all" not in cmd
            assert record["native"]["exit_code"]==0 and not record["native"]["stop_reason"]
            assert sha(mesh)==record["native"]["msh_sha256"]
            assert sha(log)==record["native"]["log_sha256"]
            assert b"Done meshing 2D" in log and b"Error   :" not in log
            assert b'Include "M0_ROTATED.geo"' in geo
            assert (b"Background Field = 7" in geo)==(case==CASES[1])
            nodes,tris,types=parse_msh(mesh)
            result=evaluate(nodes,tris)
            assert result["tags"]=={int(k):v for k,v in record["surface"]["physical_tri6_counts"].items()}
            for zone,value in result["sizes"].items():
                assert abs(value["median_mm"]/1000-record["pore_edge_size"][zone]["median_edge_m"])<1e-15
            result.update({"nodes":len(nodes),"tri6":len(tris),"types":types})
            out["cases"][case]=result
        a,b=(out["cases"][c] for c in CASES)
        out["south_median_edge_ratio_B_A"]=b["sizes"]["south"]["median_mm"]/a["sizes"]["south"]["median_mm"]
        out["north_median_edge_ratio_B_A"]=b["sizes"]["north"]["median_mm"]/a["sizes"]["north"]["median_mm"]
        out["equator_median_edge_ratio_B_A"]=b["sizes"]["equator"]["median_mm"]/a["sizes"]["equator"]["median_mm"]
        print(json.dumps(out,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main(sys.argv[1])
