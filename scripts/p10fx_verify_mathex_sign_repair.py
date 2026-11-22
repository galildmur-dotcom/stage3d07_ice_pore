#!/usr/bin/env python3
"""Prove that the P10FX syntax repair preserves P10FW's intended C1 field.

Source-only numerical equivalence; no native Gmsh mesh or physical FEM claim.
"""
from pathlib import Path
import importlib.util
import math
import random

ROOT=Path(__file__).resolve().parents[1]
OLDER=ROOT/"research/proposals/P10FW_M1_UNIFORM_CALIBRATED_WINDOWS_20261122/P10FW_uniform_math.py"
NEWER=ROOT/"research/proposals/P10FX_M1_UNIFORM_MATHEX_REPAIR_WINDOWS_20261122/P10FX_uniform_math.py"


def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    old=module(OLDER,"old_p10fw_math")
    new=module(NEWER,"new_p10fx_math")
    _,old_base,old_matrix,old_log,old_h=old.generated_geo()
    _,new_base,new_matrix,new_log,new_h=new.generated_geo()
    assert old_base==new_base and old_matrix==new_matrix
    assert "--0.80000000000000004" in old_log
    assert not any(s in new_log+new_h for s in ("--","+-","++","-+"))
    safe={"__builtins__":{},"sqrt":math.sqrt,"min":min,"max":max,
          "exp":math.exp,"log":math.log}
    f=[compile(s,"<native source-only parity>","eval")
       for s in (old_log,new_log,old_h,new_h)]
    rng=random.Random(20261122)
    pts=[]
    for d in new.RAD_KNOTS:
        for mu in new.MU_KNOTS:
            r=.001+d
            pts.append((r*math.sqrt(1-mu*mu),0.,.03+r*mu))
    for _ in range(6000):
        d=rng.uniform(0,.027)
        mu=rng.uniform(-1,1)
        phi=rng.uniform(0,math.tau)
        r=.001+d
        pts.append((r*math.sqrt(1-mu*mu)*math.cos(phi),
                    r*math.sqrt(1-mu*mu)*math.sin(phi),.03+r*mu))
    error=0.
    for x,y,z in pts:
        context=dict(safe,x=x,y=y,z=z)
        a,b,c,d=[eval(expr,context) for expr in f]
        error=max(error,abs(a-b),abs(c-d)/c)
    assert len(pts)==6018 and error<2e-12,(len(pts),error)
    print("P10FX_SIGN_REPAIR_6018_POINTS_SAME_MATH_PASS")
    print("source_old_field_chars",len(old_h),"fixed_field_chars",len(new_h))
    print("max_numeric_diff",error)
    print("NATIVE_GMSH_NOT_TESTED; NO_3D; NO_FEM")


if __name__=="__main__":
    main()
