#!/usr/bin/env python3
"""Independent raw P10GL Tet10 343/729QP D-027 audit AFTER native evidence.

NO native Gmsh and NO FEM; inherits P10GJ audited Duffy/Tet10 shape functions
for direct like-for-like comparison against immutable signed M0 343/729QP.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np

import p10gj_offline_343_729_adjudicate as parent

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"research/proposals/P10GL_ONE_P10GK_HXT10_WINDOWS_20261123"
BASELINE=SOURCE/"P10GJ_M0_QP_BASELINE.json"
FROZEN=SOURCE/"P10GJ_D027_FROZEN_GATES.json"
M0_SHA="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
GEO="P10GL_ONE_P10GK_M1_HXT10.geo"
MESH="P10GL_M1_SOUTH_C1_CANDIDATE.msh"


def need(ok,msg):
    if not ok:raise ValueError("P10GL_INDEPENDENT_STOP: "+msg)


def sha(b):return hashlib.sha256(b).hexdigest()


def adjudicate(path):
    raw=Path(path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(z.testzip() is None,"ZIP CRC failure")
        names=z.namelist()
        need(len(names)==len(set(names)) and all("/" not in n and "\\" not in n for n in names),
             "unsafe evidence ZIP entries")
        report=json.loads(z.read("P10GL_M1_MANIFEST.json"))
        frozen=json.loads(z.read("P10GJ_D027_FROZEN_GATES.json"))
        need(sha(z.read("P10GJ_D027_FROZEN_GATES.json"))==sha(FROZEN.read_bytes()),
             "M0-only frozen D-027 thresholds changed")
        need(frozen["M0_msh_sha256"]==M0_SHA,"different canonical M0")
        need(sha(z.read(GEO))==sha((SOURCE/GEO).read_bytes()),
             "P10GL wrapper GEO changed")
        need(sha(z.read("P10GL_SOURCE_SHA256.json"))==
             sha((SOURCE/"P10GL_SOURCE_SHA256.json").read_bytes()),
             "release source manifest changed")
        need(report["revision"]=="P10GL_R1_USER_APPROVED_ONE_P10GK_C1_HXT10_3D_NO_FEM"
             and report["native_3d_attempts"]==1
             and report["FEM_attempts"]==0
             and report["native"]["native_exit_code"]==0
             and report["native"]["stop_reason"]=="",
             "real native one-shot Gmsh evidence invalid")
        log=z.read("P10GL_GMSH_3D.log").decode("utf-8",errors="replace")
        need("Gmsh 4.15.2" in log and "Done meshing 3D" in log
             and "Meshing order 2" in log and "Error   :" not in log,
             "Gmsh log lacks complete native Tet10 3D")
        need(z.read("P10GK_R1_C1_SOUTH_POLE_SOURCE_ONLY_20261123.zip")==
             (SOURCE/"P10GK_R1_C1_SOUTH_POLE_SOURCE_ONLY_20261123.zip").read_bytes(),
             "P10GK C1 source release changed")
        mesh=z.read(MESH)
        need(sha(mesh)==report["mesh_sha256"],"candidate mesh SHA mismatch")
        nodes,tets,faces=parent.read_msh(mesh)
        full,min27=parent.baseline_volumes(nodes,tets)
        a=parent.sample(nodes,tets,full,7)
        b=parent.sample(nodes,tets,full,9)
        ref=json.loads(BASELINE.read_text())
        q7=parent.compare(a,ref,7)
        q9=parent.compare(b,ref,9)
        v7=np.array([r["M1_over_M0_Q_V"] for r in q7["signed18"]])
        v9=np.array([r["M1_over_M0_Q_V"] for r in q9["signed18"]])
        delta=float(np.max(np.abs(v7-v9)))
        oldmean=ref["M0"]["volume_m3"]/ref["M0"]["tet10"]
        global7=float((a["total_volume"]/len(tets))/oldmean)
        global9=float((b["total_volume"]/len(tets))/oldmean)
        p=frozen["fixed_policy"]
        macro_policy=p["macro_QP_effective_Veff_assessment"]
        macros=[]
        for row in q9["macros"]:
            if row["M0_Neff"]<macro_policy["minimum_baseline_effective_Tet10_for_hard_macro"]:
                continue
            north_south=row["name"].startswith("near_0_500um_polar_abs_mu_ge_0p8")
            hi=(macro_policy["populated_near_polar_d_le_0p5mm_ratio_max"] if north_south
                else macro_policy["populated_macro_ratio_max"])
            low=macro_policy["populated_macro_ratio_min"]
            macros.append({"name":row["name"],"M0_Neff":row["M0_Neff"],
                           "M1_Neff":row["M1_Neff"],"QV729":row["Q_V"],
                           "allowed":[low,hi],"pass":low<=row["Q_V"]<=hi})
        preliminary=report.get("D027_preliminary_27QP",{})
        checks={
            "native_27QP_preliminary":preliminary.get("27qp_preliminary_all_pass") is True,
            "all_343QP_sampled_detJ_positive":a["min_detJ"]>0,
            "all_729QP_sampled_detJ_positive":b["min_detJ"]>0,
            "global_QV343_in_0p80_0p85":.8<=global7<=.85,
            "global_QV729_in_0p80_0p85":.8<=global9<=.85,
            "all_18_signed_343_729_delta_max_0p02":delta<=.02,
            "all_populated_macro_D027_gates":all(x["pass"] for x in macros),
            "CAD_vol343_rel_error_max_0p005":
                abs(a["total_volume"]/parent.CAD_VOL-1)<=.005,
            "CAD_vol729_rel_error_max_0p005":
                abs(b["total_volume"]/parent.CAD_VOL-1)<=.005,
        }
        legacy=int(sum(.8<=x<=.85 for x in v9))
        return {"protocol":"P10GL_INDEPENDENT_RAW_TET10_343_729_D027_NO_FEM",
                "original_evidence_sha256":sha(raw),"mesh_sha256":sha(mesh),
                "nodes":len(nodes)-1,"tet10":len(tets),
                "tri6_physical_counts":{str(k):v for k,v in sorted(faces.items())},
                "sampled_min_detJ_27_343_729":[min27,a["min_detJ"],b["min_detJ"]],
                "global_QV343":global7,"global_QV729":global9,
                "max_signed18_QV343_729_delta":delta,
                "legacy_18_0p80_0p85_diagnostic_count":legacy,
                "signed343":q7,"signed729":q9,"populated_macro_hard":macros,
                "D027_checks":checks,"D027_robust_mesh_gate":all(checks.values()),
                "approval_status":"MESH_QA_ONLY_SEPARATE_SCIENTIFIC_GO_REQUIRED",
                "FEM_attempts":0,"FEM_authorized":False}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--selftest",action="store_true")
    ap.add_argument("--evidence",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    parent.selftest()
    need(sha(FROZEN.read_bytes())==
         "2dcb1ae0444f4bcdedc427ce661c8a4c7bc1018d6a34c282f1434e3b1b378aea",
         "old frozen baseline file mismatch")
    if a.selftest:
        print("P10GL_INDEPENDENT_27_343_729QP_SELFTEST_PASS_NO_MESH_NO_FEM")
        return
    need(a.evidence is not None,"need --evidence")
    result=adjudicate(a.evidence)
    if a.out:
        with a.out.open("x",encoding="utf-8") as f:
            json.dump(result,f,ensure_ascii=False,indent=2);f.write("\n")
    print("P10GL_D027_POSTNATIVE_RESULT",json.dumps({
        "mesh_gate":result["D027_robust_mesh_gate"],
        "global_QV729":result["global_QV729"],
        "legacy_18_diagnostic":result["legacy_18_0p80_0p85_diagnostic_count"]}))


if __name__=="__main__":main()
