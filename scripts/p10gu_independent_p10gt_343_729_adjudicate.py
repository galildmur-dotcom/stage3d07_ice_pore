#!/usr/bin/env python3
"""Independent P10GT raw Tet10 27/343/729QP D-027 read-only audit."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile
import numpy as np

import p10gj_offline_343_729_adjudicate as parent

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"research/proposals/P10GL_ONE_P10GK_HXT10_WINDOWS_20261123/P10GJ_D027_FROZEN_GATES.json"
BASELINE=ROOT/"research/proposals/P10GL_ONE_P10GK_HXT10_WINDOWS_20261123/P10GJ_M0_QP_BASELINE.json"
PIN="7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3"
M0_SHA="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"


def sha(raw):return hashlib.sha256(raw).hexdigest()
def check(ok,msg):
    if not ok:raise ValueError("P10GU_INDEPENDENT_STOP: "+msg)


def adjudicate(path):
    raw=Path(path).read_bytes()
    check(sha(raw)==PIN,"original P10GT evidence SHA changed")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        check(z.testzip() is None and len(z.namelist())==8,"ZIP CRC/file count")
        check(all("/" not in n and "\\" not in n for n in z.namelist()),"archive path")
        manifest=json.loads(z.read("P10GT_MANIFEST.json"))
        check(manifest["revision"]=="P10GT_R1_ONE_HXT10_ALGO6_A09_MU20_MESH_ONLY" and
              manifest["native_3d_attempts"]==1 and manifest["FEM_attempts"]==0 and
              manifest["native"]["native_exit_code"]==0 and not manifest["native"]["stop_reason"],
              "one native HXT10 not confirmed")
        frozen_raw=z.read("P10GJ_D027_FROZEN_GATES.json")
        baseline_raw=z.read("P10GJ_M0_QP_BASELINE.json")
        check(sha(frozen_raw)==sha(FROZEN.read_bytes()) and
              sha(baseline_raw)==sha(BASELINE.read_bytes()),"frozen M0 baseline/policy changed")
        frozen=json.loads(frozen_raw)
        ref=json.loads(baseline_raw)
        check(frozen["M0_msh_sha256"]==M0_SHA and ref["canonical_M0_msh_sha256"]==M0_SHA,
              "wrong canonical M0")
        geo=z.read("P10GT_HXT10.geo")
        check(b"Mesh.Algorithm = 6;" in geo and b"Mesh.Algorithm3D = 10;" in geo and
              b"Background Field = 7;" in geo and b"Mesh.MeshSizeFactor = 0.9378887276834518;" in geo,
              "wrong new geometry size field")
        log=z.read("P10GT_GMSH_3D.log")
        check(sha(log)==manifest["log_sha256"] and b"Done meshing 3D" in log and
              b"Meshing order 2" in log and b"Error   :" not in log,
              "Gmsh native log")
        msh=z.read("P10GT_HXT10.msh")
        check(sha(msh)==manifest["mesh_sha256"],"original 3D MSH SHA mismatch")
        nodes,tets,faces=parent.read_msh(msh)
        check(len(tets)==manifest["qa27"]["tet10"] and len(tets)>0,"Tet10 count mismatch")
        full,min27=parent.baseline_volumes(nodes,tets)
        q7=parent.sample(nodes,tets,full,7)
        q9=parent.sample(nodes,tets,full,9)
        j7=parent.compare(q7,ref,7)
        j9=parent.compare(q9,ref,9)
        ratios7=np.array([r["M1_over_M0_Q_V"] for r in j7["signed18"]])
        ratios9=np.array([r["M1_over_M0_Q_V"] for r in j9["signed18"]])
        delta=float(np.max(np.abs(ratios7-ratios9)))
        old_mean=ref["M0"]["volume_m3"]/ref["M0"]["tet10"]
        global7=float((q7["total_volume"]/len(tets))/old_mean)
        global9=float((q9["total_volume"]/len(tets))/old_mean)
        policy=frozen["fixed_policy"]
        macc=policy["macro_QP_effective_Veff_assessment"]
        macros=[]
        for row in j9["macros"]:
            if row["M0_Neff"]<macc["minimum_baseline_effective_Tet10_for_hard_macro"]:
                continue
            polar=row["name"].startswith("near_0_500um_polar_abs_mu_ge_0p8")
            high=(macc["populated_near_polar_d_le_0p5mm_ratio_max"] if polar
                  else macc["populated_macro_ratio_max"])
            low=macc["populated_macro_ratio_min"]
            macros.append({"name":row["name"],"M0_Neff":row["M0_Neff"],
                           "M1_Neff":row["M1_Neff"],"QV729":row["Q_V"],
                           "allowed":[low,high],"pass":low<=row["Q_V"]<=high})
        prelim=manifest["D027_27qp_preliminary"]
        checks={
            "27QP_preliminary":prelim["27qp_preliminary_all_pass"] is True,
            "343QP_detJ_positive":q7["min_detJ"]>0,
            "729QP_detJ_positive":q9["min_detJ"]>0,
            "global_QV343_in_0p80_0p85":.8<=global7<=.85,
            "global_QV729_in_0p80_0p85":.8<=global9<=.85,
            "signed18_343_729_delta_le_0p02":delta<=.02,
            "populated_macros_D027":all(x["pass"] for x in macros),
            "CAD_volume343":abs(q7["total_volume"]/parent.CAD_VOL-1)<=.005,
            "CAD_volume729":abs(q9["total_volume"]/parent.CAD_VOL-1)<=.005,
        }
        return {"protocol":"P10GU_INDEPENDENT_REAL_P10GT_27_343_729QP_D027_NO_FEM",
                "original_zip_sha256":PIN,"mesh_sha256":sha(msh),
                "nodes":len(nodes)-1,"tet10":len(tets),
                "surface_physical_counts":{str(k):v for k,v in sorted(faces.items())},
                "minimum_detJ_27_343_729":[min27,float(q7["min_detJ"]),float(q9["min_detJ"])],
                "global_QV343":global7,"global_QV729":global9,
                "max_signed18_QV343_729_delta":delta,
                "legacy_signed18_in_0p80_0p85":int(np.sum((ratios9>=.8)&(ratios9<=.85))),
                "signed18_343":j7,"signed18_729":j9,
                "populated_macros":macros,"checks":checks,
                "D027_robust_mesh_gate":all(checks.values()),
                "FEM_attempts":0,"FEM_GO":False}


if __name__=="__main__":
    result=adjudicate(sys.argv[1])
    print(json.dumps(result,indent=2,ensure_ascii=False))
