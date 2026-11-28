#!/usr/bin/env python3
"""P10GS: independent read-only audit of original 20-case P10GR MSH2 evidence."""
from __future__ import annotations
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from p10gq_independent_p10gp_2d_audit import parse_msh,evaluate

ZIP_PIN="856136bba9e9a684ce39a8234a00c2031d54ac6dfa1e1477a67ea07fabdeb25e"
ALPHAS=(.03,.06,.09)
ENDS=(-.7,-.5,-.2)


def sha(x):return hashlib.sha256(x).hexdigest()


def main(path):
    raw=Path(path).read_bytes()
    assert sha(raw)==ZIP_PIN,"P10GR primary ZIP SHA mismatch"
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None and len(z.namelist())==103
        m=json.loads(z.read("P10GR_MANIFEST.json"))
        assert m["revision"]=="P10GR_R1_PRESPECIFIED_20_SURFACE_CASES_NO_3D_FEM"
        assert m["status"]=="ALL_20_2D_COMPLETED_PENDING_INDEPENDENT_AUDIT"
        assert (m["native_2d_attempts"],m["native_3d_attempts"],m["FEM_attempts"])==(20,0,0)
        rows=list(csv.DictReader(io.StringIO(z.read("P10GR_COMPARISON.csv").decode("utf-8"))))
        assert len(rows)==20
        expected={f"ALGO{alg}_A00_BASE" for alg in (5,6)}
        expected.update(f"ALGO{alg}_A{round(a*100):02d}_MU{round(abs(e)*100):02d}"
                        for alg in (5,6) for a in ALPHAS for e in ENDS)
        assert set(m["cases"])==expected=={r["case"] for r in rows}
        summary={}
        for name in sorted(expected):
            case=m["cases"][name]
            native=case["native"]
            assert case["status"]=="PASS"
            assert native["exit_code"]==0 and native["stop_reason"]==""
            assert native["command"].count("-2")==1 and "-3" not in native["command"]
            msh=z.read(name+"/P10GR.msh")
            geo=z.read(name+"/P10GR.geo")
            log=z.read(name+"/P10GR.log")
            assert sha(msh)==native["msh_sha256"] and sha(log)==native["log_sha256"]
            assert b"Done meshing 2D" in log and b"Error   :" not in log
            assert b'Include "M0_ROTATED.geo";' in geo
            assert f'Mesh.Algorithm = {case["surface"].get("algorithm",name[4])};'.encode() in geo
            nodes,tris,types=parse_msh(msh)
            mine=evaluate(nodes,tris)
            assert mine["tags"]=={int(k):v for k,v in case["surface"]["physical_tri6_counts"].items()}
            assert len(nodes)==case["surface"]["nodes"] and len(tris)==case["surface"]["total_tri6"]
            assert abs(mine["adjacent_characteristic_ratio"]["all_pore"]["max"]-
                       case["neighbour_grading"]["all"]["max"])<1e-12
            assert abs(mine["adjacent_characteristic_ratio"]["south"]["max"]-
                       case["neighbour_grading"]["south"]["max"])<1e-12
            for region in ("north","south","equator","all_pore"):
                assert abs(mine["sizes"][region]["median_mm"]*1e-3-
                           case["pore_edge_size"][region]["median_edge_m"])<1e-14
            summary[name]={"algorithm":int(name[4]),"nodes":len(nodes),"tri6":len(tris),
                           "south_median_mm":mine["sizes"]["south"]["median_mm"],
                           "north_median_mm":mine["sizes"]["north"]["median_mm"],
                           "equator_median_mm":mine["sizes"]["equator"]["median_mm"],
                           "q_corner_min":case["surface"]["q_corner_min"],
                           "neighbour_max":mine["adjacent_characteristic_ratio"]["all_pore"]["max"],
                           "south_neighbour_max":mine["adjacent_characteristic_ratio"]["south"]["max"]}
        for name,val in summary.items():
            control=summary[f'ALGO{val["algorithm"]}_A00_BASE']
            val["south_ratio"] = val["south_median_mm"]/control["south_median_mm"]
            val["north_ratio"] = val["north_median_mm"]/control["north_median_mm"]
            val["equator_ratio"] = val["equator_median_mm"]/control["equator_median_mm"]
            row=next(x for x in rows if x["case"]==name)
            assert abs(val["south_ratio"]-float(row["south_edge_B_over_baseline"]))<1e-12
            assert abs(val["north_ratio"]-float(row["north_edge_B_over_baseline"]))<1e-12
        eligible=[(name,v) for name,v in summary.items() if not name.endswith("_BASE") and
                  v["south_ratio"]<=.98 and abs(v["north_ratio"]-1)<=.03 and
                  abs(v["equator_ratio"]-1)<=.03 and v["q_corner_min"]>=.45 and v["neighbour_max"]<=2.2]
        eligible.sort(key=lambda x:(x[1]["south_ratio"],-x[1]["q_corner_min"],x[1]["neighbour_max"]))
        print(json.dumps({"original_zip_sha256":ZIP_PIN,"status":"P10GS_INDEPENDENT_20_MSH_PASS",
                          "count":len(summary),"eligible_count":len(eligible),"eligible":eligible,
                          "all_summary":summary},ensure_ascii=False,indent=2))


if __name__=="__main__":main(sys.argv[1])
