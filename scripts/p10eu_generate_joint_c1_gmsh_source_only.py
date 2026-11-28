#!/usr/bin/env python3
"""P10EU: deterministic, unexecuted C1 Gmsh source, independent algebraic QA.

No Gmsh, FEM, mesh generation or Windows one-shot marker is invoked here.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import random

import numpy as np

import p10es_m1_measured_smooth_sizing_calibration as es
import p10et_joint_surface_volume_topology_contract as et
from p10ed_verify_original_m1_m2_raw_spatial import CENTRE, kappa

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT / "gmsh/sphere_pore_B6_refined.geo"
ET_SCRIPT = ROOT / "scripts/p10et_joint_surface_volume_topology_contract.py"
ET_JSON = ROOT / "research/evidence/P10ET_SURFACE_VOLUME_CONTRACT_20261122/derived/P10ET_SURFACE_VOLUME_TOPOLOGY_CONTRACT.json"
GEO_OUT = ROOT / "gmsh/P10EU_M2_C1_JOINT_SURFACE_VOLUME_SOURCE_ONLY.geo"
JSON_OUT = ROOT / "research/evidence/P10EU_GMSH_C1_SOURCE_20261122/derived/P10EU_C1_GMSH_SOURCE_AUDIT.json"
PINS = {
    "parent_GEO": "8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0",
    "P10ET_script": "e3507949430a11de003ff044f3145c3d89b811c215fe4d4dc132b9857dbe9600",
    "P10ET_JSON": "69ed863fd22ffe9a4bcd780e1cc187f3e2d54a1d9b91572dfe1df1a4286909bc",
}


def stop(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("P10EU_STOP: " + message)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parents() -> tuple[np.ndarray, dict]:
    for key, path in (("parent_GEO", PARENT), ("P10ET_script", ET_SCRIPT),
                      ("P10ET_JSON", ET_JSON)):
        stop(path.is_file() and sha(path) == PINS[key], "source SHA " + key)
    parent = PARENT.read_text(encoding="utf-8")
    for key in ('Physical Surface("PORE_WALL",8)',
                'Physical Volume("ICE_VOLUME",1)', "Field[2] = Threshold;",
                "Field[2].DistMin=0.0015;", "Field[2].DistMax=0.018;",
                "Mesh.MeshSizeFromPoints=0;", "Mesh.MeshSizeFromCurvature=0;",
                "Mesh.MeshSizeExtendFromBoundary=0;"):
        stop(key in parent, "canonical parent geometry/field: " + key)
    stop(es.NEAR == .00042855883184652975 and
         es.FAR == .0070524788853066865 and
         es.DIST_MIN == .0015 and es.DIST_MAX == .018 and
         es.CORNER_ROUND_RADIUS == 5e-5, "M1 empirical sizing constants")
    j = json.loads(ET_JSON.read_text(encoding="utf-8"))
    p = j["source_only_c1_wall_normal_field"]
    c = np.array(p["M1_bounded_coefficients"])
    stop(np.max(abs(c - [.018, .012593756600121672, -.0031079955054980225])) < 1e-15
         and p["alpha_north"] == et.ALPHA_N
         and p["north_wall_taper_lambda"] == et.LAMBDA_N
         and p["north_axis_extra_lambda"] == et.LAMBDA_N_CORE
         and p["wall_normal_taper_m"] == et.LAYER_TAPER_M
         and abs(p["alpha_south_compensated"] -
                 (1 - .8 * math.exp(-3*c[1]))) < 1e-15,
         "P10ET registered field coefficients")
    return c, p


def clip(t: str) -> str:
    return "min(1,max(0," + t + "))"


def S(t: str) -> str:
    u = clip(t)
    return "(" + u + "*" + u + "*(3-2*" + u + "))"


def positive_round(t: str, e: float) -> str:
    """C1 positive-part: 0 below -e, t above +e, quadratic inside."""
    u = clip("((" + t + "+" + repr(e) + ")/" + repr(2*e) + ")")
    return "(max(0,(" + t + "-" + repr(e) + "))+" + repr(e) + "*" + u + "*" + u + ")"


def expression(coeff: np.ndarray, p: dict) -> str:
    # Single MathEval; nested MathEval field references are intentionally absent.
    rho = "sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)"
    rr = "(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)"
    d = "(" + rho + "-0.001)"
    mu = "((z-0.03)/" + rho + ")"
    mu2 = "((z-0.03)*(z-0.03)/" + rr + ")"
    wn, ws, wc = (S("((" + mu + "-0.6)/0.2)"),
                  S("((-" + mu + "-0.6)/0.2)"),
                  S("((" + mu + "-0.8)/0.1)"))
    kp = "((1-" + S("((" + rho + "-0.0011)/0.0004)") + ")*" + S("((" + mu2 + "-0.36)/0.28)") + ")"
    pa = positive_round("(" + d + "-0.0015)", es.CORNER_ROUND_RADIUS)
    pb = positive_round("(" + d + "-0.018)", es.CORNER_ROUND_RADIUS)
    slope = (es.FAR - es.NEAR)/(es.DIST_MAX - es.DIST_MIN)
    h0 = "(" + repr(es.NEAR) + "+" + repr(slope) + "*(" + pa + "-" + pb + "))"
    beta = ("(" + kp + "*(" + repr(float(coeff[0])) + "*" + wn + "+" +
            repr(float(coeff[1])) + "*" + ws + "+" +
            repr(float(coeff[2])) + "*" + wn + "*" + wc + "))")
    alpha = ("(" + repr(p["alpha_base"]) + "+(" +
             repr(p["alpha_north"] - p["alpha_base"]) + ")*" + wn + "+(" +
             repr(p["alpha_south_compensated"] - p["alpha_base"]) + ")*" + ws + ")")
    fade = S("(" + d + "/" + repr(p["wall_normal_taper_m"]) + ")")
    wall = ("(" + kp + "*" + wn + "*(" +
            repr(p["north_wall_taper_lambda"]) + "+" +
            repr(p["north_axis_extra_lambda"]) + "*" + wc + ")*(1-" + fade + "))")
    expr = ("(" + h0 + "*exp(" + beta + ")*exp(log(1-" +
            alpha + "*" + kp + ")/3)*exp(" + wall + "))")
    stop(len(expr) < 30000 and "F2" not in expr, "flattened MathEval limit")
    return expr


ALLOWED_NAMES = {"x", "y", "z", "sqrt", "min", "max", "exp", "log"}


def compile_safe(expr: str):
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.Load, ast.Add, ast.Sub,
                             ast.Mult, ast.Div, ast.UAdd, ast.USub)):
            continue
        if isinstance(node, ast.Name):
            stop(node.id in ALLOWED_NAMES, "non-Gmsh name")
        elif isinstance(node, ast.Constant):
            stop(type(node.value) in (float, int), "non-numeric literal")
        elif isinstance(node, ast.BinOp):
            stop(isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)),
                 "non-Gmsh binary")
        elif isinstance(node, ast.UnaryOp):
            stop(isinstance(node.op, (ast.UAdd, ast.USub)), "non-Gmsh unary")
        elif isinstance(node, ast.Call):
            stop(isinstance(node.func, ast.Name) and
                 node.func.id in ALLOWED_NAMES - {"x", "y", "z"} and
                 not node.keywords, "non-Gmsh MathEval function")
        else:
            stop(False, "unexpected expression AST " + type(node).__name__)
    return compile(tree, "<P10EU_SOURCE_MATH_ONLY>", "eval")


def eval_expr(code, pt: np.ndarray) -> float:
    x, y, z = (float(v) for v in pt)
    return float(eval(code, {"__builtins__": {}},
                      {"x": x, "y": y, "z": z, "sqrt": math.sqrt,
                       "min": min, "max": max, "exp": math.exp, "log": math.log}))


def pt(d: float, mu: float, phi: float) -> np.ndarray:
    xy = (.001+d)*math.sqrt(max(0., 1-mu*mu))
    return CENTRE + np.array([xy*math.cos(phi), xy*math.sin(phi), (.001+d)*mu])


def numeric_test(code, coeff: np.ndarray, p: dict) -> dict:
    ds = (0., 1e-9, .00005, .000099999, .0001, .000100001, .0002,
          .000399999, .0004, .000400001, .0005, .00145, .0015,
          .00155, .01795, .018, .01805, .025)
    mus = (-1., -.999999, -.9, -.8, -.799999, -.7, -.6, -.599999,
           0., .599999, .6, .7, .799999, .8, .85, .9, .999999, 1.)
    pts = [pt(d, mu, phi) for d in ds for mu in mus
           for phi in (0., .27, 1.78, 3.19, 4.91)]
    rng = random.Random(20261122)
    for _ in range(6000):
        d = .0005*rng.random() if rng.random() < .75 else .025*rng.random()
        pts.append(pt(d, 2*rng.random()-1, 2*math.pi*rng.random()))
    pts = np.array(pts)
    observed = np.array([eval_expr(code, q) for q in pts])
    expected, calibrated, _ = et.calc_draft(pts, coeff, p)
    error = np.abs(observed-expected)/expected
    stop(np.all(np.isfinite(observed)) and np.all(observed > 0) and
         error.max() < 5e-12, "P10ET algebraic 3D field parity")
    rad = np.linalg.norm(pts-CENTRE, axis=1)-.001
    kp = kappa(pts)
    mask1, mask0 = kp >= 1-1e-12, kp == 0
    stop(mask1.any() and mask0.any(), "kappa endpoints")
    qold = (observed[mask1]/es.field2(rad[mask1]))**3
    qcal = (observed[mask1]/calibrated[mask1])**3
    deviation = float(np.max(abs(observed[mask0]/es.field2(rad[mask0])-1)))
    stop(.75-1e-12 <= qold.min() <= qold.max() <= .85+1e-12 and
         .75-1e-12 <= qcal.min() <= qcal.max() <= .85+1e-12 and
         deviation < .012, "nominal h^3 / kappa=0 precontract")
    return {"sample_count":len(pts), "max_relative_h_parity_error":float(error.max()),
            "kappa1_hcube_over_original_Field2":[float(qold.min()),float(qold.max())],
            "kappa1_hcube_over_bounded_M1":[float(qcal.min()),float(qcal.max())],
            "kappa0_max_relative_h_deviation":deviation, "native_Gmsh":0,"FEM":0}


def build_geo(expr: str) -> str:
    return ("// P10EU SOURCE ONLY — native Gmsh/FEM requires separate authorization.\n"
            "// Unmodified included CAD/physical tags/legacy Field2 SHA256 " + PINS["parent_GEO"] + "\n"
            "// Single flattened MathEval on pore Tri6 and neighboring Tet10.\n"
            "nearSize = " + repr(es.NEAR) + ";\n"
            "farSize = " + repr(es.FAR) + ";\n"
            'Include "sphere_pore_B6_refined.geo";\n'
            "Field[6] = MathEval;\n"
            'Field[6].F = "' + expr + '";\n'
            "Background Field=6;\n"
            "Mesh.Algorithm=5;\n"
            "Mesh.Algorithm3D=10;\n"
            "Mesh.MeshSizeExtendFromBoundary=0;\n"
            "Mesh.MeshSizeFromPoints=0;\n"
            "Mesh.MeshSizeFromCurvature=0;\n"
            "Mesh.MeshSizeFactor=1;\n"
            "Mesh.MeshSizeMin=0;\n"
            "Mesh.MeshSizeMax=1e22;\n")


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--selftest", action="store_true")
    a.add_argument("--write", action="store_true")
    a.add_argument("--verify", action="store_true")
    a.add_argument("--geo", type=Path, default=GEO_OUT)
    a.add_argument("--audit-json", type=Path, default=JSON_OUT)
    args = a.parse_args()
    stop(sum((args.selftest,args.write,args.verify)) == 1, "choose one mode")
    coeff, p = parents()
    expr = expression(coeff, p)
    code = compile_safe(expr)
    results = numeric_test(code, coeff, p)
    geo = build_geo(expr)
    stop(geo.count('Include "sphere_pore_B6_refined.geo";') == 1 and
         geo.count("Field[6] = MathEval;") == 1 and
         geo.count("Background Field=6;") == 1 and
         geo.count("Mesh.Algorithm=5;") == 1 and
         geo.count("Mesh.Algorithm3D=10;") == 1 and
         geo.count('Field[6].F = "') == 1 and
         geo.split('Field[6].F = "')[1].split('";')[0] == expr and
         "Mesh 3;" not in geo and "SystemCall" not in geo,
         "single field, exact canonical include, no active mesh command")
    for option in ("Mesh.MeshSizeFromPoints=0;",
                   "Mesh.MeshSizeFromCurvature=0;",
                   "Mesh.MeshSizeExtendFromBoundary=0;",
                   "Mesh.MeshSizeFactor=1;", "Mesh.MeshSizeMin=0;",
                   "Mesh.MeshSizeMax=1e22;"):
        stop(geo.count(option) == 1, "sizing precedence " + option)
    audit = {
        "protocol": "P10EU_UNEXECUTED_SINGLE_FLATTENED_C1_MATHEVAL",
        "parent_sha256": PINS, "generated_GEO_sha256": hashlib.sha256(geo.encode()).hexdigest(),
        "expression_characters": len(expr), "nested_MathEval_count": 0,
        "source_only_parity": results,
        "Gmsh_options": {"Mesh.Algorithm":5,"Mesh.Algorithm3D":10,
                         "Mesh.MeshSizeFromPoints":0,"Mesh.MeshSizeFromCurvature":0,
                         "Mesh.MeshSizeExtendFromBoundary":0,"Mesh.MeshSizeFactor":1,
                         "Mesh.MeshSizeMin":0,"Mesh.MeshSizeMax":1e22},
        "future_real_D025": "both 3D north/south Veff(M2)/Veff(M1) in [.75,.85] at 729QP, 343QP convergence",
        "surface_Tri6_area": "diagnostic only, not a hard acceptance gate",
        "neighbor_gradation": "diagnostic until investigator approves a numerical threshold",
        "status": "NO_NEW_NATIVE_GMSH_NO_FEM_NO_NEW_M2"}
    audit_text = json.dumps(audit, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        for path, content in ((args.geo,geo),(args.audit_json,audit_text)):
            if path.exists():
                stop(path.read_text(encoding="utf-8") == content,
                     "refusing to overwrite changed file: " + str(path))
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(content,encoding="utf-8")
    if args.verify:
        stop(args.geo.is_file() and args.geo.read_text(encoding="utf-8") == geo,
             "source GEO differs from pinned field")
        stop(args.audit_json.is_file() and
             args.audit_json.read_text(encoding="utf-8") == audit_text,
             "source audit JSON differs from pinned field")
    mode = "WRITE" if args.write else "VERIFY" if args.verify else "SELFTEST"
    print("P10EU_C1_GMSH_SOURCE_ONLY_" + mode + "_PASS",
          "samples",results["sample_count"],"math_error",format(results["max_relative_h_parity_error"],".5g"),
          "expression_chars",len(expr),"native_Gmsh=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
