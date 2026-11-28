#!/usr/bin/env python3
"""P10GK R1 C1 south-pole MathEval source QA; NO mesh or FEM.

Modes:
  --selftest   stdlib-only on Linux/Windows, no subprocess/native Gmsh
  --preflight  Windows pinned native Gmsh4.15.2 -parse_and_exit ONLY
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
PROJECT = Path(r"G:\ildar\Stage3D07")
RUNS = PROJECT / "LOCAL_RUNS"
GMSH = Path(r"C:\gmsh-4.15.2-Windows64\gmsh.exe")
M0_SHA = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
REV = "P10GK_R1_C1_SOUTH_FOCUS_SOURCE_ONLY"
GEO = "P10GK_M1_SOUTH_C1_SOURCE_ONLY.geo"
MANIFEST = "P10GK_SOURCE_SHA256.json"
POLICY = "P10GK_SOURCE_POLICY.json"
TR = "min(1,max(0,(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.0015)/0.0005))"
TS = "min(1,max(0,(((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))+0.8)/0.2))"
FINAL = "F3*(1-0.06*(1-F4*F4*(3-2*F4))*(1-F5*F5*(3-2*F5)))"
PINNED = {
    "M0.geo": "ac6981b04d205cc00bf50ddbaf6722c884af7189ef4e3e743253c754f69e62aa",
    "sphere_pore_B6_refined.geo": "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0",
    "M0_ROTATED.geo": "21cef72e9e0d7fde3a383b6db3ebde4bc6b62cf180b7b65947e5fe1fa57f0c9a",
    "sphere_pore_B6_refined_rotated.geo": "e3f4d1c472e4d047962bf05f63406f2bbb20b89f20e74ac2e6f2ba8cfd305329",
}
SOURCE_FILES = {
    GEO, "M0.geo", "M0_ROTATED.geo", "sphere_pore_B6_refined.geo",
    "sphere_pore_B6_refined_rotated.geo", "P10GJ_M1_ROTATED_CANDIDATE.geo",
    "P10GJ_D027_GATE_POLICY.json", POLICY, "P10GK_source_qa.py",
    "01_P10GK_NATIVE_PARSE_ONLY.cmd", "README_P10GK_RU.md",
}


def need(condition, message):
    if not condition:
        raise ValueError("P10GK_SOURCE_ONLY_STOP: " + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for data in iter(lambda: source.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_field_expressions():
    text = (HERE / GEO).read_text(encoding="utf-8")
    f = {int(idx): expr for idx, expr in re.findall(
        r'Field\[(\d+)\]\.F\s*=\s*"([^"]+)"\s*;', text)}
    need(f == {4: TR, 5: TS, 6: FINAL}, "new MathEval expressions modified")
    need('Include "M0_ROTATED.geo";' in text, "wrong parent geometry include")
    need(len(re.findall(r"Background\s+Field\s*=", text)) == 1
         and re.search(r"Background\s+Field\s*=\s*6\s*;", text),
         "background field must be F6")
    for idx in (4, 5, 6):
        need(re.search(r"Field\[" + str(idx) + r"\]\s*=\s*MathEval\s*;", text),
             "required MathEval missing")
    for required in (
        "Mesh.MeshSizeFactor = 0.9378887276834518;",
        "Mesh.Algorithm3D = 10;", "Mesh.ElementOrder = 2;",
        "Mesh.HighOrderOptimize = 1;", "Mesh.MshFileVersion = 2.2;",
        "Mesh.Binary = 0;",
    ):
        need(required in text, "driver setting modified: " + required)
    need("Mesh.MeshSizeExtendFromBoundary=0;" in
         (HERE / "M0_ROTATED.geo").read_text(encoding="utf-8"),
         "M0 no-boundary-extension setting missing")
    return f


def source_gate():
    release = read_json(HERE / MANIFEST)
    need(release.get("revision") == REV
         and release.get("native_mesh_3d_authorized") is False
         and release.get("FEM_authorized") is False
         and set(release.get("files", {})) == SOURCE_FILES,
         "release source manifest invalid")
    for name, digest in release["files"].items():
        need((HERE / name).is_file() and sha(HERE / name) == digest,
             "missing/modified release source " + name)
    for name, digest in PINNED.items():
        need(sha(HERE / name) == digest, "canonical or rotated GEO modified " + name)
    parent = (HERE / "M0.geo").read_text(encoding="utf-8")
    rotated = (HERE / "M0_ROTATED.geo").read_text(encoding="utf-8")
    need(rotated.replace('Include "sphere_pore_B6_refined_rotated.geo";',
                         'Include "sphere_pore_B6_refined.geo";') == parent,
         "M0 C1 source field changed")
    cad = (HERE / "sphere_pore_B6_refined.geo").read_text(encoding="utf-8")
    cadrot = (HERE / "sphere_pore_B6_refined_rotated.geo").read_text(encoding="utf-8")
    anchor = "Sphere(3) = {poreCX,poreCY,poreCZ,r0};"
    rotate = "Rotate { {1,0,0}, {poreCX,poreCY,poreCZ}, Pi/2 } { Volume{3}; }"
    need(cadrot.replace(anchor + "\n" + rotate, anchor) == cad,
         "OCC pore axis and geometry changed")
    p = read_json(HERE / POLICY)
    need(p.get("revision") == REV and p.get("scientific_status") == "PROPOSED_NOT_MESHED"
         and p.get("native_mesh_3d_authorized") is False
         and p.get("FEM_authorized") is False
         and p.get("future_3d_attempt_requires_fresh_user_permission") is True
         and p.get("parent_M0_msh_sha256") == M0_SHA
         and p.get("new_local_south_alpha") == 0.06
         and p.get("global_mesh_size_factor") == 0.9378887276834518
         and p.get("south_physical_polar_0_500um_QV_hard_max") == 0.98
         and p.get("global_M1_to_M0_Veff_hard") == [.8, .85]
         and p.get("signed18_individual_0p80_0p85") == "diagnostic_only",
         "source-only policy changed")
    old = read_json(HERE / "P10GJ_D027_GATE_POLICY.json")
    need(old["mandatory_global_Veff_ratio"] == [.8, .85]
         and old["macro_QP_effective_Veff_assessment"]
         ["populated_near_polar_d_le_0p5mm_ratio_max"] == .98,
         "historical D-027 altered")
    get_field_expressions()
    return p


def softplus(t, eps=.00005):
    u = min(1., max(0., (t + eps) / (2 * eps)))
    return max(0., t - eps) + eps * u * u


def m0_radial(x, y, z):
    radius = math.sqrt(x*x + y*y + (z - .03)**2 + 1e-24)
    d = radius - .001
    return .00046165100702485221 + .43244858021734583 * (
        softplus(d-.0015) - softplus(d-.018))


def evaluate_raw(x, y, z, fields):
    # Trusted pinned source only, restricted expression globals, no filesystem/code calls.
    safe = {"__builtins__": {}, "sqrt": math.sqrt, "min": min, "max": max}
    env = {"x": x, "y": y, "z": z, "F3": m0_radial(x, y, z)}
    for index in (4, 5, 6):
        env["F" + str(index)] = eval(fields[index], safe, env)
    return env


def sample(d, mu):
    radius = .001 + d
    return (radius*math.sqrt(max(0., 1-mu*mu)), 0., .03+radius*mu)


def test_field():
    f = get_field_expressions()
    max_abs = 0.
    lowest = 2.; highest = 0.
    for j in range(121):
        d = .020 * j / 120
        for k in range(101):
            mu = -1 + 2*k / 100
            v = evaluate_raw(*sample(d, mu), f)
            tr = min(1., max(0., (d-.0005)/.0005))
            ts = min(1., max(0., (mu+.8)/.2))
            expect = 1-.06*(1-tr*tr*(3-2*tr))*(1-ts*ts*(3-2*ts))
            measured = v["F6"]/v["F3"]
            max_abs = max(max_abs, abs(expect-measured))
            lowest = min(lowest, measured);highest = max(highest, measured)
            need(math.isfinite(v["F6"]) and v["F6"] > 0,
                 "nonpositive/nonfinite final field")
    need(max_abs < 5e-13, "MathEval/analytic weights disagree")
    need(abs(lowest-.94) < 1e-13 and abs(highest-1.) < 1e-13,
         "wrong local size bound")
    def ratio(d, mu):
        v = evaluate_raw(*sample(d, mu), f)
        return v["F6"]/v["F3"]
    for d in (0., .00025, .0005):
        need(abs(ratio(d, -1.)-.94) < 2e-13, "south cap not fully targeted")
        need(abs(ratio(d, 1.)-1.) < 2e-13, "north cap unexpectedly touched")
    for d in (.001, .002, .01):
        need(abs(ratio(d, -1.)-1.) < 2e-13, "field failed to decay radially")
    for d0,mu0,step,tol in (
        (.0005,-1.,1e-8,.03),(.001,-1.,1e-8,.03),
        (.00025,-.8,1e-6,.001),(.00025,-.6,1e-6,.001)):
        if mu0==-1.:
            f1=lambda u:ratio(u,mu0)
            p=d0
        else:
            f1=lambda u:ratio(d0,u)
            p=mu0
        left=(f1(p)-f1(p-step))/step
        right=(f1(p+step)-f1(p))/step
        need(abs(left-right)<tol, "C1 transition seam derivative jump")
    return {"sampled_points":121*101,"max_analytic_MathEval_ratio_error":max_abs,
            "factor_min":lowest,"factor_max":highest,
            "C1_seam_tests":4,"native_Gmsh_3d":0,"FEM":0}


def require_windows():
    need(sys.platform == "win32", "native parse-only requires user Windows 11")
    need((PROJECT / "meshes").is_dir() and RUNS.is_dir(),
         "canonical G: project folders missing")
    need(sha(PROJECT / "meshes" / "M0.msh") == M0_SHA,
         "canonical M0.msh changed")
    need(GMSH.is_file(), "pinned native Gmsh4.15.2 missing")
    result = subprocess.run([str(GMSH), "-version"], cwd=HERE,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=15, check=False)
    version = result.stdout.decode("utf-8", errors="replace").strip()
    need(result.returncode == 0 and "4.15.2" in version, "native Gmsh wrong version")
    return {"gmsh_version":version,"gmsh_exe_sha256":sha(GMSH),
            "parent_M0_sha256":M0_SHA}


def preflight():
    policy = source_gate()
    samples = test_field()
    installed = require_windows()
    folder = RUNS / ("P10GK_SOURCE_PREFLIGHT_" + datetime.now(timezone.utc)
                     .strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(parents=False, exist_ok=False)
    report = {"revision":REV,"status":"P10GK_SOURCE_PREFLIGHT_STOP_NO_MESH_NO_FEM",
              "policy":policy,"math_eval_samples":samples,"installed":installed,
              "native_1d_2d_3d_attempts":0,"FEM_attempts":0}
    try:
        for name in (GEO,"M0_ROTATED.geo","sphere_pore_B6_refined_rotated.geo"):
            with (HERE / name).open("rb") as a,(folder / name).open("xb") as b:
                shutil.copyfileobj(a,b)
            need(sha(folder/name)==sha(HERE/name),"source copy mismatch")
        cmd = [str(GMSH),str(folder/GEO),"-parse_and_exit","-nopopup","-nt","2"]
        need(not any(x in cmd for x in ("-1","-2","-3")),"forbidden meshing command")
        result = subprocess.run(cmd,cwd=folder,stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                timeout=60,check=False)
        log=folder/"P10GK_NATIVE_PARSE_ONLY.log"
        log.write_text(result.stdout.decode("utf-8",errors="replace"),encoding="utf-8")
        need(result.returncode==0 and not re.search(r"\bError\s*:",
             log.read_text(encoding="utf-8")),"native parse-only STOP")
        need(not list(folder.glob("*.msh")),"unexpected mesh from parse-only")
        report["status"]="P10GK_SOURCE_AND_NATIVE_PARSE_ONLY_PASS_NO_MESH_NO_FEM"
        report["native_parse_only_exit_code"]=result.returncode
        report["native_parse_log_sha256"]=sha(log)
        code=0
    except BaseException as error:
        report["error"]=repr(error)
        (folder/"P10GK_PREFLIGHT_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
        code=2
    write_new(folder/"P10GK_SOURCE_REPORT.json",report)
    with zipfile.ZipFile(folder/"P10GK_SOURCE_PREFLIGHT_EVIDENCE.zip","x",
                         compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix.lower()!=".zip":z.write(p,p.name)
        for name in (POLICY,MANIFEST):z.write(HERE/name,name)
    print(report["status"],flush=True)
    print("SEND:",folder/"P10GK_SOURCE_PREFLIGHT_EVIDENCE.zip",flush=True)
    return code


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--selftest",action="store_true")
    g.add_argument("--preflight",action="store_true")
    a=p.parse_args()
    source_gate()
    samples=test_field()
    print("P10GK_SOURCE_C1_12221_SAMPLES_PASS",json.dumps(samples),flush=True)
    if a.selftest:
        print("P10GK_NO_MESH_NO_FEM_SELFTEST_PASS",flush=True)
        return 0
    return preflight()


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception as error:
        print("P10GK_STOP:",repr(error),file=sys.stderr,flush=True)
        raise SystemExit(2)
