#!/usr/bin/env python3
"""Compare all P10DN MathEval formulas against independent Python kappa.

This checks mathematical equivalence, NOT that native Gmsh accepts the GEO syntax.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import re


ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"research/proposals/P10DN_M2_COEFF20_SOURCE_ONLY_20261121"
GEO=BASE/"P10DN_M2_FIELD20.geo"
SRC=BASE/"P10DN_m2_coefficient.py"


def main() -> None:
    s=GEO.read_text(encoding="utf-8")
    if 'Include "sphere_pore_B6_refined.geo";' not in s or "Background Field=6;" not in s:
        raise RuntimeError("wrong base CAD or background field")
    expressions={}
    for fid in (3,4,5,6):
        matches=re.findall(rf'^Field\[{fid}\]\.F\s*=\s*"([^"]+)";',s,re.M)
        if len(matches)!=1:
            raise RuntimeError("missing MathEval F"+str(fid))
        expressions[fid]=matches[0]
    spec=importlib.util.spec_from_file_location("p10dn",SRC)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fns={"min":min,"max":max,"sqrt":math.sqrt,"log":math.log,"exp":math.exp}
    checked=0
    for distance in (0.,.00005,.0001,.000105,.0002,.0003,.0004,.0005,.001,.012):
        for mu in (-1.,-.95,-.85,-.8,-.79,-.7,-.6,0.,.6,.7,.79,.8,.85,.95,1.):
            for phi in (0.,.7,2.3,4.9):
                rho=.001+distance
                xy=rho*math.sqrt(max(0.,1-mu*mu))
                x,y,z=xy*math.cos(phi),xy*math.sin(phi),.03+rho*mu
                v={"x":x,"y":y,"z":z,"F2":.0009,**fns}
                for fid in (3,4,5,6):
                    v[f"F{fid}"]=eval(expressions[fid],{"__builtins__":{}},v)
                k=mod.kappa_xyz(x,y,z)
                vr=mod.volume_ratio(k)
                if abs(v["F5"]-k)>2e-12 or abs((v["F6"]/.0009)**3-vr)>3e-12:
                    raise RuntimeError(f"GEO/Python mismatch at {distance=}, {mu=}, {phi=}")
                if not (-1e-12<=v["F5"]<=1+1e-12 and .8-1e-12<=
                        (v["F6"]/.0009)**3<=1+1e-12):
                    raise RuntimeError("GEO volume coefficient outside limit")
                checked+=1
    print("P10DN_M2_GEO_PYTHON_EQUIVALENCE_OK",f"points={checked}",
          "kappa_bound=0..1 target_volume_bound=0.8..1 native_Gmsh=NOT_TESTED FEM=0")


if __name__=="__main__":
    main()
