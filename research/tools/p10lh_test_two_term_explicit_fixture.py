#!/usr/bin/env python3
"""P10LH standalone algebraic QP fixture; no solver, mesh, or FEM imports.

Derivatives of the quotient are checked against an independent complex-step
evaluation of a small synthetic objective. All input values are exact Fractions.
"""
from __future__ import annotations

from fractions import Fraction as F
import json
import math
from pathlib import Path


def qp_fixture():
    # (spatial bin, physical QP volume, source, volume derivative,
    #  volume times source derivative is deliberately evaluated separately)
    return [
        (0, F(2), F(5), F(1, 5), F(3, 7)),
        (0, F(3), F(11), F(-2, 5), F(-1, 3)),
        (1, F(5), F(7), F(3, 5), F(2, 9)),
        (2, F(7), F(13), F(-1, 7), F(1, 4)),
    ]


def exact_split(qps, weight=F(5, 3)):
    volume = sum((v for _, v, _, _, _ in qps), F(0))
    numerator = sum((v * s for _, v, s, _, _ in qps), F(0))
    mean = numerator / volume
    bins = sorted({b for b, *_ in qps})
    out = {}
    for b in bins:
        term = [(v, s, dv, ds) for idx, v, s, dv, ds in qps if idx == b]
        geometry = weight / volume * sum((dv * (s - mean) for v, s, dv, ds in term), F(0))
        stress = weight / volume * sum((v * ds for v, s, dv, ds in term), F(0))
        out[b] = (geometry, stress)
    return out


def complex_step(qps, weight=F(5, 3)):
    # Differentiates the independently formed full quotient using complex step.
    # Here both volumes and source values vary; no split expression appears.
    h = 1e-24
    v_complex = [complex(float(v), h * float(dv)) for _, v, _, dv, _ in qps]
    s_complex = [complex(float(s), h * float(ds)) for _, _, s, _, ds in qps]
    numerator = sum((v * s for v, s in zip(v_complex, s_complex)), 0j)
    denominator = sum(v_complex, 0j)
    return float(weight) * (numerator / denominator).imag / h


def main():
    qps = qp_fixture()
    components = exact_split(qps)
    assert len(components) == 3
    assert all(g != 0 and s != 0 for g, s in components.values())
    total_g = sum((g for g, _ in components.values()), F(0))
    total_s = sum((s for _, s in components.values()), F(0))
    total = total_g + total_s
    independent = complex_step(qps)
    absolute_error = abs(float(total) - independent)
    assert absolute_error < 1e-12, (total, independent, absolute_error)

    # Partition invariance: regrouping all QPs into one spatial cell leaves total.
    combined = exact_split([(0, *values[1:]) for values in qps])
    assert sum((g + s for g, s in combined.values()), F(0)) == total
    assert exact_split(list(reversed(qps))) == components

    # Shifting every source by a constant must leave the normalized geometry
    # contribution and the derivative of the mean unchanged.
    shifted = [(b, v, s + F(79, 6), dv, ds) for b, v, s, dv, ds in qps]
    assert exact_split(shifted) == components
    assert abs(complex_step(shifted) - independent) < 1e-12

    # A zero deformation of QP volume removes only the geometric term.
    fixed_volume = [(b, v, s, F(0), ds) for b, v, s, dv, ds in qps]
    assert all(g == 0 for g, s in exact_split(fixed_volume).values())
    # A zero stress/source derivative removes only the chain-rule term.
    fixed_source = [(b, v, s, dv, F(0)) for b, v, s, dv, ds in qps]
    assert all(s == 0 for g, s in exact_split(fixed_source).values())

    # This incorrect implementation is deliberately required to FAIL the
    # independent reference: omitting quotient normalization is not innocuous.
    vtot = sum((v for _, v, _, _, _ in qps), F(0))
    wrong_without_normalization = F(5, 3) / vtot * sum((dv * s + v * ds for _, v, s, dv, ds in qps), F(0))
    assert abs(float(wrong_without_normalization - total)) > 1e-3

    report = {
        'protocol': 'P10LH_QP_EXPLICIT_TWO_TERM_SOURCE_ONLY',
        'status': 'PASS_SYNTHETIC_ONLY',
        'n_qps': len(qps), 'n_bins': len(components),
        'geometry_exact': str(total_g), 'stress_exact': str(total_s),
        'combined_exact': str(total),
        'complex_step_reference': independent,
        'absolute_error': absolute_error,
        'all_bins_nonzero_both_terms': True,
        'checks': [
            'exact fraction per-bin decomposition',
            'independent complex-step full normalized quotient',
            'permutation and spatial regrouping invariance',
            'invariance under uniform source offset',
            'volume-derivative-off removes only geometry',
            'source-derivative-off removes only stress',
            'missing normalization produces demonstrably wrong answer',
        ],
        'mesh_generation_attempts': 0, 'FEM_attempts': 0,
        'limitation': 'Does not execute Tet10 C++ mechanical_step or validate physical M8/M9 source states.',
    }
    destination = Path(__file__).resolve().parents[2] / 'research' / 'P10LH_SYNTHETIC_QP_QA.json'
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
