#!/usr/bin/env python3
"""Deterministically derive M0 C1 smoothed Threshold field from canonical CAD.

This runs at archive BUILD time only, never modifies the user's meshes.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEAR = .0004616510070248522
FAR = .0075970525806110575
A = .0015
B = .018
EPS = .00005


def clamp(x):
    return min(1., max(0., x))


def softplus(t):
    u = clamp((t+EPS)/(2*EPS))
    return max(0.,t-EPS)+EPS*u*u


def value(d):
    return NEAR+(FAR-NEAR)/(B-A)*(softplus(d-A)-softplus(d-B))


def soft_expr(t):
    u = f"min(1,max(0,(({t})+{EPS:.17g})/{2*EPS:.17g}))"
    return f"(max(0,({t})-{EPS:.17g})+{EPS:.17g}*({u})*({u}))"


def make_expression():
    d = "(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.001)"
    return (f"({NEAR:.17g}+{(FAR-NEAR)/(B-A):.17g}*("
            f"{soft_expr(f'({d})-{A:.17g}')}"
            f"-{soft_expr(f'({d})-{B:.17g}')}))")


def main():
    assert abs(value(0)-NEAR)<1e-14 and abs(value(.05)-FAR)<1e-14
    assert all(NEAR-1e-12<=value(k*.00005)<=FAR+1e-12 for k in range(501))
    for endpoint in (A-EPS,A+EPS,B-EPS,B+EPS):
        h=1e-9
        dl=(value(endpoint)-value(endpoint-h))/h
        dr=(value(endpoint+h)-value(endpoint))/h
        assert abs(dl-dr)<1e-4, (endpoint,dl,dr)
    x=make_expression()
    assert "+-" not in x and "--" not in x
    assert x.count("(")==x.count(")")
    segments=[x[i:i+380] for i in range(0,len(x),380)]
    block="Field[3].F = StrCat(\n  "+",\n  ".join('"'+s+'"' for s in segments)+"\n);"
    path=HERE/"M0.geo"
    content=path.read_text(encoding="utf-8")
    start="// P10FP_F3_GENERATED_BEGIN"
    end="// P10FP_F3_GENERATED_END"
    assert content.count(start)==content.count(end)==1
    prefix, tail=content.split(start,1)
    _, suffix=tail.split(end,1)
    new=prefix+start+"\n"+block+"\n"+end+suffix
    path.write_text(new,encoding="utf-8")
    print("P10FP_M0_C1_BASELINE_FIELD_OK",len(x),"near",NEAR,"far",FAR)


if __name__ == "__main__":
    main()
