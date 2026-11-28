#!/usr/bin/env python3
"""P10PX independent source-only M8 audit + true LAPACKE/Algoim spot checks.

Requires the pinned accepted M8.msh, Algoim with the P10PV C++20 patch,
and ABI-compatible LAPACKE/LAPACK/BLAS. NEVER runs FEM or changes the mesh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

LINE = re.compile(
    r"^P10PX_M8_ALGOIM element=(\d+) pole=(north|south) mode=(\d+) q=(\d+) "
    r"tet_rel=([\d.eE+-]+) cut_volume=([\d.eE+-]+) "
    r"cut_frac=([\d.eE+-]+) points=(\d+) active=(\d+)$"
)


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--mesh",type=Path,required=True)
    a.add_argument("--algoim-root",type=Path,required=True)
    a.add_argument("--lapacke-include",type=Path,required=True)
    a.add_argument("--lapacke-lib",type=Path,required=True)
    a.add_argument("--lapack-lib",required=True)
    a.add_argument("--blas-lib",required=True)
    a.add_argument("--cxx",default="g++")
    a.add_argument("--output",type=Path,default=Path("P10PX_M8_REAL_ALGOIM_QA.json"))
    a.add_argument("--geometry-json",type=Path,default=Path("P10PX_M8_READ_ONLY_TRIAGE_QA.json"))
    a.add_argument("--samples",type=Path,default=Path("P10PX_M8_TET10_SAMPLE_NODES.txt"))
    a.add_argument("--binary",type=Path,default=Path("./p10px_m8_algoim_test"))
    args=a.parse_args()
    root=Path(__file__).resolve().parent
    script=root/"P10PX_M8_CONSERVATIVE_TET10_TRIAGE.py"
    source=root/"P10PX_ALGOIM_REAL_M8_TET10_SOURCE_ONLY.cpp"
    mesh=args.mesh.resolve();samples=args.samples.resolve()
    geo_json=args.geometry_json.resolve();binary=args.binary.resolve()
    exe=[sys.executable,str(script),"--mesh",str(mesh),
         "--output",str(geo_json),"--samples",str(samples)]
    triage=subprocess.run(exe,capture_output=True,text=True,timeout=90)
    if triage.returncode:
        raise RuntimeError("M8 geometry preflight failed: "+triage.stderr+triage.stdout)
    geometry=json.loads(geo_json.read_text(encoding="utf-8"))
    if geometry["status"]!="PASS_READ_ONLY_M8_GEOMETRY_TRIAGE":
        raise RuntimeError("M8 geometry not accepted")
    cmd=[args.cxx,"-std=c++20","-O2","-Wl,--gc-sections",
         "-I"+str(args.algoim_root.resolve()/"algoim"),
         "-I"+str(args.lapacke_include.resolve()),
         str(source),str(args.lapacke_lib.resolve()),args.lapack_lib,args.blas_lib,
         "-lm","-o",str(binary)]
    build=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
    if build.returncode:
        raise RuntimeError("M8 Algoim compilation failed: "+build.stderr[-4000:])
    # This test MUST refuse a true multi-quartic cut before Algoim's
    # potentially unbounded resultant construction starts.
    guard=subprocess.run([str(binary),str(samples),"0","7","2"],
                         capture_output=True,text=True,timeout=10)
    if guard.returncode!=3 or "P10PX_M8_UNSUPPORTED_MULTIPLE_QUARTIC_CUTS" not in guard.stdout:
        raise RuntimeError("multi-quartic preflight guard failed")
    cases=[]
    for index,expected_id,expected_pole in [(1,6813,"south"),(3,10725,"north"),(5,10114,"north")]:
        run=subprocess.run([str(binary),str(samples),str(index),"7","8"],
                           capture_output=True,text=True,timeout=80)
        if run.returncode or "P10PX_M8_ALGOIM_SOURCE_ONLY_PASS" not in run.stdout:
            raise RuntimeError(f"actual M8 Tet10 element {expected_id} failed:\n"+
                               (run.stdout+run.stderr)[-4000:])
        if "retained=4 skipped=3" not in run.stdout:
            raise RuntimeError("certified boundary elimination did not happen")
        rows=[]
        for line in run.stdout.splitlines():
            match=LINE.fullmatch(line)
            if match:
                eid,pole,mode,q,terr,vol,frac,points,active=match.groups()
                row={"element_id":int(eid),"pole":pole,"mode":int(mode),"q":int(q),
                     "tet_rel":float(terr),"cut_volume_m3":float(vol),
                     "cut_fraction":float(frac),"nodes":int(points),
                     "active_nodes":int(active)}
                if (row["element_id"]!=expected_id or row["pole"]!=expected_pole or
                    not 0<=row["cut_fraction"]<=1.05 or
                    not 0<row["active_nodes"]<=row["nodes"]):
                    raise RuntimeError("invalid real M8 cut-cell partition")
                rows.append(row)
        if [r["q"] for r in rows]!=[2,3,4,6,8]:
            raise RuntimeError("incomplete M8 q-refinement sequence")
        last,prev=rows[-1],rows[-2]
        if last["tet_rel"]>=1e-5:
            raise RuntimeError(f"q8 volume closure failed for element {expected_id}")
        delta=abs(last["cut_volume_m3"]-prev["cut_volume_m3"])/last["cut_volume_m3"]
        if delta>2e-4:
            raise RuntimeError(f"q6/q8 cut volume not stable for element {expected_id}")
        cases.append({"sample_index":index,"element_id":expected_id,"pole":expected_pole,
                      "requested_physical_constraints":6,
                      "retained_active_constraints_including_tetra":4,
                      "q6_q8_cut_volume_relative_change":delta,
                      "q8":last,"records":rows})
    report={"stage":"P10PX", "status":"PASS_REAL_ACCEPTED_M8_ALGOIM_SELECTED_TET10_ONLY",
            "source_only":True,"fem_started":False,"mesh_generated":False,
            "mesh_changed":False,"gmsh_optimized":False,
            "mesh_sha256":sha(mesh),"geometry_triage_sha256":sha(geo_json),
            "sample_file_sha256":sha(samples),"cxx_source_sha256":sha(source),
            "triage_source_sha256":sha(script),
            "accepted_m8":True,"tet10_count":geometry["tet10_count"],
            "node_count":geometry["node_count"],
            "detj_samples":geometry["tet10_jacobian_quadrature_samples"],
            "min_detj":geometry["minimum_det_j"],
            "multi_quartic_resultant_guard":"PASS_SKIP_EXIT3_SAMP0",
            "all_sample_cases_are_real_m8_elements":True,
            "unsampled_elements_not_approved_for_algoim":True,
            "no_physical_EDV_or_adjoint_approval":True,
            "algoim_spot_checks":cases}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P10PX_M8_REAL_ALGOIM_QA_PASS tested="+str(len(cases))+
          " det_min="+format(geometry["minimum_det_j"],".10g"))
    for case in cases:
        print("P10PX_M8_CASE element="+str(case["element_id"])+
              " pole="+case["pole"]+" q8_rel_tet="+str(case["q8"]["tet_rel"])+
              " q6_q8_cut_change="+str(case["q6_q8_cut_volume_relative_change"]))


if __name__=="__main__":
    try:
        main()
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
        print("P10PX_QA_STOP",exc,file=sys.stderr)
        raise SystemExit(2)
