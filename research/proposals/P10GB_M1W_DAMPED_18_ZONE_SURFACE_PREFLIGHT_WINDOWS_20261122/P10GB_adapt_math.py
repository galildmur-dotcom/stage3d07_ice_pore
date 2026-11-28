#!/usr/bin/env python3
"""P10GB: source-only C1 damped 18-zone feedback from real M1V 729QP.

Full-volume actual q=0.825 is a goal, never a prediction or FEM GO.
Uniform goal κ=1: spatial size compensation offsets stochastic Gmsh bias.
"""
import json
import math
from pathlib import Path
import random

import P10FX_uniform_math as prior

HERE=Path(__file__).resolve().parent
DATA=HERE/"P10GA_M0_M1V_SIGNED18_343_729QP.json"
TARGET=.825
BETA=.40
M0_SHA="926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
M1V_SHA="c3f69d3d6f3d88333f2aec7a5aa13db535f9eed4e76ba6c29bed4b88fa31ea06"


def need(ok,why):
    if not ok:
        raise RuntimeError("P10GB_MATH_STOP: "+why)


def calibration():
    d=json.loads(DATA.read_text(encoding="utf-8"))
    need(d.get("protocol")=="P10GA_INDEPENDENT_M0_M1V_FIXED_18_SIGNED_ZONES_343_729QP" and
         d.get("M0_sha256")==M0_SHA and d.get("M1V_sha256")==M1V_SHA and
         d.get("curved_geometry_gate") is True and
         d.get("quadrature_stable_below_0p02") is True and
         d.get("strict_18_zone_pass_count")==7 and
         d.get("verdict")=="M1V_ADAPTATION_STOP_NO_FEM",
         "real M1V source evidence mismatch")
    rows=d["levels"]["9"]["zones18"]
    need(len(rows)==18 and
         max(abs(x["M1V_over_M0_Veff_ratio"]-y["M1V_over_M0_Veff_ratio"])
             for x,y in zip(d["levels"]["7"]["zones18"],rows))<.02,
         "343-to-729QP observed response unstable")
    old=prior.load_matrix()
    correction=[]
    raw=[]
    for r in range(3):
        zones=rows[6*r:6*r+6]
        need([x["hemisphere"] for x in zones]==["north","south"]*3,
             "signed hemisphere order mismatch")
        # Order mu=-.8,-.6,-.2,+.2,+.6,+.8 (south→north).
        ordered=[zones[i] for i in (1,3,5,4,2,0)]
        residual=[math.log(TARGET/x["M1V_over_M0_Veff_ratio"])
                  for x in ordered]
        raw.append(residual)
        correction.append([old[r][i]+BETA*residual[i] for i in range(6)])
    need(max(abs(v) for row in raw for v in row)<.35,
         "residual too large for cautious source-only update")
    need(all(math.isfinite(v) for row in correction for v in row),
         "nonfinite corrected field")
    return correction,raw,old


def generated_geo():
    original=prior.M0_GEO.read_text(encoding="utf-8")
    base=prior.baseline_field(original)
    matrix,residual,old=calibration()
    logc=prior.logcomp_expression(matrix)
    field=f"({base})*exp((log({prior.PREVIOUS_NOMINAL:.17g})+({logc}))/3)"
    geo=(
        "// P10GB: FRESH M1W from M0, 18 REAL signed-zone 729QP M1V feedback.\n"
        "// BETA=0.40 damped C1 correction; target ACTUAL 0.825 everywhere.\n"
        "// Field is empirical Gmsh-bias compensation, NOT physical kappa(x).\n"
        "// Surface 2D preflight precedes exactly one native 3D attempt.\n"
        'Include "M0.geo";\n'
        "Field[4] = MathEval;\n"
        f"Field[4].F = StrCat(\n  {prior.split_for_gmsh(logc)}\n);\n"
        "Field[5] = MathEval;\n"
        f"Field[5].F = StrCat(\n  {prior.split_for_gmsh(field)}\n);\n"
        "Background Field=5;\n"
        "Mesh.Algorithm=5;\nMesh.Algorithm3D=10;\n"
        "Mesh.ElementOrder=2;\nMesh.HighOrderOptimize=1;\n"
        "Mesh.MeshSizeExtendFromBoundary=0;\n"
        "Mesh.MeshSizeFromPoints=0;\nMesh.MeshSizeFromCurvature=0;\n"
        "Mesh.MeshSizeMin=0;\nMesh.MeshSizeMax=1e22;\n"
        "Mesh.MshFileVersion=2.2;\nMesh.Binary=0;\n"
    )
    need(geo.count('Include "M0.geo"')==1 and
         geo.count("Background Field=5;")==1 and
         "F3" not in field and "F4" not in field,
         "native Gmsh source contract failed")
    return geo,base,matrix,logc,field


def math_selftest():
    geo,base,matrix,logc,field=generated_geo()
    _,_,_,_,oldfield=prior.generated_geo()
    safe={"__builtins__":{},"sqrt":math.sqrt,"min":min,"max":max,
          "exp":math.exp,"log":math.log}
    a=compile(logc,"<P10GB correction>","eval")
    b=compile(field,"<P10GB size>","eval")
    c=compile(base,"<M0 size>","eval")
    d=compile(oldfield,"<M1V old size>","eval")
    rng=random.Random(20261122)
    samples=[]
    for r in prior.RAD_KNOTS:
        for mu in prior.MU_KNOTS:
            radius=.001+r
            samples.append((radius*math.sqrt(1-mu*mu),0.,.03+radius*mu))
    for _ in range(6000):
        rad=.001+rng.uniform(0,.027)
        mu=rng.uniform(-1,1)
        phi=rng.uniform(0,math.tau)
        samples.append((rad*math.sqrt(1-mu*mu)*math.cos(phi),
                        rad*math.sqrt(1-mu*mu)*math.sin(phi),.03+rad*mu))
    error=0.; h_change=0.; low=math.inf;high=0.
    for x,y,z in samples:
        context=dict(safe,x=x,y=y,z=z)
        expected=prior.evaluate_numeric(matrix,x,y,z)
        actual=eval(a,context)
        h0=eval(c,context)
        h=eval(b,context)
        hprev=eval(d,context)
        predicted=h0*(prior.PREVIOUS_NOMINAL*math.exp(expected))**(1/3)
        need(h0>0 and h>0 and hprev>0 and math.isfinite(h),"nonpositive field")
        error=max(error,abs(actual-expected),abs(h-predicted)/predicted)
        h_change=max(h_change,abs(h/hprev-1))
        local=(h/h0)**3
        low=min(low,local);high=max(high,local)
    need(error<2e-12 and h_change<.06,
         "C1 expression mismatch or undamped feedback >6 percent in h")
    return {"status":"P10GB_SOURCE_ONLY_DAMPED_18_ZONE_C1_MATH_PASS_NO_NATIVE_NO_FEM",
            "sample_points":len(samples),"maximum_source_expression_discrepancy":error,
            "maximum_size_h_fraction_change_from_M1V":h_change,
            "target_actual_ratio":TARGET,"strict_real_18_zone_gate":[.8,.85],
            "feedback_gain":BETA,"nominal_h3_h0_min":low,"nominal_h3_h0_max":high,
            "new_log_matrix":matrix,"expression_characters":len(field),
            "source_only_not_geometry_or_uniformity_go":True}


if __name__=="__main__":
    print(json.dumps(math_selftest(),ensure_ascii=False,indent=2))
