#!/usr/bin/env python3
"""P10FW source-only C1 compensation of observed Gmsh zone-density bias.

Scientific target q=0.825 CONSTANT in ALL physical zones. Spatial variations
in prescribed h correct generator bias, and have no physics-derived kappa.
No claim that the resulting native mesh achieves the target.
"""
import json
import math
from pathlib import Path
import random
import re

HERE=Path(__file__).resolve().parent
DATA=HERE/"P10FW_REAL_M0_M1_SIGNED_18_ZONE_729QP.json"
M0_GEO=HERE/"M0.geo"
TARGET=.825
PREVIOUS_NOMINAL=.8
RAD_KNOTS=(.0001,.0003,.0005)
MU_KNOTS=(-.8,-.6,-.2,.2,.6,.8)


def need(ok,message):
    if not ok:
        raise RuntimeError("P10FW_MATH_STOP: "+message)


def smooth_numeric(x):
    x=max(0.,min(1.,x))
    return x*x*(3-2*x)


def smooth_expression(value):
    v=f"min(1,max(0,({value})))"
    return f"(({v})*({v})*(3-2*({v})))"


def load_matrix():
    d=json.loads(DATA.read_text(encoding="utf-8"))
    need(d.get("protocol")=="P10FW_REAL_18_ZONE_SIGNED_HEMISPHERE_CALIBRATION"
         and abs(d["target_actual_Veff_ratio_everywhere"]-TARGET)<1e-14
         and d["max_signed_zone_q_343_to_729_delta"]<.02,
         "unexpected/unstable independent source measurements")
    old=d["sample_levels"]["9"]["zones18"]
    need(len(old)==18,"18 zones expected")
    vals=[]
    for r in range(3):
        row=old[r*6:(r+1)*6]
        need([x["hemisphere"] for x in row]==["north","south"]*3,
             "signed hemisphere orientation changed")
        # Order from south pole to north pole.
        q=[row[1],row[3],row[5],row[4],row[2],row[0]]
        vals.append([math.log(TARGET/x["measured_M1_over_M0"]) for x in q])
    need(max(abs(x) for row in vals for x in row)<.36,
         "empirical field compensation exceeds safe calibration range")
    return vals


def baseline_field(geo):
    token="Field[3].F = StrCat("
    need(geo.count(token)==1,"canonical M0 smooth field missing")
    body=geo.split(token,1)[1].split(");",1)[0]
    formula="".join(re.findall(r'"([^"]*)"',body))
    need(len(formula)>500 and formula.count("(")==formula.count(")") and
         "F3" not in formula,"bad baseline MathEval")
    return formula


def split_for_gmsh(expr):
    need(expr and expr.count("(")==expr.count(")") and "+-" not in expr,
         "malformed native MathEval expression")
    return ",\n  ".join('"'+expr[i:i+340]+'"' for i in range(0,len(expr),340))


def logcomp_expression(matrix):
    r="sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)"
    d=f"({r}-0.001)"
    mu=f"((z-0.03)/({r}))"
    a,b,c=RAD_KNOTS
    radial1=smooth_expression(f"(({d})-{a:.17g})/{(b-a):.17g}")
    radial2=smooth_expression(f"(({d})-{b:.17g})/{(c-b):.17g}")
    angle=[smooth_expression(f"(({mu})-{MU_KNOTS[i]:.17g})/"
                             f"{(MU_KNOTS[i+1]-MU_KNOTS[i]):.17g}")
           for i in range(5)]
    pieces=[]
    for row in matrix:
        parts=[f"({row[0]:.17g})"]
        for i in range(5):
            parts.append(f"({row[i+1]-row[i]:.17g})*({angle[i]})")
        pieces.append("("+"+".join(parts)+")")
    # C1 convex interpolation across physical radial shells and mu bands.
    return f"((1-({radial1}))*({pieces[0]})+(({radial1})-({radial2}))*({pieces[1]})+({radial2})*({pieces[2]}))"


def evaluate_numeric(matrix,x,y,z):
    radius=math.sqrt(x*x+y*y+(z-.03)**2+1e-24)
    d=radius-.001
    mu=(z-.03)/radius
    angle=[smooth_numeric((mu-MU_KNOTS[i])/(MU_KNOTS[i+1]-MU_KNOTS[i]))
           for i in range(5)]
    angular=[row[0]+sum((row[i+1]-row[i])*angle[i] for i in range(5))
             for row in matrix]
    s0=smooth_numeric((d-RAD_KNOTS[0])/(RAD_KNOTS[1]-RAD_KNOTS[0]))
    s1=smooth_numeric((d-RAD_KNOTS[1])/(RAD_KNOTS[2]-RAD_KNOTS[1]))
    return (1-s0)*angular[0]+(s0-s1)*angular[1]+s1*angular[2]


def generated_geo():
    original=M0_GEO.read_text(encoding="utf-8")
    base=baseline_field(original)
    matrix=load_matrix()
    logc=logcomp_expression(matrix)
    field=f"({base})*exp((log({PREVIOUS_NOMINAL:.17g})+({logc}))/3)"
    geo=(
        "// P10FW: FRESH uniform M1 desired actual local volume 0.80..0.85.\n"
        "// Size compensation corrects historical remeshing bias, NOT physical kappa(x).\n"
        "// 18 measured signed 3D zones, continuous C1 interpolation in d and mu.\n"
        "// SOURCE-ONLY: no real new M1U GO until independent 729QP.\n"
        'Include "M0.geo";\n'
        "Field[4] = MathEval;\n"
        f"Field[4].F = StrCat(\n  {split_for_gmsh(logc)}\n);\n"
        "Field[5] = MathEval;\n"
        f"Field[5].F = StrCat(\n  {split_for_gmsh(field)}\n);\n"
        "Background Field=5;\n"
        "Mesh.Algorithm=5;\nMesh.Algorithm3D=10;\n"
        "Mesh.ElementOrder=2;\nMesh.HighOrderOptimize=1;\n"
        "Mesh.MeshSizeExtendFromBoundary=0;\n"
        "Mesh.MeshSizeFromPoints=0;\nMesh.MeshSizeFromCurvature=0;\n"
        "Mesh.MeshSizeMin=0;\nMesh.MeshSizeMax=1e22;\n"
        "Mesh.MshFileVersion=2.2;\nMesh.Binary=0;\n"
    )
    need(geo.count('Include "M0.geo"')==1 and geo.count("Background Field=5;")==1
         and "F3" not in field and "F4" not in field,
         "Gmsh source contract")
    return geo,base,matrix,logc,field


def math_selftest():
    geo,base,matrix,logc,field=generated_geo()
    safe={"__builtins__":{},"sqrt":math.sqrt,"min":min,"max":max,
          "exp":math.exp,"log":math.log}
    comp=compile(logc,"<P10FW C1 compensation>","eval")
    full=compile(field,"<P10FW C1 size>","eval")
    original=compile(base,"<P10FW M0 size>","eval")
    samples=[]
    for d in RAD_KNOTS:
        for mu in MU_KNOTS:
            r=.001+d
            samples.append((r*math.sqrt(1-mu*mu),0.,.03+r*mu))
    rng=random.Random(20261122)
    for _ in range(6000):
        d=rng.uniform(0,.027)
        mu=rng.uniform(-1,1)
        phi=rng.uniform(0,math.tau)
        r=.001+d
        samples.append((r*math.sqrt(1-mu*mu)*math.cos(phi),
                        r*math.sqrt(1-mu*mu)*math.sin(phi),.03+r*mu))
    error=0.
    low=math.inf;high=0.
    for x,y,z in samples:
        v=dict(safe,x=x,y=y,z=z)
        expected=evaluate_numeric(matrix,x,y,z)
        actual=eval(comp,v)
        h=eval(full,v)
        h0=eval(original,v)
        need(h>0 and h0>0 and math.isfinite(h), "nonpositive size field")
        predicted=h0*(PREVIOUS_NOMINAL*math.exp(expected))**(1/3)
        error=max(error,abs(expected-actual),abs(h-predicted)/predicted)
        q=(h/h0)**3
        low=min(low,q);high=max(high,q)
    need(error<2e-12,"source MathEval and independent C1 law mismatch")
    return {"status":"P10FW_UNIFORM_TARGET_C1_SOURCE_MATH_PASS_NO_GMSH_NO_FEM",
            "sample_points":len(samples),"max_formula_discrepancy":error,
            "nominal_h3_h0_min":low,"nominal_h3_h0_max":high,
            "target_actual_Veff":TARGET,"strict_real_uniform_gate":[.8,.85],
            "matrix_log_factors":matrix,
            "interpolation_radial_m":RAD_KNOTS,
            "interpolation_mu":MU_KNOTS,
            "math_expression_characters":len(field),
            "scientific_go":False}


if __name__=="__main__":
    print(json.dumps(math_selftest(),ensure_ascii=False,indent=2))
